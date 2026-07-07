from fastapi import APIRouter, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import secrets
import re
import os
import io
import logging
import time
from PIL import Image

from dockerlabs.models import (
    User, Machine, Writeup, PendingMachineSubmission,
    CreatorRanking, WriteupRanking, PendingWriteup, NameClaim,
    UsernameChangeRequest, CompletedMachine, Rating,
    EmailVerificationToken, PasswordResetToken, SessionConfig,
)
from dockerlabs.extensions import db
from werkzeug.security import check_password_hash as _werkzeug_check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

_FLASK_TO_FASTAPI = {
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
        'bunkerlabs.accesos_bunkerlabs': '/bunkerlabs/gestion',
        'bunkerlabs.gestion_bunkerlabs': '/bunkerlabs/gestion',
        'bunkerlabs.bunkerlabs_recursos': '/bunkerlabs/recursos',
        'bunkerlabs.delete_bunker_token': '/bunkerlabs/gestion/{token_id}/delete',
        # Páginas principales
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
        'main.pending_machines': '/pending-machines',
        'main.user_pending_machines': '/user-pending',
        'main.approve_machine': '/api/admin/pending-machines/{machine_id}/approve',
        'main.reject_machine': '/api/admin/pending-machines/{machine_id}/reject',
        'main.bug_bounty': '/bug-bounty',
        # Máquinas
        'maquinas.maquinas_hechas': '/maquinas-hechas',
        'maquinas.gestion_maquinas': '/gestion-maquinas',
        'maquinas.add_maquina_page': '/add-maquina',
        'maquinas.actualizar_maquina': '/api/gestion-maquinas/actualizar',
        'maquinas.eliminar_maquina': '/api/gestion-maquinas/eliminar',
        'maquinas.serve_machine_logo': '/img/maquina/{machine_id}',
        # Writeups
        'writeups.writeups_publicados': '/writeups-publicados',
        'writeups.writeups_recibidos': '/writeups-recibidos',
        'writeups.writeups_analisis': '/writeups-analisis',
        # Auth API
        'auth.request_username_change': '/api/auth/request_username_change',
        # Máquinas claims
        'maquinas.approve_claim': '/api/claims/{claim_id}/approve',
        'maquinas.reject_claim': '/api/claims/{claim_id}/reject',
        'maquinas.reclamar_maquina': '/api/reclamar-maquina',
        # Misc
        'dashboard': '/dashboard',
        'index': '/',
        'peticiones': '/peticiones',
    }



def url_for(endpoint, **kwargs):
    """Genera la URL para un endpoint dado, compatible con las plantillas Jinja2."""
    if endpoint == 'static':
        filename = kwargs.get('filename', '')
        return f"/static/{filename}"
    if endpoint in _FLASK_TO_FASTAPI:
        path = _FLASK_TO_FASTAPI[endpoint]
        # Sustituir parámetros dinámicos {param} con los kwargs recibidos
        used_keys = set()
        def replace_param(match, _kw=kwargs):
            key = match.group(1)
            used_keys.add(key)
            return str(_kw.get(key, match.group(0)))
        path = re.sub(r'\{(\w+)\}', replace_param, path)
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

# Añadir el año actual como variable global en todas las plantillas
def get_current_year():
    return datetime.now().year

templates.env.globals['current_year'] = get_current_year

# Modelos de petición/respuesta

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

# Variable global para la clave de sesión (se inicializa lazy)
_session_secret_key = None

def get_session_secret_key():
    """Obtiene la clave de sesión desde la base de datos (lazy initialization)."""
    global _session_secret_key
    if _session_secret_key is None:
        _session_secret_key = SessionConfig.get_or_create_secret_key()
    return _session_secret_key

def get_session_serializer():
    return URLSafeTimedSerializer(get_session_secret_key(), salt='cookie-session')

def compute_csrf_token(session_id) -> str:
    """Token CSRF stateless: HMAC-SHA256(clave_de_sesión, _id).
    Es determinista a partir del id de sesión, así que no necesita
    persistirse en la cookie; el meta-tag y la verificación calculan el mismo."""
    import hmac, hashlib
    secret = get_session_secret_key()
    if isinstance(secret, str):
        secret = secret.encode()
    return hmac.new(secret, str(session_id).encode(), hashlib.sha256).hexdigest()

def get_session(request: Request) -> dict:
    """Extrae y valida la sesión del usuario desde la cookie firmada."""
    cookie = request.cookies.get("session")
    if not cookie:
        return {}

    serializer = get_session_serializer()
    try:
        data = serializer.loads(cookie, max_age=2592000)  # 30 días
        d = dict(data) if isinstance(data, dict) else {}
        # CSRF stateless: el token se deriva del _id de sesión de forma
        # determinista (no depende de que la cookie lo persista).
        sid = d.get("_id")
        if sid:
            d["csrf_token"] = compute_csrf_token(sid)
        return d
    except Exception as e:
        # Log para diagnosticar problemas de sesión (pero no exponer detalles al cliente)
        logger = logging.getLogger(__name__)
        logger.debug(f"Error al deserializar sesión: {type(e).__name__}")
        return {}

