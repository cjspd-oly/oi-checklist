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
from bs4 import BeautifulSoup

# this is probably really bad but the website doesn't work without it
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

load_dotenv()  # Load environment variables from .env

app = Flask(__name__)
# Allow cookies to be sent from frontend
app.config['SESSION_COOKIE_SAMESITE'] = 'None' if os.getenv("FLASK_ENV") == "production" else 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv("FLASK_ENV") == "production"
CORS(app, supports_credentials=True, origins=[os.getenv("FRONTEND_URL")])

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

def sync_ojuz_submissions(active_contest, ojuz_username):
    """
    Utility function to sync oj.uz submissions for a virtual contest.
    
    Args:
        active_contest: The active contest object with user_id, contest_name, contest_stage, start_time, end_time
        ojuz_username: The user's oj.uz username
        
    Returns:
        List of submission data dictionaries
    """
    db = get_db()
    
    user_id = active_contest['user_id']
    contest_name = active_contest['contest_name']
    contest_stage = active_contest['contest_stage']
    contest_start_time = active_contest['start_time']
    contest_end_time = active_contest['end_time']
    
    # Convert times to datetime objects for comparison
    start_dt = datetime.fromisoformat(contest_start_time.replace('Z', '+00:00'))
    end_dt = datetime.fromisoformat(contest_end_time.replace('Z', '+00:00'))
    
    # Get contest problems and their oj.uz links
    if contest_stage is not None:
        contest_problems = db.execute('''
            SELECT 
                cp.problem_index,
                p.name as problem_name,
                p.link as problem_link
            FROM contest_problems cp
            JOIN problems p ON cp.problem_source = p.source 
                            AND cp.problem_year = p.year 
                            AND cp.problem_number = p.number
            WHERE cp.contest_name = ? AND cp.contest_stage = ?
            AND p.link LIKE 'https://oj.uz/%'
            ORDER BY cp.problem_index
        ''', (contest_name, contest_stage)).fetchall()
    else:
        contest_problems = db.execute('''
            SELECT 
                cp.problem_index,
                p.name as problem_name,
                p.link as problem_link
            FROM contest_problems cp
            JOIN problems p ON cp.problem_source = p.source 
                            AND cp.problem_year = p.year 
                            AND cp.problem_number = p.number
            WHERE cp.contest_name = ? AND cp.contest_stage IS NULL
            AND p.link LIKE 'https://oj.uz/%'
            ORDER BY cp.problem_index
        ''', (contest_name,)).fetchall()
    
    print(f"Found {len(contest_problems)} oj.uz problems for contest {contest_name}, stage: {contest_stage}")
    for row in contest_problems:
        print(dict(row))
    
    if not contest_problems:
        return []
    
    # Create mapping of problem links to problem info
    problem_link_map = {
        problem['problem_link']: {
            'index': problem['problem_index'],
            'name': problem['problem_name']
        }
        for problem in contest_problems
    }
    
    # Headers for requests
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    print(f"Starting oj.uz sync for user {ojuz_username}, contest {contest_name} {contest_stage}")
    print(f"Contest time range: {contest_start_time} to {contest_end_time}")
    
    # Step 1: Get all relevant submissions from the submissions page(s)
    relevant_submissions = []
    submissions_url = f"https://oj.uz/submissions?handle={ojuz_username}"
    
    while submissions_url:
        print(f"Fetching submissions page: {submissions_url}")
        
        try:
            response = requests.get(submissions_url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"Failed to fetch submissions page: {response.status_code}")
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all submission rows in the table
            submission_rows = soup.select('table.table tbody tr')
            if not submission_rows:
                print("No submission rows found, breaking")
                break
            
            last_submission_id = None
            found_relevant = False
            
            for row in submission_rows:
                try:
                    # Extract submission time
                    time_span = row.find('span', {'data-timestamp-iso': True})
                    if not time_span:
                        continue
                    
                    submission_time_str = time_span['data-timestamp-iso']
                    submission_dt = datetime.fromisoformat(submission_time_str.replace('Z', '+00:00'))
                    
                    # Check if submission is within contest time range
                    if submission_dt < start_dt:
                        # We've gone past the contest start time, stop pagination
                        print(f"Reached submission before contest start time: {submission_time_str}")
                        submissions_url = None
                        break
                    
                    if submission_dt > end_dt:
                        # Submission is after contest end, skip
                        continue
                    
                    # Extract submission ID
                    submission_link = row.find('a', href=re.compile(r'/submission/\d+'))
                    if not submission_link:
                        continue
                    
                    submission_id = submission_link['href'].split('/')[-1]
                    last_submission_id = submission_id
                    
                    # Extract problem link
                    problem_link_elem = row.find('a', href=re.compile(r'/problem/view/'))
                    if not problem_link_elem:
                        continue
                    
                    problem_link = 'https://oj.uz' + problem_link_elem['href']
                    
                    # Check if this problem is part of our contest
                    if problem_link in problem_link_map:
                        print(f"Found relevant submission {submission_id} for {problem_link} at {submission_time_str}")
                        relevant_submissions.append({
                            'submission_id': submission_id,
                            'submission_time': submission_time_str,
                            'problem_link': problem_link,
                            'problem_index': problem_link_map[problem_link]['index'],
                            'problem_name': problem_link_map[problem_link]['name']
                        })
                        found_relevant = True
                
                except Exception as e:
                    print(f"Error processing submission row: {e}")
                    continue
            
            # Prepare next page URL if we need to continue
            if submissions_url and last_submission_id and not found_relevant:
                # If we didn't find any relevant submissions on this page, continue to next
                submissions_url = f"https://oj.uz/submissions?handle={ojuz_username}&direction=down&id={last_submission_id}"
            elif submissions_url and last_submission_id and found_relevant:
                # We found some, but might need more from earlier pages
                submissions_url = f"https://oj.uz/submissions?handle={ojuz_username}&direction=down&id={last_submission_id}"
            else:
                submissions_url = None
                
            time.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            print(f"Error fetching submissions page: {e}")
            break
    
    print(f"Found {len(relevant_submissions)} relevant submissions")
    
    # Step 2: Fetch detailed scores for each submission (only if submissions exist)
    detailed_submissions = []
    if relevant_submissions:
        def fetch_submission_details(submission_info):
            try:
                submission_url = f"https://oj.uz/submission/{submission_info['submission_id']}"
                print(f"Fetching submission details: {submission_url}")
                
                response = requests.get(submission_url, headers=headers, timeout=10)
                if response.status_code != 200:
                    print(f"Failed to fetch submission {submission_info['submission_id']}")
                    return None
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract subtask scores
                subtask_scores = []
                total_score = 0
                
                # Find all subtask panels
                subtask_divs = soup.find_all('div', id=re.compile(r'subtask_results_div_\d+'))
                
                for subtask_div in subtask_divs:
                    try:
                        # Find the subtask score span
                        score_span = subtask_div.find('span', class_=re.compile(r'subtask-score'))
                        if score_span:
                            # Extract score text like "17 / 17" or "0 / 6" or "39.61 / 100"
                            score_text = score_span.get_text().strip()
                            score_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*/\s*([0-9]+(?:\.[0-9]+)?)', score_text)
                            if score_match:
                                earned = float(score_match.group(1))
                                max_points = float(score_match.group(2))
                                # Round to 2 decimal places and convert to int if it's a whole number
                                earned_rounded = round(earned, 2)
                                if earned_rounded == int(earned_rounded):
                                    earned_rounded = int(earned_rounded)
                                total_score += earned_rounded
                                subtask_scores.append(earned_rounded)
                            else:
                                subtask_scores.append(0)
                        else:
                            subtask_scores.append(0)
                    except Exception as e:
                        print(f"Error parsing subtask in submission {submission_info['submission_id']}: {e}")
                        subtask_scores.append(0)
                
                return {
                    'submission_id': submission_info['submission_id'],
                    'submission_time': submission_info['submission_time'],
                    'problem_index': submission_info['problem_index'],
                    'problem_name': submission_info['problem_name'],
                    'problem_link': submission_info['problem_link'],
                    'total_score': total_score,
                    'subtask_scores': subtask_scores
                }
                
            except Exception as e:
                print(f"Error fetching submission {submission_info['submission_id']}: {e}")
                return None
        
        # Fetch all submission details in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = executor.map(fetch_submission_details, relevant_submissions)
            for result in results:
                if result:
                    detailed_submissions.append(result)
                time.sleep(0.2)  # Rate limiting between requests
    
    print(f"Successfully fetched details for {len(detailed_submissions)} submissions")
    
    # Step 3: Calculate best scores per problem and save to database
    problem_best_scores = {}  # problem_index -> {'total_score': X, 'subtask_scores': [], 'earliest_improvement_time': str}
    
    for submission in detailed_submissions:
        problem_idx = submission['problem_index']
        
        if problem_idx not in problem_best_scores:
            problem_best_scores[problem_idx] = {
                'total_score': submission['total_score'],
                'subtask_scores': submission['subtask_scores'][:],
                'earliest_improvement_time': submission['submission_time']
            }
        else:
            # Update with maximum scores per subtask
            current_best = problem_best_scores[problem_idx]
            new_subtask_scores = []
            improved = False
            
            max_len = max(len(current_best['subtask_scores']), len(submission['subtask_scores']))
            for i in range(max_len):
                current_score = current_best['subtask_scores'][i] if i < len(current_best['subtask_scores']) else 0
                new_score = submission['subtask_scores'][i] if i < len(submission['subtask_scores']) else 0
                max_score = max(current_score, new_score)
                new_subtask_scores.append(max_score)
                
                # Check if this submission improved any subtask
                if new_score > current_score:
                    improved = True
            
            new_total_score = sum(new_subtask_scores)
            
            # If this submission improved the total score, update the earliest improvement time
            if new_total_score > current_best['total_score']:
                # Parse submission times to compare which is earlier
                current_time = datetime.fromisoformat(current_best['earliest_improvement_time'].replace('Z', '+00:00'))
                submission_time = datetime.fromisoformat(submission['submission_time'].replace('Z', '+00:00'))
                earliest_time = min(current_time, submission_time).isoformat().replace('+00:00', 'Z')
                
                problem_best_scores[problem_idx] = {
                    'total_score': new_total_score,
                    'subtask_scores': new_subtask_scores,
                    'earliest_improvement_time': earliest_time
                }
            elif improved:
                # Even if total didn't improve, if any subtask improved, consider updating time if this is earlier
                submission_time = datetime.fromisoformat(submission['submission_time'].replace('Z', '+00:00'))
                current_time = datetime.fromisoformat(current_best['earliest_improvement_time'].replace('Z', '+00:00'))
                
                if submission_time < current_time:
                    problem_best_scores[problem_idx]['earliest_improvement_time'] = submission['submission_time']
                
                # Update subtask scores even if total didn't improve
                problem_best_scores[problem_idx]['subtask_scores'] = new_subtask_scores
        
        # Save individual submission to database
        db.execute('''
            INSERT OR REPLACE INTO user_virtual_submissions 
            (user_id, contest_name, contest_stage, submission_time, problem_index, score, subtask_scores)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, contest_name, contest_stage,
            submission['submission_time'],
            submission['problem_index'],
            submission['total_score'],
            json.dumps(submission['subtask_scores'])
        ))
    
    db.commit()
    
    # Prepare return data with final scores
    submissions_summary = []
    
    # Ensure all contest problems are represented, even if not attempted
    for problem in contest_problems:
        problem_idx = problem['problem_index']
        
        if problem_idx in problem_best_scores:
            # Problem was attempted
            best_scores = problem_best_scores[problem_idx]
            submissions_summary.append({
                'problem_index': problem_idx,
                'problem_name': problem['problem_name'],
                'problem_link': problem['problem_link'],
                'score': best_scores['total_score'],
                'subtask_scores': best_scores['subtask_scores'],
                'submission_time': best_scores['earliest_improvement_time']
            })
        else:
            # Problem was not attempted - default to 0 score
            submissions_summary.append({
                'problem_index': problem_idx,
                'problem_name': problem['problem_name'],
                'problem_link': problem['problem_link'],
                'score': 0,
                'subtask_scores': [],
                'submission_time': None
            })
    
    # Sort by problem index to ensure correct order
    submissions_summary.sort(key=lambda x: x['problem_index'])
    
    print(f"Final scores calculated for {len(submissions_summary)} problems")
    
    return submissions_summary

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
    username_row = db.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    if username_row and username_row["username"] == "demo-user":
        return jsonify({"error": "Demo user cannot link GitHub accounts."}), 403

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
    user = db.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, password)
    ).fetchone()
    if user:
        session_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO sessions (session_id, user_id) VALUES (?, ?)",
            (session_id, user["id"])
        )
        # Fetch stored localStorage (if any)
        local_storage_row = db.execute(
            "SELECT local_storage FROM user_settings WHERE user_id = ?",
            (user["id"],)
        ).fetchone()
        local_storage_data = None if local_storage_row is None else local_storage_row["local_storage"]
        db.commit()
        return jsonify({
            "success": True,
            "token": session_id,
            "local_storage": local_storage_data
        })
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
        'NOIPRELIM', 'NOIQUAL', 'NOIFINAL', 'POI', 'NOISEL', 'CEOI', 'COI', 'BOI', 'JOIOC'
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

@app.route('/api/logout', methods=["POST"])
@session_required
def api_logout():
    session_id = request.headers.get("Authorization").split(" ")[1]

    # Don't delete the fixed demo session
    if session_id == "demo-session-fixed-token-123456789":
        return jsonify({"success": True, "message": "Demo session preserved."})

    data = request.get_json(silent=True) or {}
    local_storage_data = data.get("local_storage")

    db = get_db()

    # Store localStorage in user_settings before logout
    if local_storage_data is not None:
        db.execute(
            "UPDATE user_settings SET local_storage = ? WHERE user_id = ?",
            (local_storage_data, request.user_id)
        )

    # Delete session
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
            avc.ojuz_synced,
            c.duration_minutes,
            c.location,
            c.website,
            c.link
        FROM active_virtual_contests avc
        JOIN contests c ON avc.contest_name = c.name AND (avc.contest_stage = c.stage OR (avc.contest_stage IS NULL AND c.stage IS NULL))
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
        JOIN contests c ON v.contest_name = c.name AND (v.contest_stage = c.stage OR (v.contest_stage IS NULL AND c.stage IS NULL))
        WHERE v.user_id = ?
        ORDER BY v.started_at DESC
        LIMIT 3
    ''', (user_id,)).fetchall()

    # Get all completed contests for this user
    completed_contests = db.execute('''
        SELECT DISTINCT contest_name || '|' || COALESCE(contest_stage, '') as contest_key
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
            if cp['contest_name'] == c['name'] and (cp['contest_stage'] == c['stage'] or (cp['contest_stage'] is None and c['stage'] is None)):
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
        JOIN contests c ON v.contest_name = c.name AND (v.contest_stage = c.stage OR (v.contest_stage IS NULL AND c.stage IS NULL))
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
    contest_stage = data.get('contest_stage')  # This can be None/null now
    
    if not contest_name:
        return jsonify({'error': 'Missing contest_name'}), 400
    
    db = get_db()
    
    # Check if user already has an active contest
    existing = db.execute(
        'SELECT 1 FROM active_virtual_contests WHERE user_id = ?',
        (user_id,)
    ).fetchone()
    
    if existing:
        return jsonify({'error': 'User already has an active contest'}), 400
    
    # Check if user has already completed this contest
    # Handle both NULL and non-NULL contest_stage cases
    if contest_stage is not None:
        completed = db.execute(
            'SELECT 1 FROM user_virtual_contests WHERE user_id = ? AND contest_name = ? AND contest_stage = ?',
            (user_id, contest_name, contest_stage)
        ).fetchone()
    else:
        completed = db.execute(
            'SELECT 1 FROM user_virtual_contests WHERE user_id = ? AND contest_name = ? AND contest_stage IS NULL',
            (user_id, contest_name)
        ).fetchone()
    
    if completed:
        return jsonify({'error': 'Contest already completed'}), 400
    
    # Verify contest exists
    # Handle both NULL and non-NULL contest_stage cases
    if contest_stage is not None:
        contest_exists = db.execute(
            'SELECT 1 FROM contests WHERE name = ? AND stage = ?',
            (contest_name, contest_stage)
        ).fetchone()
    else:
        contest_exists = db.execute(
            'SELECT 1 FROM contests WHERE name = ? AND stage IS NULL',
            (contest_name,)
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
    
    # Get the active contest with duration info
    active_contest = db.execute('''
        SELECT 
            avc.contest_name, 
            avc.contest_stage, 
            avc.start_time,
            c.duration_minutes
        FROM active_virtual_contests avc
        JOIN contests c ON avc.contest_name = c.name AND (avc.contest_stage = c.stage OR (avc.contest_stage IS NULL AND c.stage IS NULL))
        WHERE avc.user_id = ?
    ''', (user_id,)).fetchone()
    
    if not active_contest:
        return jsonify({'error': 'No active contest found'}), 404
    
    # Calculate the end time, capped at contest duration
    start_time = datetime.fromisoformat(active_contest['start_time'].replace('Z', '+00:00'))
    duration_minutes = active_contest['duration_minutes']
    utc_now = datetime.now(pytz.UTC)
    
    # Calculate maximum allowed end time based on contest duration
    max_end_time = start_time + timedelta(minutes=duration_minutes)
    
    # Cap the end time at the maximum allowed time
    capped_end_time = min(utc_now, max_end_time)
    capped_end_time_iso = capped_end_time.isoformat()
    
    # Update the active contest with capped end_time
    db.execute('''
        UPDATE active_virtual_contests 
        SET end_time = ?
        WHERE user_id = ?
    ''', (capped_end_time_iso, user_id))
    db.commit()
    
    # Create updated active_contest object with capped end_time for sync function
    active_contest_with_end = {
        'user_id': user_id,
        'contest_name': active_contest['contest_name'],
        'contest_stage': active_contest['contest_stage'],
        'start_time': active_contest['start_time'],
        'end_time': capped_end_time_iso
    }
    
    # Handle oj.uz sync if username provided (after contest is officially ended)
    submissions = []
    final_scores = []
    if ojuz_username:
        try:
            submissions = sync_ojuz_submissions(active_contest_with_end, ojuz_username)
            # Extract just the scores for the final scores array
            final_scores = [sub['score'] for sub in sorted(submissions, key=lambda x: x['problem_index'])]
            total_score = sum(final_scores)
            
            # Mark this contest as oj.uz synced and save scores to prevent manual score manipulation
            if submissions is not None:
                db.execute('''
                    UPDATE active_virtual_contests 
                    SET ojuz_synced = 1, score = ?, per_problem_scores = ?
                    WHERE user_id = ?
                ''', (total_score, json.dumps(final_scores), user_id))
                db.commit()
        except Exception as e:
            print(f"Error syncing oj.uz submissions: {e}")
            # Continue anyway - contest is already ended
    
    response_data = {'success': True}
    if ojuz_username and submissions is not None:  # Return if oj.uz sync was attempted and succeeded
        response_data['submissions'] = submissions
        response_data['final_scores'] = final_scores
    
    return jsonify(response_data)

@app.route('/api/virtual-contests/confirm', methods=["POST"])
@session_required
def confirm_virtual_contest():
    """
    Confirm and finalize an oj.uz synced virtual contest.
    This moves the contest from active_virtual_contests to user_virtual_contests
    and updates the user's problem scores in the database.
    """
    user_id = request.user_id
    db = get_db()
    
    # Get the ended active contest with oj.uz sync
    active_contest = db.execute('''
        SELECT contest_name, contest_stage, start_time, end_time, score, per_problem_scores, ojuz_synced
        FROM active_virtual_contests 
        WHERE user_id = ? AND end_time IS NOT NULL AND ojuz_synced = 1
    ''', (user_id,)).fetchone()
    
    if not active_contest:
        return jsonify({'error': 'No oj.uz synced contest found to confirm'}), 404
    
    contest_name = active_contest['contest_name']
    contest_stage = active_contest['contest_stage']
    start_time = active_contest['start_time']
    end_time = active_contest['end_time']
    total_score = active_contest['score']
    per_problem_scores = active_contest['per_problem_scores']
    
    # Get contest problems to update user's problem scores
    contest_problems = db.execute('''
        SELECT 
            cp.problem_index,
            p.name as problem_name,
            p.source,
            p.year
        FROM contest_problems cp
        JOIN problems p ON cp.problem_source = p.source 
                        AND cp.problem_year = p.year 
                        AND cp.problem_number = p.number
        WHERE cp.contest_name = ? AND (cp.contest_stage = ? OR (cp.contest_stage IS NULL AND ? IS NULL))
        ORDER BY cp.problem_index
    ''', (contest_name, contest_stage, contest_stage)).fetchall()
    
    # Parse the per-problem scores from JSON
    try:
        scores_list = json.loads(per_problem_scores) if per_problem_scores else []
    except:
        scores_list = []
    
    # Update user's problem scores in the database
    for i, problem in enumerate(contest_problems):
        if i < len(scores_list):
            score = scores_list[i]
            
            # Determine status based on score
            if score == 100:
                status = 2  # solved
            elif score > 0:
                status = 1  # partial
            else:
                status = 0  # failed
            
            # Update or insert the problem status and score
            db.execute('''
                INSERT INTO problem_statuses (user_id, problem_name, source, year, status, score)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, problem_name, source, year)
                DO UPDATE SET 
                    status = CASE WHEN excluded.score > problem_statuses.score THEN excluded.status ELSE problem_statuses.status END,
                    score = MAX(excluded.score, problem_statuses.score)
            ''', (user_id, problem['problem_name'], problem['source'], problem['year'], status, score))
    
    # Move the contest to completed virtual contests
    db.execute('''
        INSERT OR REPLACE INTO user_virtual_contests 
        (user_id, contest_name, contest_stage, started_at, ended_at, score, per_problem_scores)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, contest_name, contest_stage, start_time, end_time, total_score, per_problem_scores))
    
    # Remove from active contests
    db.execute('DELETE FROM active_virtual_contests WHERE user_id = ?', (user_id,))
    
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
        SELECT contest_name, contest_stage, start_time, end_time, ojuz_synced
        FROM active_virtual_contests 
        WHERE user_id = ? AND end_time IS NOT NULL
    ''', (user_id,)).fetchone()
    
    if not active_contest:
        return jsonify({'error': 'No ended contest found'}), 404
    
    # Security check: Prevent manual score submission for oj.uz synced contests
    if active_contest['ojuz_synced']:
        return jsonify({'error': 'Cannot manually modify scores for oj.uz synced contests!'}), 403
    
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

    contest_list = []
    for contest in contest_names.split(','):
        if '|' in contest:
            name, stage = contest.strip().split('|', 1)
            # Handle empty stage (convert to None for NULL matching)
            stage = stage.strip() if stage.strip() else None
            contest_list.append((name.strip(), stage))
        else:
            # No stage separator, assume no stage (NULL)
            contest_list.append((contest.strip(), None))

    if not contest_list:
        return jsonify({"error": "No valid contests provided"}), 400

    db = get_db()
    
    # Build dynamic query to handle NULL stages properly
    where_conditions = []
    params = []
    
    for name, stage in contest_list:
        if stage is None:
            where_conditions.append("(contest_name = ? AND contest_stage IS NULL)")
            params.append(name)
        else:
            where_conditions.append("(contest_name = ? AND contest_stage = ?)")
            params.extend([name, stage])
    
    where_clause = " OR ".join(where_conditions)
    
    contest_scores = db.execute(f'''
        SELECT contest_name, contest_stage, medal_names, medal_cutoffs, problem_scores
        FROM contest_scores 
        WHERE {where_clause}
    ''', params).fetchall()
    
    # Convert to dictionary format
    scores_dict = {}
    for row in contest_scores:
        key = f"{row['contest_name']}|{row['contest_stage'] or ''}"
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
        JOIN contests c ON v.contest_name = c.name AND (v.contest_stage = c.stage OR (v.contest_stage IS NULL AND c.stage IS NULL))
        WHERE v.user_id = ?
    ''', (user_id,)).fetchall()
    
    # Find contest with matching slug
    for contest in contests:
        contest_slug = (contest['contest_name'] + (contest['contest_stage'] or '')).lower().replace(' ', '')
        if contest_slug == slug:
            return jsonify(dict(contest))
    
    return jsonify({'error': 'Contest not found'}), 404

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
