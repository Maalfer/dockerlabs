import os
import json
import re
import secrets
import sqlite3
import io
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, g, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from urllib.parse import urlparse, urljoin

from .database import get_db
from .decorators import role_required, csrf_protect, get_current_role
from . import validators
from bunkerlabs.extensions import limiter

# Configuración de carpetas (importadas desde app.py)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PROFILE_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'images', 'perfiles')
ALLOWED_PROFILE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

# Crear el Blueprint
auth_bp = Blueprint('auth', __name__)


def get_profile_image_static_path(username):
    if not username:
        return None

    for ext in ALLOWED_PROFILE_EXTENSIONS:
        candidate = os.path.join(PROFILE_UPLOAD_FOLDER, f"{username}{ext}")
        if os.path.exists(candidate):
            return f"images/perfiles/{username}{ext}"

    return None


def load_username_change_requests():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT
            r.*,
            u.email AS user_email,
            COUNT(ws.id) AS conflict_count,
            GROUP_CONCAT(ws.maquina || ' (id:' || ws.id || ')', ', ') AS conflict_examples
        FROM username_change_requests r
        LEFT JOIN users u ON u.id = r.user_id
        LEFT JOIN writeups_subidos ws ON ws.autor = r.requested_username
        GROUP BY r.id
        ORDER BY r.created_at DESC, r.id DESC
    """)
    rows = cursor.fetchall()
    return rows


@auth_bp.route('/register', methods=['GET', 'POST'])
@csrf_protect
@limiter.limit("3 per minute", methods=["POST"])
def register():
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
        else:
            db = get_db()
            pwd_hash = generate_password_hash(password)

            existing = db.execute(
                "SELECT id FROM users WHERE username = ? OR email = ?",
                (username, email)
            ).fetchone()

            if existing:
                error = "El usuario o el correo ya están registrados."
            else:
                autor_exists = db.execute(
                    """
                    SELECT 1 FROM maquinas WHERE autor = ?
                    UNION
                    SELECT 1 FROM writeups_subidos WHERE autor = ?
                    UNION
                    SELECT 1 FROM writeups_recibidos WHERE autor = ?
                    LIMIT 1
                    """,
                    (username, username, username)
                ).fetchone()

                if autor_exists:
                    try:
                        db.execute(
                            """
                            INSERT INTO nombre_claims (
                                username,
                                email,
                                password_hash,
                                nombre_solicitado,
                                nombre_actual,
                                motivo,
                                estado
                            )
                            VALUES (?, ?, ?, ?, ?, ?, 'pendiente')
                            """,
                            (
                                username,
                                email,
                                pwd_hash,
                                username,
                                username,
                                "Solicitud de registro con nombre coincidente con autor de máquina o writeup."
                            )
                        )
                        db.commit()
                        pending_message = (
                            "Tu solicitud de registro se ha enviado para revisión. "
                            "El nombre de usuario coincide con el de un autor de máquina o writeup, "
                            "y deberá ser aprobado por un administrador o moderador."
                        )
                    except sqlite3.Error:
                        error = "Se ha producido un error al registrar la solicitud. Inténtalo más tarde."
                else:
                    try:
                        db.execute(
                            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                            (username, email, pwd_hash, 'jugador')
                        )
                        db.commit()

                        pin = f"{secrets.randbelow(10**6):06d}"
                        pin_hash = generate_password_hash(pin)
                        now_ts = datetime.utcnow().isoformat(timespec='seconds')

                        db.execute(
                            "UPDATE users SET recovery_pin_hash = ?, recovery_pin_created_at = ? WHERE username = ?",
                            (pin_hash, now_ts, username)
                        )
                        db.commit()

                        recovery_pin = pin
                        pending_message = "Cuenta creada correctamente. Guarda tu PIN de recuperación."

                    except sqlite3.IntegrityError:
                        error = "El usuario o el correo ya están registrados."

    remaining = session.pop('rate_limit_remaining', None)
    return render_template('register.html', error=error, pending_message=pending_message, recovery_pin=recovery_pin)


@auth_bp.route('/recover', methods=['GET', 'POST'])
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def recover():
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
            db = get_db()
            row = db.execute(
                "SELECT id, recovery_pin_hash, recovery_pin_created_at FROM users WHERE username = ?",
                (username,)
            ).fetchone()

            if not row:
                error = "Usuario no encontrado."
            elif not row['recovery_pin_hash']:
                error = "No hay un PIN de recuperación registrado para este usuario. Regístrate nuevamente o contacta al soporte."
            else:
                stored_pin_hash = row['recovery_pin_hash']
                if not check_password_hash(stored_pin_hash, pin):
                    error = "PIN incorrecto."
                else:
                    created_at = row['recovery_pin_created_at']
                    try:
                        created_dt = datetime.fromisoformat(created_at)
                    except Exception:
                        created_dt = None

                    if created_dt:
                        if datetime.utcnow() - created_dt > timedelta(days=7):
                            error = "El PIN ha expirado. Solicita uno nuevo registrándote o contactando soporte."
                        else:
                            new_pwd_hash = generate_password_hash(password)
                            db.execute(
                                "UPDATE users SET password_hash = ?, recovery_pin_hash = NULL, recovery_pin_created_at = NULL WHERE username = ?",
                                (new_pwd_hash, username)
                            )
                            db.commit()
                            return redirect(url_for('auth.login', success="Contraseña actualizada correctamente."))
                    else:
                        error = "Error en la fecha de emisión del PIN. Contacta al soporte."

    return render_template('recover.html', error=error)


@auth_bp.route('/login', methods=['GET', 'POST'])
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def login():
    error = None
    success = request.args.get('success')

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        db = get_db()
        cur = db.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,)
        )
        user = cur.fetchone()

        if user is None or not check_password_hash(user['password_hash'], password):
            error = "Usuario o contraseña incorrectos."
        else:
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))

    remaining = session.pop('rate_limit_remaining', None)
    return render_template('login.html', error=error, success=success)


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@auth_bp.route('/api/change_password', methods=['POST'])
@role_required('admin', 'moderador', 'jugador')
@csrf_protect
@limiter.limit("10 per minute")
def api_change_password():
    data = request.json or {}
    current = (data.get('current_password') or '').strip()
    new = (data.get('new_password') or '').strip()

    if not current or not new:
        return jsonify({"error": "Faltan datos"}), 400

    # opcional: validación de requisitos en servidor
    if len(new) < 8:
        return jsonify({"error": "La nueva contraseña debe tener al menos 8 caracteres"}), 400
    if not any(c.isupper() for c in new) or not any(c.isdigit() for c in new) or not any(not c.isalnum() for c in new):
        return jsonify({"error": "La nueva contraseña debe incluir mayúscula, número y carácter especial"}), 400

    db = get_db()
    username = (session.get('username') or '').strip()
    if not username:
        return jsonify({"error": "Debes iniciar sesión."}), 403

    user = db.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,)).fetchone()
    if not user:
        return jsonify({"error": "Usuario no encontrado."}), 404

    if not check_password_hash(user['password_hash'], current):
        return jsonify({"error": "La contraseña actual es incorrecta."}), 403

    try:
        new_hash = generate_password_hash(new)
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user['id']))
        db.commit()
        return jsonify({"message": "Contraseña actualizada correctamente."}), 200
    except Exception as e:
        return jsonify({"error": f"Error al actualizar la contraseña: {str(e)}"}), 500


@auth_bp.route('/api/update_profile', methods=['POST'])
@role_required('admin', 'moderador', 'jugador')
@csrf_protect
@limiter.limit("10 per minute")
def update_profile():
    data = request.json
    biography = data.get('biography', '')
    
    # Don't strip - preserve user's formatting including leading/trailing whitespace
    if biography is None:
        biography = ''

    if len(biography) > 500:
        return jsonify({"error": "La biografía no puede exceder los 500 caracteres."}), 400

    user_id = session.get('user_id')
    
    try:
        db = get_db()
        db.execute(
            "UPDATE users SET biography = ? WHERE id = ?",
            (biography, user_id)
        )
        db.commit()
        return jsonify({"message": "Perfil actualizado correctamente."}), 200
    except Exception as e:
        return jsonify({"error": f"Error al actualizar el perfil: {str(e)}"}), 500


@auth_bp.route('/api/update_social_links', methods=['POST'])
@role_required('admin', 'moderador', 'jugador')
@csrf_protect
@limiter.limit("10 per minute")
def update_social_links():
    """Update user's social media links (LinkedIn, GitHub, YouTube)"""
    data = request.json or {}
    
    linkedin_url = (data.get('linkedin_url') or '').strip()
    github_url = (data.get('github_url') or '').strip()
    youtube_url = (data.get('youtube_url') or '').strip()
    
    # Validate URLs - they should either be empty or valid URLs
    def is_valid_url(url, domain_regex):
        if not url:
            return True, None
        
        # SECURITY: Check for dangerous characters that could be used for XSS attacks
        # These characters can break out of HTML attributes
        dangerous_chars = ['"', "'", '<', '>', '`']
        for char in dangerous_chars:
            if char in url:
                return False, f"La URL contiene caracteres no permitidos: {char}"
        
        # Validate URL structure using urllib.parse
        try:
            parsed = urlparse(url)
            # Must have scheme (http/https) and netloc (domain)
            if not parsed.scheme or not parsed.netloc:
                return False, "La URL no tiene un formato válido"
            # Only allow http and https schemes
            if parsed.scheme not in ('http', 'https'):
                return False, "Solo se permiten URLs con http o https"
        except Exception:
            return False, "Error al analizar la URL"
        
        # Basic URL validation with regex
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if url_pattern.match(url) is None:
            return False, "El formato de la URL no es válido"
            
        # Domain specific validation
        if not re.match(domain_regex, url, re.IGNORECASE):
            return False, "La URL no pertenece al dominio esperado"
        
        return True, None
    
    linkedin_regex = r'^https://(www\.)?linkedin\.com/.*$'
    github_regex = r'^https://(www\.)?github\.com/.*$'
    youtube_regex = r'^https://(www\.)?(youtube\.com|youtu\.be)/.*$'

    # Validate each URL and return specific error messages
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
    
    # Convert empty strings to None for database
    linkedin_url = linkedin_url if linkedin_url else None
    github_url = github_url if github_url else None
    youtube_url = youtube_url if youtube_url else None
    
    user_id = session.get('user_id')
    
    try:
        db = get_db()
        db.execute(
            """UPDATE users 
               SET linkedin_url = ?, github_url = ?, youtube_url = ? 
               WHERE id = ?""",
            (linkedin_url, github_url, youtube_url, user_id)
        )
        db.commit()
        return jsonify({"message": "Enlaces de redes sociales actualizados correctamente."}), 200
    except Exception as e:
        return jsonify({"error": f"Error al actualizar enlaces: {str(e)}"}), 500


