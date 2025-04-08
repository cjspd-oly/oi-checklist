import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

c.execute('''CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)''')

c.execute('''CREATE TABLE problems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    number INTEGER,
    source TEXT,
    year INTEGER,
    link TEXT
)''')

c.execute('''
CREATE TABLE problem_statuses (
    user_id INTEGER,
    problem_name TEXT,
    status INTEGER DEFAULT 0,
    PRIMARY KEY(user_id, problem_name),
    FOREIGN KEY(user_id) REFERENCES users(id)
)
''')

conn.commit()
conn.close()
