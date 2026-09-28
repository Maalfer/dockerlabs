"""Autenticacion: alta, acceso y recuperacion de contrasena."""

import logging
import os
import re
import secrets
from datetime import datetime
from typing import Optional

from fastapi import Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from dockerlabs.extensions import db
from dockerlabs.models import (
    User,
    Machine,
    Writeup,
    PendingWriteup,
    EmailVerificationToken,
    PasswordResetToken,
)


class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    redirect_url: Optional[str] = None

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

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    password: str
    password2: str


def register_auth_routes(api_router, get_session, verify_csrf_token, create_session_cookie, check_password_hash_safe, get_user_and_verify_password):
    """Registra las rutas de este modulo en el router recibido."""

    @api_router.post("/auth/login", response_model=LoginResponse)
    async def api_auth_login(request: Request, data: LoginRequest, session: dict = Depends(get_session)):
        # Ejecutar consulta de DB en threadpool para evitar problemas de sesión
        user_data = await run_in_threadpool(get_user_and_verify_password, data.username, data.password)
    
        if user_data is None:
            return JSONResponse(status_code=401, content={"success": False, "message": "Usuario o contraseña incorrectos."})
            
        cookie_val = create_session_cookie(
            user_data['id'],
            user_data['username'],
            user_data['role'],
            existing_session=session,
            session_version=user_data['session_version'],
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
            return JSONResponse(status_code=400, content={"success": False, "message": "Este nombre de usuario coincide con el de un autor de máquina o writeup. Elige otro nombre de usuario."})

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
        # Invalida cualquier sesión abierta con la contraseña anterior (p.ej.
        # si el reset fue porque la cuenta estaba comprometida).
        user.session_version = (user.session_version or 1) + 1
        reset_token.used = True
        db.session.commit()
        return {"success": True, "message": "Contrasena actualizada correctamente."}
