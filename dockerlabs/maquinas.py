"""Utilidades de cálculo del ranking de creadores de máquinas."""

from .models import Machine, CreatorRanking
from .extensions import db


def recalcular_ranking_creadores():
    """Recalcula el ranking de creadores de máquinas."""
    def clean(s):
        return (s or "").strip()

    from sqlalchemy import func

    results = db.session.query(
        Machine.autor, func.count(Machine.id)
    ).filter(Machine.origen != 'empezar').group_by(Machine.autor).all()

    try:
        CreatorRanking.query.delete()
        for autor, count in results:
            nombre = clean(autor)
            if not nombre:
                continue
            db.session.add(CreatorRanking(nombre=nombre, maquinas=count))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