async def verify_csrf_token(request: Request, session: dict = Depends(get_session)):
    """Verifica el token CSRF en peticiones de escritura."""
    if request.method not in ("POST", "PUT", "DELETE", "PATCH"):
        return True

    session_token = session.get("csrf_token")
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
    """Devuelve la URL de imagen de perfil del usuario."""
    if user_id:
        return f"/img/perfil/{user_id}"
    if username:
        user = User.query.filter_by(username=username).first()
        if user:
            return f"/img/perfil/{user.id}"
    return "/static/dockerlabs/images/balu.webp"

# Añadir get_profile_image_url a los globals de Jinja2 después de definir la función
templates.env.globals['get_profile_image_url'] = get_fastapi_profile_image_url

# Cache-busting automático: fingerprinting de URL basado en mtime del archivo.
# Cuando se modifica un archivo estático su mtime cambia → la URL cambia →
# Cloudflare y el navegador descargan la versión nueva.
_STATIC_DIR_CB = os.path.join(BASE_DIR, 'static')
_static_ver_cache: dict = {}

def static_v(filename: str) -> str:
    filepath = os.path.join(_STATIC_DIR_CB, filename)
    try:
        mtime = os.path.getmtime(filepath)
        cached = _static_ver_cache.get(filename)
        if cached is None or cached[0] != mtime:
            _static_ver_cache[filename] = (mtime, format(int(mtime), 'x'))
        return '/static/' + filename + '?v=' + _static_ver_cache[filename][1]
    except OSError:
        return '/static/' + filename + '?v=0'

templates.env.globals['static_v'] = static_v

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
    from sqlalchemy.orm import contains_eager

    results = db.session.query(
        CreatorRanking
    ).outerjoin(User, func.lower(User.username) == func.lower(CreatorRanking.nombre)) \
    .options(contains_eager(CreatorRanking.user)) \
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
    from sqlalchemy.orm import contains_eager

    results = db.session.query(
        WriteupRanking
    ).outerjoin(User, func.lower(User.username) == func.lower(WriteupRanking.nombre)) \
    .options(contains_eager(WriteupRanking.user)) \
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

