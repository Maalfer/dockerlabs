from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import secrets
import json
from . import extensions
from .decorators import csrf_protect, role_required
from .db_access import get_bunker_db

bunkerlabs_bp = Blueprint('bunkerlabs', __name__)

@bunkerlabs_bp.route('/bunkerlabs-login', methods=['GET', 'POST'])
@csrf_protect
@extensions.limiter.limit("5 per minute", methods=["POST"])
def bunkerlabs_login():
    # Enforce DockerLabs authentication
    if session.get('user_id') is None:
        return redirect(url_for('auth.login'))

    error = None

    if request.method == 'POST':
        token_introducido = (request.form.get('password') or '').strip()

        if not token_introducido:
            error = "Debes introducir un token de acceso."
        else:
            db = get_bunker_db()
            fila = db.execute(
                "SELECT id, nombre FROM bunker_access_tokens WHERE token = ? AND activo = 1",
                (token_introducido,)
            ).fetchone()

            if fila is not None:
                # Sync DockerLabs username to BunkerLabs token
                docker_username = session.get('username')
                if docker_username:
                    db.execute(
                        "UPDATE bunker_access_tokens SET nombre = ? WHERE id = ?",
                        (docker_username, fila['id'])
                    )
                    db.commit()
                    # Update session with the new name
                    session['bunkerlabs_nombre'] = docker_username
                else:
                    session['bunkerlabs_nombre'] = fila['nombre']

                session['bunkerlabs_ok'] = True
                session['bunkerlabs_id'] = fila['id']
                return redirect(url_for('bunkerlabs.bunkerlabs_home'))
            else:
                error = "Token incorrecto o inactivo."

    return render_template('bunkerlabs/bunkerlabs-login.html', error=error)

@bunkerlabs_bp.route('/bunkerlabs')
def bunkerlabs_home():
    # Enforce DockerLabs authentication
    if session.get('user_id') is None:
        return redirect(url_for('auth.login'))

    if not session.get('bunkerlabs_ok'):
        return redirect(url_for('bunkerlabs.bunkerlabs_login'))

    db = get_bunker_db()
    maquinas = db.execute("SELECT * FROM maquinas ORDER BY id ASC").fetchall()

    return render_template('bunkerlabs/bunkerlabs.html', maquinas=maquinas)


@bunkerlabs_bp.route('/accesos-bunkerlabs', methods=['GET', 'POST'])
@role_required('admin')
@csrf_protect
@extensions.limiter.limit("5 per minute", methods=["POST"])
def accesos_bunkerlabs():
    db = get_bunker_db()
    error = None
    success = None
    nuevo_token = None

    if request.method == 'POST':
        nombre = (request.form.get('nombre') or '').strip()

        if not nombre:
            error = "El nombre es obligatorio."
        else:
            nuevo_token = secrets.token_urlsafe(8)

            try:
                db.execute(
                    "INSERT INTO bunker_access_tokens (nombre, token) VALUES (?, ?)",
                    (nombre, nuevo_token)
                )
                db.commit()
                success = f"Token creado correctamente para {nombre}"
            except sqlite3.IntegrityError:
                error = "Error con el token generado."

    tokens = db.execute(
        "SELECT id, nombre, token, created_at, activo FROM bunker_access_tokens ORDER BY created_at DESC"
    ).fetchall()

    return render_template(
        'accesos-bunkerlabs.html',
        tokens=tokens,
        error=error,
        success=success,
        nuevo_token=nuevo_token
    )

@bunkerlabs_bp.route('/accesos-bunkerlabs/<int:token_id>/delete', methods=['POST'])
@role_required('admin')
@csrf_protect
@extensions.limiter.limit("5 per minute", methods=["POST"])
def delete_bunker_token(token_id):
    db = get_bunker_db()
    db.execute("DELETE FROM bunker_access_tokens WHERE id = ?", (token_id,))
    db.commit()
    return redirect(url_for('bunkerlabs.accesos_bunkerlabs'))


@bunkerlabs_bp.route('/subir-flag', methods=['POST'])
@csrf_protect
@extensions.limiter.limit("10 per minute", methods=["POST"])
def subir_flag():
    data = request.get_json()
    maquina_nombre = data.get('maquina')
    pin_introducido = data.get('pin')

    if not maquina_nombre or not pin_introducido:
        return jsonify({'error': 'Faltan datos'}), 400

    db = get_bunker_db()
    maquina = db.execute(
        "SELECT id, dificultad, pin FROM maquinas WHERE nombre = ?",
        (maquina_nombre,)
    ).fetchone()

    if not maquina:
        return jsonify({'error': 'Máquina no encontrada'}), 404

    pin_real = maquina['pin']
    dificultad = maquina['dificultad']
    maquina_id = maquina['id']
    user_id = session.get('bunkerlabs_id')

    if not user_id:
        return jsonify({'error': 'Sesión no válida.'}), 401

    if pin_real == pin_introducido:
        # Verificar si ya la ha completado
        ya_completada = db.execute(
            "SELECT id FROM bunker_solves WHERE user_id = ? AND machine_id = ?",
            (user_id, maquina_id)
        ).fetchone()

        if ya_completada:
            return jsonify({'message': 'Flag correcta, pero ya habías completado esta máquina.'}), 200

        # Calcular puntos
        puntos_map = {
            'Muy Fácil': 1,
            'Fácil': 2,
            'Medio': 3,
            'Difícil': 4
        }
        puntos = puntos_map.get(dificultad, 0)

        try:
            # Registrar solve
            db.execute(
                "INSERT INTO bunker_solves (user_id, machine_id) VALUES (?, ?)",
                (user_id, maquina_id)
            )
            # Sumar puntos al usuario
            db.execute(
                "UPDATE bunker_access_tokens SET puntos = puntos + ? WHERE id = ?",
                (puntos, user_id)
            )
            db.commit()
            return jsonify({'message': f'¡Flag correcta! Has ganado {puntos} puntos.'}), 200
        except Exception as e:
            return jsonify({'error': 'Error al procesar la flag.'}), 500

    else:
        return jsonify({'error': 'Flag incorrecta.'}), 401

@bunkerlabs_bp.route('/api/bunker-ranking', methods=['GET'])
@extensions.limiter.limit("60 per minute", methods=["GET"])
def bunker_ranking():
    db = get_bunker_db()
    rows = db.execute(
        """
        SELECT nombre, puntos
        FROM bunker_access_tokens
        WHERE puntos > 0
        ORDER BY puntos DESC, LOWER(nombre) ASC
        """
    ).fetchall()

    ranking = []
    for row in rows:
        ranking.append({
            "nombre": row["nombre"],
            "puntos": row["puntos"]
        })

    return jsonify(ranking), 200
