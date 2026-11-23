"""Administracion de usuarios: cambio de rol, borrado y gestion de contrasenas."""

import os
import secrets
from datetime import timedelta

from fastapi import Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from werkzeug.security import generate_password_hash

from dockerlabs.extensions import db
from dockerlabs.models import User, PasswordResetToken
from dockerlabs.tiempo import utcnow
import logging

logger = logging.getLogger(__name__)


class UpdateRoleRequest(BaseModel):
    role: str


class SetPasswordRequest(BaseModel):
    password: str
    password2: str


def register_admin_usuarios_routes(api_router, get_session, verify_csrf_token):
    """Registra las rutas de este modulo en el router recibido."""

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

        user = db.session.get(User, user_id)
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


        user = db.session.get(User, user_id)
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
            logger.exception("Error inesperado en api_delete_user")
            db.session.rollback()
            return JSONResponse(status_code=500, content={"error": f"Error al eliminar el usuario: {str(e)}"})

    @api_router.post("/admin/set_user_password/{user_id}")
    async def api_set_user_password(request: Request, user_id: int, data: SetPasswordRequest, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
        caller_id = session.get('user_id')
        caller_role = session.get('role', '').strip().lower()
        if not caller_id or caller_role != 'admin':
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        if data.password != data.password2:
            return JSONResponse(status_code=400, content={"error": "Las contraseñas no coinciden"})

        from dockerlabs import validators
        valid, pwd_error = validators.validate_password_complexity(data.password)
        if not valid:
            return JSONResponse(status_code=400, content={"error": pwd_error})

        user = db.session.get(User, user_id)
        if not user:
            return JSONResponse(status_code=404, content={"error": "Usuario no encontrado"})

        user.password_hash = generate_password_hash(data.password, method='pbkdf2:sha256')
        # Cierra cualquier sesión abierta con la contraseña anterior.
        user.session_version = (user.session_version or 1) + 1
        db.session.commit()
        logger.info("Admin %s estableció una nueva contraseña para %s", session.get('username'), user.username)
        return {"message": f"Contraseña de {user.username} actualizada correctamente.", "success": True}

    @api_router.post("/admin/send_password_reset/{user_id}")
    async def api_send_password_reset(request: Request, user_id: int, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
        caller_id = session.get('user_id')
        caller_role = session.get('role', '').strip().lower()
        if not caller_id or caller_role != 'admin':
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        from dockerlabs.email import send_password_reset_email, is_smtp_configured

        if not is_smtp_configured():
            return JSONResponse(status_code=503, content={"error": "El servicio de correo no está configurado."})

        user = db.session.get(User, user_id)
        if not user:
            return JSONResponse(status_code=404, content={"error": "Usuario no encontrado"})

        PasswordResetToken.query.filter_by(user_id=user.id, used=False).delete()
        db.session.flush()

        token = secrets.token_urlsafe(32)
        expires_at = utcnow() + timedelta(hours=1)
        reset_token = PasswordResetToken(token=token, user_id=user.id, expires_at=expires_at)
        db.session.add(reset_token)
        db.session.commit()

        base_url = os.environ.get('APP_URL', '').rstrip('/') or str(request.base_url).rstrip('/')
        await run_in_threadpool(send_password_reset_email, user.email, user.username, token, base_url)
        logger.info("Admin %s envió un email de restablecimiento a %s", session.get('username'), user.username)
        return {"message": f"Email de restablecimiento enviado a {user.email}.", "success": True}
