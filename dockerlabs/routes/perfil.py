"""Perfil del usuario: contrasena, datos, redes sociales y foto."""

import io
import logging
import os
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import BackgroundTasks, Depends, File, Request, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image
from pydantic import BaseModel
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from dockerlabs.extensions import db
from dockerlabs.models import EmailChangeToken, User


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: Optional[str] = None

class UpdateProfileRequest(BaseModel):
    biography: Optional[str] = None
    nombre_diploma: Optional[str] = None

class UpdateSocialLinksRequest(BaseModel):
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    youtube_url: Optional[str] = None

class RequestEmailChangeRequest(BaseModel):
    current_password: str
    new_email: str


# Límite del cambio de email: es un endpoint que envía correo y reautentica,
# mismo motivo que forgot-password. Por user_id (ya requiere sesión activa).
_email_change_hits: dict = defaultdict(list)
_EMAIL_CHANGE_LIMIT = 3
_EMAIL_CHANGE_WINDOW = 900  # 15 min


def _email_change_rate_limited(user_id: int) -> bool:
    now = time.time()
    hits = _email_change_hits[user_id]
    hits[:] = [t for t in hits if now - t < _EMAIL_CHANGE_WINDOW]
    if len(hits) >= _EMAIL_CHANGE_LIMIT:
        return True
    hits.append(now)
    return False


def register_perfil_routes(api_router, get_session, verify_csrf_token, check_password_hash_safe, create_session_cookie, BASE_DIR):
    """Registra las rutas de este modulo en el router recibido."""

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
        # Invalida el resto de sesiones abiertas (p.ej. una cookie robada deja
        # de servir en cuanto el titular legítimo cambia su contraseña).
        user_obj.session_version = (user_obj.session_version or 1) + 1
        db.session.commit()

        response = JSONResponse(content={"message": "Contraseña actualizada correctamente.", "success": True})
        # Esta misma sesión hizo el cambio a propósito: se refresca su cookie
        # con el session_version nuevo para que no quede ella misma deslogueada.
        cookie_val = create_session_cookie(
            user_id,
            session.get("username") or user_obj.username,
            session.get("role") or user_obj.role,
            existing_session=session,
            _id=session.get("_id"),
            session_version=user_obj.session_version,
        )
        response.set_cookie(key="session", value=cookie_val, httponly=True, secure=True, path="/", samesite="lax")
        return response

    @api_router.post("/update_profile")
    async def api_update_profile(request: Request, data: UpdateProfileRequest, background: BackgroundTasks, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
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

        # El cambio de email vive en /api/request_email_change: requiere la
        # contraseña actual y confirmación por correo antes de aplicarse (ver
        # esa ruta). Aquí ya no se acepta directamente.

        diploma_cambiado = user_obj.nombre_diploma != nombre_diploma_sanitized

        try:
            user_obj.biography = biography_sanitized
            user_obj.nombre_diploma = nombre_diploma_sanitized
            db.session.commit()

            if diploma_cambiado:
                # El nombre va impreso en el PDF: los diplomas ya emitidos caducan.
                # Re-renderizarlos cuesta ~170 ms cada uno, así que va después de
                # responder y no hace esperar al usuario.
                from dockerlabs.routes.certificados import sync_user_certificates_safe
                background.add_task(sync_user_certificates_safe, user_obj.id, force=True)

            return {"message": "Perfil actualizado correctamente.", "success": True}
        except Exception as e:
            db.session.rollback()
            return JSONResponse(status_code=500, content={"error": f"Error al actualizar el perfil: {str(e)}"})

    @api_router.post("/request_email_change")
    async def api_request_email_change(request: Request, data: RequestEmailChangeRequest, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
        """Inicia el cambio de email: exige la contraseña actual (evita que una
        sesión robada baste para secuestrar la cuenta vía "olvidé mi
        contraseña") y no aplica el cambio hasta confirmarlo desde la
        dirección nueva (evita fijar un correo que el usuario no controla)."""
        user_id = session.get('user_id')
        if not user_id:
            return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})

        if _email_change_rate_limited(user_id):
            return JSONResponse(status_code=429, content={"error": "Has solicitado el cambio de correo demasiadas veces. Inténtalo de nuevo en unos minutos."})

        user_obj = User.query.get(user_id)
        if not user_obj:
            return JSONResponse(status_code=404, content={"error": "Usuario no encontrado."})

        if not check_password_hash_safe(user_obj.password_hash, data.current_password):
            return JSONResponse(status_code=400, content={"error": "La contraseña actual es incorrecta."})

        from dockerlabs import validators
        new_email = validators.sanitize_text(data.new_email.strip().lower())
        if not new_email or len(new_email) > 35:
            return JSONResponse(status_code=400, content={"error": "Correo electrónico no válido."})

        if new_email == user_obj.email.lower():
            return JSONResponse(status_code=400, content={"error": "Ese ya es tu correo actual."})

        existing = User.query.filter(User.email == new_email, User.id != user_id).first()
        if existing:
            return JSONResponse(status_code=400, content={"error": "Ese correo electrónico ya está en uso por otra cuenta."})

        from dockerlabs.email import send_email_change_verification, send_email_change_notice, is_smtp_configured
        if not is_smtp_configured():
            return JSONResponse(status_code=503, content={"error": "El servicio de correo no está configurado. Contacta al administrador."})

        # Un solo cambio pendiente a la vez: una solicitud nueva invalida
        # cualquier enlace anterior sin usar (mismo patrón que password reset).
        EmailChangeToken.query.filter_by(user_id=user_id, used=False).delete()
        db.session.flush()

        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        change_tok = EmailChangeToken(token=token, user_id=user_id, new_email=new_email, expires_at=expires_at)
        db.session.add(change_tok)
        db.session.commit()

        old_email = user_obj.email
        base_url = os.environ.get('APP_URL', '').rstrip('/') or str(request.base_url).rstrip('/')
        from fastapi.concurrency import run_in_threadpool
        await run_in_threadpool(send_email_change_verification, new_email, user_obj.username, token, base_url)
        # Aviso a la dirección actual: así el titular legítimo se entera de
        # inmediato si alguien más solicitó el cambio desde su sesión, aunque
        # la confirmación en la dirección nueva no llegue a completarse.
        await run_in_threadpool(send_email_change_notice, old_email, user_obj.username, new_email)

        return {"message": "Te hemos enviado un correo a tu nueva dirección para confirmar el cambio.", "success": True}

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
