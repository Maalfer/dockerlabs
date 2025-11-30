import os
import json
import re
import secrets
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, g, flash
from flask_httpauth import HTTPBasicAuth
from flask import send_from_directory
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from werkzeug.utils import secure_filename
from flask_limiter.errors import RateLimitExceeded

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

PROFILE_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'images', 'perfiles')
MACHINE_LOGOS_FOLDER = os.path.join(BASE_DIR, 'static', 'images', 'logos')
ALLOWED_PROFILE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_LOGO_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
LOGO_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'images', 'logos')


app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'), template_folder=os.path.join(BASE_DIR, 'templates'))
auth = HTTPBasicAuth()

app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SECRET_KEY'] = "PAAS" # Esta no es la que está en producción claramente

from bunkerlabs.extensions import limiter
limiter.init_app(app)

@app.after_request
def apply_security_headers(response):
    nonce = g.get('csp_nonce')
    
    if nonce:
        response.headers['Content-Security-Policy'] = (
            f"default-src 'self'; "
            f"style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net; "
            f"img-src 'self' data: blob:; "
            f"font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            f"frame-src 'self' https://www.youtube.com; "
            f"frame-ancestors 'self'; "
        )

    response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains; preload'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    return response


@app.errorhandler(RateLimitExceeded)
def handle_rate_limit(e):
    """
    Guardamos en session el tiempo restante (segundos) para mostrarlo en la plantilla.
    Flask-Limiter normalmente coloca el header 'Retry-After' con segundos.
    """
    retry_after = None
    try:
        import re
        m = re.search(r"(\d+)", str(e.description or ""))
        if m:
            retry_after = int(m.group(1))
    except Exception:
        retry_after = None

    if not retry_after:
        retry_after = 15

    session['rate_limit_remaining'] = retry_after

    return redirect(request.path)



app.config['DATABASE'] = os.path.join(BASE_DIR, 'dockerlabs.db')
app.config['BUNKER_DATABASE'] = os.path.join(BASE_DIR, 'bunkerlabs.db')


from .database import get_db, get_bunker_db, init_db, init_bunker_db, close_db
from . import validators

@app.teardown_appcontext
def teardown_db(exception):
    close_db(exception)



with app.app_context():
    init_db()
    init_bunker_db()


