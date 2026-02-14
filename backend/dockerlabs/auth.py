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

@auth_bp.route('/register', methods=['GET', 'POST'])
@csrf_protect
@limiter.limit("3 per minute", methods=["POST"])

def register():
    """
    User registration endpoint.
    ---
    tags:
      - Auth
    responses:
      200:
        description: Registration page or success message.
    """
    error = None
    pending_message = None
    recovery_pin = None

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        if not username or not email or not password:
            error = "Todos los campos son obligatorios."
        elif len(username) > 20:
            error = "El nombre de usuario no puede exceder 20 caracteres."
        elif len(email) > 35:
            error = "El correo electrónico no puede exceder 35 caracteres."
        elif password != password2:
            error = "Las contraseñas no coinciden."
                                                               
        elif '/' in username or '\\' in username or '..' in username or '.' in username:
            error = "El nombre de usuario no puede contener caracteres especiales como /, \\, o puntos."
                                                                            
        elif username.lower() in ['admin', 'root', 'system', 'default', 'balulero', 'default-profile', 'logo', 'pingu']:
            error = "Este nombre de usuario está reservado por el sistema."
                                                   
        elif not re.match(r'^[A-Za-z0-9_-]+$', username):
            error = "El nombre de usuario solo puede contener letras, números, guiones y guiones bajos."
        else:
            from .extensions import db as alchemy_db
            from sqlalchemy.exc import IntegrityError
            
            pwd_hash = generate_password_hash(password)

            existing = User.query.filter(
                (User.username == username) | (User.email == email)
            ).first()

            if existing:
                error = "El usuario o el correo ya están registrados."
            else:

                from .models import Machine

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
                        
                        pending_message = (
                            "Tu solicitud de registro se ha enviado para revisión. "
                            "El nombre de usuario coincide con el de un autor de máquina o writeup, "
                            "y deberá ser aprobado por un administrador o moderador."
                        )
                    except Exception:
                        alchemy_db.session.rollback()
                        error = "Se ha producido un error al registrar la solicitud. Inténtalo más tarde."
                else:
                    try:
                                                 
                        new_user = User(
                            username=username,
                            email=email,
                            password_hash=pwd_hash,
                            role='jugador'
                        )

                        import string
                        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                        pin = ''.join(secrets.choice(alphabet) for i in range(15))
                        pin_hash = generate_password_hash(pin)
                        now_ts = datetime.utcnow()
                        
                        new_user.recovery_pin_hash = pin_hash
                        new_user.recovery_pin_plain = pin
                        new_user.recovery_pin_created_at = now_ts
                        
                        alchemy_db.session.add(new_user)
                        alchemy_db.session.commit()

                        recovery_pin = pin
                        pending_message = "Cuenta creada correctamente. Conserve su PIN de recuperación (nunca expira)."

                    except IntegrityError:
                        alchemy_db.session.rollback()
                        error = "El usuario o el correo ya están registrados."
                    except Exception as e:
                        alchemy_db.session.rollback()
                        error = f"Error al crear usuario: {str(e)}"

    remaining = session.pop('rate_limit_remaining', None)
    return render_template('dockerlabs/register.html', error=error, pending_message=pending_message, recovery_pin=recovery_pin)

@auth_bp.route('/recover', methods=['GET', 'POST'])
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])

