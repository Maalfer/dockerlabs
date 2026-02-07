from datetime import datetime
import secrets

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from dockerlabs.extensions import db as alchemy_db
from dockerlabs.models import Machine
from . import extensions
from .decorators import csrf_protect, role_required
from .models import BunkerAccessToken, BunkerSolve, BunkerAccessLog

bunkerlabs_bp = Blueprint('bunkerlabs', __name__)

PUNTOS_MAP = {
    'Muy Fácil': 1,
    'Fácil': 2,
    'Medio': 3,
    'Difícil': 4
}


@bunkerlabs_bp.route('/login', methods=['GET', 'POST'])
@csrf_protect
@extensions.limiter.limit("5 per minute", methods=["POST"])
def bunkerlabs_login():
    """
    BunkerLabs login.
    ---
    tags:
      - BunkerLabs
    responses:
      200:
        description: Login page or redirect.
    """
    if session.get('user_id') is None:
        return redirect(url_for('auth.login'))

    error = None

    if request.method == 'POST':
        token_introducido = (request.form.get('password') or '').strip()

        if not token_introducido:
            error = "Debes introducir una contraseña de acceso."
        else:
                                   
            token_obj = BunkerAccessToken.query.filter_by(
                token=token_introducido,
                activo=1
            ).first()

            if token_obj is not None:
                                                              
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
                return redirect(url_for('bunkerlabs.bunkerlabs_home'))
            else:
                error = "Contraseña incorrecta o inactiva."

    return render_template('bunkerlabs/login.html', error=error)


@bunkerlabs_bp.route('/guest')
@extensions.limiter.limit("5 per minute")
def bunkerlabs_guest():
    """
    Enter BunkerLabs in guest mode.
    ---
    tags:
      - BunkerLabs
    responses:
      302:
        description: Redirect to BunkerLabs home.
    """
    if session.get('user_id') is None:
        return redirect(url_for('auth.login'))
    
    session['bunkerlabs_ok'] = True
    session['bunkerlabs_guest'] = True
    session['bunkerlabs_nombre'] = "Invitado"
    session['bunkerlabs_id'] = None
    
    return redirect(url_for('bunkerlabs.bunkerlabs_home'))


@bunkerlabs_bp.route('/logout')
def bunkerlabs_logout():
    """
    Logout from BunkerLabs.
    ---
    tags:
      - BunkerLabs
    responses:
      302:
        description: Redirect to BunkerLabs login.
    """
    # Clear BunkerLabs session keys
    session.pop('bunkerlabs_ok', None)
    session.pop('bunkerlabs_guest', None)
    session.pop('bunkerlabs_nombre', None)
    session.pop('bunkerlabs_id', None)
    
    return redirect(url_for('bunkerlabs.bunkerlabs_login'))


@bunkerlabs_bp.route('/', methods=['GET', 'POST'])
def bunkerlabs_home():
    """
    Página principal de acceso a máquinas.
    ---
    tags:
      - BunkerLabs
    responses:
      200:
        description: Home page.
    """
    # Verificar si viene un token por URL para acceso directo
    token_url = request.args.get('token')
    if token_url:
        token_obj = BunkerAccessToken.query.filter_by(
            token=token_url,
            activo=1
        ).first()
        
        if token_obj:
            docker_username = session.get('username')
            docker_user_id = session.get('user_id')
            
            # Si el usuario está autenticado en DockerLabs, usar su nombre
            if docker_username and docker_user_id:
                token_obj.nombre = docker_username
                session['bunkerlabs_nombre'] = docker_username
                session['bunkerlabs_anonymous'] = False
            else:
                # Usuario anónimo - no autenticado en DockerLabs
                session['bunkerlabs_nombre'] = 'Anónimo'
                session['bunkerlabs_anonymous'] = True
                session['username'] = 'Anónimo'
                session['user_id'] = None
            
            # Marcar sesión como OK para el login de BunkerLabs
            session['bunkerlabs_ok'] = True
                
            token_obj.last_accessed = datetime.utcnow()
            
            new_log = BunkerAccessLog(
                token_id=token_obj.id,
                user_nombre=session['bunkerlabs_nombre'],
                accessed_at=datetime.utcnow()
            )
            alchemy_db.session.add(new_log)
            alchemy_db.session.commit()
            
            # Redirigir limpio para quitar el token de la URL
            return redirect(url_for('bunkerlabs.bunkerlabs_home'))
        else:
            flash('El enlace de acceso no es válido o está inactivo.', 'error')
            return redirect(url_for('bunkerlabs.bunkerlabs_login'))

    if 'bunkerlabs_nombre' not in session:
        return redirect(url_for('bunkerlabs.bunkerlabs_login'))
    
    # Permitir acceso anónimo si tienen token válido (bunkerlabs_ok = True)
    # ya no requiere user_id de DockerLabs
    if not session.get('bunkerlabs_ok'):
        return redirect(url_for('bunkerlabs.bunkerlabs_login'))

    maquinas = Machine.query.filter_by(origen='bunker').order_by(Machine.id.asc()).all()
    
    is_anonymous = session.get('bunkerlabs_anonymous', False)

    return render_template('bunkerlabs/home.html', 
                           maquinas=maquinas, 
                           is_guest=session.get('bunkerlabs_guest', False),
                           is_anonymous=is_anonymous)


