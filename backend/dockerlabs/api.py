import os
from flask import Blueprint, jsonify, url_for, session, request
from .auth import get_profile_image_static_path
from bunkerlabs.extensions import limiter

api_bp = Blueprint('api', __name__)

@api_bp.route('/api', methods=['GET'])
@limiter.limit("60 per minute", methods=["GET"])
def api_summary():
    """
    Obtener resumen de máquinas, creadores y writeups.
    ---
    tags:
      - API Pública
    responses:
      200:
        description: Diccionario con datos del resumen.
    """
    from .models import Machine, CreatorRanking, WriteupRanking, Writeup
    from sqlalchemy import func

    maquinas_objs = Machine.query.filter_by(origen='docker').order_by(Machine.id.asc()).all()
    info_maquinas = []
    maquinas_names = []
    for m in maquinas_objs:
        d = {
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
            'link_descarga': m.link_descarga
        }
        if d['imagen']:
             d['imagen_url'] = url_for('static', filename=f"dockerlabs/{d['imagen']}", _external=True)
        info_maquinas.append(d)
        maquinas_names.append(d['nombre'])

    creadores_objs = CreatorRanking.query.order_by(CreatorRanking.maquinas.desc(), func.lower(CreatorRanking.nombre).asc()).all()
    ranking_creadores = [{'id': r.id, 'nombre': r.nombre, 'maquinas': r.maquinas} for r in creadores_objs]

    ranking_w_objs = WriteupRanking.query.order_by(WriteupRanking.puntos.desc(), func.lower(WriteupRanking.nombre).asc()).all()
    ranking_writeups = [{'id': r.id, 'nombre': r.nombre, 'puntos': r.puntos} for r in ranking_w_objs]

    writeups_objs = Writeup.query.order_by(Writeup.created_at.desc()).all()
    writeups_textos = []
    writeups_videos = []
    for w in writeups_objs:
        d = {
            'id': w.id,
            'maquina': w.maquina,
            'autor': w.autor,
            'url': w.url,
            'tipo': w.tipo,
            'created_at': w.created_at
        }
        if w.tipo == 'texto':
            writeups_textos.append(d)
        else:
            writeups_videos.append(d)

    total_creadores = len(ranking_creadores)
    total_puntos = sum(r['puntos'] for r in ranking_writeups)
    total_writeups = len(writeups_objs)

    metadata = {
        "total_creadores": total_creadores,
        "total_puntos": total_puntos,
        "total_writeups": total_writeups
    }

    response = {
        "info_maquinas": info_maquinas,
        "maquinas": maquinas_names,
        "metadata": metadata,
        "ranking_creadores": ranking_creadores,
        "ranking_writeups": ranking_writeups,
        "writeups": {
            "textos": writeups_textos,
            "videos": writeups_videos
        }
    }

    return jsonify(response), 200