@auth_bp.route('/upload-profile-photo', methods=['POST'])
@role_required('admin', 'moderador', 'jugador')
@csrf_protect
@limiter.limit("10 per minute", methods=["POST"])
def upload_profile_photo():
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

    # resetear stream para Pillow
    try:
        file.stream.seek(0)
        img = Image.open(file.stream)
        img.verify()
    except Exception as exc:
        logging.exception("Verificación de imagen fallida")
        return jsonify({'error': 'La imagen enviada no es válida'}), 400

    # resetear stream para guardar
    try:
        file.stream.seek(0)
    except Exception:
        # si no es seekable, reconstruimos desde file_bytes
        file = type(file)(io.BytesIO(file_bytes), filename=getattr(file, 'filename', 'upload'))

    original_filename = secure_filename(file.filename or '')
    _, ext = os.path.splitext(original_filename)
    ext = ext.lower()
    if ext not in ALLOWED_PROFILE_EXTENSIONS:
        return jsonify({'error': 'Formato de imagen no permitido'}), 400

    # Validar contenido real de la imagen
    valid, error = validators.validate_image_content(file.stream)
    if not valid:
        return jsonify({'error': f'Archivo inválido: {error}'}), 400

    username = (session.get('username') or '').strip()
    if not username:
        return jsonify({'error': 'No se ha podido determinar el usuario'}), 400

    # asegurar existencia del directorio
    os.makedirs(PROFILE_UPLOAD_FOLDER, exist_ok=True)

    final_filename = f"{username}{ext}"
    save_path = os.path.join(PROFILE_UPLOAD_FOLDER, final_filename)

    # Guardado atómico: escribe en archivo temporal y luego replace
    # Nota: No incluimos el username en el nombre temporal para evitar problemas
    # de encoding Unicode en entornos Apache/WSGI con locale ASCII
    try:
        fd, tmp_path = tempfile.mkstemp(dir=PROFILE_UPLOAD_FOLDER, prefix=".profile_upload.tmp.", suffix=ext)
        os.close(fd)
        # write bytes to tmp file
        with open(tmp_path, 'wb') as fh:
            # si ya tenemos file_bytes, úsalos; si no, leer del stream
            if 'file_bytes' in locals() and file_bytes:
                fh.write(file_bytes)
            else:
                file.stream.seek(0)
                shutil.copyfileobj(file.stream, fh)

        # permisos seguros (opcional)
        try:
            os.chmod(tmp_path, 0o644)
        except Exception:
            pass

        # mover de forma atómica al destino
        os.replace(tmp_path, save_path)

    except Exception as exc:
        logging.exception("Error al guardar la foto de perfil")
        # intenta limpiar fichero temporal si existe
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return jsonify({'error': 'Error al guardar la imagen en el servidor'}), 500

    # Forzar bust de cache en cliente añadiendo timestamp
    ts = int(time.time())
    image_url = url_for('static', filename=f'images/perfiles/{final_filename}') + f"?t={ts}"

    return jsonify({
        'message': 'Foto de perfil actualizada correctamente.',
        'image_url': image_url
    }), 200


