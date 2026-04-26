from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import func
from datetime import datetime
import secrets
import re
import os
import io
import shutil
import sqlite3
import tempfile
import zipfile
import fcntl
from slowapi import Limiter
from slowapi.util import get_remote_address

# Importaciones Flask (necesarias durante la migración)
# No importamos flask_app
from dockerlabs.models import User, Machine, Writeup, PendingMachineSubmission, Category, CreatorRanking, WriteupRanking, PendingWriteup, NameClaim, UsernameChangeRequest, PendingWriteup, WriteupEditRequest, CompletedMachine, Rating
from dockerlabs.extensions import db as alchemy_db
from dockerlabs.decorators import generate_csrf_token
from werkzeug.security import check_password_hash, generate_password_hash
from flask.sessions import SecureCookieSessionInterface

def url_for(endpoint, **kwargs):
    """Función url_for compatible con Flask para FastAPI"""
    if endpoint == 'static':
        filename = kwargs.get('filename', '')
        return f"/static/{filename}"
    
    # Mapeo de rutas de Flask a FastAPI
    flask_to_fastapi = {
        'auth.login': '/login',
        'auth.register': '/register',
        'auth.recover': '/recover',
        'auth.logout': '/logout',
        'auth.gestion_usuarios': '/gestion-usuarios',
        'bunkerlabs.bunkerlabs_login': '/bunkerlabs/login',
        'bunkerlabs.accesos_bunkerlabs': '/bunkerlabs/accesos',
        'main.home': '/',
        'main.dashboard': '/dashboard',
        'main.instrucciones_uso': '/instrucciones-uso',
        'main.soporte': '/soporte',
        'main.equipo': '/equipo',
        'main.enviar_maquina': '/enviar-maquina',
        'main.como_se_crea': '/como-se-crea-una-maquina',
        'main.agradecimientos': '/agradecimientos',
        'main.terminos_condiciones': '/terminos-condiciones',
        'main.politica_privacidad': '/politica-privacidad',
        'main.politica_cookies': '/politica-cookies',
        'main.condiciones_uso': '/condiciones-uso',
        'main.estadisticas': '/estadisticas',
        'main.backups_page': '/backups',
        'main.download_backup': '/backups/download',
        'main.restore_backup': '/backups/restore',
        'main.pending_machines': '/pending-machines',
        'main.user_pending_machines': '/user-pending',
        'main.approve_machine': '/api/admin/pending-machines/{id}/approve',
        'main.reject_machine': '/api/admin/pending-machines/{id}/reject',
        'main.bug_bounty': '/bug-bounty',
        # Auth
        'auth.login': '/login',
        'auth.register': '/register',
        'auth.recover': '/recover',
        'auth.logout': '/logout',
        'auth.gestion_usuarios': '/gestion-usuarios',
        # BunkerLabs
        'bunkerlabs.bunkerlabs_login': '/bunkerlabs/login',
        'bunkerlabs.bunkerlabs_home': '/bunkerlabs',
        'bunkerlabs.bunkerlabs_logout': '/bunkerlabs/logout',
        'bunkerlabs.bunkerlabs_guest': '/bunkerlabs/guest',
        'bunkerlabs.accesos_bunkerlabs': '/bunkerlabs/accesos',
        'bunkerlabs.delete_bunker_token': '/bunkerlabs/accesos/{token_id}/delete',
        # Máquinas
        'maquinas.maquinas_hechas': '/maquinas-hechas',
        'maquinas.gestion_maquinas': '/gestion-maquinas',
        'maquinas.add_maquina_page': '/add-maquina',
        'maquinas.actualizar_maquina': '/gestion-maquinas/actualizar',
        'maquinas.eliminar_maquina': '/gestion-maquinas/eliminar',
        'maquinas.serve_machine_logo': '/img/maquina/{machine_id}',
        # Writeups
        'writeups.writeups_publicados': '/writeups-publicados',
        'writeups.writeups_recibidos': '/writeups-recibidos',
        # Misc
        'dashboard': '/dashboard',
        'index': '/',
        'peticiones': '/peticiones-writeups',
    }

    # Si está en el mapeo, usar la ruta de FastAPI
    if endpoint in flask_to_fastapi:
        path = flask_to_fastapi[endpoint]
        # Sustituir parámetros dinámicos {param} con los kwargs recibidos
        used_keys = set()
        import re as _re
        def replace_param(match, _kw=kwargs):
            key = match.group(1)
            used_keys.add(key)
            return str(_kw.get(key, match.group(0)))
        path = _re.sub(r'\{(\w+)\}', replace_param, path)
        # Parámetros restantes como query string
        qs_params = {k: v for k, v in kwargs.items() if k not in used_keys and k != '_external'}
        if qs_params:
            from urllib.parse import urlencode
            path = f"{path}?{urlencode(qs_params)}"
        return path

    # Para otros endpoints, devolver el nombre del endpoint
    return f"/{endpoint}"

# Configurar Jinja2 templates
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, 'templates'))

# Sobrescribir url_for en el entorno de Jinja2 para usar nuestra función personalizada
templates.env.globals['url_for'] = url_for

# --- Modelos Pydantic ---

class AutorRankingResponse(BaseModel):
    id: int
    nombre: str
    maquinas: int
    autor: str
    imagen: str

class WriteupRankingResponse(BaseModel):
    id: int
    nombre: str
    puntos: int
    imagen_url: str

class MaquinaInfoResponse(BaseModel):
    id: int
    nombre: str
    dificultad: str
    clase: str
    color: str
    autor: str
    enlace_autor: str
    fecha: str
    imagen: str
    descripcion: str
    link_descarga: str
    imagen_url: Optional[str] = None

class MetadataResponse(BaseModel):
    total_creadores: int
    total_puntos: int
    total_writeups: int

class WriteupBasicResponse(BaseModel):
    id: int
    maquina: str
    autor: str
    url: str
    tipo: str
    created_at: Optional[datetime] = None

class WriteupsCategoriaResponse(BaseModel):
    textos: List[WriteupBasicResponse]
    videos: List[WriteupBasicResponse]

class RankingCreadorBasic(BaseModel):
    id: int
    nombre: str
    maquinas: int

class RankingWriteupBasic(BaseModel):
    id: int
    nombre: str
    puntos: int

class ApiSummaryResponse(BaseModel):
    info_maquinas: List[MaquinaInfoResponse]
    maquinas: List[str]
    metadata: MetadataResponse
    ranking_creadores: List[RankingCreadorBasic]
    ranking_writeups: List[RankingWriteupBasic]
    writeups: WriteupsCategoriaResponse

