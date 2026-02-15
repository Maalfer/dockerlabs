import os
import json
import re
import secrets
import io
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, g, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from urllib.parse import urlparse, urljoin

from .decorators import role_required, csrf_protect, get_current_role
from . import validators
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

@auth_bp.route('/auth/api_register', methods=['POST'])
@csrf_protect
@limiter.limit("3 per minute", methods=["POST"])
def api_register():
    """
    API User registration endpoint.
    """
    import re
    import secrets
    import string
    from datetime import datetime
    from .extensions import db as alchemy_db
    from sqlalchemy.exc import IntegrityError
    from .models import Machine, NameClaim, PendingWriteup

    data = request.json or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''
    password2 = data.get('password2') or ''

    if not username or not email or not password:
        return jsonify({'success': False, 'error': "Todos los campos son obligatorios."}), 400
    if len(username) > 20:
        return jsonify({'success': False, 'error': "El nombre de usuario no puede exceder 20 caracteres."}), 400
    if len(email) > 35:
        return jsonify({'success': False, 'error': "El correo electrónico no puede exceder 35 caracteres."}), 400
    if password != password2:
        return jsonify({'success': False, 'error': "Las contraseñas no coinciden."}), 400
    
    if '/' in username or '\\' in username or '..' in username or '.' in username:
        return jsonify({'success': False, 'error': "El nombre de usuario no puede contener caracteres especiales."}), 400
    
    if username.lower() in ['admin', 'root', 'system', 'default', 'balulero', 'default-profile', 'logo', 'pingu']:
         return jsonify({'success': False, 'error': "Este nombre de usuario está reservado por el sistema."}), 400
    
    if not re.match(r'^[A-Za-z0-9_-]+$', username):
        return jsonify({'success': False, 'error': "El nombre de usuario solo puede contener letras, números, guiones y guiones bajos."}), 400

    pwd_hash = generate_password_hash(password)

    existing = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()

    if existing:
        return jsonify({'success': False, 'error': "El usuario o el correo ya están registrados."}), 400

    auth_conflict = False
    
    if Machine.query.filter_by(autor=username).first():
        auth_conflict = True
    elif Writeup.query.filter_by(autor=username).first():
        auth_conflict = True
    elif PendingWriteup.query.filter_by(autor=username).first():
            auth_conflict = True

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
            
            return jsonify({
                'success': True, 
                'message': "Tu solicitud de registro se ha enviado para revisión. El nombre coincide con un autor existente."
            }), 200
        except Exception:
            alchemy_db.session.rollback()
            return jsonify({'success': False, 'error': "Se ha producido un error al registrar la solicitud."}), 500
    else:
        try:
            new_user = User(
                username=username,
                email=email,
                password_hash=pwd_hash,
                role='jugador'
            )

            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            pin = ''.join(secrets.choice(alphabet) for i in range(15))
            pin_hash = generate_password_hash(pin)
            now_ts = datetime.utcnow()
            
            new_user.recovery_pin_hash = pin_hash
            new_user.recovery_pin_plain = pin
            new_user.recovery_pin_created_at = now_ts
            
            alchemy_db.session.add(new_user)
            alchemy_db.session.commit()

            return jsonify({
                'success': True, 
                'message': "Cuenta creada correctamente.", 
                'recovery_pin': pin
            }), 200

        except IntegrityError:
            alchemy_db.session.rollback()
            return jsonify({'success': False, 'error': "El usuario o el correo ya están registrados."}), 400
        except Exception as e:
            alchemy_db.session.rollback()
            return jsonify({'success': False, 'error': f"Error al crear usuario: {str(e)}"}), 500

@auth_bp.route('/register', methods=['GET', 'POST'])
@csrf_protect
@limiter.limit("3 per minute", methods=["POST"])
def register():
    """
    User registration endpoint.
    Legacy route, kept for redirect or 404? 
    Given React handles this, we can remove or redirect to /.
    For now, remove content and return 404 or redirect.
    But let's just remove it as per plan.
    """
    return redirect('/')

