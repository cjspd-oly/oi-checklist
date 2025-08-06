import sqlite3
import os
from dotenv import load_dotenv
import subprocess
import json
from collections import defaultdict
from pathlib import Path

load_dotenv()

backend_dir = os.getenv("BACKEND_DIR")
if not backend_dir:
    raise RuntimeError("BACKEND_DIR not set in environment variables")

compile_to_json_script = os.path.join(backend_dir, "contests", "compile_to_json.py")
json_output_path = os.path.join(backend_dir, "contests", "data.json")
contests_dir = os.path.join(backend_dir, "contests")

# Run compile_to_json.py
subprocess.run(["python3", compile_to_json_script, contests_dir, "--output", json_output_path], check=True)

with open(json_output_path, "r", encoding="utf-8") as f:
    contests = json.load(f)

yaml_files_by_dir = defaultdict(set)

db_path = os.getenv("DATABASE_PATH", "database.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Clear existing data
cur.execute("DELETE FROM contest_problems")
cur.execute("DELETE FROM contests")
cur.execute("DELETE FROM contest_scores")

for contest in contests:
    name = contest["name"]
    stage = contest["stage"]
    source = contest["source"]
    year = contest["year"]

    cur.execute('''
        INSERT INTO contests (
            name, stage, location, duration_minutes, source, year,
            date, website, link, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        name,
        stage,
        contest.get("location"),
        contest.get("duration_minutes"),
        source,
        year,
        contest.get("date"),
        contest.get("website"),
        contest.get("link"),
        contest.get("notes"),
    ))

    for i, p in enumerate(contest["problems"]):
        cur.execute('''
            INSERT INTO contest_problems (
                contest_name, contest_stage,
                problem_source, problem_year, problem_number,
                problem_index
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            name,
            stage,
            p["source"],
            p["year"],
            p["number"],
            i + 1
        ))

    # YAML path
    rel_path = os.path.join(
        "contests",
        source.lower(),
        str(year),
        f"{stage.replace(' ', '_')}.yaml"
    )
    yaml_files_by_dir[os.path.dirname(rel_path)].add(os.path.basename(rel_path))

    # -------- Process Scores if Available --------
    scores_json_path = Path(contests_dir) / source.lower() / str(year) / f"scores_{stage.replace(' ', '_')}.json"
    if scores_json_path.exists():
        with open(scores_json_path, "r", encoding="utf-8") as f:
            scores_data = json.load(f)

        # Build ordered list of scores per problem
        problem_keys = sorted(scores_data.keys(), key=int)
        problem_scores = [scores_data[key] for key in problem_keys]

        medal_cutoffs_block = contest.get("medal_cutoffs")
        if medal_cutoffs_block and isinstance(medal_cutoffs_block, list) and len(medal_cutoffs_block) > 0:
            cutoffs = medal_cutoffs_block[0]
            medal_names = list(cutoffs.keys())
            medal_cutoffs = [cutoffs[m] for m in medal_names]

            cur.execute('''
                INSERT INTO contest_scores (
                    contest_name, contest_stage,
                    medal_names, medal_cutoffs, problem_scores
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                name,
                stage,
                json.dumps(medal_names),
                json.dumps(medal_cutoffs),
                json.dumps(problem_scores),
            ))

conn.commit()
conn.close()

print("Processed YAML structure:")
for directory in sorted(yaml_files_by_dir):
    print(f"{directory}/")
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
