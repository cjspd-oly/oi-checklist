import sqlite3
import os
from dotenv import load_dotenv
import json

load_dotenv()

backend_dir = os.getenv("BACKEND_DIR")
if not backend_dir:
    raise RuntimeError("BACKEND_DIR not set in environment variables")

with open(os.path.join(backend_dir, "data.json"), "r", encoding="utf-8") as f:
    problems = json.load(f)

db_path = os.getenv("DATABASE_PATH", "database.db")  # fallback to "database.db" if not set
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Clear existing problems
cur.execute("DELETE FROM problems")

for p in problems:
    cur.execute('''
        INSERT INTO problems (name, number, source, year, link)
        VALUES (?, ?, ?, ?, ?)
    ''', (p["name"], p["number"], p["source"], p["year"], p["link"]))

conn.commit()
conn.close()
