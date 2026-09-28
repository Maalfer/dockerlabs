from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime
import secrets
import re
import os
import logging


from dockerlabs.models import User, SessionConfig, ApiToken
from dockerlabs.extensions import db
from dockerlabs.token_auth import verify_api_token
from werkzeug.security import check_password_hash as _werkzeug_check_password_hash

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
        # Misc
        'dashboard': '/dashboard',
        'index': '/',
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

def _extract_api_token(request: Request) -> Optional[str]:
    """Token de admin enviado por cabecera: `Authorization: Bearer <token>`
    o, como alternativa, `X-Admin-Token: <token>`."""
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        candidate = auth[7:].strip()
        if candidate:
            return candidate
    header_token = request.headers.get("X-Admin-Token", "").strip()
    return header_token or None


def _get_session_from_api_token(request: Request) -> Optional[dict]:
    """Si la petición trae un token de admin por cabecera, lo valida contra
    `ApiToken` y devuelve una sesión equivalente a la de un admin logueado
    por cookie (mismo dict que produce el resto de esta función: user_id,
    username, role). Devuelve None si no se envió ningún token (para que
    get_session() siga con el flujo normal de cookie); devuelve {} (sesión
    vacía, igual que "no autenticado") si se envió un token pero no es
    válido, para no confundirlo con una cookie que pudiera venir a la vez.

    Solo hay unos pocos tokens de admin activos a la vez (los genera el
    propio dueño de la plataforma desde /dashboard), así que iterar y
    comparar con pbkdf2 es aceptable y evita tener que indexar por hash."""
    token = _extract_api_token(request)
    if not token:
        return None

    logger = logging.getLogger(__name__)
    try:
        candidates = ApiToken.query.filter(ApiToken.revoked_at.is_(None)).all()
    except Exception:
        db.session.rollback()
        logger.warning("Error consultando ApiToken para autenticación por cabecera")
        return {}

    for row in candidates:
        if verify_api_token(row.token_hash, token):
            admin = User.query.get(row.admin_user_id)
            if not admin or admin.role != "admin":
                # El dueño del token ya no es admin (degradado o borrado): no
                # cae a ningún otro rol, se trata como no autenticado.
                return {}
            row.last_used_at = datetime.utcnow()
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
            return {
                "user_id": admin.id,
                "username": admin.username,
                "role": "admin",
                "_auth_via": "api_token",
            }

    # Token presente pero no coincide con ninguno activo: rechazar.
    return {}


def get_session(request: Request) -> dict:
    """Extrae y valida la sesión del usuario: desde un token de API de admin
    por cabecera (ver `_get_session_from_api_token`) o, si no hay token,
    desde la cookie de sesión firmada. Este es el punto único del que
    dependen todas las rutas (directamente o vía `require_auth_and_role`),
    así que un token válido por cabecera hereda automáticamente el mismo
    acceso que ya tiene un admin logueado, sin tocar cada ruta."""
    token_session = _get_session_from_api_token(request)
    if token_session is not None:
        return token_session

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

        # Revalidación contra BD: antes solo se hacía para admin/moderador (para
        # que degradar o borrar a un admin surta efecto de inmediato). Ahora se
        # hace para cualquier sesión logueada, y además se compara
        # `session_version`: cambiar contraseña, cambiar email o borrar la
        # cuenta incrementan esa columna (o hacen desaparecer la fila), lo que
        # invalida cualquier cookie emitida antes de ese momento sin necesitar
        # un almacén de sesiones. Cookies previas a este campo no traen
        # session_version en el payload y se aceptan sin comparar (se exige a
        # partir del próximo login o cambio de credenciales, para no cerrar de
        # golpe la sesión de todo el mundo al desplegar esto).
        uid = d.get("user_id")
        if uid:
            real = None
            try:
                real = db.session.query(User.role, User.session_version).filter(User.id == uid).one_or_none()
            except Exception:
                db.session.rollback()
                real = None

            if real is None:
                # Cuenta borrada: la sesión deja de ser válida.
                return {}

            real_role, real_session_version = real
            cookie_session_version = d.get("session_version")
            if cookie_session_version is not None and cookie_session_version != real_session_version:
                return {}

            if real_role != d.get("role"):
                d["role"] = real_role
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







