from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session, flash
import re
import urllib.parse
import json
from datetime import datetime
from .auth import get_profile_image_static_path
from .decorators import role_required, csrf_protect, get_current_role
from bunkerlabs.extensions import limiter
from . import validators
from .models import User, Machine, Writeup, PendingWriteup, WriteupRanking, WriteupReport, WriteupEditRequest
from .extensions import db as alchemy_db
from sqlalchemy import func, or_

writeups_bp = Blueprint('writeups', __name__)

def recalcular_ranking_writeups():
    puntos_por_dificultad = {
        "muy fácil": 1, "muy facil": 1,
        "fácil": 2, "facil": 2,
        "medio": 3,
        "difícil": 4, "dificil": 4,
    }

    results = alchemy_db.session.query(Writeup.autor, Machine.dificultad)        .join(Machine, Writeup.maquina == Machine.nombre).all()
    
    ranking = {}
    for autor, dificultad in results:
        if not autor: continue
        dificultad_lower = (dificultad or "").strip().lower()
        puntos = puntos_por_dificultad.get(dificultad_lower, 1)
        ranking[autor] = ranking.get(autor, 0) + puntos

    WriteupRanking.query.delete()           

    for autor, puntos in ranking.items():
        entry = WriteupRanking(nombre=autor, puntos=puntos)
        alchemy_db.session.add(entry)
    
    alchemy_db.session.commit()

@writeups_bp.route('/subirwriteups', methods=['POST'])
@role_required('admin', 'moderador', 'jugador')
@csrf_protect
@limiter.limit("10 per minute", methods=["POST"])
def subir_writeups():
    """
    Submit a writeup.
    ---
    tags:
      - Writeups
    responses:
      200:
        description: Writeup submitted.
    """
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

    if not all(k in data for k in ("maquina", "url", "tipo")):
        return jsonify({"error": "Faltan datos"}), 400

    maquina = data.get("maquina", "").strip()
                                                                             
    autor = session.get("username")
    if not autor:
                                                                   
        return jsonify({"error": "Usuario no identificado"}), 403
    autor = autor.strip()
    
    url = data.get("url", "").strip()
    tipo = data.get("tipo", "").strip().lower()

    valid, error = validators.validate_machine_name(maquina)
    if not valid:
        return jsonify({"error": f"Campo 'maquina' inválido: {error}"}), 400

    valid, error = validators.validate_author_name(autor)
    if not valid:
         return jsonify({"error": f"Nombre de usuario inválido en sesión: {error}"}), 400

    valid, error = validators.validate_url(url)
    if not valid:
        return jsonify({"error": f"URL inválida: {error}"}), 400

    valid, error = validators.validate_writeup_type(tipo)
    if not valid:
        return jsonify({"error": f"Tipo inválido: {error}"}), 400

    tipo = "video" if tipo == "video" else "texto"

    machine_exists = Machine.query.filter_by(nombre=maquina).first()
    if not machine_exists:

        return jsonify({"error": "La máquina especificada no existe"}), 400

    writeup_exist = PendingWriteup.query.filter_by(
        autor=autor,
        maquina=maquina
    ).first()

    if writeup_exist:
        return jsonify({"error": "Writeup ya está en pendiente de revisión."}), 400

    writeup_publicado = Writeup.query.filter_by(
        autor=autor,
        maquina=maquina
    ).first()

    if writeup_publicado:
        return jsonify({"error": "Writeup ya publicado."}), 400

    try:
        new_pending = PendingWriteup(
            maquina=maquina,
            autor=autor,
            url=url,
            tipo=tipo
        )
        alchemy_db.session.add(new_pending)
        alchemy_db.session.commit()

    except Exception as e:
        alchemy_db.session.rollback()
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

    req = WriteupEditRequest.query.get(request_id)

    if req is None:
        return redirect(safe_redirect)

    if req.estado != 'pendiente':
        return redirect(safe_redirect)

    current_writeup = Writeup.query.get(req.writeup_id)
    if not current_writeup:
        return redirect(safe_redirect)

    new_maquina = req.maquina_nueva if req.maquina_nueva else current_writeup.maquina
    new_autor = req.autor_nuevo if req.autor_nuevo else current_writeup.autor
    new_url = req.url_nueva if req.url_nueva else current_writeup.url
    new_tipo = req.tipo_nuevo if req.tipo_nuevo else current_writeup.tipo

    current_writeup.maquina = new_maquina
    current_writeup.autor = new_autor
    current_writeup.url = new_url
    current_writeup.tipo = new_tipo

    alchemy_db.session.add(current_writeup)

    req.estado = 'aprobada'
    alchemy_db.session.add(req)

    alchemy_db.session.commit()
    recalcular_ranking_writeups()

    return redirect(safe_redirect)