def recover():
    """
    Password recovery endpoint.
    ---
    tags:
      - Auth
    responses:
      200:
        description: Recovery page or redirect to login.
    """
    error = None
    success = None

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        pin = request.form.get('pin', '').strip()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        if not username or not pin or not password:
            error = "Todos los campos son obligatorios."
        elif password != password2:
            error = "Las contraseñas no coinciden."
        else:
            from .extensions import db as alchemy_db
            
            user_obj = User.query.filter_by(username=username).first()

            if not user_obj:
                error = "Usuario no encontrado."
            elif not user_obj.recovery_pin_hash:
                error = "No hay un PIN de recuperación registrado para este usuario. Regístrate nuevamente o contacta al soporte."
            else:
                if not check_password_hash(user_obj.recovery_pin_hash, pin):
                    error = "PIN incorrecto."
                else:
                    if user_obj.recovery_pin_created_at:
                         # PIN retrieval logic changed: PINs no longer expire
                         new_pwd_hash = generate_password_hash(password)
                         user_obj.password_hash = new_pwd_hash
                         user_obj.recovery_pin_hash = None
                         user_obj.recovery_pin_created_at = None
                         
                         alchemy_db.session.commit()
                         return redirect(url_for('auth.login', success="Contraseña actualizada correctamente."))
                    else:
                         error = "Error en la fecha de emisión del PIN. Contacta al soporte."

    return render_template('dockerlabs/recover.html', error=error)

@auth_bp.route('/login', methods=['GET', 'POST'])
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])

def login():
    """
    User login endpoint.
    ---
    tags:
      - Auth
    responses:
      200:
        description: Login page or redirect to dashboard.
    """
    error = None
    success = request.args.get('success')

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if user is None or not check_password_hash(user.password_hash, password):
            error = "Usuario o contraseña incorrectos."
        else:
            session.clear()
                               
            login_user(user)

            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('dashboard'))

    remaining = session.pop('rate_limit_remaining', None)
    return render_template('dockerlabs/login.html', error=error, success=success)


@auth_bp.route('/auth/api_login', methods=['POST'])
@csrf_protect
@limiter.limit("10 per minute", methods=["POST"])
def api_login():
    """
    API login endpoint for SPA clients. Accepts JSON {username,password} and returns JSON.
    """
    data = request.json or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({'success': False, 'message': 'Faltan credenciales'}), 400

    user = User.query.filter_by(username=username).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return jsonify({'success': False, 'message': 'Usuario o contraseña incorrectos'}), 401

    # login the user and set session
    session.clear()
    login_user(user)
    session['user_id'] = user.id
    session['username'] = user.username

    return jsonify({'success': True, 'redirect': url_for('dashboard')})

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

@auth_bp.route('/api/change_password', methods=['POST'])
@role_required('admin', 'moderador', 'jugador')
@csrf_protect
@limiter.limit("10 per minute")

def api_change_password():
    """
    Change current user password.
    ---
    tags:
      - User
    responses:
      200:
        description: Password updated successfully.
      400:
        description: Invalid input or password requirements not met.
    """
    data = request.json or {}
    current = (data.get('current_password') or '').strip()
    new = (data.get('new_password') or '').strip()

    if not current or not new:
        return jsonify({"error": "Faltan datos"}), 400

    if len(new) < 8:
        return jsonify({"error": "La nueva contraseña debe tener al menos 8 caracteres"}), 400
    if not any(c.isupper() for c in new) or not any(c.isdigit() for c in new) or not any(not c.isalnum() for c in new):
        return jsonify({"error": "La nueva contraseña debe incluir mayúscula, número y carácter especial"}), 400

    from .extensions import db as alchemy_db
    
    username = (session.get('username') or '').strip()
    if not username:
        return jsonify({"error": "Debes iniciar sesión."}), 403

    user_obj = User.query.filter_by(username=username).first()
    if not user_obj:
        return jsonify({"error": "Usuario no encontrado."}), 404

    if not check_password_hash(user_obj.password_hash, current):
        return jsonify({"error": "La contraseña actual es incorrecta."}), 403

    try:
        new_hash = generate_password_hash(new)
        user_obj.password_hash = new_hash
        alchemy_db.session.commit()
        return jsonify({"message": "Contraseña actualizada correctamente."}), 200
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({"error": f"Error al actualizar la contraseña: {str(e)}"}), 500

@auth_bp.route('/api/update_profile', methods=['POST'])
@role_required('admin', 'moderador', 'jugador')
@csrf_protect
@limiter.limit("10 per minute")