@auth_bp.route('/gestion-usuarios')
@role_required('admin')
def gestion_usuarios():
    db = get_db()
    usuarios = db.execute(
        "SELECT id, username, email, role, created_at FROM users ORDER BY id ASC"
    ).fetchall()

    return render_template('gestion_usuarios.html', usuarios=usuarios)


@auth_bp.route('/update_user_role/<int:user_id>', methods=['POST'])
@role_required('admin')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"]) 
def update_user_role(user_id):
    nuevo_rol = (request.form.get('role') or '').strip().lower()
    if nuevo_rol not in ('jugador', 'moderador', 'admin'):
        return redirect(url_for('auth.gestion_usuarios'))
    db = get_db()
    db.execute(
        "UPDATE users SET role = ? WHERE id = ?",
        (nuevo_rol, user_id)
    )
    db.commit()
    return redirect(url_for('auth.gestion_usuarios'))


@auth_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@role_required('admin')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def delete_user(user_id):
    db = get_db()
    try:
        user = db.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            flash("Usuario no encontrado.")
            return redirect(url_for('auth.gestion_usuarios'))

        if session.get('user_id') == user_id:
            flash("No puedes eliminar tu propia cuenta desde aquí.")
            return redirect(url_for('auth.gestion_usuarios'))

        if user['role'] == 'admin':
            admins = db.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'admin'").fetchone()
            if admins and admins['cnt'] <= 1:
                flash("No se puede eliminar al último administrador.")
                return redirect(url_for('auth.gestion_usuarios'))

        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()
        flash("Usuario eliminado correctamente.")
    except sqlite3.IntegrityError:
        db.rollback()
        flash("No se puede eliminar el usuario por restricciones de integridad.")
    except Exception as e:
        db.rollback()
        flash("Error al eliminar el usuario: " + str(e))

    return redirect(url_for('auth.gestion_usuarios'))


