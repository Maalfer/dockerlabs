from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session, flash
import re
import urllib.parse
import json
from datetime import datetime
from .database import get_db
from .decorators import role_required, csrf_protect
from bunkerlabs.extensions import limiter
from . import validators

writeups_bp = Blueprint('writeups', __name__)

def recalcular_ranking_writeups():
    db = get_db()

    puntos_por_dificultad = {
        "muy fácil": 1,
        "muy facil": 1,
        "fácil": 2,
        "facil": 2,
        "medio": 3,
        "difícil": 4,
        "dificil": 4,
    }

    rows = db.execute(
        """
        SELECT ws.autor AS autor, m.dificultad AS dificultad
        FROM writeups_subidos ws
        JOIN maquinas m ON ws.maquina = m.nombre
        """
    ).fetchall()

    ranking = {}

    for row in rows:
        autor = (row["autor"] or "").strip()
        dificultad = (row["dificultad"] or "").strip().lower()

        if not autor:
            continue

        puntos = puntos_por_dificultad.get(dificultad, 1)
        ranking[autor] = ranking.get(autor, 0) + puntos

    db.execute("DELETE FROM ranking_writeups")

    for autor, puntos in ranking.items():
        db.execute(
            """
            INSERT INTO ranking_writeups (nombre, puntos)
            VALUES (?, ?)
            """,
            (autor, puntos),
        )

    db.commit()