# Autenticación



def encode_session_cookie(session_data: dict) -> str:
    """Codifica y firma los datos de sesión como cookie."""
    serializer = get_session_serializer()
    return serializer.dumps(session_data)

def create_session_cookie(user_id: int, username: str, role: str = 'jugador', existing_session: dict = None, _id: str = None, session_version: int = None) -> str:
    import hashlib
    import os

    session_data = existing_session or {}
    if _id is None:
        _id = hashlib.sha512(os.urandom(24)).hexdigest()

    session_data['_user_id'] = str(user_id)
    session_data['_fresh'] = True
    session_data['_id'] = _id
    session_data['user_id'] = user_id
    session_data['username'] = username
    session_data['role'] = role
    # Sesiones anónimas (login/register/recover antes de autenticar) no traen
    # session_version: get_session() no las revalida contra BD (user_id=0).
    # Para un login real sí se pasa, para que get_session() pueda detectar
    # cambios de contraseña/email/borrado de cuenta posteriores a esta cookie.
    if session_version is not None:
        session_data['session_version'] = session_version
    elif 'session_version' in session_data:
        del session_data['session_version']

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
        'role': user.role,
        'session_version': user.session_version
    }












# Perfil








# Administración






# Toggle acceso guest

# Subida de logo de máquina

# Lista de usuarios (autocompletado admin)

# Valoración de máquina

# Consulta de valoración

# Máquinas completadas


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
from dockerlabs.routes.public_profile import register_public_profile_routes

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
    compute_csrf_token=compute_csrf_token,
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

register_public_profile_routes(
    pages_router=pages_router,
    db=db,
    api_router=api_router,
    get_session=get_session,
    verify_csrf_token=verify_csrf_token,
    templates=templates,
)

register_image_routes(
    api_router=api_router,
    pages_router=pages_router,
)


# --- Rutas extraidas de este mismo modulo (antes estaban aqui en linea) ------
from dockerlabs.routes.api_publica import register_api_publica_routes
from dockerlabs.routes.auth import register_auth_routes
from dockerlabs.routes.perfil import register_perfil_routes
from dockerlabs.routes.admin_usuarios import register_admin_usuarios_routes
from dockerlabs.routes.maquinas_api import register_maquinas_api_routes
from dockerlabs.routes.api_tokens import register_api_tokens_routes

register_api_publica_routes(
    api_router=api_router,
    get_session=get_session,
    verify_csrf_token=verify_csrf_token,
    get_fastapi_profile_image_url=get_fastapi_profile_image_url,
)

register_auth_routes(
    api_router=api_router,
    get_session=get_session,
    verify_csrf_token=verify_csrf_token,
    create_session_cookie=create_session_cookie,
    check_password_hash_safe=check_password_hash_safe,
    get_user_and_verify_password=_get_user_and_verify_password,
)

register_perfil_routes(
    api_router=api_router,
    get_session=get_session,
    verify_csrf_token=verify_csrf_token,
    check_password_hash_safe=check_password_hash_safe,
    create_session_cookie=create_session_cookie,
    BASE_DIR=BASE_DIR,
)

register_admin_usuarios_routes(
    api_router=api_router,
    get_session=get_session,
    verify_csrf_token=verify_csrf_token,
)

register_api_tokens_routes(
    api_router=api_router,
    get_session=get_session,
    verify_csrf_token=verify_csrf_token,
    db=db,
)

register_maquinas_api_routes(
    api_router=api_router,
    get_session=get_session,
    verify_csrf_token=verify_csrf_token,
    BASE_DIR=BASE_DIR,
)

from dockerlabs.routes.seo import register_seo_routes

register_seo_routes(pages_router=pages_router)
