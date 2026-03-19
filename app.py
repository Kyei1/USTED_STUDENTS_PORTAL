import os

from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, Student

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret-key-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///usted_portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
with app.app_context():
    db.create_all()


@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        password = request.form.get('password', '')

        student = Student.query.filter_by(student_id=student_id).first()

        # Temporary plain-text comparison as requested.
        if student and password == student.password_hash:
            session['student_id'] = student.student_id
            session['first_name'] = student.first_name
            flash(f'Login successful! Welcome, {student.first_name}.', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid student ID or password. Please try again.', 'danger')
        return render_template('login.html')

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'student_id' not in session:
        flash('Please log in to access the dashboard.', 'warning')
        return redirect(url_for('login'))
    return render_template('dashboard.html',
                           first_name=session.get('first_name'),
                           student_id=session.get('student_id'))


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
