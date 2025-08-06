import re
import time
import random
import requests
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template, request, jsonify, redirect, abort
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

# this is probably really bad but the website doesn't work without it
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

load_dotenv()  # Load environment variables from .env

app = Flask(__name__)
# Allow cookies to be sent from frontend
app.config['SESSION_COOKIE_SAMESITE'] = 'None' if os.getenv("FLASK_ENV") == "production" else 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv("FLASK_ENV") == "production"
CORS(app, supports_credentials=True, origins=["https://checklist.spoi.org.in"])
app.secret_key = "your-secret-key"
app.permanent_session_lifetime = timedelta(days=1)

def get_db():
    db_path = os.getenv("DATABASE_PATH", "database.db")  # fallback to "database.db" if not set
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def session_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return jsonify({"error": "Token is missing"}), 403
        session_id = auth.split(" ")[1]
        db = get_db()
        row = db.execute("SELECT user_id FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if not row:
            return jsonify({"error": "Invalid or expired session"}), 401
        request.user_id = row["user_id"]
        return f(*args, **kwargs)
    return decorated_function

# GitHub OAuth config from .env
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_CALLBACK_URL = os.getenv("BACKEND_URL") + "/auth/github/callback"
GITHUB_AUTH_URL = 'https://github.com/login/oauth/authorize'
GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'
GITHUB_USER_API = 'https://api.github.com/user'

FRONTEND_URL = os.getenv("FRONTEND_URL")

@app.route("/auth/github/start")
def github_start():
    github = OAuth2Session(GITHUB_CLIENT_ID, redirect_uri=GITHUB_CALLBACK_URL)
    auth_url, _ = github.authorization_url(GITHUB_AUTH_URL)
    return redirect(auth_url)

@app.route("/auth/github/link")
def github_link():
    state = request.args.get("state")
    session_token = request.args.get("session_id")
    redirect_to = request.args.get("redirect_to", "/")  # default to home if not specified

    if not state or not session_token:
        return jsonify({"error": "Missing OAuth state or session token"}), 400

    db = get_db()
    session = db.execute("SELECT user_id FROM sessions WHERE session_id = ?", (session_token,)).fetchone()
    if not session:
        return jsonify({"error": "Invalid or expired session"}), 401

    user_id = session["user_id"]
    github = OAuth2Session(GITHUB_CLIENT_ID, redirect_uri=GITHUB_CALLBACK_URL)
    auth_url, new_state = github.authorization_url(
        GITHUB_AUTH_URL, state=state
    )

    if not hasattr(app, 'oauth_state_map'):
        app.oauth_state_map = {}
    app.oauth_state_map[state] = {
        "user_id": user_id,
        "redirect_to": redirect_to
    }

    return redirect(auth_url)

@app.route("/auth/github/callback")
def github_callback():
    github = OAuth2Session(GITHUB_CLIENT_ID, redirect_uri=GITHUB_CALLBACK_URL)
    try:
        token = github.fetch_token(
            GITHUB_TOKEN_URL,
            client_secret=GITHUB_CLIENT_SECRET,
            authorization_response=request.url
        )
    except Exception as e:
        return jsonify({"error": "OAuth token exchange failed", "details": str(e)}), 400

    # Get user info from GitHub
    resp = github.get(GITHUB_USER_API)
    if not resp.ok:
        return jsonify({"error": "Failed to fetch user info from GitHub"}), 400

    github_info = resp.json()
    github_id = str(github_info.get("id"))
    github_username = github_info.get("login")

    db = get_db()

    # Check if this GitHub account is already linked
    identity = db.execute(
        "SELECT user_id FROM auth_identities WHERE provider = ? AND provider_user_id = ?",
        ("github", github_id)
    ).fetchone()

    # Load any pending link request
    linking_data = None
    state = request.args.get("state")
    if state and hasattr(app, "oauth_state_map"):
        linking_data = app.oauth_state_map.pop(state, None)

    if identity:
        user_id = identity["user_id"]
    elif linking_data:
        user_id = linking_data["user_id"]
        db.execute(
            "INSERT INTO auth_identities (user_id, provider, provider_user_id, display_name) VALUES (?, ?, ?, ?)",
            (user_id, "github", github_id, github_username)
        )
        db.commit()
    else:
        # Create a new user
        base_username = github_username
        attempt = 0
        while True:
            candidate = f"{base_username}" if attempt == 0 else f"{base_username}-{attempt}"
            taken = db.execute("SELECT 1 FROM users WHERE username = ?", (candidate,)).fetchone()
            if not taken:
                github_username = candidate
                break
            attempt += 1

        db.execute("INSERT INTO users (username) VALUES (?)", (github_username,))
        user_id = db.execute("SELECT id FROM users WHERE username = ?", (github_username,)).fetchone()["id"]
        db.execute(
            "INSERT INTO auth_identities (user_id, provider, provider_user_id, display_name) VALUES (?, ?, ?, ?)",
            (user_id, "github", github_id, github_username)
        )
        db.commit()

    # Create new session
    session_id = str(uuid.uuid4())
    db.execute("INSERT INTO sessions (session_id, user_id) VALUES (?, ?)", (session_id, user_id))
    db.commit()

    # Redirect back to frontend
    redirect_to = linking_data["redirect_to"] if linking_data and "redirect_to" in linking_data else "/"
    return redirect(f"{FRONTEND_URL}/github-auth-success.html?token={session_id}&redirect_to={redirect_to}")

@app.route("/api/github/status")
@session_required
def github_status():
    db = get_db()
    identity = db.execute(
        "SELECT display_name FROM auth_identities WHERE provider = ? AND user_id = ?",
        ("github", request.user_id)
    ).fetchone()

    if identity:
        return jsonify({"github_username": identity["display_name"]}), 200
    else:
        return jsonify({"error": "GitHub not linked"}), 404


@app.route("/api/github/unlink", methods=["POST"])
@session_required
def github_unlink():
    db = get_db()
    identity = db.execute(
        "SELECT id FROM auth_identities WHERE provider = ? AND user_id = ?",
        ("github", request.user_id)
    ).fetchone()
    if not identity:
        return jsonify({"error": "No linked GitHub account"}), 400
    linked_count = db.execute(
        """
        SELECT 
            (SELECT COUNT(*) FROM auth_identities WHERE user_id = ?) +
            (SELECT CASE WHEN password IS NOT NULL THEN 1 ELSE 0 END FROM users WHERE id = ?)
        """,
        (request.user_id, request.user_id)
    ).fetchone()[0]
    if linked_count <= 1:
        return jsonify({"error": "You cannot unlink GitHub as it's your only login method!"}), 400
    db.execute(
        "DELETE FROM auth_identities WHERE provider = ? AND user_id = ?",
        ("github", request.user_id)
    )
    db.commit()
    return jsonify({"success": True, "message": "GitHub unlinked successfully."})

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json()
    username = data.get("username")
    password_raw = data.get("password")
    if not username or not password_raw:
        return jsonify({"error": "Missing username or password"}), 400
    password = hashlib.sha256(password_raw.encode()).hexdigest()
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
    existing_user = cursor.fetchone()
    if existing_user:
        return jsonify({"error": "Username taken"}), 409
    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    db.commit()
    return jsonify({"message": "User registered successfully"}), 201

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json
    username = data.get("username")
    password = hashlib.sha256(data.get("password", "").encode()).hexdigest()
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()
    if user:
        session_id = str(uuid.uuid4())
        db.execute("INSERT INTO sessions (session_id, user_id) VALUES (?, ?)", (session_id, user["id"]))
        db.commit()
        return jsonify({"success": True, "token": session_id})
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route('/api/whoami', methods=["GET"])
@session_required
def whoami():
    db = get_db()
    user = db.execute("SELECT username FROM users WHERE id=?", (request.user_id,)).fetchone()
    if user:
        return jsonify({'username': user['username']})
    return jsonify({'error': 'User not found'}), 404

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

@app.route('/api/verify-ojuz', methods=['POST'])
@session_required
def verify_ojuz():
    data = request.get_json()
    oidc_auth_cookie = data.get('cookie')

    if not oidc_auth_cookie:
        return jsonify({"error": "Missing cookie"}), 400
    # URL of the homepage
    homepage_url = 'https://oj.uz'
    # Send a GET request to the homepage with the OIDC cookie
    headers = {
        'Cookie': f'oidc-auth={oidc_auth_cookie}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    try:
        response = requests.get(homepage_url, headers=headers, timeout=5)
        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch homepage"}), 500
        # Check if the username appears on the homepage by looking for the specific span element
        match = re.search(r'<span><a href="/profile/([^"]+)">([^<]+)</a></span>', response.text)
        if match:
            username = match.group(2)  # Extract the username
            return jsonify({"valid": True, "username": username})
        else:
            # If no match found, the user is not logged in
            return jsonify({"valid": False}), 400
    except Exception as e:
        return jsonify({"error": f"Error fetching homepage: {str(e)}"}), 500

@app.route('/api/update-ojuz', methods=['POST'])
@session_required
def update_ojuz_scores():
    data = request.get_json()
    oidc_auth = data.get('cookie')
    if not oidc_auth:
        return jsonify({'error': 'Missing oidc-auth cookie'}), 400

    user_id = request.user_id
    db = get_db()

    # Step 1: Fetch all oj.uz problems + current progress
    sources = [
        'APIO', 'EGOI', 'INOI', 'ZCO', 'IOI', 'JOIFR', 'JOISC', 'IOITC',
        'NOIPRELIM', 'NOIQUAL', 'NOIFINAL', 'POI', 'NOISEL', 'CEOI', 'COI', 'BOI'
    ]
    placeholders = ', '.join(['?'] * len(sources))
    problem_rows = db.execute(
        f"SELECT name, link, source, year, COALESCE(number, 0) as number FROM problems WHERE source IN ({placeholders})",
        tuple(sources)
    ).fetchall()

    progress_rows = db.execute(
        f"SELECT problem_name, source, year, status, score FROM problem_statuses "
        f"WHERE user_id = ? AND source IN ({placeholders})",
        (user_id, *sources)
    ).fetchall()

    # Organize progress
    progress = {
        (row['problem_name'], row['source'], row['year']): {
            'status': row['status'],
            'score': row['score']
        }
        for row in progress_rows
    }

    # Filter only oj.uz problems
    oj_problems = [
        {
            'name': row['name'],
            'link': row['link'],
            'source': row['source'],
            'year': row['year']
        }
        for row in problem_rows if row['link'].startswith('https://oj.uz/')
    ]

    # Step 2: Fetch scores using threads
    headers = {
        'Cookie': f'oidc-auth={oidc_auth}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }

    def fetch_score(problem):
        print("Fetching:", problem['link'])
        try:
            time.sleep(random.uniform(0.2, 0.5))
            res = requests.get(problem['link'], headers=headers, timeout=5)
            if 'Sign in' in res.text:
                return 'INVALID_COOKIE'
            match = re.search(r"circleProgress\(\s*{\s*value:\s*([0-9.]+)", res.text)
            if match:
                score = round(float(match.group(1)) * 100)
                print("Score for", problem['name'], ":", score)
                return (problem, score)
            else:
                print("No score found for", problem['name'])
        except Exception as e:
            print("Error fetching", problem['name'], ":", e)
        return None

    results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for result in executor.map(fetch_score, oj_problems):
            if result == 'INVALID_COOKIE':
                return jsonify({'error': 'Invalid or expired cookie'}), 401
            if result is not None:
                results.append(result)

    updated = 0
    for problem, new_score in results:
        key = (problem['name'], problem['source'], problem['year'])
        old = progress.get(key, {'status': 0, 'score': 0})

        # Set new score to max(new score, old score)
        new_score = max(new_score, old['score'])

        # Determine the new status based on the new score
        if new_score == 100:
            new_status = 2  # solved
        elif 0 < new_score < 100:
            new_status = 1  # in progress
        else:
            new_status = 0  # failed

        # Always update the entry, even if the score hasn't changed
        db.execute(
            '''
            INSERT INTO problem_statuses (user_id, problem_name, source, year, score, status)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, problem_name, source, year)
            DO UPDATE SET score = ?, status = ?
            ''',
            (
                user_id, problem['name'], problem['source'], problem['year'], new_score, new_status,
                new_score, new_status
            )
        )
        updated += 1
        print(f"Updated {problem['name']} to score {new_score} and status {new_status}")

    db.commit()
    db.close()
    return jsonify({'updated': updated, 'total_checked': len(results)}), 200

@app.route('/api/update-olympiad-order', methods=['POST'])
@session_required
def update_olympiad_order():
    data = request.get_json()
    user_id = request.user_id

    olympiad_order = data.get('olympiad_order')
    if not isinstance(olympiad_order, list):
        return jsonify({"error": "Invalid or missing olympiad_order"}), 400

    db = get_db()
    db.execute(
        '''
        INSERT INTO user_settings (user_id, olympiad_order)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET olympiad_order = excluded.olympiad_order
        ''',
        (user_id, json.dumps(olympiad_order))
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

    # Fetch olympiad order
    row = db.execute(
        '''
        SELECT olympiad_order FROM user_settings
        WHERE user_id = ?
        ''',
        (user_id,)
    ).fetchone()

    db.close()

    if row and row['olympiad_order']:
        try:
            order = json.loads(row['olympiad_order'])
            return jsonify(olympiad_order=order)
        except Exception:
            return jsonify({"error": "Failed to parse olympiad_order"}), 500
    else:
        return jsonify(olympiad_order=None)

@app.route('/api/logout', methods=["POST"])
@session_required
def api_logout():
    session_id = request.headers.get("Authorization").split(" ")[1]
    db = get_db()
    db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    db.commit()
    return jsonify({"success": True, "message": "Logged out successfully."})

@app.route('/api/virtual-contests', methods=["GET"])
@session_required
def get_virtual_contests():
    user_id = request.user_id
    db = get_db()
    
    # Check if user has an active virtual contest
    active_contest = db.execute('''
        SELECT 
            avc.contest_name,
            avc.contest_stage,
            avc.start_time,
            avc.end_time,
            c.duration_minutes,
            c.location,
            c.website,
            c.link
        FROM active_virtual_contests avc
        JOIN contests c ON avc.contest_name = c.name AND avc.contest_stage = c.stage
        WHERE avc.user_id = ?
    ''', (user_id,)).fetchone()
    
    # Get all contests with their problems
    contests = db.execute('''
        SELECT 
            name, stage, source, year, duration_minutes,
            COALESCE(location, '') as location,
            COALESCE(website, '') as website,
            COALESCE(link, '') as link,
            COALESCE(date, '') as date,
            COALESCE(notes, '') as notes
        FROM contests 
        ORDER BY year DESC, source, stage
    ''').fetchall()
    
    # Get contest problems for all contests
    contest_problems = db.execute('''
        SELECT 
            cp.contest_name,
            cp.contest_stage,
            cp.problem_source,
            cp.problem_year,
            cp.problem_number,
            cp.problem_index
        FROM contest_problems cp
        ORDER BY cp.contest_name, cp.contest_stage, cp.problem_index
    ''').fetchall()
    
    # Get last 3 virtual contests for this user
    recent_virtuals = db.execute('''
        SELECT 
            v.contest_name, v.contest_stage,
            c.source as contest_source, c.year as contest_year,
            v.started_at,
            v.score as total_score,
            v.per_problem_scores,
            CASE 
                WHEN c.link LIKE '%oj.uz%' THEN 'oj.uz'
                ELSE 'manual'
            END as platform
        FROM user_virtual_contests v
        JOIN contests c ON v.contest_name = c.name AND v.contest_stage = c.stage
        WHERE v.user_id = ?
        ORDER BY v.started_at DESC
        LIMIT 3
    ''', (user_id,)).fetchall()

    # Get all completed contests for this user
    completed_contests = db.execute('''
        SELECT DISTINCT contest_name || '|' || contest_stage as contest_key
        FROM user_virtual_contests
        WHERE user_id = ?
    ''', (user_id,)).fetchall()

    # Convert to dictionary format
    contests_dict = {}
    for c in contests:
        source = c['source']
        year = c['year']
        if source not in contests_dict:
            contests_dict[source] = {}
        if year not in contests_dict[source]:
            contests_dict[source][year] = []
        
        contest_dict = dict(c)
        # Add problems for this contest
        contest_dict['problems'] = []
        for cp in contest_problems:
            if cp['contest_name'] == c['name'] and cp['contest_stage'] == c['stage']:
                contest_dict['problems'].append({
                    'source': cp['problem_source'],
                    'year': cp['problem_year'],
                    'number': cp['problem_number'],
                    'index': cp['problem_index']
                })
        
        contests_dict[source][year].append(contest_dict)

    recent_list = [dict(v) for v in recent_virtuals]
    completed_list = [row['contest_key'] for row in completed_contests]

    result = {
        'contests': contests_dict,
        'recent': recent_list,
        'completed_contests': completed_list
    }
    
    # Add active contest info if exists
    if active_contest:
        result['active_contest'] = dict(active_contest)
    
    return jsonify(result)

@app.route('/api/virtual-contests/history', methods=["GET"])
@session_required
def get_virtual_contest_history():
    user_id = request.user_id
    db = get_db()
    
    # Get all virtual contests for this user
    contests = db.execute('''
        SELECT 
            v.contest_name,
            v.contest_stage,
            c.source as contest_source,
            c.year as contest_year,
            v.started_at,
            v.ended_at,
            v.score as total_score,
            v.per_problem_scores,
            CASE 
                WHEN c.link LIKE '%oj.uz%' THEN 'oj.uz'
                ELSE 'manual'
            END as platform
        FROM user_virtual_contests v
        JOIN contests c ON v.contest_name = c.name AND v.contest_stage = c.stage
        WHERE v.user_id = ?
        ORDER BY v.started_at DESC
    ''', (user_id,)).fetchall()
    
    # Convert to list of dictionaries
    contests_list = [dict(contest) for contest in contests]
    
    return jsonify({
        'contests': contests_list
    })

@app.route('/api/virtual-contests/start', methods=["POST"])
@session_required
def start_virtual_contest():
    user_id = request.user_id
    data = request.get_json()
    
    contest_name = data.get('contest_name')
    contest_stage = data.get('contest_stage')
    
    if not all([contest_name, contest_stage]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    db = get_db()
    
    # Check if user already has an active contest
    existing = db.execute(
        'SELECT 1 FROM active_virtual_contests WHERE user_id = ?',
        (user_id,)
    ).fetchone()
    
    if existing:
        return jsonify({'error': 'User already has an active contest'}), 400
    
    # Check if user has already completed this contest
    completed = db.execute(
        'SELECT 1 FROM user_virtual_contests WHERE user_id = ? AND contest_name = ? AND contest_stage = ?',
        (user_id, contest_name, contest_stage)
    ).fetchone()
    
    if completed:
        return jsonify({'error': 'Contest already completed'}), 400
    
    # Verify contest exists
    contest_exists = db.execute(
        'SELECT 1 FROM contests WHERE name = ? AND stage = ?',
        (contest_name, contest_stage)
    ).fetchone()
    
    if not contest_exists:
        return jsonify({'error': 'Contest not found'}), 404
    
    # Start the virtual contest with UTC timestamp
    utc_now = datetime.now(pytz.UTC).isoformat()
    db.execute('''
        INSERT INTO active_virtual_contests 
        (user_id, contest_name, contest_stage, start_time)
        VALUES (?, ?, ?, ?)
    ''', (user_id, contest_name, contest_stage, utc_now))
    
    db.commit()
    return jsonify({'success': True})

@app.route('/api/virtual-contests/end', methods=["POST"])
@session_required
def end_virtual_contest():
    user_id = request.user_id
    data = request.get_json()
    
    # Get optional oj.uz username for auto-sync
    ojuz_username = data.get('ojuz_username')
    
    db = get_db()
    
    # Get the active contest
    active_contest = db.execute('''
        SELECT contest_name, contest_stage, start_time
        FROM active_virtual_contests 
        WHERE user_id = ?
    ''', (user_id,)).fetchone()
    
    if not active_contest:
        return jsonify({'error': 'No active contest found'}), 404
    
    utc_now = datetime.now(pytz.UTC).isoformat()
    
    # Handle oj.uz sync if username provided
    if ojuz_username:
        # TODO: Implement oj.uz score syncing logic
        # For now, just mark as ended
        pass
    
    # Update the active contest with end_time
    db.execute('''
        UPDATE active_virtual_contests 
        SET end_time = ?
        WHERE user_id = ?
    ''', (utc_now, user_id))
    
    db.commit()
    return jsonify({'success': True})

@app.route('/api/virtual-contests/submit', methods=["POST"])
@session_required
def submit_virtual_contest():
    user_id = request.user_id
    data = request.get_json()
    
    # Get scores data
    scores = data.get('scores', [])
    total_score = data.get('total_score', 0)
    
    if not scores:
        return jsonify({'error': 'No scores provided'}), 400
    
    db = get_db()
    
    # Get the ended active contest
    active_contest = db.execute('''
        SELECT contest_name, contest_stage, start_time, end_time
        FROM active_virtual_contests 
        WHERE user_id = ? AND end_time IS NOT NULL
    ''', (user_id,)).fetchone()
    
    if not active_contest:
        return jsonify({'error': 'No ended contest found'}), 404
    
    contest_name = active_contest['contest_name']
    contest_stage = active_contest['contest_stage']
    start_time = active_contest['start_time']
    end_time = active_contest['end_time']
    
    # Save the virtual contest result to main table
    db.execute('''
        INSERT OR REPLACE INTO user_virtual_contests 
        (user_id, contest_name, contest_stage, started_at, ended_at, score, per_problem_scores)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, contest_name, contest_stage, start_time, end_time, total_score, json.dumps(scores)))
    
    # Remove from active contests
    db.execute('DELETE FROM active_virtual_contests WHERE user_id = ?', (user_id,))
    
    db.commit()
    return jsonify({'success': True})

@app.route('/api/virtual-contests/sync-ojuz', methods=["POST"])
@session_required
def sync_ojuz_virtual_contest():
    user_id = request.user_id
    data = request.get_json()
    
    ojuz_username = data.get('ojuz_username')
    
    if not ojuz_username:
        return jsonify({'error': 'Missing oj.uz username'}), 400
    
    # TODO: Implement oj.uz score syncing logic
    # For now, just return success to avoid errors
    return jsonify({'success': True, 'message': 'oj.uz sync not implemented yet'})

@app.route('/api/contest-scores', methods=["GET"])
@session_required
def get_contest_scores():
    contest_names = request.args.get('contests')
    if not contest_names:
        return jsonify({"error": "Missing 'contests' query parameter"}), 400

    # Parse contest names (format: "contest_name|contest_stage,contest_name2|contest_stage2")
    contest_list = []
    for contest in contest_names.split(','):
        if '|' in contest:
            name, stage = contest.strip().split('|', 1)
            contest_list.append((name, stage))
    
    if not contest_list:
        return jsonify({"error": "No valid contests provided"}), 400

    db = get_db()
    
    # Fetch contest scores for the requested contests
    placeholders = ', '.join(['(?, ?)'] * len(contest_list))
    flat_params = [item for pair in contest_list for item in pair]
    
    contest_scores = db.execute(f'''
        SELECT contest_name, contest_stage, medal_names, medal_cutoffs, problem_scores
        FROM contest_scores 
        WHERE (contest_name, contest_stage) IN ({placeholders})
    ''', flat_params).fetchall()
    
    # Convert to dictionary format
    scores_dict = {}
    for row in contest_scores:
        key = f"{row['contest_name']}|{row['contest_stage']}"
        scores_dict[key] = {
            'medal_names': json.loads(row['medal_names']) if row['medal_names'] else [],
            'medal_cutoffs': json.loads(row['medal_cutoffs']) if row['medal_cutoffs'] else [],
            'problem_scores': json.loads(row['problem_scores']) if row['problem_scores'] else []
        }
    
    return jsonify(scores_dict)

@app.route('/api/virtual-contests/detail/<slug>', methods=["GET"])
@session_required
def get_virtual_contest_detail(slug):
    user_id = request.user_id
    db = get_db()
    
    # Get all virtual contests for this user to find matching slug
    contests = db.execute('''
        SELECT 
            v.contest_name,
            v.contest_stage,
            c.source as contest_source,
            c.year as contest_year,
            c.location,
            c.website,
            v.started_at,
            v.ended_at,
            v.score as total_score,
            v.per_problem_scores,
            CASE 
                WHEN c.link LIKE '%oj.uz%' THEN 'oj.uz'
                ELSE 'manual'
            END as platform
        FROM user_virtual_contests v
        JOIN contests c ON v.contest_name = c.name AND v.contest_stage = c.stage
        WHERE v.user_id = ?
    ''', (user_id,)).fetchall()
    
    # Find contest with matching slug
    for contest in contests:
        contest_slug = (contest['contest_name'] + contest['contest_stage']).lower().replace(' ', '')
        if contest_slug == slug:
            return jsonify(dict(contest))
    
    return jsonify({'error': 'Contest not found'}), 404

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5001)
