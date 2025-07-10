import re
import time
import random
import requests
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template, request, jsonify
import sqlite3
import hashlib
import os
import populate_problems
from dotenv import load_dotenv
from flask_cors import CORS
from datetime import timedelta, datetime
import jwt  # Import PyJWT
from functools import wraps
import json

load_dotenv()  # Load environment variables from .env

app = Flask(__name__)
# Allow cookies to be sent from frontend
app.config['SESSION_COOKIE_SAMESITE'] = 'None' if os.getenv("FLASK_ENV") == "production" else 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv("FLASK_ENV") == "production"
CORS(app, supports_credentials=True, origins=["http://localhost:5501", "https://avighnac.github.io"])
app.secret_key = "your-secret-key"
app.permanent_session_lifetime = timedelta(days=1)

# JWT Secret key
JWT_SECRET_KEY = "your-jwt-secret-key"  # Change this in production

def get_db():
    db_path = os.getenv("DATABASE_PATH", "database.db")  # fallback to "database.db" if not set
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# JWT token required decorator
def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Token is missing"}), 403

        try:
            token = token.split(" ")[1]  # Extract the token from "Bearer <token>"
            decoded_token = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            request.user_id = decoded_token["user_id"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)

    return decorated_function

# @app.before_request
# def simulate_network_lag():
#     time.sleep(0.2)

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
        # Generate JWT token
        token = jwt.encode(
            {"user_id": user["id"], "exp": datetime.utcnow() + timedelta(days=1)}, 
            JWT_SECRET_KEY, 
            algorithm="HS256"
        )
        return jsonify({"success": True, "token": token})
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route('/api/whoami', methods=["GET"])
@token_required
def whoami():
    db = get_db()
    user = db.execute("SELECT username FROM users WHERE id=?", (request.user_id,)).fetchone()
    
    if user:
        return jsonify({'username': user['username']})
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/settings', methods=["GET"])
@token_required
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
@token_required
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
@token_required
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
        f'SELECT * FROM problems WHERE source IN ({placeholders}) ORDER BY source, year, number',
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
            f'SELECT * FROM problems WHERE source IN ({placeholders}) ORDER BY source, year, number',
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
@token_required
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
@token_required
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
@token_required
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
@token_required
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
        f"SELECT name, link, source, year FROM problems WHERE source IN ({placeholders})",
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
@token_required
def update_olympiad_order():
    data = request.get_json()
    user_id = request.user_id

    olympiad_order = data.get('olympiad_order')
    if not isinstance(olympiad_order, list):
        return jsonify({"error": "Invalid or missing olympiad_order"}), 400

    db = get_db()
    db.execute(
        '''
        UPDATE user_settings
        SET olympiad_order = ?
        WHERE user_id = ?
        ''',
        (json.dumps(olympiad_order), user_id)
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
    print(f"user id: {user_id}")

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
def api_logout():
    return jsonify({"success": True, "message": "JWTs are stateless, no need to logout explicitly."})

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5001)