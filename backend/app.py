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

load_dotenv()  # Load environment variables from .env

app = Flask(__name__)
# Allow cookies to be sent from frontend
app.config['SESSION_COOKIE_SAMESITE'] = 'None' if os.getenv("FLASK_ENV") == "production" else 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv("FLASK_ENV") == "production"
CORS(app, supports_credentials=True, origins=["http://127.0.0.1:5500", "https://avighnac.github.io"])
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

@app.route('/api/logout', methods=["POST"])
def api_logout():
    return jsonify({"success": True, "message": "JWTs are stateless, no need to logout explicitly."})

if __name__ == "__main__":
    app.run(debug=True)