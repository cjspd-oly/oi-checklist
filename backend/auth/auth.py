import hashlib
from flask import request, jsonify
import uuid
from database.db import get_db

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

def whoami():
    db = get_db()
    user = db.execute("SELECT username FROM users WHERE id=?", (request.user_id,)).fetchone()
    if user:
        return jsonify({'username': user['username']})
    return jsonify({'error': 'User not found'}), 404

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