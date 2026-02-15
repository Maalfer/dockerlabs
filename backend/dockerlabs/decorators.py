from functools import wraps
from flask import session, request, jsonify, redirect, url_for, g
import secrets
from datetime import datetime

tokens = {}

def get_current_role():
    user = getattr(g, 'user', None)
    if user is None:
        return None
                                                        
    if isinstance(user, dict):
        return user.get('role')
    return getattr(user, 'role', None)

def generate_csrf_token():
    token = session.get('csrf_token')
    if not token:
        token = secrets.token_hex(32)
        try:
            session['csrf_token'] = token
        except (RuntimeError, KeyError):

            pass
    return token

def csrf_protect(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            session_token = session.get('csrf_token')
            header_token = request.headers.get('X-CSRFToken') or request.headers.get('X-CSRF-Token')
            form_token = request.form.get('csrf_token') if request.form else None
            token = header_token or form_token
            if not session_token or not token:
                if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
                    return jsonify({'error': 'CSRF token missing'}), 400
                return redirect('/'), 403
            if not secrets.compare_digest(str(session_token), str(token)):
                if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
                    return jsonify({'error': 'CSRF token invalid'}), 400
                return redirect('/'), 403
        return view_func(*args, **kwargs)
    return wrapped_view

def role_required(*roles_permitidos):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if session.get('user_id') is None:
                if request.path.startswith('/api') or request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
                    return jsonify({'error': 'Unauthorized'}), 401
                return redirect('/'), 403
            
            role = get_current_role()
            if role not in roles_permitidos:
                if request.path.startswith('/api') or request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
                    return jsonify({'error': 'Forbidden'}), 403
                return redirect('/'), 403
            return view_func(*args, **kwargs)
        return wrapped_view
    return decorator

def generate_token():
    return secrets.token_hex(16)

def verify_token(token):
    if token in tokens:
        if datetime.now() < tokens[token]:
            return True
        else:
            del tokens[token]
    return False