@api_router.post("/submit-machine", response_model=SubmitMachineResponse)
async def api_submit_machine(request: Request, data: SubmitMachineRequest, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
    user_id = session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})

    username = session.get("username")

    # Validacion de entrada ANTES de persistir. El nombre se renderiza en un
    # onclick de la cola de revision (contexto JS); rechazamos metacaracteres
    # HTML/JS y caracteres de control. Ademas validamos que las URLs no usen
    # esquemas peligrosos (javascript:, data:, ...).
    from dockerlabs import validators
    nombre_raw = (data.nombre or "").strip()
    _bad = set('<>"\'`\\')
    if not nombre_raw:
        return JSONResponse(status_code=400, content={"error": "El nombre de la maquina es obligatorio"})
    if len(nombre_raw) > 100:
        return JSONResponse(status_code=400, content={"error": "El nombre de la maquina es demasiado largo (maximo 100 caracteres)"})
    if any(c in _bad for c in nombre_raw) or any(ord(c) < 32 or ord(c) == 127 for c in nombre_raw):
        return JSONResponse(status_code=400, content={"error": "El nombre de la maquina contiene caracteres no permitidos"})
    for _campo, _valor in (("link_maquina", data.link_maquina), ("writeup_url", data.writeup_url)):
        if _valor and _valor.strip():
            _oku, _erru = validators.validate_url(_valor.strip())
            if not _oku:
                return JSONResponse(status_code=400, content={"error": f"{_campo}: {_erru}"})

    sub = PendingMachineSubmission(
        nombre=nombre_raw,
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
    db.session.add(sub)
    db.session.commit()

    return {"success": True, "message": "Máquina enviada y pendiente de revisión"}

# Autenticación

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    redirect_url: Optional[str] = None

def encode_session_cookie(session_data: dict) -> str:
    """Codifica y firma los datos de sesión como cookie."""
    serializer = get_session_serializer()
    return serializer.dumps(session_data)

def create_session_cookie(user_id: int, username: str, role: str = 'jugador', existing_session: dict = None) -> str:
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
    
    return encode_session_cookie(session_data)

def check_password_hash_safe(password_hash: str, password: str) -> bool:
    """Verifica password hash compatible con todas las plataformas.
    
    Maneja el caso de scrypt en macOS usando el paquete scrypt de PyPI como fallback.
    """
    # Si no es scrypt, usar werkzeug directamente
    if not password_hash.startswith('scrypt'):
        return _werkzeug_check_password_hash(password_hash, password)
    
    # Para scrypt, extraer parámetros y verificar manualmente
    try:
        # Formato werkzeug: scrypt:32768:8:1$<salt>$<hash_hex>
        # ej: scrypt:32768:8:1$TvqUilznpmYjn49g$43c27e71...
        parts = password_hash.split('$')
        if len(parts) != 3:
            return False
        
        method_part = parts[0]  # scrypt:32768:8:1
        salt_str = parts[1]     # salt (string plano, no base64)
        expected_hash_hex = parts[2]  # hash en hexadecimal (64 bytes = 128 hex chars)
        
        # Parsear parámetros (N:r:p)
        if ':' in method_part:
            # Formato: scrypt:N:r:p
            _, n_str, r_str, p_str = method_part.split(':')
            n, r, p = int(n_str), int(r_str), int(p_str)
        else:
            # Valores por defecto werkzeug: scrypt$... (sin parámetros)
            n, r, p = 32768, 8, 1  # 2^15 = 32768
        
        # Calcular maxmem como hace werkzeug (132 * n * r * p)
        maxmem = 132 * n * r * p
        
        password_bytes = password.encode('utf-8')
        salt_bytes = salt_str.encode('utf-8')  # El salt se codifica directamente
        
        # Calcular hash scrypt
        try:
            # Intentar usar hashlib primero (Linux/Windows)
            import hashlib
            derived = hashlib.scrypt(
                password_bytes,
                salt=salt_bytes,
                n=n, r=r, p=p,
                maxmem=maxmem,
                dklen=64  # werkzeug usa 64 bytes
            )
        except AttributeError:
            # Fallback para macOS usando el paquete scrypt
            import scrypt
            derived = scrypt.hash(
                password_bytes,
                salt_bytes,
                N=n, r=r, p=p,
                buflen=64  # 64 bytes como werkzeug
            )
        
        # Convertir a hexadecimal y comparar
        import hmac
        derived_hex = derived.hex()
        return hmac.compare_digest(derived_hex, expected_hash_hex)
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error verificando hash scrypt: {e}")
        return False

def _get_user_and_verify_password(username: str, password: str):
    """Función síncrona para consultar usuario y verificar contraseña."""
    user = User.query.filter_by(username=username.strip()).first()
    if user is None:
        return None
    if not check_password_hash_safe(user.password_hash, password):
        return None
    # Extraer todos los datos necesarios antes de retornar
    return {
        'id': user.id,
        'username': user.username,
        'role': user.role
    }

@api_router.post("/auth/login", response_model=LoginResponse)
async def api_auth_login(request: Request, data: LoginRequest, session: dict = Depends(get_session)):
    # Ejecutar consulta de DB en threadpool para evitar problemas de sesión
    user_data = await run_in_threadpool(_get_user_and_verify_password, data.username, data.password)
    
    if user_data is None:
        return JSONResponse(status_code=401, content={"success": False, "message": "Usuario o contraseña incorrectos."})
            
    cookie_val = create_session_cookie(
        user_data['id'], 
        user_data['username'], 
        user_data['role'], 
        existing_session=session
    )
        
    response = JSONResponse(content={"success": True, "redirect_url": "/dashboard"})
    response.set_cookie(
        key="session", 
        value=cookie_val, 
        httponly=True,
        secure=True,
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
    pending_message: Optional[str] = None
    verify_email: Optional[bool] = None

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


    pwd_hash = generate_password_hash(password, method='pbkdf2:sha256')
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
            db.session.add(claim)
            db.session.commit()
            msg = "Tu solicitud de registro se ha enviado para revisión. El nombre de usuario coincide con el de un autor de máquina o writeup, y deberá ser aprobado por un administrador o moderador."
            return {"success": True, "pending_message": msg}
        except Exception:
            db.session.rollback()
            return JSONResponse(status_code=500, content={"success": False, "message": "Error al registrar la solicitud."})
    else:
        from datetime import timedelta
        from dockerlabs.email import send_verification_email, is_smtp_configured

        # Also block if there's already a pending verification for this username/email
        pending_conflict = EmailVerificationToken.query.filter(
            (EmailVerificationToken.username == username) | (EmailVerificationToken.email == email)
        ).first()
        if pending_conflict:
            return JSONResponse(status_code=400, content={"success": False, "message": "Ya existe un registro pendiente para este usuario o correo. Revisa tu bandeja de entrada o espera 24h."})

        if is_smtp_configured():
            try:
                token = secrets.token_urlsafe(32)
                expires_at = datetime.utcnow() + timedelta(hours=24)
                pending = EmailVerificationToken(
                    token=token,
                    username=username,
                    email=email,
                    password_hash=pwd_hash,
                    expires_at=expires_at,
                )
                db.session.add(pending)
                db.session.commit()

                base_url = os.environ.get('APP_URL', '').rstrip('/') or str(request.base_url).rstrip('/')
                await run_in_threadpool(send_verification_email, email, username, token, base_url)
                return {"success": True, "verify_email": True}
            except Exception as e:
                db.session.rollback()
                return JSONResponse(status_code=500, content={"success": False, "message": f"Error al procesar el registro: {str(e)}"})
        else:
            logging.getLogger(__name__).warning("SMTP no configurado — creando usuario sin verificacion de email")
            try:
                new_user = User(username=username, email=email, password_hash=pwd_hash, role='jugador')
                db.session.add(new_user)
                db.session.commit()
                return {"success": True, "message": "Cuenta creada correctamente. Ya puedes iniciar sesion."}
            except IntegrityError:
                db.session.rollback()
                return JSONResponse(status_code=400, content={"success": False, "message": "El usuario o el correo ya estan registrados."})
            except Exception as e:
                db.session.rollback()
                return JSONResponse(status_code=500, content={"success": False, "message": f"Error al crear usuario: {str(e)}"})



class ForgotPasswordRequest(BaseModel):
    email: str

@api_router.post("/auth/forgot-password")
async def api_auth_forgot_password(request: Request, data: ForgotPasswordRequest):
    from datetime import timedelta
    from sqlalchemy import func as _func
    from dockerlabs.email import send_password_reset_email, is_smtp_configured

    generic_msg = "Si el correo existe en nuestro sistema, recibiras un enlace de recuperacion en breve."

    if not is_smtp_configured():
        return JSONResponse(status_code=503, content={"success": False, "message": "El servicio de correo no esta configurado. Contacta al administrador."})

    email = data.email.strip().lower()
    user = User.query.filter(_func.lower(User.email) == email).first()
    if not user:
        return {"success": True, "message": generic_msg}

    PasswordResetToken.query.filter_by(user_id=user.id, used=False).delete()
    db.session.flush()

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    reset_token = PasswordResetToken(token=token, user_id=user.id, expires_at=expires_at)
    db.session.add(reset_token)
    db.session.commit()

    base_url = os.environ.get('APP_URL', '').rstrip('/') or str(request.base_url).rstrip('/')
    await run_in_threadpool(send_password_reset_email, user.email, user.username, token, base_url)
    return {"success": True, "message": generic_msg}


class ResetPasswordRequest(BaseModel):
    token: str
    password: str
    password2: str

@api_router.post("/auth/reset-password")
async def api_auth_reset_password(request: Request, data: ResetPasswordRequest):
    if not data.token or not data.password:
        return JSONResponse(status_code=400, content={"success": False, "message": "Datos incompletos."})
    if data.password != data.password2:
        return JSONResponse(status_code=400, content={"success": False, "message": "Las contrasenyas no coinciden."})

    from dockerlabs import validators
    valid, pwd_error = validators.validate_password_complexity(data.password)
    if not valid:
        return JSONResponse(status_code=400, content={"success": False, "message": pwd_error})

    reset_token = PasswordResetToken.query.filter_by(token=data.token, used=False).first()
    if not reset_token:
        return JSONResponse(status_code=400, content={"success": False, "message": "Enlace de recuperacion invalido o ya utilizado."})

    if datetime.utcnow() > reset_token.expires_at:
        db.session.delete(reset_token)
        db.session.commit()
        return JSONResponse(status_code=400, content={"success": False, "message": "El enlace ha expirado. Solicita uno nuevo."})

    user = User.query.get(reset_token.user_id)
    if not user:
        return JSONResponse(status_code=400, content={"success": False, "message": "Usuario no encontrado."})

    user.password_hash = generate_password_hash(data.password, method='pbkdf2:sha256')
    reset_token.used = True
    db.session.commit()
    return {"success": True, "message": "Contrasena actualizada correctamente."}

# Perfil

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: Optional[str] = None

class UpdateProfileRequest(BaseModel):
    email: Optional[str] = None
    biography: Optional[str] = None
    nombre_diploma: Optional[str] = None

class UpdateSocialLinksRequest(BaseModel):
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    youtube_url: Optional[str] = None

@api_router.post("/change_password")
async def api_change_password(request: Request, data: ChangePasswordRequest, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
    user_id = session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})
        
    if data.confirm_password is not None and data.new_password != data.confirm_password:
        return JSONResponse(status_code=400, content={"error": "Las contraseñas nuevas no coinciden."})
    
    # Validar complejidad de contraseña
    from dockerlabs import validators
    valid, pwd_error = validators.validate_password_complexity(data.new_password)
    if not valid:
        return JSONResponse(status_code=400, content={"error": pwd_error})

    
    user_obj = User.query.get(user_id)
    if not user_obj:
        return JSONResponse(status_code=404, content={"error": "Usuario no encontrado."})
            
    if not check_password_hash_safe(user_obj.password_hash, data.current_password):
        return JSONResponse(status_code=400, content={"error": "La contraseña actual es incorrecta."})
            
    user_obj.password_hash = generate_password_hash(data.new_password, method='pbkdf2:sha256')
    db.session.commit()
    return {"message": "Contraseña actualizada correctamente.", "success": True}

@api_router.post("/update_profile")
async def api_update_profile(request: Request, data: UpdateProfileRequest, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
    user_id = session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})
        
    # Sanitizar inputs
    from dockerlabs import validators
    biography_sanitized = validators.sanitize_text(data.biography.strip()) if data.biography else ""
    nombre_diploma_sanitized = validators.sanitize_text(data.nombre_diploma.strip())[:100] if data.nombre_diploma and data.nombre_diploma.strip() else None

    user_obj = User.query.get(user_id)
    if not user_obj:
        return JSONResponse(status_code=404, content={"error": "Usuario no encontrado."})

    # El email es opcional: el formulario de perfil solo envía la biografía.
    # Solo se valida y actualiza el email si el cliente lo incluye.
    if data.email is not None and data.email.strip():
        email_sanitized = validators.sanitize_text(data.email.strip())
        existing = User.query.filter(User.email == email_sanitized, User.id != user_id).first()
        if existing:
            return JSONResponse(status_code=400, content={"error": "Ese correo electrónico ya está en uso por otra cuenta."})
        user_obj.email = email_sanitized

    try:
        user_obj.biography = biography_sanitized
        user_obj.nombre_diploma = nombre_diploma_sanitized
        db.session.commit()
        return {"message": "Perfil actualizado correctamente.", "success": True}
    except Exception as e:
        db.session.rollback()
        return JSONResponse(status_code=500, content={"error": f"Error al actualizar el perfil: {str(e)}"})

