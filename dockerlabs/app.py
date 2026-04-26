import os
import json
import secrets
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlparse, urljoin

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, g, flash, send_from_directory
from flask_login import LoginManager, current_user
from flask_limiter.errors import RateLimitExceeded
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from bunkerlabs.extensions import limiter
import bunkerlabs.decorators as decorators

from .extensions import db as alchemy_db
from .database import init_db
from . import validators
from .models import User
from .decorators import get_current_role, generate_csrf_token, csrf_protect, role_required, generate_token, verify_token
from .auth import auth_bp, get_profile_image_static_path, get_profile_image_url, load_username_change_requests
from .maquinas import maquinas_bp, recalcular_ranking_creadores
from .helpers import render_403_error, render_404_error
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'), template_folder=os.path.join(BASE_DIR, 'templates'))

app.config['SESSION_COOKIE_SECURE'] = True                                  
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

app.config['SECRET_KEY'] = secrets.token_hex(32)                                                  

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

limiter.init_app(app)

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

    # Permissions-Policy: desactiva características del navegador no utilizadas
    response.headers['Permissions-Policy'] = (
        'accelerometer=(), '
        'autoplay=(), '
        'camera=(), '
        'display-capture=(), '
        'encrypted-media=(), '
        'fullscreen=(), '
        'gamepad=(), '
        'geolocation=(), '
        'gyroscope=(), '
        'hid=(), '
        'idle-detection=(), '
        'magnetometer=(), '
        'microphone=(), '
        'midi=(), '
        'payment=(), '
        'picture-in-picture=(), '
        'publickey-credentials-get=(), '
        'screen-wake-lock=(), '
        'serial=(), '
        'storage-access=(), '
        'usb=(), '
        'xr-spatial-tracking=()'
    )

    return response

app.config['DATABASE'] = os.path.join(BASE_DIR, 'database', 'dockerlabs.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{app.config['DATABASE']}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

alchemy_db.init_app(app)

with app.app_context():
    init_db()


@app.before_request
def load_logged_in_user():
                                         
    g.csp_nonce = secrets.token_urlsafe(16)

    if current_user.is_authenticated:
        g.user = current_user
    else:
        g.user = None

decorators.get_current_role = get_current_role

app.register_blueprint(auth_bp)
app.register_blueprint(maquinas_bp)

@app.context_processor
def inject_globals():
    return {
        'current_user_role': get_current_role(),
        'csrf_token': generate_csrf_token,
        'csp_nonce': g.get('csp_nonce', ''),
        'get_profile_image_url': get_profile_image_url
    }

def obtener_dificultades():
    from .models import Machine
    dificultades = {}

    maquinas = Machine.query.filter_by(origen='docker').with_entities(Machine.nombre, Machine.dificultad).all()
    
    for m in maquinas:
        if m.nombre and m.dificultad:
            dificultades[m.nombre] = m.dificultad.lower()

    return dificultades

@app.errorhandler(404)
def page_not_found(e):
    return render_404_error()

from bunkerlabs import bunkerlabs_bp
app.register_blueprint(bunkerlabs_bp, url_prefix='/bunkerlabs')

from .writeups import writeups_bp
app.register_blueprint(writeups_bp)

from .routes import main_bp
app.register_blueprint(main_bp)

from .messaging import messaging_bp
app.register_blueprint(messaging_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)                                
