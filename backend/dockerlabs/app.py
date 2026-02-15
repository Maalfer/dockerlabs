import os
import json
import re
import secrets
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlparse, urljoin

from flask import Flask, request, jsonify, redirect, url_for, session, g, flash, send_from_directory
from flask_httpauth import HTTPBasicAuth
from flask_login import LoginManager, current_user
from flask_limiter.errors import RateLimitExceeded
from flasgger import Swagger
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from bunkerlabs.extensions import limiter
import bunkerlabs.decorators as decorators

from .extensions import db as alchemy_db
from .database import init_db
from . import validators
from .models import User
from .decorators import get_current_role, generate_csrf_token, csrf_protect, role_required, generate_token, verify_token
from .auth import auth_bp, get_profile_image_static_path, load_username_change_requests
from .maquinas import maquinas_bp, recalcular_ranking_creadores
from .api import api_bp

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PROFILE_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'images', 'perfiles')
MACHINE_LOGOS_FOLDER = os.path.join(BASE_DIR, 'static', 'images', 'logos')
LOGO_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'images', 'logos')
ALLOWED_PROFILE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_LOGO_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}

# Serve templates and static assets from the sibling `frontend/` folder so React assets
# and original templates are available after the repo reorganization.
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'frontend'))
DIST_DIR = os.path.join(FRONTEND_DIR, 'dist')
app = Flask(
    __name__,
    static_folder=os.path.join(FRONTEND_DIR, 'static'),
    template_folder=None
)
auth = HTTPBasicAuth()

from dotenv import load_dotenv
load_dotenv()

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs/"
}
swagger = Swagger(app, config=swagger_config)

# Use Secure cookies only when explicitly enabled (e.g., behind HTTPS in production).
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', '0') == '1'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

if not app.config['SECRET_KEY']:
    # Generar una clave segura aleatoria si no está configurada (útil para desarrollo/scripts)
    app.config['SECRET_KEY'] = secrets.token_hex(32)
    print("WARNING: SECRET_KEY not set. Using a temporary generated key.")                                                  

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
            f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net https://www.googletagmanager.com; "
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

@app.before_request
def restrict_swagger_access():
    if request.path.startswith('/docs') or request.path.startswith('/apispec.json') or request.path.startswith('/flasgger_static'):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))


decorators.get_current_role = get_current_role

app.register_blueprint(auth_bp)
app.register_blueprint(maquinas_bp)
app.register_blueprint(api_bp)


@app.route('/api/csrf')
def api_csrf():
    """
    Return a CSRF token and ensure session cookie is set for client-side forms.
    """
    token = generate_csrf_token()
    return jsonify({'csrf_token': token})

@app.context_processor
def inject_globals():
    return {
        'current_user_role': get_current_role(),
        'csrf_token': generate_csrf_token,                                             
        'csp_nonce': g.get('csp_nonce', '')
    }

def obtener_dificultades():
    from .models import Machine
    dificultades = {}

    maquinas = Machine.query.filter_by(origen='docker').with_entities(Machine.nombre, Machine.dificultad).all()
    
    for m in maquinas:
        if m.nombre and m.dificultad:
            dificultades[m.nombre] = m.dificultad.lower()

    return dificultades

@app.route('/terminos-condiciones')
def terminos_condiciones():
    """
    Página de términos y condiciones.
    ---
    tags:
      - Páginas
    responses:
      200:
        description: Página de términos.
    """
    return redirect('/')

@app.route('/bug-bounty')
def bug_bounty():
    """
    Página de Bug Bounty.
    ---
    tags:
      - Páginas
    responses:
      200:
        description: Página de Bug Bounty.
    """
    return redirect('/')

@app.route('/dashboard')
@role_required('admin', 'moderador', 'jugador')
def dashboard():
    """
    Panel de usuario (Dashboard).
    ---
    tags:
      - Páginas
    responses:
      200:
        description: Dashboard del usuario.
    """
    return redirect('/')


@app.route('/api/dashboard-data')
@role_required('admin', 'moderador', 'jugador')
def api_dashboard_data():
    """
    JSON API: Return dashboard data (pending claims + machines list).
    """
    from .models import Machine, MachineClaim

    maquinas = Machine.query.filter_by(origen='docker').with_entities(
        Machine.id, Machine.nombre, Machine.autor
    ).order_by(Machine.nombre.asc()).all()

    machines_list = [{'id': m.id, 'nombre': m.nombre, 'autor': m.autor} for m in maquinas]

    role = session.get('role') or (g.user.role if hasattr(g, 'user') and g.user else None)
    claims_list = []
    if role in ('admin', 'moderador'):
        claims = MachineClaim.query.filter_by(estado='pendiente').order_by(
            MachineClaim.created_at.desc()
        ).all()
        claims_list = [{
            'id': c.id,
            'username': c.username,
            'maquina_nombre': c.maquina_nombre,
            'contacto': c.contacto,
            'prueba': c.prueba,
            'estado': c.estado,
            'created_at': c.created_at.isoformat() if c.created_at else None
        } for c in claims]

    return jsonify({'machines': machines_list, 'claims': claims_list})




from flask import abort


@app.route('/')
def index():
    """Serve the React frontend built `index.html` as the application root."""
    index_path = os.path.join(DIST_DIR, 'index.html')
    if not os.path.exists(index_path):
        return jsonify({'error': 'React build not found. Run the frontend dev server or build the frontend.'}), 404
    return send_from_directory(DIST_DIR, 'index.html')


@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """Serve Vite-built asset bundles (JS/CSS) from dist/assets/."""
    return send_from_directory(os.path.join(DIST_DIR, 'assets'), filename)


# Catch-all for client-side routes: serve the React app for unknown paths
@app.route('/<path:unknown>')
def catch_all(unknown):
    # Do not interfere with API, static, docs, or asset routes
    if unknown.startswith(('api', 'static', 'docs', 'flasgger_static', 'assets', 'auth')):
        return abort(404)
    index_path = os.path.join(DIST_DIR, 'index.html')
    if not os.path.exists(index_path):
        return abort(404)
    return send_from_directory(DIST_DIR, 'index.html')

@app.errorhandler(404)
def page_not_found(e):
    if request.path.startswith('/api') or request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
        return jsonify({'error': 'Not Found'}), 404
    index_path = os.path.join(DIST_DIR, 'index.html')
    if not os.path.exists(index_path):
        return jsonify({'error': 'Not Found'}), 404
    return send_from_directory(DIST_DIR, 'index.html')

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
