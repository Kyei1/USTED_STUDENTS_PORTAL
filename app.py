import os
from flask import Flask, session
from models import db, Announcement, StudentAnnouncementRead
from routes import public_bp, student_bp


def create_app():
    """Application factory for the USTED Students Portal."""
    app = Flask(__name__)
    
    # Configuration
    app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret-key-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///usted_portal.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database with app
    db.init_app(app)
    with app.app_context():
        db.create_all()
    
    # Register blueprints
    app.register_blueprint(public_bp)
    app.register_blueprint(student_bp)

    @app.context_processor
    def inject_announcements():
        """Provide latest student-facing announcements to templates."""
        student_id = session.get('student_id')
        if not student_id:
            return {
                'top_announcements': [],
                'top_read_announcement_ids': [],
                'top_unread_count': 0,
            }

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
    
    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