class UserInfoBasic(BaseModel):
    id: int
    username: str
    email: str
    role: str
    biography: Optional[str]
    linkedin_url: Optional[str]
    github_url: Optional[str]
    youtube_url: Optional[str]
    created_at: Optional[datetime]
    profile_image_url: str

class CompletedMachineResponse(BaseModel):
    machine_name: str
    completed_at: Optional[datetime]

class UserInfoResponse(BaseModel):
    is_authenticated: bool
    user: Optional[UserInfoBasic] = None
    completed_machines: Optional[List[CompletedMachineResponse]] = None
    submitted_writeups: Optional[List[WriteupBasicResponse]] = None
    error: Optional[str] = None

class SubmitMachineRequest(BaseModel):
    nombre: str
    link_maquina: str
    dificultad: str
    discord_user: str
    categoria: Optional[str] = None
    tags: Optional[str] = None
    descripcion: Optional[str] = None
    notas: Optional[str] = None
    writeup_url: Optional[str] = None

class SubmitMachineResponse(BaseModel):
    success: Optional[bool] = None
    message: Optional[str] = None
    error: Optional[str] = None

api_router = APIRouter(prefix="/api", tags=["API Pública"])

# Router separado para páginas HTML (sin prefijo /api)
pages_router = APIRouter(tags=["Páginas HTML"])

from itsdangerous import URLSafeTimedSerializer
import secrets

# Clave secreta para la sesión. Se reinicia al iniciar el servidor igual que antes en app.py
SESSION_SECRET_KEY = secrets.token_hex(32)

def get_session_serializer():
    from itsdangerous.url_safe import URLSafeTimedSerializer
    return URLSafeTimedSerializer(SESSION_SECRET_KEY, salt='cookie-session')

def get_flask_session(request: Request) -> dict:
    """Extraer sesión desde cookies usando itsdangerous directamente sin Flask."""
    cookie = request.cookies.get("session")
    if not cookie:
        return {}
    
    serializer = get_session_serializer()
    try:
        data = serializer.loads(cookie)
        return dict(data) if isinstance(data, dict) else {}
    except:
        return {}

async def verify_csrf_token(request: Request, flask_session: dict = Depends(get_flask_session)):
    """Verifica el token CSRF tal y como lo hacía @csrf_protect de Flask."""
    if request.method not in ("POST", "PUT", "DELETE", "PATCH"):
        return True

    session_token = flask_session.get("csrf_token")
    token = request.headers.get("X-CSRFToken") or request.headers.get("X-CSRF-Token")

    if not token and request.method == "POST":
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            form = await request.form()
            token = form.get("csrf_token")

    # Si no hay sesión (usuario no autenticado), no verificar CSRF para endpoints públicos
    if not session_token:
        return True

    if not token or not secrets.compare_digest(str(session_token), str(token)):
        raise HTTPException(status_code=403, detail="CSRF token missing or invalid")
    return True

def get_fastapi_profile_image_url(username: Optional[str] = None, user_id: Optional[int] = None) -> str:
    """Helper to bypass Flask's url_for dependency in FastAPI.
    Genera URLs consistentes con el endpoint /img/perfil/{user_id} en pages_router.
    """
    if user_id:
        return f"/img/perfil/{user_id}"
    if username:
        from dockerlabs.models import User as _User
        user = _User.query.filter_by(username=username).first()
        if user:
            return f"/img/perfil/{user.id}"
    return "/static/dockerlabs/images/balu.webp"

# Añadir get_profile_image_url a los globals de Jinja2 después de definir la función
templates.env.globals['get_profile_image_url'] = get_fastapi_profile_image_url

@api_router.get("", response_model=ApiSummaryResponse)
def api_summary(request: Request):
    
    maquinas_objs = Machine.query.filter_by(origen='docker').order_by(Machine.id.asc()).all()
    info_maquinas = []
    maquinas_names = []
    for m in maquinas_objs:
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
            'link_descarga': m.link_descarga
        }
        if d['imagen']:
            # Reemplazo de url_for estático de Flask
            d['imagen_url'] = f"/static/dockerlabs/{d['imagen']}"
        info_maquinas.append(d)
        maquinas_names.append(d['nombre'])

    creadores_objs = CreatorRanking.query.order_by(CreatorRanking.maquinas.desc(), func.lower(CreatorRanking.nombre).asc()).all()
    ranking_creadores = [{'id': r.id, 'nombre': r.nombre, 'maquinas': r.maquinas} for r in creadores_objs]

    ranking_w_objs = WriteupRanking.query.order_by(WriteupRanking.puntos.desc(), func.lower(WriteupRanking.nombre).asc()).all()
    ranking_writeups = [{'id': r.id, 'nombre': r.nombre, 'puntos': r.puntos} for r in ranking_w_objs]

    writeups_objs = Writeup.query.order_by(Writeup.created_at.desc()).all()
    writeups_textos = []
    writeups_videos = []
    for w in writeups_objs:
        d = {
            'id': w.id,
            'maquina': w.maquina,
            'autor': w.autor,
            'url': w.url,
            'tipo': w.tipo,
            'created_at': w.created_at
        }
        if w.tipo == 'texto':
            writeups_textos.append(d)
        else:
            writeups_videos.append(d)

    total_creadores = len(ranking_creadores)
    total_puntos = sum(r['puntos'] for r in ranking_writeups)
    total_writeups = len(writeups_objs)

    metadata = {
        "total_creadores": total_creadores,
        "total_puntos": total_puntos,
        "total_writeups": total_writeups
    }

    response = {
        "info_maquinas": info_maquinas,
        "maquinas": maquinas_names,
        "metadata": metadata,
        "ranking_creadores": ranking_creadores,
        "ranking_writeups": ranking_writeups,
        "writeups": {
            "textos": writeups_textos,
            "videos": writeups_videos
        }
    }

    return response

@api_router.get("/ranking_autores", response_model=List[AutorRankingResponse])
def api_ranking_autores(request: Request):
    from sqlalchemy.orm import joinedload

    results = alchemy_db.session.query(
        CreatorRanking
    ).outerjoin(User, func.lower(User.username) == func.lower(CreatorRanking.nombre)) \
    .options(joinedload(CreatorRanking.user)) \
    .order_by(CreatorRanking.maquinas.desc(), func.lower(CreatorRanking.nombre).asc()) \
    .all()

    response_list = []
    for creator in results:
        r = {
            'id': creator.id,
            'nombre': creator.nombre,
            'maquinas': creator.maquinas,
            'autor': creator.nombre
        }
        user_id = creator.user.id if creator.user else None
        r['imagen'] = get_fastapi_profile_image_url(username=r['autor'], user_id=user_id)
        response_list.append(r)

    return response_list

@api_router.get("/ranking_writeups", response_model=List[WriteupRankingResponse])
def api_ranking_writeups(request: Request):
    from sqlalchemy.orm import joinedload

    results = alchemy_db.session.query(
        WriteupRanking
    ).outerjoin(User, func.lower(User.username) == func.lower(WriteupRanking.nombre)) \
    .options(joinedload(WriteupRanking.user)) \
    .order_by(WriteupRanking.puntos.desc(), func.lower(WriteupRanking.nombre).asc()) \
    .all()

    response_list = []
    for rank in results:
        r = {
            'id': rank.id,
            'nombre': rank.nombre,
            'puntos': rank.puntos
        }
        author_name = rank.nombre
        user_id = rank.user.id if rank.user else None
        r['imagen_url'] = get_fastapi_profile_image_url(username=author_name, user_id=user_id)
        response_list.append(r)

    return response_list

@api_router.get("/user/info", response_model=UserInfoResponse)
def api_user_info(request: Request, flask_session: dict = Depends(get_flask_session)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "No has iniciado sesión", "is_authenticated": False})

    
    user = User.query.get(user_id)
    if not user:
         return JSONResponse(status_code=404, content={"error": "Usuario no encontrado", "is_authenticated": False})

    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'biography': user.biography,
        'linkedin_url': user.linkedin_url,
        'github_url': user.github_url,
        'youtube_url': user.youtube_url,
        'created_at': user.created_at,
        'profile_image_url': get_fastapi_profile_image_url(username=user.username, user_id=user.id)
    }

    completed_objs = CompletedMachine.query.filter_by(user_id=user_id).order_by(CompletedMachine.completed_at.desc()).all()
    completed_machines = [{'machine_name': c.machine_name, 'completed_at': c.completed_at} for c in completed_objs]

    writeups_objs = Writeup.query.filter_by(autor=user.username).order_by(Writeup.created_at.desc()).all()
    writeups = [{
        'id': w.id,
        'maquina': w.maquina,
        'autor': w.autor,
        'url': w.url,
        'tipo': w.tipo,
        'created_at': w.created_at
    } for w in writeups_objs]

    try:
        # Simular request sin cookies
        req = Request({
            'type': 'http', 
            'url': 'http://test.com/login',
            'method': 'GET',
            'headers': {}, 
            'cookies': {},
            'query_string': ''
        })
    except Exception as e:
        print(f"Error: {str(e)}")

    response = {
        "is_authenticated": True,
        "user": user_data,
        "completed_machines": completed_machines,
        "submitted_writeups": writeups
    }

    return response

@api_router.post("/submit-machine", response_model=SubmitMachineResponse)
async def api_submit_machine(request: Request, data: SubmitMachineRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})

    username = flask_session.get("username")

    from dockerlabs.models import PendingMachineSubmission

    sub = PendingMachineSubmission(
        nombre=data.nombre,
        link_maquina=data.link_maquina,
        dificultad=data.dificultad,
        categoria=data.categoria,
        tags=data.tags,
        descripcion=data.descripcion,
        notas=data.notas,
        writeup_url=data.writeup_url,
        discord_user=data.discord_user,
        autor_solicitante=username,
        estado="pendiente"
    )
    alchemy_db.session.add(sub)
    alchemy_db.session.commit()

    return {"success": True, "message": "Máquina enviada y pendiente de revisión"}

# --- Endpoints de Autenticación (Auth) ---

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    redirect_url: Optional[str] = None

def set_flask_session_cookie(existing_session: dict) -> str:
    serializer = get_session_serializer()
    return serializer.dumps(existing_session)

def create_flask_session_cookie(user_id: int, username: str, role: str = 'jugador', existing_session: dict = None) -> str:
    import hashlib
    import os
    
    session_data = existing_session or {}
    _id = hashlib.sha512(os.urandom(24)).hexdigest()
    
    session_data['_user_id'] = str(user_id)
    session_data['_fresh'] = True
    session_data['_id'] = _id
    session_data['user_id'] = user_id
    session_data['username'] = username
    session_data['role'] = role
    
    return set_flask_session_cookie(session_data)

@api_router.post("/auth/login", response_model=LoginResponse)
async def api_auth_login(request: Request, data: LoginRequest, flask_session: dict = Depends(get_flask_session)):
    
    user = User.query.filter_by(username=data.username.strip()).first()
    if user is None or not check_password_hash(user.password_hash, data.password):
        return JSONResponse(status_code=401, content={"success": False, "message": "Usuario o contraseña incorrectos."})
            
    cookie_val = create_flask_session_cookie(user.id, user.username, user.role, existing_session=flask_session)
        
    response = JSONResponse(content={"success": True, "redirect_url": "/dashboard"})
    # Configurar la cookie de sesión de manera compatible con Flask
    response.set_cookie(
        key="session", 
        value=cookie_val, 
        httponly=True,
        path="/",
        samesite="lax"
    )
    return response

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    password2: str
    terms: bool

class RegisterResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    recovery_pin: Optional[str] = None
    pending_message: Optional[str] = None

class RecoverRequest(BaseModel):
    username: str
    pin: str
    password: str
    password2: str

class RecoverResponse(BaseModel):
    success: bool
    message: Optional[str] = None