@auth_bp.route('/recover', methods=['GET', 'POST'])
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def recover():
    """
    Password recovery endpoint.
    Legacy route.
    """
    return redirect('/')

@auth_bp.route('/login', methods=['GET', 'POST'])
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def login():
    """
    User login endpoint.
    Legacy route.
    """
    return redirect('/')

@auth_bp.route('/gestion-usuarios')
@role_required('admin', 'moderador')
def gestion_usuarios():
    """
    Admin user management page.
    Legacy route.
    """
    return redirect('/')


@auth_bp.route('/api/usuarios')
@role_required('admin', 'moderador')
def api_get_usuarios():
    """JSON API: list usuarios for admin/moderador"""
    usuarios = User.query.order_by(User.id.asc()).all()
    current_role = session.get('role', '')
    out = []
    for u in usuarios:
        out.append({
            'id': u.id,
            'username': u.username,
            'email': u.email if current_role == 'admin' else None,
            'role': u.role,
            'created_at': getattr(u, 'created_at', str(u.created_at)),
            'recovery_pin_plain': getattr(u, 'recovery_pin_plain', None)
        })
    return jsonify({'usuarios': out}), 200


@auth_bp.route('/api/update_user_role', methods=['POST'])
@role_required('admin')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def api_update_user_role():
    """JSON API: update user role"""
    from .extensions import db as alchemy_db
    data = request.json or {}
    try:
        user_id = int(data.get('user_id'))
    except Exception:
        return jsonify({'error': 'user_id inválido'}), 400

    nuevo_rol = (data.get('role') or '').strip().lower()
    if nuevo_rol not in ('jugador', 'moderador', 'admin'):
        return jsonify({'error': 'rol inválido'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'usuario no encontrado'}), 404

    try:
        user.role = nuevo_rol
        alchemy_db.session.commit()
        return jsonify({'ok': True}), 200
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/api/delete_user', methods=['POST'])
@role_required('admin')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def api_delete_user():
    """JSON API: delete a user"""
    from .extensions import db as alchemy_db
    data = request.json or {}
    try:
        user_id = int(data.get('user_id'))
    except Exception:
        return jsonify({'error': 'user_id inválido'}), 400

    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'usuario no encontrado'}), 404

        if session.get('user_id') == user_id:
            return jsonify({'error': 'no puedes eliminar tu propia cuenta desde aquí'}), 403

        if user.role == 'admin':
            admin_count = User.query.filter_by(role='admin').count()
            if admin_count <= 1:
                return jsonify({'error': 'no se puede eliminar al último administrador'}), 400

        alchemy_db.session.delete(user)
        alchemy_db.session.commit()
        return jsonify({'ok': True}), 200
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/update_user_role/<int:user_id>', methods=['POST'])
@role_required('admin')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"]) 
 
def update_user_role(user_id):
    """
    Update user role.
    ---
    tags:
      - Admin
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
    responses:
      302:
        description: Redirect to user management.
    """
    from .extensions import db as alchemy_db
    
    nuevo_rol = (request.form.get('role') or '').strip().lower()
    if nuevo_rol not in ('jugador', 'moderador', 'admin'):
        return redirect(url_for('auth.gestion_usuarios'))

    user = User.query.get(user_id)
    if user:
         user.role = nuevo_rol
         alchemy_db.session.commit()
         
    return redirect(url_for('auth.gestion_usuarios'))

@auth_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@role_required('admin')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])

def delete_user(user_id):
    """
    Delete a user.
    ---
    tags:
      - Admin
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
    responses:
      302:
        description: Redirect to user management.
    """
    from .extensions import db as alchemy_db
    
    try:
        user = User.query.get(user_id)
        if not user:
            flash("Usuario no encontrado.")
            return redirect(url_for('auth.gestion_usuarios'))

        if session.get('user_id') == user_id:
            flash("No puedes eliminar tu propia cuenta desde aquí.")
            return redirect(url_for('auth.gestion_usuarios'))

        if user.role == 'admin':
            admin_count = User.query.filter_by(role='admin').count()
            if admin_count <= 1:
                flash("No se puede eliminar al último administrador.")
                return redirect(url_for('auth.gestion_usuarios'))

        alchemy_db.session.delete(user)
        alchemy_db.session.commit()
        flash("Usuario eliminado correctamente.")
    except Exception as e:
        alchemy_db.session.rollback()
        flash("Error al eliminar el usuario: " + str(e))

    return redirect(url_for('auth.gestion_usuarios'))