@api_router.post("/update_social_links")
async def api_update_social_links(request: Request, data: UpdateSocialLinksRequest, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
    user_id = session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})

    # Sanitizar y VALIDAR inputs. validate_url rechaza esquemas peligrosos
    # (javascript:, data:, vbscript:, file:, about:) y caracteres que permiten
    # romper atributos HTML (comillas, <, >, backtick). Evita el XSS almacenado
    # via enlaces sociales que terminaba en un innerHTML con href=.
    from dockerlabs import validators

    def _clean_social_url(raw):
        if not raw or not raw.strip():
            return "", None
        raw = raw.strip()
        ok, err = validators.validate_url(raw)
        if not ok:
            return None, err
        return validators.sanitize_text(raw), None

    linkedin_sanitized, _err = _clean_social_url(data.linkedin_url)
    if _err:
        return JSONResponse(status_code=400, content={"error": f"Enlace de LinkedIn invalido: {_err}"})
    github_sanitized, _err = _clean_social_url(data.github_url)
    if _err:
        return JSONResponse(status_code=400, content={"error": f"Enlace de GitHub invalido: {_err}"})
    youtube_sanitized, _err = _clean_social_url(data.youtube_url)
    if _err:
        return JSONResponse(status_code=400, content={"error": f"Enlace de YouTube invalido: {_err}"})
    
    user_obj = User.query.get(user_id)
    if not user_obj:
        return JSONResponse(status_code=404, content={"error": "Usuario no encontrado."})
            
    user_obj.linkedin_url = linkedin_sanitized
    user_obj.github_url = github_sanitized
    user_obj.youtube_url = youtube_sanitized
        
    db.session.commit()
    return {"message": "Enlaces de redes sociales actualizados correctamente.", "success": True}

