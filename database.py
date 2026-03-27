import sqlite3
from pathlib import Path

# Keep legacy sqlite helper aligned with the Flask app database location.
DATABASE = str(Path('instance') / 'usted_portal.db')


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn
