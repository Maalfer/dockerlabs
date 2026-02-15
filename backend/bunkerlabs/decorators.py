from flask import request, session, redirect, url_for, jsonify
from functools import wraps
import secrets

get_current_role = None


def _wants_json():
    return request.path.startswith('/bunkerlabs/api') or request.path.startswith('/api') or (
        request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']
    )

def csrf_protect(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            session_token = session.get('csrf_token')
            header_token = request.headers.get('X-CSRFToken') or request.headers.get('X-CSRF-Token')
            form_token = request.form.get('csrf_token') if request.form else None
            token = header_token or form_token
            if not session_token or not token:
                if _wants_json():
                    return jsonify({'error': 'CSRF token missing'}), 400
                return redirect('/'), 403
            if not secrets.compare_digest(str(session_token), str(token)):
                if _wants_json():
                    return jsonify({'error': 'CSRF token invalid'}), 400
                return redirect('/'), 403
        return view_func(*args, **kwargs)
    return wrapped_view

def role_required(*roles_permitidos):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if session.get('user_id') is None:
                if _wants_json():
                    return jsonify({'error': 'Unauthorized'}), 401
                return redirect(url_for('auth.login'))

            role = get_current_role()
            if role not in roles_permitidos:
                if _wants_json():
                    return jsonify({'error': 'Forbidden'}), 403
                return redirect('/'), 403

            return view_func(*args, **kwargs)
        return wrapped_view
    return decorator
