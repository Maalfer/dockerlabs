from flask import request, session, redirect, url_for, render_template, jsonify
from functools import wraps
import secrets

get_current_role = None

def csrf_protect(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            session_token = session.get('csrf_token')
            header_token = request.headers.get('X-CSRFToken') or request.headers.get('X-CSRF-Token')
            form_token = request.form.get('csrf_token') if request.form else None
            token = header_token or form_token
            if not session_token or not token:
                return render_template('403.html'), 403
            if not secrets.compare_digest(str(session_token), str(token)):
                return render_template('403.html'), 403
        return view_func(*args, **kwargs)
    return wrapped_view

def role_required(*roles_permitidos):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if session.get('user_id') is None:
                return redirect(url_for('auth.login'))

            role = get_current_role()
            if role not in roles_permitidos:
                return render_template('403.html'), 403

            return view_func(*args, **kwargs)
        return wrapped_view
    return decorator