def update_profile():
    """
    Update user profile biography.
    ---
    tags:
      - User
    responses:
      200:
        description: Profile updated.
    """
    data = request.json
    biography = data.get('biography', '')

    if biography is None:
        biography = ''

    if len(biography) > 500:
        return jsonify({"error": "La biografía no puede exceder los 500 caracteres."}), 400

    from .extensions import db as alchemy_db

    user_id = session.get('user_id')
    user_obj = User.query.get(user_id)
    
    if not user_obj:
         return jsonify({"error": "Usuario no encontrado"}), 404

    try:
        user_obj.biography = biography
        alchemy_db.session.commit()
        return jsonify({"message": "Perfil actualizado correctamente."}), 200
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({"error": f"Error al actualizar el perfil: {str(e)}"}), 500

@auth_bp.route('/api/update_social_links', methods=['POST'])
@role_required('admin', 'moderador', 'jugador')
@csrf_protect
@limiter.limit("10 per minute")

def update_social_links():
    """
    Update user social media links.
    ---
    tags:
      - User
    responses:
      200:
        description: Links updated.
    """
                                                                      
    data = request.json or {}
    
    linkedin_url = (data.get('linkedin_url') or '').strip()
    github_url = (data.get('github_url') or '').strip()
    youtube_url = (data.get('youtube_url') or '').strip()

    def is_valid_url(url, domain_regex):
        if not url:
            return True, None

        dangerous_chars = ['"', "'", '<', '>', '`']
        for char in dangerous_chars:
            if char in url:
                return False, f"La URL contiene caracteres no permitidos: {char}"

        try:
            parsed = urlparse(url)
                                                               
            if not parsed.scheme or not parsed.netloc:
                return False, "La URL no tiene un formato válido"

            scheme_lower = parsed.scheme.lower()
            dangerous_protocols = ['javascript', 'data', 'vbscript', 'file', 'about']
            if scheme_lower in dangerous_protocols:
                return False, f"El protocolo '{parsed.scheme}:' no está permitido por razones de seguridad"

            if scheme_lower not in ('http', 'https'):
                return False, "Solo se permiten URLs con http o https"
        except Exception:
            return False, "Error al analizar la URL"

        url_pattern = re.compile(
            r'^https?://'                       
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'             
            r'localhost|'                
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'            
            r'(?::\d+)?'                 
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if url_pattern.match(url) is None:
            return False, "El formato de la URL no es válido"

        if not re.match(domain_regex, url, re.IGNORECASE):
            return False, "La URL no pertenece al dominio esperado"
        
        return True, None
    
    linkedin_regex = r'^https://(www\.)?linkedin\.com/.*$'
    github_regex = r'^https://(www\.)?github\.com/.*$'
    youtube_regex = r'^https://(www\.)?(youtube\.com|youtu\.be)/.*$'

    if linkedin_url:
        valid, error = is_valid_url(linkedin_url, linkedin_regex)
        if not valid:
            return jsonify({"error": f"URL de LinkedIn inválida: {error}"}), 400
    
    if github_url:
        valid, error = is_valid_url(github_url, github_regex)
        if not valid:
            return jsonify({"error": f"URL de GitHub inválida: {error}"}), 400
    
    if youtube_url:
        valid, error = is_valid_url(youtube_url, youtube_regex)
        if not valid:
            return jsonify({"error": f"URL de YouTube inválida: {error}"}), 400

    linkedin_url = linkedin_url if linkedin_url else None
    github_url = github_url if github_url else None
    youtube_url = youtube_url if youtube_url else None
    
    user_id = session.get('user_id')
    
    from .extensions import db as alchemy_db
    
    try:
        user_obj = User.query.get(user_id)
        if not user_obj:
            return jsonify({"error": "Usuario no encontrado"}), 404
            
        user_obj.linkedin_url = linkedin_url
        user_obj.github_url = github_url
        user_obj.youtube_url = youtube_url
        
        alchemy_db.session.commit()
        return jsonify({"message": "Enlaces de redes sociales actualizados correctamente."}), 200


    @auth_bp.route('/api/me')
    def api_me():
        """
        Return current authenticated user info for SPA.
        """
        if 'user_id' not in session:
            return jsonify({'authenticated': False}), 401

        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'authenticated': False}), 404

        profile_path = get_profile_image_static_path(user.username, user_id=user.id)
        profile_image_url = url_for('static', filename=profile_path)

        return jsonify({
            'authenticated': True,
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'biography': user.biography,
            'linkedin_url': user.linkedin_url,
            'github_url': user.github_url,
            'youtube_url': user.youtube_url,
            'profile_image_url': profile_image_url,
            'role': user.role
        })
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({"error": f"Error al actualizar enlaces: {str(e)}"}), 500

