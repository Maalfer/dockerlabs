from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from dockerlabs.extensions import db as alchemy_db
from dockerlabs.models import Machine
from . import extensions
from .decorators import csrf_protect, role_required
from .models import BunkerAccessToken, BunkerSolve, BunkerAccessLog

bunkerlabs_bp = Blueprint('bunkerlabs', __name__)

@bunkerlabs_bp.route('/', methods=['GET', 'POST'])
def bunkerlabs_home():
    """
    Redirect root to frontend or handle legacy link.
    """
    token_url = request.args.get('token')
    if token_url:
        return redirect(f'http://localhost:5173/bunkerlabs?token={token_url}')
    return redirect('http://localhost:5173/bunkerlabs')



@bunkerlabs_bp.route('/subir-flag', methods=['POST'])
@csrf_protect
@extensions.limiter.limit("10 per minute", methods=["POST"])
def subir_flag():
    """
    Submit a flag for BunkerLabs machine.
    ---
    tags:
      - BunkerLabs
    responses:
      200:
        description: Flag processing result.
    """
    data = request.get_json()
    maquina_nombre = data.get('maquina')
    pin_introducido = data.get('pin')

    if not maquina_nombre or not pin_introducido:
        return jsonify({'error': 'Faltan datos'}), 400

    maquina = Machine.query.filter_by(nombre=maquina_nombre, origen='bunker').first()

    if not maquina:
        return jsonify({'error': 'Máquina no encontrada'}), 404

    pin_real = maquina.pin
    dificultad = maquina.dificultad
    maquina_id = maquina.id
    user_id = session.get('bunkerlabs_id')

    if not user_id:
        if session.get('bunkerlabs_guest'):
            if not maquina.guest_access:
                 return jsonify({'error': 'Los invitados no pueden subir flags.'}), 403
            
            # Logic to attribute solve to DockerLabs user even if in Guest mode
            docker_username = session.get('username')
            if docker_username:
                # Find existing token for this user
                token_obj = BunkerAccessToken.query.filter_by(nombre=docker_username).first()
                if not token_obj:
                    # Create a hidden token for this user so they can rank
                    try:
                        new_token = secrets.token_hex(16)
                        token_obj = BunkerAccessToken(
                            nombre=docker_username,
                            token=new_token,
                            activo=1
                        )
                        alchemy_db.session.add(token_obj)
                        alchemy_db.session.commit()
                    except IntegrityError:
                        alchemy_db.session.rollback()
                        return jsonify({'error': 'Error al registrar progreso.'}), 500
                
                user_id = token_obj.id
            else:
                 return jsonify({'message': '¡Flag correcta! (Modo invitado: no se guarda el progreso)'}), 200
        else:
            return jsonify({'error': 'Sesión no válida.'}), 401

    if pin_real == pin_introducido:
                                    
        ya_completada = BunkerSolve.query.filter_by(
            user_id=user_id,
            machine_id=maquina_id
        ).first()

        if ya_completada:
            return jsonify({'message': 'Flag correcta, pero ya habías completado esta máquina.'}), 200

        puntos = PUNTOS_MAP.get(dificultad, 0)

        try:
                            
            new_solve = BunkerSolve(
                user_id=user_id,
                machine_id=maquina_id
            )
            alchemy_db.session.add(new_solve)

            token_obj = BunkerAccessToken.query.get(user_id)
            if token_obj:
                token_obj.puntos += puntos
            
            alchemy_db.session.commit()
            return jsonify({'message': f'¡Flag correcta! Has ganado {puntos} puntos.'}), 200
        except Exception as e:
            alchemy_db.session.rollback()
            return jsonify({'error': 'Error al procesar la flag.'}), 500

    else:
        return jsonify({'error': 'Flag incorrecta.'}), 401

@bunkerlabs_bp.route('/api/ranking', methods=['GET'])
@extensions.limiter.limit("60 per minute", methods=["GET"])
def bunker_ranking():
    """
    Get BunkerLabs player ranking.
    ---
    tags:
      - BunkerLabs
    responses:
      200:
        description: List of players ranked by points.
    """
    tokens = BunkerAccessToken.query.filter(
        BunkerAccessToken.puntos > 0
    ).order_by(
        BunkerAccessToken.puntos.desc(),
        func.lower(BunkerAccessToken.nombre).asc()
    ).all()

    ranking = []
    for token in tokens:
        ranking.append({
            "nombre": token.nombre,
            "puntos": token.puntos
        })

    return jsonify(ranking), 200

