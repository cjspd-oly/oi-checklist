import re
import time
import random
import requests
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, redirect
import sqlite3
import hashlib
import os
from dotenv import load_dotenv
from flask_cors import CORS
from datetime import timedelta, datetime
import pytz
from functools import wraps
import json
import uuid
from requests_oauthlib import OAuth2Session

# our functions
from database.db import get_db
from scrape.ojuz import sync_ojuz_submissions, verify_ojuz, update_ojuz_scores
from auth.session import session_required
from auth.github import *
from auth.discord import *
from auth.google import *
from auth.auth import *
from notes.notes import get_note, save_note
from virtual_contests.vc import *

# this is probably really bad but the website doesn't work without it
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SESSION_COOKIE_SAMESITE'] = 'None' if os.getenv("FLASK_ENV") == "production" else 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = os.getenv("FLASK_ENV") == "production"
    CORS(app, supports_credentials=True, origins=[os.getenv("FRONTEND_URL")])
    return app

app = create_app()

# Notes api
app.add_url_rule("/api/note", view_func=session_required(get_note), methods=["GET"])
app.add_url_rule("/api/note", view_func=session_required(save_note), methods=["POST"])

# Auth
## GitHub oauth
app.add_url_rule("/auth/github/start", view_func=github_start, methods=["GET"])
app.add_url_rule("/auth/github/link", view_func=github_link, methods=["GET"])
app.add_url_rule("/auth/github/callback", view_func=github_callback, methods=["GET"])
app.add_url_rule("/api/github/status", view_func=session_required(github_status), methods=["GET"])
app.add_url_rule("/api/github/unlink", view_func=session_required(github_unlink), methods=["POST"])

## Discord oauth
app.add_url_rule("/auth/discord/start", view_func=discord_start)
app.add_url_rule("/auth/discord/link", view_func=discord_link)
app.add_url_rule("/auth/discord/callback", view_func=discord_callback)
app.add_url_rule("/api/discord/status", view_func=session_required(discord_status))
app.add_url_rule("/api/discord/unlink", view_func=session_required(discord_unlink), methods=["POST"])

## Google oauth
app.add_url_rule("/auth/google/start", view_func=google_start)
app.add_url_rule("/auth/google/link", view_func=google_link)
app.add_url_rule("/auth/google/callback", view_func=google_callback)
app.add_url_rule("/api/google/status", view_func=session_required(google_status))
app.add_url_rule("/api/google/unlink", view_func=session_required(google_unlink), methods=["POST"])

## regular auth
app.add_url_rule("/api/register", view_func=api_register, methods=["POST"])
app.add_url_rule("/api/login", view_func=api_login, methods=["POST"])
app.add_url_rule("/api/whoami", view_func=session_required(whoami), methods=["GET"])
app.add_url_rule("/api/logout", view_func=session_required(api_logout), methods=["POST"])

# oj.uz sync stuff (out of contest)
app.add_url_rule("/api/verify-ojuz", view_func=session_required(verify_ojuz), methods=["POST"])
app.add_url_rule("/api/update-ojuz", view_func=session_required(update_ojuz_scores), methods=["POST"])

# virtual contest stuff
app.add_url_rule("/api/virtual-contests", view_func=session_required(get_virtual_contests), methods=["GET"])
app.add_url_rule("/api/virtual-contests/history", view_func=session_required(get_virtual_contest_history), methods=["GET"])
app.add_url_rule("/api/virtual-contests/start", view_func=session_required(start_virtual_contest), methods=["POST"])
app.add_url_rule("/api/virtual-contests/end", view_func=session_required(end_virtual_contest), methods=["POST"])
app.add_url_rule("/api/virtual-contests/confirm", view_func=session_required(confirm_virtual_contest), methods=["POST"])
app.add_url_rule("/api/virtual-contests/submit", view_func=session_required(submit_virtual_contest), methods=["POST"])
app.add_url_rule("/api/contest-scores", view_func=session_required(get_contest_scores), methods=["GET"])
app.add_url_rule("/api/virtual-contests/detail/<slug>", view_func=session_required(get_virtual_contest_detail), methods=["GET"])

@app.route('/api/settings', methods=["GET"])
@session_required
def get_user_settings():
    user_id = request.user_id
    db = get_db()

    row = db.execute(
        'SELECT checklist_public FROM user_settings WHERE user_id = ?',
        (user_id,)
    ).fetchone()

    # If no row yet, assume default (private)
    checklist_public = bool(row['checklist_public']) if row else False

    return jsonify({
        "checklist_public": checklist_public
    })

@app.route('/api/settings', methods=["POST"])
@session_required
def update_user_settings():
    user_id = request.user_id
    db = get_db()

    data = request.get_json()
    if 'checklist_public' not in data:
        return jsonify({"error": "Missing 'checklist_public' in request body"}), 400

    checklist_public = int(bool(data['checklist_public']))  # sanitize to 0/1

    db.execute('''
        INSERT INTO user_settings (user_id, checklist_public)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET checklist_public = excluded.checklist_public
    ''', (user_id, checklist_public))
    db.commit()

    return jsonify({"success": True})

