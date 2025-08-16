import os
import sys
import json
import sqlite3
import subprocess
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

backend_dir_env = os.getenv("BACKEND_DIR")
if not backend_dir_env:
    raise RuntimeError("BACKEND_DIR not set in environment variables")

BACKEND_DIR = Path(backend_dir_env).resolve()

DATA_DIR = BACKEND_DIR / "data" / "problems"
YAML_TO_JSON = DATA_DIR / "yaml_to_json.py"

if not YAML_TO_JSON.is_file():
    raise FileNotFoundError(f"yaml_to_json.py not found at: {YAML_TO_JSON}")

JSON_OUT = BACKEND_DIR / "problems.tmp.json"

subprocess.run(
    [sys.executable, str(YAML_TO_JSON), str(DATA_DIR), "--output", str(JSON_OUT)],
    check=True,
)

with JSON_OUT.open("r", encoding="utf-8") as f:
    problems = json.load(f)

yaml_files_by_dir = defaultdict(set)

db_path = os.getenv("DATABASE_PATH", str(BACKEND_DIR / "database.db"))
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("DELETE FROM problems")

for p in problems:
    extra = p.get("extra", "")
    if extra:
        rel_path = Path("data") / "problems" / p["source"].lower() / str(p["year"]) / f"{extra.replace(' ', '_')}.yaml"
    else:
        rel_path = Path("data") / "problems" / p["source"].lower() / f"{p['year']}.yaml"

    yaml_files_by_dir[str(rel_path.parent)].add(rel_path.name)

    try:
        if "number" in p:
            cur.execute(
                """
                INSERT INTO problems (name, number, source, year, link, extra)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (p["name"], p["number"], p["source"], p["year"], p["link"], extra),
            )
        else:
            cur.execute(
                """
                INSERT INTO problems (name, source, year, link, extra)
                VALUES (?, ?, ?, ?, ?)
                """,
                (p["name"], p["source"], p["year"], p["link"], extra),
            )
    except sqlite3.IntegrityError:
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
    JSON_OUT.unlink()
    print(f"Deleted temporary file: {JSON_OUT}")
except OSError as e:
    print(f"Warning: could not delete {JSON_OUT}: {e}")
