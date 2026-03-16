"""USTED Student Portal – Flask application."""

import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from database import get_connection

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))


@app.route("/", methods=["GET"])
def index():
    """Redirect root URL to login page."""
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Display login form and authenticate the student."""
    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        password = request.form.get("password", "")

        if not student_id or not password:
            flash("Please provide both Student ID and password.", "error")
            return render_template("login.html")

        conn = get_connection()
        try:
            student = conn.execute(
                "SELECT * FROM STUDENT WHERE student_id = ?",
                (student_id,),
            ).fetchone()
        finally:
            conn.close()

        if student and check_password_hash(student["password_hash"], password):
            session["student_id"] = student["student_id"]
            session["first_name"] = student["first_name"]
            flash(f"Welcome, {student['first_name']}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid Student ID or password.", "error")

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    """Simple protected dashboard page."""
    if "student_id" not in session:
        flash("Please log in to access the dashboard.", "error")
        return redirect(url_for("login"))
    return render_template("dashboard.html", first_name=session.get("first_name"))


@app.route("/logout")
def logout():
    """Clear the session and redirect to login."""
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
