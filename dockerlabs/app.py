"""
app.py — Capa de inicialización de Flask (middleware para FastAPI).

Flask ya NO gestiona ninguna ruta de la aplicación. Actúa exclusivamente como:
  - Proveedor del contexto de SQLAlchemy (flask_app.app_context())
  - Gestor de sesiones cifradas (SECRET_KEY compartida con FastAPI)
  - Configurador de la base de datos y LoginManager
  - Middleware de cabeceras de seguridad HTTP

Todas las rutas están en: dockerlabs/routers.py (FastAPI)
"""

import os
import secrets

from flask import Flask, g
from flask_login import LoginManager, current_user

from bunkerlabs.extensions import limiter

from .extensions import db as alchemy_db
from .database import init_db
from .models import User
from .decorators import get_current_role, generate_csrf_token
from .auth import get_profile_image_url
from .helpers import render_403_error, render_404_error

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, 'static'),
    template_folder=os.path.join(BASE_DIR, 'templates')
)

# ── Seguridad de sesión ────────────────────────────────────────────────────────
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SECRET_KEY'] = secrets.token_hex(32)

# ── Login Manager ──────────────────────────────────────────────────────────────
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ── Rate limiter ───────────────────────────────────────────────────────────────
limiter.init_app(app)

# ── Cabeceras de seguridad HTTP ────────────────────────────────────────────────
@app.after_request
def apply_security_headers(response):
    nonce = g.get('csp_nonce')

    if nonce:
        response.headers['Content-Security-Policy-Report-Only'] = (
            f"default-src 'self'; "
            f"style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            f"script-src 'self' 'nonce-{nonce}' 'unsafe-hashes' https://cdn.jsdelivr.net https://www.googletagmanager.com; "
            f"img-src 'self' data: https:; "
            f"font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            f"connect-src 'self'; "
            f"frame-src 'self' https://www.youtube.com; "
            f"frame-ancestors 'self'; "
            f"object-src 'none'; "
            f"base-uri 'self'; "
            f"form-action 'self';"
        )

    response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains; preload'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = (
        'accelerometer=(), autoplay=(), camera=(), display-capture=(), '
        'encrypted-media=(), fullscreen=(), gamepad=(), geolocation=(), '
        'gyroscope=(), hid=(), idle-detection=(), magnetometer=(), '
        'microphone=(), midi=(), payment=(), picture-in-picture=(), '
        'publickey-credentials-get=(), screen-wake-lock=(), serial=(), '
        'storage-access=(), usb=(), xr-spatial-tracking=()'
    )
    return response

# ── Base de datos ──────────────────────────────────────────────────────────────
app.config['DATABASE'] = os.path.join(BASE_DIR, 'database', 'dockerlabs.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{app.config['DATABASE']}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

alchemy_db.init_app(app)

with app.app_context():
    init_db()

# ── Hooks de request ───────────────────────────────────────────────────────────
@app.before_request
def load_logged_in_user():
    g.csp_nonce = secrets.token_urlsafe(16)
    g.user = current_user if current_user.is_authenticated else None

# ── Context processors (para plantillas Flask residuales) ─────────────────────
@app.context_processor
def inject_globals():
    return {
        'current_user_role': get_current_role(),
        'csrf_token': generate_csrf_token,
        'csp_nonce': g.get('csp_nonce', ''),
        'get_profile_image_url': get_profile_image_url,
    }

# ── Manejadores de error ───────────────────────────────────────────────────────
@app.errorhandler(403)
def forbidden_error(e):
    return render_403_error()

@app.errorhandler(404)
def page_not_found(e):
    return render_404_error()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