@auth_bp.route('/upload-profile-photo', methods=['POST'])
@role_required('admin', 'moderador', 'jugador')
@csrf_protect
@limiter.limit("10 per minute", methods=["POST"])

def upload_profile_photo():
    """
    Upload profile photo.
    ---
    tags:
      - User
    consumes:
      - multipart/form-data
    parameters:
      - name: photo
        in: formData
        type: file
        required: true
    responses:
      200:
        description: Photo uploaded.
    """
    from PIL import Image
    import tempfile
    import shutil
    import time
    import logging

    if 'username' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    file = request.files.get('photo')
    if not file or file.filename == '':
        return jsonify({'error': 'No se ha enviado ningún archivo'}), 400

    if not file.mimetype.startswith('image/'):
        return jsonify({'error': 'El archivo debe ser una imagen'}), 400

    MAX_UPLOAD_BYTES = 5 * 1024 * 1024
    file_bytes = file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        return jsonify({'error': 'La imagen es demasiado grande (máx 5MB)'}), 400

    try:
        file.stream.seek(0)
        img = Image.open(file.stream)
        img.verify()
    except Exception as exc:
        logging.exception("Verificación de imagen fallida")
        return jsonify({'error': 'La imagen enviada no es válida'}), 400

    try:
        file.stream.seek(0)
    except Exception:
                                                           
        file = type(file)(io.BytesIO(file_bytes), filename=getattr(file, 'filename', 'upload'))

    original_filename = secure_filename(file.filename or '')
    _, ext = os.path.splitext(original_filename)
    ext = ext.lower()
    if ext not in ALLOWED_PROFILE_EXTENSIONS:
        return jsonify({'error': 'Formato de imagen no permitido'}), 400

    valid, error = validators.validate_image_content(file.stream)
    if not valid:
        return jsonify({'error': f'Archivo inválido: {error}'}), 400

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'No se ha podido determinar el ID de usuario'}), 400

    os.makedirs(PROFILE_UPLOAD_FOLDER, exist_ok=True)

    final_filename = f"{user_id}{ext}"
    save_path = os.path.join(PROFILE_UPLOAD_FOLDER, final_filename)

    try:
        fd, tmp_path = tempfile.mkstemp(dir=PROFILE_UPLOAD_FOLDER, prefix=".profile_upload.tmp.", suffix=ext)
        os.close(fd)
                                 
        with open(tmp_path, 'wb') as fh:
                                                                      
            if 'file_bytes' in locals() and file_bytes:
                fh.write(file_bytes)
            else:
                file.stream.seek(0)
                shutil.copyfileobj(file.stream, fh)

        try:
            os.chmod(tmp_path, 0o644)
        except Exception:
            pass

        os.replace(tmp_path, save_path)

    except Exception as exc:
        logging.exception("Error al guardar la foto de perfil")
                                                    
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return jsonify({'error': 'Error al guardar la imagen en el servidor'}), 500

    ts = int(time.time())
    image_url = url_for('static', filename=f'dockerlabs/images/perfiles/{final_filename}') + f"?t={ts}"

    return jsonify({
        'message': 'Foto de perfil actualizada correctamente.',
        'image_url': image_url
    }), 200

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

    return render_template('dockerlabs/gestion_usuarios.html', usuarios=usuarios)

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
