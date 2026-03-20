import os
from flask import Flask
from models import db
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
    
    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
