"""Admin routes blueprint for the USTED Students Portal."""

from functools import wraps

from flask import Blueprint, render_template, session, redirect, url_for, flash

from models import Admin


admin_bp = Blueprint(
    'admin',
    __name__,
    url_prefix='/admin',
)


def admin_login_required(view_func):
    """Decorator to require admin login for protected admin routes."""
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if session.get('user_role') != 'admin' or not session.get('admin_id'):
            flash('Please sign in as admin to continue.', 'warning')
            return redirect(url_for('public.login'))
        return view_func(*args, **kwargs)
    return wrapped_view


def get_current_admin():
    """Resolve admin from active session."""
    admin_id = session.get('admin_id')
    if not admin_id:
        return None
    return Admin.query.filter_by(admin_id=admin_id).first()


@admin_bp.route('/dashboard')
@admin_login_required
def dashboard():
    """Lightweight admin dashboard placeholder for unified login routing."""
    admin = get_current_admin()
    if not admin:
        session.clear()
        flash('Admin record not found. Please log in again.', 'danger')
        return redirect(url_for('public.login'))

    return render_template('admin/dashboard.html', admin=admin)


@admin_bp.route('/logout')
@admin_login_required
def logout():
    """Clear admin session and return to login."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.login'))
