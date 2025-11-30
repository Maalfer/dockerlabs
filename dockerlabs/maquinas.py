import os
import json
from datetime import datetime
import sqlite3
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash, current_app
from werkzeug.utils import secure_filename
from .database import get_db, get_bunker_db
from .decorators import role_required, csrf_protect, get_current_role
from bunkerlabs.extensions import limiter
from . import validators

maquinas_bp = Blueprint('maquinas', __name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MACHINE_LOGOS_FOLDER = os.path.join(BASE_DIR, 'static', 'images', 'logos')
LOGO_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'images', 'logos')
ALLOWED_LOGO_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
ALLOWED_PROFILE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

def recalcular_ranking_creadores():
    db = get_db()

    rows = db.execute(
        """
        SELECT autor, COUNT(*) AS maquinas
        FROM maquinas
        GROUP BY autor
        """
    ).fetchall()

    db.execute("DELETE FROM ranking_creadores")

    for row in rows:
        nombre = (row["autor"] or "").strip()
        maquinas = row["maquinas"] or 0

        if not nombre:
            continue

        db.execute(
            """
            INSERT INTO ranking_creadores (nombre, maquinas)
            VALUES (?, ?)
            """,
            (nombre, maquinas),
        )

    db.commit()

@maquinas_bp.route('/gestion-maquinas')
@role_required('admin', 'moderador', 'jugador')
def gestion_maquinas():
    db = get_db()
    bunker_db = get_bunker_db()

    current_username = (session.get('username') or '').strip()
    role = get_current_role()

    if role in ('admin', 'moderador'):
        maquinas_docker = db.execute(
            "SELECT * FROM maquinas ORDER BY id ASC"
        ).fetchall()

        maquinas_bunker = bunker_db.execute(
            "SELECT * FROM maquinas ORDER BY id ASC"
        ).fetchall()
    else:
        if not current_username:
            maquinas_docker = []
            maquinas_bunker = []
        else:
            maquinas_docker = db.execute(
                """
                SELECT *
                FROM maquinas
                WHERE autor = ?
                ORDER BY id ASC
                """,
                (current_username,)
            ).fetchall()

            maquinas_bunker = bunker_db.execute(
                """
                SELECT *
                FROM maquinas
                WHERE autor = ?
                ORDER BY id ASC
                """,
                (current_username,)
            ).fetchall()

    # Fetch categories for machines
    categorias_map = {}
    if maquinas_docker:
        db_main = get_db()
        for m in maquinas_docker:
            cat = db_main.execute(
                "SELECT categoria FROM categorias WHERE machine_id = ? AND origen = 'docker'",
                (m['id'],)
            ).fetchone()
            categorias_map[('docker', m['id'])] = cat['categoria'] if cat else ''
    
    if maquinas_bunker:
        db_main = get_db()
        for m in maquinas_bunker:
            cat = db_main.execute(
                "SELECT categoria FROM categorias WHERE machine_id = ? AND origen = 'bunker'",
                (m['id'],)
            ).fetchone()
            categorias_map[('bunker', m['id'])] = cat['categoria'] if cat else ''

    return render_template(
        'gestion_maquinas.html',
        maquinas_docker=maquinas_docker,
        maquinas_bunker=maquinas_bunker,
        current_username=current_username,
        categorias_map=categorias_map
    )