@bunkerlabs_bp.route('/api/logs/<int:token_id>', methods=['GET'])
@role_required('admin')
def get_bunker_access_logs(token_id):
    """
    Get access logs for a specific Bunker token.
    ---
    tags:
      - BunkerLabs
    parameters:
      - name: token_id
        in: path
        type: integer
        required: true
        description: The ID of the token.
    responses:
      200:
        description: List of access logs.
    """
    logs = BunkerAccessLog.query.filter_by(token_id=token_id).order_by(BunkerAccessLog.accessed_at.desc()).all()
    
    data = []
    for log in logs:
        data.append({
            "nombre": log.user_nombre,
            "fecha": log.accessed_at.strftime('%d-%m-%Y %H:%M:%S')
        })
        
    return jsonify(data), 200

@bunkerlabs_bp.route('/api/logs/<int:token_id>/delete', methods=['POST'])
@role_required('admin')
@csrf_protect
def delete_bunker_access_logs(token_id):
    """
    Delete access logs for a token.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Logs deleted.
    """
    try:
        BunkerAccessLog.query.filter_by(token_id=token_id).delete()
        alchemy_db.session.commit()
        return jsonify({'message': 'Historial eliminado correctamente.'}), 200
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({'error': 'Error al eliminar el historial.'}), 500

@bunkerlabs_bp.route('/api/writeups/<string:maquina_nombre>', methods=['GET'])
def get_writeups(maquina_nombre):
    """Obtener writeups de una máquina de Entornos Reales."""
    from .models import BunkerWriteup
    
    writeups = BunkerWriteup.query.filter_by(maquina=maquina_nombre).order_by(BunkerWriteup.created_at.desc()).all()
    
    writeups_data = [
        {
            'id': w.id,
            'autor': w.autor,
            'url': w.url,
            'tipo': w.tipo,
            'locked': w.locked,
            'created_at': w.created_at.isoformat() if w.created_at else None
        }
        for w in writeups
    ]
    
    return jsonify({'writeups': writeups_data}), 200



@bunkerlabs_bp.route('/admin/writeups/toggle_lock/<int:writeup_id>', methods=['POST'])
@role_required('admin')
@csrf_protect
@extensions.limiter.limit("20 per minute", methods=["POST"])
def toggle_writeup_lock(writeup_id):
    """Alternar estado de bloqueo de writeup."""
    from .models import BunkerWriteup
    
    writeup = BunkerWriteup.query.get(writeup_id)
    
    if not writeup:
        return jsonify({'error': 'Writeup no encontrado'}), 404
        
    try:
        writeup.locked = not writeup.locked
        alchemy_db.session.commit()
        return jsonify({'message': 'Estado actualizado', 'locked': writeup.locked}), 200
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({'error': str(e)}), 500




@bunkerlabs_bp.route('/admin/machines/update_flag/<int:machine_id>', methods=['POST'])
@role_required('admin')
@csrf_protect
def update_machine_flag(machine_id):
    """Update flag (pin) for a BunkerLabs machine"""
    try:
        machine = Machine.query.get(machine_id)
        if not machine or machine.origen != 'bunker':
            return jsonify({'error': 'Máquina no encontrada'}), 404
        
        new_flag = request.json.get('flag', '').strip()
        
        if not new_flag:
            return jsonify({'error': 'La flag no puede estar vacía'}), 400
        
        machine.pin = new_flag
        alchemy_db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Flag actualizada para {machine.nombre}',
            'machine_id': machine_id,
            'machine_name': machine.nombre
        })
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ===================================================================
# JSON API ENDPOINTS FOR REACT FRONTEND
# ===================================================================

@bunkerlabs_bp.route('/api/session', methods=['GET'])
def api_session():
    """Return current BunkerLabs session status."""
    from dockerlabs.decorators import get_current_role
    role = get_current_role() if session.get('user_id') else None
    return jsonify({
        'logged_in': bool(session.get('bunkerlabs_ok')) or (role == 'admin'),
        'nombre': session.get('bunkerlabs_nombre'),
        'is_guest': session.get('bunkerlabs_guest', False),
        'is_anonymous': session.get('bunkerlabs_anonymous', False),
        'is_admin': role == 'admin' if role else False,
        'docker_logged_in': session.get('user_id') is not None,
        'csrf_token': session.get('csrf_token', ''),
    }), 200


