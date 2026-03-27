"""Initialize the current portal schema and seed baseline data.

This script is kept for convenience and now targets the same database
used by the Flask app (instance/usted_portal.db).
"""

from app import app, db
from seed_db import seed_initial_data


def init_db():
    with app.app_context():
        db.create_all()
    seed_initial_data(reset_schema=False)
    print('Database initialized successfully using current schema.')


if __name__ == '__main__':
    init_db()
