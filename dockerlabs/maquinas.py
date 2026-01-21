import os
import json
from datetime import datetime
from urllib.parse import urlparse, urljoin
from sqlalchemy.exc import IntegrityError
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash, current_app
from werkzeug.utils import secure_filename
from .decorators import role_required, csrf_protect, get_current_role
from bunkerlabs.extensions import limiter
from . import validators
from .models import Machine, Category, CreatorRanking, MachineClaim, MachineEditRequest, Rating, CompletedMachine
from bunkerlabs.models import BunkerMachine
from .extensions import db as alchemy_db

maquinas_bp = Blueprint('maquinas', __name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MACHINE_LOGOS_FOLDER = os.path.join(BASE_DIR, 'static', 'images', 'logos')
LOGO_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'images', 'logos')
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

@maquinas_bp.route('/gestion-maquinas')
@role_required('admin', 'moderador', 'jugador')
def gestion_maquinas():
    """
    Machine management dashboard.
    ---
    tags:
      - Machines
    responses:
      200:
        description: List of machines.
    """
    current_username = (session.get('username') or '').strip()
    role = get_current_role()

    if role in ('admin', 'moderador'):
        maquinas_docker = Machine.query.order_by(Machine.id.asc()).all()
                                     
        maquinas_bunker = BunkerMachine.query.order_by(BunkerMachine.id.asc()).all()
    else:
        if not current_username:
            maquinas_docker = []
            maquinas_bunker = []
        else:
            maquinas_docker = Machine.query.filter_by(autor=current_username).order_by(Machine.id.asc()).all()
                                                     
            maquinas_bunker = BunkerMachine.query.filter_by(autor=current_username).order_by(BunkerMachine.id.asc()).all()

    categorias_map = {}
    if maquinas_docker:
                                              
        docker_cats = Category.query.filter_by(origen='docker').all()
        docker_cats_lookup = {c.machine_id: c.categoria for c in docker_cats}
        
        for m in maquinas_docker:
            categorias_map[('docker', m.id)] = docker_cats_lookup.get(m.id, '')
    
    if maquinas_bunker:
                                                                                             
        bunker_ids = [m.id for m in maquinas_bunker]                                   
        if bunker_ids:
            bunker_cats = Category.query.filter(
                Category.origen == 'bunker',
                Category.machine_id.in_(bunker_ids)
            ).all()
            
            bunker_cats_lookup = {c.machine_id: c.categoria for c in bunker_cats}
            
            for m in maquinas_bunker:
                categorias_map[('bunker', m.id)] = bunker_cats_lookup.get(m.id, '')

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
    """
    Update machine details.
    ---
    tags:
      - Machines
    responses:
      302:
        description: Redirect to management page.
    """
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
        maquina = Machine.query.get(maquina_id)
    else:
                            
        maquina = BunkerMachine.query.get(maquina_id)

    if maquina is None:
        return redirect(url_for('maquinas.gestion_maquinas'))

    role = get_current_role()
    username = (session.get('username') or '').strip()

    maquina_autor = maquina.autor

    if role not in ('admin', 'moderador'):
        if role == 'jugador' and maquina_autor == username:
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

            try:
                edit_request = MachineEditRequest(
                    machine_id=maquina_id,
                    origen=origen,
                    autor=username,
                    nuevos_datos=nuevos_datos,
                    estado='pendiente'
                )
                alchemy_db.session.add(edit_request)
                alchemy_db.session.commit()
            except Exception as e:
                alchemy_db.session.rollback()
                                                                                          
                pass

            return redirect(url_for('maquinas.gestion_maquinas'))

        return render_template('403.html'), 403

    try:
        if origen == 'docker':
                            
            maquina.nombre = nombre
            maquina.dificultad = dificultad
            maquina.clase = clase
            maquina.color = color
            maquina.autor = autor
            maquina.enlace_autor = enlace_autor
            maquina.fecha = fecha
            maquina.imagen = imagen
            maquina.descripcion = descripcion
            maquina.link_descarga = link_descarga
            
            alchemy_db.session.commit()

            cat_obj = Category.query.filter_by(machine_id=maquina_id, origen='docker').first()
            if categoria:
                if cat_obj:
                    cat_obj.categoria = categoria
                else:
                    new_cat = Category(machine_id=maquina_id, origen='docker', categoria=categoria)
                    alchemy_db.session.add(new_cat)
            else:
                if cat_obj:
                    alchemy_db.session.delete(cat_obj)
            
            alchemy_db.session.commit()
            
            recalcular_ranking_creadores()

        else:
                                    
            maquina.nombre = nombre
            maquina.dificultad = dificultad
            maquina.clase = clase
            maquina.color = color
            maquina.autor = autor
            maquina.enlace_autor = enlace_autor
            maquina.fecha = fecha
            maquina.imagen = imagen
            maquina.descripcion = descripcion
            maquina.link_descarga = link_descarga
            
            alchemy_db.session.commit()

            cat_obj = Category.query.filter_by(machine_id=maquina_id, origen='bunker').first()
            if categoria:
                if cat_obj:
                    cat_obj.categoria = categoria
                else:
                    new_cat = Category(machine_id=maquina_id, origen='bunker', categoria=categoria)
                    alchemy_db.session.add(new_cat)
            else:
                if cat_obj:
                    alchemy_db.session.delete(cat_obj)
            
            alchemy_db.session.commit()

    except Exception:
        alchemy_db.session.rollback()
        pass

    return redirect(url_for('maquinas.gestion_maquinas'))

