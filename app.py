from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
import hashlib

app = Flask(__name__)
app.secret_key = "your-secret-key"

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    if "user_id" in session:
        return redirect("/dashboard")
    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = hashlib.sha256(request.form["password"].encode()).hexdigest()
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            db.commit()
        except:
            return "Username taken"
        return redirect("/login")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = hashlib.sha256(request.form["password"].encode()).hexdigest()
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()
        if user:
            session["user_id"] = user["id"]
            return redirect("/dashboard")
        return "Invalid credentials"
    return render_template("login.html")

@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    db = sqlite3.connect('database.db')
    db.row_factory = sqlite3.Row

    # Fetch all problems
    problems_raw = db.execute(
        'SELECT * FROM problems ORDER BY year, number'
    ).fetchall()

    # Fetch user progress
    progress_rows = db.execute(
        'SELECT problem_name, status FROM problem_statuses WHERE user_id = ?',
        (user_id,)
    ).fetchall()
    progress = {row['problem_name']: row['status'] for row in progress_rows}

    # Group by category -> year -> problems
    problems_by_category = {}
    for row in problems_raw:
        category = row['source']
        year = row['year']
        problem = dict(row)
        problem['status'] = progress.get(problem['name'], 0)

        problems_by_category.setdefault(category, {})
        problems_by_category[category].setdefault(year, [])
        problems_by_category[category][year].append(problem)

    return render_template('dashboard.html', problems_by_category=problems_by_category)

@app.route('/api/update-problem-status', methods=['POST'])
def update_problem_status():
    data = request.get_json()
    user_id = session.get('user_id')
    problem_name = data['problem_name']
    status = data['status']

    db = sqlite3.connect('database.db')
    db.execute(
        '''
        INSERT INTO problem_statuses (user_id, problem_name, status)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, problem_name) DO UPDATE SET status = ?
        ''',
        (user_id, problem_name, status, status)
    )
    db.commit()
    return jsonify(success=True)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
