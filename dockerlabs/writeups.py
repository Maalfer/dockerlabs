"""
WRITEUPS - Funciones de utilidad (recalcular_ranking_writeups).

Todas las rutas Flask de este módulo han sido migradas a FastAPI (routers.py).
Este módulo solo conserva recalcular_ranking_writeups(), llamada desde
routers.py tras operaciones que modifican writeups aprobados.
"""

from .models import Writeup, Machine, WriteupRanking
from .extensions import db as alchemy_db


def recalcular_ranking_writeups():
    """Recalcula el ranking de autores de writeups por puntos."""
    puntos_por_dificultad = {
        "muy fácil": 1, "muy facil": 1,
        "fácil": 2, "facil": 2,
        "medio": 3,
        "difícil": 4, "dificil": 4,
    }

    # Primero: writeups con máquina asociada (con dificultad conocida)
    results = (
        alchemy_db.session.query(Writeup.autor, Machine.dificultad)
        .join(Machine, Writeup.maquina == Machine.nombre)
        .all()
    )

    ranking = {}
    for autor, dificultad in results:
        if not autor:
            continue
        dificultad_lower = (dificultad or "").strip().lower()
        puntos = puntos_por_dificultad.get(dificultad_lower, 1)
        ranking[autor] = ranking.get(autor, 0) + puntos

    # Segundo: writeups sin máquina asociada (asignar 1 punto por defecto)
    writeups_sin_maquina = (
        alchemy_db.session.query(Writeup.autor)
        .outerjoin(Machine, Writeup.maquina == Machine.nombre)
        .filter(Machine.id == None)
        .all()
    )

    for (autor,) in writeups_sin_maquina:
        if not autor:
            continue
        ranking[autor] = ranking.get(autor, 0) + 1  # 1 punto por defecto

    try:
        WriteupRanking.query.delete()
        for autor, puntos in ranking.items():
            alchemy_db.session.add(WriteupRanking(nombre=autor, puntos=puntos))
        alchemy_db.session.commit()
    except Exception:
        alchemy_db.session.rollback()
        raise
