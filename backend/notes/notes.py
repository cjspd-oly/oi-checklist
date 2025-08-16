from flask import request, jsonify
from database.db import get_db

def get_note():
    name = request.args.get('problem_name')
    source = request.args.get('source')
    year = request.args.get('year', type=int)
    if not name or not source or year is None:
        return jsonify({"error": "Missing required parameters"}), 400

    with get_db() as db:
        row = db.execute(
            '''
            SELECT note FROM user_problem_notes
            WHERE user_id = ? AND problem_name = ? AND source = ? AND year = ?
            ''',
            (request.user_id, name, source, year)
        ).fetchone()

    return jsonify({"note": (row['note'] if row else '')}), 200

def save_note():
    data = request.get_json(silent=True) or {}
    name = data.get('problem_name')
    source = data.get('source')
    year = data.get('year')
    note = data.get('note', '')
    if not name or not source or year is None:
        return jsonify({"error": "Missing required fields"}), 400
    try:
        year_int = int(year)
    except Exception:
        return jsonify({"error": "Invalid year"}), 400

    with get_db() as db:
        db.execute(
            '''
            INSERT INTO user_problem_notes (user_id, problem_name, source, year, note, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, problem_name, source, year)
            DO UPDATE SET note = excluded.note, updated_at = CURRENT_TIMESTAMP
            ''',
            (request.user_id, name, source, year_int, note)
        )
        db.commit()

    return jsonify({"success": True})