import secrets


def generate_csrf_token():
    """Genera un token CSRF aleatorio."""
    return secrets.token_hex(32)