@writeups_bp.route('/writeup-edit-requests/<int:request_id>/reject', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def reject_writeup_edit(request_id):
    req = WriteupEditRequest.query.get(request_id)
    if req:
        req.estado = 'rechazada'
        alchemy_db.session.commit()
    return redirect(request.referrer or url_for('peticiones'))

@writeups_bp.route('/writeup-edit-requests/<int:request_id>/revert', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
def revert_writeup_edit(request_id):
    req = WriteupEditRequest.query.get(request_id)
    if req:
        req.estado = 'pendiente'
        alchemy_db.session.commit()
    return redirect(url_for('peticiones'))

@writeups_bp.route('/api/writeups_recibidos/<int:writeup_id>/aprobar', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("20 per minute", methods=["POST"])
def api_aprobar_writeup_recibido(writeup_id):
    """
    Approve received writeup.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Writeup approved.
    """
    try:
        pending = PendingWriteup.query.get(writeup_id)
        if pending is None:
             return jsonify({"error": "Writeup no encontrado"}), 404

        autor_real = pending.autor
        nuevo = User.query.filter_by(username=autor_real).first()

        if not nuevo:
                                     
            usuario = User.query.filter(func.lower(User.username) == func.lower(autor_real)).first()
            if usuario:
                autor_real = usuario.username

        exists = Writeup.query.filter_by(maquina=pending.maquina, autor=autor_real, url=pending.url).first()
        if not exists:
            new_writeup = Writeup(
                maquina=pending.maquina,
                autor=autor_real,
                url=pending.url,
                tipo=pending.tipo
            )
            alchemy_db.session.add(new_writeup)

        alchemy_db.session.delete(pending)
        
        alchemy_db.session.commit()

        recalcular_ranking_writeups()

        return jsonify({"message": "Writeup aprobado y movido a publicados."}), 200

    except Exception as e:
        return jsonify({"error": f"Error al aprobar el writeup: {str(e)}"}), 500

@writeups_bp.route('/writeup/<int:writeup_id>/edit', methods=['POST'])
@csrf_protect
def edit_writeup(writeup_id):

    flash('Esta función está en mantenimiento. Por favor usa las otras formas de editar writeups.', 'warning')
    return redirect(url_for('writeups_publicados'))

@writeups_bp.route('/peticiones-writeups/<int:req_id>/aprobar', methods=['POST'])
@role_required('admin', 'moderador')
def aprobar_cambio_writeup(req_id):

    req = WriteupEditRequest.query.get(req_id)
    if not req:
        return "No encontrado", 404

    writeup = Writeup.query.get(req.writeup_id)
    if writeup:
        writeup.maquina = req.maquina_nueva
        writeup.autor = req.autor_nuevo
        writeup.url = req.url_nueva
        writeup.tipo = req.tipo_nuevo
        alchemy_db.session.add(writeup)

    alchemy_db.session.delete(req)
    alchemy_db.session.commit()

    return redirect(url_for("peticiones_writeups"))

@writeups_bp.route('/peticiones-writeups/<int:req_id>/rechazar', methods=['POST'])
@role_required('admin', 'moderador')
def rechazar_cambio_writeup(req_id):
    req = WriteupEditRequest.query.get(req_id)
    if req:
         alchemy_db.session.delete(req)
         alchemy_db.session.commit()
    return redirect(url_for("peticiones_writeups"))

@writeups_bp.route('/api/writeups_subidos/<int:writeup_id>', methods=['PUT'])
@role_required('admin', 'moderador', 'jugador')
@csrf_protect
@limiter.limit("20 per minute", methods=["PUT"]) 
def api_update_writeup_subido(writeup_id):
    """
    Update submitted writeup.
    ---
    tags:
      - Writeups
    responses:
      200:
        description: Writeup updated.
    """
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

    role = session.get('role')
    username = (session.get('username') or '').strip()
    user_id = session.get('user_id')

    writeup = Writeup.query.get(writeup_id)

    if writeup is None:
        return jsonify({"error": "Writeup no encontrado"}), 404

    maquina_db = (writeup.maquina or "").strip()
    autor_db = (writeup.autor or "").strip()

    if role in ('admin', 'moderador'):
        try:
                              
            writeup.maquina = maquina_db
            writeup.autor = autor_db
            writeup.url = url
            writeup.tipo = tipo
            
            alchemy_db.session.commit()
            recalcular_ranking_writeups()
            return jsonify({"message": "Writeup actualizado correctamente"}), 200
        except Exception as e:
            alchemy_db.session.rollback()
            return jsonify({"error": f"Error al actualizar en la base de datos: {str(e)}"}), 500

    if not username:
        return jsonify({"error": "Debes iniciar sesión."}), 403

    if username.lower() != autor_db.lower():
        return jsonify({"error": "No tienes permiso para modificar este writeup."}), 403

    try:
                                       
        edit_request = WriteupEditRequest(
            writeup_id=writeup.id,
            user_id=user_id,
            username=username,
            maquina_original=maquina_db,
            autor_original=autor_db,
            url_original=writeup.url,
            tipo_original=writeup.tipo,
            maquina_nueva=maquina_db,
            autor_nuevo=autor_db,
            url_nueva=url,
            tipo_nuevo=tipo
        )
        alchemy_db.session.add(edit_request)
        alchemy_db.session.commit()
        return jsonify({"message": "Tu petición de cambio ha sido enviada para revisión."}), 200
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({"error": f"Error al crear la petición de cambio: {str(e)}"}), 500

@writeups_bp.route('/api/writeups_subidos/<int:writeup_id>', methods=['DELETE'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("20 per minute", methods=["DELETE"]) 
def api_delete_writeup_subido(writeup_id):
    """
    Delete submitted writeup.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Writeup deleted.
    """
    try:
        writeup = Writeup.query.get(writeup_id)
        if not writeup:
            return jsonify({"error": "Writeup no encontrado"}), 404

        alchemy_db.session.delete(writeup)
        alchemy_db.session.commit()

        recalcular_ranking_writeups()

        return jsonify({"message": "Writeup eliminado correctamente"}), 200
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({"error": f"Error al eliminar en la base de datos: {str(e)}"}), 500

@writeups_bp.route('/api/writeups/<maquina_nombre>', methods=['GET'])
@limiter.limit("60 per minute", methods=["GET"]) 
def api_writeups_maquina(maquina_nombre):
    """
    Get writeups for a machine.
    ---
    tags:
      - Writeups
    parameters:
      - name: maquina_nombre
        in: path
        type: string
        required: true
    responses:
      200:
        description: List of writeups.
    """
    writeups_query = alchemy_db.session.query(
            Writeup.id, Writeup.autor, Writeup.url, Writeup.tipo, User.id
        ).outerjoin(User, func.lower(User.username) == func.lower(Writeup.autor))         .filter(Writeup.maquina == maquina_nombre)         .order_by(Writeup.created_at.desc(), Writeup.id.desc()).all()

    writeups = []
    for wid, autor, url, tipo, uid in writeups_query:
        tipo_raw = (tipo or "").strip().lower()
        tipo_emoji = "\U0001F3A5" if tipo_raw == "video" else "\U0001F4DD"
        writeups.append({
            "id": wid,
            "name": autor,
            "url": url,
            "type": tipo_emoji,
            "es_usuario_registrado": bool(uid),
        })

    return jsonify(writeups), 200

@writeups_bp.route('/api/writeups/<int:writeup_id>/report', methods=['POST'])
@limiter.limit("10 per minute", methods=["POST"])
def api_report_writeup(writeup_id):
    """
    Report a writeup.
    ---
    tags:
      - Writeups
    responses:
      200:
        description: Report submitted.
    """
    if 'user_id' not in session:
        return jsonify({"error": "Debes iniciar sesión para reportar"}), 401

    data = request.get_json()
    reason = data.get('reason', 'Sin motivo especificado')
    user_id = session['user_id']

    writeup = Writeup.query.get(writeup_id)
    if not writeup:
        return jsonify({"error": "Writeup no encontrado"}), 404

    try:
        report = WriteupReport(writeup_id=writeup_id, reporter_id=user_id, reason=reason)
        alchemy_db.session.add(report)
        alchemy_db.session.commit()
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({"error": "Error al guardar el reporte"}), 500
    except Exception as e:
        return jsonify({"error": "Error al guardar el reporte"}), 500

    return jsonify({"message": "Reporte enviado correctamente"}), 200

@writeups_bp.route('/api/reports/<int:report_id>/ignore', methods=['POST'])
@role_required('admin', 'moderador')
def api_ignore_report(report_id):
    """
    Ignore/Delete a writeup report.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Report ignored.
    """
    try:
        report = WriteupReport.query.get(report_id)
        if report:
            alchemy_db.session.delete(report)
            alchemy_db.session.commit()
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({"error": "Error al eliminar el reporte"}), 500
    
    return jsonify({"message": "Reporte ignorado/eliminado correctamente"}), 200

@writeups_bp.route('/api/writeup_reports', methods=['GET'])
@role_required('admin', 'moderador')
def api_get_reports():
    """
    Get all writeup reports.
    ---
    tags:
      - Admin
    responses:
      200:
        description: List of reports.
    """
    reports_orm = WriteupReport.query.order_by(WriteupReport.created_at.desc()).all()
    
    reports = []
    for r in reports_orm:

        reporter_name = r.reporter.username if r.reporter else "Unknown"

        writeup_data = {}
        if r.writeup:
            writeup_data = {
                "id": r.writeup.id,
                "autor": r.writeup.autor,
                "maquina": r.writeup.maquina,
                "url": r.writeup.url,
                "tipo": r.writeup.tipo
            }
        
        reports.append({
            "id": r.id,
            "reason": r.reason,
            "created_at": r.created_at,
            "reporter_name": reporter_name,
            "writeup": writeup_data
        })

    return jsonify(reports), 200

@writeups_bp.route('/writeups-recibidos')
@role_required('admin', 'moderador')
def writeups_recibidos():
    """
    Received writeups page.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Received writeups page.
    """
    return render_template('dockerlabs/writeups_recibidos.html')

@writeups_bp.route('/api/ranking_writeups', methods=['GET'])
@limiter.limit("60 per minute", methods=["GET"]) 
def api_ranking_writeups():
    rankings_orm = WriteupRanking.query.order_by(WriteupRanking.puntos.desc(), func.lower(WriteupRanking.nombre).asc()).all()

    ranking = []
    for r in rankings_orm:
        ranking.append({
            "nombre": r.nombre,
            "puntos": r.puntos
        })

    return jsonify(ranking), 200

@writeups_bp.route('/api/ranking_creadores', methods=['GET'])
@limiter.limit("60 per minute", methods=["GET"]) 
def api_ranking_creadores():
    """
    Obtener ranking de creadores.
    ---
    tags:
      - API Pública
    responses:
      200:
        description: Ranking de creadores.
    """
                                     
    rankings = CreatorRanking.query.order_by(
        CreatorRanking.maquinas.desc(),
        func.lower(CreatorRanking.nombre).asc()
    ).all()

    ranking = []
    for r in rankings:
        ranking.append({
            "nombre": r.nombre,
            "maquinas": r.maquinas
        })

    return jsonify(ranking), 200

@writeups_bp.route('/api/author_profile', methods=['GET'])
@limiter.limit("60 per minute", methods=["GET"]) 
def api_author_profile():
    """
    Obtener perfil del autor.
    ---
    tags:
      - API Pública
    parameters:
      - name: nombre
        in: query
        type: string
        required: true
    responses:
      200:
        description: Perfil del autor.
    """
    nombre = (request.args.get('nombre') or '').strip()
    if not nombre:
        return jsonify({'error': 'Nombre requerido'}), 400

    maquinas_orm = Machine.query.filter_by(autor=nombre).order_by(Machine.fecha.desc()).all()

    maquinas = []
    for m in maquinas_orm:
        imagen_url = None
        if m.imagen:
            img = (m.imagen or "").strip()
            if img.startswith('dockerlabs/') or img.startswith('bunkerlabs/'):
                static_path = img
            elif '/' in img:
                static_path = f'dockerlabs/images/{img}'
            else:
                static_path = f'dockerlabs/images/logos/{img}'
            imagen_url = url_for('static', filename=static_path)
        
        maquinas.append({
            "nombre": m.nombre,
            "dificultad": m.dificultad,
            "imagen_url": imagen_url
        })

    writeups_orm = Writeup.query.filter_by(autor=nombre).order_by(Writeup.created_at.desc()).all()
    writeups = []
    for w in writeups_orm:
        writeups.append({
            "maquina": w.maquina,
            "url": w.url,
            "tipo": w.tipo
        })

    user = User.query.filter(func.lower(User.username) == func.lower(nombre)).first()
    
    user_id = user.id if user else None
    biography = user.biography if user else None
    linkedin_url = user.linkedin_url if user else None
    github_url = user.github_url if user else None
    youtube_url = user.youtube_url if user else None

    profile_static_path = get_profile_image_static_path(nombre, user_id=user_id)
    if profile_static_path is None:
        profile_static_path = 'dockerlabs/images/balu.webp'
    
    profile_image_url = url_for('static', filename=profile_static_path)
    
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

@writeups_bp.route('/api/writeups_recibidos', methods=['GET'])
@role_required('admin', 'moderador')
@limiter.limit("60 per minute", methods=["GET"]) 
def api_list_writeups_recibidos():
    """
    List received writeups.
    ---
    tags:
      - Admin
    responses:
      200:
        description: List of received writeups.
    """

    results = alchemy_db.session.query(PendingWriteup, Machine.imagen).outerjoin(Machine, PendingWriteup.maquina == Machine.nombre)        .order_by(PendingWriteup.created_at.desc(), PendingWriteup.id.desc()).all()
        
    writeups = []
    for pw, imagen in results:
        writeups.append({
            "id": pw.id,
            "maquina": pw.maquina,
            "autor": pw.autor,
            "url": pw.url,
            "tipo": pw.tipo,
            "created_at": pw.created_at,
            "imagen": imagen
        })
    return jsonify(writeups), 200

@writeups_bp.route('/api/writeups_recibidos/<int:writeup_id>', methods=['PUT'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("20 per minute", methods=["PUT"]) 
def api_update_writeup_recibido(writeup_id):
    """
    Update received writeup.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Writeup updated.
    """
    data = request.json or {}
    if not all(k in data for k in ("maquina", "autor", "url", "tipo")):
        return jsonify({"error": "Faltan datos"}), 400

    maquina = data["maquina"].strip()
    autor = data["autor"].strip()
    url = data["url"].strip()
    tipo = data["tipo"].strip()

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
        pending = PendingWriteup.query.get(writeup_id)
        if not pending:
             return jsonify({"error": "Writeup no encontrado"}), 404
             
        pending.maquina = maquina
        pending.autor = autor
        pending.url = url
        pending.tipo = tipo
        
        alchemy_db.session.commit()

        return jsonify({"message": "Writeup actualizado correctamente"}), 200
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({"error": f"Error al actualizar en la base de datos: {str(e)}"}), 500

@writeups_bp.route('/api/writeups_recibidos/<int:writeup_id>', methods=['DELETE'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("20 per minute", methods=["DELETE"]) 
def api_delete_writeup_recibido(writeup_id):
    """
    Delete received writeup.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Writeup deleted.
    """
    try:
        pending = PendingWriteup.query.get(writeup_id)
        if not pending:
            return jsonify({"error": "Writeup no encontrado"}), 404

        alchemy_db.session.delete(pending)
        alchemy_db.session.commit()

        return jsonify({"message": "Writeup eliminado correctamente"}), 200
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({"error": f"Error al eliminar en la base de datos: {str(e)}"}), 500

@writeups_bp.route('/writeups-publicados')
@role_required('admin', 'moderador', 'jugador')
def writeups_publicados():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    """
    Published writeups page.
    ---
    tags:
      - Writeups
    responses:
      200:
        description: Published writeups page.
    """
    return render_template('dockerlabs/writeups_publicados.html',user=user)

@writeups_bp.route('/api/writeups_subidos', methods=['GET'])
@role_required('admin', 'moderador', 'jugador')
@limiter.limit("60 per minute", methods=["GET"]) 
def api_list_writeups_subidos():
    """
    List submitted writeups.
    ---
    tags:
      - Writeups
    responses:
      200:
        description: List of submitted writeups.
    """
    maquina = request.args.get('maquina', type=str)
    filter_mode = request.args.get('filter')
    role = get_current_role()
    username = (session.get('username') or '').strip()

    query = Writeup.query
    
    # Logic:
    # If standard user -> always filter by their username
    # If admin/mod -> 
    #    if filter='mine' -> filter by their username
    #    else -> show all
    
    if role in ['admin', 'moderador']:
        if filter_mode == 'mine' and username:
            query = query.filter_by(autor=username)
            
        if maquina:
            query = query.filter_by(maquina=maquina)
    else:
        if not username:
            return jsonify([]), 200
        query = query.filter_by(autor=username)
        if maquina:
            query = query.filter_by(maquina=maquina)

    writeups_objs = query.order_by(Writeup.created_at.desc(), Writeup.id.desc()).all()

    writeups = []
    for w in writeups_objs:
        writeups.append({
            "id": w.id,
            "maquina": w.maquina,
            "autor": w.autor,
            "url": w.url,
            "tipo": w.tipo,
            "created_at": w.created_at,
        })

    return jsonify(writeups), 200

@writeups_bp.route('/api/writeups_subidos/maquinas', methods=['GET'])
@role_required('admin', 'moderador', 'jugador')
@limiter.limit("60 per minute", methods=["GET"]) 
def api_list_maquinas_writeups_subidos():
    """
    List machines with submitted writeups.
    ---
    tags:
    """
    filter_mode = request.args.get('filter')
    role = get_current_role()
    username = (session.get('username') or '').strip()

    query = alchemy_db.session.query(
        Writeup.maquina,
        func.count().label('total'),
        Machine.imagen
    ).outerjoin(Machine, Writeup.maquina == Machine.nombre)     .filter(Writeup.maquina != None, Writeup.maquina != '')
    
    if role in ['admin', 'moderador']:
        if filter_mode == 'mine' and username:
             query = query.filter(Writeup.autor == username)
    else:
        if not username:
            return jsonify([]), 200
        query = query.filter(Writeup.autor == username)

    results = query.group_by(Writeup.maquina, Machine.imagen)                   .order_by(func.lower(Writeup.maquina)).all()

    maquinas = []
    for maquina_nombre, total, imagen in results:
        imagen_rel = (imagen or "").strip()
        imagen_url = None
        if imagen_rel:
            if imagen_rel.startswith('dockerlabs/') or imagen_rel.startswith('bunkerlabs/'):
                static_path = imagen_rel
            elif '/' in imagen_rel:
                static_path = f'dockerlabs/images/{imagen_rel}'
            else:
                static_path = f'dockerlabs/images/logos/{imagen_rel}'
            imagen_url = url_for('static', filename=static_path)
        
        maquinas.append({
            "maquina": maquina_nombre,
            "total": total,
            "imagen": imagen_url,
        })

    return jsonify(maquinas), 200

@writeups_bp.route('/peticiones-writeups')
@role_required('admin', 'moderador')
def peticiones_writeups():
    """
    Writeup petitions page.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Petitions page.
    """
                                    
    requests = WriteupEditRequest.query.order_by(WriteupEditRequest.id.desc()).all()

    return render_template("peticiones.html", peticiones=requests)
