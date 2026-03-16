import sqlite3
import os

DATABASE = os.path.join(os.path.dirname(__file__), "students.db")


def get_connection():
    """Return a new SQLite connection to the database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn
