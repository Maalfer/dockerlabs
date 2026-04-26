from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import func
from datetime import datetime
import secrets
import re

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

def get_flask_session(request: Request):
    """Extrae y decodifica la cookie de sesión de Flask para autenticación cruzada."""
    cookie = request.cookies.get("session")
    if not cookie:
        return {}
    from dockerlabs.app import app as flask_app
    from flask.sessions import SecureCookieSessionInterface
    session_interface = SecureCookieSessionInterface()
    serializer = session_interface.get_signing_serializer(flask_app)
    try:
        return serializer.loads(cookie)
    except:
        return {}

def verify_csrf_token(request: Request, flask_session: dict = Depends(get_flask_session)):
    """Verifica el token CSRF tal y como lo hacía @csrf_protect de Flask."""
    session_token = flask_session.get("csrf_token")
    header_token = request.headers.get("X-CSRFToken") or request.headers.get("X-CSRF-Token")
    if not session_token or not header_token or not secrets.compare_digest(str(session_token), str(header_token)):
        raise HTTPException(status_code=403, detail="CSRF token missing or invalid")
    return True

def get_fastapi_profile_image_url(username: Optional[str] = None, user_id: Optional[int] = None) -> str:
    """Helper to bypass Flask's url_for dependency in FastAPI."""
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
    from dockerlabs.app import app as flask_app
    from dockerlabs.models import Machine, CreatorRanking, WriteupRanking, Writeup
    from dockerlabs.extensions import db as alchemy_db
    
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

def get_fastapi_profile_image_url(username: Optional[str] = None, user_id: Optional[int] = None) -> str:
    """Helper to bypass Flask's url_for dependency in FastAPI."""
    if user_id:
        return f"/img/perfil/{user_id}"
    if username:
        from dockerlabs.models import User as _User
        user = _User.query.filter_by(username=username).first()
        if user:
            return f"/img/perfil/{user.id}"
    return "/static/dockerlabs/images/balu.webp"

@api_router.get("/ranking_autores", response_model=List[AutorRankingResponse])
def api_ranking_autores():
    # Retrasar importaciones de Flask para evitar problemas circulares al arrancar
    from dockerlabs.app import app as flask_app
    from dockerlabs.models import CreatorRanking, User
    from dockerlabs.extensions import db as alchemy_db
    
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
    from dockerlabs.app import app as flask_app
    from dockerlabs.models import WriteupRanking, User
    from dockerlabs.extensions import db as alchemy_db
    
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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User, CompletedMachine, Writeup
    
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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import PendingMachineSubmission
    from dockerlabs.extensions import db as alchemy_db

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

def create_flask_session_cookie(user_id: int, username: str, existing_session: dict = None) -> str:
    from dockerlabs.app import app as flask_app
    from flask.sessions import SecureCookieSessionInterface
    import hashlib
    import os
    
    session_data = existing_session or {}
    _id = hashlib.sha512(os.urandom(24)).hexdigest()
    
    session_data['_user_id'] = str(user_id)
    session_data['_fresh'] = True
    session_data['_id'] = _id
    session_data['user_id'] = user_id
    session_data['username'] = username
    
    session_interface = SecureCookieSessionInterface()
    serializer = session_interface.get_signing_serializer(flask_app)
    return serializer.dumps(session_data)

@api_router.post("/auth/login", response_model=LoginResponse)
def api_auth_login(data: LoginRequest, request: Request, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User
    from werkzeug.security import check_password_hash
    
    with flask_app.app_context():
        user = User.query.filter_by(username=data.username.strip()).first()
        if user is None or not check_password_hash(user.password_hash, data.password):
            return JSONResponse(status_code=401, content={"success": False, "message": "Usuario o contraseña incorrectos."})
            
        cookie_val = create_flask_session_cookie(user.id, user.username, existing_session=flask_session)
        
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
def api_auth_register(data: RegisterRequest, csrf_ok: bool = Depends(verify_csrf_token)):
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
    
    import re
    if '/' in username or '\\' in username or '..' in username or '.' in username:
        return JSONResponse(status_code=400, content={"success": False, "message": "El nombre de usuario no puede contener caracteres especiales como /, \\, o puntos."})
    if username.lower() in ['admin', 'root', 'system', 'default', 'balulero', 'default-profile', 'logo', 'pingu']:
        return JSONResponse(status_code=400, content={"success": False, "message": "Este nombre de usuario está reservado por el sistema."})
    if not re.match(r'^[A-Za-z0-9_-]+$', username):
        return JSONResponse(status_code=400, content={"success": False, "message": "El nombre de usuario solo puede contener letras, números, guiones y guiones bajos."})

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User, Machine, Writeup, PendingWriteup, NameClaim
    from werkzeug.security import generate_password_hash
    from sqlalchemy.exc import IntegrityError
    from dockerlabs.extensions import db as alchemy_db
    import secrets
    from datetime import datetime

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
def api_auth_recover(data: RecoverRequest, csrf_ok: bool = Depends(verify_csrf_token)):
    username = data.username.strip()
    pin = data.pin.strip()
    password = data.password
    password2 = data.password2

    if not username or not pin or not password:
        return JSONResponse(status_code=400, content={"success": False, "message": "Todos los campos son obligatorios."})
    if password != password2:
        return JSONResponse(status_code=400, content={"success": False, "message": "Las contraseñas no coinciden."})

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User
    from werkzeug.security import check_password_hash, generate_password_hash
    from dockerlabs.extensions import db as alchemy_db

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
def api_change_password(data: ChangePasswordRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})
        
    if data.new_password != data.confirm_password:
        return JSONResponse(status_code=400, content={"error": "Las contraseñas nuevas no coinciden."})

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User
    from werkzeug.security import check_password_hash, generate_password_hash
    from dockerlabs.extensions import db as alchemy_db
    
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
def api_update_profile(data: UpdateProfileRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})
        
    if not data.email.strip():
        return JSONResponse(status_code=400, content={"error": "El email es obligatorio."})

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User
    from dockerlabs.extensions import db as alchemy_db
    
    with flask_app.app_context():
        user_obj = User.query.get(user_id)
        if not user_obj:
            return JSONResponse(status_code=404, content={"error": "Usuario no encontrado."})
            
        user_obj.email = data.email.strip()
        user_obj.biography = data.biography.strip() if data.biography else ""
        alchemy_db.session.commit()
        return {"message": "Perfil actualizado correctamente.", "success": True}