@api_router.post("/upload-profile-photo")
async def api_upload_profile_photo(
    request: Request,
    photo: UploadFile = File(...),
    session: dict = Depends(get_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    user_id = session.get('user_id')
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

    ALLOWED_PROFILE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.avif'}
    if ext not in ALLOWED_PROFILE_EXTENSIONS:
        return JSONResponse(status_code=400, content={"error": "Formato de imagen no permitido"})

    valid, error = validators.validate_image_content(io.BytesIO(file_bytes))
    if not valid:
        return JSONResponse(status_code=400, content={"error": f"Archivo inválido: {error}"})

    import time
    from dockerlabs.image_utils import to_webp

    try:
        webp_bytes = to_webp(file_bytes, profile='perfil')
    except Exception as exc:
        logging.exception("Error al convertir imagen de perfil a WebP")
        return JSONResponse(status_code=400, content={"error": "No se pudo procesar la imagen"})

    user_obj = User.query.get(user_id)
    if not user_obj:
        return JSONResponse(status_code=400, content={"error": "No se ha podido determinar el usuario"})

    almacenamiento_dir = os.path.join(BASE_DIR, 'uploads', 'perfiles')
    os.makedirs(almacenamiento_dir, exist_ok=True)

    ts = int(time.time())
    filename = f"user_{user_id}_{ts}.webp"
    file_path = os.path.join(almacenamiento_dir, filename)

    try:
        with open(file_path, 'wb') as f:
            f.write(webp_bytes)

        if user_obj.profile_image_path:
            old_path = os.path.join(BASE_DIR, user_obj.profile_image_path)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except Exception:
                    pass

        user_obj.profile_image_path = f"uploads/perfiles/{filename}"
        user_obj.profile_image_data = None
        user_obj.profile_image_mime = 'image/webp'
        db.session.commit()
    except Exception as exc:
        logging.exception("Error al guardar la foto de perfil en disco")
        db.session.rollback()
        return JSONResponse(status_code=500, content={"error": "Error al guardar la imagen en el servidor"})

    image_url = f"/img/perfil/{user_id}?t={ts}"

    return {
        'message': 'Foto de perfil actualizada correctamente.',
        'image_url': image_url
    }

# Administración

class UpdateRoleRequest(BaseModel):
    role: str

class RequestUsernameChangeRequest(BaseModel):
    requested_username: str
    reason: Optional[str] = None
    contacto_opcional: Optional[str] = None

class RejectUsernameChangeRequest(BaseModel):
    decision_reason: Optional[str] = "Rechazado por moderador/admin"

@api_router.post("/admin/update_user_role/{user_id}")
async def api_update_user_role(request: Request, user_id: int, data: UpdateRoleRequest, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_id = session.get('user_id')
    caller_role = session.get('role', '').strip().lower()

    if not caller_id or caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    nuevo_rol = data.role.strip().lower()
    if nuevo_rol not in ('jugador', 'moderador', 'admin'):
        return JSONResponse(status_code=400, content={"error": "Rol inválido"})

    # Los moderadores no pueden asignar rol de admin
    if caller_role == 'moderador' and nuevo_rol == 'admin':
        return JSONResponse(status_code=403, content={"error": "Los moderadores no pueden asignar rol de admin"})

    user = User.query.get(user_id)
    if not user:
        return JSONResponse(status_code=404, content={"error": "Usuario no encontrado"})

    # Un moderador no puede modificar el rol de un administrador
    if caller_role == "moderador" and user.role == "admin":
        return JSONResponse(status_code=403, content={"error": "Los moderadores no pueden modificar a un administrador"})
    # No degradar al último administrador (evita el lockout total)
    if user.role == "admin" and nuevo_rol != "admin" and User.query.filter_by(role="admin").count() <= 1:
        return JSONResponse(status_code=400, content={"error": "No se puede degradar al último administrador."})

    user.role = nuevo_rol
    db.session.commit()
    return {"message": f"Rol de {user.username} actualizado a {nuevo_rol}", "success": True}

@api_router.post("/admin/delete_user/{user_id}")
async def api_delete_user(request: Request, user_id: int, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_id = session.get('user_id')
    caller_role = session.get('role', '')
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
        db.session.delete(user)
        db.session.commit()
        return {"message": "Usuario eliminado correctamente.", "success": True}
    except Exception as e:
        db.session.rollback()
        return JSONResponse(status_code=500, content={"error": f"Error al eliminar el usuario: {str(e)}"})

@api_router.post("/auth/request_username_change")
async def api_request_username_change(request: Request, data: RequestUsernameChangeRequest, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
    import re as _re
    user_id = session.get('user_id')
    old_username = session.get('username')
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
        db.session.add(new_req)
        db.session.commit()
        return {"message": "Solicitud enviada. Un moderador o admin deberá aprobarla.", "success": True}
    except Exception:
        db.session.rollback()
        return JSONResponse(status_code=500, content={"error": "Error al procesar la solicitud."})

@api_router.post("/admin/approve_username_change/{request_id}")
async def api_approve_username_change(request: Request, request_id: int, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_id = session.get('user_id')
    caller_role = session.get('role', '')
    if not caller_id or caller_role not in ('admin',):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

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
        db.session.commit()
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
            db.session.commit()
            try:
                from dockerlabs.writeups import recalcular_ranking_writeups
                recalcular_ranking_writeups()
            except Exception:
                pass
        except Exception:
            db.session.rollback()

    req.estado = 'aprobada'
    req.processed_by = caller_id
    req.processed_at = datetime.utcnow()
    req.decision_reason = decision_reason
    db.session.commit()

    msg = f"Nombre cambiado correctamente a {requested_username}."
    if conflict_count > 0:
        msg = f"Nombre cambiado pero existe conflicto con {conflict_count} writeup(s)."
    return {"message": msg, "success": True, "conflict_count": conflict_count}

@api_router.post("/admin/reject_username_change/{request_id}")
async def api_reject_username_change(request: Request, request_id: int, data: RejectUsernameChangeRequest, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_id = session.get('user_id')
    caller_role = session.get('role', '')
    if not caller_id or caller_role not in ('admin',):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    req = UsernameChangeRequest.query.get(request_id)
    if not req:
        return JSONResponse(status_code=404, content={"error": "Petición no encontrada."})
    req.estado = 'rechazada'
    req.processed_by = caller_id
    req.processed_at = datetime.utcnow()
    req.decision_reason = data.decision_reason
    db.session.commit()
    return {"message": "Petición rechazada correctamente.", "success": True}

@api_router.post("/admin/revert_username_change/{request_id}")
async def api_revert_username_change(request: Request, request_id: int, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_id = session.get('user_id')
    caller_role = session.get('role', '')
    if not caller_id or caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    req = UsernameChangeRequest.query.get(request_id)
    if not req:
        return JSONResponse(status_code=404, content={"error": "Petición no encontrada."})
    req.estado = 'pendiente'
    req.processed_by = None
    req.processed_at = None
    req.decision_reason = None
    db.session.commit()
    return {"message": "Petición revertida a pendiente.", "success": True}

class RateMachineRequest(BaseModel):
    maquina_nombre: str
    dificultad_score: float
    aprendizaje_score: float
    recomendaria_score: float
    diversion_score: float

class ToggleCompletedRequest(BaseModel):
    machine_name: str

# Toggle acceso guest
@api_router.post("/gestion-maquinas/toggle-guest-access")
def api_toggle_guest_access(
    request: Request,
    id: int = Form(...),
    session: dict = Depends(get_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    caller_role = session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    maquina = Machine.query.get(id)
    if not maquina:
        return JSONResponse(status_code=404, content={"error": "Máquina no encontrada"})
    maquina.guest_access = not maquina.guest_access
    db.session.commit()
    return {"message": "Estado actualizado", "guest_access": maquina.guest_access}

# Subida de logo de máquina
@api_router.post("/gestion-maquinas/upload-logo")
async def api_upload_machine_logo(
    request: Request,
    logo: UploadFile = File(...),
    machine_id: int = Form(...),
    origen: str = Form(...),
    session: dict = Depends(get_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    caller_role = session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    if not logo or not logo.filename:
        return JSONResponse(status_code=400, content={"error": "No se ha enviado ningún archivo"})
    if not logo.content_type.startswith('image/'):
        return JSONResponse(status_code=400, content={"error": "El archivo debe ser una imagen"})

    file_bytes = await logo.read()
    if len(file_bytes) > 2 * 1024 * 1024:
        return JSONResponse(status_code=400, content={"error": "La imagen es demasiado grande (máx 2MB)"})

    from dockerlabs import validators

    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "La imagen enviada no es válida"})

    valid, err = validators.validate_image_content(io.BytesIO(file_bytes))
    if not valid:
        return JSONResponse(status_code=400, content={"error": f"Imagen inválida: {err}"})

    original_filename = secure_filename(logo.filename or '')
    _, ext = os.path.splitext(original_filename)
    ext = ext.lower()
    ALLOWED = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.tiff', '.avif'}
    if ext not in ALLOWED:
        return JSONResponse(status_code=400, content={"error": "Formato de imagen no permitido"})

    from dockerlabs.image_utils import to_webp

    maq = Machine.query.get(machine_id)
    if not maq:
        return JSONResponse(status_code=404, content={"error": "Máquina no encontrada"})

    is_svg = (ext == '.svg')
    if is_svg:
        logo_mime = 'image/svg+xml'
        save_bytes = file_bytes
        save_ext = '.svg'
    else:
        try:
            save_bytes = to_webp(file_bytes, profile='logo')
        except Exception:
            return JSONResponse(status_code=400, content={"error": "No se pudo procesar la imagen"})
        logo_mime = 'image/webp'
        save_ext = '.webp'

    almacenamiento_dir = os.path.join(BASE_DIR, 'uploads', 'logos')
    os.makedirs(almacenamiento_dir, exist_ok=True)

    ts = int(time.time())
    prefix = 'bunker' if origen == 'bunker' else 'docker'
    final_filename = f"{prefix}_{machine_id}_{ts}{save_ext}"
    file_path = os.path.join(almacenamiento_dir, final_filename)

    try:
        with open(file_path, 'wb') as f:
            f.write(save_bytes)

        if maq.logo_path:
            old_path = os.path.join(BASE_DIR, maq.logo_path)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except Exception:
                    pass

        maq.logo_path = f"uploads/logos/{final_filename}"
        maq.logo_data = None
        maq.logo_mime = logo_mime
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return JSONResponse(status_code=500, content={"error": str(e)})

    return {
        "message": "Logo subido correctamente",
        "filename": final_filename,
        "image_url": f"/img/maquina/{machine_id}?t={ts}"
    }

# Lista de usuarios (autocompletado admin)
@api_router.get("/get_users")
def api_get_users(request: Request, session: dict = Depends(get_session)):
    caller_role = session.get('role', '')
    if caller_role != 'admin':
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})


    users = User.query.order_by(User.username.asc()).all()
    return {"users": [{"id": u.id, "username": u.username} for u in users]}

# Valoración de máquina
@api_router.post("/rate_machine")
def api_rate_machine(request: Request, data: RateMachineRequest, session: dict = Depends(get_session)):
    user_id = session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión para puntuar"})

    scores = [data.dificultad_score, data.aprendizaje_score, data.recomendaria_score, data.diversion_score]
    if any(s < 1 or s > 5 for s in scores):
        return JSONResponse(status_code=400, content={"success": False, "message": "Las puntuaciones deben estar entre 1 y 5"})

    try:
        existing = Rating.query.filter_by(usuario_id=user_id, maquina_nombre=data.maquina_nombre).first()
        if existing:
            existing.dificultad_score = data.dificultad_score
            existing.aprendizaje_score = data.aprendizaje_score
            existing.recomendaria_score = data.recomendaria_score
            existing.diversion_score = data.diversion_score
            existing.fecha = datetime.utcnow()
        else:
            new_rating = Rating(
                usuario_id=user_id,
                maquina_nombre=data.maquina_nombre,
                dificultad_score=data.dificultad_score,
                aprendizaje_score=data.aprendizaje_score,
                recomendaria_score=data.recomendaria_score,
                diversion_score=data.diversion_score
            )
            db.session.add(new_rating)
        db.session.commit()
        return {"success": True, "message": "Puntuación guardada correctamente"}
    except Exception as e:
        db.session.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

# Consulta de valoración
@api_router.get("/get_machine_rating/{maquina_nombre}")
def api_get_machine_rating(request: Request, maquina_nombre: str, session: dict = Depends(get_session)):
    avg_result = db.session.query(
        func.avg(Rating.dificultad_score).label('avg_dificultad'),
        func.avg(Rating.aprendizaje_score).label('avg_aprendizaje'),
        func.avg(Rating.recomendaria_score).label('avg_recomendaria'),
        func.avg(Rating.diversion_score).label('avg_diversion'),
        func.count(Rating.id).label('count')
    ).filter_by(maquina_nombre=maquina_nombre).first()

    user_id = session.get('user_id')
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

# Máquinas completadas
@api_router.get("/completed_machines/{machine_name}")
def api_get_completed_machines(request: Request, machine_name: str, session: dict = Depends(get_session)):
    user_id = session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    completed = CompletedMachine.query.filter_by(user_id=user_id, machine_name=machine_name).first()
    return {"completed": completed is not None}

@api_router.post("/toggle_completed_machine")
async def api_toggle_completed_machine(request: Request, data: ToggleCompletedRequest, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
    user_id = session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Not authenticated", "success": False})

    machine_name = data.machine_name.strip()
    if not machine_name:
        return JSONResponse(status_code=400, content={"error": "Machine name required", "success": False})

    if not Machine.query.filter_by(nombre=machine_name).first():
        return JSONResponse(status_code=400, content={"error": "Máquina no válida", "success": False})

    existing = CompletedMachine.query.filter_by(user_id=user_id, machine_name=machine_name).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return {"success": True, "completed": False}
    else:
        new_comp = CompletedMachine(user_id=user_id, machine_name=machine_name)
        db.session.add(new_comp)
        db.session.commit()
        return {"success": True, "completed": True}

# Reclamación de Nombre
@api_router.post("/admin/nombre-claims/{claim_id}/approve")
async def api_approve_nombre_claim(request: Request, claim_id: int, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    claim = NameClaim.query.get(claim_id)
    if not claim:
        return JSONResponse(status_code=404, content={"error": "Claim no encontrado"})

    existing = User.query.filter(
        (User.username == claim.nombre_solicitado) | (User.email == claim.email)
    ).first()
    if existing:
        claim.estado = 'rechazada'
        db.session.commit()
        return JSONResponse(status_code=400, content={"error": "El nombre o email ya está en uso. Claim rechazado automáticamente."})

    try:
        new_user = User(
            username=claim.nombre_solicitado,
            email=claim.email,
            password_hash=claim.password_hash,
            role='jugador'
        )
        db.session.add(new_user)
        claim.estado = 'aprobada'
        db.session.commit()
        return {"message": f"Claim aprobado. Usuario '{claim.nombre_solicitado}' creado.", "success": True}
    except IntegrityError:
        db.session.rollback()
        claim.estado = 'rechazada'
        db.session.commit()
        return JSONResponse(status_code=400, content={"error": "Error de integridad. Claim rechazado."})
    except Exception as e:
        db.session.rollback()
        return JSONResponse(status_code=500, content={"error": str(e)})

@api_router.post("/admin/nombre-claims/{claim_id}/reject")
async def api_reject_nombre_claim(request: Request, claim_id: int, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    claim = NameClaim.query.get(claim_id)
    if not claim:
        return JSONResponse(status_code=404, content={"error": "Claim no encontrado"})
    claim.estado = 'rechazada'
    db.session.commit()
    return {"message": "Claim rechazado.", "success": True}

@api_router.post("/admin/nombre-claims/{claim_id}/revert")
async def api_revert_nombre_claim(request: Request, claim_id: int, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    claim = NameClaim.query.get(claim_id)
    if not claim:
        return JSONResponse(status_code=404, content={"error": "Claim no encontrado"})
    claim.estado = 'pendiente'
    db.session.commit()
    return {"message": "Claim revertido a pendiente.", "success": True}

def require_auth_and_role(session: dict, allowed_roles: list):
    """Helper para verificar autenticación y roles."""
    user_id = session.get('user_id')
    role = session.get('role', '')
    if not user_id:
        return False, RedirectResponse(url="/login", status_code=302)
    if role not in allowed_roles:
        return False, RedirectResponse(url="/", status_code=302)
    return True, None


from dockerlabs.routes.notifications import register_notification_routes
from dockerlabs.routes.writeups import register_writeup_routes
from dockerlabs.routes.bunker_api import register_bunker_api_routes
from dockerlabs.routes.images import register_image_routes
from dockerlabs.routes.certificados import register_certificado_routes
from dockerlabs.routes.pending_admin import register_pending_admin_routes
from dockerlabs.routes.pages_admin import register_pages_admin_routes
from dockerlabs.routes.pages_core import register_pages_core_routes

register_notification_routes(
    api_router=api_router,
    get_session=get_session,
    verify_csrf_token=verify_csrf_token,
    db=db,
)

register_writeup_routes(
    api_router=api_router,
    get_session=get_session,
    verify_csrf_token=verify_csrf_token,
    db=db,
)

register_bunker_api_routes(
    api_router=api_router,
    get_session=get_session,
    verify_csrf_token=verify_csrf_token,
    db=db,
)

register_pending_admin_routes(
    api_router=api_router,
    get_session=get_session,
    verify_csrf_token=verify_csrf_token,
    db=db,
)


from dockerlabs.routes.machines import register_machine_routes


from dockerlabs.routes.bunkerlabs_pages import register_bunkerlabs_pages_routes

register_bunkerlabs_pages_routes(
    pages_router=pages_router,
    get_session=get_session,
    verify_csrf_token=verify_csrf_token,
    require_auth_and_role=require_auth_and_role,
    encode_session_cookie=encode_session_cookie,
    templates=templates,
    db=db,
    url_for=url_for,
)

register_machine_routes(
    api_router=api_router,
    pages_router=pages_router,
    get_session=get_session,
    verify_csrf_token=verify_csrf_token,
    require_auth_and_role=require_auth_and_role,
    encode_session_cookie=encode_session_cookie,
    templates=templates,
    db=db,
    url_for=url_for,
)

register_pages_admin_routes(
    pages_router=pages_router,
    get_session=get_session,
    verify_csrf_token=verify_csrf_token,
    require_auth_and_role=require_auth_and_role,
    encode_session_cookie=encode_session_cookie,
    templates=templates,
    url_for=url_for,
    db=db,
)

register_pages_core_routes(
    pages_router=pages_router,
    get_session=get_session,
    create_session_cookie=create_session_cookie,
    get_fastapi_profile_image_url=get_fastapi_profile_image_url,
    url_for=url_for,
    templates=templates,
    db=db,
)


register_certificado_routes(
    api_router=api_router,
    get_session=get_session,
    db=db,
)

register_image_routes(
    api_router=api_router,
    pages_router=pages_router,
)