@auth_bp.route('/request_username_change', methods=['POST'])
@csrf_protect
def request_username_change():
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

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM users WHERE username = ?", (requested_username,))
    if cursor.fetchone():
        flash("Ese nombre ya está en uso.", "danger")
        return redirect(url_for('dashboard'))

    cursor.execute("""
        INSERT INTO username_change_requests (user_id, old_username, requested_username, reason, contacto_opcional)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, old_username, requested_username, reason, contacto_opcional))

    db.commit()

    flash("Solicitud enviada. Un moderador o admin deberá aprobarla.", "success")
    return redirect(url_for('dashboard'))


@auth_bp.route('/approve_username_change/<int:request_id>', methods=['POST'])
@role_required('admin')
@csrf_protect
def approve_username_change(request_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM username_change_requests WHERE id = ?", (request_id,))
    req = cursor.fetchone()

    if not req:
        flash("Petición no encontrada.", "danger")
        return redirect(url_for('peticiones'))

    if req['estado'] != 'pendiente':
        flash("Esta petición ya fue procesada.", "warning")
        return redirect(url_for('peticiones'))

    requested_username = req['requested_username']

    cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (requested_username, req['user_id']))
    if cursor.fetchone():
        cursor.execute("""
            UPDATE username_change_requests
            SET estado='rechazada',
                processed_by=?,
                processed_at=datetime('now','localtime'),
                decision_reason='Nombre ya en uso al aprobar'
            WHERE id=?
        """, (session['user_id'], request_id))
        db.commit()
        flash("El nombre ya está en uso. No se pudo aprobar.", "danger")
        return redirect(url_for('peticiones'))

    cursor.execute("SELECT COUNT(1) AS cnt FROM writeups_subidos WHERE LOWER(autor) = LOWER(?)", (requested_username,))
    row = cursor.fetchone()
    conflict_count = row['cnt'] if row else 0

    if conflict_count > 0:
        decision_reason = f'Aprobado con conflicto: {conflict_count} writeup(s) tienen ese autor'
    else:
        decision_reason = 'Aprobado por admin'

    cursor.execute("UPDATE users SET username = ? WHERE id = ?", (requested_username, req['user_id']))

    if conflict_count == 0:
        try:
            cursor.execute(
                "UPDATE writeups_subidos SET autor = ? WHERE LOWER(autor) = LOWER(?)",
                (requested_username, req['old_username'])
            )
            cursor.execute(
                "UPDATE writeups_recibidos SET autor = ? WHERE LOWER(autor) = LOWER(?)",
                (requested_username, req['old_username'])
            )
            cursor.execute(
                "UPDATE ranking_writeups SET nombre = ? WHERE LOWER(nombre) = LOWER(?)",
                (requested_username, req['old_username'])
            )
            cursor.execute(
                "UPDATE ranking_creadores SET nombre = ? WHERE LOWER(nombre) = LOWER(?)",
                (requested_username, req['old_username'])
            )
            db.commit()
            try:
                from .writeups import recalcular_ranking_writeups
                recalcular_ranking_writeups()
            except Exception:
                pass
        except Exception:
            db.rollback()

    cursor.execute("""
        UPDATE username_change_requests
        SET estado='aprobada',
            processed_by=?,
            processed_at=datetime('now','localtime'),
            decision_reason=?
        WHERE id=?
    """, (session['user_id'], decision_reason, request_id))

    db.commit()

    if conflict_count > 0:
        flash(f"El nombre ha sido cambiado pero existe conflicto con {conflict_count} writeup(s). Revisa las alertas en peticiones.", "warning")
    else:
        flash(f"El nombre del usuario ha sido cambiado correctamente a {requested_username}.", "success")

    return redirect(url_for('peticiones'))


@auth_bp.route('/reject_username_change/<int:request_id>', methods=['POST'])
@role_required('admin')
@csrf_protect
def reject_username_change(request_id):
    reason = request.form.get("decision_reason", "Rechazado por moderador/admin")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM username_change_requests WHERE id = ?", (request_id,))
    req = cursor.fetchone()

    if not req:
        flash("Petición no encontrada.", "danger")
        return redirect(url_for('peticiones'))

    cursor.execute("""
        UPDATE username_change_requests
        SET estado='rechazada',
            processed_by=?,
            processed_at=datetime('now','localtime'),
            decision_reason=?
        WHERE id=?
    """, (session['user_id'], reason, request_id))

    db.commit()

    flash("Petición rechazada correctamente.", "info")
    return redirect(url_for('peticiones'))


@auth_bp.route('/username_change/<int:request_id>/revert', methods=['POST'])
@role_required('admin', 'moderador')
def revert_username_change(request_id):
    db = get_db()
    db.execute("UPDATE username_change_requests SET estado = 'pendiente' WHERE id = ?", (request_id,))
    db.commit()
    return redirect(url_for('peticiones'))
