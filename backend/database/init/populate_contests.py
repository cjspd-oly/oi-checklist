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

CONTESTS_DIR = BACKEND_DIR / "data" / "contests"
COMPILE_TO_JSON = CONTESTS_DIR / "compile_to_json.py"
JSON_OUT = BACKEND_DIR / "contests.tmp.json"

if not COMPILE_TO_JSON.is_file():
    raise FileNotFoundError(f"compile_to_json.py not found at: {COMPILE_TO_JSON}")

subprocess.run(
    [sys.executable, str(COMPILE_TO_JSON), str(CONTESTS_DIR), "--output", str(JSON_OUT)],
    check=True,
)

with JSON_OUT.open("r", encoding="utf-8") as f:
    contests = json.load(f)

yaml_files_by_dir = defaultdict(set)
db_path = os.getenv("DATABASE_PATH", str(BACKEND_DIR / "database.db"))
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("DELETE FROM contest_problems")
cur.execute("DELETE FROM contest_scores")
cur.execute("DELETE FROM contests")

for contest in contests:
    name = contest["name"]
    source = contest["source"]
    year = contest["year"]
    stage = contest.get("stage")  # may be None

    # Insert contest row
    cur.execute(
        """
        INSERT INTO contests (
            name, stage, location, duration_minutes, source, year,
            date, website, link, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
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
        ),
    )

    # Insert problems for the contest
    for i, p in enumerate(contest["problems"]):
        cur.execute(
            """
            INSERT INTO contest_problems (
                contest_name, contest_stage,
                problem_source, problem_year, problem_number,
                problem_index
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                stage,
                p["source"],
                p["year"],
                p["number"],
                i + 1,
            ),
        )

    # (These are for preview/debugging; not used for file I/O below.)
    if stage is None:
        # No stages: data/contests/<source>/<year>.yaml
        rel_path = Path("data") / "contests" / source.lower() / f"{year}.yaml"
        scores_json_path = CONTESTS_DIR / source.lower() / f"scores_{year}.json"
    else:
        stage_filename = stage.replace(" ", "_")
        rel_path = Path("data") / "contests" / source.lower() / str(year) / f"{stage_filename}.yaml"
        scores_json_path = CONTESTS_DIR / source.lower() / str(year) / f"scores_{stage_filename}.json"

    yaml_files_by_dir[str(rel_path.parent)].add(rel_path.name)

    # Insert scores (if present in compiled JSON)
    scores_data = contest.get("scores")
    if scores_data:
        # Order problems numerically by key
        problem_keys = sorted(scores_data.keys(), key=int)
        problem_scores = [scores_data[k] for k in problem_keys]

        medal_cutoffs_block = contest.get("medal_cutoffs")
        if isinstance(medal_cutoffs_block, list) and medal_cutoffs_block:
            cutoffs = medal_cutoffs_block[0]
            medal_names = list(cutoffs.keys())
            medal_cutoffs = [cutoffs[m] for m in medal_names]

            cur.execute(
                """
                INSERT INTO contest_scores (
                    contest_name, contest_stage,
                    medal_names, medal_cutoffs, problem_scores
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    name,
                    stage,
                    json.dumps(medal_names),
                    json.dumps(medal_cutoffs),
                    json.dumps(problem_scores),
                ),
            )

conn.commit()
conn.close()

# Pretty print YAML structure preview
print("Processed YAML structure:")
for directory in sorted(yaml_files_by_dir):
    print(f"📂 {directory}/")
    files = sorted(yaml_files_by_dir[directory])
    display = files if len(files) <= 3 else [files[0], "...", files[-1]]
    for i, file in enumerate(display):
        prefix = "└── " if i == len(display) - 1 else "├── "
        print(f"    {prefix}{file}")

# Cleanup temp JSON
try:
    JSON_OUT.unlink()
    print(f"Deleted temporary file: {JSON_OUT}")
except OSError as e:
    print(f"Warning: could not delete {JSON_OUT}: {e}")
