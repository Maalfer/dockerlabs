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

# Importaciones Flask (necesarias durante la migración)
from dockerlabs.app import app as flask_app
from dockerlabs.models import User, Machine, Writeup, PendingMachineSubmission, Category, CreatorRanking, WriteupRanking, PendingWriteup, NameClaim, UsernameChangeRequest, PendingWriteup, WriteupEditRequest, CompletedMachine, Rating
from dockerlabs.extensions import db as alchemy_db
from werkzeug.security import check_password_hash, generate_password_hash
from flask.sessions import SecureCookieSessionInterface

# Función url_for personalizada para compatibilidad con Flask
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

def get_flask_session(request: Request) -> dict:
    """Extraer sesión Flask desde cookies para compatibilidad."""
    cookie = request.cookies.get("session")
    if not cookie:
        return {}
    
    # Crear un Request-like object para SecureCookieSessionInterface
    class MinimalRequest:
        def __init__(self, cookies):
            self.cookies = cookies
    
    session_interface = SecureCookieSessionInterface()
    serializer = session_interface.get_signing_serializer(flask_app)
    try:
        data = serializer.loads(cookie)
        return data if isinstance(data, dict) else {}
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

    if not session_token or not token or not secrets.compare_digest(str(session_token), str(token)):
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

@api_router.get("", response_model=ApiSummaryResponse)
def api_summary():
    
    with flask_app.app_context():
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
def api_ranking_autores():
    
    with flask_app.app_context():
        results = alchemy_db.session.query(
            CreatorRanking, User
        ).outerjoin(User, func.lower(User.username) == func.lower(CreatorRanking.nombre)) \
        .order_by(CreatorRanking.maquinas.desc(), func.lower(CreatorRanking.nombre).asc()) \
        .all()
        
        response_list = []
        for creator, user in results:
            r = {
                'id': creator.id,
                'nombre': creator.nombre,
                'maquinas': creator.maquinas,
                'autor': creator.nombre                
            }
            user_id = user.id if user else None
            r['imagen'] = get_fastapi_profile_image_url(username=r['autor'], user_id=user_id)
            response_list.append(r)
            
        return response_list

@api_router.get("/ranking_writeups", response_model=List[WriteupRankingResponse])
def api_ranking_writeups():
    
    with flask_app.app_context():
        results = alchemy_db.session.query(
            WriteupRanking, User
        ).outerjoin(User, func.lower(User.username) == func.lower(WriteupRanking.nombre)) \
        .order_by(WriteupRanking.puntos.desc(), func.lower(WriteupRanking.nombre).asc()) \
        .all()
        
        response_list = []
        for rank, user in results:
            r = {
                'id': rank.id,
                'nombre': rank.nombre,
                'puntos': rank.puntos
            }
            author_name = rank.nombre
            user_id = user.id if user else None
            r['imagen_url'] = get_fastapi_profile_image_url(username=author_name, user_id=user_id)
            response_list.append(r)

        return response_list

@api_router.get("/user/info", response_model=UserInfoResponse)
def api_user_info(flask_session: dict = Depends(get_flask_session)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "No has iniciado sesión", "is_authenticated": False})

    
    with flask_app.app_context():
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
def submit_machine(
    data: SubmitMachineRequest,
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})

    username = flask_session.get("username")

    from dockerlabs.models import PendingMachineSubmission

    with flask_app.app_context():
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
    session_interface = SecureCookieSessionInterface()
    serializer = session_interface.get_signing_serializer(flask_app)
    return serializer.dumps(existing_session)

def create_flask_session_cookie(user_id: int, username: str, role: str = 'jugador', existing_session: dict = None) -> str:
    import hashlib
    
    session_data = existing_session or {}
    _id = hashlib.sha512(os.urandom(24)).hexdigest()
    
    session_data['_user_id'] = str(user_id)
    session_data['_fresh'] = True
    session_data['_id'] = _id
    session_data['user_id'] = user_id
    session_data['username'] = username
    session_data['role'] = role
    
    session_interface = SecureCookieSessionInterface()
    serializer = session_interface.get_signing_serializer(flask_app)
    return serializer.dumps(session_data)

@api_router.post("/auth/login", response_model=LoginResponse)
async def api_auth_login(data: LoginRequest, request: Request, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    
    with flask_app.app_context():
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
async def api_auth_register(data: RegisterRequest, csrf_ok: bool = Depends(verify_csrf_token)):
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
    
    if '/' in username or '\\' in username or '..' in username or '.' in username:
        return JSONResponse(status_code=400, content={"success": False, "message": "El nombre de usuario no puede contener caracteres especiales como /, \\, o puntos."})
    if username.lower() in ['admin', 'root', 'system', 'default', 'balulero', 'default-profile', 'logo', 'pingu']:
        return JSONResponse(status_code=400, content={"success": False, "message": "Este nombre de usuario está reservado por el sistema."})
    if not re.match(r'^[A-Za-z0-9_-]+$', username):
        return JSONResponse(status_code=400, content={"success": False, "message": "El nombre de usuario solo puede contener letras, números, guiones y guiones bajos."})


    with flask_app.app_context():
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
async def api_auth_recover(data: RecoverRequest, csrf_ok: bool = Depends(verify_csrf_token)):
    username = data.username.strip()
    pin = data.pin.strip()
    password = data.password
    password2 = data.password2

    if not username or not pin or not password:
        return JSONResponse(status_code=400, content={"success": False, "message": "Todos los campos son obligatorios."})
    if password != password2:
        return JSONResponse(status_code=400, content={"success": False, "message": "Las contraseñas no coinciden."})


    with flask_app.app_context():
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
async def api_change_password(data: ChangePasswordRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})
        
    if data.new_password != data.confirm_password:
        return JSONResponse(status_code=400, content={"error": "Las contraseñas nuevas no coinciden."})

    
    with flask_app.app_context():
        user_obj = User.query.get(user_id)
        if not user_obj:
            return JSONResponse(status_code=404, content={"error": "Usuario no encontrado."})
            
        if not check_password_hash(user_obj.password_hash, data.current_password):
            return JSONResponse(status_code=400, content={"error": "La contraseña actual es incorrecta."})
            
        user_obj.password_hash = generate_password_hash(data.new_password)
        alchemy_db.session.commit()
        return {"message": "Contraseña actualizada correctamente.", "success": True}

@api_router.post("/update_profile")
async def api_update_profile(data: UpdateProfileRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})
        
    if not data.email.strip():
        return JSONResponse(status_code=400, content={"error": "El email es obligatorio."})

    
    with flask_app.app_context():
        user_obj = User.query.get(user_id)
        if not user_obj:
            return JSONResponse(status_code=404, content={"error": "Usuario no encontrado."})
            
        user_obj.email = data.email.strip()
        user_obj.biography = data.biography.strip() if data.biography else ""
        alchemy_db.session.commit()
        return {"message": "Perfil actualizado correctamente.", "success": True}

@api_router.post("/update_social_links")
async def api_update_social_links(data: UpdateSocialLinksRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})

    
    with flask_app.app_context():
        user_obj = User.query.get(user_id)
        if not user_obj:
            return JSONResponse(status_code=404, content={"error": "Usuario no encontrado."})
            
        user_obj.linkedin_url = data.linkedin_url.strip() if data.linkedin_url else ""
        user_obj.github_url = data.github_url.strip() if data.github_url else ""
        user_obj.youtube_url = data.youtube_url.strip() if data.youtube_url else ""
        
        alchemy_db.session.commit()
        return {"message": "Enlaces de redes sociales actualizados correctamente.", "success": True}

from fastapi import UploadFile, File