@maquinas_bp.route('/gestion-maquinas/actualizar', methods=['POST'])
@role_required('admin', 'moderador', 'jugador')
@csrf_protect
@limiter.limit("8 per minute", methods=["POST"])
def actualizar_maquina():
    origen = (request.form.get('origen') or '').strip()
    maquina_id = request.form.get('id')

    if not maquina_id or origen not in ('docker', 'bunker'):
        return redirect(url_for('maquinas.gestion_maquinas'))

    try:
        maquina_id = int(maquina_id)
    except ValueError:
        return redirect(url_for('maquinas.gestion_maquinas'))

    nombre = (request.form.get('nombre') or '').strip()
    dificultad = (request.form.get('dificultad') or '').strip()
    autor = (request.form.get('autor') or '').strip()
    enlace_autor = (request.form.get('enlace_autor') or '').strip()
    fecha = (request.form.get('fecha') or '').strip()
    imagen = (request.form.get('imagen') or '').strip()
    descripcion = (request.form.get('descripcion') or '').strip()
    link_descarga = (request.form.get('link_descarga') or '').strip()
    categoria = (request.form.get('categoria') or '').strip()
    
    # Auto-assign color and class based on difficulty
    difficulty_map = {
        'Muy Fácil': {'color': '#43959b', 'clase': 'muy-facil'},
        'Fácil': {'color': '#8bc34a', 'clase': 'facil'},
        'Medio': {'color': '#e0a553', 'clase': 'medio'},
        'Difícil': {'color': '#d83c31', 'clase': 'dificil'}
    }
    
    mapping = difficulty_map.get(dificultad, {'color': '#8bc34a', 'clase': 'facil'})
    clase = mapping['clase']
    color = mapping['color']

    if origen == 'docker':
        db = get_db()
    else:
        db = get_bunker_db()

    maquina = db.execute(
        "SELECT * FROM maquinas WHERE id = ?",
        (maquina_id,)
    ).fetchone()

    if maquina is None:
        return redirect(url_for('maquinas.gestion_maquinas'))

    role = get_current_role()
    username = (session.get('username') or '').strip()

    if role not in ('admin', 'moderador'):
        if role == 'jugador' and maquina['autor'] == username:
            nuevos_datos = json.dumps({
                "nombre": nombre,
                "dificultad": dificultad,
                "clase": clase,
                "color": color,
                "autor": autor,
                "enlace_autor": enlace_autor,
                "fecha": fecha,
                "imagen": imagen,
                "descripcion": descripcion,
                "link_descarga": link_descarga
            })

            db_main = get_db()
            db_main.execute(
                """
                INSERT INTO machine_edit_requests (
                    machine_id, origen, autor, nuevos_datos, estado
                )
                VALUES (?, ?, ?, ?, 'pendiente')
                """,
                (maquina_id, origen, username, nuevos_datos)
            )
            db_main.commit()

            return redirect(url_for('maquinas.gestion_maquinas'))

        return render_template('403.html'), 403

    try:
        db.execute(
            """
            UPDATE maquinas
            SET nombre = ?, dificultad = ?, clase = ?, color = ?, autor = ?, enlace_autor = ?,
                fecha = ?, imagen = ?, descripcion = ?, link_descarga = ?
            WHERE id = ?
            """,
            (
                nombre,
                dificultad,
                clase,
                color,
                autor,
                enlace_autor,
                fecha,
                imagen,
                descripcion,
                link_descarga,
                maquina_id
            )
        )
        db.commit()

        # Update category in categorias table (main database)
        db_main = get_db()
        if categoria:
            # Insert or replace category
            db_main.execute(
                """
                INSERT OR REPLACE INTO categorias (machine_id, origen, categoria)
                VALUES (?, ?, ?)
                """,
                (maquina_id, origen, categoria)
            )
        else:
            # Remove category if empty
            db_main.execute(
                "DELETE FROM categorias WHERE machine_id = ? AND origen = ?",
                (maquina_id, origen)
            )
        db_main.commit()

        if origen == 'docker':
            recalcular_ranking_creadores()

    except Exception:
        pass

    return redirect(url_for('maquinas.gestion_maquinas'))

@maquinas_bp.route('/gestion-maquinas/eliminar', methods=['POST'])
@role_required('admin', 'moderador', 'jugador')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"]) 
def eliminar_maquina():
    origen = (request.form.get('origen') or '').strip()
    maquina_id = request.form.get('id')

    if not maquina_id or origen not in ('docker', 'bunker'):
        return redirect(url_for('maquinas.gestion_maquinas'))

    try:
        maquina_id = int(maquina_id)
    except ValueError:
        return redirect(url_for('maquinas.gestion_maquinas'))

    if origen == 'docker':
        db = get_db()
    else:
        db = get_bunker_db()

    maquina = db.execute(
        "SELECT * FROM maquinas WHERE id = ?",
        (maquina_id,)
    ).fetchone()
    if maquina is None:
        return redirect(url_for('maquinas.gestion_maquinas'))

    role = get_current_role()
    username = (session.get('username') or '').strip()

    if role not in ('admin', 'moderador') and not (role == 'jugador' and maquina['autor'] == username):
        return render_template('403.html'), 403

    try:
        # Delete associated image file if exists (for BunkerLabs machines)
        if origen == 'bunker' and maquina.get('imagen'):
            imagen_path = maquina['imagen']
            # Full path: static/images/logos-bunkerlabs/filename.ext
            full_image_path = os.path.join(BASE_DIR, 'static', 'images', imagen_path)
            if os.path.exists(full_image_path):
                try:
                    os.remove(full_image_path)
                except Exception as e:
                    # Log but don't fail if image deletion fails
                    print(f"Warning: Could not delete image {full_image_path}: {e}")
        
        db.execute(
            "DELETE FROM maquinas WHERE id = ?",
            (maquina_id,)
        )
        db.commit()
        if origen == 'docker':
            recalcular_ranking_creadores()
    except Exception:
        pass

    return redirect(url_for('maquinas.gestion_maquinas'))