@api_router.post("/auth/register", response_model=RegisterResponse)
async def api_auth_register(request: Request, data: RegisterRequest):
    username = data.username.strip()
    email = data.email.strip()
    password = data.password
    password2 = data.password2
    terms_accepted = data.terms

    if not username or not email or not password:
        return JSONResponse(status_code=400, content={"success": False, "message": "Todos los campos son obligatorios."})
    if not terms_accepted:
        return JSONResponse(status_code=400, content={"success": False, "message": "Debes aceptar los Términos y Condiciones para registrarte."})
    if len(username) > 20:
        return JSONResponse(status_code=400, content={"success": False, "message": "El nombre de usuario no puede exceder 20 caracteres."})
    if len(email) > 35:
        return JSONResponse(status_code=400, content={"success": False, "message": "El correo electrónico no puede exceder 35 caracteres."})
    if password != password2:
        return JSONResponse(status_code=400, content={"success": False, "message": "Las contraseñas no coinciden."})
    
    # Validar complejidad de contraseña
    from dockerlabs import validators
    valid, pwd_error = validators.validate_password_complexity(password)
    if not valid:
        return JSONResponse(status_code=400, content={"success": False, "message": pwd_error})
    
    if '/' in username or '\\' in username or '..' in username or '.' in username:
        return JSONResponse(status_code=400, content={"success": False, "message": "El nombre de usuario no puede contener caracteres especiales como /, \\, o puntos."})
    if username.lower() in ['admin', 'root', 'system', 'default', 'balulero', 'default-profile', 'logo', 'pingu']:
        return JSONResponse(status_code=400, content={"success": False, "message": "Este nombre de usuario está reservado por el sistema."})
    if not re.match(r'^[A-Za-z0-9_-]+$', username):
        return JSONResponse(status_code=400, content={"success": False, "message": "El nombre de usuario solo puede contener letras, números, guiones y guiones bajos."})


    pwd_hash = generate_password_hash(password)
    existing = User.query.filter((User.username == username) | (User.email == email)).first()
    if existing:
        return JSONResponse(status_code=400, content={"success": False, "message": "El usuario o el correo ya están registrados."})

    auth_conflict = False
    if Machine.query.filter_by(autor=username).first(): auth_conflict = True
    elif Writeup.query.filter_by(autor=username).first(): auth_conflict = True
    elif PendingWriteup.query.filter_by(autor=username).first(): auth_conflict = True

    if auth_conflict:
        try:
            claim = NameClaim(
                username=username,
                email=email,
                password_hash=pwd_hash,
                nombre_solicitado=username,
                nombre_actual=username,
                motivo="Solicitud de registro con nombre coincidente con autor de máquina o writeup.",
                estado='pendiente'
            )
            alchemy_db.session.add(claim)
            alchemy_db.session.commit()
            msg = "Tu solicitud de registro se ha enviado para revisión. El nombre de usuario coincide con el de un autor de máquina o writeup, y deberá ser aprobado por un administrador o moderador."
            return {"success": True, "pending_message": msg}
        except Exception:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"success": False, "message": "Error al registrar la solicitud."})
    else:
        try:
            new_user = User(username=username, email=email, password_hash=pwd_hash, role='jugador')
            import string
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            pin = ''.join(secrets.choice(alphabet) for i in range(15))
            pin_hash = generate_password_hash(pin)
                
            new_user.recovery_pin_hash = pin_hash
            # SECURITY WARNING: recovery_pin_plain se almacena en texto plano por compatibilidad.
            # Debería eliminarse en una migración futura de base de datos.
            # El PIN solo se muestra una vez al usuario después del registro.
            new_user.recovery_pin_plain = pin
            new_user.recovery_pin_created_at = datetime.utcnow()
                
            alchemy_db.session.add(new_user)
            alchemy_db.session.commit()
            return {"success": True, "recovery_pin": pin}
        except IntegrityError:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=400, content={"success": False, "message": "El usuario o el correo ya están registrados."})
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"success": False, "message": f"Error al crear usuario: {str(e)}"})


@api_router.post("/auth/recover", response_model=RecoverResponse)
async def api_auth_recover(request: Request, data: RecoverRequest, csrf_ok: bool = Depends(verify_csrf_token)):
    username = data.username.strip()
    pin = data.pin.strip()
    password = data.password
    password2 = data.password2

    if not username or not pin or not password:
        return JSONResponse(status_code=400, content={"success": False, "message": "Todos los campos son obligatorios."})
    if password != password2:
        return JSONResponse(status_code=400, content={"success": False, "message": "Las contraseñas no coinciden."})
    
    # Validar complejidad de contraseña
    from dockerlabs import validators
    valid, pwd_error = validators.validate_password_complexity(password)
    if not valid:
        return JSONResponse(status_code=400, content={"success": False, "message": pwd_error})


    user_obj = User.query.filter_by(username=username).first()
    if not user_obj:
        return JSONResponse(status_code=400, content={"success": False, "message": "Usuario no encontrado."})
    if not user_obj.recovery_pin_hash:
        return JSONResponse(status_code=400, content={"success": False, "message": "No hay un PIN de recuperación registrado para este usuario. Regístrate nuevamente o contacta al soporte."})
    if not check_password_hash(user_obj.recovery_pin_hash, pin):
        return JSONResponse(status_code=400, content={"success": False, "message": "PIN incorrecto."})
        
    if user_obj.recovery_pin_created_at:
         new_pwd_hash = generate_password_hash(password)
         user_obj.password_hash = new_pwd_hash
         user_obj.recovery_pin_hash = None
         user_obj.recovery_pin_created_at = None
         alchemy_db.session.commit()
         return {"success": True, "message": "Contraseña actualizada correctamente."}
    else:
         return JSONResponse(status_code=400, content={"success": False, "message": "Error en la fecha de emisión del PIN. Contacta al soporte."})

# --- Endpoints de Gestión de Perfil (Profile) ---

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class UpdateProfileRequest(BaseModel):
    email: str
    biography: Optional[str] = None

class UpdateSocialLinksRequest(BaseModel):
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    youtube_url: Optional[str] = None

@api_router.post("/change_password")
async def api_change_password(request: Request, data: ChangePasswordRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})
        
    if data.new_password != data.confirm_password:
        return JSONResponse(status_code=400, content={"error": "Las contraseñas nuevas no coinciden."})
    
    # Validar complejidad de contraseña
    from dockerlabs import validators
    valid, pwd_error = validators.validate_password_complexity(data.new_password)
    if not valid:
        return JSONResponse(status_code=400, content={"error": pwd_error})

    
    user_obj = User.query.get(user_id)
    if not user_obj:
        return JSONResponse(status_code=404, content={"error": "Usuario no encontrado."})
            
    if not check_password_hash(user_obj.password_hash, data.current_password):
        return JSONResponse(status_code=400, content={"error": "La contraseña actual es incorrecta."})
            
    user_obj.password_hash = generate_password_hash(data.new_password)
    alchemy_db.session.commit()
    return {"message": "Contraseña actualizada correctamente.", "success": True}

@api_router.post("/update_profile")
async def api_update_profile(request: Request, data: UpdateProfileRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})
        
    if not data.email.strip():
        return JSONResponse(status_code=400, content={"error": "El email es obligatorio."})
    
    # Sanitizar inputs
    from dockerlabs import validators
    email_sanitized = validators.sanitize_text(data.email.strip())
    biography_sanitized = validators.sanitize_text(data.biography.strip()) if data.biography else ""

    
    user_obj = User.query.get(user_id)
    if not user_obj:
        return JSONResponse(status_code=404, content={"error": "Usuario no encontrado."})
            
    user_obj.email = email_sanitized
    user_obj.biography = biography_sanitized
    alchemy_db.session.commit()
    return {"message": "Perfil actualizado correctamente.", "success": True}

@api_router.post("/update_social_links")
async def api_update_social_links(request: Request, data: UpdateSocialLinksRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})

    # Sanitizar inputs
    from dockerlabs import validators
    linkedin_sanitized = validators.sanitize_text(data.linkedin_url.strip()) if data.linkedin_url else ""
    github_sanitized = validators.sanitize_text(data.github_url.strip()) if data.github_url else ""
    youtube_sanitized = validators.sanitize_text(data.youtube_url.strip()) if data.youtube_url else ""
    
    user_obj = User.query.get(user_id)
    if not user_obj:
        return JSONResponse(status_code=404, content={"error": "Usuario no encontrado."})
            
    user_obj.linkedin_url = linkedin_sanitized
    user_obj.github_url = github_sanitized
    user_obj.youtube_url = youtube_sanitized
        
    alchemy_db.session.commit()
    return {"message": "Enlaces de redes sociales actualizados correctamente.", "success": True}