@api_router.post("/upload-profile-photo")
async def upload_profile_photo(
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
    
    with flask_app.app_context():
        user_obj = User.query.get(user_id)
        if not user_obj:
            return JSONResponse(status_code=400, content={"error": "No se ha podido determinar el usuario"})

        try:
            user_obj.profile_image_data = file_bytes
            user_obj.profile_image_mime = mime_type
            alchemy_db.session.commit()
        except Exception as exc:
            logging.exception("Error al guardar la foto de perfil en la base de datos")
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": "Error al guardar la imagen en el servidor"})

        ts = int(time.time())
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
async def api_update_user_role(user_id: int, data: UpdateRoleRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
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

    with flask_app.app_context():
        user = User.query.get(user_id)
        if not user:
            return JSONResponse(status_code=404, content={"error": "Usuario no encontrado"})
        user.role = nuevo_rol
        alchemy_db.session.commit()
        return {"message": f"Rol de {user.username} actualizado a {nuevo_rol}", "success": True}

@api_router.post("/admin/delete_user/{user_id}")
async def api_delete_user(user_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_id = flask_session.get('user_id')
    caller_role = flask_session.get('role', '')
    if not caller_id or caller_role not in ('admin',):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    if caller_id == user_id:
        return JSONResponse(status_code=400, content={"error": "No puedes eliminar tu propia cuenta desde aquí."})


    with flask_app.app_context():
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
async def api_request_username_change(data: RequestUsernameChangeRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
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

    with flask_app.app_context():
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
async def api_approve_username_change(request_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_id = flask_session.get('user_id')
    caller_role = flask_session.get('role', '')
    if not caller_id or caller_role not in ('admin',):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import User, UsernameChangeRequest, Writeup, PendingWriteup, WriteupRanking, CreatorRanking
    from sqlalchemy import func

    with flask_app.app_context():
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
async def api_reject_username_change(request_id: int, data: RejectUsernameChangeRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_id = flask_session.get('user_id')
    caller_role = flask_session.get('role', '')
    if not caller_id or caller_role not in ('admin',):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import UsernameChangeRequest

    with flask_app.app_context():
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
async def api_revert_username_change(request_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_id = flask_session.get('user_id')
    caller_role = flask_session.get('role', '')
    if not caller_id or caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import UsernameChangeRequest

    with flask_app.app_context():
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
    machine_id: int,
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import Machine

    with flask_app.app_context():
        maquina = Machine.query.get(machine_id)
        if not maquina:
            return JSONResponse(status_code=404, content={"error": "Máquina no encontrada"})
        maquina.guest_access = not maquina.guest_access
        alchemy_db.session.commit()
        return {"message": "Estado actualizado", "guest_access": maquina.guest_access}

# ── Upload Machine Logo ──────────────────────────────────────────
@api_router.post("/gestion-maquinas/upload-logo")
async def api_upload_machine_logo(
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

    with flask_app.app_context():
        maq = Machine.query.get(machine_id)
        if not maq:
            return JSONResponse(status_code=404, content={"error": "Máquina no encontrada"})

        if origen == 'bunker':
            nombre_seguro = secure_filename(maq.nombre)
            final_filename = f"{nombre_seguro}{ext}"
            db_path_prefix = "bunkerlabs/images/logos-bunkerlabs"
        else:
            ts = int(_time.time())
            final_filename = f"docker_{machine_id}_{ts}{ext}"
            db_path_prefix = "dockerlabs/images/logos"

        try:
            maq.logo_data = file_bytes
            maq.logo_mime = logo_mime
            maq.imagen = f"{db_path_prefix}/{final_filename}"
            alchemy_db.session.commit()
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})

        return {
            "message": "Logo subido correctamente",
            "image_path": maq.imagen,
            "filename": final_filename,
            "image_url": f"/img/maquina/{machine_id}"
        }

# ── Get Users (admin autocomplete) ──────────────────────────────
@api_router.get("/get_users")
def api_get_users(flask_session: dict = Depends(get_flask_session)):
    caller_role = flask_session.get('role', '')
    if caller_role != 'admin':
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})


    with flask_app.app_context():
        users = User.query.order_by(User.username.asc()).all()
        return {"users": [{"id": u.id, "username": u.username} for u in users]}

# ── Rate Machine ─────────────────────────────────────────────────
@api_router.post("/rate_machine")
def api_rate_machine(data: RateMachineRequest, flask_session: dict = Depends(get_flask_session)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión para puntuar"})

    scores = [data.dificultad_score, data.aprendizaje_score, data.recomendaria_score, data.diversion_score]
    if any(s < 1 or s > 5 for s in scores):
        return JSONResponse(status_code=400, content={"success": False, "message": "Las puntuaciones deben estar entre 1 y 5"})

    from dockerlabs.models import Rating

    with flask_app.app_context():
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
def api_get_machine_rating(maquina_nombre: str, flask_session: dict = Depends(get_flask_session)):
    from dockerlabs.models import Rating
    from sqlalchemy import func

    with flask_app.app_context():
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
def api_check_completed_machine(machine_name: str, flask_session: dict = Depends(get_flask_session)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    from dockerlabs.models import CompletedMachine

    with flask_app.app_context():
        completed = CompletedMachine.query.filter_by(user_id=user_id, machine_name=machine_name).first()
        return {"completed": completed is not None}

@api_router.post("/toggle_completed_machine")
async def api_toggle_completed_machine(data: ToggleCompletedRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Not authenticated", "success": False})

    machine_name = data.machine_name.strip()
    if not machine_name:
        return JSONResponse(status_code=400, content={"error": "Machine name required", "success": False})

    from dockerlabs.models import Machine, CompletedMachine

    with flask_app.app_context():
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
async def api_approve_nombre_claim(claim_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import NameClaim, User

    with flask_app.app_context():
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
async def api_reject_nombre_claim(claim_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import NameClaim

    with flask_app.app_context():
        claim = NameClaim.query.get(claim_id)
        if not claim:
            return JSONResponse(status_code=404, content={"error": "Claim no encontrado"})
        claim.estado = 'rechazada'
        alchemy_db.session.commit()
        return {"message": "Claim rechazado.", "success": True}

@api_router.post("/admin/nombre-claims/{claim_id}/revert")
async def api_revert_nombre_claim(claim_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import NameClaim

    with flask_app.app_context():
        claim = NameClaim.query.get(claim_id)
        if not claim:
            return JSONResponse(status_code=404, content={"error": "Claim no encontrado"})
        claim.estado = 'pendiente'
        alchemy_db.session.commit()
        return {"message": "Claim revertido a pendiente.", "success": True}

# ─────────────────────────────────────────────────────────────────
# Fase 10 – APIs JSON de Writeups + Pending Machines (routes.py)
# ─────────────────────────────────────────────────────────────────

class SubmitWriteupRequest(BaseModel):
    maquina: str
    url: str
    tipo: str  # "video" | "texto"

class UpdateWriteupRequest(BaseModel):
    url: str
    tipo: str

class UpdateWriteupRecibidoRequest(BaseModel):
    maquina: str
    autor: str
    url: str
    tipo: str

class ReportWriteupRequest(BaseModel):
    reason: Optional[str] = "Sin motivo especificado"

class RejectUsernameRequest(BaseModel):
    decision_reason: Optional[str] = "Rechazado por moderador/admin"

# ── Subir Writeup ────────────────────────────────────────────────
@api_router.post("/submit_writeup")
async def api_submit_writeup(data: SubmitWriteupRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    import re as _re, urllib.parse as _up
    user_id = flask_session.get('user_id')
    autor = flask_session.get('username', '').strip()
    if not user_id or not autor:
        return JSONResponse(status_code=403, content={"error": "Debes iniciar sesión"})

    maquina = data.maquina.strip()
    url = data.url.strip()
    tipo = data.tipo.strip().lower()

    from dockerlabs import validators
    from dockerlabs.models import Machine, PendingWriteup, Writeup

    valid, err = validators.validate_machine_name(maquina)
    if not valid:
        return JSONResponse(status_code=400, content={"error": f"Campo 'maquina' inválido: {err}"})
    valid, err = validators.validate_url(url)
    if not valid:
        return JSONResponse(status_code=400, content={"error": f"URL inválida: {err}"})
    valid, err = validators.validate_writeup_type(tipo)
    if not valid:
        return JSONResponse(status_code=400, content={"error": f"Tipo inválido: {err}"})

    tipo = "video" if tipo == "video" else "texto"

    with flask_app.app_context():
        if not Machine.query.filter_by(nombre=maquina).first():
            return JSONResponse(status_code=400, content={"error": "La máquina especificada no existe"})
        if PendingWriteup.query.filter_by(autor=autor, maquina=maquina).first():
            return JSONResponse(status_code=400, content={"error": "Writeup ya está en pendiente de revisión."})
        if Writeup.query.filter_by(autor=autor, maquina=maquina).first():
            return JSONResponse(status_code=400, content={"error": "Writeup ya publicado."})
        try:
            new_pending = PendingWriteup(maquina=maquina, autor=autor, url=url, tipo=tipo)
            alchemy_db.session.add(new_pending)
            alchemy_db.session.commit()
            return {"message": "Writeup enviado correctamente"}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": f"Error al guardar: {str(e)}"})

# ── Aprobar Writeup Recibido ─────────────────────────────────────
@api_router.post("/writeups/recibidos/{writeup_id}/aprobar")
async def api_aprobar_writeup_recibido(writeup_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import User, PendingWriteup, Writeup, WriteupRanking
    from sqlalchemy import func

    with flask_app.app_context():
        try:
            pending = PendingWriteup.query.get(writeup_id)
            if not pending:
                return JSONResponse(status_code=404, content={"error": "Writeup no encontrado"})

            autor_real = pending.autor
            usuario = User.query.filter(func.lower(User.username) == func.lower(autor_real)).first()
            if usuario:
                autor_real = usuario.username

            if not Writeup.query.filter_by(maquina=pending.maquina, autor=autor_real, url=pending.url).first():
                new_writeup = Writeup(maquina=pending.maquina, autor=autor_real, url=pending.url, tipo=pending.tipo)
                alchemy_db.session.add(new_writeup)

            alchemy_db.session.delete(pending)
            alchemy_db.session.commit()

            # Recalcular ranking dentro del contexto
            from dockerlabs.writeups import recalcular_ranking_writeups
            recalcular_ranking_writeups()

            return {"message": "Writeup aprobado y movido a publicados."}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Error al aprobar: {str(e)}"})

# ── Aprobar/Rechazar/Revertir WriteupEditRequest ─────────────────
@api_router.post("/writeups/edit-requests/{request_id}/approve")
async def api_approve_writeup_edit(request_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import Writeup, WriteupEditRequest

    with flask_app.app_context():
        req = WriteupEditRequest.query.get(request_id)
        if not req or req.estado != 'pendiente':
            return JSONResponse(status_code=404, content={"error": "Petición no encontrada o ya procesada"})

        writeup = Writeup.query.get(req.writeup_id)
        if not writeup:
            return JSONResponse(status_code=404, content={"error": "Writeup original no encontrado"})

        writeup.maquina = req.maquina_nueva or writeup.maquina
        writeup.autor = req.autor_nuevo or writeup.autor
        writeup.url = req.url_nueva or writeup.url
        writeup.tipo = req.tipo_nuevo or writeup.tipo
        req.estado = 'aprobada'
        alchemy_db.session.commit()

        from dockerlabs.writeups import recalcular_ranking_writeups
        recalcular_ranking_writeups()
        return {"message": "Petición de edición aprobada.", "success": True}

@api_router.post("/writeups/edit-requests/{request_id}/reject")
async def api_reject_writeup_edit(request_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import WriteupEditRequest

    with flask_app.app_context():
        req = WriteupEditRequest.query.get(request_id)
        if req:
            req.estado = 'rechazada'
            alchemy_db.session.commit()
        return {"message": "Petición rechazada.", "success": True}

@api_router.post("/writeups/edit-requests/{request_id}/revert")
async def api_revert_writeup_edit(request_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import WriteupEditRequest

    with flask_app.app_context():
        req = WriteupEditRequest.query.get(request_id)
        if req:
            req.estado = 'pendiente'
            alchemy_db.session.commit()
        return {"message": "Petición revertida a pendiente.", "success": True}

# ── CRUD Writeups Subidos (publicados) ───────────────────────────
@api_router.put("/writeups/subidos/{writeup_id}")
def api_update_writeup_subido(writeup_id: int, data: UpdateWriteupRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    user_id = flask_session.get('user_id')
    username = flask_session.get('username', '').strip()
    caller_role = flask_session.get('role', '')
    if not user_id:
        return JSONResponse(status_code=403, content={"error": "Debes iniciar sesión."})

    from dockerlabs import validators
    from dockerlabs.models import Writeup, WriteupEditRequest

    valid, err = validators.validate_url(data.url)
    if not valid:
        return JSONResponse(status_code=400, content={"error": f"URL inválida: {err}"})
    valid, err = validators.validate_writeup_type(data.tipo)
    if not valid:
        return JSONResponse(status_code=400, content={"error": f"Tipo inválido: {err}"})

    with flask_app.app_context():
        writeup = Writeup.query.get(writeup_id)
        if not writeup:
            return JSONResponse(status_code=404, content={"error": "Writeup no encontrado"})

        maquina_db = (writeup.maquina or '').strip()
        autor_db = (writeup.autor or '').strip()

        if caller_role in ('admin', 'moderador'):
            try:
                writeup.url = data.url
                writeup.tipo = data.tipo
                alchemy_db.session.commit()
                from dockerlabs.writeups import recalcular_ranking_writeups
                recalcular_ranking_writeups()
                return {"message": "Writeup actualizado correctamente"}
            except Exception as e:
                alchemy_db.session.rollback()
                return JSONResponse(status_code=500, content={"error": str(e)})

        if not username or username.lower() != autor_db.lower():
            return JSONResponse(status_code=403, content={"error": "No tienes permiso para modificar este writeup."})

        try:
            edit_request = WriteupEditRequest(
                writeup_id=writeup.id, user_id=user_id, username=username,
                maquina_original=maquina_db, autor_original=autor_db,
                url_original=writeup.url, tipo_original=writeup.tipo,
                maquina_nueva=maquina_db, autor_nuevo=autor_db,
                url_nueva=data.url, tipo_nuevo=data.tipo
            )
            alchemy_db.session.add(edit_request)
            alchemy_db.session.commit()
            return {"message": "Tu petición de cambio ha sido enviada para revisión."}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})

@api_router.delete("/writeups/subidos/{writeup_id}")
def api_delete_writeup_subido(writeup_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import Writeup

    with flask_app.app_context():
        writeup = Writeup.query.get(writeup_id)
        if not writeup:
            return JSONResponse(status_code=404, content={"error": "Writeup no encontrado"})
        alchemy_db.session.delete(writeup)
        alchemy_db.session.commit()
        from dockerlabs.writeups import recalcular_ranking_writeups
        recalcular_ranking_writeups()
        return {"message": "Writeup eliminado correctamente"}

# ── CRUD Writeups Recibidos (pendientes) ─────────────────────────
@api_router.put("/writeups/recibidos/{writeup_id}")
def api_update_writeup_recibido(writeup_id: int, data: UpdateWriteupRecibidoRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs import validators
    from dockerlabs.models import PendingWriteup

    for val_fn, field in [(validators.validate_machine_name, data.maquina), (validators.validate_author_name, data.autor),
                          (validators.validate_url, data.url), (validators.validate_writeup_type, data.tipo)]:
        valid, err = val_fn(field)
        if not valid:
            return JSONResponse(status_code=400, content={"error": err})

    with flask_app.app_context():
        pending = PendingWriteup.query.get(writeup_id)
        if not pending:
            return JSONResponse(status_code=404, content={"error": "Writeup no encontrado"})
        pending.maquina = data.maquina
        pending.autor = data.autor
        pending.url = data.url
        pending.tipo = data.tipo
        alchemy_db.session.commit()
        return {"message": "Writeup actualizado correctamente"}

@api_router.delete("/writeups/recibidos/{writeup_id}")
def api_delete_writeup_recibido(writeup_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import PendingWriteup

    with flask_app.app_context():
        pending = PendingWriteup.query.get(writeup_id)
        if not pending:
            return JSONResponse(status_code=404, content={"error": "Writeup no encontrado"})
        alchemy_db.session.delete(pending)
        alchemy_db.session.commit()
        return {"message": "Writeup eliminado correctamente"}

# ── Writeups por Máquina (pública) ──────────────────────────────
@api_router.get("/writeups/{maquina_nombre}")
def api_writeups_maquina(maquina_nombre: str, flask_session: dict = Depends(get_flask_session)):
    from dockerlabs.models import Writeup, User
    from sqlalchemy import func

    with flask_app.app_context():
        results = alchemy_db.session.query(
            Writeup.id, Writeup.autor, Writeup.url, Writeup.tipo, User.id
        ).outerjoin(User, func.lower(User.username) == func.lower(Writeup.autor)) \
         .filter(Writeup.maquina == maquina_nombre) \
         .order_by(Writeup.created_at.desc(), Writeup.id.desc()).all()

        writeups = []
        for wid, autor, url, tipo, uid in results:
            tipo_raw = (tipo or '').strip().lower()
            tipo_emoji = "\U0001F3A5" if tipo_raw == "video" else "\U0001F4DD"
            writeups.append({"id": wid, "name": autor, "url": url, "type": tipo_emoji, "es_usuario_registrado": bool(uid)})
        return writeups

# ── Reportar Writeup ─────────────────────────────────────────────
@api_router.post("/writeups/{writeup_id}/report")
def api_report_writeup(writeup_id: int, data: ReportWriteupRequest, flask_session: dict = Depends(get_flask_session)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión para reportar"})

    from dockerlabs.models import Writeup, WriteupReport

    with flask_app.app_context():
        if not Writeup.query.get(writeup_id):
            return JSONResponse(status_code=404, content={"error": "Writeup no encontrado"})
        try:
            report = WriteupReport(writeup_id=writeup_id, reporter_id=user_id, reason=data.reason)
            alchemy_db.session.add(report)
            alchemy_db.session.commit()
            return {"message": "Reporte enviado correctamente"}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": "Error al guardar el reporte"})

# ── Ignorar Reporte ──────────────────────────────────────────────
@api_router.post("/admin/reports/{report_id}/ignore")
def api_ignore_report(report_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import WriteupReport

    with flask_app.app_context():
        report = WriteupReport.query.get(report_id)
        if report:
            alchemy_db.session.delete(report)
            alchemy_db.session.commit()
        return {"message": "Reporte ignorado/eliminado correctamente"}

# ── Listar Reportes (admin) ──────────────────────────────────────
@api_router.get("/admin/writeup_reports")
def api_get_reports(flask_session: dict = Depends(get_flask_session)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import WriteupReport

    with flask_app.app_context():
        reports_orm = WriteupReport.query.order_by(WriteupReport.created_at.desc()).all()
        reports = []
        for r in reports_orm:
            writeup_data = {}
            if r.writeup:
                writeup_data = {"id": r.writeup.id, "autor": r.writeup.autor,
                                "maquina": r.writeup.maquina, "url": r.writeup.url, "tipo": r.writeup.tipo}
            reports.append({
                "id": r.id, "reason": r.reason,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "reporter_name": r.reporter.username if r.reporter else "Unknown",
                "writeup": writeup_data
            })
        return reports

# ── Listar Writeups Recibidos (admin) ────────────────────────────
@api_router.get("/writeups/recibidos/list")
def api_list_writeups_recibidos(flask_session: dict = Depends(get_flask_session)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import PendingWriteup, Machine

    with flask_app.app_context():
        results = alchemy_db.session.query(PendingWriteup, Machine.id, Machine.imagen) \
            .outerjoin(Machine, PendingWriteup.maquina == Machine.nombre) \
            .order_by(PendingWriteup.created_at.desc(), PendingWriteup.id.desc()).all()

        writeups = []
        for pw, machine_id, imagen in results:
            image_url = f"/img/maquina/{machine_id}" if machine_id else None
            writeups.append({
                "id": pw.id, "maquina": pw.maquina, "autor": pw.autor,
                "url": pw.url, "tipo": pw.tipo,
                "created_at": pw.created_at.isoformat() if pw.created_at else None,
                "imagen": image_url
            })
        return writeups

# ── Ranking Writeups y Creadores (pública) ───────────────────────
@api_router.get("/writeups/ranking")
def api_ranking_writeups_v2(flask_session: dict = Depends(get_flask_session)):
    from dockerlabs.models import WriteupRanking
    from sqlalchemy import func

    with flask_app.app_context():
        from dockerlabs.extensions import db as alchemy_db
        rankings = WriteupRanking.query.order_by(WriteupRanking.puntos.desc(), func.lower(WriteupRanking.nombre).asc()).all()
        return [{"nombre": r.nombre, "puntos": r.puntos} for r in rankings]

# ── Author Profile (pública) ─────────────────────────────────────
@api_router.get("/author_profile")
def api_author_profile(nombre: str, flask_session: dict = Depends(get_flask_session)):
    if not nombre:
        return JSONResponse(status_code=400, content={"error": "Nombre requerido"})

    from dockerlabs.models import User, Machine, Writeup
    from sqlalchemy import func
    from dockerlabs.auth import get_profile_image_url

    with flask_app.app_context():
        maquinas_orm = Machine.query.filter_by(autor=nombre).order_by(Machine.fecha.desc()).all()
        maquinas = [{"nombre": m.nombre, "dificultad": m.dificultad, "imagen_url": f"/img/maquina/{m.id}"} for m in maquinas_orm]

        writeups_orm = Writeup.query.filter_by(autor=nombre).order_by(Writeup.created_at.desc()).all()
        writeups = [{"maquina": w.maquina, "url": w.url, "tipo": w.tipo} for w in writeups_orm]

        user = User.query.filter(func.lower(User.username) == func.lower(nombre)).first()
        user_id = user.id if user else None
        profile_image_url = get_profile_image_url(username=nombre, user_id=user_id)

        return {
            "nombre": nombre,
            "profile_image_url": profile_image_url,
            "maquinas": maquinas,
            "writeups": writeups,
            "biography": user.biography if user else None,
            "linkedin_url": user.linkedin_url if user else None,
            "github_url": user.github_url if user else None,
            "youtube_url": user.youtube_url if user else None,
        }

# ── Pending Machines Approve/Reject (routes.py) ──────────────────
@api_router.post("/admin/pending-machines/{machine_id}/approve")
def api_approve_pending_machine(machine_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import PendingMachineSubmission

    with flask_app.app_context():
        sub = PendingMachineSubmission.query.get(machine_id)
        if not sub:
            return JSONResponse(status_code=404, content={"error": "Máquina pendiente no encontrada"})
        sub.estado = "aprobado"
        sub.reviewed_at = datetime.utcnow()
        alchemy_db.session.commit()
        return {"message": "Máquina aprobada", "success": True}

@api_router.post("/admin/pending-machines/{machine_id}/reject")
def api_reject_pending_machine(machine_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.models import PendingMachineSubmission

    with flask_app.app_context():
        sub = PendingMachineSubmission.query.get(machine_id)
        if not sub:
            return JSONResponse(status_code=404, content={"error": "Máquina pendiente no encontrada"})
        sub.estado = "rechazado"
        sub.reviewed_at = datetime.utcnow()
        alchemy_db.session.commit()
        return {"message": "Máquina rechazada", "success": True}


# ═══════════════════════════════════════════════════════════════════════════════
# MENSAJERÍA - Migrado desde messaging.py (Flask Blueprint)
# ═══════════════════════════════════════════════════════════════════════════════

from slowapi import Limiter
from slowapi.util import get_remote_address

# Modelos Pydantic para mensajería
class SendMessageRequest(BaseModel):
    receiver: str
    content: str

class SendMessageResponse(BaseModel):
    success: bool
    message: Optional[str] = None

class ConversationResponse(BaseModel):
    username: str
    unread: int
    last_message: str
    timestamp: str

class ConversationsListResponse(BaseModel):
    conversations: List[ConversationResponse]

class ChatMessageResponse(BaseModel):
    sender: str
    content: str
    timestamp: str
    mine: bool

class ChatResponse(BaseModel):
    messages: List[ChatMessageResponse]

class UnreadCountResponse(BaseModel):
    count: int

class SearchUsersResponse(BaseModel):
    users: List[dict]

class BroadcastResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    count: Optional[int] = None

class SimpleSuccessResponse(BaseModel):
    success: bool
    message: Optional[str] = None


# Helper para obtener el limiter desde el estado de la app
def get_limiter():
    from dockerlabs.asgi import limiter
    return limiter


@api_router.post("/messages/send", response_model=SendMessageResponse)
def api_send_message(
    data: SendMessageRequest,
    request: Request,
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    """
    Enviar mensaje a otro usuario.
    Rate limit: 30 por minuto.
    """
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

    receiver_username = data.receiver.strip() if data.receiver else ""
    content = data.content.strip() if data.content else ""

    if not receiver_username or not content:
        return JSONResponse(status_code=400, content={"success": False, "message": "Hay cierta información que no se permite enviar 😉"})

    if len(content) > 1000:
        return JSONResponse(status_code=400, content={"success": False, "message": "Mensaje demasiado largo"})

    # Validación de enlaces
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    if url_pattern.search(content):
        return JSONResponse(status_code=400, content={"success": False, "message": "No se permiten enlaces"})

    from dockerlabs.models import User, Mensajeria
    from sqlalchemy import or_, and_

    with flask_app.app_context():
        receiver = User.query.filter_by(username=receiver_username).first()
        if not receiver:
            return JSONResponse(status_code=404, content={"success": False, "message": "Usuario no encontrado"})

        if receiver.id == user_id:
            return JSONResponse(status_code=400, content={"success": False, "message": "No puedes enviarte mensajes a ti mismo"})

        sender_id = user_id
        receiver_id = receiver.id

        # FIFO Limit: máximo 100 mensajes por conversación
        msgs_query = Mensajeria.query.filter(
            or_(
                and_(Mensajeria.sender_id == sender_id, Mensajeria.receiver_id == receiver_id),
                and_(Mensajeria.sender_id == receiver_id, Mensajeria.receiver_id == sender_id)
            )
        ).order_by(Mensajeria.timestamp.asc())

        count = msgs_query.count()

        if count >= 100:
            # Eliminar mensajes más antiguos
            to_delete_count = count - 99
            oldest_msgs = msgs_query.limit(to_delete_count).all()
            for m in oldest_msgs:
                alchemy_db.session.delete(m)

        new_msg = Mensajeria(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content
        )
        alchemy_db.session.add(new_msg)
        alchemy_db.session.commit()

    return {"success": True}


@api_router.get("/messages/conversations", response_model=ConversationsListResponse)
def api_get_conversations(flask_session: dict = Depends(get_flask_session)):
    """Obtener lista de conversaciones del usuario."""
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

    from dockerlabs.models import User, Mensajeria
    from sqlalchemy import or_, and_

    with flask_app.app_context():
        # Usuarios con los que se ha intercambiado mensajes
        sent_subquery = alchemy_db.session.query(Mensajeria.receiver_id).filter(
            Mensajeria.sender_id == user_id,
            Mensajeria.deleted_by_sender == False
        )

        received_subquery = alchemy_db.session.query(Mensajeria.sender_id).filter(
            Mensajeria.receiver_id == user_id,
            Mensajeria.deleted_by_receiver == False
        )

        subquery = sent_subquery.union(received_subquery).subquery()
        contact_ids = [row[0] for row in alchemy_db.session.query(subquery).all()]

        contacts = []
        for cid in contact_ids:
            user = User.query.get(cid)
            if user:
                # Contar no leídos
                unread = Mensajeria.query.filter_by(
                    sender_id=cid,
                    receiver_id=user_id,
                    read=False,
                    deleted_by_receiver=False
                ).count()

                # Último mensaje
                last_msg = Mensajeria.query.filter(
                    or_(
                        and_(Mensajeria.sender_id == user_id, Mensajeria.receiver_id == cid, Mensajeria.deleted_by_sender == False),
                        and_(Mensajeria.sender_id == cid, Mensajeria.receiver_id == user_id, Mensajeria.deleted_by_receiver == False)
                    )
                ).order_by(Mensajeria.timestamp.desc()).first()

                if last_msg:
                    contacts.append({
                        'username': user.username,
                        'unread': unread,
                        'last_message': last_msg.content[:30] + '...' if len(last_msg.content) > 30 else last_msg.content,
                        'timestamp': last_msg.timestamp.isoformat()
                    })

        contacts.sort(key=lambda x: x['timestamp'] or '', reverse=True)

    return {"conversations": contacts}


@api_router.get("/messages/chat/{username}", response_model=ChatResponse)
def api_get_chat(username: str, flask_session: dict = Depends(get_flask_session)):
    """Obtener mensajes de una conversación específica."""
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

    from dockerlabs.models import User, Mensajeria
    from sqlalchemy import or_, and_

    with flask_app.app_context():
        other_user = User.query.filter_by(username=username).first()
        if not other_user:
            return JSONResponse(status_code=404, content={"success": False, "message": "Usuario no encontrado"})

        other_id = other_user.id

        messages = Mensajeria.query.filter(
            or_(
                and_(Mensajeria.sender_id == user_id, Mensajeria.receiver_id == other_id, Mensajeria.deleted_by_sender == False),
                and_(Mensajeria.sender_id == other_id, Mensajeria.receiver_id == user_id, Mensajeria.deleted_by_receiver == False)
            )
        ).order_by(Mensajeria.timestamp.asc()).all()

        # Marcar como leídos
        unread_msgs = Mensajeria.query.filter_by(
            sender_id=other_id,
            receiver_id=user_id,
            read=False,
            deleted_by_receiver=False
        ).all()

        for m in unread_msgs:
            m.read = True
        alchemy_db.session.commit()

        result_messages = [{
            'sender': m.sender.username,
            'content': m.content,
            'timestamp': m.timestamp.isoformat(),
            'mine': m.sender_id == user_id
        } for m in messages]

    return {"messages": result_messages}


@api_router.post("/messages/delete_conversation/{username}", response_model=SimpleSuccessResponse)
def api_delete_conversation(
    username: str,
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    """Eliminar una conversación (soft delete)."""
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

    from dockerlabs.models import User, Mensajeria

    with flask_app.app_context():
        other_user = User.query.filter_by(username=username).first()
        if not other_user:
            return JSONResponse(status_code=404, content={"success": False, "message": "Usuario no encontrado"})

        other_id = other_user.id

        # Soft delete de mensajes enviados
        sent_msgs = Mensajeria.query.filter_by(sender_id=user_id, receiver_id=other_id).all()
        for m in sent_msgs:
            m.deleted_by_sender = True

        # Soft delete de mensajes recibidos
        received_msgs = Mensajeria.query.filter_by(sender_id=other_id, receiver_id=user_id).all()
        for m in received_msgs:
            m.deleted_by_receiver = True

        alchemy_db.session.commit()

    return {"success": True}


@api_router.get("/messages/unread_count", response_model=UnreadCountResponse)
def api_get_unread_count(flask_session: dict = Depends(get_flask_session)):
    """Obtener cantidad de mensajes no leídos."""
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"count": 0})

    from dockerlabs.models import Mensajeria

    with flask_app.app_context():
        count = Mensajeria.query.filter_by(
            receiver_id=user_id,
            read=False,
            deleted_by_receiver=False
        ).count()

    return {"count": count}


@api_router.get("/messages/search_users", response_model=SearchUsersResponse)
def api_search_users(q: str = "", flask_session: dict = Depends(get_flask_session)):
    """Buscar usuarios por nombre."""
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"users": []})


    with flask_app.app_context():
        query = q.strip()
        if not query:
            return {"users": []}

        users = User.query.filter(User.username.ilike(f'%{query}%'), User.id != user_id).limit(10).all()

    return {"users": [{'username': u.username} for u in users]}


@api_router.post("/messages/broadcast", response_model=BroadcastResponse)
def api_broadcast_message(
    request: Request,
    data: SendMessageRequest,
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    """
    Enviar mensaje broadcast a todos los usuarios (solo admin).
    Rate limit: 1 por 5 minutos.
    """
    user_id = flask_session.get('user_id')
    role = flask_session.get('role', '')

    if not user_id:
        return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

    if role != 'admin':
        return JSONResponse(status_code=403, content={"success": False, "message": "Acceso denegado"})

    content = data.content.strip() if data.content else ""

    if not content:
        return JSONResponse(status_code=400, content={"success": False, "message": "El mensaje no puede estar vacío"})

    if len(content) > 1000:
        return JSONResponse(status_code=400, content={"success": False, "message": "Mensaje demasiado largo"})

    # Validación de enlaces
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    if url_pattern.search(content):
        return JSONResponse(status_code=400, content={"success": False, "message": "No se permiten enlaces en difusiones"})

    from dockerlabs.models import User, Mensajeria

    with flask_app.app_context():
        sender_id = user_id
        users = User.query.filter(User.id != sender_id).all()

        new_messages = []
        for user in users:
            new_messages.append(Mensajeria(
                sender_id=sender_id,
                receiver_id=user.id,
                content=content,
                timestamp=datetime.utcnow(),
                read=False
            ))

        alchemy_db.session.add_all(new_messages)
        alchemy_db.session.commit()

    return {"success": True, "count": len(new_messages)}


# ═══════════════════════════════════════════════════════════════════════════════
# WRITEUPS - Migrado desde writeups.py (endpoints JSON)
# ═══════════════════════════════════════════════════════════════════════════════

class WriteupItem(BaseModel):
    id: int
    maquina: str
    autor: str
    url: str
    tipo: str
    created_at: Optional[datetime] = None

class MaquinaWriteupItem(BaseModel):
    maquina: str
    total: int
    imagen: Optional[str] = None

class MaquinasWriteupsResponse(BaseModel):
    maquinas: List[MaquinaWriteupItem]


@api_router.get("/writeups_subidos", response_model=List[WriteupItem])
def api_list_writeups_subidos(
    maquina: Optional[str] = None,
    filter_mode: Optional[str] = None,
    flask_session: dict = Depends(get_flask_session)
):
    """
    Listar writeups subidos.
    - admin/moderador: pueden ver todos o filtrar por 'mine'
    - usuario normal: solo ve sus propios writeups
    Rate limit: 60 por minuto.
    """
    user_id = flask_session.get('user_id')
    role = flask_session.get('role', '')
    username = (flask_session.get('username') or '').strip()

    if not user_id:
        return JSONResponse(status_code=401, content=[])

    from dockerlabs.models import Writeup

    with flask_app.app_context():
        query = Writeup.query

        # Lógica de permisos
        if role in ['admin', 'moderador']:
            if filter_mode == 'mine' and username:
                query = query.filter_by(autor=username)
            if maquina:
                query = query.filter_by(maquina=maquina)
        else:
            # Usuario normal: solo sus propios writeups
            if not username:
                return []
            query = query.filter_by(autor=username)
            if maquina:
                query = query.filter_by(maquina=maquina)

        writeups_objs = query.order_by(Writeup.created_at.desc(), Writeup.id.desc()).all()

        result = []
        for w in writeups_objs:
            result.append({
                "id": w.id,
                "maquina": w.maquina,
                "autor": w.autor,
                "url": w.url,
                "tipo": w.tipo,
                "created_at": w.created_at,
            })

    return result


@api_router.get("/writeups_subidos/maquinas", response_model=MaquinasWriteupsResponse)
def api_list_maquinas_writeups_subidos(
    filter_mode: Optional[str] = None,
    flask_session: dict = Depends(get_flask_session)
):
    """
    Listar máquinas que tienen writeups subidos.
    Rate limit: 60 por minuto.
    """
    user_id = flask_session.get('user_id')
    role = flask_session.get('role', '')
    username = (flask_session.get('username') or '').strip()

    if not user_id:
        return JSONResponse(status_code=401, content={"maquinas": []})

    from dockerlabs.models import Writeup, Machine
    from sqlalchemy import func

    with flask_app.app_context():
        query = alchemy_db.session.query(
            Writeup.maquina,
            func.count().label('total'),
            Machine.imagen
        ).outerjoin(Machine, Writeup.maquina == Machine.nombre) \
         .filter(Writeup.maquina != None, Writeup.maquina != '')

        # Lógica de permisos
        if role in ['admin', 'moderador']:
            if filter_mode == 'mine' and username:
                query = query.filter(Writeup.autor == username)
        else:
            if not username:
                return {"maquinas": []}
            query = query.filter(Writeup.autor == username)

        results = query.group_by(Writeup.maquina, Machine.imagen) \
                       .order_by(func.lower(Writeup.maquina)).all()

        maquinas = []
        for maquina_nombre, total, imagen in results:
            imagen_rel = (imagen or "").strip()
            imagen_url = None
            if imagen_rel:
                if imagen_rel.startswith('dockerlabs/') or imagen_rel.startswith('bunkerlabs/'):
                    static_path = imagen_rel
                elif '/' in imagen_rel:
                    static_path = f'dockerlabs/images/{imagen_rel}'
                else:
                    static_path = f'dockerlabs/images/logos/{imagen_rel}'
                # Usar ruta estática directa, sin url_for
                imagen_url = f"/static/{static_path}"

            maquinas.append({
                "maquina": maquina_nombre,
                "total": total,
                "imagen": imagen_url,
            })

    return {"maquinas": maquinas}


# ═══════════════════════════════════════════════════════════════════════════════
# SERVING DE IMÁGENES - Rutas sin prefijo /api (pages_router)
# Se exponen en /img/perfil/{id} y /img/maquina/{id}
# También se añaden alias /api/img/perfil/{id} y /api/img/maquina/{id}
# por retrocompatibilidad con auth.py (get_profile_image_url)
# ═══════════════════════════════════════════════════════════════════════════════

def _serve_profile_image_logic(user_id: int):
    """
    Lógica compartida para servir la imagen de perfil desde BD con fallback a disco.
    """
    _BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    PROFILE_UPLOAD_FOLDER = os.path.join(_BASE_DIR, 'static', 'dockerlabs', 'images', 'perfiles')
    ALLOWED_PROFILE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    default_image = "dockerlabs/images/balu.webp"

    def get_profile_image_static_path(username, uid=None):
        if uid:
            for ext in ALLOWED_PROFILE_EXTENSIONS:
                candidate = os.path.join(PROFILE_UPLOAD_FOLDER, f"{uid}{ext}")
                if os.path.exists(candidate):
                    return f"dockerlabs/images/perfiles/{uid}{ext}"
        if not username:
            return default_image
        if '/' in username or '\\' in username or '..' in username:
            return default_image
        from werkzeug.utils import secure_filename
        candidates_names = [username, username.lower(), secure_filename(username), secure_filename(username).lower()]
        candidates_names = list(dict.fromkeys(candidates_names))
        for name in candidates_names:
            for ext in ALLOWED_PROFILE_EXTENSIONS:
                candidate = os.path.join(PROFILE_UPLOAD_FOLDER, f"{name}{ext}")
                if os.path.exists(candidate):
                    return f"dockerlabs/images/perfiles/{name}{ext}"
        return default_image

    with flask_app.app_context():
        user = User.query.get(user_id)

        # Primero intentar desde la base de datos (campo deferred)
        if user:
            try:
                image_data = user.profile_image_data
                if image_data:
                    mime = user.profile_image_mime or 'image/jpeg'
                    return StreamingResponse(
                        io.BytesIO(image_data),
                        media_type=mime,
                        headers={"Cache-Control": "public, max-age=3600"}
                    )
            except Exception:
                pass  # Si el campo deferred falla, continúa con el fallback a disco

        # Fallback a disco
        disk_path = get_profile_image_static_path(user.username if user else None, uid=user_id)
        if disk_path and disk_path != default_image:
            full_path = os.path.join(_BASE_DIR, 'static', disk_path)
            if os.path.exists(full_path):
                return FileResponse(full_path, headers={"Cache-Control": "public, max-age=3600"})

    # Default fallback
    default_path = os.path.join(_BASE_DIR, 'static', default_image)
    if os.path.exists(default_path):
        return FileResponse(default_path)
    raise HTTPException(status_code=404, detail="Imagen no encontrada")


def _serve_machine_logo_logic(machine_id: int):
    """
    Lógica compartida para servir el logo de máquina desde BD con fallback a disco.
    """
    _BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    with flask_app.app_context():
        machine = Machine.query.get(machine_id)

        # Primero intentar desde la base de datos
        if machine:
            try:
                logo_data = machine.logo_data
                if logo_data:
                    mime = machine.logo_mime or 'image/jpeg'
                    return StreamingResponse(
                        io.BytesIO(logo_data),
                        media_type=mime,
                        headers={"Cache-Control": "public, max-age=3600"}
                    )
            except Exception:
                pass

        # Fallback a fichero estático
        if machine and machine.imagen:
            full_path = os.path.join(_BASE_DIR, 'static', machine.imagen)
            if os.path.exists(full_path):
                return FileResponse(full_path, headers={"Cache-Control": "public, max-age=3600"})

    # Default logo
    default_logo = os.path.join(_BASE_DIR, 'static', 'dockerlabs', 'images', 'logos', 'logo.png')
    if os.path.exists(default_logo):
        return FileResponse(default_logo)
    raise HTTPException(status_code=404, detail="Logo no encontrado")


# Rutas principales (sin prefijo /api): usadas por las plantillas HTML y get_fastapi_profile_image_url
@pages_router.get("/img/perfil/{user_id}")
def serve_profile_image(user_id: int):
    """Sirve la imagen de perfil: primero desde BD, luego desde disco, luego imagen por defecto."""
    return _serve_profile_image_logic(user_id)


@pages_router.get("/img/maquina/{machine_id}")
def serve_machine_logo(machine_id: int):
    """Sirve el logo de la máquina: primero desde BD, luego desde disco, luego logo por defecto."""
    return _serve_machine_logo_logic(machine_id)


# Alias con prefijo /api: retrocompatibilidad con auth.py (get_profile_image_url genera /api/img/perfil/)
@api_router.get("/img/perfil/{user_id}")
def serve_profile_image_api(user_id: int):
    """Alias /api/img/perfil/{user_id} → delega en la lógica principal."""
    return _serve_profile_image_logic(user_id)


@api_router.get("/img/maquina/{machine_id}")
def serve_machine_logo_api(machine_id: int):
    """Alias /api/img/maquina/{machine_id} → delega en la lógica principal."""
    return _serve_machine_logo_logic(machine_id)




# ═══════════════════════════════════════════════════════════════════════════════
# BUNKERLABS API - Endpoints JSON migrados desde bunkerlabs.py
# ═══════════════════════════════════════════════════════════════════════════════

class FlagValidationRequest(BaseModel):
    maquina_nombre: str
    pin: str

class FlagValidationResponse(BaseModel):
    message: str
    puntos: Optional[int] = None

class RankingEntry(BaseModel):
    id: int
    nombre: str
    puntos: int

class RankingResponse(BaseModel):
    ranking: List[RankingEntry]


@api_router.post("/bunker/validate-flag", response_model=FlagValidationResponse)
def api_validate_flag(
    data: FlagValidationRequest,
    flask_session: dict = Depends(get_flask_session)
):
    """
    Validar flag de máquina BunkerLabs.
    Equivalente a: POST /api/validate_flag en bunkerlabs.py
    Rate limit: 30 por minuto.
    """
    user_id = flask_session.get('user_id')
    username = (flask_session.get('username') or '').strip()

    if not user_id and not flask_session.get('bunkerlabs_guest'):
        raise HTTPException(status_code=401, detail="Sesión no válida")

    from dockerlabs.models import Machine, CompletedMachine, User
    from sqlalchemy import func

    PUNTOS_MAP = {"Muy Fácil": 10, "Fácil": 20, "Medio": 30, "Difícil": 40}

    with flask_app.app_context():
        maquina = Machine.query.filter_by(
            nombre=data.maquina_nombre.strip(),
            origen='bunker'
        ).first()

        if not maquina:
            raise HTTPException(status_code=404, detail="Máquina no encontrada")

        # Verificar acceso de invitado
        if flask_session.get('bunkerlabs_guest'):
            if not maquina.guest_access:
                raise HTTPException(status_code=403, detail="Los invitados no pueden subir flags")
            if maquina.pin == data.pin.strip():
                return {"message": "¡Flag correcta! (Modo invitado: no se guarda el progreso)"}
            raise HTTPException(status_code=401, detail="Flag incorrecta")

        # Usuario autenticado
        if maquina.pin != data.pin.strip():
            raise HTTPException(status_code=401, detail="Flag incorrecta")

        # Verificar si ya completó esta máquina
        ya_completada = CompletedMachine.query.filter_by(
            user_id=user_id,
            machine_name=maquina.nombre
        ).first()

        if ya_completada:
            return {"message": "Flag correcta, pero ya habías completado esta máquina"}

        puntos = PUNTOS_MAP.get(maquina.dificultad, 0)

        try:
            # Marcar como completada en DockerLabs
            completed = CompletedMachine(
                user_id=user_id,
                machine_name=maquina.nombre,
                completed_at=datetime.utcnow()
            )
            alchemy_db.session.add(completed)

            # Actualizar puntos del usuario
            user = User.query.get(user_id)
            if user:
                user.puntos = (user.puntos or 0) + puntos

            alchemy_db.session.commit()
            return {"message": f"¡Flag correcta! Has ganado {puntos} puntos", "puntos": puntos}

        except Exception:
            alchemy_db.session.rollback()
            raise HTTPException(status_code=500, detail="Error al procesar la flag")


@api_router.get("/bunker/ranking", response_model=RankingResponse)
def api_bunker_ranking():
    """
    Obtener ranking de jugadores BunkerLabs.
    Equivalente a: GET /api/ranking en bunkerlabs.py
    Rate limit: 60 por minuto.
    """

    with flask_app.app_context():
        # Solo usuarios con puntos > 0, ordenados por puntos descendente
        users = User.query.filter(User.puntos > 0).order_by(User.puntos.desc()).all()

        ranking = []
        for idx, user in enumerate(users, start=1):
            ranking.append({
                "id": idx,
                "nombre": user.username or "Unknown",
                "puntos": user.puntos or 0
            })

    return {"ranking": ranking}


# ═══════════════════════════════════════════════════════════════════════════════
# BUNKERLABS API (Fase 5) - Endpoints restantes migrados desde bunkerlabs.py
# ═══════════════════════════════════════════════════════════════════════════════

class BunkerAccessLogEntry(BaseModel):
    nombre: str
    fecha: str

class BunkerAccessLogsResponse(BaseModel):
    logs: List[BunkerAccessLogEntry]

class BunkerWriteupItem(BaseModel):
    id: int
    autor: str
    url: str
    tipo: str
    locked: bool
    created_at: Optional[str] = None

class BunkerWriteupsResponse(BaseModel):
    writeups: List[BunkerWriteupItem]

class ToggleLockResponse(BaseModel):
    message: str
    locked: bool

class UpdateFlagRequest(BaseModel):
    flag: str

class UpdateFlagResponse(BaseModel):
    success: bool
    message: str
    machine_id: int
    machine_name: str


@api_router.get("/bunker/logs/{token_id}", response_model=BunkerAccessLogsResponse)
def api_get_bunker_access_logs(
    token_id: int,
    flask_session: dict = Depends(get_flask_session)
):
    """
    Obtener logs de acceso para un token BunkerLabs.
    Equivalente a: GET /api/logs/<token_id> en bunkerlabs.py
    Solo admin.
    """
    role = flask_session.get('role', '')
    if role != 'admin':
        raise HTTPException(status_code=403, detail="Acceso denegado")

    from bunkerlabs.models import BunkerAccessLog

    with flask_app.app_context():
        logs = BunkerAccessLog.query.filter_by(token_id=token_id) \
                                   .order_by(BunkerAccessLog.accessed_at.desc()).all()

        result = []
        for log in logs:
            result.append({
                "nombre": log.user_nombre,
                "fecha": log.accessed_at.strftime('%d-%m-%Y %H:%M:%S')
            })

    return {"logs": result}


@api_router.delete("/bunker/logs/{token_id}")
def api_delete_bunker_access_logs(
    token_id: int,
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    """
    Eliminar logs de acceso para un token BunkerLabs.
    Equivalente a: POST /api/logs/<token_id>/delete en bunkerlabs.py
    Solo admin. Requiere CSRF.
    """
    role = flask_session.get('role', '')
    if role != 'admin':
        raise HTTPException(status_code=403, detail="Acceso denegado")

    from bunkerlabs.models import BunkerAccessLog

    with flask_app.app_context():
        try:
            BunkerAccessLog.query.filter_by(token_id=token_id).delete()
            alchemy_db.session.commit()
            return {"message": "Historial eliminado correctamente"}
        except Exception:
            alchemy_db.session.rollback()
            raise HTTPException(status_code=500, detail="Error al eliminar el historial")


@api_router.get("/bunker/writeups/{maquina_nombre}", response_model=BunkerWriteupsResponse)
def api_get_bunker_writeups(maquina_nombre: str):
    """
    Obtener writeups de una máquina BunkerLabs (Entornos Reales).
    Equivalente a: GET /api/writeups/<maquina_nombre> en bunkerlabs.py
    """
    from bunkerlabs.models import BunkerWriteup

    with flask_app.app_context():
        writeups = BunkerWriteup.query.filter_by(maquina=maquina_nombre) \
                                      .order_by(BunkerWriteup.created_at.desc()).all()

        result = []
        for w in writeups:
            result.append({
                "id": w.id,
                "autor": w.autor,
                "url": w.url,
                "tipo": w.tipo,
                "locked": w.locked,
                "created_at": w.created_at.isoformat() if w.created_at else None
            })

    return {"writeups": result}


@api_router.post("/bunker/admin/writeups/toggle-lock/{writeup_id}", response_model=ToggleLockResponse)
def api_toggle_writeup_lock(
    writeup_id: int,
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    """
    Alternar estado de bloqueo de un writeup BunkerLabs.
    Equivalente a: POST /admin/writeups/toggle_lock/<writeup_id> en bunkerlabs.py
    Solo admin. Requiere CSRF.
    Rate limit: 20 por minuto.
    """
    role = flask_session.get('role', '')
    if role != 'admin':
        raise HTTPException(status_code=403, detail="Acceso denegado")

    from bunkerlabs.models import BunkerWriteup

    with flask_app.app_context():
        writeup = BunkerWriteup.query.get(writeup_id)
        if not writeup:
            raise HTTPException(status_code=404, detail="Writeup no encontrado")

        try:
            writeup.locked = not writeup.locked
            alchemy_db.session.commit()
            return {"message": "Estado actualizado", "locked": writeup.locked}
        except Exception as e:
            alchemy_db.session.rollback()
            raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/bunker/admin/machines/update-flag/{machine_id}", response_model=UpdateFlagResponse)
def api_update_machine_flag(
    machine_id: int,
    data: UpdateFlagRequest,
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    """
    Actualizar flag (pin) de una máquina BunkerLabs.
    Equivalente a: POST /admin/machines/update_flag/<machine_id> en bunkerlabs.py
    Solo admin. Requiere CSRF.
    """
    role = flask_session.get('role', '')
    if role != 'admin':
        raise HTTPException(status_code=403, detail="Acceso denegado")

    from dockerlabs.models import Machine

    with flask_app.app_context():
        machine = Machine.query.get(machine_id)
        if not machine or machine.origen != 'bunker':
            raise HTTPException(status_code=404, detail="Máquina no encontrada")

        if not data.flag.strip():
            raise HTTPException(status_code=400, detail="La flag no puede estar vacía")

        try:
            machine.pin = data.flag.strip()
            alchemy_db.session.commit()
            return {
                "success": True,
                "message": f"Flag actualizada para {machine.nombre}",
                "machine_id": machine_id,
                "machine_name": machine.nombre
            }
        except Exception as e:
            alchemy_db.session.rollback()
            raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINAS HTML - Fase 4a: Páginas principales migradas desde Flask
# ═══════════════════════════════════════════════════════════════════════════════
# NOTA: Estas páginas se sirven desde FastAPI pero mantienen compatibilidad
# con los templates Jinja2 originales de Flask.

@pages_router.get("/", response_class=HTMLResponse)
def index_page(request: Request, flask_session: dict = Depends(get_flask_session)):
    """
    Página principal (home).
    Equivalente a: GET / en app.py
    """
    from dockerlabs.models import Machine, Category, CompletedMachine
    from sqlalchemy import func

    with flask_app.app_context():
        # Obtener máquinas con categorías
        query = alchemy_db.session.query(Machine, Category.categoria).filter(
            Machine.origen == 'docker'
        ).outerjoin(
            Category, (Machine.id == Category.machine_id) & (Category.origen == 'docker')
        ).order_by(Machine.id.asc()).all()

        all_maquinas = []
        for m, cat_name in query:
            all_maquinas.append({
                'id': m.id,
                'nombre': m.nombre,
                'dificultad': m.dificultad,
                'clase': m.clase,
                'color': m.color,
                'autor': m.autor,
                'enlace_autor': m.enlace_autor,
                'fecha': m.fecha,
                'imagen': m.imagen,
                'imagen_url': f"/api/img/maquina/{m.id}",
                'descripcion': m.descripcion,
                'link_descarga': m.link_descarga,
                'categoria': cat_name
            })

        # Ordenar por fecha (más recientes primero)
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

        # Top 2 más recientes
        machine_ranks = {}
        top_2_items = maquinas_con_fecha[:2]
        for idx, (m, _) in enumerate(top_2_items):
            machine_ranks[m['id']] = idx + 1

        top_2_ids = {m['id'] for m, _ in top_2_items}
        top_2 = [m for m, _ in top_2_items]
        rest = [m for m in all_maquinas if m['id'] not in top_2_ids]
        maquinas = top_2 + rest

        # Máquinas completadas del usuario
        completed_machines = []
        user_id = flask_session.get('user_id')
        if user_id:
            comp_objs = CompletedMachine.query.filter_by(user_id=user_id).all()
            completed_machines = [c.machine_name.strip() for c in comp_objs]

        single_machine = len(maquinas) == 1

        categorias_map = {}
        for m in maquinas:
            categorias_map[m['id']] = m['categoria'] if m['categoria'] else ''

    # Crear sesión compatible con Flask para plantillas
    session_data = {}
    if user_id:
        session_data = {
            'user_id': user_id,
            'username': flask_session.get('username'),
            'role': flask_session.get('role')
        }

    context = {
        "request": request,
        "maquinas": maquinas,
        "completed_machines": completed_machines,
        "machine_ranks": machine_ranks,
        "single_machine": single_machine,
        "categorias_map": categorias_map,
        "current_user": {"is_authenticated": bool(user_id), "id": user_id},
        "session": session_data,
        "csrf_token_value": secrets.token_urlsafe(32),
        "url_for": url_for,
        "g": {"csp_nonce": secrets.token_urlsafe(32)}
    }
    return templates.TemplateResponse(request, "dockerlabs/home.html", context)


@pages_router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request, flask_session: dict = Depends(get_flask_session)):
    """
    Dashboard de usuario.
    Equivalente a: GET /dashboard en app.py
    Requiere autenticación.
    """
    user_id = flask_session.get('user_id')
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)

    role = flask_session.get('role', '')
    if role not in ['admin', 'moderador', 'jugador']:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    from dockerlabs.models import Machine

    with flask_app.app_context():
        maquinas = Machine.query.filter_by(origen='docker') \
                                .with_entities(Machine.id, Machine.nombre, Machine.autor) \
                                .order_by(Machine.nombre.asc()).all()

        current_username = flask_session.get('username')
        profile_image_url = get_fastapi_profile_image_url(
            username=current_username,
            user_id=user_id
        )

    # Crear sesión compatible con Flask para plantillas
    session_data = {}
    if user_id:
        session_data = {
            'user_id': user_id,
            'username': current_username,
            'role': role
        }

    context = {
        "request": request,
        "maquinas": maquinas,
        "profile_image_url": profile_image_url,
        "user": {"id": user_id, "username": current_username, "role": role},
        "current_user_role": role,
        "session": session_data,
        "csrf_token_value": secrets.token_urlsafe(32),
        "get_profile_image_url": get_fastapi_profile_image_url,
        "url_for": url_for,
        "g": {"csp_nonce": secrets.token_urlsafe(32)}
    }
    return templates.TemplateResponse(request, "dockerlabs/admin/dashboard.html", context)


@pages_router.get("/logout")
def logout_page(request: Request):
    """
    Logout endpoint.
    Equivalente a: GET /logout en auth.py
    """
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="session", path="/")
    return response


@pages_router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, flask_session: dict = Depends(get_flask_session)):
    """
    Página de login.
    Equivalente a: GET /login en auth.py
    """
    # Si ya está autenticado, redirigir al dashboard
    user_id = flask_session.get('user_id')
    if user_id:
        return RedirectResponse(url="/dashboard", status_code=302)

    # Generar y almacenar CSRF token en la sesión
    csrf_token = secrets.token_urlsafe(32)
    flask_session["csrf_token"] = csrf_token

    # Actualizar la cookie de sesión para incluir el CSRF token
    cookie_val = create_flask_session_cookie(
        flask_session.get('user_id') or 0,
        flask_session.get('username') or '',
        flask_session.get('role') or 'jugador',
        existing_session=flask_session
    )

    # Crear contexto para la plantilla
    context = {
        "request": request,
        "csrf_token_value": csrf_token,
        "url_for": url_for,
        "g": {"csp_nonce": secrets.token_urlsafe(32)},
        "session": flask_session,
        "success": None,
        "remaining": None
    }
    
    response = templates.TemplateResponse(request, "dockerlabs/auth/login.html", context)
    response.set_cookie(
        key="session",
        value=cookie_val,
        httponly=True,
        path="/",
        samesite="lax"
    )
    return response


@pages_router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, flask_session: dict = Depends(get_flask_session)):
    """
    Página de registro.
    Equivalente a: GET /register en auth.py
    """
    # Si ya está autenticado, redirigir al dashboard
    if flask_session.get('user_id'):
        return RedirectResponse(url="/dashboard", status_code=302)

    # Generar y almacenar CSRF token en la sesión
    csrf_token = secrets.token_urlsafe(32)
    flask_session["csrf_token"] = csrf_token

    # Actualizar la cookie de sesión para incluir el CSRF token
    cookie_val = create_flask_session_cookie(
        flask_session.get('user_id') or 0,
        flask_session.get('username') or '',
        flask_session.get('role') or 'jugador',
        existing_session=flask_session
    )
    
    # Crear sesión compatible con Flask para plantillas
    session_data = {}
    if flask_session.get('user_id'):
        session_data = {
            'user_id': flask_session.get('user_id'),
            'username': flask_session.get('username'),
            'role': flask_session.get('role')
        }

    context = {
        "remaining": request.query_params.get('remaining'),
        "session": session_data,
        "csrf_token_value": csrf_token,
        "url_for": url_for,
        "g": {"csp_nonce": secrets.token_urlsafe(32)}
    }
    response = templates.TemplateResponse(request, "dockerlabs/auth/register.html", context)
    response.set_cookie(
        key="session",
        value=cookie_val,
        httponly=True,
        path="/",
        samesite="lax"
    )
    return response


@pages_router.get("/recover", response_class=HTMLResponse)
def recover_page(request: Request, flask_session: dict = Depends(get_flask_session)):
    """
    Página de recuperación de contraseña.
    Equivalente a: GET /recover en auth.py
    """
    # Si ya está autenticado, redirigir al dashboard
    if flask_session.get('user_id'):
        return RedirectResponse(url="/dashboard", status_code=302)

    # Generar y almacenar CSRF token en la sesión
    csrf_token = secrets.token_urlsafe(32)
    flask_session["csrf_token"] = csrf_token

    # Actualizar la cookie de sesión para incluir el CSRF token
    cookie_val = create_flask_session_cookie(
        flask_session.get('user_id') or 0,
        flask_session.get('username') or '',
        flask_session.get('role') or 'jugador',
        existing_session=flask_session
    )
    
    # Crear sesión compatible con Flask para plantillas
    session_data = {}
    if flask_session.get('user_id'):
        session_data = {
            'user_id': flask_session.get('user_id'),
            'username': flask_session.get('username'),
            'role': flask_session.get('role')
        }

    context = {
        "session": session_data,
        "csrf_token_value": csrf_token,
        "url_for": url_for,
        "g": {"csp_nonce": secrets.token_urlsafe(32)}
    }
    response = templates.TemplateResponse(request, "dockerlabs/auth/recover.html", context)
    response.set_cookie(
        key="session",
        value=cookie_val,
        httponly=True,
        path="/",
        samesite="lax"
    )
    return response


# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINAS HTML - Fase 4b: Páginas de información
# ═══════════════════════════════════════════════════════════════════════════════

@pages_router.get("/instrucciones-uso", response_class=HTMLResponse)
def instrucciones_uso_page(request: Request):
    """Página de instrucciones de uso."""
    return templates.TemplateResponse(request, "dockerlabs/info/instrucciones_uso.html", {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}})


@pages_router.get("/soporte", response_class=HTMLResponse)
def soporte_page(request: Request):
    """Página de soporte."""
    return templates.TemplateResponse(request, "dockerlabs/info/soporte.html", {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}})


@pages_router.get("/equipo", response_class=HTMLResponse)
def equipo_page(request: Request):
    """Página del equipo."""
    return templates.TemplateResponse(request, "dockerlabs/equipo.html", {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}})


@pages_router.get("/enviar-maquina", response_class=HTMLResponse)
def enviar_maquina_page(request: Request):
    """Página para enviar máquina."""
    return templates.TemplateResponse(request, "dockerlabs/info/enviar_maquina.html", {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}})


@pages_router.get("/como-se-crea-una-maquina", response_class=HTMLResponse)
def como_se_crea_page(request: Request):
    """Página de cómo crear una máquina."""
    return templates.TemplateResponse(request, "dockerlabs/info/como_se_crea_una_maquina.html", {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}})


@pages_router.get("/agradecimientos", response_class=HTMLResponse)
def agradecimientos_page(request: Request):
    """Página de agradecimientos."""
    return templates.TemplateResponse(request, "dockerlabs/info/agradecimientos.html", {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}})


@pages_router.get("/terminos-condiciones", response_class=HTMLResponse)
def terminos_condiciones_page(request: Request):
    """Página de términos y condiciones."""
    return templates.TemplateResponse(request, "dockerlabs/info/terminos-condiciones.html", {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}})


@pages_router.get("/bug-bounty", response_class=HTMLResponse)
def bug_bounty_page(request: Request):
    """Página de bug bounty."""
    return templates.TemplateResponse(request, "dockerlabs/bug_bounty.html", {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}})


@pages_router.get("/politica-privacidad", response_class=HTMLResponse)
def politica_privacidad_page(request: Request):
    """Página de política de privacidad."""
    return templates.TemplateResponse(request, "politicas/politica_privacidad.html", {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}})


@pages_router.get("/politica-cookies", response_class=HTMLResponse)
def politica_cookies_page(request: Request):
    """Página de política de cookies."""
    return templates.TemplateResponse(request, "politicas/politica_cookies.html", {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}})


@pages_router.get("/condiciones-uso", response_class=HTMLResponse)
def condiciones_uso_page(request: Request):
    """Página de condiciones de uso."""
    return templates.TemplateResponse(request, "politicas/condiciones_uso.html", {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}})


# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINAS HTML - Fase 4c: Páginas de administración
# ═══════════════════════════════════════════════════════════════════════════════

def require_auth_and_role(flask_session: dict, allowed_roles: list):
    """Helper para verificar autenticación y roles."""
    user_id = flask_session.get('user_id')
    role = flask_session.get('role', '')
    if not user_id:
        return False, RedirectResponse(url="/login", status_code=302)
    if role not in allowed_roles:
        return False, RedirectResponse(url="/", status_code=302)
    return True, None


@pages_router.get("/gestion-usuarios", response_class=HTMLResponse)
def gestion_usuarios_page(request: Request, flask_session: dict = Depends(get_flask_session)):
    """Página de gestión de usuarios. Solo admin/moderador."""
    ok, redirect = require_auth_and_role(flask_session, ['admin', 'moderador'])
    if not ok:
        return redirect

    # Pagination parameters
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 10))
    search = request.query_params.get('search', '').strip()

    with flask_app.app_context():
        query = User.query

        # Apply search filter
        if search:
            query = query.filter(
                (User.username.ilike(f'%{search}%')) |
                (User.email.ilike(f'%{search}%')) |
                (User.role.ilike(f'%{search}%'))
            )

        # Get total count
        total = query.count()

        # Apply pagination
        usuarios = query.order_by(User.id.asc()).offset((page - 1) * per_page).limit(per_page).all()

        # Calculate pagination info
        total_pages = (total + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages

    return templates.TemplateResponse(
        request,
        "dockerlabs/admin/gestion_usuarios.html",
        {
            "usuarios": usuarios,
            "session": flask_session,
            "g": {"csp_nonce": secrets.token_urlsafe(32)},
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_prev": has_prev,
            "has_next": has_next,
            "search": search,
            "current_user_role": flask_session.get('role', '')
        }
    )


@pages_router.get("/gestion-maquinas", response_class=HTMLResponse)
def gestion_maquinas_page(request: Request, flask_session: dict = Depends(get_flask_session)):
    """Página de gestión de máquinas. Solo admin/moderador/jugador."""
    ok, redirect = require_auth_and_role(flask_session, ['admin', 'moderador', 'jugador'])
    if not ok:
        return redirect

    from dockerlabs.models import Machine, Category

    with flask_app.app_context():
        current_username = flask_session.get('username', '')
        role = flask_session.get('role', '')

        if role in ('admin', 'moderador'):
            maquinas_docker = Machine.query.filter_by(origen='docker').order_by(Machine.id.asc()).all()
            maquinas_bunker = Machine.query.filter_by(origen='bunker').order_by(Machine.id.asc()).all()
        else:
            if current_username:
                maquinas_docker = Machine.query.filter_by(origen='docker', autor=current_username).order_by(Machine.id.asc()).all()
                maquinas_bunker = Machine.query.filter_by(origen='bunker', autor=current_username).order_by(Machine.id.asc()).all()
            else:
                maquinas_docker = []
                maquinas_bunker = []

        # Obtener categorías
        categorias_map = {}
        if maquinas_docker:
            docker_cats = Category.query.filter_by(origen='docker').all()
            docker_lookup = {c.machine_id: c.categoria for c in docker_cats}
            for m in maquinas_docker:
                categorias_map[('docker', m.id)] = docker_lookup.get(m.id, '')

        if maquinas_bunker:
            bunker_ids = [m.id for m in maquinas_bunker]
            if bunker_ids:
                bunker_cats = Category.query.filter(
                    Category.origen == 'bunker',
                    Category.machine_id.in_(bunker_ids)
                ).all()
                bunker_lookup = {c.machine_id: c.categoria for c in bunker_cats}
                for m in maquinas_bunker:
                    categorias_map[('bunker', m.id)] = bunker_lookup.get(m.id, '')

    return templates.TemplateResponse(
        request,
        "dockerlabs/admin/gestion_maquinas.html",
        {
            "maquinas_docker": maquinas_docker,
            "maquinas_bunker": maquinas_bunker,
            "current_username": current_username,
            "categorias_map": categorias_map,
            "session": flask_session,
            "g": {"csp_nonce": secrets.token_urlsafe(32)}
        }
    )


@pages_router.get("/backups", response_class=HTMLResponse)
def backups_page(request: Request, flask_session: dict = Depends(get_flask_session)):
    """Página de backups. Solo admin."""
    ok, redirect = require_auth_and_role(flask_session, ['admin'])
    if not ok:
        return redirect

    return templates.TemplateResponse(
        request,
        "dockerlabs/admin/backups.html",
        {
            "session": flask_session,
            "g": {"csp_nonce": secrets.token_urlsafe(32)}
        }
    )

def _get_db_paths():
    db_path = flask_app.config.get('DATABASE')
    if not db_path:
        raise RuntimeError("DATABASE path is not configured")
    return {
        "db": db_path,
        "wal": f"{db_path}-wal",
        "shm": f"{db_path}-shm",
        "journal": f"{db_path}-journal",
    }

def _acquire_db_lock():
    db_paths = _get_db_paths()
    lock_path = f"{db_paths['db']}.lock"
    os.makedirs(os.path.dirname(db_paths['db']), exist_ok=True)
    lock_fh = open(lock_path, 'a+')
    fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
    return lock_fh

def _create_sqlite_snapshot_db(tmp_dir):
    db_paths = _get_db_paths()
    src_db = db_paths['db']
    snapshot_path = os.path.join(tmp_dir, os.path.basename(src_db))

    if not os.path.exists(src_db):
        raise FileNotFoundError("Database file not found")

    src = sqlite3.connect(src_db)
    try:
        try:
            src.execute("PRAGMA wal_checkpoint(FULL);")
        except Exception:
            pass

        dest = sqlite3.connect(snapshot_path)
        try:
            src.backup(dest)
            dest.commit()
        finally:
            dest.close()
    finally:
        src.close()

    return snapshot_path

@pages_router.post("/backups/download")
def download_backup(flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    ok, redirect = require_auth_and_role(flask_session, ['admin'])
    if not ok:
        return redirect

    lock_fh = _acquire_db_lock()
    try:
        alchemy_db.session.remove()
        alchemy_db.engine.dispose()

        with tempfile.TemporaryDirectory(prefix="dockerlabs_backup_") as tmp_dir:
            snapshot_db_path = _create_sqlite_snapshot_db(tmp_dir)

            db_paths = _get_db_paths()
            extras = []
            for k in ('wal', 'shm', 'journal'):
                p = db_paths[k]
                if os.path.exists(p) and os.path.isfile(p):
                    extras.append(p)

            zip_bytes = io.BytesIO()
            with zipfile.ZipFile(zip_bytes, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.write(snapshot_db_path, arcname=os.path.basename(snapshot_db_path))
                for p in extras:
                    zf.write(p, arcname=os.path.basename(p))

            zip_bytes.seek(0)
            return StreamingResponse(
                zip_bytes,
                media_type='application/zip',
                headers={'Content-Disposition': 'attachment; filename="dockerlabs_sqlite_backup.zip"'}
            )
    finally:
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
        finally:
            lock_fh.close()

@pages_router.post("/backups/restore")
async def restore_backup(
    backup_zip: UploadFile = File(...),
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    ok, redirect = require_auth_and_role(flask_session, ['admin'])
    if not ok:
        return redirect

    if not backup_zip or not (backup_zip.filename or '').lower().endswith('.zip'):
        flask_session['_flashes'] = [('danger', 'Debes proporcionar un archivo .zip')]
        cookie = set_flask_session_cookie(flask_session)
        resp = RedirectResponse(url='/backups', status_code=302)
        resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
        return resp

    lock_fh = _acquire_db_lock()
    try:
        with tempfile.TemporaryDirectory(prefix="dockerlabs_restore_") as tmp_dir:
            zip_path = os.path.join(tmp_dir, 'upload.zip')
            
            content = await backup_zip.read()
            with open(zip_path, "wb") as f:
                f.write(content)

            extract_dir = os.path.join(tmp_dir, 'extracted')
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)

            db_paths = _get_db_paths()
            expected_db_name = os.path.basename(db_paths['db'])
            candidate_db = os.path.join(extract_dir, expected_db_name)
            if not os.path.exists(candidate_db):
                db_candidates = []
                for root, _, files in os.walk(extract_dir):
                    for fn in files:
                        if fn.lower().endswith('.db'):
                            db_candidates.append(os.path.join(root, fn))
                if len(db_candidates) != 1:
                    flask_session['_flashes'] = [('danger', 'El .zip debe contener exactamente un archivo .db (o el nombre esperado).')]
                    cookie = set_flask_session_cookie(flask_session)
                    resp = RedirectResponse(url='/backups', status_code=302)
                    resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
                    return resp
                candidate_db = db_candidates[0]

            candidate_wal = None
            candidate_shm = None
            candidate_journal = None
            for fn in os.listdir(extract_dir):
                if fn == os.path.basename(db_paths['wal']):
                    candidate_wal = os.path.join(extract_dir, fn)
                elif fn == os.path.basename(db_paths['shm']):
                    candidate_shm = os.path.join(extract_dir, fn)
                elif fn == os.path.basename(db_paths['journal']):
                    candidate_journal = os.path.join(extract_dir, fn)

            alchemy_db.session.remove()
            alchemy_db.engine.dispose()

            db_dir = os.path.dirname(db_paths['db'])
            os.makedirs(db_dir, exist_ok=True)

            for p in (db_paths['wal'], db_paths['shm'], db_paths['journal']):
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass

            with tempfile.NamedTemporaryFile(dir=db_dir, prefix='.restore_tmp.', suffix='.db', delete=False) as tmp_db_fh:
                tmp_db_path = tmp_db_fh.name
            try:
                shutil.copyfile(candidate_db, tmp_db_path)
                os.replace(tmp_db_path, db_paths['db'])
            finally:
                try:
                    if os.path.exists(tmp_db_path):
                        os.remove(tmp_db_path)
                except Exception:
                    pass

            if candidate_wal:
                shutil.copyfile(candidate_wal, db_paths['wal'] + '.tmp')
                os.replace(db_paths['wal'] + '.tmp', db_paths['wal'])
            if candidate_shm:
                shutil.copyfile(candidate_shm, db_paths['shm'] + '.tmp')
                os.replace(db_paths['shm'] + '.tmp', db_paths['shm'])
            if candidate_journal:
                shutil.copyfile(candidate_journal, db_paths['journal'] + '.tmp')
                os.replace(db_paths['journal'] + '.tmp', db_paths['journal'])

        flask_session['_flashes'] = [('success', 'Backup restaurado correctamente.')]
        cookie = set_flask_session_cookie(flask_session)
        resp = RedirectResponse(url='/backups', status_code=302)
        resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
        return resp
    except zipfile.BadZipFile:
        flask_session['_flashes'] = [('danger', 'El archivo .zip no es válido.')]
        cookie = set_flask_session_cookie(flask_session)
        resp = RedirectResponse(url='/backups', status_code=302)
        resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
        return resp
    except Exception as e:
        flask_session['_flashes'] = [('danger', f'Error al restaurar el backup: {str(e)}')]
        cookie = set_flask_session_cookie(flask_session)
        resp = RedirectResponse(url='/backups', status_code=302)
        resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
        return resp
    finally:
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
        finally:
            lock_fh.close()


@pages_router.get("/pending-machines", response_class=HTMLResponse)
def pending_machines_page(request: Request, flask_session: dict = Depends(get_flask_session)):
    """Página de máquinas pendientes. Admin/moderador."""
    ok, redirect = require_auth_and_role(flask_session, ['admin', 'moderador'])
    if not ok:
        return redirect

    from dockerlabs.models import PendingMachineSubmission

    with flask_app.app_context():
        machines = PendingMachineSubmission.query.order_by(
            PendingMachineSubmission.submitted_at.desc()
        ).all()

    return templates.TemplateResponse(
        request,
        "dockerlabs/admin/pending_machines.html",
        {
            "machines": machines,
            "session": flask_session,
            "g": {"csp_nonce": secrets.token_urlsafe(32)}
        }
    )


@pages_router.get("/user-pending", response_class=HTMLResponse)
def user_pending_page(request: Request, flask_session: dict = Depends(get_flask_session)):
    """Página de máquinas pendientes del usuario."""
    user_id = flask_session.get('user_id')
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        request,
        "dockerlabs/user/user_pending.html",
        {
            "username": flask_session.get('username'),
            "session": flask_session,
            "g": {"csp_nonce": secrets.token_urlsafe(32)}
        }
    )


@pages_router.get("/writeups-recibidos", response_class=HTMLResponse)
def writeups_recibidos_page(request: Request, flask_session: dict = Depends(get_flask_session)):
    """Página de writeups recibidos. Admin/moderador."""
    ok, redirect = require_auth_and_role(flask_session, ['admin', 'moderador'])
    if not ok:
        return redirect

    return templates.TemplateResponse(
        request,
        "dockerlabs/user/writeups_recibidos.html",
        {
            "session": flask_session,
            "g": {"csp_nonce": secrets.token_urlsafe(32)}
        }
    )


@pages_router.get("/writeups-publicados", response_class=HTMLResponse)
def writeups_publicados_page(request: Request, flask_session: dict = Depends(get_flask_session)):
    """Página de writeups publicados. Admin/moderador/jugador."""
    ok, redirect = require_auth_and_role(flask_session, ['admin', 'moderador', 'jugador'])
    if not ok:
        return redirect


    with flask_app.app_context():
        user = User.query.get(flask_session.get('user_id')) if flask_session.get('user_id') else None

    return templates.TemplateResponse(
        request,
        "dockerlabs/user/writeups_publicados.html",
        {
            "user": user,
            "session": flask_session,
            "g": {"csp_nonce": secrets.token_urlsafe(32)}
        }
    )


@pages_router.get("/peticiones-writeups", response_class=HTMLResponse)
def peticiones_writeups_page(request: Request, flask_session: dict = Depends(get_flask_session)):
    """Página de peticiones de writeups. Admin/moderador."""
    ok, redirect = require_auth_and_role(flask_session, ['admin', 'moderador'])
    if not ok:
        return redirect

    from dockerlabs.models import WriteupEditRequest

    with flask_app.app_context():
        requests = WriteupEditRequest.query.order_by(WriteupEditRequest.id.desc()).all()

    return templates.TemplateResponse(
        request,
        "dockerlabs/admin/peticiones_writeups.html",
        {
            "peticiones": requests,
            "session": flask_session,
            "g": {"csp_nonce": secrets.token_urlsafe(32)}
        }
    )


@pages_router.get("/estadisticas", response_class=HTMLResponse)
def estadisticas_page(request: Request):
    """Página de estadísticas de la plataforma."""
    from dockerlabs.models import Machine, Writeup, User

    def get_distribution_by_year(items, date_extractor):
        """Helper para calcular distribución por año."""
        year_counts = {}
        total = 0
        for item in items:
            try:
                year = date_extractor(item)
                if year:
                    year_counts[year] = year_counts.get(year, 0) + 1
                    total += 1
            except:
                continue

        distribution = {}
        if total > 0:
            for year, count in year_counts.items():
                distribution[year] = round((count / total) * 100, 2)

        return dict(sorted(distribution.items()))

    with flask_app.app_context():
        machines = Machine.query.all()
        def machine_date_extractor(m):
            try:
                parts = m.fecha.split('/')
                if len(parts) == 3:
                    return int(parts[2])
            except:
                return None
            return None

        machine_stats = get_distribution_by_year(machines, machine_date_extractor)

        # Writeups
        writeups = Writeup.query.all()
        def writeup_date_extractor(w):
            return w.created_at.year if w.created_at else None

        writeup_stats = get_distribution_by_year(writeups, writeup_date_extractor)

        # Usuarios
        users = User.query.all()
        def user_date_extractor(u):
            return u.created_at.year if u.created_at else None

        user_stats = get_distribution_by_year(users, user_date_extractor)

    return templates.TemplateResponse(
        request,
        "dockerlabs/user/estadisticas.html",
        {
            "machine_stats": machine_stats,
            "writeup_stats": writeup_stats,
            "user_stats": user_stats,
            "session": {},
            "g": {"csp_nonce": secrets.token_urlsafe(32)}
        }
    )


# Notification endpoints
class SendNotificationRequest(BaseModel):
    title: str
    content: str


@api_router.post("/notifications/send")
def api_send_notification(
    request_data: SendNotificationRequest,
    flask_session: dict = Depends(get_flask_session)
):
    """Enviar una notificación (solo admin/moderador)."""
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

    from dockerlabs.models import User, Notification

    with flask_app.app_context():
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'moderador']:
            return JSONResponse(status_code=403, content={"success": False, "message": "No tienes permisos"})

        if not request_data.title or not request_data.content:
            return JSONResponse(status_code=400, content={"success": False, "message": "Título y contenido son requeridos"})

        if len(request_data.title) > 200:
            return JSONResponse(status_code=400, content={"success": False, "message": "Título demasiado largo (máximo 200 caracteres)"})

        notification = Notification(
            sender_id=user_id,
            title=request_data.title,
            content=request_data.content
        )
        alchemy_db.session.add(notification)
        alchemy_db.session.commit()

    return {"success": True, "message": "Notificación enviada"}


@api_router.get("/notifications")
def api_get_notifications(flask_session: dict = Depends(get_flask_session)):
    """Obtener notificaciones del usuario."""
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

    from dockerlabs.models import Notification, User

    with flask_app.app_context():
        notifications = Notification.query.order_by(Notification.created_at.desc()).limit(50).all()
        result = []
        for notif in notifications:
            sender = User.query.get(notif.sender_id)
            result.append({
                "id": notif.id,
                "title": notif.title,
                "content": notif.content,
                "created_at": notif.created_at.isoformat(),
                "read": notif.read,
                "sender": sender.username if sender else "Desconocido"
            })

        unread_count = Notification.query.filter_by(read=False).count()

    return {"success": True, "notifications": result, "unread_count": unread_count}


@api_router.post("/notifications/{notification_id}/read")
def api_mark_notification_read(
    notification_id: int,
    flask_session: dict = Depends(get_flask_session)
):
    """Marcar notificación como leída."""
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

    from dockerlabs.models import Notification

    with flask_app.app_context():
        notification = Notification.query.get(notification_id)
        if not notification:
            return JSONResponse(status_code=404, content={"success": False, "message": "Notificación no encontrada"})

        notification.read = True
        alchemy_db.session.commit()

    return {"success": True}


@api_router.delete("/notifications/{notification_id}")
def api_delete_notification(
    notification_id: int,
    flask_session: dict = Depends(get_flask_session)
):
    """Eliminar notificación."""
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

    from dockerlabs.models import Notification

    with flask_app.app_context():
        notification = Notification.query.get(notification_id)
        if not notification:
            return JSONResponse(status_code=404, content={"success": False, "message": "Notificación no encontrada"})

        alchemy_db.session.delete(notification)
        alchemy_db.session.commit()

    return {"success": True, "message": "Notificación eliminada"}


# ═══════════════════════════════════════════════════════════════════════════════
# MÁQUINAS - Migrado desde maquinas.py
# ═══════════════════════════════════════════════════════════════════════════════

from dockerlabs.models import MachineClaim, MachineEditRequest

class ActualizarMaquinaRequest(BaseModel):
    id: int
    origen: str
    nombre: str
    dificultad: str
    autor: str
    enlace_autor: Optional[str] = ""
    fecha: str
    imagen: Optional[str] = ""
    descripcion: str
    link_descarga: str
    categoria: Optional[str] = ""

class ReclamarMaquinaRequest(BaseModel):
    maquina_nombre: str
    contacto: str
    prueba: str

class AddMaquinaRequest(BaseModel):
    nombre: str
    dificultad: Optional[str] = ""
    autor: str
    fecha: str
    descripcion: str
    link_descarga: str
    imagen: Optional[str] = ""
    destino: Optional[str] = "docker"
    pin: Optional[str] = ""
    entorno_real: Optional[bool] = False
    categoria: Optional[str] = ""

def _difficulty_to_color_clase(dificultad: str):
    d = dificultad.strip().lower()
    if "muy" in d:
        return "muy-facil", "Muy Fácil", "#43959b"
    elif "facil" in d or "fácil" in d:
        return "facil", "Fácil", "#8bc34a"
    elif "medio" in d:
        return "medio", "Medio", "#e0a553"
    else:
        return "dificil", "Difícil", "#d83c31"


@api_router.post("/gestion-maquinas/actualizar")
async def api_actualizar_maquina(
    data: ActualizarMaquinaRequest,
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    """API: Actualizar datos de una máquina."""
    role = flask_session.get('role', '')
    username = (flask_session.get('username') or '').strip()
    user_id = flask_session.get('user_id')

    if not user_id:
        return JSONResponse(status_code=401, content={"error": "No autenticado"})
    if data.origen not in ('docker', 'bunker'):
        return JSONResponse(status_code=400, content={"error": "Origen inválido"})

    clase, dificultad_texto, color = _difficulty_to_color_clase(data.dificultad)

    with flask_app.app_context():
        maquina = Machine.query.get(data.id)
        if not maquina:
            return JSONResponse(status_code=404, content={"error": "Máquina no encontrada"})

        if role not in ('admin', 'moderador'):
            if role == 'jugador' and maquina.autor == username:
                import json as _json
                nuevos_datos = _json.dumps({
                    "nombre": data.nombre, "dificultad": dificultad_texto,
                    "clase": clase, "color": color, "autor": data.autor,
                    "enlace_autor": data.enlace_autor, "fecha": data.fecha,
                    "imagen": data.imagen, "descripcion": data.descripcion,
                    "link_descarga": data.link_descarga
                })
                try:
                    edit_req = MachineEditRequest(machine_id=data.id, origen=data.origen, autor=username, nuevos_datos=nuevos_datos, estado='pendiente')
                    alchemy_db.session.add(edit_req)
                    alchemy_db.session.commit()
                    return {"success": True, "message": "Solicitud de edición enviada para revisión"}
                except Exception as e:
                    alchemy_db.session.rollback()
                    return JSONResponse(status_code=500, content={"error": str(e)})
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        try:
            maquina.nombre = data.nombre
            maquina.dificultad = dificultad_texto
            maquina.clase = clase
            maquina.color = color
            maquina.autor = data.autor
            maquina.enlace_autor = data.enlace_autor or ""
            maquina.fecha = data.fecha
            maquina.imagen = data.imagen or ""
            maquina.descripcion = data.descripcion
            maquina.link_descarga = data.link_descarga
            alchemy_db.session.commit()

            cat_obj = Category.query.filter_by(machine_id=data.id, origen=data.origen).first()
            if data.categoria:
                if cat_obj:
                    cat_obj.categoria = data.categoria
                else:
                    alchemy_db.session.add(Category(machine_id=data.id, origen=data.origen, categoria=data.categoria))
            else:
                if cat_obj:
                    alchemy_db.session.delete(cat_obj)
            alchemy_db.session.commit()

            if data.origen == 'docker':
                from dockerlabs.maquinas import recalcular_ranking_creadores
                recalcular_ranking_creadores()

            return {"success": True, "message": "Máquina actualizada correctamente"}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})


@api_router.post("/gestion-maquinas/eliminar")
def api_eliminar_maquina(
    machine_id: int,
    origen: str,
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    """API: Eliminar una máquina. Solo admin/moderador."""
    role = flask_session.get('role', '')
    user_id = flask_session.get('user_id')
    if not user_id or role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
    if origen not in ('docker', 'bunker'):
        return JSONResponse(status_code=400, content={"error": "Origen inválido"})

    with flask_app.app_context():
        maquina = Machine.query.get(machine_id)
        if not maquina:
            return JSONResponse(status_code=404, content={"error": "Máquina no encontrada"})
        try:
            if origen == 'bunker':
                from bunkerlabs.models import BunkerSolve
                BunkerSolve.query.filter_by(machine_id=machine_id).delete()
            alchemy_db.session.delete(maquina)
            alchemy_db.session.commit()
            if origen == 'docker':
                from dockerlabs.maquinas import recalcular_ranking_creadores
                recalcular_ranking_creadores()
            return {"success": True, "message": "Máquina eliminada correctamente"}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})


@pages_router.get("/add-maquina", response_class=HTMLResponse)
def add_maquina_page_get(request: Request, flask_session: dict = Depends(get_flask_session)):
    """Página de añadir máquina. Solo admin."""
    ok, redir = require_auth_and_role(flask_session, ['admin'])
    if not ok:
        return redir
    return templates.TemplateResponse(
        request,
        "dockerlabs/info/add-maquina.html",
        {"error": None, "session": flask_session, "g": {"csp_nonce": secrets.token_urlsafe(32)}}
    )


@api_router.post("/add-maquina")
async def api_add_maquina(
    data: AddMaquinaRequest,
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    """API: Añadir una nueva máquina. Solo admin."""
    role = flask_session.get('role', '')
    user_id = flask_session.get('user_id')
    if not user_id or role != 'admin':
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    with flask_app.app_context():
        if not User.query.filter_by(username=data.autor).first():
            return JSONResponse(status_code=400, content={"error": "El autor no es un usuario registrado"})

        try:
            from datetime import datetime as _dt
            fecha = _dt.strptime(data.fecha, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return JSONResponse(status_code=400, content={"error": "Formato de fecha inválido (YYYY-MM-DD)"})

        user_obj = User.query.get(user_id)
        enlace_autor = ""
        if user_obj:
            enlace_autor = user_obj.youtube_url or user_obj.github_url or user_obj.linkedin_url or ""

        imagen = data.imagen or "dockerlabs/images/logos/logo.png"

        if data.destino == 'bunker' and data.entorno_real:
            clase, dificultad_texto, color = "real", "Real", "#ffffff"
        else:
            clase, dificultad_texto, color = _difficulty_to_color_clase(data.dificultad)

        try:
            new_machine = Machine(
                nombre=data.nombre, dificultad=dificultad_texto, clase=clase, color=color,
                autor=data.autor, enlace_autor=enlace_autor, fecha=fecha, imagen=imagen,
                descripcion=data.descripcion, link_descarga=data.link_descarga,
                pin=data.pin if data.destino == 'bunker' else None,
                origen=data.destino or 'docker'
            )
            alchemy_db.session.add(new_machine)
            alchemy_db.session.commit()
            if data.destino == 'docker':
                from dockerlabs.maquinas import recalcular_ranking_creadores
                recalcular_ranking_creadores()
            redirect_url = '/bunkerlabs' if data.destino == 'bunker' else '/'
            return {"success": True, "message": "Máquina añadida correctamente", "redirect_url": redirect_url}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})


@api_router.post("/reclamar-maquina")
def api_reclamar_maquina(
    data: ReclamarMaquinaRequest,
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    """API: Reclamar autoría de una máquina."""
    user_id = flask_session.get('user_id')
    username = (flask_session.get('username') or '').strip()
    role = flask_session.get('role', '')
    if not user_id or role not in ('jugador', 'admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    with flask_app.app_context():
        try:
            alchemy_db.session.add(MachineClaim(user_id=user_id, username=username, maquina_nombre=data.maquina_nombre, contacto=data.contacto, prueba=data.prueba, estado='pendiente'))
            alchemy_db.session.commit()
            return {"success": True, "message": "Reclamación enviada correctamente"}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})


@api_router.post("/claims/{claim_id}/approve")
def api_approve_claim(claim_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    """API: Aprobar reclamación de máquina. Solo admin."""
    ok, _ = require_auth_and_role(flask_session, ['admin'])
    if not ok:
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
    with flask_app.app_context():
        claim = MachineClaim.query.get(claim_id)
        if not claim:
            return JSONResponse(status_code=404, content={"error": "No encontrada"})
        try:
            maquina = Machine.query.filter_by(nombre=claim.maquina_nombre).first()
            if maquina:
                maquina.autor = claim.username
            claim.estado = 'aprobada'
            alchemy_db.session.commit()
            from dockerlabs.maquinas import recalcular_ranking_creadores
            recalcular_ranking_creadores()
            return {"success": True}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})


@api_router.post("/claims/{claim_id}/reject")
def api_reject_claim(claim_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    """API: Rechazar reclamación. Solo admin."""
    ok, _ = require_auth_and_role(flask_session, ['admin'])
    if not ok:
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
    with flask_app.app_context():
        claim = MachineClaim.query.get(claim_id)
        if not claim:
            return JSONResponse(status_code=404, content={"error": "No encontrada"})
        try:
            alchemy_db.session.delete(claim)
            alchemy_db.session.commit()
            return {"success": True}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})


@api_router.post("/claims/{claim_id}/revert")
def api_revert_claim(claim_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    """API: Revertir reclamación a pendiente. Admin/moderador."""
    ok, _ = require_auth_and_role(flask_session, ['admin', 'moderador'])
    if not ok:
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
    with flask_app.app_context():
        claim = MachineClaim.query.get(claim_id)
        if not claim:
            return JSONResponse(status_code=404, content={"error": "No encontrada"})
        claim.estado = 'pendiente'
        alchemy_db.session.commit()
        return {"success": True}


@api_router.post("/machine-edit-requests/{request_id}/approve")
def api_approve_machine_edit(request_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    """API: Aprobar edición de máquina. Admin/moderador."""
    ok, _ = require_auth_and_role(flask_session, ['admin', 'moderador'])
    if not ok:
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
    with flask_app.app_context():
        req = MachineEditRequest.query.get(request_id)
        if not req:
            return JSONResponse(status_code=404, content={"error": "No encontrada"})
        try:
            import json as _json
            nuevos = _json.loads(req.nuevos_datos)
        except Exception:
            nuevos = {}
        maquina = Machine.query.get(req.machine_id)
        if maquina:
            for field in ("nombre","dificultad","clase","color","autor","enlace_autor","fecha","imagen","descripcion","link_descarga"):
                val = nuevos.get(field)
                if val:
                    setattr(maquina, field, val)
            alchemy_db.session.commit()
            if req.origen == 'docker':
                from dockerlabs.maquinas import recalcular_ranking_creadores
                recalcular_ranking_creadores()
        req.estado = 'aprobada'
        alchemy_db.session.commit()
        return {"success": True}


@api_router.post("/machine-edit-requests/{request_id}/reject")
def api_reject_machine_edit(request_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    """API: Rechazar edición de máquina. Admin/moderador."""
    ok, _ = require_auth_and_role(flask_session, ['admin', 'moderador'])
    if not ok:
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
    with flask_app.app_context():
        req = MachineEditRequest.query.get(request_id)
        if not req:
            return JSONResponse(status_code=404, content={"error": "No encontrada"})
        req.estado = 'rechazada'
        alchemy_db.session.commit()
        return {"success": True}


@api_router.post("/machine-edit-requests/{request_id}/revert")
def api_revert_machine_edit(request_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    """API: Revertir edición a pendiente. Admin/moderador."""
    ok, _ = require_auth_and_role(flask_session, ['admin', 'moderador'])
    if not ok:
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
    with flask_app.app_context():
        req = MachineEditRequest.query.get(request_id)
        if not req:
            return JSONResponse(status_code=404, content={"error": "No encontrada"})
        req.estado = 'pendiente'
        alchemy_db.session.commit()
        return {"success": True}


@pages_router.get("/maquinas-hechas", response_class=HTMLResponse)
def maquinas_hechas_page(request: Request, flask_session: dict = Depends(get_flask_session)):
    """Página de máquinas completadas por el usuario."""
    user_id = flask_session.get('user_id')
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)

    with flask_app.app_context():
        results = alchemy_db.session.query(
            CompletedMachine.machine_name,
            CompletedMachine.completed_at,
            Machine.id,
            Machine.dificultad,
            Machine.color,
            Machine.imagen,
            Machine.clase,
            Machine.autor
        ).outerjoin(Machine, CompletedMachine.machine_name == Machine.nombre) \
         .filter(CompletedMachine.user_id == user_id) \
         .order_by(CompletedMachine.completed_at.desc()).all()

        completed_machines = []
        for row in results:
            completed_machines.append({
                "machine_name": row.machine_name,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                "machine_id": row.id,
                "machine_logo_url": f'/img/maquina/{row.id}' if row.id else '/static/dockerlabs/images/logos/logo.png',
                "dificultad": row.dificultad,
                "color": row.color,
                "imagen": row.imagen,
                "clase": row.clase,
                "autor": row.autor
            })

        total_machines = Machine.query.filter_by(origen='docker').count()
        completed_count = len(completed_machines)
        completion_percentage = round((completed_count / total_machines * 100), 1) if total_machines > 0 else 0

    return templates.TemplateResponse(
        request,
        "dockerlabs/maquinas_hechas.html",
        {
            "completed_machines": completed_machines,
            "total_machines": total_machines,
            "completed_count": completed_count,
            "completion_percentage": completion_percentage,
            "session": flask_session,
            "g": {"csp_nonce": secrets.token_urlsafe(32)}
        }
    )


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH - Migrado desde auth.py
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi import Form

@pages_router.post("/request_username_change")
async def form_request_username_change(
    request: Request,
    requested_username: str = Form(...),
    reason: str = Form(""),
    contacto_opcional: str = Form(""),
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    """
    Versión form-based de solicitud de cambio de nombre.
    Equivalente a POST /request_username_change en auth.py (Flask).
    Redirige con mensaje flash en la sesión.
    """
    import re as _re

    user_id = flask_session.get('user_id')
    old_username = (flask_session.get('username') or '').strip()

    def redirect_with_flash(msg: str, category: str = "danger"):
        flask_session['_flashes'] = [(category, msg)]
        cookie = set_flask_session_cookie(flask_session)
        resp = RedirectResponse(url='/dashboard', status_code=302)
        resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
        return resp

    if not user_id:
        return redirect_with_flash("Debes iniciar sesión para solicitar un cambio de nombre.", "warning")

    requested_username = requested_username.strip()
    if not requested_username:
        return redirect_with_flash("Debes proporcionar un nuevo nombre de usuario.")

    if not _re.match(r'^[a-zA-Z0-9_-]{3,20}$', requested_username):
        return redirect_with_flash("El nombre debe tener entre 3 y 20 caracteres y solo letras, números, guiones y guiones bajos.")

    with flask_app.app_context():
        from dockerlabs.models import UsernameChangeRequest as UCR
        existing = UCR.query.filter_by(user_id=user_id, estado='pendiente').first()
        if existing:
            return redirect_with_flash("Ya tienes una solicitud de cambio de nombre pendiente.", "warning")

        try:
            new_req = UCR(
                user_id=user_id,
                old_username=old_username,
                requested_username=requested_username,
                reason=(reason or '').strip(),
                contacto_opcional=(contacto_opcional or '').strip(),
                estado='pendiente'
            )
            alchemy_db.session.add(new_req)
            alchemy_db.session.commit()
            return redirect_with_flash("Solicitud enviada correctamente. El equipo de administración la revisará pronto.", "success")
        except Exception as e:
            alchemy_db.session.rollback()
            return redirect_with_flash(f"Error al enviar la solicitud: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# BUNKERLABS - Páginas HTML migradas desde bunkerlabs/bunkerlabs.py
# ═══════════════════════════════════════════════════════════════════════════════

from bunkerlabs.models import BunkerAccessToken, BunkerSolve, BunkerAccessLog

class CreateBunkerTokenRequest(BaseModel):
    nombre: str
    password: str

class AddBunkerWriteupRequest(BaseModel):
    maquina: str
    autor: str
    url: str
    tipo: str
    locked: Optional[bool] = False


@pages_router.get("/bunkerlabs/login", response_class=HTMLResponse)
@pages_router.post("/bunkerlabs/login", response_class=HTMLResponse)
async def bunkerlabs_login_page(
    request: Request,
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    """Login de BunkerLabs."""
    if flask_session.get('bunkerlabs_ok'):
        return RedirectResponse(url='/bunkerlabs', status_code=302)

    error = None

    if request.method == "POST":
        form = await request.form()
        token_introducido = (form.get('password') or '').strip()

        if not token_introducido:
            error = "Debes introducir una contraseña de acceso."
        else:
            with flask_app.app_context():
                token_obj = BunkerAccessToken.query.filter_by(token=token_introducido, activo=1).first()
                if token_obj:
                    docker_username = flask_session.get('username')
                    if docker_username:
                        token_obj.nombre = docker_username
                        token_obj.last_accessed = datetime.utcnow()
                        alchemy_db.session.add(BunkerAccessLog(token_id=token_obj.id, user_nombre=docker_username, accessed_at=datetime.utcnow()))
                        alchemy_db.session.commit()
                        flask_session['bunkerlabs_nombre'] = docker_username
                    else:
                        flask_session['bunkerlabs_nombre'] = token_obj.nombre
                        token_obj.last_accessed = datetime.utcnow()
                        alchemy_db.session.add(BunkerAccessLog(token_id=token_obj.id, user_nombre=token_obj.nombre, accessed_at=datetime.utcnow()))
                        alchemy_db.session.commit()

                    flask_session['bunkerlabs_ok'] = True
                    flask_session['bunkerlabs_id'] = token_obj.id
                    cookie = set_flask_session_cookie(flask_session)
                    resp = RedirectResponse(url='/bunkerlabs', status_code=302)
                    resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
                    return resp
                else:
                    error = "Contraseña incorrecta o inactiva."

    csrf_token = flask_session.get("csrf_token")
    if not csrf_token:
        csrf_token = secrets.token_urlsafe(32)
        flask_session["csrf_token"] = csrf_token
        
    context = {
        "error": error, 
        "session": flask_session, 
        "csrf_token_value": csrf_token,
        "g": {"csp_nonce": secrets.token_urlsafe(32)}
    }
    
    response = templates.TemplateResponse(request, "bunkerlabs/login-bunkerlabs.html", context)
    response.set_cookie("session", set_flask_session_cookie(flask_session), httponly=True, path="/", samesite="lax")
    return response


@pages_router.get("/bunkerlabs/guest")
def bunkerlabs_guest(request: Request, flask_session: dict = Depends(get_flask_session)):
    """Acceso en modo invitado a BunkerLabs."""
    is_unauthenticated = flask_session.get('user_id') is None
    flask_session['bunkerlabs_ok'] = True
    flask_session['bunkerlabs_guest'] = True
    flask_session['bunkerlabs_nombre'] = "Invitado"
    flask_session['bunkerlabs_id'] = None
    flask_session['bunkerlabs_unauthenticated'] = is_unauthenticated
    cookie = set_flask_session_cookie(flask_session)
    resp = RedirectResponse(url='/bunkerlabs', status_code=302)
    resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
    return resp


@pages_router.get("/bunkerlabs/logout")
def bunkerlabs_logout(request: Request, flask_session: dict = Depends(get_flask_session)):
    """Logout de BunkerLabs. Limpia las claves de sesión de BunkerLabs."""
    for key in ('bunkerlabs_ok', 'bunkerlabs_guest', 'bunkerlabs_nombre', 'bunkerlabs_id'):
        flask_session.pop(key, None)
    cookie = set_flask_session_cookie(flask_session)
    resp = RedirectResponse(url='/bunkerlabs/login', status_code=302)
    resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
    return resp


@pages_router.get("/bunkerlabs", response_class=HTMLResponse)
@pages_router.get("/bunkerlabs/", response_class=HTMLResponse)
async def bunkerlabs_home(
    request: Request,
    token: Optional[str] = None,
    flask_session: dict = Depends(get_flask_session)
):
    """Página principal de BunkerLabs."""
    if token:
        with flask_app.app_context():
            token_obj = BunkerAccessToken.query.filter_by(token=token, activo=1).first()
            if token_obj:
                docker_username = flask_session.get('username')
                docker_user_id = flask_session.get('user_id')
                if docker_username and docker_user_id:
                    token_obj.nombre = docker_username
                    flask_session['bunkerlabs_nombre'] = docker_username
                    flask_session['bunkerlabs_anonymous'] = False
                else:
                    flask_session['bunkerlabs_nombre'] = 'Anónimo'
                    flask_session['bunkerlabs_anonymous'] = True
                flask_session['bunkerlabs_ok'] = True
                token_obj.last_accessed = datetime.utcnow()
                alchemy_db.session.add(BunkerAccessLog(token_id=token_obj.id, user_nombre=flask_session['bunkerlabs_nombre'], accessed_at=datetime.utcnow()))
                alchemy_db.session.commit()
                cookie = set_flask_session_cookie(flask_session)
                resp = RedirectResponse(url='/bunkerlabs', status_code=302)
                resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
                return resp
            else:
                flask_session['_flashes'] = [('error', 'El enlace de acceso no es válido o está inactivo.')]
                cookie = set_flask_session_cookie(flask_session)
                resp = RedirectResponse(url='/bunkerlabs/login', status_code=302)
                resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
                return resp

    if 'bunkerlabs_nombre' not in flask_session or not flask_session.get('bunkerlabs_ok'):
        return RedirectResponse(url='/bunkerlabs/login', status_code=302)

    with flask_app.app_context():
        maquinas = Machine.query.filter_by(origen='bunker').order_by(Machine.id.asc()).all()

    return templates.TemplateResponse(
        request,
        "bunkerlabs/home.html",
        {
            "maquinas": maquinas,
            "is_guest": flask_session.get('bunkerlabs_guest', False),
            "is_anonymous": flask_session.get('bunkerlabs_anonymous', False),
            "is_unauthenticated_guest": flask_session.get('bunkerlabs_unauthenticated', False),
            "session": flask_session,
            "g": {"csp_nonce": secrets.token_urlsafe(32)}
        }
    )


@pages_router.get("/bunkerlabs/accesos", response_class=HTMLResponse)
@pages_router.post("/bunkerlabs/accesos", response_class=HTMLResponse)
async def accesos_bunkerlabs(
    request: Request,
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    """Gestión de accesos de BunkerLabs. Solo admin."""
    ok, redir = require_auth_and_role(flask_session, ['admin'])
    if not ok:
        return redir

    error = None
    success = None

    if request.method == "POST":
        form = await request.form()
        nombre = (form.get('nombre') or '').strip()
        password = (form.get('password') or '').strip()

        if not nombre or not password:
            error = "El nombre y la contraseña son obligatorios."
        else:
            with flask_app.app_context():
                try:
                    from sqlalchemy.exc import IntegrityError as _IE
                    alchemy_db.session.add(BunkerAccessToken(nombre=nombre, token=password))
                    alchemy_db.session.commit()
                    success = f"Acceso creado correctamente para {nombre}"
                except _IE:
                    alchemy_db.session.rollback()
                    error = "Error: Esa contraseña ya existe."

    with flask_app.app_context():
        from bunkerlabs.models import BunkerWriteup
        tokens = BunkerAccessToken.query.order_by(BunkerAccessToken.created_at.desc()).all()
        real_machines = Machine.query.filter_by(origen='bunker', clase='real').order_by(Machine.nombre.asc()).all()
        writeups = BunkerWriteup.query.order_by(BunkerWriteup.created_at.desc()).all()
        bunker_machines = Machine.query.filter_by(origen='bunker').order_by(Machine.nombre.asc()).all()

    csrf_token = flask_session.get("csrf_token")
    if not csrf_token:
        csrf_token = secrets.token_urlsafe(32)
        flask_session["csrf_token"] = csrf_token

    context = {
        "tokens": tokens,
        "error": error,
        "success": success,
        "real_machines": real_machines,
        "writeups": writeups,
        "bunker_machines": bunker_machines,
        "session": flask_session,
        "csrf_token_value": csrf_token,
        "g": {"csp_nonce": secrets.token_urlsafe(32)}
    }

    response = templates.TemplateResponse(request, "bunkerlabs/accesos.html", context)
    response.set_cookie("session", set_flask_session_cookie(flask_session), httponly=True, path="/", samesite="lax")
    return response


@pages_router.post("/bunkerlabs/accesos/{token_id}/delete")
def delete_bunker_token(
    token_id: int,
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    """Eliminar token de acceso a BunkerLabs. Solo admin."""
    ok, redir = require_auth_and_role(flask_session, ['admin'])
    if not ok:
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    with flask_app.app_context():
        token_obj = BunkerAccessToken.query.get(token_id)
        if token_obj:
            alchemy_db.session.delete(token_obj)
            alchemy_db.session.commit()
    return RedirectResponse(url='/bunkerlabs/accesos', status_code=302)


@pages_router.post("/bunkerlabs/admin/writeups/add")
async def add_bunker_writeup(
    request: Request,
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    """Añadir writeup para máquina de Entornos Reales. Solo admin."""
    ok, redir = require_auth_and_role(flask_session, ['admin'])
    if not ok:
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    form = await request.form()
    maquina = (form.get('maquina') or '').strip()
    autor = (form.get('autor') or '').strip()
    url_val = (form.get('url') or '').strip()
    tipo = (form.get('tipo') or '').strip()
    locked = 'locked' in form

    if not all([maquina, autor, url_val, tipo]) or tipo not in ['texto', 'video']:
        flask_session['_flashes'] = [('error', 'Todos los campos son obligatorios y el tipo debe ser texto o video.')]
        cookie = set_flask_session_cookie(flask_session)
        resp = RedirectResponse(url='/bunkerlabs/accesos', status_code=302)
        resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
        return resp

    with flask_app.app_context():
        from bunkerlabs.models import BunkerWriteup
        from sqlalchemy.exc import IntegrityError as _IE
        try:
            alchemy_db.session.add(BunkerWriteup(maquina=maquina, autor=autor, url=url_val, tipo=tipo, locked=locked))
            alchemy_db.session.commit()
            flask_session['_flashes'] = [('success', f'Writeup añadido correctamente para {maquina}')]
        except _IE:
            alchemy_db.session.rollback()
            flask_session['_flashes'] = [('error', 'Error: Este writeup ya existe.')]
        except Exception as e:
            alchemy_db.session.rollback()
            flask_session['_flashes'] = [('error', f'Error al añadir writeup: {str(e)}')]

    cookie = set_flask_session_cookie(flask_session)
    resp = RedirectResponse(url='/bunkerlabs/accesos', status_code=302)
    resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
    return resp


@pages_router.post("/bunkerlabs/admin/writeups/delete/{writeup_id}")
def delete_bunker_writeup(
    writeup_id: int,
    flask_session: dict = Depends(get_flask_session),
    csrf_ok: bool = Depends(verify_csrf_token)
):
    """Eliminar writeup de BunkerLabs. Solo admin."""
    ok, redir = require_auth_and_role(flask_session, ['admin'])
    if not ok:
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    with flask_app.app_context():
        from bunkerlabs.models import BunkerWriteup
        writeup = BunkerWriteup.query.get(writeup_id)
        if writeup:
            try:
                alchemy_db.session.delete(writeup)
                alchemy_db.session.commit()
                flask_session['_flashes'] = [('success', 'Writeup eliminado correctamente.')]
            except Exception as e:
                alchemy_db.session.rollback()
                flask_session['_flashes'] = [('error', f'Error al eliminar writeup: {str(e)}')]
        else:
            flask_session['_flashes'] = [('error', 'Writeup no encontrado.')]

    cookie = set_flask_session_cookie(flask_session)
    resp = RedirectResponse(url='/bunkerlabs/accesos', status_code=302)
    resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
    return resp
