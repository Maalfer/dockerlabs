from flask import session, g
import secrets

def get_current_role():
    """Obtiene el rol del usuario actual desde el objeto global g de Flask."""
    user = getattr(g, 'user', None)
    if user is None:
        return None
                                                        
    if isinstance(user, dict):
        return user.get('role')
    return getattr(user, 'role', None)

def generate_csrf_token():
    """Genera (o recupera) un token CSRF y lo guarda en la sesión de Flask."""
    token = session.get('csrf_token')
    if not token:
        token = secrets.token_hex(32)
        try:
            session['csrf_token'] = token
        except (RuntimeError, KeyError):
            pass
    return token