@writeups_bp.route('/subirwriteups', methods=['POST'])
@csrf_protect
@limiter.limit("10 per minute", methods=["POST"])
def subir_writeups():
    MAX_FIELD_LEN = 300
    MAX_URL_LEN = 1000
    ALLOWED_TIPOS = {"video", "texto"}

    def is_valid_text_field(s, max_len=MAX_FIELD_LEN):
        if not isinstance(s, str):
            return False
        s = s.strip()
        if len(s) == 0 or len(s) > max_len:
            return False
        if re.search(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', s):
            return False
        return True

    def is_safe_url(u):
        if not isinstance(u, str):
            return False
        u = u.strip()
        if len(u) == 0 or len(u) > MAX_URL_LEN:
            return False
        try:
            p = urllib.parse.urlparse(u)
        except:
            return False
        if p.scheme not in ("http", "https"):
            return False
        if not p.netloc:
            return False
        if re.search(r'[\r\n]', u):
            return False
        return True

    def is_valid_tipo(t):
        return isinstance(t, str) and t.strip().lower() in ALLOWED_TIPOS

    data = request.json

    if not all(k in data for k in ("maquina", "autor", "url", "tipo")):
        return jsonify({"error": "Faltan datos"}), 400

    maquina = data.get("maquina", "").strip()
    autor = data.get("autor", "").strip()
    url = data.get("url", "").strip()
    tipo = data.get("tipo", "").strip().lower()

    valid, error = validators.validate_machine_name(maquina)
    if not valid:
        return jsonify({"error": f"Campo 'maquina' inválido: {error}"}), 400

    valid, error = validators.validate_author_name(autor)
    if not valid:
        return jsonify({"error": f"Campo 'autor' inválido: {error}"}), 400

    valid, error = validators.validate_url(url)
    if not valid:
        return jsonify({"error": f"URL inválida: {error}"}), 400

    valid, error = validators.validate_writeup_type(tipo)
    if not valid:
        return jsonify({"error": f"Tipo inválido: {error}"}), 400

    tipo = "video" if tipo == "video" else "texto"

    db = get_db()
    exists = db.execute("SELECT 1 FROM maquinas WHERE nombre = ?", (maquina,)).fetchone()
    if not exists:
        return jsonify({"error": "La máquina especificada no existe"}), 400

    try:
        db = get_db()
        db.execute(
            """
            INSERT INTO writeups_recibidos (maquina, autor, url, tipo)
            VALUES (?, ?, ?, ?)
            """,
            (maquina, autor, url, tipo),
        )
        db.commit()

    except Exception as e:
        return jsonify({"error": f"Error al guardar en la base de datos: {str(e)}"}), 500

    return jsonify({"message": "Writeup enviado correctamente"}), 200


@writeups_bp.route('/writeup-edit-requests/<int:request_id>/approve', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def approve_writeup_edit(request_id):
    def is_safe_url(target):
        host_url = request.host_url
        ref = urllib.parse.urljoin(host_url, target)
        return urllib.parse.urlparse(ref).netloc == urllib.parse.urlparse(host_url).netloc

    ref = request.referrer
    if not ref or not is_safe_url(ref):
        safe_redirect = url_for('peticiones')
    else:
        safe_redirect = ref

    db = get_db()
    req = db.execute(
        "SELECT * FROM writeup_edit_requests WHERE id = ?",
        (request_id,)
    ).fetchone()

    if req is None:
        return redirect(safe_redirect)

    if req['estado'] != 'pendiente':
        return redirect(safe_redirect)

    db.execute(
        """
        UPDATE writeups_subidos
           SET maquina = ?, autor = ?, url = ?, tipo = ?
         WHERE id = ?
        """,
        (
            req['maquina_nueva'],
            req['autor_nuevo'],
            req['url_nueva'],
            req['tipo_nuevo'],
            req['writeup_id'],
        )
    )

    db.execute(
        "UPDATE writeup_edit_requests SET estado = 'aprobada' WHERE id = ?",
        (request_id,)
    )

    db.commit()
    recalcular_ranking_writeups()

    return redirect(safe_redirect)


@writeups_bp.route('/writeup-edit-requests/<int:request_id>/reject', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def reject_writeup_edit(request_id):
    db = get_db()
    db.execute(
        "UPDATE writeup_edit_requests SET estado = 'rechazada' WHERE id = ?",
        (request_id,)
    )
    db.commit()
    return redirect(request.referrer or url_for('peticiones'))


@writeups_bp.route('/writeup-edit-requests/<int:request_id>/revert', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
def revert_writeup_edit(request_id):
    db = get_db()
    db.execute("UPDATE writeup_edit_requests SET estado = 'pendiente' WHERE id = ?", (request_id,))
    db.commit()
    return redirect(url_for('peticiones'))


@writeups_bp.route('/api/writeups_recibidos/<int:writeup_id>/aprobar', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("20 per minute", methods=["POST"])
def api_aprobar_writeup_recibido(writeup_id):
    try:
        db = get_db()

        row = db.execute(
            """
            SELECT maquina, autor, url, tipo
            FROM writeups_recibidos
            WHERE id = ?
            """,
            (writeup_id,)
        ).fetchone()

        if row is None:
            return jsonify({"error": "Writeup no encontrado"}), 404

        autor_real = row["autor"]
        nuevo = db.execute("SELECT username FROM users WHERE username = ?", (autor_real,)).fetchone()

        if not nuevo:
            usuario = db.execute(
                "SELECT username FROM users WHERE id = (SELECT id FROM users WHERE LOWER(username)=LOWER(?))",
                (autor_real,)
            ).fetchone()
            if usuario:
                autor_real = usuario["username"]

        db.execute(
            """
            INSERT OR IGNORE INTO writeups_subidos (maquina, autor, url, tipo)
            VALUES (?, ?, ?, ?)
            """,
            (row["maquina"], autor_real, row["url"], row["tipo"])
        )

        db.execute(
            "DELETE FROM writeups_recibidos WHERE id = ?",
            (writeup_id,)
        )

        db.commit()

        recalcular_ranking_writeups()

        return jsonify({"message": "Writeup aprobado y movido a publicados."}), 200

    except Exception as e:
        return jsonify({"error": f"Error al aprobar el writeup: {str(e)}"}), 500


@writeups_bp.route('/writeup/<int:writeup_id>/edit', methods=['POST'])
@csrf_protect
def edit_writeup(writeup_id):
    db = get_db()
    cursor = db.cursor()
    user_id = session.get('user_id')
    user_role = session.get('role')

    new_title = request.form.get('title', '').strip()
    new_content = request.form.get('content', '').strip()

    if not user_id:
        flash('Debe iniciar sesión', 'danger')
        return redirect(url_for('login'))

    if user_role in ('admin', 'moderador', 'moderator'):
        cursor.execute("UPDATE writeups SET title = ?, content = ?, updated_at = ? WHERE id = ?",
                       (new_title, new_content, datetime.utcnow().isoformat(), writeup_id))
        db.commit()
        flash('Writeup actualizado correctamente', 'success')
        return redirect(url_for('writeups_publicados'))

    cursor.execute("SELECT id, status FROM writeup_edit_requests WHERE writeup_id = ? AND user_id = ? AND status = 'pending'",
                   (writeup_id, user_id))
    existing = cursor.fetchone()
    if existing:
        flash('Ya tienes una solicitud pendiente para este writeup', 'warning')
        return redirect(url_for('writeups_publicados'))

    cursor.execute(
        "INSERT INTO writeup_edit_requests (writeup_id, user_id, new_title, new_content, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)",
        (writeup_id, user_id, new_title, new_content, datetime.utcnow().isoformat())
    )
    db.commit()
    flash('Tu edición ha sido enviada para revisión', 'info')
    return redirect(url_for('writeups_publicados'))


@writeups_bp.route('/peticiones-writeups/<int:req_id>/aprobar', methods=['POST'])
@role_required('admin', 'moderador')
def aprobar_cambio_writeup(req_id):
    db = get_db()

    req = db.execute("""
        SELECT * FROM writeup_edit_requests WHERE id = ?
    """, (req_id,)).fetchone()

    if not req:
        return "No encontrado", 404

    # Aplicar el cambio
    db.execute("""
        UPDATE writeups_subidos
        SET maquina = ?, autor = ?, url = ?, tipo = ?
        WHERE id = ?
    """, (
        req["maquina_nueva"],
        req["autor_nuevo"],
        req["url_nueva"],
        req["tipo_nuevo"],
        req["writeup_id"]
    ))

    # Eliminar la petición
    db.execute("DELETE FROM writeup_edit_requests WHERE id = ?", (req_id,))
    db.commit()

    return redirect(url_for("peticiones_writeups"))


@writeups_bp.route('/peticiones-writeups/<int:req_id>/rechazar', methods=['POST'])
@role_required('admin', 'moderador')
def rechazar_cambio_writeup(req_id):
    db = get_db()
    db.execute("DELETE FROM writeup_edit_requests WHERE id = ?", (req_id,))
    db.commit()
    return redirect(url_for("peticiones_writeups"))


@writeups_bp.route('/api/writeups_subidos/<int:writeup_id>', methods=['PUT'])
@role_required('admin', 'moderador', 'jugador')
@csrf_protect
@limiter.limit("20 per minute", methods=["PUT"]) 
def api_update_writeup_subido(writeup_id):
    data = request.json or {}
    if not all(k in data for k in ("url", "tipo")):
        return jsonify({"error": "Faltan datos"}), 400

    url = data["url"].strip()
    tipo = data["tipo"].strip()

    valid, error = validators.validate_url(url)
    if not valid:
        return jsonify({"error": f"URL inválida: {error}"}), 400

    valid, error = validators.validate_writeup_type(tipo)
    if not valid:
        return jsonify({"error": f"Tipo inválido: {error}"}), 400

    db = get_db()
    role = session.get('role') # Using session directly as get_current_role is in decorators but session is available
    username = (session.get('username') or '').strip()
    user_id = session.get('user_id')

    writeup = db.execute(
        """
        SELECT id, maquina, autor, url, tipo
        FROM writeups_subidos
        WHERE id = ?
        """,
        (writeup_id,)
    ).fetchone()

    if writeup is None:
        return jsonify({"error": "Writeup no encontrado"}), 404

    maquina_db = (writeup["maquina"] or "").strip()
    autor_db = (writeup["autor"] or "").strip()

    if role in ('admin', 'moderador'):
        try:
            cur = db.execute(
                """
                UPDATE writeups_subidos
                   SET maquina = ?, autor = ?, url = ?, tipo = ?
                 WHERE id = ?
                """,
                (maquina_db, autor_db, url, tipo, writeup_id)
            )
            if cur.rowcount == 0:
                return jsonify({"error": "Writeup no encontrado"}), 404

            db.commit()
            recalcular_ranking_writeups()
            return jsonify({"message": "Writeup actualizado correctamente"}), 200
        except Exception as e:
            return jsonify({"error": f"Error al actualizar en la base de datos: {str(e)}"}), 500

    if not username:
        return jsonify({"error": "Debes iniciar sesión."}), 403

    if username.lower() != autor_db.lower():
        return jsonify({"error": "No tienes permiso para modificar este writeup."}), 403

    try:
        db.execute(
            """
            INSERT INTO writeup_edit_requests (
                writeup_id, user_id, username,
                maquina_original, autor_original, url_original, tipo_original,
                maquina_nueva, autor_nuevo, url_nueva, tipo_nuevo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                writeup["id"], user_id, username,
                maquina_db, autor_db, writeup["url"], writeup["tipo"],
                maquina_db, autor_db, url, tipo,
            )
        )
        db.commit()
        return jsonify({"message": "Tu petición de cambio ha sido enviada para revisión."}), 200
    except Exception as e:
        return jsonify({"error": f"Error al crear la petición de cambio: {str(e)}"}), 500


@writeups_bp.route('/api/writeups_subidos/<int:writeup_id>', methods=['DELETE'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("20 per minute", methods=["DELETE"]) 
def api_delete_writeup_subido(writeup_id):
    try:
        db = get_db()
        cur = db.execute(
            "DELETE FROM writeups_subidos WHERE id = ?",
            (writeup_id,),
        )
        db.commit()

        if cur.rowcount == 0:
            return jsonify({"error": "Writeup no encontrado"}), 404

        recalcular_ranking_writeups()

        return jsonify({"message": "Writeup eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": f"Error al eliminar en la base de datos: {str(e)}"}), 500


@writeups_bp.route('/api/writeups/<maquina_nombre>', methods=['GET'])
@limiter.limit("60 per minute", methods=["GET"]) 
def api_writeups_maquina(maquina_nombre):
    db = get_db()
    rows = db.execute(
        """
        SELECT ws.autor,
                ws.url,
                ws.tipo,
                CASE WHEN u.id IS NOT NULL THEN 1 ELSE 0 END AS es_usuario_registrado
        FROM writeups_subidos AS ws
        LEFT JOIN users AS u
            ON LOWER(u.username) = LOWER(ws.autor)
        WHERE ws.maquina = ?
        ORDER BY ws.created_at DESC, ws.id DESC
        """,
        (maquina_nombre,)
    ).fetchall()

    writeups = []
    for row in rows:
        tipo_raw = (row["tipo"] or "").strip().lower()
        tipo_emoji = "\U0001F3A5" if tipo_raw == "video" else "\U0001F4DD"
        writeups.append({
            "name": row["autor"],
            "url": row["url"],
            "type": tipo_emoji,
            "es_usuario_registrado": bool(row["es_usuario_registrado"]),
        })

    return jsonify(writeups), 200
