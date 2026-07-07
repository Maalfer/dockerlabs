"""Utilidades de cálculo del ranking de writeups."""

from .models import Writeup, Machine, WriteupRanking
from .extensions import db


def recalcular_ranking_writeups():
    """Recalcula el ranking de autores de writeups por puntos."""
    puntos_por_dificultad = {
        "muy fácil": 1, "muy facil": 1,
        "fácil": 2, "facil": 2,
        "medio": 3,
        "difícil": 4, "dificil": 4,
    }

    results = (
        db.session.query(Writeup.autor, Machine.dificultad)
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

    writeups_sin_maquina = (
        db.session.query(Writeup.autor)
        .outerjoin(Machine, Writeup.maquina == Machine.nombre)
        .filter(Machine.id == None)
        .all()
    )

    for (autor,) in writeups_sin_maquina:
        if not autor:
            continue
        ranking[autor] = ranking.get(autor, 0) + 1

    try:
        WriteupRanking.query.delete()
        for autor, puntos in ranking.items():
            db.session.add(WriteupRanking(nombre=autor, puntos=puntos))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
