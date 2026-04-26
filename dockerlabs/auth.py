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
        return f'/api/img/perfil/{user_id}'
    if username:
        from .models import User as _User
        user = _User.query.filter_by(username=username).first()
        if user:
            return f'/api/img/perfil/{user.id}'
    return url_for('static', filename='dockerlabs/images/balu.webp')


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
    return redirect('/')

@auth_bp.route('/request_username_change', methods=['POST'])
@login_required
@csrf_protect
def request_username_change():
    """
    Handle username change request form submission.
    Este endpoint maneja el formulario HTML y redirige.
    La lógica API está en FastAPI: POST /api/auth/request_username_change
    """
    from .models import UsernameChangeRequest
    from .extensions import db as alchemy_db
    import re as _re

    user_id = session.get('user_id')
    old_username = (session.get('username') or '').strip()
    requested_username = (request.form.get('requested_username') or '').strip()
    reason = (request.form.get('reason') or '').strip()
    contacto_opcional = (request.form.get('contacto_opcional') or '').strip()

    if not user_id:
        flash("Debes iniciar sesión para solicitar un cambio de nombre.", "warning")
        return redirect('/dashboard')

    if not requested_username:
        flash("Debes proporcionar un nuevo nombre de usuario.", "danger")
        return redirect('/dashboard')

    # Validar formato del username
    if not _re.match(r'^[a-zA-Z0-9_-]{3,20}$', requested_username):
        flash("El nombre de usuario debe tener entre 3 y 20 caracteres y solo puede contener letras, números, guiones y guiones bajos.", "danger")
        return redirect('/dashboard')

    # Verificar si ya existe una solicitud pendiente
    existing = UsernameChangeRequest.query.filter_by(
        user_id=user_id,
        estado='pendiente'
    ).first()

    if existing:
        flash("Ya tienes una solicitud de cambio de nombre pendiente.", "warning")
        return redirect('/dashboard')

    try:
        new_request = UsernameChangeRequest(
            user_id=user_id,
            old_username=old_username,
            requested_username=requested_username,
            reason=reason,
            contacto_opcional=contacto_opcional,
            estado='pendiente'
        )
        alchemy_db.session.add(new_request)
        alchemy_db.session.commit()
        flash("Solicitud enviada correctamente. El equipo de administración la revisará pronto.", "success")
    except Exception as e:
        alchemy_db.session.rollback()
        flash(f"Error al enviar la solicitud: {str(e)}", "danger")

    return redirect('/dashboard')