@auth_bp.route('/logout')
@auth_bp.route('/auth/logout')
def logout():
    """
    User logout endpoint.
    """
    logout_user()
    session.clear()
    return redirect('/')

@auth_bp.route('/api/logout', methods=['POST'])
@csrf_protect
def api_logout():
    """
    API User logout endpoint.
    """
    logout_user()
    session.clear()
    return jsonify({'success': True, 'message': 'Sesión cerrada correctamente.'}), 200

@auth_bp.route('/request_username_change', methods=['POST'])
@csrf_protect

def request_username_change():
    """
    Request username change.
    ---
    tags:
      - User
    responses:
      302:
        description: Redirect to dashboard.
    """
    if 'user_id' not in session:
        flash("Debes iniciar sesión.", "danger")
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    old_username = session['username']
    requested_username = request.form.get("requested_username", "").strip()
    reason = request.form.get("reason", "").strip()
    contacto_opcional = request.form.get("contacto_opcional", "").strip()

    if not requested_username:
        flash("Debes escribir un nombre nuevo.", "warning")
        return redirect(url_for('dashboard'))

    if len(requested_username) > 20:
        flash("El nombre de usuario no puede exceder 20 caracteres.", "warning")
        return redirect(url_for('dashboard'))

    if not re.match(r'^[A-Za-z0-9_\-]{3,20}$', requested_username):
        flash("El nombre debe tener entre 3 y 20 caracteres y solo letras, números, guion y guion bajo.", "warning")
        return redirect(url_for('dashboard'))

    from .extensions import db as alchemy_db
    
    if User.query.filter_by(username=requested_username).first():
        flash("Ese nombre ya está en uso.", "danger")
        return redirect(url_for('dashboard'))

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
    except Exception:
        alchemy_db.session.rollback()
        flash("Error al procesar la solicitud.", "danger")
        return redirect(url_for('dashboard'))

    flash("Solicitud enviada. Un moderador o admin deberá aprobarla.", "success")
    return redirect(url_for('dashboard'))