@app.route('/api/problems', methods=["GET"])
@session_required
def get_problems():
    from_names = request.args.get('names')
    if not from_names:
        return jsonify({"error": "Missing 'names' query parameter"}), 400

    # Split the names by comma and strip any leading/trailing whitespace
    from_names = [name.strip() for name in from_names.split(',')]

    user_id = request.user_id  # Get user ID from JWT token
    db = get_db()

    # Prepare the query for fetching problems for multiple sources
    placeholders = ', '.join(['?'] * len(from_names))  # Create placeholders for the sources
    problems_raw = db.execute(
        f'SELECT *, COALESCE(number, 0) as number FROM problems WHERE source IN ({placeholders}) ORDER BY source, year, number',
        tuple(from_names)
    ).fetchall()

    # Get progress data for all the sources
    progress_rows = db.execute(
        f'SELECT problem_name, source, year, status, score FROM problem_statuses WHERE user_id = ? AND source IN ({placeholders})',
        (user_id, *from_names)
    ).fetchall()

    # Organize progress by (problem_name, source, year)
    progress = {
        (row['problem_name'], row['source'], row['year']): {
            'status': row['status'],
            'score': row['score']
        }
        for row in progress_rows
    }

    # Prepare the response structure
    problems_by_category = {}

    for row in problems_raw:
        source = row['source']
        year = row['year']
        problem = dict(row)
        problem.pop("id", None)  # Remove the ID, assuming it's not needed in the response

        # Include 'extra' only if it exists and is not None
        if 'extra' in row.keys() and row['extra'] is not None:
            problem['extra'] = row['extra']

        key = (problem['name'], problem['source'], problem['year'])
        if key in progress:
            problem['status'] = progress[key]['status']
            problem['score'] = progress[key]['score']
        else:
            problem['status'] = 0
            problem['score'] = 0

        if source not in problems_by_category:
            problems_by_category[source] = {}

        problems_by_category[source].setdefault(year, []).append(problem)

    return jsonify(problems_by_category)

@app.route('/api/user', methods=["GET"])
def get_user():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Missing 'username' query parameter"}), 400

    problems = request.args.get('problems', '')
    problems_list = [p.strip() for p in problems.split(',')] if problems else []

    db = get_db()

    user = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if not user:
        return jsonify({"error": f"User {username} not found"}), 404

    user_id = user['id']

    checklist_public_row = db.execute("SELECT checklist_public FROM user_settings WHERE user_id = ?", (user_id,)).fetchone()
    checklist_public = checklist_public_row['checklist_public'] if checklist_public_row else 0

    if checklist_public == 0:
        return jsonify({"error": f"{username}'s checklist is private."}), 403

    problems_by_category = {}
    if problems_list:
        placeholders = ', '.join(['?'] * len(problems_list))

        # Get all problems for the selected sources
        problems_raw = db.execute(
            f'SELECT *, COALESCE(number, 0) as number FROM problems WHERE source IN ({placeholders}) ORDER BY source, year, number',
            tuple(problems_list)
        ).fetchall()

        # Get the user's status and score for these problems
        progress_rows = db.execute(
            f'''
            SELECT problem_name, source, year, status, score
            FROM problem_statuses
            WHERE user_id = ? AND source IN ({placeholders})
            ''',
            (user_id, *problems_list)
        ).fetchall()

        progress = {
            (row['problem_name'], row['source'], row['year']): {
                'status': row['status'],
                'score': row['score']
            }
            for row in progress_rows
        }

        for row in problems_raw:
            source = row['source']
            year = row['year']
            problem = dict(row)
            problem.pop("id", None)

            key = (problem['name'], problem['source'], problem['year'])
            if key in progress:
                problem['status'] = progress[key]['status']
                problem['score'] = progress[key]['score']
            else:
                problem['status'] = 0
                problem['score'] = 0

            if source not in problems_by_category:
                problems_by_category[source] = {}
            problems_by_category[source].setdefault(year, []).append(problem)

    return jsonify({
        "username": username,
        "checklist_public": checklist_public,
        "problems": problems_by_category
    })

@app.route('/api/update-problem-status', methods=['POST'])
@session_required
def update_problem_status():
    data = request.get_json()
    user_id = request.user_id

    problem_name = data.get('problem_name')
    source = data.get('source')
    year = data.get('year')
    status = data.get('status')

    if not all([problem_name, source, year, status is not None]):
        return jsonify({"error": "Missing required fields"}), 400

    db = get_db()
    db.execute(
        '''
        INSERT INTO problem_statuses (user_id, problem_name, source, year, status)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, problem_name, source, year)
        DO UPDATE SET status = ?
        ''',
        (user_id, problem_name, source, year, status, status)
    )
    db.commit()
    db.close()
    return jsonify(success=True)

