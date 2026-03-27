import os
from flask import Flask, session
from sqlalchemy import inspect
from models import db, Announcement, StudentAnnouncementRead
from routes import public_bp, student_bp, lecturer_bp, admin_bp


def _warn_if_legacy_grade_schema(app):
    """Log a warning when Grade score columns are still NOT NULL in an existing DB."""
    try:
        inspector = inspect(db.engine)
        if 'grade' not in set(inspector.get_table_names()):
            return

        target_columns = {'CA_score', 'Exam_Score', 'Total_Score', 'Grade_Letter'}
        non_nullable_columns = []
        for column in inspector.get_columns('grade'):
            if column['name'] in target_columns and not column.get('nullable', True):
                non_nullable_columns.append(column['name'])

        if non_nullable_columns:
            app.logger.warning(
                "Legacy Grade schema detected (non-null columns: %s). "
                "Run 'python migrate_grade_nullable.py' to enable IC support.",
                ', '.join(sorted(non_nullable_columns)),
            )
    except Exception as exc:  # pragma: no cover - defensive startup check
        app.logger.warning("Grade schema compatibility check skipped: %s", exc)


def create_app(database_uri=None):
    """Application factory for the USTED Students Portal."""
    app = Flask(__name__)
    
    # Configuration
    app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret-key-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = database_uri or 'sqlite:///usted_portal.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database with app
    db.init_app(app)
    with app.app_context():
        db.create_all()
        _warn_if_legacy_grade_schema(app)
    
    # Register blueprints
    app.register_blueprint(public_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(lecturer_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_announcements():
        """Provide announcement data for student and lecturer topbars."""
        student_id = session.get('student_id')
        lecturer_id = session.get('lecturer_id')

        if student_id:
            announcements = (
                Announcement.query
                .filter(Announcement.target_audience.in_(['All', 'Students']))
                .order_by(Announcement.date_posted.desc())
                .limit(5)
                .all()
            )

            announcement_ids = [item.announcement_id for item in announcements]
            read_ids = []
            if announcement_ids:
                read_ids = [
                    row.announcement_id
                    for row in StudentAnnouncementRead.query.filter_by(student_id=student_id)
                    .filter(StudentAnnouncementRead.announcement_id.in_(announcement_ids))
                    .all()
                ]

            unread_count = sum(1 for item in announcements if item.announcement_id not in read_ids)
            return {
                'top_announcements': announcements,
                'top_read_announcement_ids': read_ids,
                'top_unread_count': unread_count,
            }

        if lecturer_id:
            announcements = (
                Announcement.query
                .filter(Announcement.target_audience.in_(['All', 'Lecturers']))
                .order_by(Announcement.date_posted.desc())
                .limit(5)
                .all()
            )
            return {
                'top_announcements': announcements,
                'top_read_announcement_ids': [],
                'top_unread_count': len(announcements),
            }

        return {
            'top_announcements': [],
            'top_read_announcement_ids': [],
            'top_unread_count': 0,
        }
    
    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