@maquinas_bp.route('/gestion-maquinas/eliminar', methods=['POST'])
@role_required('admin', 'moderador', 'jugador')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"]) 
def eliminar_maquina():
    """
    Delete a machine.
    ---
    tags:
      - Machines
    responses:
      302:
        description: Redirect to management page.
    """
    origen = (request.form.get('origen') or '').strip()
    maquina_id = request.form.get('id')

    if not maquina_id or origen not in ('docker', 'bunker'):
        return redirect(url_for('maquinas.gestion_maquinas'))

    try:
        maquina_id = int(maquina_id)
    except ValueError:
        return redirect(url_for('maquinas.gestion_maquinas'))

    if origen == 'docker':
        maquina = Machine.query.get(maquina_id)
                                                                         
    else:
                            
        maquina = BunkerMachine.query.get(maquina_id)

    if maquina is None:
        return redirect(url_for('maquinas.gestion_maquinas'))

    role = get_current_role()
    maquina_autor = maquina.autor
    
    if role not in ('admin', 'moderador') and not (role == 'jugador' and maquina_autor == username):
        return render_template('403.html'), 403

    try:
        if origen == 'bunker':
             # Eliminar BunkerSolve asociados
             from bunkerlabs.models import BunkerSolve
             BunkerSolve.query.filter_by(machine_id=maquina_id).delete()

        imagen_path = maquina.imagen
        # No eliminar logo.png ya que es el logo por defecto compartido de la web
        if origen == 'bunker' and imagen_path:
            # Verificar que no sea logo.png (con o sin ruta)
            nombre_archivo = os.path.basename(imagen_path) if imagen_path else ''
            if nombre_archivo and nombre_archivo.lower() != 'logo.png':
                full_image_path = os.path.join(BASE_DIR, 'static', 'images', imagen_path)
                if os.path.exists(full_image_path):
                    try:
                        os.remove(full_image_path)
                    except Exception as e:
                        print(f"Warning: Could not delete image {full_image_path}: {e}")
        
        if origen == 'docker':
            alchemy_db.session.delete(maquina)
            alchemy_db.session.commit()
            recalcular_ranking_creadores()
        else:
            # Eliminar BunkerSolve asociados
            from bunkerlabs.models import BunkerSolve
            BunkerSolve.query.filter_by(machine_id=maquina_id).delete()
            
            alchemy_db.session.delete(maquina)
            alchemy_db.session.commit()
    except Exception:
        alchemy_db.session.rollback()
        pass

    return redirect(url_for('maquinas.gestion_maquinas'))