@api_bp.route('/api/user/info', methods=['GET'])
@limiter.limit("60 per minute", methods=["GET"])
def api_user_info():
    """
    Get current user information.
    ---
    tags:
      - User
    responses:
      200:
        description: User profile and stats.
      401:
        description: User not authenticated.
      404:
        description: User not found.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "No has iniciado sesión", "is_authenticated": False}), 401

    from .models import User, CompletedMachine, Writeup

    user = User.query.get(user_id)
    if not user:
         return jsonify({"error": "Usuario no encontrado", "is_authenticated": False}), 404

    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'created_at': user.created_at.isoformat() if getattr(user, 'created_at', None) else None,
        'biography': user.biography,
        'linkedin_url': user.linkedin_url,
        'github_url': user.github_url,
        'youtube_url': user.youtube_url,
        'profile_image': get_profile_image_static_path(user.username, user.id),
    }

    static_path = get_profile_image_static_path(user.username, user_id=user.id)
    if static_path is None:
        static_path = 'dockerlabs/images/balu.webp'
    
    user_data['profile_image_url'] = url_for('static', filename=static_path, _external=True)

    completed_objs = CompletedMachine.query.filter_by(user_id=user_id).order_by(CompletedMachine.completed_at.desc()).all()
    completed_machines = [{'machine_name': c.machine_name, 'completed_at': c.completed_at} for c in completed_objs]

    writeups_objs = Writeup.query.filter_by(autor=user.username).order_by(Writeup.created_at.desc()).all()
    writeups = [{
        'maquina': w.maquina,
        'url': w.url,
        'tipo': w.tipo,
        'created_at': w.created_at
    } for w in writeups_objs]

    response = {
        "is_authenticated": True,
        'user': user_data,
        'completed_machines': completed_machines,
        'submitted_writeups': writeups
    }

    return jsonify(response), 200

@api_bp.route('/api/me', methods=['GET'])
@limiter.limit("60 per minute", methods=["GET"])
def api_me():
    """Alias for /api/user/info (used by React)."""
    return api_user_info()

@api_bp.route('/api/ranking_autores', methods=['GET'])
@limiter.limit("60 per minute", methods=["GET"])
def api_ranking_autores():
    """
    Obtener ranking de creadores de máquinas.
    ---
    tags:
      - API Pública
    responses:
      200:
        description: Lista de creadores ordenados por cantidad de máquinas.
    """

    from .models import CreatorRanking, User
    from .extensions import db as alchemy_db
    from sqlalchemy import func

    results = alchemy_db.session.query(
        CreatorRanking, User
    ).outerjoin(User, func.lower(User.username) == func.lower(CreatorRanking.nombre))     .order_by(CreatorRanking.maquinas.desc(), func.lower(CreatorRanking.nombre).asc())     .all()
    
    response_list = []
    for creator, user in results:
        r = {
            'id': creator.id,
            'nombre': creator.nombre,
            'maquinas': creator.maquinas,
            'autor': creator.nombre                
        }

        user_id = user.id if user else None
        static_path = get_profile_image_static_path(r['autor'], user_id=user_id)
        
        if static_path:
             r['imagen'] = url_for('static', filename=static_path, _external=True)
        else:
             r['imagen'] = url_for('static', filename='dockerlabs/images/balu.webp', _external=True)

        response_list.append(r)

    return jsonify(response_list), 200

@api_bp.route('/api/ranking_writeups', methods=['GET'])
@limiter.limit("60 per minute", methods=["GET"])
def api_ranking_writeups():
    """
    Obtener ranking de autores de writeups.
    ---
    tags:
      - API Pública
    responses:
      200:
        description: Lista de usuarios ordenados por puntos de writeup.
    """

    from .models import WriteupRanking, User
    from .extensions import db as alchemy_db
    from sqlalchemy import func
    
    results = alchemy_db.session.query(
        WriteupRanking, User
    ).outerjoin(User, func.lower(User.username) == func.lower(WriteupRanking.nombre))     .order_by(WriteupRanking.puntos.desc(), func.lower(WriteupRanking.nombre).asc())     .all()
    
    response_list = []
    for rank, user in results:
        r = {
            'id': rank.id,
            'nombre': rank.nombre,
            'puntos': rank.puntos
        }
        
        author_name = rank.nombre
        user_id = user.id if user else None
        
        if author_name:
            static_path = get_profile_image_static_path(author_name, user_id=user_id)
            if static_path:
                r['imagen_url'] = url_for('static', filename=static_path, _external=True)
            else:
                r['imagen_url'] = url_for('static', filename='dockerlabs/images/balu.webp', _external=True)
        else:
             r['imagen_url'] = url_for('static', filename='dockerlabs/images/balu.webp', _external=True)

        response_list.append(r)

    return jsonify(response_list), 200


@api_bp.route('/api/estadisticas', methods=['GET'])
@limiter.limit("30 per minute", methods=["GET"])
def api_estadisticas():
    """
    Estadísticas de la plataforma (máquinas, writeups, usuarios por año) para el frontend React.
    ---
    tags:
      - API Pública
    responses:
      200:
        description: machine_stats, writeup_stats, user_stats (porcentajes por año).
    """
    from .models import Machine, Writeup, User
    from datetime import datetime
    from collections import defaultdict

    def get_distribution_by_year(items, date_extractor):
        year_counts = defaultdict(int)
        total = 0
        for item in items:
            try:
                year = date_extractor(item)
                if year:
                    year_counts[year] += 1
                    total += 1
            except Exception:
                continue
        distribution = {}
        if total > 0:
            for year, count in year_counts.items():
                distribution[year] = round((count / total) * 100, 2)
        return dict(sorted(distribution.items()))

    machines = Machine.query.all()
    def machine_date_extractor(m):
        if not m.fecha:
            return None
        try:
            return datetime.strptime(m.fecha, "%d/%m/%Y").year
        except (ValueError, TypeError):
            return None

    writeups = Writeup.query.all()
    def writeup_date_extractor(w):
        return w.created_at.year if w.created_at else None

    users = User.query.all()
    def user_date_extractor(u):
        return u.created_at.year if u.created_at else None

    machine_stats = get_distribution_by_year(machines, machine_date_extractor)
    writeup_stats = get_distribution_by_year(writeups, writeup_date_extractor)
    user_stats = get_distribution_by_year(users, user_date_extractor)

    return jsonify({
        "machine_stats": machine_stats,
        "writeup_stats": writeup_stats,
        "user_stats": user_stats
    }), 200


@api_bp.route('/api/maquinas', methods=['GET'])
@limiter.limit("60 per minute", methods=["GET"])
def api_maquinas():
        """
        Devuelve la lista de máquinas en formato JSON (info_maquinas).
        ---
        tags:
            - API Pública
        responses:
            200:
                description: Lista de máquinas con metadatos.
        """
        from .models import Machine

        maquinas_objs = Machine.query.filter_by(origen='docker').order_by(Machine.id.asc()).all()
        info_maquinas = []
        for m in maquinas_objs:
                d = {
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
                        'link_descarga': m.link_descarga
                }
                if d['imagen']:
                        d['imagen_url'] = url_for('static', filename=f"dockerlabs/{d['imagen']}", _external=True)
                info_maquinas.append(d)

        return jsonify(info_maquinas), 200