@bunkerlabs_bp.route('/accesos', methods=['GET', 'POST'])
@role_required('admin')
@csrf_protect
@extensions.limiter.limit("5 per minute", methods=["POST"])
def accesos_bunkerlabs():
    """
    BunkerLabs access management.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Access management page.
    """
    error = None
    success = None
    nuevo_token = None

    if request.method == 'POST':
        nombre = (request.form.get('nombre') or '').strip()
        password = (request.form.get('password') or '').strip()

        if not nombre or not password:
            error = "El nombre y la contraseña son obligatorios."
        else:
            nuevo_token = password

            try:
                                         
                new_token_obj = BunkerAccessToken(
                    nombre=nombre,
                    token=nuevo_token
                )
                alchemy_db.session.add(new_token_obj)
                alchemy_db.session.commit()
                success = f"Acceso creado correctamente para {nombre}"
            except IntegrityError:
                alchemy_db.session.rollback()
                error = "Error: Esa contraseña ya existe."

    tokens = BunkerAccessToken.query.order_by(
        BunkerAccessToken.created_at.desc()
    ).all()

    # Obtener máquinas de Entornos Reales y todos los writeups
    from .models import BunkerWriteup
    real_machines = Machine.query.filter_by(origen='bunker', clase='real').order_by(Machine.nombre.asc()).all()
    writeups = BunkerWriteup.query.order_by(BunkerWriteup.created_at.desc()).all()
    
    # Obtener todas las máquinas de bunker para gestión de flags
    bunker_machines = Machine.query.filter_by(origen='bunker').order_by(Machine.nombre.asc()).all()

    return render_template(
        'bunkerlabs/accesos.html',
        tokens=tokens,
        error=error,
        success=success,
        nuevo_token=nuevo_token,
        real_machines=real_machines,
        writeups=writeups,
        bunker_machines=bunker_machines
    )


@bunkerlabs_bp.route('/accesos/<int:token_id>/delete', methods=['POST'])
@role_required('admin')
@csrf_protect
@extensions.limiter.limit("5 per minute", methods=["POST"])
def delete_bunker_token(token_id):
    """
    Delete BunkerLabs access token.
    ---
    tags:
      - Admin
    responses:
      302:
        description: Redirect to access management.
    """
                             
    token_obj = BunkerAccessToken.query.get(token_id)
    if token_obj:
        alchemy_db.session.delete(token_obj)
        alchemy_db.session.commit()
    return redirect(url_for('bunkerlabs.accesos_bunkerlabs'))


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

@bunkerlabs_bp.route('/admin/writeups/add', methods=['POST'])
@role_required('admin')
@csrf_protect
@extensions.limiter.limit("10 per minute", methods=["POST"])
def add_writeup():
    """Añadir writeup para máquina de Entornos Reales."""
    from .models import BunkerWriteup
    
    maquina = (request.form.get('maquina') or '').strip()
    autor = (request.form.get('autor') or '').strip()
    url = (request.form.get('url') or '').strip()
    tipo = (request.form.get('tipo') or '').strip()
    locked = 'locked' in request.form
    
    if not all([maquina, autor, url, tipo]) or tipo not in ['texto', 'video']:
        flash('Todos los campos son obligatorios y el tipo debe ser texto o video.', 'error')
        return redirect(url_for('bunkerlabs.accesos_bunkerlabs'))
    
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
        flash(f'Writeup añadido correctamente para {maquina}', 'success')
    except IntegrityError:
        alchemy_db.session.rollback()
        flash('Error: Este writeup ya existe.', 'error')
    except Exception as e:
        alchemy_db.session.rollback()
        flash(f'Error al añadir writeup: {str(e)}', 'error')
    
    return redirect(url_for('bunkerlabs.accesos_bunkerlabs'))

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

@bunkerlabs_bp.route('/admin/writeups/delete/<int:writeup_id>', methods=['POST'])
@role_required('admin')
@csrf_protect
@extensions.limiter.limit("10 per minute", methods=["POST"])
def delete_writeup(writeup_id):
    """Eliminar writeup."""
    from .models import BunkerWriteup
    
    writeup = BunkerWriteup.query.get(writeup_id)
    
    if not writeup:
        flash('Writeup no encontrado.', 'error')
        return redirect(url_for('bunkerlabs.accesos_bunkerlabs'))
    
    try:
        alchemy_db.session.delete(writeup)
        alchemy_db.session.commit()
        flash('Writeup eliminado correctamente.', 'success')
    except Exception as e:
        alchemy_db.session.rollback()
        flash(f'Error al eliminar writeup: {str(e)}', 'error')
    
    return redirect(url_for('bunkerlabs.accesos_bunkerlabs'))


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