@maquinas_bp.route('/gestion-maquinas/toggle-guest-access', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("10 per minute", methods=["POST"])
def toggle_guest_access():
    """
    Toggle guest access for a BunkerLabs machine.
    """
    maquina_id = request.form.get('id')
    
    if not maquina_id:
        return jsonify({'error': 'ID de máquina requerido'}), 400
        
    try:
        maquina_id = int(maquina_id)
        maquina = BunkerMachine.query.get(maquina_id)
        
        if not maquina:
            return jsonify({'error': 'Máquina no encontrada'}), 404
            
        maquina.guest_access = not maquina.guest_access
        alchemy_db.session.commit()
        
        return jsonify({
            'message': 'Estado actualizado',
            'guest_access': maquina.guest_access
        }), 200
        
    except ValueError:
        return jsonify({'error': 'ID inválido'}), 400
    except Exception as e:
        alchemy_db.session.rollback()
        return jsonify({'error': str(e)}), 500

@maquinas_bp.route('/gestion-maquinas/upload-logo', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("10 per minute", methods=["POST"])
def upload_machine_logo():
    """
    Upload machine logo.
    ---
    tags:
      - Machines
    consumes:
      - multipart/form-data
    parameters:
      - name: logo
        in: formData
        type: file
        required: true
    responses:
      200:
        description: Logo uploaded.
      400:
        description: Invalid input or file.
    """
                                           
    from PIL import Image
    import tempfile
    
    machine_id = request.form.get('machine_id')
    origen = request.form.get('origen', '').strip()
    
    if not machine_id or origen not in ('docker', 'bunker'):
        return jsonify({'error': 'Datos inválidos'}), 400
    
    file = request.files.get('logo')
    if not file or file.filename == '':
        return jsonify({'error': 'No se ha enviado ningún archivo'}), 400

    if not file.mimetype.startswith('image/'):
        return jsonify({'error': 'El archivo debe ser una imagen'}), 400

    MAX_SIZE = 2 * 1024 * 1024
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    if file_length > MAX_SIZE:
        return jsonify({'error': 'La imagen es demasiado grande (máx 2MB)'}), 400
    file.seek(0)

    valid, error = validators.validate_image_content(file.stream)
    if not valid:
        return jsonify({'error': f'Imagen inválida: {error}'}), 400

    original_filename = secure_filename(file.filename or '')
    _, ext = os.path.splitext(original_filename)
    ext = ext.lower()
    
    if ext not in ALLOWED_LOGO_EXTENSIONS:
        return jsonify({'error': 'Formato de imagen no permitido'}), 400

    if origen == 'bunker':
                            
        maquina = BunkerMachine.query.get(machine_id)
        if maquina:
            nombre_seguro = secure_filename(maquina.nombre)
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

    os.makedirs(upload_folder, exist_ok=True)
    
    save_path = os.path.join(upload_folder, final_filename)

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
    """
    Add a new machine.
    ---
    tags:
      - Machines
    responses:
      200:
        description: Add machine page.
      302:
        description: machine added, redirect.
    """
    error = None

    if request.method == 'POST':
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
                error = "El autor seleccionado no es un usuario registrado válido."


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
                     imagen = "logos/logo.png"                                  
                else:
                     imagen = "logos/logo.png"

        # Obtener enlace_autor desde el perfil del usuario
        user_id = session.get('user_id')
        user_obj = User.query.get(user_id)
        enlace_autor = ''
        if user_obj:
            # Priorizar YouTube, luego GitHub, luego LinkedIn
            if user_obj.youtube_url:
                enlace_autor = user_obj.youtube_url
            elif user_obj.github_url:
                enlace_autor = user_obj.github_url
            elif user_obj.linkedin_url:
                enlace_autor = user_obj.linkedin_url
        
        if not enlace_autor:
            enlace_autor = current_user.youtube_url or current_user.github_url or current_user.linkedin_url or ''

        # Validación de campos obligatorios
        # Si es entorno real (bunker + entorno_real marcado), no se requiere dificultad
        entorno_real = request.form.get('entorno_real')
        is_entorno_real = destino == 'bunker' and entorno_real
        
        if is_entorno_real:
            # Para entornos reales no se requiere dificultad
            mandatory_fields = ['nombre', 'autor', 'fecha', 'descripcion', 'link_descarga']
        else:
            # Para máquinas normales se requiere dificultad
            mandatory_fields = ['nombre', 'dificultad', 'autor', 'fecha', 'descripcion', 'link_descarga']

        missing = [f for f in mandatory_fields if not request.form.get(f)]
        if missing:
            return jsonify({'error': f'Faltan campos obligatorios: {", ".join(missing)}'}), 400

        if error is None:
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
                pin = (request.form.get('pin') or '').strip()
                # Verificar si se marcó como Entorno Real
                entorno_real = request.form.get('entorno_real')
                
                # Si es entorno real, sobrescribir clase y dificultad
                if entorno_real:
                    clase = "real"
                    dificultad_texto = "Real"
                    color = "#ffffff"  # Blanco para entornos reales
                
                try:
                                        
                    new_bunker_machine = BunkerMachine(
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
                        pin=pin
                    )
                    alchemy_db.session.add(new_bunker_machine)
                    alchemy_db.session.commit()
                except IntegrityError:
                    alchemy_db.session.rollback()
                    error = "Ya existe una máquina con ese nombre."

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
                        link_descarga=link_descarga
                    )
                    alchemy_db.session.add(new_machine)
                    alchemy_db.session.commit()
                    recalcular_ranking_creadores()
                except Exception:                            
                    alchemy_db.session.rollback()
                    error = "Ya existe una máquina con ese nombre."

        if error is None:
            if destino == 'bunker':
                return redirect(url_for('bunkerlabs.bunkerlabs_home'))
            else:
                return redirect(url_for('index'))

    return render_template('add-maquina.html', error=error)

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


@maquinas_bp.route('/reclamar-maquina', methods=['POST'])
@role_required('jugador', 'admin', 'moderador')
@csrf_protect
@limiter.limit("5 per hour")
def reclamar_maquina():
    """
    Claim machine authorship.
    ---
    tags:
      - Machines
    responses:
      302:
        description: Redirect to dashboard.
    """
    maquina_nombre = (request.form.get('maquina_nombre') or '').strip()
    contacto = (request.form.get('contacto') or '').strip()
    prueba = (request.form.get('prueba') or '').strip()
    
    if not maquina_nombre or not contacto or not prueba:
        return redirect(url_for('dashboard'))

    valid, _ = validators.validate_machine_name(maquina_nombre)
    if not valid:
                                                                                       
        return redirect(url_for('dashboard'))
    
    user_id = session.get('user_id')
    username = (session.get('username') or '').strip()
    
    try:
        new_claim = MachineClaim(
            user_id=user_id,
            username=username,
            maquina_nombre=maquina_nombre,
            contacto=contacto,
            prueba=prueba,
            estado='pendiente'
        )
        alchemy_db.session.add(new_claim)
        alchemy_db.session.commit()
    except Exception:
        alchemy_db.session.rollback()
        
    return redirect(url_for('dashboard'))

@maquinas_bp.route('/claims/<int:claim_id>/approve', methods=['POST'])
@role_required('admin')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def approve_claim(claim_id):
    """
    Approve machine claim.
    ---
    tags:
      - Admin
    responses:
      302:
        description: Redirect to dashboard.
    """
    claim = MachineClaim.query.get(claim_id)
    if not claim:
        return redirect(url_for('dashboard'))

    try:
        maquina = Machine.query.filter_by(nombre=claim.maquina_nombre).first()
        if maquina:
            maquina.autor = claim.username
            
        claim.estado = 'aprobada'
        
        alchemy_db.session.commit()
        recalcular_ranking_creadores()
        
    except Exception:
        alchemy_db.session.rollback()

    return redirect(url_for('dashboard'))

@maquinas_bp.route('/claims/<int:claim_id>/reject', methods=['POST'])
@role_required('admin')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def reject_claim(claim_id):
    """
    Reject machine claim.
    ---
    tags:
      - Admin
    responses:
      302:
        description: Redirect to dashboard.
    """
    claim = MachineClaim.query.get(claim_id)
    if claim:
        try:
            alchemy_db.session.delete(claim)
            alchemy_db.session.commit()
        except:
            alchemy_db.session.rollback()

    return redirect(url_for('dashboard'))

@maquinas_bp.route('/claims/<int:claim_id>/revert', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
def revert_claim(claim_id):
    """
    Revert machine claim status.
    ---
    tags:
      - Admin
    responses:
      302:
        description: Redirect to petitions.
    """
    claim = MachineClaim.query.get(claim_id)
    if claim:
        claim.estado = 'pendiente'
        alchemy_db.session.commit()
    return redirect(url_for('peticiones'))

@maquinas_bp.route('/machine-edit-requests/<int:request_id>/approve', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def approve_machine_edit(request_id):
    """
    Approve machine edit request.
    ---
    tags:
      - Admin
    responses:
      302:
        description: Redirect to petitions.
    """
    req = MachineEditRequest.query.get(request_id)

    if not req:
        return redirect(url_for('peticiones'))

    try:
        nuevos = json.loads(req.nuevos_datos)
    except:
        nuevos = {}

    origen = req.origen
    machine_id = req.machine_id

    if origen == 'docker':
                 
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
            recalcular_ranking_creadores()

    else:
                                      
        maquina = BunkerMachine.query.get(machine_id)
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

    req.estado = 'aprobada'
    alchemy_db.session.commit()

    return redirect(url_for('peticiones'))

@maquinas_bp.route('/machine-edit-requests/<int:request_id>/reject', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"])
def reject_machine_edit(request_id):
    """
    Reject machine edit request.
    ---
    tags:
      - Admin
    responses:
      302:
        description: Redirect to petitions.
    """
    req = MachineEditRequest.query.get(request_id)
    if req:
        req.estado = 'rechazada'
        alchemy_db.session.commit()
    return redirect(url_for('peticiones'))

@maquinas_bp.route('/machine-edit-requests/<int:request_id>/revert', methods=['POST'])
@role_required('admin', 'moderador')
@csrf_protect
def revert_machine_edit(request_id):
    """
    Revert machine edit request.
    ---
    tags:
      - Admin
    responses:
      302:
        description: Redirect to petitions.
    """
    req = MachineEditRequest.query.get(request_id)
    if req:
        req.estado = 'pendiente'
        alchemy_db.session.commit()
    return redirect(url_for('peticiones'))

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

@maquinas_bp.route('/maquinas-hechas')
@role_required('admin', 'moderador', 'jugador')
def maquinas_hechas():
                                        
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    results = alchemy_db.session.query(
        CompletedMachine.machine_name,
        CompletedMachine.completed_at,
        Machine.dificultad,
        Machine.color,
        Machine.imagen,
        Machine.clase,
        Machine.autor
    ).outerjoin(Machine, CompletedMachine.machine_name == Machine.nombre)     .filter(CompletedMachine.user_id == user_id)     .order_by(CompletedMachine.completed_at.desc()).all()

    completed_machines = []
    for row in results:

        completed_at_str = row.completed_at.isoformat() if row.completed_at else None
        
        completed_machines.append({
            "machine_name": row.machine_name,
            "completed_at": completed_at_str,
            "dificultad": row.dificultad,
            "color": row.color,
            "imagen": row.imagen,
            "clase": row.clase,
            "autor": row.autor
        })
    
    total_machines = Machine.query.count()
    completed_count = len(completed_machines)
    completion_percentage = round((completed_count / total_machines * 100), 1) if total_machines > 0 else 0
    
    return render_template(
        'maquinas_hechas.html', 
        completed_machines=completed_machines,
        total_machines=total_machines,                                                                                             
        completed_count=completed_count,
        completion_percentage=completion_percentage
    )