@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    g.user = None
    if user_id is not None:
        db = get_db()
        g.user = db.execute(
            "SELECT id, username, email, role, biography, linkedin_url, github_url, youtube_url FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        if g.user is None:
            session.clear()


from .decorators import get_current_role, generate_csrf_token, csrf_protect, role_required, generate_token, verify_token
from .auth import auth_bp, get_profile_image_static_path, load_username_change_requests
from .maquinas import maquinas_bp, recalcular_ranking_creadores
from .api import api_bp

import bunkerlabs.decorators as decorators
decorators.get_current_role = get_current_role

# Registrar el blueprint de autenticación
app.register_blueprint(auth_bp)
app.register_blueprint(maquinas_bp)
app.register_blueprint(api_bp)

@app.context_processor
def inject_globals():
    return {
        'current_user_role': get_current_role(),
        'csrf_token': generate_csrf_token()
    }

def obtener_dificultades():
    db = get_db()
    dificultades = {}

    cur = db.execute("SELECT nombre, dificultad FROM maquinas")
    rows = cur.fetchall()

    for row in rows:
        nombre = row["nombre"]
        dificultad = row["dificultad"]
        if nombre and dificultad:
            dificultades[nombre] = dificultad.lower()

    return dificultades



@app.route('/terminos-condiciones')
def terminos_condiciones():
    return render_template('terminos-condiciones.html')

@app.route('/bug-bounty')
def bug_bounty():
    return render_template('bug_bounty.html')


@app.route('/dashboard')
@role_required('admin', 'moderador', 'jugador')
def dashboard():
    db = get_db()
    maquinas = db.execute(
        "SELECT id, nombre, autor FROM maquinas ORDER BY nombre ASC"
    ).fetchall()

    username = session.get('username')
    static_path = get_profile_image_static_path(username)

    if static_path is None:
        static_path = 'images/perfiles/balulero.png'

    profile_image_url = url_for('static', filename=static_path)

    return render_template(
        'dashboard.html',
        maquinas=maquinas,
        profile_image_url=profile_image_url,
        user=g.user
    )


@app.route('/reclamar-maquina', methods=['POST'])
@role_required('jugador')
@csrf_protect
@limiter.limit("5 per hour")
def reclamar_maquina():
    maquina_nombre = (request.form.get('maquina_nombre') or '').strip()
    contacto = (request.form.get('contacto') or '').strip()
    prueba = (request.form.get('prueba') or '').strip()
    
    if not maquina_nombre or not contacto or not prueba:
        return redirect(url_for('dashboard'))

    # Validar nombre de máquina
    valid, _ = validators.validate_machine_name(maquina_nombre)
    if not valid:
        # En este caso redirigimos al dashboard, idealmente mostraríamos un error flash
        return redirect(url_for('dashboard'))
    db = get_db()
    user_id = session.get('user_id')
    username = (session.get('username') or '').strip()
    db.execute(
        """
        INSERT INTO maquina_claims (user_id, username, maquina_nombre, contacto, prueba, estado)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, username, maquina_nombre, contacto, prueba, 'pendiente')
    )
    db.commit()
    return redirect(url_for('dashboard'))


@app.route('/peticiones')
@role_required('admin', 'moderador')
@limiter.limit("20 per minute")
def peticiones():
    db = get_db()

    claims = db.execute(
        """
        SELECT id, username, maquina_nombre, contacto, prueba, estado, created_at
        FROM maquina_claims
        ORDER BY created_at DESC, id DESC
        """
    ).fetchall()

    envios_maquinas = []

    peticiones_nombres = db.execute(
        """
        SELECT id,
               username,
               email,
               nombre_solicitado,
               nombre_actual,
               motivo,
               estado,
               created_at
        FROM nombre_claims
        ORDER BY created_at DESC, id DESC
        """
    ).fetchall()

    edit_requests = db.execute(
        """
        SELECT
            r.*,
            ws.maquina AS maquina_actual,
            ws.autor   AS autor_actual,
            ws.url     AS url_actual,
            ws.tipo    AS tipo_actual
        FROM writeup_edit_requests r
        LEFT JOIN writeups_subidos ws
               ON ws.id = r.writeup_id
        ORDER BY r.created_at DESC, r.id DESC
        """
    ).fetchall()

    machine_edit_requests = db.execute(
        """
        SELECT *
        FROM machine_edit_requests
        ORDER BY fecha DESC, id DESC
        """
    ).fetchall()

    machine_edit_requests_parsed = []
    for r in machine_edit_requests:
        try:
            nuevos = json.loads(r['nuevos_datos'])
        except:
            nuevos = {}
        machine_edit_requests_parsed.append({
            "id": r["id"],
            "machine_id": r["machine_id"],
            "origen": r["origen"],
            "autor": r["autor"],
            "estado": r["estado"],
            "fecha": r["fecha"],
            "nuevos": nuevos
        })

    username_change_requests = load_username_change_requests()

    return render_template(
        'peticiones.html',
        claims=claims,
        envios_maquinas=envios_maquinas,
        peticiones_nombres=peticiones_nombres,
        edit_requests=edit_requests,
        machine_edit_requests=machine_edit_requests_parsed,
        username_change_requests=username_change_requests
    )

from urllib.parse import urlparse, urljoin

@app.route('/nombre-claims/<int:claim_id>/approve', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def approve_nombre_claim(claim_id):
    def is_safe_url(target):
        host_url = request.host_url
        ref = urljoin(host_url, target)
        return urlparse(ref).netloc == urlparse(host_url).netloc

    ref = request.referrer
    if not ref or not is_safe_url(ref):
        safe_redirect = url_for('peticiones')
    else:
        safe_redirect = ref

    db = get_db()
    claim = db.execute(
        "SELECT * FROM nombre_claims WHERE id = ?",
        (claim_id,)
    ).fetchone()

    if claim is None:
        return redirect(safe_redirect)

    existing = db.execute(
        "SELECT id FROM users WHERE username = ? OR email = ?",
        (claim['nombre_solicitado'], claim['email'])
    ).fetchone()

    if existing:
        db.execute(
            "UPDATE nombre_claims SET estado = 'rechazada' WHERE id = ?",
            (claim_id,)
        )
        db.commit()
        return redirect(safe_redirect)

    try:
        db.execute(
            """
            INSERT INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            (
                claim['nombre_solicitado'],
                claim['email'],
                claim['password_hash'],
                'jugador'
            )
        )
        db.execute(
            "UPDATE nombre_claims SET estado = 'aprobada' WHERE id = ?",
            (claim_id,)
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.execute(
            "UPDATE nombre_claims SET estado = 'rechazada' WHERE id = ?",
            (claim_id,)
        )
        db.commit()

    return redirect(safe_redirect)






@app.route('/machine-edit-requests/<int:request_id>/approve', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def approve_machine_edit(request_id):
    db = get_db()
    req = db.execute(
        "SELECT * FROM machine_edit_requests WHERE id = ?",
        (request_id,)
    ).fetchone()

    if req is None:
        return redirect(url_for('peticiones'))

    try:
        nuevos = json.loads(req['nuevos_datos'])
    except:
        nuevos = {}

    origen = req['origen']
    machine_id = req['machine_id']

    if origen == 'docker':
        target_db = get_db()
    else:
        target_db = get_bunker_db()

    target_db.execute(
        """
        UPDATE maquinas
        SET nombre = ?, dificultad = ?, clase = ?, color = ?, autor = ?, enlace_autor = ?,
            fecha = ?, imagen = ?, descripcion = ?, link_descarga = ?
        WHERE id = ?
        """,
        (
            nuevos.get("nombre"),
            nuevos.get("dificultad"),
            nuevos.get("clase"),
            nuevos.get("color"),
            nuevos.get("autor"),
            nuevos.get("enlace_autor"),
            nuevos.get("fecha"),
            nuevos.get("imagen"),
            nuevos.get("descripcion"),
            nuevos.get("link_descarga"),
            machine_id
        )
    )
    target_db.commit()

    if origen == 'docker':
        recalcular_ranking_creadores()

    db.execute(
        "UPDATE machine_edit_requests SET estado = 'aprobada' WHERE id = ?",
        (request_id,)
    )
    db.commit()

    return redirect(url_for('peticiones'))


@app.route('/machine-edit-requests/<int:request_id>/reject', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def reject_machine_edit(request_id):
    db = get_db()
    db.execute(
        "UPDATE machine_edit_requests SET estado = 'rechazada' WHERE id = ?",
        (request_id,)
    )
    db.commit()
    return redirect(url_for('peticiones'))


@app.route('/machine-edit-requests/<int:request_id>/revert', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
def revert_machine_edit(request_id):
    db = get_db()
    db.execute("UPDATE machine_edit_requests SET estado = 'pendiente' WHERE id = ?", (request_id,))
    db.commit()
    return redirect(url_for('peticiones'))



from urllib.parse import urlparse, urljoin

@app.route('/nombre-claims/<int:claim_id>/reject', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def reject_nombre_claim(claim_id):
    def is_safe_url(target):
        host_url = request.host_url
        ref = urljoin(host_url, target)
        return urlparse(ref).netloc == urlparse(host_url).netloc

    ref = request.referrer
    if not ref or not is_safe_url(ref):
        safe_redirect = url_for('peticiones')
    else:
        safe_redirect = ref

    db = get_db()
    db.execute(
        "UPDATE nombre_claims SET estado = 'rechazada' WHERE id = ?",
        (claim_id,)
    )
    db.commit()
    return redirect(safe_redirect)


@app.route('/nombre-claims/<int:claim_id>/revert', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
def revert_nombre_claim(claim_id):
    db = get_db()
    db.execute("UPDATE nombre_claims SET estado = 'pendiente' WHERE id = ?", (claim_id,))
    db.commit()
    return redirect(url_for('peticiones'))



@app.route('/claims/<int:claim_id>/approve', methods=['POST'])
@role_required('admin')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def approve_claim(claim_id):
    db = get_db()
    claim = db.execute(
        "SELECT id, username, maquina_nombre FROM maquina_claims WHERE id = ?",
        (claim_id,)
    ).fetchone()
    if claim is None:
        return redirect(url_for('dashboard'))
    db.execute(
        "UPDATE maquinas SET autor = ? WHERE nombre = ?",
        (claim['username'], claim['maquina_nombre'])
    )
    db.execute(
        "UPDATE maquina_claims SET estado = 'aprobada' WHERE id = ?",
        (claim_id,)
    )
    db.commit()
    recalcular_ranking_creadores()
    return redirect(url_for('dashboard'))


@app.route('/claims/<int:claim_id>/reject', methods=['POST'])
@role_required('admin')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def reject_claim(claim_id):
    db = get_db()

    db.execute(
        "DELETE FROM maquina_claims WHERE id = ?",
        (claim_id,)
    )
    db.commit()

    return redirect(url_for('dashboard'))


@app.route('/claims/<int:claim_id>/revert', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
def revert_claim(claim_id):
    db = get_db()
    db.execute("UPDATE maquina_claims SET estado = 'pendiente' WHERE id = ?", (claim_id,))
    db.commit()
    return redirect(url_for('peticiones'))




@app.route('/')
def index():
    db = get_db()
    all_maquinas = db.execute(
        "SELECT * FROM maquinas ORDER BY id ASC"
    ).fetchall()
    
    # Encontrar la máquina más reciente por fecha
    most_recent = None
    most_recent_date = None
    
    for m in all_maquinas:
        fecha_str = m['fecha']  # formato dd/mm/yyyy
        parts = fecha_str.split('/')
        if len(parts) == 3:
            # Convertir a formato yyyy-mm-dd para comparación
            fecha_iso = f"{parts[2]}-{parts[1]}-{parts[0]}"
            
            if most_recent_date is None or fecha_iso > most_recent_date:
                most_recent = m
                most_recent_date = fecha_iso
    
    # Reorganizar: máquina más reciente primero, luego las demás en orden original
    if most_recent:
        # Convertir a dict para poder modificar la posición
        most_recent = dict(most_recent)
        maquinas = [most_recent] + [m for m in all_maquinas if m['id'] != most_recent['id']]
    else:
        maquinas = all_maquinas
    


    completed_machines = []
    if 'user_id' in session:
        completed_rows = db.execute(
            "SELECT machine_name FROM maquinas_hechas WHERE user_id = ?",
            (session['user_id'],)
        ).fetchall()
        completed_machines = [row['machine_name'].strip() for row in completed_rows]

    # Detect if there's only one machine (show centered)
    single_machine = len(maquinas) == 1

    # Fetch categories for machines
    categorias_map = {}
    for m in maquinas:
        cat = db.execute(
            "SELECT categoria FROM categorias WHERE machine_id = ? AND origen = 'docker'",
            (m['id'],)
        ).fetchone()
        categorias_map[m['id']] = cat['categoria'] if cat else ''

    return render_template('home.html', maquinas=maquinas, completed_machines=completed_machines, most_recent_id=most_recent['id'] if most_recent else None, single_machine=single_machine, categorias_map=categorias_map)


@app.route('/writeups-recibidos')
@role_required('admin', 'moderador')
def writeups_recibidos():
    return render_template('writeups_recibidos.html')


@app.route('/api/ranking_writeups', methods=['GET'])
@limiter.limit("60 per minute", methods=["GET"]) 
def api_ranking_writeups():
    db = get_db()
    rows = db.execute(
        """
        SELECT nombre, puntos
        FROM ranking_writeups
        ORDER BY puntos DESC, LOWER(nombre) ASC
        """
    ).fetchall()

    ranking = []
    for row in rows:
        ranking.append({
            "nombre": row["nombre"],
            "puntos": row["puntos"]
        })

    return jsonify(ranking), 200


@app.route('/api/ranking_creadores', methods=['GET'])
@limiter.limit("60 per minute", methods=["GET"]) 
def api_ranking_creadores():
    db = get_db()
    rows = db.execute(
        """
        SELECT nombre, maquinas
        FROM ranking_creadores
        ORDER BY maquinas DESC, LOWER(nombre) ASC
        """
    ).fetchall()

    ranking = []
    for row in rows:
        ranking.append({
            "nombre": row["nombre"],
            "maquinas": row["maquinas"]
        })

    return jsonify(ranking), 200

@app.route('/api/author_profile', methods=['GET'])
@limiter.limit("60 per minute", methods=["GET"]) 
def api_author_profile():
    nombre = (request.args.get('nombre') or '').strip()
    if not nombre:
        return jsonify({'error': 'Nombre requerido'}), 400

    db = get_db()

    maquinas_rows = db.execute(
        """
        SELECT nombre, dificultad, imagen
        FROM maquinas
        WHERE autor = ?
        ORDER BY fecha DESC
        """,
        (nombre,)
    ).fetchall()

    maquinas = []
    for row in maquinas_rows:
        imagen_rel = (row["imagen"] or "").strip()
        imagen_url = None
        if imagen_rel:
            imagen_url = url_for('static', filename=f'images/{imagen_rel}')

        maquinas.append({
            "nombre": row["nombre"],
            "dificultad": row["dificultad"],
            "imagen_url": imagen_url
        })

    writeups_rows = db.execute(
        """
        SELECT maquina, url, tipo
        FROM writeups_subidos
        WHERE autor = ?
        ORDER BY created_at DESC
        """,
        (nombre,)
    ).fetchall()

    writeups = []
    for row in writeups_rows:
        writeups.append({
            "maquina": row["maquina"],
            "url": row["url"],
            "tipo": row["tipo"]
        })

    profile_static_path = get_profile_image_static_path(nombre)
    if profile_static_path is None:
        profile_static_path = 'images/perfiles/pingu.png'

    profile_image_url = url_for('static', filename=profile_static_path)

    # Fetch biography and social links from users table
    user_row = db.execute(
        "SELECT biography, linkedin_url, github_url, youtube_url FROM users WHERE username = ?",
        (nombre,)
    ).fetchone()
    biography = user_row['biography'] if user_row and user_row['biography'] else None
    linkedin_url = user_row['linkedin_url'] if user_row and user_row['linkedin_url'] else None
    github_url = user_row['github_url'] if user_row and user_row['github_url'] else None
    youtube_url = user_row['youtube_url'] if user_row and user_row['youtube_url'] else None

    return jsonify({
        "nombre": nombre,
        "profile_image_url": profile_image_url,
        "maquinas": maquinas,
        "writeups": writeups,
        "biography": biography,
        "linkedin_url": linkedin_url,
        "github_url": github_url,
        "youtube_url": youtube_url
    }), 200


@app.route('/api/writeups_recibidos', methods=['GET'])
@role_required('admin', 'moderador')
@limiter.limit("60 per minute", methods=["GET"]) 
def api_list_writeups_recibidos():
    db = get_db()
    rows = db.execute(
        """
        SELECT id, maquina, autor, url, tipo, created_at
        FROM writeups_recibidos
        ORDER BY created_at DESC, id DESC
        """
    ).fetchall()

    writeups = []
    for row in rows:
        writeups.append({
            "id": row["id"],
            "maquina": row["maquina"],
            "autor": row["autor"],
            "url": row["url"],
            "tipo": row["tipo"],
            "created_at": row["created_at"],
        })

    return jsonify(writeups), 200


@app.route('/api/writeups_recibidos/<int:writeup_id>', methods=['PUT'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("20 per minute", methods=["PUT"]) 
def api_update_writeup_recibido(writeup_id):
    data = request.json or {}
    if not all(k in data for k in ("maquina", "autor", "url", "tipo")):
        return jsonify({"error": "Faltan datos"}), 400

    maquina = data["maquina"].strip()
    autor = data["autor"].strip()
    url = data["url"].strip()
    tipo = data["tipo"].strip()

    # Validaciones de entrada
    valid, error = validators.validate_machine_name(maquina)
    if not valid:
        return jsonify({"error": f"Nombre de máquina inválido: {error}"}), 400

    valid, error = validators.validate_author_name(autor)
    if not valid:
        return jsonify({"error": f"Nombre de autor inválido: {error}"}), 400

    valid, error = validators.validate_url(url)
    if not valid:
        return jsonify({"error": f"URL inválida: {error}"}), 400

    valid, error = validators.validate_writeup_type(tipo)
    if not valid:
        return jsonify({"error": f"Tipo inválido: {error}"}), 400

    try:
        db = get_db()
        cur = db.execute(
            """
            UPDATE writeups_recibidos
            SET maquina = ?, autor = ?, url = ?, tipo = ?
            WHERE id = ?
            """,
            (maquina, autor, url, tipo, writeup_id),
        )
        db.commit()

        if cur.rowcount == 0:
            return jsonify({"error": "Writeup no encontrado"}), 404

        return jsonify({"message": "Writeup actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": f"Error al actualizar en la base de datos: {str(e)}"}), 500


@app.route('/api/writeups_recibidos/<int:writeup_id>', methods=['DELETE'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("20 per minute", methods=["DELETE"]) 
def api_delete_writeup_recibido(writeup_id):
    try:
        db = get_db()
        cur = db.execute(
            "DELETE FROM writeups_recibidos WHERE id = ?",
            (writeup_id,),
        )
        db.commit()

        if cur.rowcount == 0:
            return jsonify({"error": "Writeup no encontrado"}), 404

        return jsonify({"message": "Writeup eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": f"Error al eliminar en la base de datos: {str(e)}"}), 500


@app.route('/writeups-publicados')
@role_required('admin', 'moderador', 'jugador')
def writeups_publicados():
    return render_template('writeups_publicados.html')


@app.route('/api/writeups_subidos', methods=['GET'])
@role_required('admin', 'moderador', 'jugador')
@limiter.limit("60 per minute", methods=["GET"]) 
def api_list_writeups_subidos():
    maquina = request.args.get('maquina', type=str)
    db = get_db()
    role = get_current_role()
    username = (session.get('username') or '').strip()

    if role in ['admin', 'moderador']:
        if maquina:
            rows = db.execute(
                """
                SELECT id, maquina, autor, url, tipo, created_at
                FROM writeups_subidos
                WHERE maquina = ?
                ORDER BY created_at DESC, id DESC
                """,
                (maquina,)
            ).fetchall()
        else:
            rows = db.execute(
                """
                SELECT id, maquina, autor, url, tipo, created_at
                FROM writeups_subidos
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()
    else:
        if not username:
            return jsonify([]), 200
        if maquina:
            rows = db.execute(
                """
                SELECT id, maquina, autor, url, tipo, created_at
                FROM writeups_subidos
                WHERE autor = ? AND maquina = ?
                ORDER BY created_at DESC, id DESC
                """,
                (username, maquina)
            ).fetchall()
        else:
            rows = db.execute(
                """
                SELECT id, maquina, autor, url, tipo, created_at
                FROM writeups_subidos
                WHERE autor = ?
                ORDER BY created_at DESC, id DESC
                """,
                (username,)
            ).fetchall()

    writeups = []
    for row in rows:
        writeups.append({
            "id": row["id"],
            "maquina": row["maquina"],
            "autor": row["autor"],
            "url": row["url"],
            "tipo": row["tipo"],
            "created_at": row["created_at"],
        })

    return jsonify(writeups), 200


@app.route('/api/writeups_subidos/maquinas', methods=['GET'])
@role_required('admin', 'moderador', 'jugador')
@limiter.limit("60 per minute", methods=["GET"]) 
def api_list_maquinas_writeups_subidos():
    db = get_db()
    role = get_current_role()
    username = (session.get('username') or '').strip()

    if role in ['admin', 'moderador']:
        rows = db.execute(
            """
            SELECT ws.maquina, COUNT(*) AS total, m.imagen
            FROM writeups_subidos ws
            LEFT JOIN maquinas m ON ws.maquina = m.nombre
            WHERE ws.maquina IS NOT NULL AND ws.maquina <> ''
            GROUP BY ws.maquina, m.imagen
            ORDER BY LOWER(ws.maquina)
            """
        ).fetchall()
    else:
        if not username:
            return jsonify([]), 200
        rows = db.execute(
            """
            SELECT ws.maquina, COUNT(*) AS total, m.imagen
            FROM writeups_subidos ws
            LEFT JOIN maquinas m ON ws.maquina = m.nombre
            WHERE ws.autor = ? AND ws.maquina IS NOT NULL AND ws.maquina <> ''
            GROUP BY ws.maquina, m.imagen
            ORDER BY LOWER(ws.maquina)
            """,
            (username,)
        ).fetchall()

    maquinas = []
    for row in rows:
        imagen_rel = (row["imagen"] or "").strip()
        imagen_url = None
        if imagen_rel:
            imagen_url = url_for('static', filename=f'images/{imagen_rel}')
        
        maquinas.append({
            "maquina": row["maquina"],
            "total": row["total"],
            "imagen": imagen_url,
        })

    return jsonify(maquinas), 200


@app.route('/peticiones-writeups')
@role_required('admin', 'moderador')
def peticiones_writeups():
    db = get_db()
    rows = db.execute("""
        SELECT *
        FROM writeup_edit_requests
        ORDER BY id DESC
    """).fetchall()

    return render_template("peticiones.html", peticiones=rows)



@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.route('/403.html')
def error_403_page():
    return render_template('403.html')


@app.route('/instrucciones-uso')
def instrucciones_uso():
    return render_template('instrucciones_uso.html')

@app.route('/enviar-maquina')
def enviar_maquina():
    return render_template('enviar_maquina.html')

@app.route('/como-se-crea-una-maquina')
def como_se_crea():
    return render_template('como_se_crea_una_maquina.html')

@app.route('/agradecimientos')
def agradecimientos():
    return render_template('agradecimientos.html')

@app.route('/politica-privacidad')
def politica_privacidad():
    return render_template('politicas/politica_privacidad.html')

@app.route('/politica-cookies')
def politica_cookies():
    return render_template('politicas/politica_cookies.html')

@app.route('/condiciones-uso')
def condiciones_uso():
    return render_template('politicas/condiciones_uso.html')


@app.route('/api/rate_machine', methods=['POST'])
def rate_machine():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Debes iniciar sesión para puntuar'}), 401
    
    data = request.json
    maquina_nombre = data.get('maquina_nombre')
    dificultad_score = data.get('dificultad_score')
    aprendizaje_score = data.get('aprendizaje_score')
    recomendaria_score = data.get('recomendaria_score')
    diversion_score = data.get('diversion_score')
    
    if not all([maquina_nombre, dificultad_score, aprendizaje_score, recomendaria_score, diversion_score]):
        return jsonify({'success': False, 'message': 'Faltan datos'}), 400
    
    try:
        db = get_db()
        
        # REQUIREMENT: Check if user has completed the machine before allowing rating
        completion_check = db.execute(
            "SELECT id FROM maquinas_hechas WHERE user_id = ? AND machine_name = ?",
            (session['user_id'], maquina_nombre)
        ).fetchone()
        
        if not completion_check:
            return jsonify({
                'success': False, 
                'message': 'Debes completar la máquina antes de poder puntuarla'
            }), 403
        
        # Check if user already rated this machine
        existing = db.execute(
            "SELECT id FROM puntuaciones WHERE usuario_id = ? AND maquina_nombre = ?",
            (session['user_id'], maquina_nombre)
        ).fetchone()
        
        if existing:
            db.execute(
                """UPDATE puntuaciones 
                   SET dificultad_score = ?, aprendizaje_score = ?, recomendaria_score = ?, diversion_score = ?, fecha = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (dificultad_score, aprendizaje_score, recomendaria_score, diversion_score, existing['id'])
            )
        else:
            db.execute(
                """INSERT INTO puntuaciones (usuario_id, maquina_nombre, dificultad_score, aprendizaje_score, recomendaria_score, diversion_score)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (session['user_id'], maquina_nombre, dificultad_score, aprendizaje_score, recomendaria_score, diversion_score)
            )
        db.commit()
        return jsonify({'success': True, 'message': 'Puntuación guardada correctamente'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/get_machine_rating/<maquina_nombre>')
def get_machine_rating(maquina_nombre):
    db = get_db()
    
    # Get average rating
    avg_result = db.execute(
        """SELECT 
            AVG(dificultad_score) as avg_dificultad,
            AVG(aprendizaje_score) as avg_aprendizaje,
            AVG(recomendaria_score) as avg_recomendaria,
            AVG(diversion_score) as avg_diversion,
            COUNT(*) as count
           FROM puntuaciones WHERE maquina_nombre = ?""",
        (maquina_nombre,)
    ).fetchone()
    
    user_rating = None
    if 'user_id' in session:
        user_result = db.execute(
            "SELECT * FROM puntuaciones WHERE usuario_id = ? AND maquina_nombre = ?",
            (session['user_id'], maquina_nombre)
        ).fetchone()
        if user_result:
            user_rating = {
                'dificultad': user_result['dificultad_score'],
                'aprendizaje': user_result['aprendizaje_score'],
                'recomendaria': user_result['recomendaria_score'],
                'diversion': user_result['diversion_score']
            }
    
    # Calculate total average
    total_avg = 0
    if avg_result and avg_result['count'] > 0:
        # Calculate average of the 4 criteria
        # This approach: average of (each user's average of 4 criteria)
        # More intuitive: sum all 4 averages and divide by 4
        criteria_sum = (avg_result['avg_dificultad'] or 0) + \
                       (avg_result['avg_aprendizaje'] or 0) + \
                       (avg_result['avg_recomendaria'] or 0) + \
                       (avg_result['avg_diversion'] or 0)
        total_avg = criteria_sum / 4
    
    return jsonify({
        'average': round(total_avg, 1),
        'count': avg_result['count'] if avg_result else 0,
        'details': {
            'dificultad': round(avg_result['avg_dificultad'] or 0, 1) if avg_result else 0,
            'aprendizaje': round(avg_result['avg_aprendizaje'] or 0, 1) if avg_result else 0,
            'recomendaria': round(avg_result['avg_recomendaria'] or 0, 1) if avg_result else 0,
            'diversion': round(avg_result['avg_diversion'] or 0, 1) if avg_result else 0
        },
        'user_rating': user_rating
    })


@app.route('/api/completed_machines/<machine_name>', methods=['GET'])
@role_required('admin', 'moderador', 'jugador')
@limiter.limit("60 per minute")
def check_completed_machine(machine_name):
    """Check if current user has completed a specific machine"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    db = get_db()
    completed = db.execute(
        "SELECT id FROM maquinas_hechas WHERE user_id = ? AND machine_name = ?",
        (user_id, machine_name)
    ).fetchone()
    
    return jsonify({'completed': completed is not None}), 200


@app.route('/api/toggle_completed_machine', methods=['POST'])
@role_required('admin', 'moderador', 'jugador')
@csrf_protect
@limiter.limit("30 per minute", methods=["POST"])
def api_toggle_completed_machine():
    """Toggle completion status for a machine"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated', 'success': False}), 401
    
    data = request.json or {}
    machine_name = (data.get('machine_name') or '').strip()
    
    if not machine_name:
        return jsonify({'error': 'Machine name required', 'success': False}), 400
    
    db = get_db()

    # Validate that the machine exists
    machine_exists = db.execute(
        "SELECT id FROM maquinas WHERE nombre = ?",
        (machine_name,)
    ).fetchone()

    if not machine_exists:
        return jsonify({'error': 'Máquina no válida', 'success': False}), 400
    
    # Check if already completed
    existing = db.execute(
        "SELECT id FROM maquinas_hechas WHERE user_id = ? AND machine_name = ?",
        (user_id, machine_name)
    ).fetchone()
    
    if existing:
        # Remove completion
        db.execute(
            "DELETE FROM maquinas_hechas WHERE user_id = ? AND machine_name = ?",
            (user_id, machine_name)
        )
        db.commit()
        return jsonify({'success': True, 'completed': False}), 200
    else:
        # Add completion
        db.execute(
            "INSERT INTO maquinas_hechas (user_id, machine_name) VALUES (?, ?)",
            (user_id, machine_name)
        )
        db.commit()
        return jsonify({'success': True, 'completed': True}), 200


@app.route('/maquinas-hechas')
@role_required('admin', 'moderador', 'jugador')
def maquinas_hechas():
    """Render completed machines page"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    
    # Get all completed machines for the user with machine details
    completed_machines = db.execute(
        """
        SELECT 
            mh.machine_name,
            mh.completed_at,
            m.dificultad,
            m.color,
            m.imagen,
            m.clase,
            m.autor
        FROM maquinas_hechas mh
        LEFT JOIN maquinas m ON mh.machine_name = m.nombre
        WHERE mh.user_id = ?
        ORDER BY mh.completed_at DESC
        """,
        (user_id,)
    ).fetchall()
    
    # Get total number of machines in the system
    total_machines = db.execute("SELECT COUNT(*) as count FROM maquinas").fetchone()['count']
    
    # Calculate completion percentage
    completed_count = len(completed_machines)
    completion_percentage = round((completed_count / total_machines * 100), 1) if total_machines > 0 else 0
    
    return render_template(
        'maquinas_hechas.html', 
        completed_machines=completed_machines,
        total_machines=total_machines,
        completed_count=completed_count,
        completion_percentage=completion_percentage
    )



from bunkerlabs import bunkerlabs_bp
app.register_blueprint(bunkerlabs_bp)

from .writeups import writeups_bp
app.register_blueprint(writeups_bp)




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False) # Cambiar a False en producción
