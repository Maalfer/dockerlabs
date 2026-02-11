import os
import json
import re
import secrets
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlparse, urljoin

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, g, flash, send_from_directory
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

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'), template_folder=os.path.join(BASE_DIR, 'templates'))
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

app.config['SESSION_COOKIE_SECURE'] = True                                  
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
    return render_template('dockerlabs/terminos-condiciones.html')

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
    return render_template('dockerlabs/bug_bounty.html')

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
    from .models import Machine

    maquinas = Machine.query.filter_by(origen='docker').with_entities(Machine.id, Machine.nombre, Machine.autor).order_by(Machine.nombre.asc()).all()

    current_username = session.get('username') or (current_user.username if current_user.is_authenticated else None)
    current_user_id = session.get('user_id') or (current_user.id if current_user.is_authenticated else None)

    static_path = get_profile_image_static_path(current_username, user_id=current_user_id)

    if static_path is None:
        static_path = 'dockerlabs/images/balu.webp'

    profile_image_url = url_for('static', filename=static_path)

    return render_template(
        'dockerlabs/dashboard.html',
        maquinas=maquinas,
        profile_image_url=profile_image_url,
        user=g.user
    )

@app.route('/peticiones')
@role_required('admin', 'moderador')
@limiter.limit("20 per minute")
def peticiones():
    """
    Gestión de peticiones de administración.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Página de peticiones.
    """
    from .models import MachineClaim, NameClaim, WriteupEditRequest, MachineEditRequest, Writeup, UsernameChangeRequest

    claims_objs = MachineClaim.query.order_by(MachineClaim.created_at.desc(), MachineClaim.id.desc()).all()

    claims = claims_objs

    envios_maquinas = []

    peticiones_nombres_objs = NameClaim.query.order_by(NameClaim.created_at.desc(), NameClaim.id.desc()).all()
    peticiones_nombres = peticiones_nombres_objs

    edit_requests_query = alchemy_db.session.query(WriteupEditRequest, Writeup).outerjoin(Writeup, Writeup.id == WriteupEditRequest.writeup_id).order_by(WriteupEditRequest.created_at.desc(), WriteupEditRequest.id.desc()).all()
    
    edit_requests = []
    for req, w in edit_requests_query:
                                                                                                         
        row = {
            'id': req.id,
            'writeup_id': req.writeup_id,
            'user_id': req.user_id,
            'username': req.username,
            'maquina_original': req.maquina_original,
            'autor_original': req.autor_original,
            'url_original': req.url_original,
            'tipo_original': req.tipo_original,
            'maquina_nueva': req.maquina_nueva,
            'autor_nuevo': req.autor_nuevo,
            'url_nueva': req.url_nueva,
            'tipo_nuevo': req.tipo_nuevo,
            'estado': req.estado,
            'created_at': req.created_at.isoformat() if req.created_at else None,                                  
                                               
            'maquina_actual': w.maquina if w else None,
            'autor_actual': w.autor if w else None,
            'url_actual': w.url if w else None,
            'tipo_actual': w.tipo if w else None
        }
        edit_requests.append(row)

    machine_edit_requests_objs = MachineEditRequest.query.order_by(MachineEditRequest.fecha.desc(), MachineEditRequest.id.desc()).all()
    
    machine_edit_requests_parsed = []
    for r in machine_edit_requests_objs:
        try:
            nuevos = json.loads(r.nuevos_datos)
        except:
            nuevos = {}
        machine_edit_requests_parsed.append({
            "id": r.id,
            "machine_id": r.machine_id,
            "origen": r.origen,
            "autor": r.autor,
            "estado": r.estado,
            "fecha": r.fecha,
            "nuevos": nuevos
        })

    from .auth import load_username_change_requests
    username_change_requests = load_username_change_requests()

    return render_template(
        'dockerlabs/peticiones.html',
        claims=claims,
        envios_maquinas=envios_maquinas,
        peticiones_nombres=peticiones_nombres,
        edit_requests=edit_requests,
        machine_edit_requests=machine_edit_requests_parsed,
        username_change_requests=username_change_requests
    )

from urllib.parse import urlparse, urljoin

