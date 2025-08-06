import sqlite3
import os
from dotenv import load_dotenv
import subprocess
import json
from collections import defaultdict

load_dotenv()

backend_dir = os.getenv("BACKEND_DIR")
if not backend_dir:
    raise RuntimeError("BACKEND_DIR not set in environment variables")

yaml_to_json_script = os.path.join(backend_dir, "data", "yaml_to_json.py")
json_output_path = os.path.join(backend_dir, "data.json")

subprocess.run(["python3", yaml_to_json_script, os.path.join(backend_dir, "data"), "--output", json_output_path], check=True)

with open(json_output_path, "r", encoding="utf-8") as f:
    problems = json.load(f)

yaml_files_by_dir = defaultdict(set)

db_path = os.getenv("DATABASE_PATH", "database.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("DELETE FROM problems")

for p in problems:
    extra = p.get("extra", "")
    rel_path = os.path.join("data", p["source"].lower(), str(p["year"]), f"{extra.replace(' ', '_')}.yaml") if extra else os.path.join("data", p["source"].lower(), f"{p['year']}.yaml")
    yaml_files_by_dir[os.path.dirname(rel_path)].add(os.path.basename(rel_path))

    try:
        if 'number' in p:
            cur.execute(
                '''
                INSERT INTO problems (name, number, source, year, link, extra)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (p["name"], p["number"], p["source"], p["year"], p["link"], extra)
            )
        else:
            cur.execute(
                '''
                INSERT INTO problems (name, source, year, link, extra)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (p["name"], p["source"], p["year"], p["link"], extra)
            )
    except sqlite3.IntegrityError as e:
        print("Error inserting problem:", p)
        raise

conn.commit()
conn.close()

print("Processed YAML structure:")
for directory in sorted(yaml_files_by_dir):
    print(f"📂 {directory}/")
    files = sorted(yaml_files_by_dir[directory])
    display = files if len(files) <= 3 else [files[0], "...", files[-1]]
    for i, file in enumerate(display):
        prefix = "└── " if i == len(display) - 1 else "├── "
        print(f"    {prefix}{file}")

try:
    os.remove(json_output_path)
    print(f"Deleted temporary file: {json_output_path}")
except OSError as e:
    print(f"Warning: could not delete {json_output_path}: {e}")
