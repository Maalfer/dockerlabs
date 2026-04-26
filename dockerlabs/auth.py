import os
import json
import re
import secrets
import io
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, g, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from urllib.parse import urlparse, urljoin

from .decorators import role_required, csrf_protect, get_current_role
from . import validators
from bunkerlabs.extensions import limiter
from .models import User, NameClaim, UsernameChangeRequest, Writeup, CreatorRanking, PendingWriteup, WriteupRanking

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PROFILE_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'dockerlabs',  'images', 'perfiles')
ALLOWED_PROFILE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

auth_bp = Blueprint('auth', __name__)

def get_profile_image_static_path(username, user_id=None):

    default_image = "dockerlabs/images/balu.webp"

    if user_id:
        for ext in ALLOWED_PROFILE_EXTENSIONS:
            candidate = os.path.join(PROFILE_UPLOAD_FOLDER, f"{user_id}{ext}")
            if os.path.exists(candidate):
                return f"dockerlabs/images/perfiles/{user_id}{ext}"

    if not username:
        return default_image

    if '/' in username or '\\' in username or '..' in username:
        return default_image

    # Candidatos a comprobar: nombre original, minusculas, seguro, seguro minusculas
    candidates_names = []
    candidates_names.append(username)
    candidates_names.append(username.lower())
    
    s_name = secure_filename(username)
    if s_name != username:
         candidates_names.append(s_name)
         candidates_names.append(s_name.lower())
    
    # Eliminar duplicados preservando orden
    candidates_names = list(dict.fromkeys(candidates_names))

    for name in candidates_names:
        for ext in ALLOWED_PROFILE_EXTENSIONS:
            candidate = os.path.join(PROFILE_UPLOAD_FOLDER, f"{name}{ext}")
            if os.path.exists(candidate):
                return f"dockerlabs/images/perfiles/{name}{ext}"

    return default_image


def get_profile_image_url(username=None, user_id=None):
    """Devuelve la URL del endpoint /img/perfil/<id> para el usuario."""
    if user_id:
        return url_for('auth.serve_profile_image', user_id=user_id)
    if username:
        from .models import User as _User
        user = _User.query.filter_by(username=username).first()
        if user:
            return url_for('auth.serve_profile_image', user_id=user.id)
    return url_for('static', filename='dockerlabs/images/balu.webp')


@auth_bp.route('/img/perfil/<int:user_id>')
def serve_profile_image(user_id):
    """
    Sirve la imagen de perfil desde la BD (fallback a disco).
    ---
    tags:
      - User
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Imagen de perfil.
    """
    from .models import User as _User
    user = _User.query.get(user_id)
    if user and user.profile_image_data:
        mime = user.profile_image_mime or 'image/jpeg'
        return send_file(io.BytesIO(user.profile_image_data), mimetype=mime)
    # Fallback a disco
    disk_path = get_profile_image_static_path(
        user.username if user else None,
        user_id=user_id
    )
    if disk_path and disk_path != 'dockerlabs/images/balu.webp':
        full_path = os.path.join(BASE_DIR, 'static', disk_path)
        if os.path.exists(full_path):
            return send_file(full_path)
    return redirect(url_for('static', filename='dockerlabs/images/balu.webp'))


def load_username_change_requests():

    from sqlalchemy import func, case

    requests = UsernameChangeRequest.query.order_by(UsernameChangeRequest.created_at.desc(), UsernameChangeRequest.id.desc()).all()
    
    rows = []
    for req in requests:
        user = User.query.get(req.user_id)
        user_email = user.email if user else "Unknown"

        conflicting_writeups = Writeup.query.filter_by(autor=req.requested_username).all()
        conflict_count = len(conflicting_writeups)
        
        conflict_examples = ", ".join([f"{w.maquina} (id:{w.id})" for w in conflicting_writeups])

        row = {
            "id": req.id,
            "user_id": req.user_id,
            "old_username": req.old_username,
            "requested_username": req.requested_username,
            "reason": req.reason,
            "contacto_opcional": req.contacto_opcional,
            "estado": req.estado,
            "created_at": req.created_at,
            "processed_by": req.processed_by,
            "processed_at": req.processed_at,
            "decision_reason": req.decision_reason,
            "user_email": user_email,
            "conflict_count": conflict_count,
            "conflict_examples": conflict_examples
        }
        rows.append(row)
        
    return rows

@auth_bp.route('/register', methods=['GET'])
@limiter.limit("5 per minute")
def register():
    """
    User registration endpoint (Página HTML).
    La lógica de registro (POST) ha sido migrada a FastAPI (/api/auth/register).
    """
    remaining = session.pop('rate_limit_remaining', None)
    return render_template('dockerlabs/auth/register.html', remaining=remaining)

@auth_bp.route('/recover', methods=['GET'])
@limiter.limit("5 per minute")
def recover():
    """
    Password recovery endpoint (Página HTML).
    La lógica de recuperación (POST) ha sido migrada a FastAPI (/api/auth/recover).
    """
    return render_template('dockerlabs/auth/recover.html')

@auth_bp.route('/login', methods=['GET'])
@limiter.limit("5 per minute")
def login():
    """
    User login endpoint (Página HTML).
    La validación de credenciales (POST) ha sido migrada a FastAPI (/api/auth/login).
    """
    success = request.args.get('success')
    remaining = session.pop('rate_limit_remaining', None)
    return render_template('dockerlabs/auth/login.html', success=success, remaining=remaining)

@auth_bp.route('/logout')

def logout():
    """
    User logout endpoint.
    ---
    tags:
      - Auth
    responses:
      302:
        description: Redirect to index.
    """
    logout_user()
    session.clear()
    return redirect(url_for('index'))

@auth_bp.route('/gestion-usuarios')
@role_required('admin', 'moderador')

def gestion_usuarios():
    """
    Admin user management page.
    ---
    tags:
      - Admin
    responses:
      200:
        description: List of users.
    """
    usuarios = User.query.order_by(User.id.asc()).all()

    return render_template('dockerlabs/admin/gestion_usuarios.html', usuarios=usuarios)