@app.route('/nombre-claims/<int:claim_id>/approve', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def approve_nombre_claim(claim_id):
    """
    Aprobar reclamación de nombre de usuario.
    ---
    tags:
      - Admin
    responses:
      302:
        description: Redirigir a peticiones.
    """
    def is_safe_url(target):
        host_url = request.host_url
        ref = urljoin(host_url, target)
        return urlparse(ref).netloc == urlparse(host_url).netloc

    ref = request.referrer
    if not ref or not is_safe_url(ref):
        safe_redirect = url_for('peticiones')
    else:
        safe_redirect = ref

    from .models import NameClaim, User
    from sqlalchemy.exc import IntegrityError
    
    claim = NameClaim.query.get(claim_id)

    if claim is None:
        return redirect(safe_redirect)

    existing = User.query.filter((User.username == claim.nombre_solicitado) | (User.email == claim.email)).first()

    if existing:
        claim.estado = 'rechazada'
        alchemy_db.session.commit()
        return redirect(safe_redirect)

    try:
                         
        new_user = User(
            username=claim.nombre_solicitado,
            email=claim.email,
            password_hash=claim.password_hash,
            role='jugador'
        )
        alchemy_db.session.add(new_user)

        claim.estado = 'aprobada'
        
        alchemy_db.session.commit()
    except IntegrityError:
        alchemy_db.session.rollback()
        claim.estado = 'rechazada'
        alchemy_db.session.commit()
    except Exception:
        alchemy_db.session.rollback()

    return redirect(safe_redirect)

from urllib.parse import urlparse, urljoin

@app.route('/nombre-claims/<int:claim_id>/reject', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def reject_nombre_claim(claim_id):
    """
    Rechazar reclamación de nombre de usuario.
    ---
    tags:
      - Admin
    responses:
      302:
        description: Redirigir a peticiones.
    """
    def is_safe_url(target):
        host_url = request.host_url
        ref = urljoin(host_url, target)
        return urlparse(ref).netloc == urlparse(host_url).netloc

    ref = request.referrer
    if not ref or not is_safe_url(ref):
        safe_redirect = url_for('peticiones')
    else:
        safe_redirect = ref

    from .models import NameClaim
    claim = NameClaim.query.get(claim_id)
    if claim:
        claim.estado = 'rechazada'
        alchemy_db.session.commit()
        
    return redirect(safe_redirect)

@app.route('/nombre-claims/<int:claim_id>/revert', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
def revert_nombre_claim(claim_id):
    """
    Revertir estado de reclamación de nombre.
    ---
    tags:
      - Admin
    responses:
      302:
        description: Redirigir a peticiones.
    """
    from .models import NameClaim
    claim = NameClaim.query.get(claim_id)
    if claim:
        claim.estado = 'pendiente'
        alchemy_db.session.commit()
    return redirect(url_for('peticiones'))

@app.route('/')
def index():
    """
    Página de inicio.
    ---
    tags:
      - Páginas
    responses:
      200:
        description: Página de bienvenida.
    """
    from .models import Machine, Category, CompletedMachine, User
    from sqlalchemy import func
    from .extensions import db as alchemy_db

    query = alchemy_db.session.query(Machine, Category.categoria).filter(
        Machine.origen == 'docker'
    ).outerjoin(
        Category, (Machine.id == Category.machine_id) & (Category.origen == 'docker')
    ).order_by(Machine.id.asc()).all()
    
    all_maquinas = []
    for m, cat_name in query:
                        
        d = {
            'id': m.id,
            'nombre': m.nombre,
            'dificultad': m.dificultad,
            'clase': m.clase,
            'color': m.color,
            'autor': m.autor,
            'enlace_autor': m.enlace_autor,
            'fecha': m.fecha,
            'imagen': m.imagen,
            'descripcion': m.descripcion,
            'link_descarga': m.link_descarga,
            'posicion': m.posicion,
            'categoria': cat_name
        }
        all_maquinas.append(d)

    maquinas_con_fecha = []
    for m_dict in all_maquinas:
        fecha_str = m_dict['fecha']                     
        try:
            parts = fecha_str.split('/')
            if len(parts) == 3:
                            
                fecha_iso = f"{parts[2]}-{parts[1]}-{parts[0]}"
                maquinas_con_fecha.append((m_dict, fecha_iso))
        except Exception:
            pass

    maquinas_con_fecha.sort(key=lambda x: x[1], reverse=True)

    machine_ranks = {}
    top_2_items = maquinas_con_fecha[:2]
    for idx, (m, _) in enumerate(top_2_items):
        machine_ranks[m['id']] = idx + 1
    
    top_2_ids = {m['id'] for m, _ in top_2_items}
    top_2 = [m for m, _ in top_2_items]
    rest = [m for m in all_maquinas if m['id'] not in top_2_ids]
    maquinas = top_2 + rest

    completed_machines = []
    if current_user.is_authenticated:
                                        
        comp_objs = CompletedMachine.query.filter_by(user_id=current_user.id).all()
        completed_machines = [c.machine_name.strip() for c in comp_objs]

    single_machine = len(maquinas) == 1

    categorias_map = {}
    for m in maquinas:
        categorias_map[m['id']] = m['categoria'] if m['categoria'] else ''

    return render_template('dockerlabs/home.html', maquinas=maquinas, completed_machines=completed_machines, machine_ranks=machine_ranks, single_machine=single_machine, categorias_map=categorias_map)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('dockerlabs/404.html'), 404

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
