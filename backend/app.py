from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
import hashlib
import os
import populate_problems
from dotenv import load_dotenv
from flask_cors import CORS


load_dotenv()  # Load environment variables from .env

app = Flask(__name__)
# Allow cookies to be sent from frontend
CORS(app, supports_credentials=True, origins=["http://127.0.0.1:5501"])
app.secret_key = "your-secret-key"

def get_db():
    db_path = os.getenv("DATABASE_PATH", "database.db")  # fallback to "database.db" if not set
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

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
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route('/api/whoami')
def get():
    if not session.get('user_id'):
        return jsonify({'error': 'Not logged in'}), 401
    return jsonify({'username': session['username']})

@app.route('/api/problems')
def get_problems():
    from_names = request.args.get('names')
    if not from_names:
        return jsonify({"error": "Missing 'names' query parameter"}), 400

    # Split the names by comma and strip any leading/trailing whitespace
    from_names = [name.strip() for name in from_names.split(',')]

    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

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

@app.route('/api/update-problem-status', methods=['POST'])
def update_problem_status():
    data = request.get_json()
    user_id = session.get('user_id')
    problem_name = data['problem_name']
    source = data['source']
    year = data['year']
    status = data['status']

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
def update_problem_score():
    data = request.get_json()
    user_id = session.get('user_id')
    problem_name = data['problem_name']
    source = data['source']
    year = data['year']
    score = data['score']

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


@app.route('/api/logout', methods=["POST"])
def api_logout():
    session.clear()  # Clears all session data
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True)