@auth_bp.route('/api/request_username_change', methods=['POST'])
@csrf_protect
@limiter.limit("5 per hour")
def api_request_username_change():
    """
    JSON API: Request username change (for React dashboard).
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Debes iniciar sesión.'}), 401

    data = request.json or {}
    user_id = session['user_id']
    old_username = session['username']
    requested_username = (data.get('requested_username') or '').strip()
    reason = (data.get('reason') or '').strip()
    contacto_opcional = (data.get('contacto_opcional') or '').strip()

    if not requested_username:
        return jsonify({'error': 'Debes escribir un nombre nuevo.'}), 400

    if len(requested_username) > 20:
        return jsonify({'error': 'El nombre de usuario no puede exceder 20 caracteres.'}), 400

    if not re.match(r'^[A-Za-z0-9_\-]{3,20}$', requested_username):
        return jsonify({'error': 'El nombre debe tener entre 3 y 20 caracteres y solo letras, números, guion y guion bajo.'}), 400

    from .extensions import db as alchemy_db

    if User.query.filter_by(username=requested_username).first():
        return jsonify({'error': 'Ese nombre ya está en uso.'}), 400

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
        return jsonify({'message': 'Solicitud enviada. Un moderador o admin deberá aprobarla.'}), 200
    except Exception:
        alchemy_db.session.rollback()
        return jsonify({'error': 'Error al procesar la solicitud.'}), 500

@auth_bp.route('/approve_username_change/<int:request_id>', methods=['POST'])
@role_required('admin')
@csrf_protect

def approve_username_change(request_id):
    """
    Approve username change request.
    ---
    tags:
      - Admin
    responses:
      302:
        description: Redirect to petitions.
    """
    from .extensions import db as alchemy_db
    from sqlalchemy import func
    from datetime import datetime
    from .models import User, UsernameChangeRequest, Writeup, PendingWriteup, WriteupRanking, CreatorRanking
    
    req = UsernameChangeRequest.query.get(request_id)
    if not req:
        flash("Petición no encontrada.", "danger")
        return redirect(url_for('peticiones'))

    if req.estado != 'pendiente':
        flash("Esta petición ya fue procesada.", "warning")
        return redirect(url_for('peticiones'))

    requested_username = req.requested_username

    existing_user = User.query.filter(User.username == requested_username, User.id != req.user_id).first()
    if existing_user:
        req.estado = 'rechazada'
        req.processed_by = session['user_id']
        req.processed_at = datetime.utcnow()
        req.decision_reason = 'Nombre ya en uso al aprobar'
        
        alchemy_db.session.commit()
        
        flash("El nombre ya está en uso. No se pudo aprobar.", "danger")
        return redirect(url_for('peticiones'))

    conflict_count = Writeup.query.filter(func.lower(Writeup.autor) == func.lower(requested_username)).count()

    if conflict_count > 0:
        decision_reason = f'Aprobado con conflicto: {conflict_count} writeup(s) tienen ese autor'
    else:
        decision_reason = 'Aprobado por admin'

    user = User.query.get(req.user_id)
    if user:
        user.username = requested_username

    if conflict_count == 0:
        try:
            old_lower = req.old_username.lower()

            Writeup.query.filter(func.lower(Writeup.autor) == old_lower)                .update({Writeup.autor: requested_username}, synchronize_session=False)

            PendingWriteup.query.filter(func.lower(PendingWriteup.autor) == old_lower)                .update({PendingWriteup.autor: requested_username}, synchronize_session=False)

            WriteupRanking.query.filter(func.lower(WriteupRanking.nombre) == old_lower)                .update({WriteupRanking.nombre: requested_username}, synchronize_session=False)

            CreatorRanking.query.filter(func.lower(CreatorRanking.nombre) == old_lower)                .update({CreatorRanking.nombre: requested_username}, synchronize_session=False)

            alchemy_db.session.commit()
            
            try:
                from .writeups import recalcular_ranking_writeups
                recalcular_ranking_writeups()
            except Exception:
                pass
                
        except Exception:
            alchemy_db.session.rollback()

    req.estado = 'aprobada'
    req.processed_by = session['user_id']
    req.processed_at = datetime.utcnow()
    req.decision_reason = decision_reason

    alchemy_db.session.commit()

    if conflict_count > 0:
        flash(f"El nombre ha sido cambiado pero existe conflicto con {conflict_count} writeup(s). Revisa las alertas en peticiones.", "warning")
    else:
        flash(f"El nombre del usuario ha sido cambiado correctamente a {requested_username}.", "success")

    return redirect(url_for('peticiones'))


@auth_bp.route('/api/username-change/<int:request_id>/approve', methods=['POST'])
@role_required('admin')
@csrf_protect
def api_approve_username_change(request_id):
    """Approve username change via JSON API."""
    from .extensions import db as alchemy_db
    from sqlalchemy import func
    from datetime import datetime
    from .models import User, UsernameChangeRequest, Writeup, PendingWriteup, WriteupRanking, CreatorRanking

    req = UsernameChangeRequest.query.get(request_id)
    if not req:
        return jsonify({'error': 'Petición no encontrada.'}), 404

    if req.estado != 'pendiente':
        return jsonify({'error': 'Petición ya procesada.'}), 400

    requested_username = req.requested_username

    existing_user = User.query.filter(User.username == requested_username, User.id != req.user_id).first()
    if existing_user:
        req.estado = 'rechazada'
        req.processed_by = session.get('user_id')
        req.processed_at = datetime.utcnow()
        req.decision_reason = 'Nombre ya en uso al aprobar'
        alchemy_db.session.commit()
        return jsonify({'error': 'El nombre ya está en uso.'}), 400

    conflict_count = Writeup.query.filter(func.lower(Writeup.autor) == func.lower(requested_username)).count()

    if conflict_count > 0:
        decision_reason = f'Aprobado con conflicto: {conflict_count} writeup(s) tienen ese autor'
    else:
        decision_reason = 'Aprobado por admin'

    user = User.query.get(req.user_id)
    if user:
        user.username = requested_username

    if conflict_count == 0:
        try:
            old_lower = req.old_username.lower()

            Writeup.query.filter(func.lower(Writeup.autor) == old_lower)                .update({Writeup.autor: requested_username}, synchronize_session=False)

            PendingWriteup.query.filter(func.lower(PendingWriteup.autor) == old_lower)                .update({PendingWriteup.autor: requested_username}, synchronize_session=False)

            WriteupRanking.query.filter(func.lower(WriteupRanking.nombre) == old_lower)                .update({WriteupRanking.nombre: requested_username}, synchronize_session=False)

            CreatorRanking.query.filter(func.lower(CreatorRanking.nombre) == old_lower)                .update({CreatorRanking.nombre: requested_username}, synchronize_session=False)

            alchemy_db.session.commit()
            try:
                from .writeups import recalcular_ranking_writeups
                recalcular_ranking_writeups()
            except Exception:
                pass
        except Exception:
            alchemy_db.session.rollback()

    req.estado = 'aprobada'
    req.processed_by = session.get('user_id')
    req.processed_at = datetime.utcnow()
    req.decision_reason = decision_reason

    alchemy_db.session.commit()

    return jsonify({'message': 'Petición aprobada', 'conflict_count': conflict_count}), 200


@auth_bp.route('/api/username-change/<int:request_id>/reject', methods=['POST'])
@role_required('admin')
@csrf_protect
def api_reject_username_change(request_id):
    reason = (request.json or {}).get('decision_reason', 'Rechazado por moderador/admin')
    from .extensions import db as alchemy_db
    req = UsernameChangeRequest.query.get(request_id)
    if not req:
        return jsonify({'error': 'Petición no encontrada.'}), 404
    req.estado = 'rechazada'
    req.processed_by = session.get('user_id')
    req.processed_at = datetime.utcnow()
    req.decision_reason = reason
    alchemy_db.session.commit()
    return jsonify({'message': 'Petición rechazada'}), 200


@auth_bp.route('/api/username-change/<int:request_id>/revert', methods=['POST'])
@role_required('admin')
@csrf_protect
def api_revert_username_change(request_id):
    from .extensions import db as alchemy_db
    req = UsernameChangeRequest.query.get(request_id)
    if not req:
        return jsonify({'error': 'Petición no encontrada.'}), 404
    req.estado = 'pendiente'
    alchemy_db.session.commit()
    return jsonify({'message': 'Petición revertida a pendiente'}), 200

@auth_bp.route('/reject_username_change/<int:request_id>', methods=['POST'])
@role_required('admin')
@csrf_protect

def reject_username_change(request_id):
    """
    Reject username change request.
    ---
    tags:
      - Admin
    responses:
      302:
        description: Redirect to petitions.
    """
    reason = request.form.get("decision_reason", "Rechazado por moderador/admin")

    from .extensions import db as alchemy_db
    req = UsernameChangeRequest.query.get(request_id)

    if not req:
        flash("Petición no encontrada.", "danger")
        return redirect(url_for('peticiones'))

    req.estado = 'rechazada'
    req.processed_by = session['user_id']
    req.processed_at = datetime.utcnow()
    req.decision_reason = reason
    
    alchemy_db.session.commit()

    flash("Petición rechazada correctamente.", "info")
    return redirect(url_for('peticiones'))

@auth_bp.route('/username_change/<int:request_id>/revert', methods=['POST'])
@role_required('admin', 'moderador')

def revert_username_change(request_id):
    """
    Revert username change status to pending.
    ---
    tags:
      - Admin
    responses:
      302:
        description: Redirect to petitions.
    """
    from .extensions import db as alchemy_db
    req = UsernameChangeRequest.query.get(request_id)
    if req:
        req.estado = 'pendiente'
        req.processed_by = None
        req.processed_at = None
        req.decision_reason = None
        alchemy_db.session.commit()
    return redirect(url_for('peticiones'))
