from functools import wraps
from flask import session, redirect, url_for, flash, g
from models import User

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

def login_required(roles=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            user = get_current_user()
            if not user:
                session.clear()
                flash('Session expired. Please log in again.', 'warning')
                return redirect(url_for('login'))
            if roles:
                if isinstance(roles, str) and user.role != roles:
                    flash('Unauthorized access for your role.', 'danger')
                    return redirect(url_for('dashboard'))
                elif isinstance(roles, (list, tuple)) and user.role not in roles:
                    flash('Unauthorized access for your role.', 'danger')
                    return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
