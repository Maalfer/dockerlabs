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















@writeups_bp.route('/writeups-recibidos')
@role_required('admin', 'moderador')
def writeups_recibidos():
    """
    Received writeups page.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Received writeups page.
    """
    return render_template('dockerlabs/user/writeups_recibidos.html')






@writeups_bp.route('/writeups-publicados')
@role_required('admin', 'moderador', 'jugador')
def writeups_publicados():
    """
    Published writeups page.
    ---
    tags:
      - Writeups
    responses:
      200:
        description: Published writeups page.
    """
    user = None
    if session.get('user_id'):
        user = User.query.get(session.get('user_id'))
    return render_template('dockerlabs/user/writeups_publicados.html', user=user)


@writeups_bp.route('/peticiones-writeups')
@role_required('admin', 'moderador')
def peticiones_writeups():
    """
    Writeup petitions page.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Petitions page.
    """
                                    
    requests = WriteupEditRequest.query.order_by(WriteupEditRequest.id.desc()).all()

    return render_template("dockerlabs/admin/peticiones.html", peticiones=requests)