from fastapi import UploadFile, File

@api_router.post("/upload-profile-photo")
async def api_upload_profile_photo(
    request: Request,
    photo: UploadFile = File(...),
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})

    if not photo or not photo.filename:
        return JSONResponse(status_code=400, content={"error": "No se ha enviado ningún archivo"})

    if not photo.content_type.startswith('image/'):
        return JSONResponse(status_code=400, content={"error": "El archivo debe ser una imagen"})

    file_bytes = await photo.read()
    MAX_UPLOAD_BYTES = 5 * 1024 * 1024
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        return JSONResponse(status_code=400, content={"error": "La imagen es demasiado grande (máx 5MB)"})

    from PIL import Image
    import io
    import logging
    from werkzeug.utils import secure_filename
    from dockerlabs import validators

    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()
    except Exception as exc:
        logging.exception("Verificación de imagen fallida")
        return JSONResponse(status_code=400, content={"error": "La imagen enviada no es válida"})

    original_filename = secure_filename(photo.filename or '')
    _, ext = os.path.splitext(original_filename)
    ext = ext.lower()
    
    ALLOWED_PROFILE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
    if ext not in ALLOWED_PROFILE_EXTENSIONS:
        return JSONResponse(status_code=400, content={"error": "Formato de imagen no permitido"})

    valid, error = validators.validate_image_content(io.BytesIO(file_bytes))
    if not valid:
        return JSONResponse(status_code=400, content={"error": f"Archivo inválido: {error}"})

    ext_to_mime = {
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.png': 'image/png', '.gif': 'image/gif', '.webp': 'image/webp'
    }
    mime_type = ext_to_mime.get(ext, 'image/jpeg')

    import time
    
    user_obj = User.query.get(user_id)
    if not user_obj:
        return JSONResponse(status_code=400, content={"error": "No se ha podido determinar el usuario"})

    # Guardar imagen en disco en database/almacenamiento/perfiles
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    almacenamiento_dir = os.path.join(BASE_DIR, 'database', 'almacenamiento', 'perfiles')
    os.makedirs(almacenamiento_dir, exist_ok=True)
    
    ts = int(time.time())
    filename = f"user_{user_id}_{ts}{ext}"
    file_path = os.path.join(almacenamiento_dir, filename)
    
    try:
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
        
        # Guardar ruta en BD y limpiar datos binarios antiguos
        user_obj.profile_image_path = f"database/almacenamiento/perfiles/{filename}"
        user_obj.profile_image_data = None
        user_obj.profile_image_mime = mime_type
        alchemy_db.session.commit()
    except Exception as exc:
        logging.exception("Error al guardar la foto de perfil en disco")
        alchemy_db.session.rollback()
        return JSONResponse(status_code=500, content={"error": "Error al guardar la imagen en el servidor"})

    image_url = f"/img/perfil/{user_id}?t={ts}"

    return {
        'message': 'Foto de perfil actualizada correctamente.',
        'image_url': image_url
    }

# --- Endpoints de Administración ---

class UpdateRoleRequest(BaseModel):
    role: str

class RequestUsernameChangeRequest(BaseModel):
    requested_username: str
    reason: Optional[str] = None
    contacto_opcional: Optional[str] = None

class RejectUsernameChangeRequest(BaseModel):
    decision_reason: Optional[str] = "Rechazado por moderador/admin"