@bunkerlabs_bp.route('/api/login', methods=['POST'])
@csrf_protect
@extensions.limiter.limit("5 per minute", methods=["POST"])
def api_login():
    """JSON login for BunkerLabs."""
    if session.get('user_id') is None:
        return jsonify({'error': 'Debes iniciar sesión en DockerLabs primero.'}), 401

    data = request.get_json() or {}
    token_introducido = (data.get('password') or '').strip()

    if not token_introducido:
        return jsonify({'error': 'Debes introducir una contraseña de acceso.'}), 400

    token_obj = BunkerAccessToken.query.filter_by(
        token=token_introducido,
        activo=1
    ).first()

    if token_obj is None:
        return jsonify({'error': 'Contraseña incorrecta o inactiva.'}), 401

    docker_username = session.get('username')
    if docker_username:
        token_obj.nombre = docker_username
        token_obj.last_accessed = datetime.utcnow()
        new_log = BunkerAccessLog(
            token_id=token_obj.id,
            user_nombre=docker_username,
            accessed_at=datetime.utcnow()
        )
        alchemy_db.session.add(new_log)
        alchemy_db.session.commit()
        session['bunkerlabs_nombre'] = docker_username
    else:
        session['bunkerlabs_nombre'] = token_obj.nombre
        token_obj.last_accessed = datetime.utcnow()
        new_log = BunkerAccessLog(
            token_id=token_obj.id,
            user_nombre=token_obj.nombre,
            accessed_at=datetime.utcnow()
        )
        alchemy_db.session.add(new_log)
        alchemy_db.session.commit()

    session['bunkerlabs_ok'] = True
    session['bunkerlabs_id'] = token_obj.id
    session.pop('bunkerlabs_guest', None)

    return jsonify({'success': True, 'nombre': session['bunkerlabs_nombre']}), 200


@bunkerlabs_bp.route('/api/guest', methods=['POST'])
@extensions.limiter.limit("5 per minute")
def api_guest():
    """Enter BunkerLabs as guest via JSON."""
    if session.get('user_id') is None:
        return jsonify({'error': 'Debes iniciar sesión en DockerLabs primero.'}), 401

    session['bunkerlabs_ok'] = True
    session['bunkerlabs_guest'] = True
    session['bunkerlabs_nombre'] = "Invitado"
    session['bunkerlabs_id'] = None

    return jsonify({'success': True, 'nombre': 'Invitado'}), 200


@bunkerlabs_bp.route('/api/logout', methods=['POST'])
def api_logout():
    """Logout from BunkerLabs via JSON."""
    session.pop('bunkerlabs_ok', None)
    session.pop('bunkerlabs_guest', None)
    session.pop('bunkerlabs_nombre', None)
    session.pop('bunkerlabs_id', None)
    return jsonify({'success': True}), 200


@bunkerlabs_bp.route('/api/machines', methods=['GET'])
def api_machines():
    """Return all BunkerLabs machines as JSON."""
    from dockerlabs.decorators import get_current_role
    role = get_current_role()
    if not session.get('bunkerlabs_ok') and role != 'admin':
        return jsonify({'error': 'No autorizado'}), 401

    maquinas = Machine.query.filter_by(origen='bunker').order_by(Machine.id.asc()).all()
    is_guest = session.get('bunkerlabs_guest', False)

    result = []
    for m in maquinas:
        result.append({
            'id': m.id,
            'nombre': m.nombre,
            'tamaño': m.tamaño if hasattr(m, 'tamaño') else '',
            'clase': m.clase,
            'color': m.color,
            'autor': m.autor,
            'enlace_autor': m.enlace_autor,
            'fecha': m.fecha,
            'imagen': m.imagen,
            'descripcion': m.descripcion,
            'link_descarga': m.link_descarga,
            'dificultad': m.dificultad,
            'guest_access': m.guest_access if hasattr(m, 'guest_access') else True,
        })

    return jsonify({
        'machines': result,
        'is_guest': is_guest,
        'is_anonymous': session.get('bunkerlabs_anonymous', False),
    }), 200