@app.route('/api/update-problem-score', methods=['POST'])
@session_required
def update_problem_score():
    data = request.get_json()
    user_id = request.user_id  

    problem_name = data.get('problem_name')
    source = data.get('source')
    year = data.get('year')
    score = data.get('score')

    if not all([problem_name, source, year, score is not None]):
        return jsonify({"error": "Missing required fields"}), 400

    db = get_db()
    db.execute(
        '''
        INSERT INTO problem_statuses (user_id, problem_name, source, year, score)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, problem_name, source, year)
        DO UPDATE SET score = ?
        ''',
        (user_id, problem_name, source, year, score, score)
    )
    db.commit()
    db.close()
    return jsonify(success=True)

@app.route('/api/update-olympiad-order', methods=['POST'])
@session_required
def update_olympiad_order():
    data = request.get_json()
    user_id = request.user_id

    olympiad_order = data.get('olympiad_order')
    hidden = data.get('hidden')

    if not isinstance(olympiad_order, list):
        return jsonify({"error": "Invalid or missing olympiad_order"}), 400
    if hidden is not None and not isinstance(hidden, list):
        return jsonify({"error": "Invalid 'hidden' list"}), 400

    db = get_db()
    db.execute(
        '''
        INSERT INTO user_settings (user_id, olympiad_order, hidden)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET 
            olympiad_order = excluded.olympiad_order,
            hidden = excluded.hidden
        ''',
        (user_id, json.dumps(olympiad_order), json.dumps(hidden) if hidden is not None else json.dumps([]))
    )
    db.commit()
    db.close()

    return jsonify(success=True)

@app.route('/api/get-olympiad-order', methods=['GET'])
def get_olympiad_order():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Missing 'username' query parameter"}), 400
    db = get_db()
    # Get user ID from username
    user = db.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    if not user:
        db.close()
        return jsonify({"error": f"User '{username}' not found"}), 404

    user_id = user['id']
    # Fetch olympiad order and hidden list
    row = db.execute(
        '''
        SELECT olympiad_order, hidden FROM user_settings
        WHERE user_id = ?
        ''',
        (user_id,)
    ).fetchone()
    db.close()
    olympiad_order = None
    hidden = None
    if row:
        if row['olympiad_order']:
            try:
                olympiad_order = json.loads(row['olympiad_order'])
            except Exception:
                return jsonify({"error": "Failed to parse olympiad_order"}), 500
        if row['hidden']:
            try:
                hidden = json.loads(row['hidden'])
            except Exception:
                return jsonify({"error": "Failed to parse hidden"}), 500
    return jsonify(olympiad_order=olympiad_order, hidden=hidden)

@app.route('/api/demo-login', methods=["POST"])
def api_demo_login():
    """
    Demo login endpoint that provides a fixed session for the demo account.
    This avoids creating infinite temporary sessions.
    """
    db = get_db()
    
    # Fixed demo account details
    demo_username = "demo-user"
    demo_session_id = "demo-session-fixed-token-123456789"
    
    # Ensure demo user exists
    demo_user = db.execute("SELECT id FROM users WHERE username = ?", (demo_username,)).fetchone()
    if not demo_user:
        # Create demo user if it doesn't exist
        db.execute("INSERT INTO users (username) VALUES (?)", (demo_username,))
        demo_user_id = db.execute("SELECT id FROM users WHERE username = ?", (demo_username,)).fetchone()["id"]
    else:
        demo_user_id = demo_user["id"]
    
    # Ensure demo session exists (or update if user_id changed)
    existing_session = db.execute("SELECT user_id FROM sessions WHERE session_id = ?", (demo_session_id,)).fetchone()
    if not existing_session:
        # Create fixed demo session
        db.execute("INSERT INTO sessions (session_id, user_id) VALUES (?, ?)", (demo_session_id, demo_user_id))
    elif existing_session["user_id"] != demo_user_id:
        # Update session to point to correct demo user
        db.execute("UPDATE sessions SET user_id = ? WHERE session_id = ?", (demo_user_id, demo_session_id))
    
    db.commit()
    
    return jsonify({
        "success": True, 
        "token": demo_session_id,
        "username": demo_username
    })

@app.route('/api/settings/sync', methods=["POST"])
@session_required
def sync_settings_to_account():
    data = request.get_json(silent=True) or {}
    local_storage_data = data.get("local_storage")
    db = get_db()
    # Store localStorage in user_settings
    if local_storage_data is not None:
        db.execute(
            "UPDATE user_settings SET local_storage = ? WHERE user_id = ?",
            (local_storage_data, request.user_id)
        )
        db.commit()
        return jsonify({"success": True, "message": "Settings synced successfully."})
    return jsonify({"success": False, "message": "No settings data provided."}), 400

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=os.getenv("PORT"))
