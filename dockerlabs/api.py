import os
from flask import Blueprint, jsonify, url_for
from .database import get_db
from bunkerlabs.extensions import limiter

api_bp = Blueprint('api', __name__)

@api_bp.route('/api', methods=['GET'])
@limiter.limit("60 per minute", methods=["GET"])
def api_summary():
    db = get_db()

    # Info Maquinas
    maquinas_rows = db.execute("SELECT * FROM maquinas ORDER BY id ASC").fetchall()
    info_maquinas = []
    maquinas_names = []
    for row in maquinas_rows:
        # Convert row to dict
        m = dict(row)
        # Add full image URL if needed, or keep relative
        if m.get('imagen'):
             m['imagen_url'] = url_for('static', filename=m['imagen'], _external=True)
        info_maquinas.append(m)
        maquinas_names.append(m['nombre'])

    # Ranking Creadores
    creadores_rows = db.execute("SELECT * FROM ranking_creadores ORDER BY maquinas DESC, LOWER(nombre) ASC").fetchall()
    ranking_creadores = [dict(row) for row in creadores_rows]

    # Ranking Writeups
    ranking_writeups_rows = db.execute("SELECT * FROM ranking_writeups ORDER BY puntos DESC, LOWER(nombre) ASC").fetchall()
    ranking_writeups = [dict(row) for row in ranking_writeups_rows]

    # Writeups
    writeups_rows = db.execute("SELECT * FROM writeups_subidos ORDER BY created_at DESC").fetchall()
    writeups_textos = []
    writeups_videos = []
    for row in writeups_rows:
        w = dict(row)
        if w['tipo'] == 'texto':
            writeups_textos.append(w)
        else:
            writeups_videos.append(w)

    # Metadata
    total_creadores = len(ranking_creadores)
    total_puntos = sum(r['puntos'] for r in ranking_writeups)
    total_writeups = len(writeups_rows)

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