@api_router.post("/admin/update_user_role/{user_id}")
async def api_update_user_role(request: Request, user_id: int, data: UpdateRoleRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_id = flask_session.get('user_id')
    caller_role = flask_session.get('role', '').lower()
    
    # Debug logging
    print(f"DEBUG: caller_id={caller_id}, caller_role={caller_role}")
    
    if not caller_id or caller_role not in ('admin', 'moderador', 'moderator'):
        print(f"DEBUG: Access denied - caller_role not in allowed roles")
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    nuevo_rol = data.role.strip().lower()
    if nuevo_rol not in ('jugador', 'moderador', 'moderator', 'admin'):
        return JSONResponse(status_code=400, content={"error": "Rol inválido"})

    # Los moderadores no pueden asignar rol de admin
    if caller_role in ('moderador', 'moderator') and nuevo_rol == 'admin':
        return JSONResponse(status_code=403, content={"error": "Los moderadores no pueden asignar rol de admin"})

    user = User.query.get(user_id)
    if not user:
        return JSONResponse(status_code=404, content={"error": "Usuario no encontrado"})
    user.role = nuevo_rol
    alchemy_db.session.commit()
    return {"message": f"Rol de {user.username} actualizado a {nuevo_rol}", "success": True}

@api_router.post("/admin/delete_user/{user_id}")
async def api_delete_user(request: Request, user_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_id = flask_session.get('user_id')
    caller_role = flask_session.get('role', '')
    if not caller_id or caller_role not in ('admin',):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    if caller_id == user_id:
        return JSONResponse(status_code=400, content={"error": "No puedes eliminar tu propia cuenta desde aquí."})


    user = User.query.get(user_id)
    if not user:
        return JSONResponse(status_code=404, content={"error": "Usuario no encontrado."})
    if user.role == 'admin':
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count <= 1:
            return JSONResponse(status_code=400, content={"error": "No se puede eliminar al último administrador."})
    try:
        alchemy_db.session.delete(user)
        alchemy_db.session.commit()
        return {"message": "Usuario eliminado correctamente.", "success": True}
    except Exception as e:
        alchemy_db.session.rollback()
        return JSONResponse(status_code=500, content={"error": f"Error al eliminar el usuario: {str(e)}"})

@api_router.post("/auth/request_username_change")
async def api_request_username_change(request: Request, data: RequestUsernameChangeRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    import re as _re
    user_id = flask_session.get('user_id')
    old_username = flask_session.get('username')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión."})

    requested_username = data.requested_username.strip()
    reason = (data.reason or '').strip()
    contacto_opcional = (data.contacto_opcional or '').strip()

    if not requested_username:
        return JSONResponse(status_code=400, content={"error": "Debes escribir un nombre nuevo."})
    if len(requested_username) > 20:
        return JSONResponse(status_code=400, content={"error": "El nombre de usuario no puede exceder 20 caracteres."})
    if not _re.match(r'^[A-Za-z0-9_\-]{3,20}$', requested_username):
        return JSONResponse(status_code=400, content={"error": "El nombre debe tener entre 3 y 20 caracteres y solo letras, números, guion y guion bajo."})

    from dockerlabs.models import User, UsernameChangeRequest

    if User.query.filter_by(username=requested_username).first():
        return JSONResponse(status_code=400, content={"error": "Ese nombre ya está en uso."})
    try:
        new_req = UsernameChangeRequest(
            user_id=user_id,
            old_username=old_username,
            requested_username=requested_username,
            reason=reason,
            contacto_opcional=contacto_opcional,
            estado='pendiente'
        )
        alchemy_db.session.add(new_req)
        alchemy_db.session.commit()
        return {"message": "Solicitud enviada. Un moderador o admin deberá aprobarla.", "success": True}
    except Exception:
        alchemy_db.session.rollback()
        return JSONResponse(status_code=500, content={"error": "Error al procesar la solicitud."})

@api_router.post("/admin/approve_username_change/{request_id}")
async def api_approve_username_change(request: Request, request_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_id = flask_session.get('user_id')
    caller_role = flask_session.get('role', '')
    if not caller_id or caller_role not in ('admin',):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import User, UsernameChangeRequest, Writeup, PendingWriteup, WriteupRanking, CreatorRanking
    from sqlalchemy import func

    req = UsernameChangeRequest.query.get(request_id)
    if not req:
        return JSONResponse(status_code=404, content={"error": "Petición no encontrada."})
    if req.estado != 'pendiente':
        return JSONResponse(status_code=400, content={"error": "Esta petición ya fue procesada."})

    requested_username = req.requested_username
    existing_user = User.query.filter(User.username == requested_username, User.id != req.user_id).first()
    if existing_user:
        req.estado = 'rechazada'
        req.processed_by = caller_id
        req.processed_at = datetime.utcnow()
        req.decision_reason = 'Nombre ya en uso al aprobar'
        alchemy_db.session.commit()
        return JSONResponse(status_code=400, content={"error": "El nombre ya está en uso. No se pudo aprobar."})

    conflict_count = Writeup.query.filter(func.lower(Writeup.autor) == func.lower(requested_username)).count()
    decision_reason = f'Aprobado con conflicto: {conflict_count} writeup(s)' if conflict_count > 0 else 'Aprobado por admin'

    user = User.query.get(req.user_id)
    if user:
        user.username = requested_username

    if conflict_count == 0:
        try:
            old_lower = req.old_username.lower()
            Writeup.query.filter(func.lower(Writeup.autor) == old_lower).update({Writeup.autor: requested_username}, synchronize_session=False)
            PendingWriteup.query.filter(func.lower(PendingWriteup.autor) == old_lower).update({PendingWriteup.autor: requested_username}, synchronize_session=False)
            WriteupRanking.query.filter(func.lower(WriteupRanking.nombre) == old_lower).update({WriteupRanking.nombre: requested_username}, synchronize_session=False)
            CreatorRanking.query.filter(func.lower(CreatorRanking.nombre) == old_lower).update({CreatorRanking.nombre: requested_username}, synchronize_session=False)
            alchemy_db.session.commit()
            try:
                from dockerlabs.writeups import recalcular_ranking_writeups
                recalcular_ranking_writeups()
            except Exception:
                pass
        except Exception:
            alchemy_db.session.rollback()

    req.estado = 'aprobada'
    req.processed_by = caller_id
    req.processed_at = datetime.utcnow()
    req.decision_reason = decision_reason
    alchemy_db.session.commit()

    msg = f"Nombre cambiado correctamente a {requested_username}."
    if conflict_count > 0:
        msg = f"Nombre cambiado pero existe conflicto con {conflict_count} writeup(s)."
    return {"message": msg, "success": True, "conflict_count": conflict_count}

@api_router.post("/admin/reject_username_change/{request_id}")
async def api_reject_username_change(request: Request, request_id: int, data: RejectUsernameChangeRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_id = flask_session.get('user_id')
    caller_role = flask_session.get('role', '')
    if not caller_id or caller_role not in ('admin',):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import UsernameChangeRequest

    req = UsernameChangeRequest.query.get(request_id)
    if not req:
        return JSONResponse(status_code=404, content={"error": "Petición no encontrada."})
    req.estado = 'rechazada'
    req.processed_by = caller_id
    req.processed_at = datetime.utcnow()
    req.decision_reason = data.decision_reason
    alchemy_db.session.commit()
    return {"message": "Petición rechazada correctamente.", "success": True}

@api_router.post("/admin/revert_username_change/{request_id}")
async def api_revert_username_change(request: Request, request_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_id = flask_session.get('user_id')
    caller_role = flask_session.get('role', '')
    if not caller_id or caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import UsernameChangeRequest

    req = UsernameChangeRequest.query.get(request_id)
    if not req:
        return JSONResponse(status_code=404, content={"error": "Petición no encontrada."})
    req.estado = 'pendiente'
    req.processed_by = None
    req.processed_at = None
    req.decision_reason = None
    alchemy_db.session.commit()
    return {"message": "Petición revertida a pendiente.", "success": True}

# ─────────────────────────────────────────────────────────────────
# Fase 9 – APIs JSON de Máquinas (maquinas.py) + Nombre-Claims (app.py)
# ─────────────────────────────────────────────────────────────────

class RateMachineRequest(BaseModel):
    maquina_nombre: str
    dificultad_score: float
    aprendizaje_score: float
    recomendaria_score: float
    diversion_score: float

class ToggleCompletedRequest(BaseModel):
    machine_name: str

# ── Toggle Guest Access ──────────────────────────────────────────
@api_router.post("/gestion-maquinas/toggle-guest-access")
def api_toggle_guest_access(
    request: Request,
    machine_id: int,
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import Machine

    maquina = Machine.query.get(machine_id)
    if not maquina:
        return JSONResponse(status_code=404, content={"error": "Máquina no encontrada"})
    maquina.guest_access = not maquina.guest_access
    alchemy_db.session.commit()
    return {"message": "Estado actualizado", "guest_access": maquina.guest_access}

# ── Upload Machine Logo ──────────────────────────────────────────
@api_router.post("/gestion-maquinas/upload-logo")
async def api_upload_machine_logo(
    request: Request,
    logo: UploadFile = File(...),
    machine_id: int = 0,
    origen: str = "docker",
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    if not logo or not logo.filename:
        return JSONResponse(status_code=400, content={"error": "No se ha enviado ningún archivo"})
    if not logo.content_type.startswith('image/'):
        return JSONResponse(status_code=400, content={"error": "El archivo debe ser una imagen"})

    file_bytes = await logo.read()
    if len(file_bytes) > 2 * 1024 * 1024:
        return JSONResponse(status_code=400, content={"error": "La imagen es demasiado grande (máx 2MB)"})

    from PIL import Image
    import io as _io, os as _os
    from werkzeug.utils import secure_filename
    from dockerlabs import validators

    try:
        img = Image.open(_io.BytesIO(file_bytes))
        img.verify()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "La imagen enviada no es válida"})

    valid, err = validators.validate_image_content(_io.BytesIO(file_bytes))
    if not valid:
        return JSONResponse(status_code=400, content={"error": f"Imagen inválida: {err}"})

    original_filename = secure_filename(logo.filename or '')
    _, ext = _os.path.splitext(original_filename)
    ext = ext.lower()
    ALLOWED = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
    if ext not in ALLOWED:
        return JSONResponse(status_code=400, content={"error": "Formato de imagen no permitido"})

    ext_to_mime = {
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
        '.gif': 'image/gif', '.webp': 'image/webp', '.svg': 'image/svg+xml'
    }
    logo_mime = ext_to_mime.get(ext, 'image/jpeg')

    from dockerlabs.models import Machine

    maq = Machine.query.get(machine_id)
    if not maq:
        return JSONResponse(status_code=404, content={"error": "Máquina no encontrada"})

    # Guardar imagen en disco en database/almacenamiento/logos
    BASE_DIR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
    almacenamiento_dir = _os.path.join(BASE_DIR, 'database', 'almacenamiento', 'logos')
    _os.makedirs(almacenamiento_dir, exist_ok=True)
    
    if origen == 'bunker':
        nombre_seguro = secure_filename(maq.nombre)
        final_filename = f"bunker_{nombre_seguro}{ext}"
    else:
        ts = int(_time.time())
        final_filename = f"docker_{machine_id}_{ts}{ext}"
    
    file_path = _os.path.join(almacenamiento_dir, final_filename)

    try:
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
        
        # Guardar ruta en BD y limpiar datos binarios antiguos
        maq.logo_path = f"database/almacenamiento/logos/{final_filename}"
        maq.logo_data = None
        maq.logo_mime = logo_mime
        alchemy_db.session.commit()
    except Exception as e:
        alchemy_db.session.rollback()
        return JSONResponse(status_code=500, content={"error": str(e)})

    return {
        "message": "Logo subido correctamente",
        "filename": final_filename,
        "image_url": f"/img/maquina/{machine_id}"
    }

# ── Get Users (admin autocomplete) ──────────────────────────────
@api_router.get("/get_users")
def api_get_users(request: Request, flask_session: dict = Depends(get_flask_session)):
    caller_role = flask_session.get('role', '')
    if caller_role != 'admin':
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})


    users = User.query.order_by(User.username.asc()).all()
    return {"users": [{"id": u.id, "username": u.username} for u in users]}

# ── Rate Machine ─────────────────────────────────────────────────
@api_router.post("/rate_machine")
def api_rate_machine(request: Request, data: RateMachineRequest, flask_session: dict = Depends(get_flask_session)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión para puntuar"})

    scores = [data.dificultad_score, data.aprendizaje_score, data.recomendaria_score, data.diversion_score]
    if any(s < 1 or s > 5 for s in scores):
        return JSONResponse(status_code=400, content={"success": False, "message": "Las puntuaciones deben estar entre 1 y 5"})

    from dockerlabs.models import Rating

    try:
        existing = Rating.query.filter_by(usuario_id=user_id, maquina_nombre=data.maquina_nombre).first()
        if existing:
            existing.dificultad_score = data.dificultad_score
            existing.aprendizaje_score = data.aprendizaje_score
            existing.recomendaria_score = data.recomendaria_score
            existing.diversion_score = data.diversion_score
            existing.fecha = datetime.utcnow()
        else:
            from dockerlabs.models import Rating as RatingModel
            new_rating = RatingModel(
                usuario_id=user_id,
                maquina_nombre=data.maquina_nombre,
                dificultad_score=data.dificultad_score,
                aprendizaje_score=data.aprendizaje_score,
                recomendaria_score=data.recomendaria_score,
                diversion_score=data.diversion_score
            )
            alchemy_db.session.add(new_rating)
        alchemy_db.session.commit()
        return {"success": True, "message": "Puntuación guardada correctamente"}
    except Exception as e:
        alchemy_db.session.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

# ── Get Machine Rating ───────────────────────────────────────────
@api_router.get("/get_machine_rating/{maquina_nombre}")
def api_get_machine_rating(request: Request, maquina_nombre: str, flask_session: dict = Depends(get_flask_session)):
    from dockerlabs.models import Rating
    from sqlalchemy import func

    avg_result = alchemy_db.session.query(
        func.avg(Rating.dificultad_score).label('avg_dificultad'),
        func.avg(Rating.aprendizaje_score).label('avg_aprendizaje'),
        func.avg(Rating.recomendaria_score).label('avg_recomendaria'),
        func.avg(Rating.diversion_score).label('avg_diversion'),
        func.count(Rating.id).label('count')
    ).filter_by(maquina_nombre=maquina_nombre).first()

    user_id = flask_session.get('user_id')
    user_rating = None
    if user_id:
        user_result = Rating.query.filter_by(usuario_id=user_id, maquina_nombre=maquina_nombre).first()
        if user_result:
            user_rating = {
                'dificultad': user_result.dificultad_score,
                'aprendizaje': user_result.aprendizaje_score,
                'recomendaria': user_result.recomendaria_score,
                'diversion': user_result.diversion_score
            }

    count = avg_result.count if avg_result else 0
    total_avg = 0
    if count > 0:
        criteria_sum = ((avg_result.avg_dificultad or 0) + (avg_result.avg_aprendizaje or 0) +
                        (avg_result.avg_recomendaria or 0) + (avg_result.avg_diversion or 0))
        total_avg = criteria_sum / 4

    return {
        'average': round(total_avg, 1),
        'count': count,
        'details': {
            'dificultad': round(avg_result.avg_dificultad or 0, 1) if count > 0 else 0,
            'aprendizaje': round(avg_result.avg_aprendizaje or 0, 1) if count > 0 else 0,
            'recomendaria': round(avg_result.avg_recomendaria or 0, 1) if count > 0 else 0,
            'diversion': round(avg_result.avg_diversion or 0, 1) if count > 0 else 0
        },
        'user_rating': user_rating
    }

# ── Completed Machines ───────────────────────────────────────────
@api_router.get("/completed_machines/{machine_name}")
def api_get_completed_machines(request: Request, machine_name: str, flask_session: dict = Depends(get_flask_session)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    from dockerlabs.models import CompletedMachine

    completed = CompletedMachine.query.filter_by(user_id=user_id, machine_name=machine_name).first()
    return {"completed": completed is not None}

@api_router.post("/toggle_completed_machine")
async def api_toggle_completed_machine(request: Request, data: ToggleCompletedRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Not authenticated", "success": False})

    machine_name = data.machine_name.strip()
    if not machine_name:
        return JSONResponse(status_code=400, content={"error": "Machine name required", "success": False})

    from dockerlabs.models import Machine, CompletedMachine

    if not Machine.query.filter_by(nombre=machine_name).first():
        return JSONResponse(status_code=400, content={"error": "Máquina no válida", "success": False})

    existing = CompletedMachine.query.filter_by(user_id=user_id, machine_name=machine_name).first()
    if existing:
        alchemy_db.session.delete(existing)
        alchemy_db.session.commit()
        return {"success": True, "completed": False}
    else:
        new_comp = CompletedMachine(user_id=user_id, machine_name=machine_name)
        alchemy_db.session.add(new_comp)
        alchemy_db.session.commit()
        return {"success": True, "completed": True}

# ── Nombre-Claims (app.py) ───────────────────────────────────────
@api_router.post("/admin/nombre-claims/{claim_id}/approve")
async def api_approve_nombre_claim(request: Request, claim_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import NameClaim, User

    claim = NameClaim.query.get(claim_id)
    if not claim:
        return JSONResponse(status_code=404, content={"error": "Claim no encontrado"})

    existing = User.query.filter(
        (User.username == claim.nombre_solicitado) | (User.email == claim.email)
    ).first()
    if existing:
        claim.estado = 'rechazada'
        alchemy_db.session.commit()
        return JSONResponse(status_code=400, content={"error": "El nombre o email ya está en uso. Claim rechazado automáticamente."})

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
        return {"message": f"Claim aprobado. Usuario '{claim.nombre_solicitado}' creado.", "success": True}
    except IntegrityError:
        alchemy_db.session.rollback()
        claim.estado = 'rechazada'
        alchemy_db.session.commit()
        return JSONResponse(status_code=400, content={"error": "Error de integridad. Claim rechazado."})
    except Exception as e:
        alchemy_db.session.rollback()
        return JSONResponse(status_code=500, content={"error": str(e)})

@api_router.post("/admin/nombre-claims/{claim_id}/reject")
async def api_reject_nombre_claim(request: Request, claim_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import NameClaim

    claim = NameClaim.query.get(claim_id)
    if not claim:
        return JSONResponse(status_code=404, content={"error": "Claim no encontrado"})
    claim.estado = 'rechazada'
    alchemy_db.session.commit()
    return {"message": "Claim rechazado.", "success": True}

@api_router.post("/admin/nombre-claims/{claim_id}/revert")
async def api_revert_nombre_claim(request: Request, claim_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import NameClaim

    claim = NameClaim.query.get(claim_id)
    if not claim:
        return JSONResponse(status_code=404, content={"error": "Claim no encontrado"})
    claim.estado = 'pendiente'
    alchemy_db.session.commit()
    return {"message": "Claim revertido a pendiente.", "success": True}

def require_auth_and_role(flask_session: dict, allowed_roles: list):
    """Helper para verificar autenticación y roles."""
    user_id = flask_session.get('user_id')
    role = flask_session.get('role', '')
    if not user_id:
        return False, RedirectResponse(url="/login", status_code=302)
    if role not in allowed_roles:
        return False, RedirectResponse(url="/", status_code=302)
    return True, None


from dockerlabs.routes.notifications import register_notification_routes
from dockerlabs.routes.messaging import register_messaging_routes
from dockerlabs.routes.writeups import register_writeup_routes
from dockerlabs.routes.bunker_api import register_bunker_api_routes
from dockerlabs.routes.images import register_image_routes
from dockerlabs.routes.pending_admin import register_pending_admin_routes
from dockerlabs.routes.pages_admin import register_pages_admin_routes
from dockerlabs.routes.pages_core import register_pages_core_routes

register_notification_routes(
    api_router=api_router,
    get_flask_session=get_flask_session,
    alchemy_db=alchemy_db,
)

register_messaging_routes(
    api_router=api_router,
    get_flask_session=get_flask_session,
    verify_csrf_token=verify_csrf_token,
    alchemy_db=alchemy_db,
)

register_writeup_routes(
    api_router=api_router,
    get_flask_session=get_flask_session,
    verify_csrf_token=verify_csrf_token,
    alchemy_db=alchemy_db,
)

register_bunker_api_routes(
    api_router=api_router,
    get_flask_session=get_flask_session,
    verify_csrf_token=verify_csrf_token,
    alchemy_db=alchemy_db,
)

register_pending_admin_routes(
    api_router=api_router,
    get_flask_session=get_flask_session,
    verify_csrf_token=verify_csrf_token,
    alchemy_db=alchemy_db,
)


from dockerlabs.routes.machines import register_machine_routes


from dockerlabs.routes.auth_forms import register_auth_form_routes
from dockerlabs.routes.bunkerlabs_pages import register_bunkerlabs_pages_routes

register_auth_form_routes(
    pages_router=pages_router,
    get_flask_session=get_flask_session,
    verify_csrf_token=verify_csrf_token,
    set_flask_session_cookie=set_flask_session_cookie,
    alchemy_db=alchemy_db,
)

register_bunkerlabs_pages_routes(
    pages_router=pages_router,
    get_flask_session=get_flask_session,
    verify_csrf_token=verify_csrf_token,
    require_auth_and_role=require_auth_and_role,
    set_flask_session_cookie=set_flask_session_cookie,
    templates=templates,
    alchemy_db=alchemy_db,
)

register_machine_routes(
    api_router=api_router,
    pages_router=pages_router,
    get_flask_session=get_flask_session,
    verify_csrf_token=verify_csrf_token,
    require_auth_and_role=require_auth_and_role,
    set_flask_session_cookie=set_flask_session_cookie,
    templates=templates,
    alchemy_db=alchemy_db,
)

register_pages_admin_routes(
    pages_router=pages_router,
    get_flask_session=get_flask_session,
    verify_csrf_token=verify_csrf_token,
    require_auth_and_role=require_auth_and_role,
    set_flask_session_cookie=set_flask_session_cookie,
    templates=templates,
    generate_csrf_token=generate_csrf_token,
    url_for=url_for,
    alchemy_db=alchemy_db,
)

register_pages_core_routes(
    pages_router=pages_router,
    get_flask_session=get_flask_session,
    create_flask_session_cookie=create_flask_session_cookie,
    get_fastapi_profile_image_url=get_fastapi_profile_image_url,
    url_for=url_for,
    templates=templates,
    alchemy_db=alchemy_db,
)

register_image_routes(
    api_router=api_router,
    pages_router=pages_router,
)
