import os
import json
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
from .decorators import role_required, csrf_protect, get_current_role
from bunkerlabs.extensions import limiter
from . import validators
from .models import Machine, Category, CreatorRanking, MachineClaim, MachineEditRequest, Rating, CompletedMachine

from .extensions import db as alchemy_db

maquinas_bp = Blueprint('maquinas', __name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MACHINE_LOGOS_FOLDER = os.path.join(BASE_DIR, 'static', 'dockerlabs', 'images', 'logos')
LOGO_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'dockerlabs', 'images', 'logos')
ALLOWED_LOGO_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
ALLOWED_PROFILE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

def recalcular_ranking_creadores():
                            
    def clean(s): return (s or "").strip()

    from sqlalchemy import func
    
    results = alchemy_db.session.query(Machine.autor, func.count(Machine.id)).group_by(Machine.autor).all()

    try:
        CreatorRanking.query.delete()

        for autor, count in results:
            nombre = clean(autor)
            if not nombre: continue
            
            entry = CreatorRanking(nombre=nombre, maquinas=count)
            alchemy_db.session.add(entry)
            
        alchemy_db.session.commit()
    except Exception as e:
        alchemy_db.session.rollback()



@maquinas_bp.route('/api/add-maquina', methods=['POST'])
@role_required('admin')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def api_add_maquina():
    """
    API to add a new machine.
    """
    error = None
    try:
        nombre = (request.form.get('nombre') or '').strip()
        dificultad_form = (request.form.get('dificultad') or '').strip()
        autor = (request.form.get('autor') or '').strip()
        fecha_raw = (request.form.get('fecha') or '').strip()
        descripcion = (request.form.get('descripcion') or '').strip()
        link_descarga = (request.form.get('link_descarga') or '').strip()
        imagen = (request.form.get('imagen') or '').strip()
        destino = (request.form.get('destino') or 'docker').strip().lower()

        # Validar que el autor sea un usuario registrado
        from .models import User
        if autor:
            user_exists = User.query.filter_by(username=autor).first()
            if not user_exists:
                return jsonify({'error': "El autor seleccionado no es un usuario registrado válido."}), 400

        file = request.files.get('imagen')
        if file and file.filename:
            file.seek(0, os.SEEK_END)
            size = file.tell()
            file.seek(0)
            MAX_IMAGE_SIZE = 2 * 1024 * 1024
            if size > MAX_IMAGE_SIZE:
                return jsonify({'error': "La imagen excede el tamaño máximo permitido de 2MB."}), 400
            elif not file.mimetype.startswith('image/'):
                return jsonify({'error': "El archivo subido no es una imagen válida."}), 400
            else:
                valid, err_msg = validators.validate_image_content(file.stream)
                if not valid:
                    return jsonify({'error': f"Contenido de imagen inválido: {err_msg}"}), 400
                else:
                    original = secure_filename(file.filename)
                
                _, ext = os.path.splitext(original)
                ext = ext.lower()
                if ext in ALLOWED_PROFILE_EXTENSIONS:
                    nombre_seguro = secure_filename(nombre) if nombre else secure_filename(original)
                    final_filename = f"{nombre_seguro}{ext}"
                    
                    if destino == 'bunker':
                        upload_folder = os.path.join(BASE_DIR, 'static', 'bunkerlabs', 'images', 'logos-bunkerlabs')
                        db_path_prefix = "bunkerlabs/images/logos-bunkerlabs"
                    else:
                        upload_folder = LOGO_UPLOAD_FOLDER
                        db_path_prefix = "dockerlabs/images/logos"

                    os.makedirs(upload_folder, exist_ok=True)
                    save_path = os.path.join(upload_folder, final_filename)
                    file.save(save_path)
                    imagen = f"{db_path_prefix}/{final_filename}"
                else:
                    return jsonify({'error': "Extensión de imagen no permitida."}), 400
        else:
            if not imagen:
                if destino == 'bunker':
                     imagen = "dockerlabs/images/logos/logo.png"
                else:
                     imagen = "dockerlabs/images/logos/logo.png"

        # Obtener enlace_autor desde el perfil del usuario
        # NOTE: logic here might need to fetch the AUTHOR'S profile, not the current user's profile if admin is adding for someone else?
        # The original code used session.get('user_id'), which is the ADMIN's id. 
        # But 'autor' field is the username of the creator.
        # If the admin is adding a machine FOR someone else, we should probably get THAT user's links.
        # However, to stay consistent with original logic (which uses session user), we will keep it.
        # Wait, the original code validates 'autor' exists, but sets 'enlace_autor' based on 'user_id' (the logged in admin).
        # This seems like a bug in the original code or intended behavior where admin takes credit/provides links?
        # Let's stick to original behavior for now or improve it?
        # Original: user_id = session.get('user_id'); user_obj = User.query.get(user_id)
        # Let's keep it 1:1 for now to avoid side effects.
        
        user_id = session.get('user_id')
        user_obj = User.query.get(user_id)
        enlace_autor = ''
        if user_obj:
            if user_obj.youtube_url:
                enlace_autor = user_obj.youtube_url
            elif user_obj.github_url:
                enlace_autor = user_obj.github_url
            elif user_obj.linkedin_url:
                enlace_autor = user_obj.linkedin_url
        
        entorno_real = request.form.get('entorno_real')
        is_entorno_real = destino == 'bunker' and entorno_real
        
        if is_entorno_real:
            mandatory_fields = ['nombre', 'autor', 'fecha', 'descripcion', 'link_descarga']
        else:
            mandatory_fields = ['nombre', 'dificultad', 'autor', 'fecha', 'descripcion', 'link_descarga']

        missing = [f for f in mandatory_fields if not request.form.get(f)]
        if missing:
             return jsonify({'error': f'Faltan campos obligatorios: {", ".join(missing)}'}), 400

        try:
            fecha = datetime.strptime(fecha_raw, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return jsonify({'error': "Formato de fecha inválido."}), 400

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
            pin = (request.form.get('pin') or '').strip()
            entorno_real = request.form.get('entorno_real')
            
            if entorno_real:
                clase = "real"
                dificultad_texto = "Real"
                color = "#ffffff"
            
            try:
                new_bunker_machine = Machine(
                    nombre=nombre,
                    dificultad=dificultad_texto,
                    clase=clase,
                    color=color,
                    autor=autor,
                    enlace_autor=enlace_autor,
                    fecha=fecha,
                    imagen=imagen,
                    descripcion=descripcion,
                    link_descarga=link_descarga,
                    pin=pin,
                    origen='bunker'
                )
                alchemy_db.session.add(new_bunker_machine)
                alchemy_db.session.commit()
            except IntegrityError:
                alchemy_db.session.rollback()
                return jsonify({'error': "Ya existe una máquina con ese nombre."}), 400

        else:
            try:
                new_machine = Machine(
                    nombre=nombre,
                    dificultad=dificultad_texto,
                    clase=clase,
                    color=color,
                    autor=autor,
                    enlace_autor=enlace_autor,
                    fecha=fecha,
                    imagen=imagen,
                    descripcion=descripcion,
                    link_descarga=link_descarga,
                    origen='docker'
                )
                alchemy_db.session.add(new_machine)
                alchemy_db.session.commit()
                recalcular_ranking_creadores()
            except Exception:
                alchemy_db.session.rollback()
                return jsonify({'error': "Ya existe una máquina con ese nombre."}), 400

        return jsonify({'message': "Máquina añadida correctamente", 'success': True}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@maquinas_bp.route('/api/get_users', methods=['GET'])
@role_required('admin')
def get_users():
    """
    Get list of registered users.
    ---
    tags:
      - API
    responses:
      200:
        description: List of users.
    """
    from .models import User
    
    users = User.query.order_by(User.username.asc()).all()
    users_list = [{'id': u.id, 'username': u.username} for u in users]
    
    return jsonify({'users': users_list}), 200

@maquinas_bp.route('/api/maquinas', methods=['GET'])
@role_required('admin', 'moderador', 'jugador')
def api_get_maquinas():
    """
    Get list of machines for management (React).
    """
    current_username = (session.get('username') or '').strip()
    role = get_current_role()

    if role in ('admin', 'moderador'):
        maquinas_docker = Machine.query.filter_by(origen='docker').order_by(Machine.id.asc()).all()
        maquinas_bunker = Machine.query.filter_by(origen='bunker').order_by(Machine.id.asc()).all()
    else:
        if not current_username:
            maquinas_docker = []
            maquinas_bunker = []
        else:
            maquinas_docker = Machine.query.filter_by(origen='docker', autor=current_username).order_by(Machine.id.asc()).all()
            maquinas_bunker = Machine.query.filter_by(origen='bunker', autor=current_username).order_by(Machine.id.asc()).all()
            
    # Helper to serialize machine
    def serialize(m):
        return {
            'id': m.id,
            'nombre': m.nombre,
            'dificultad': m.dificultad,
            'autor': m.autor,
            'enlace_autor': m.enlace_autor,
            'fecha': m.fecha,
            'imagen': m.imagen,
            'descripcion': m.descripcion,
            'link_descarga': m.link_descarga,
            'guest_access': m.guest_access if hasattr(m, 'guest_access') else False,
            'origen': m.origen
        }

    return jsonify({
        'docker': [serialize(m) for m in maquinas_docker],
        'bunker': [serialize(m) for m in maquinas_bunker]
    }), 200


@maquinas_bp.route('/api/public/maquinas', methods=['GET'])
def api_get_public_maquinas():
    """
    Get public list of machines for Home Page (React).
    Includes 'completada' status for logged-in users.
    """
    current_username = (session.get('username') or '').strip()
    
    # 1. Fetch Machines
    maquinas_docker = Machine.query.filter_by(origen='docker').order_by(Machine.id.asc()).all()
    maquinas_bunker = Machine.query.filter_by(origen='bunker').order_by(Machine.id.asc()).all()
    
    # 2. Fetch Completed IDs if user is logged in
    completed_ids = set()
    if current_username:
        try:
            completes = CompletedMachine.query.filter_by(username=current_username).all()
            completed_ids = {c.machine_id for c in completes}
        except Exception:
            pass 
            
    # 3. Fetch Categories
    cats = Category.query.all()
    cat_map = {(c.origen, c.machine_id): c.categoria for c in cats}
    
    def serialize_public(m):
        return {
            'id': m.id,
            'nombre': m.nombre,
            'dificultad': m.dificultad,
            'clase': m.clase,
            'color': m.color,
            'autor': m.autor,
            'enlace_autor': m.enlace_autor,
            'fecha': m.fecha,
            'imagen': m.imagen,
            'descripcion': m.descripcion,
            'link_descarga': m.link_descarga,
            'guest_access': m.guest_access if hasattr(m, 'guest_access') else False,
            'origen': m.origen,
            'categoria': cat_map.get((m.origen, m.id), ''),
            'completada': m.id in completed_ids if current_username else False
        }

    return jsonify({
        'docker': [serialize_public(m) for m in maquinas_docker],
        'bunker': [serialize_public(m) for m in maquinas_bunker]
    }), 200


@maquinas_bp.route('/api/claims/<int:claim_id>/revert', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
def api_revert_claim(claim_id):
    """
    JSON API: Revert machine claim status.
    """
    try:
        claim = MachineClaim.query.get(claim_id)
        if claim:
            claim.estado = 'pendiente'
            alchemy_db.session.commit()
            return jsonify({'message': 'Reclamación revertida a pendiente.'}), 200
        return jsonify({'error': 'Reclamación no encontrada.'}), 404
    except Exception:
        alchemy_db.session.rollback()
        return jsonify({'error': 'Error al revertir la reclamación.'}), 500


@maquinas_bp.route('/api/machine-edit-requests/<int:request_id>/approve', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def api_approve_machine_edit(request_id):
    """
    JSON API: Approve machine edit request.
    """
    req = MachineEditRequest.query.get(request_id)

    if not req:
        return jsonify({'error': 'Solicitud no encontrada'}), 404

    try:
        nuevos = json.loads(req.nuevos_datos)
    except:
        nuevos = {}

    origen = req.origen
    machine_id = req.machine_id

    try:
        maquina = Machine.query.get(machine_id)
        if maquina:
            if novos_nombre := nuevos.get("nombre"): maquina.nombre = novos_nombre
            if novos_diff := nuevos.get("dificultad"): maquina.dificultad = novos_diff
            if novos_cls := nuevos.get("clase"): maquina.clase = novos_cls
            if novos_col := nuevos.get("color"): maquina.color = novos_col
            if novos_aut := nuevos.get("autor"): maquina.autor = novos_aut
            if novos_lnk := nuevos.get("enlace_autor"): maquina.enlace_autor = novos_lnk
            if novos_fec := nuevos.get("fecha"): maquina.fecha = novos_fec
            if novos_img := nuevos.get("imagen"): maquina.imagen = novos_img
            if novos_desc := nuevos.get("descripcion"): maquina.descripcion = novos_desc
            if novos_dl := nuevos.get("link_descarga"): maquina.link_descarga = novos_dl
            
            alchemy_db.session.commit()
            if origen == 'docker':
                recalcular_ranking_creadores()

        req.estado = 'aprobada'
        alchemy_db.session.commit()
        return jsonify({'message': 'Edición aprobada correctamente'}), 200
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({'error': str(e)}), 500


@maquinas_bp.route('/api/machine-edit-requests/<int:request_id>/reject', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def api_reject_machine_edit(request_id):
    """
    JSON API: Reject machine edit request.
    """
    req = MachineEditRequest.query.get(request_id)
    if req:
        try:
            req.estado = 'rechazada'
            alchemy_db.session.commit()
            return jsonify({'message': 'Edición rechazada'}), 200
        except Exception as e:
            alchemy_db.session.rollback()
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Solicitud no encontrada'}), 404


@maquinas_bp.route('/api/machine-edit-requests/<int:request_id>/revert', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
def api_revert_machine_edit(request_id):
    """
    JSON API: Revert machine edit request.
    """
    req = MachineEditRequest.query.get(request_id)
    if req:
        try:
            req.estado = 'pendiente'
            alchemy_db.session.commit()
            return jsonify({'message': 'Edición revertida a pendiente'}), 200
        except Exception as e:
            alchemy_db.session.rollback()
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Solicitud no encontrada'}), 404

@maquinas_bp.route('/api/rate_machine', methods=['POST'])
def rate_machine():
    """
    Rate a machine.
    ---
    tags:
      - Machines
    responses:
      200:
        description: Rating saved.
    """
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
        dificultad_score = float(dificultad_score)
        aprendizaje_score = float(aprendizaje_score)
        recomendaria_score = float(recomendaria_score)
        diversion_score = float(diversion_score)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Las puntuaciones deben ser números válidos'}), 400

    scores = [dificultad_score, aprendizaje_score, recomendaria_score, diversion_score]
    if any(score < 1 or score > 5 for score in scores):
        return jsonify({'success': False, 'message': 'Las puntuaciones deben estar entre 1 y 5'}), 400
    
    try:
        user_id = session['user_id']

        # completion_check removed to allow rating without completing
        # completion_check = CompletedMachine.query.filter_by(user_id=user_id, machine_name=maquina_nombre).first()
        
        # if not completion_check:
        #     return jsonify({
        #         'success': False, 
        #         'message': 'Debes completar la máquina antes de poder puntuarla'
        #     }), 403

        existing = Rating.query.filter_by(usuario_id=user_id, maquina_nombre=maquina_nombre).first()
        
        if existing:
            existing.dificultad_score = dificultad_score
            existing.aprendizaje_score = aprendizaje_score
            existing.recomendaria_score = recomendaria_score
            existing.diversion_score = diversion_score
            existing.fecha = datetime.utcnow()
        else:
            new_rating = Rating(
                usuario_id=user_id,
                maquina_nombre=maquina_nombre,
                dificultad_score=dificultad_score,
                aprendizaje_score=aprendizaje_score,
                recomendaria_score=recomendaria_score,
                diversion_score=diversion_score
            )
            alchemy_db.session.add(new_rating)
            
        alchemy_db.session.commit()
        return jsonify({'success': True, 'message': 'Puntuación guardada correctamente'})
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@maquinas_bp.route('/api/get_machine_rating/<maquina_nombre>')
def get_machine_rating(maquina_nombre):
    """
    Get machine rating.
    ---
    tags:
      - Machines
    parameters:
      - name: maquina_nombre
        in: path
        type: string
        required: true
    responses:
      200:
        description: Machine rating stats.
    """
                         
    from sqlalchemy import func
    
    avg_result = alchemy_db.session.query(
        func.avg(Rating.dificultad_score).label('avg_dificultad'),
        func.avg(Rating.aprendizaje_score).label('avg_aprendizaje'),
        func.avg(Rating.recomendaria_score).label('avg_recomendaria'),
        func.avg(Rating.diversion_score).label('avg_diversion'),
        func.count(Rating.id).label('count')
    ).filter_by(maquina_nombre=maquina_nombre).first()
    
    user_rating = None
    if 'user_id' in session:
        user_result = Rating.query.filter_by(usuario_id=session['user_id'], maquina_nombre=maquina_nombre).first()
        if user_result:
            user_rating = {
                'dificultad': user_result.dificultad_score,
                'aprendizaje': user_result.aprendizaje_score,
                'recomendaria': user_result.recomendaria_score,
                'diversion': user_result.diversion_score
            }

    count = avg_result.count if avg_result else 0
    total_avg = 0
    if count > 0:
        criteria_sum = (avg_result.avg_dificultad or 0) +                       (avg_result.avg_aprendizaje or 0) +                       (avg_result.avg_recomendaria or 0) +                       (avg_result.avg_diversion or 0)
        total_avg = criteria_sum / 4
    
    return jsonify({
        'average': round(total_avg, 1),
        'count': count,
        'details': {
            'dificultad': round(avg_result.avg_dificultad or 0, 1) if count > 0 else 0,
            'aprendizaje': round(avg_result.avg_aprendizaje or 0, 1) if count > 0 else 0,
            'recomendaria': round(avg_result.avg_recomendaria or 0, 1) if count > 0 else 0,
            'diversion': round(avg_result.avg_diversion or 0, 1) if count > 0 else 0
        },
        'user_rating': user_rating
    })

@maquinas_bp.route('/api/maquinas-hechas', methods=['GET'])
@role_required('admin', 'moderador', 'jugador')
def api_maquinas_hechas():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    results = alchemy_db.session.query(
        CompletedMachine.machine_name,
        CompletedMachine.completed_at,
        Machine.dificultad,
        Machine.color,
        Machine.imagen,
        Machine.clase,
        Machine.autor
    ).outerjoin(Machine, CompletedMachine.machine_name == Machine.nombre) \
     .filter(CompletedMachine.user_id == user_id) \
     .order_by(CompletedMachine.completed_at.desc()).all()

    completed_machines = []
    for row in results:
        completed_at_str = row.completed_at.isoformat() if row.completed_at else None
        completed_machines.append({
            "machine_name": row.machine_name,
            "completed_at": completed_at_str,
            "dificultad": row.dificultad,
            "color": row.color, # Keep backend color if consistent, or map in frontend
            "imagen": row.imagen,
            "clase": row.clase,
            "autor": row.autor
        })
    
    total_machines = Machine.query.filter_by(origen='docker').count()
    completed_count = len(completed_machines)
    completion_percentage = round((completed_count / total_machines * 100), 1) if total_machines > 0 else 0
    
    return jsonify({
        'completed_machines': completed_machines,
        'total_machines': total_machines,
        'completed_count': completed_count,
        'completion_percentage': completion_percentage
    }), 200

@maquinas_bp.route('/api/completed_machines/<machine_name>', methods=['GET'])
@role_required('admin', 'moderador', 'jugador')
@limiter.limit("60 per minute")
def check_completed_machine(machine_name):
                                                                
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    completed = CompletedMachine.query.filter_by(user_id=user_id, machine_name=machine_name).first()
    
    return jsonify({'completed': completed is not None}), 200

@maquinas_bp.route('/api/toggle_completed_machine', methods=['POST'])
@role_required('admin', 'moderador', 'jugador')
@csrf_protect
@limiter.limit("30 per minute", methods=["POST"])
def api_toggle_completed_machine():
                                                
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated', 'success': False}), 401
    
    data = request.json or {}
    machine_name = (data.get('machine_name') or '').strip()
    
    if not machine_name:
        return jsonify({'error': 'Machine name required', 'success': False}), 400

    machine_exists = Machine.query.filter_by(nombre=machine_name).first()
    if not machine_exists:

        pass
        
    if not machine_exists:

        return jsonify({'error': 'Máquina no válida', 'success': False}), 400

    existing = CompletedMachine.query.filter_by(user_id=user_id, machine_name=machine_name).first()
    
    if existing:
                           
        alchemy_db.session.delete(existing)
        alchemy_db.session.commit()
        return jsonify({'success': True, 'completed': False}), 200
    else:
                        
        new_comp = CompletedMachine(user_id=user_id, machine_name=machine_name)
        alchemy_db.session.add(new_comp)
        alchemy_db.session.commit()
        return jsonify({'success': True, 'completed': True}), 200




@maquinas_bp.route('/api/maquina', methods=['PUT'])
@role_required('admin', 'moderador', 'jugador')
@csrf_protect
def api_update_maquina():
    """
    Update machine details via API.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        maquina_id = data.get('id')
        origen = (data.get('origen') or '').strip()
        
        if not maquina_id or origen not in ('docker', 'bunker'):
            return jsonify({'error': 'Invalid ID or origin'}), 400
            
        maquina_id = int(maquina_id)
        
        if origen == 'docker':
            maquina = Machine.query.get(maquina_id)
        else:
            maquina = Machine.query.get(maquina_id)
            
        if not maquina:
            return jsonify({'error': 'Machine not found'}), 404
            
        # Permission check
        role = get_current_role()
        username = (session.get('username') or '').strip()
        
        if role not in ('admin', 'moderador'):
             if role == 'jugador' and maquina.autor == username:
                 pass 
             else:
                 return jsonify({'error': 'Unauthorized'}), 403

        # Update fields
        maquina.nombre = data.get('nombre', maquina.nombre).strip()
        maquina.dificultad = data.get('dificultad', maquina.dificultad).strip()
        
        # Difficulty color mapping
        difficulty_map = {
            'Muy Fácil': {'color': '#43959b', 'clase': 'muy-facil'},
            'Fácil': {'color': '#8bc34a', 'clase': 'facil'},
            'Medio': {'color': '#e0a553', 'clase': 'medio'},
            'Difícil': {'color': '#d83c31', 'clase': 'dificil'}
        }
        mapping = difficulty_map.get(maquina.dificultad, {'color': '#8bc34a', 'clase': 'facil'})
        maquina.clase = mapping['clase']
        maquina.color = mapping['color']

        maquina.autor = data.get('autor', maquina.autor).strip()
        maquina.enlace_autor = data.get('enlace_autor', maquina.enlace_autor).strip()
        maquina.fecha = data.get('fecha', maquina.fecha).strip()
        maquina.descripcion = data.get('descripcion', maquina.descripcion).strip()
        maquina.link_descarga = data.get('link_descarga', maquina.link_descarga).strip()
        
        alchemy_db.session.commit()
        
        # Update category
        categoria = data.get('categoria', '').strip()
        cat_obj = Category.query.filter_by(machine_id=maquina_id, origen=origen).first()
        if categoria:
            if cat_obj:
                cat_obj.categoria = categoria
            else:
                new_cat = Category(machine_id=maquina_id, origen=origen, categoria=categoria)
                alchemy_db.session.add(new_cat)
        else:
            if cat_obj:
                alchemy_db.session.delete(cat_obj)
        
        alchemy_db.session.commit()
        
        # Recalculate ranking if docker
        if origen == 'docker':
            recalcular_ranking_creadores()
            
        return jsonify({'success': True}), 200
        
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({'error': str(e)}), 500

@maquinas_bp.route('/api/maquina', methods=['DELETE'])
@role_required('admin', 'moderador', 'jugador')
@csrf_protect
def api_delete_maquina():
    """
    Delete a machine via API.
    """
    try:
        data = request.get_json()
        maquina_id = data.get('id')
        origen = (data.get('origen') or '').strip()
        
        if not maquina_id or origen not in ('docker', 'bunker'):
             return jsonify({'error': 'Invalid parameters'}), 400
             
        maquina_id = int(maquina_id)
        maquina = Machine.query.get(maquina_id)
        
        if not maquina:
            return jsonify({'error': 'Machine not found'}), 404
            
        # Permission check
        role = get_current_role()
        username = (session.get('username') or '').strip()
        
        if role not in ('admin', 'moderador') and not (role == 'jugador' and maquina.autor == username):
            return jsonify({'error': 'Unauthorized'}), 403
            
        # Delete logic
        if origen == 'docker':
             alchemy_db.session.delete(maquina)
             alchemy_db.session.commit()
             recalcular_ranking_creadores()
        else:
             from bunkerlabs.models import BunkerSolve
             BunkerSolve.query.filter_by(machine_id=maquina_id).delete()
             alchemy_db.session.delete(maquina)
             alchemy_db.session.commit()
             
        return jsonify({'success': True}), 200

    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({'error': str(e)}), 500

