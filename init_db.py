"""Initialize the SQLite database.

Creates the STUDENT table and inserts one dummy user.
Run this script once before starting the application:

    python init_db.py
"""

from werkzeug.security import generate_password_hash
from database import get_connection


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS STUDENT (
            student_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name    TEXT    NOT NULL,
            last_name     TEXT    NOT NULL,
            password_hash TEXT    NOT NULL
        )
        """
    )

    # Insert a dummy student only if the table is empty
    cursor.execute("SELECT COUNT(*) FROM STUDENT")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            """
            INSERT INTO STUDENT (first_name, last_name, password_hash)
            VALUES (?, ?, ?)
            """,
            (
                "John",
                "Doe",
                generate_password_hash("password123"),
            ),
        )
        print("Dummy student inserted: student_id=1, first_name=John, last_name=Doe, password=password123")
    else:
        print("Table already contains data — skipping dummy insert.")

    conn.commit()
    conn.close()
    print("Database initialized successfully.")


if __name__ == "__main__":
    init_db()