@api_router.post("/update_social_links")
def api_update_social_links(data: UpdateSocialLinksRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User
    from dockerlabs.extensions import db as alchemy_db
    
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
    import os
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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User
    from dockerlabs.extensions import db as alchemy_db
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
def api_update_user_role(user_id: int, data: UpdateRoleRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_id = flask_session.get('user_id')
    caller_role = flask_session.get('role', '')
    if not caller_id or caller_role not in ('admin',):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    nuevo_rol = data.role.strip().lower()
    if nuevo_rol not in ('jugador', 'moderador', 'admin'):
        return JSONResponse(status_code=400, content={"error": "Rol inválido"})

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User
    from dockerlabs.extensions import db as alchemy_db

    with flask_app.app_context():
        user = User.query.get(user_id)
        if not user:
            return JSONResponse(status_code=404, content={"error": "Usuario no encontrado"})
        user.role = nuevo_rol
        alchemy_db.session.commit()
        return {"message": f"Rol de {user.username} actualizado a {nuevo_rol}", "success": True}

@api_router.post("/admin/delete_user/{user_id}")
def api_delete_user(user_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_id = flask_session.get('user_id')
    caller_role = flask_session.get('role', '')
    if not caller_id or caller_role not in ('admin',):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    if caller_id == user_id:
        return JSONResponse(status_code=400, content={"error": "No puedes eliminar tu propia cuenta desde aquí."})

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User
    from dockerlabs.extensions import db as alchemy_db

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
def api_request_username_change(data: RequestUsernameChangeRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User, UsernameChangeRequest
    from dockerlabs.extensions import db as alchemy_db

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
def api_approve_username_change(request_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_id = flask_session.get('user_id')
    caller_role = flask_session.get('role', '')
    if not caller_id or caller_role not in ('admin',):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User, UsernameChangeRequest, Writeup, PendingWriteup, WriteupRanking, CreatorRanking
    from dockerlabs.extensions import db as alchemy_db
    from sqlalchemy import func
    from datetime import datetime

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
def api_reject_username_change(request_id: int, data: RejectUsernameChangeRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_id = flask_session.get('user_id')
    caller_role = flask_session.get('role', '')
    if not caller_id or caller_role not in ('admin',):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import UsernameChangeRequest
    from dockerlabs.extensions import db as alchemy_db
    from datetime import datetime

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
def api_revert_username_change(request_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_id = flask_session.get('user_id')
    caller_role = flask_session.get('role', '')
    if not caller_id or caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import UsernameChangeRequest
    from dockerlabs.extensions import db as alchemy_db

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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import Machine
    from dockerlabs.extensions import db as alchemy_db

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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import Machine
    from dockerlabs.extensions import db as alchemy_db
    import time as _time

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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User

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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import Rating
    from dockerlabs.extensions import db as alchemy_db
    from datetime import datetime

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
    from dockerlabs.app import app as flask_app
    from dockerlabs.models import Rating
    from dockerlabs.extensions import db as alchemy_db
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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import CompletedMachine

    with flask_app.app_context():
        completed = CompletedMachine.query.filter_by(user_id=user_id, machine_name=machine_name).first()
        return {"completed": completed is not None}

@api_router.post("/toggle_completed_machine")
def api_toggle_completed_machine(data: ToggleCompletedRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    user_id = flask_session.get('user_id')
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Not authenticated", "success": False})

    machine_name = data.machine_name.strip()
    if not machine_name:
        return JSONResponse(status_code=400, content={"error": "Machine name required", "success": False})

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import Machine, CompletedMachine
    from dockerlabs.extensions import db as alchemy_db

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
def api_approve_nombre_claim(claim_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import NameClaim, User
    from dockerlabs.extensions import db as alchemy_db
    from sqlalchemy.exc import IntegrityError

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
def api_reject_nombre_claim(claim_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import NameClaim
    from dockerlabs.extensions import db as alchemy_db

    with flask_app.app_context():
        claim = NameClaim.query.get(claim_id)
        if not claim:
            return JSONResponse(status_code=404, content={"error": "Claim no encontrado"})
        claim.estado = 'rechazada'
        alchemy_db.session.commit()
        return {"message": "Claim rechazado.", "success": True}

@api_router.post("/admin/nombre-claims/{claim_id}/revert")
def api_revert_nombre_claim(claim_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import NameClaim
    from dockerlabs.extensions import db as alchemy_db

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
@api_router.post("/writeups/submit")
def api_submit_writeup(data: SubmitWriteupRequest, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    import re as _re, urllib.parse as _up
    user_id = flask_session.get('user_id')
    autor = flask_session.get('username', '').strip()
    if not user_id or not autor:
        return JSONResponse(status_code=403, content={"error": "Debes iniciar sesión"})

    maquina = data.maquina.strip()
    url = data.url.strip()
    tipo = data.tipo.strip().lower()

    from dockerlabs.app import app as flask_app
    from dockerlabs import validators
    from dockerlabs.models import Machine, PendingWriteup, Writeup
    from dockerlabs.extensions import db as alchemy_db

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
def api_aprobar_writeup_recibido(writeup_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User, PendingWriteup, Writeup, WriteupRanking
    from dockerlabs.extensions import db as alchemy_db
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
def api_approve_writeup_edit(request_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import Writeup, WriteupEditRequest
    from dockerlabs.extensions import db as alchemy_db

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
def api_reject_writeup_edit(request_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import WriteupEditRequest
    from dockerlabs.extensions import db as alchemy_db

    with flask_app.app_context():
        req = WriteupEditRequest.query.get(request_id)
        if req:
            req.estado = 'rechazada'
            alchemy_db.session.commit()
        return {"message": "Petición rechazada.", "success": True}

@api_router.post("/writeups/edit-requests/{request_id}/revert")
def api_revert_writeup_edit(request_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
    caller_role = flask_session.get('role', '')
    if caller_role not in ('admin', 'moderador'):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import WriteupEditRequest
    from dockerlabs.extensions import db as alchemy_db

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

    from dockerlabs.app import app as flask_app
    from dockerlabs import validators
    from dockerlabs.models import Writeup, WriteupEditRequest
    from dockerlabs.extensions import db as alchemy_db

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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import Writeup
    from dockerlabs.extensions import db as alchemy_db

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

    from dockerlabs.app import app as flask_app
    from dockerlabs import validators
    from dockerlabs.models import PendingWriteup
    from dockerlabs.extensions import db as alchemy_db

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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import PendingWriteup
    from dockerlabs.extensions import db as alchemy_db

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
    from dockerlabs.app import app as flask_app
    from dockerlabs.models import Writeup, User
    from dockerlabs.extensions import db as alchemy_db
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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import Writeup, WriteupReport
    from dockerlabs.extensions import db as alchemy_db

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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import WriteupReport
    from dockerlabs.extensions import db as alchemy_db

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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import WriteupReport
    from dockerlabs.extensions import db as alchemy_db

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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import PendingWriteup, Machine
    from dockerlabs.extensions import db as alchemy_db

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
    from dockerlabs.app import app as flask_app
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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User, Machine, Writeup
    from dockerlabs.extensions import db as alchemy_db
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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import PendingMachineSubmission
    from dockerlabs.extensions import db as alchemy_db
    from datetime import datetime

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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import PendingMachineSubmission
    from dockerlabs.extensions import db as alchemy_db
    from datetime import datetime

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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User, Mensajeria
    from dockerlabs.extensions import db as alchemy_db
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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User, Mensajeria
    from dockerlabs.extensions import db as alchemy_db
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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User, Mensajeria
    from dockerlabs.extensions import db as alchemy_db
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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User, Mensajeria
    from dockerlabs.extensions import db as alchemy_db

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

    from dockerlabs.app import app as flask_app
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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User

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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import User, Mensajeria
    from dockerlabs.extensions import db as alchemy_db
    from datetime import datetime

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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import Writeup
    from dockerlabs.extensions import db as alchemy_db

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

    from dockerlabs.app import app as flask_app
    from dockerlabs.models import Writeup, Machine
    from dockerlabs.extensions import db as alchemy_db
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
