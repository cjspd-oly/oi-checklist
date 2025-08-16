from functools import wraps
from flask import request, jsonify
from database.db import get_db

def session_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return jsonify({"error": "Token is missing"}), 403
        session_id = auth.split(" ", 1)[1]
        with get_db() as db:
            row = db.execute(
                "SELECT user_id FROM sessions WHERE session_id = ?",
                (session_id,)
            ).fetchone()
        if not row:
            return jsonify({"error": "Invalid or expired session"}), 401
        request.user_id = row["user_id"]
        return f(*args, **kwargs)
    return decorated_function
