from flask import Blueprint, render_template, session
from .decorators import role_required, get_current_role
from .models import User, WriteupEditRequest

writeups_bp = Blueprint('writeups', __name__)

def recalcular_ranking_writeups():
    puntos_por_dificultad = {
        "muy fácil": 1, "muy facil": 1,
        "fácil": 2, "facil": 2,
        "medio": 3,
        "difícil": 4, "dificil": 4,
    }

    results = alchemy_db.session.query(Writeup.autor, Machine.dificultad)        .join(Machine, Writeup.maquina == Machine.nombre).all()
    
    ranking = {}
    for autor, dificultad in results:
        if not autor: continue
        dificultad_lower = (dificultad or "").strip().lower()
        puntos = puntos_por_dificultad.get(dificultad_lower, 1)
        ranking[autor] = ranking.get(autor, 0) + puntos

    WriteupRanking.query.delete()           

    for autor, puntos in ranking.items():
        entry = WriteupRanking(nombre=autor, puntos=puntos)
        alchemy_db.session.add(entry)
    
    alchemy_db.session.commit()
















