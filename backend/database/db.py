import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

def get_db():
    db_path = os.getenv("DATABASE_PATH", "database.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn