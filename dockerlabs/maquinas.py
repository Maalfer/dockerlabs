"""
MAQUINAS - Funciones de utilidad (recalcular_ranking_creadores).

Todas las rutas Flask de este módulo han sido migradas a FastAPI (routers.py):
  - POST /gestion-maquinas/actualizar
  - POST /gestion-maquinas/eliminar
  - GET|POST /add-maquina
  - POST /reclamar-maquina
  - POST /claims/<id>/approve|reject|revert
  - POST /machine-edit-requests/<id>/approve|reject|revert
  - GET /maquinas-hechas

Este módulo solo conserva recalcular_ranking_creadores(), que es llamada
desde routers.py tras cada operación que modifica las máquinas.
"""

import os
from .models import Machine, CreatorRanking
from .extensions import db as alchemy_db

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MACHINE_LOGOS_FOLDER = os.path.join(BASE_DIR, 'static', 'dockerlabs', 'images', 'logos')
LOGO_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'dockerlabs', 'images', 'logos')
ALLOWED_LOGO_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}


def recalcular_ranking_creadores():
    """Recalcula el ranking de creadores de máquinas."""
    def clean(s):
        return (s or "").strip()

    from sqlalchemy import func

    results = alchemy_db.session.query(
        Machine.autor, func.count(Machine.id)
    ).group_by(Machine.autor).all()

    try:
        CreatorRanking.query.delete()
        for autor, count in results:
            nombre = clean(autor)
            if not nombre:
                continue
            alchemy_db.session.add(CreatorRanking(nombre=nombre, maquinas=count))
        alchemy_db.session.commit()
    except Exception:
        alchemy_db.session.rollback()
        raise