@bunkerlabs_bp.route('/api/accesos', methods=['GET'])
@role_required('admin')
def api_accesos_get():
    """Return accesos data for admin panel."""
    from .models import BunkerWriteup

    tokens = BunkerAccessToken.query.order_by(
        BunkerAccessToken.created_at.desc()
    ).all()

    tokens_data = []
    for t in tokens:
        tokens_data.append({
            'id': t.id,
            'nombre': t.nombre,
            'token': t.token,
            'activo': bool(t.activo),
            'puntos': t.puntos,
            'created_at': t.created_at.isoformat() if t.created_at else None,
            'last_accessed': t.last_accessed.isoformat() if t.last_accessed else None,
        })

    real_machines = Machine.query.filter_by(origen='bunker', clase='real').order_by(Machine.nombre.asc()).all()
    real_machines_data = [{'id': m.id, 'nombre': m.nombre} for m in real_machines]

    writeups = BunkerWriteup.query.order_by(BunkerWriteup.created_at.desc()).all()
    writeups_data = [{
        'id': w.id,
        'maquina': w.maquina,
        'autor': w.autor,
        'url': w.url,
        'tipo': w.tipo,
        'locked': w.locked,
        'created_at': w.created_at.isoformat() if w.created_at else None,
    } for w in writeups]

    bunker_machines = Machine.query.filter_by(origen='bunker').order_by(Machine.nombre.asc()).all()
    bunker_machines_data = [{
        'id': m.id,
        'nombre': m.nombre,
        'dificultad': m.dificultad,
        'color': m.color,
        'pin': m.pin if hasattr(m, 'pin') else '',
    } for m in bunker_machines]

    return jsonify({
        'tokens': tokens_data,
        'real_machines': real_machines_data,
        'writeups': writeups_data,
        'bunker_machines': bunker_machines_data,
    }), 200


@bunkerlabs_bp.route('/api/accesos', methods=['POST'])
@role_required('admin')
@csrf_protect
@extensions.limiter.limit("5 per minute", methods=["POST"])
def api_accesos_create():
    """Create a new access token via JSON."""
    data = request.get_json() or {}
    nombre = (data.get('nombre') or '').strip()
    password = (data.get('password') or '').strip()

    if not nombre or not password:
        return jsonify({'error': 'El nombre y la contraseña son obligatorios.'}), 400

    try:
        new_token_obj = BunkerAccessToken(
            nombre=nombre,
            token=password
        )
        alchemy_db.session.add(new_token_obj)
        alchemy_db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Acceso creado correctamente para {nombre}',
            'token': password,
        }), 200
    except IntegrityError:
        alchemy_db.session.rollback()
        return jsonify({'error': 'Error: Esa contraseña ya existe.'}), 409


@bunkerlabs_bp.route('/api/accesos/<int:token_id>', methods=['DELETE'])
@role_required('admin')
@csrf_protect
def api_delete_token(token_id):
    """Delete a BunkerLabs access token via JSON."""
    token_obj = BunkerAccessToken.query.get(token_id)
    if not token_obj:
        return jsonify({'error': 'Token no encontrado'}), 404
    alchemy_db.session.delete(token_obj)
    alchemy_db.session.commit()
    return jsonify({'success': True, 'message': 'Token eliminado'}), 200


@bunkerlabs_bp.route('/api/writeups/add', methods=['POST'])
@role_required('admin')
@csrf_protect
@extensions.limiter.limit("10 per minute", methods=["POST"])
def api_add_writeup():
    """Add writeup via JSON."""
    from .models import BunkerWriteup

    data = request.get_json() or {}
    maquina = (data.get('maquina') or '').strip()
    autor = (data.get('autor') or '').strip()
    url = (data.get('url') or '').strip()
    tipo = (data.get('tipo') or '').strip()
    locked = data.get('locked', False)

    if not all([maquina, autor, url, tipo]) or tipo not in ['texto', 'video']:
        return jsonify({'error': 'Todos los campos son obligatorios y el tipo debe ser texto o video.'}), 400

    try:
        new_writeup = BunkerWriteup(
            maquina=maquina,
            autor=autor,
            url=url,
            tipo=tipo,
            locked=locked
        )
        alchemy_db.session.add(new_writeup)
        alchemy_db.session.commit()
        return jsonify({'success': True, 'message': f'Writeup añadido correctamente para {maquina}'}), 200
    except IntegrityError:
        alchemy_db.session.rollback()
        return jsonify({'error': 'Error: Este writeup ya existe.'}), 409
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({'error': f'Error al añadir writeup: {str(e)}'}), 500


@bunkerlabs_bp.route('/api/writeups/<int:writeup_id>', methods=['DELETE'])
@role_required('admin')
@csrf_protect
def api_delete_writeup(writeup_id):
    """Delete writeup via JSON."""
    from .models import BunkerWriteup

    writeup = BunkerWriteup.query.get(writeup_id)
    if not writeup:
        return jsonify({'error': 'Writeup no encontrado'}), 404

    try:
        alchemy_db.session.delete(writeup)
        alchemy_db.session.commit()
        return jsonify({'success': True, 'message': 'Writeup eliminado correctamente.'}), 200
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({'error': f'Error al eliminar writeup: {str(e)}'}), 500