@maquinas_bp.route('/gestion-maquinas/upload-logo', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("10 per minute", methods=["POST"])
def upload_machine_logo():
    """Upload a logo image for a machine"""
    from PIL import Image
    import tempfile
    
    machine_id = request.form.get('machine_id')
    origen = request.form.get('origen', '').strip()
    
    if not machine_id or origen not in ('docker', 'bunker'):
        return jsonify({'error': 'Datos inválidos'}), 400
    
    file = request.files.get('logo')
    if not file or file.filename == '':
        return jsonify({'error': 'No se ha enviado ningún archivo'}), 400
    
    # Validate file type
    if not file.mimetype.startswith('image/'):
        return jsonify({'error': 'El archivo debe ser una imagen'}), 400
    
    # Size limit: 2MB
    MAX_SIZE = 2 * 1024 * 1024
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    if file_length > MAX_SIZE:
        return jsonify({'error': 'La imagen es demasiado grande (máx 2MB)'}), 400
    file.seek(0)
    
    # Validate image content
    valid, error = validators.validate_image_content(file.stream)
    if not valid:
        return jsonify({'error': f'Imagen inválida: {error}'}), 400
    
    # Secure filename
    original_filename = secure_filename(file.filename or '')
    _, ext = os.path.splitext(original_filename)
    ext = ext.lower()
    
    if ext not in ALLOWED_LOGO_EXTENSIONS:
        return jsonify({'error': 'Formato de imagen no permitido'}), 400
    
    # Create filename
    if origen == 'bunker':
        db = get_bunker_db()
        maquina = db.execute("SELECT nombre FROM maquinas WHERE id = ?", (machine_id,)).fetchone()
        if maquina:
            nombre_seguro = secure_filename(maquina['nombre'])
            final_filename = f"{nombre_seguro}{ext}"
        else:
             timestamp = int(datetime.now().timestamp())
             final_filename = f"{origen}_{machine_id}_{timestamp}{ext}"
    else:
        timestamp = int(datetime.now().timestamp())
        final_filename = f"{origen}_{machine_id}_{timestamp}{ext}"
    
    if origen == 'bunker':
        upload_folder = os.path.join(BASE_DIR, 'static', 'images', 'logos-bunkerlabs')
        db_path_prefix = "logos-bunkerlabs"
    else:
        upload_folder = MACHINE_LOGOS_FOLDER
        db_path_prefix = "logos"

    # Ensure directory exists
    os.makedirs(upload_folder, exist_ok=True)
    
    save_path = os.path.join(upload_folder, final_filename)
    
    # Save file atomically
    try:
        fd, tmp_path = tempfile.mkstemp(dir=upload_folder, prefix=f".{origen}_{machine_id}.tmp.")
        os.close(fd)
        
        with open(tmp_path, 'wb') as fh:
            file.stream.seek(0)
            fh.write(file.stream.read())
        
        os.chmod(tmp_path, 0o644)
        os.replace(tmp_path, save_path)
        
    except Exception as e:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except:
            pass
        return jsonify({'error': f'Error al guardar la imagen: {str(e)}'}), 500
    
    # Return the relative path for the database
    relative_path = f"{db_path_prefix}/{final_filename}"
    
    return jsonify({
        'message': 'Logo subido correctamente',
        'image_path': relative_path,
        'filename': final_filename
    }), 200

@maquinas_bp.route('/add-maquina', methods=['GET', 'POST'])
@role_required('admin')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"]) 
def add_maquina_page():
    error = None

    if request.method == 'POST':
        nombre = (request.form.get('nombre') or '').strip()
        dificultad_form = (request.form.get('dificultad') or '').strip()
        autor = (request.form.get('autor') or '').strip()
        enlace_autor = (request.form.get('enlace_autor') or '').strip()
        fecha_raw = (request.form.get('fecha') or '').strip()
        descripcion = (request.form.get('descripcion') or '').strip()
        link_descarga = (request.form.get('link_descarga') or '').strip()
        imagen = (request.form.get('imagen') or '').strip()
        destino = (request.form.get('destino') or 'docker').strip().lower()

        file = request.files.get('imagen')
        if file and file.filename:
            file.seek(0, os.SEEK_END)
            size = file.tell()
            file.seek(0)
            MAX_IMAGE_SIZE = 2 * 1024 * 1024
            if size > MAX_IMAGE_SIZE:
                error = "La imagen excede el tamaño máximo permitido de 2MB."
            elif not file.mimetype.startswith('image/'):
                error = "El archivo subido no es una imagen válida."
            else:
                # Validate content
                valid, err_msg = validators.validate_image_content(file.stream)
                if not valid:
                    error = f"Contenido de imagen inválido: {err_msg}"
                else:
                    original = secure_filename(file.filename)
                _, ext = os.path.splitext(original)
                ext = ext.lower()
                if ext in ALLOWED_PROFILE_EXTENSIONS:
                    nombre_seguro = secure_filename(nombre) if nombre else secure_filename(original)
                    final_filename = f"{nombre_seguro}{ext}"
                    
                    if destino == 'bunker':
                        upload_folder = os.path.join(BASE_DIR, 'static', 'images', 'logos-bunkerlabs')
                        db_path_prefix = "logos-bunkerlabs"
                    else:
                        upload_folder = LOGO_UPLOAD_FOLDER
                        db_path_prefix = "logos"

                    os.makedirs(upload_folder, exist_ok=True)
                    save_path = os.path.join(upload_folder, final_filename)
                    file.save(save_path)
                    imagen = f"{db_path_prefix}/{final_filename}"
                else:
                    error = "Extensión de imagen no permitida."
        else:
            if not imagen:
                if destino == 'bunker':
                     imagen = "logos/logo.png" # Fallback to main logo if needed
                else:
                     imagen = "logos/logo.png"

        if not all([nombre, dificultad_form, autor, enlace_autor, fecha_raw, descripcion, link_descarga]):
            error = "Faltan campos obligatorios."
        else:

            try:
                fecha = datetime.strptime(fecha_raw, "%Y-%m-%d").strftime("%d/%m/%Y")
            except ValueError:
                error = "Formato de fecha inválido."

        if error is None:
            color_dificultad = {
                "muy facil": "#43959b",
                "muy fácil": "#43959b",
                "facil": "#8bc34a",
                "fácil": "#8bc34a",
                "medio": "#e0a553",
                "dificil": "#d83c31",
                "difícil": "#d83c31"
            }

            dificultad_lower = dificultad_form.strip().lower()

            if "muy" in dificultad_lower:
                clase = "muy-facil"
                dificultad_texto = "Muy Fácil"
            elif "facil" in dificultad_lower or "fácil" in dificultad_lower:
                clase = "facil"
                dificultad_texto = "Fácil"
            elif "medio" in dificultad_lower:
                clase = "medio"
                dificultad_texto = "Medio"
            else:
                clase = "dificil"
                dificultad_texto = "Difícil"

            color = color_dificultad.get(dificultad_lower, "#43959b")

            if destino == 'bunker':
                db = get_bunker_db()
                pin = (request.form.get('pin') or '').strip()
                
                try:
                    db.execute(
                        """
                        INSERT INTO maquinas
                        (nombre, dificultad, clase, color, autor, enlace_autor,
                         fecha, imagen, descripcion, link_descarga, pin)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            nombre,
                            dificultad_texto,
                            clase,
                            color,
                            autor,
                            enlace_autor,
                            fecha,
                            imagen,
                            descripcion,
                            link_descarga,
                            pin
                        )
                    )
                    db.commit()
                except sqlite3.IntegrityError:
                    error = "Ya existe una máquina con ese nombre."

            else:
                db = get_db()
                try:
                    db.execute(
                        """
                        INSERT INTO maquinas
                        (nombre, dificultad, clase, color, autor, enlace_autor,
                         fecha, imagen, descripcion, link_descarga)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            nombre,
                            dificultad_texto,
                            clase,
                            color,
                            autor,
                            enlace_autor,
                            fecha,
                            imagen,
                            descripcion,
                            link_descarga
                        )
                    )
                    db.commit()
                    recalcular_ranking_creadores()
                except sqlite3.IntegrityError:
                    error = "Ya existe una máquina con ese nombre."

        if error is None:
            if destino == 'bunker':
                return redirect(url_for('bunkerlabs.bunkerlabs_home'))
            else:
                return redirect(url_for('index'))

    return render_template('add-maquina.html', error=error)
