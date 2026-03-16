from database import get_db_connection
from werkzeug.security import generate_password_hash


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS STUDENT (
            student_id   TEXT PRIMARY KEY,
            first_name   TEXT NOT NULL,
            last_name    TEXT NOT NULL,
            Email_address TEXT NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')

    dummy_password_hash = generate_password_hash('password123')
    cursor.execute('''
        INSERT OR IGNORE INTO STUDENT
            (student_id, first_name, last_name, Email_address, password_hash)
        VALUES (?, ?, ?, ?, ?)
    ''', ('STU001', 'John', 'Doe', 'john.doe@usted.edu', dummy_password_hash))

    conn.commit()
    conn.close()
    print('Database initialised successfully.')


if __name__ == '__main__':
    init_db()
