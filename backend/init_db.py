import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

db_path = os.getenv("DATABASE_PATH", "database.db")  # fallback to "database.db" if not set
conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute('''CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

c.execute('''
CREATE TABLE auth_identities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    provider TEXT NOT NULL,
    provider_user_id TEXT,
    display_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, provider_user_id),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
''')

c.execute('''CREATE TABLE problems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    number INTEGER,
    source TEXT,
    year INTEGER,
    link TEXT,
    extra TEXT,
    UNIQUE(source, year, number, extra)
)''')

c.execute('''
CREATE TABLE problem_statuses (
    user_id INTEGER,
    problem_name TEXT,
    source TEXT,
    year INTEGER,
    status INTEGER DEFAULT 0,
    score REAL DEFAULT 0,
    PRIMARY KEY(user_id, problem_name, source, year),
    FOREIGN KEY(user_id) REFERENCES users(id)
)
''')

c.execute('''
CREATE TABLE user_settings (
    user_id INTEGER PRIMARY KEY,
    checklist_public BOOLEAN NOT NULL DEFAULT 0,
    olympiad_order TEXT DEFAULT NULL,
    local_storage TEXT DEFAULT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
)
''')

c.execute('''
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
)''')

c.execute('''
CREATE TABLE contests (
    name TEXT NOT NULL,
    stage TEXT,
    location TEXT,
    duration_minutes INTEGER,
    source TEXT NOT NULL,
    year INTEGER NOT NULL,
    date DATE,
    website TEXT,
    link TEXT,
    notes TEXT,
    PRIMARY KEY(name, stage)
)''')

c.execute('''CREATE TABLE contest_scores (
    contest_name TEXT NOT NULL,
    contest_stage TEXT,
    medal_names TEXT,
    medal_cutoffs TEXT,
    problem_scores TEXT,
    PRIMARY KEY(contest_name, contest_stage),
    FOREIGN KEY(contest_name, contest_stage)
        REFERENCES contests(name, stage) ON DELETE CASCADE
)''')

c.execute('''
CREATE TABLE contest_problems (
    contest_name TEXT NOT NULL,
    contest_stage TEXT,
    problem_source TEXT NOT NULL,
    problem_year INTEGER NOT NULL,
    problem_number INTEGER NOT NULL,
    problem_index INTEGER NOT NULL,
    PRIMARY KEY (contest_name, contest_stage, problem_index),
    FOREIGN KEY (contest_name, contest_stage)
        REFERENCES contests(name, stage) ON DELETE CASCADE,
    FOREIGN KEY (problem_source, problem_year, problem_number)
        REFERENCES problems(source, year, number) ON DELETE CASCADE
)''')

c.execute('''
  CREATE TABLE user_virtual_contests (
    user_id INTEGER NOT NULL,
    contest_name TEXT NOT NULL,
    contest_stage TEXT,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    score REAL,
    per_problem_scores TEXT,
    PRIMARY KEY(user_id, contest_name, contest_stage),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(contest_name, contest_stage) REFERENCES contests(name, stage) ON DELETE CASCADE
)''')

c.execute('''
CREATE TABLE user_virtual_submissions (
    user_id INTEGER NOT NULL,
    contest_name TEXT NOT NULL,
    contest_stage TEXT,
    submission_time TIMESTAMP NOT NULL,
    problem_index INTEGER NOT NULL,
    score REAL NOT NULL,
    subtask_scores TEXT NOT NULL,
    FOREIGN KEY(user_id, contest_name, contest_stage)
        REFERENCES user_virtual_contests(user_id, contest_name, contest_stage)
        ON DELETE CASCADE
)''')

c.execute('''
CREATE TABLE active_virtual_contests (
    user_id INTEGER PRIMARY KEY,
    contest_name TEXT NOT NULL,
    contest_stage TEXT,
    start_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    ojuz_synced BOOLEAN NOT NULL DEFAULT 0,
    score REAL,
    per_problem_scores TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(contest_name, contest_stage) REFERENCES contests(name, stage) ON DELETE CASCADE
)''')

conn.commit()
conn.close()
