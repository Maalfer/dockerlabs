import sqlite3
import os
from flask import g, current_app

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

def get_bunker_db():
    if 'bunker_db' not in g:
        g.bunker_db = sqlite3.connect(current_app.config['BUNKER_DATABASE'])
        g.bunker_db.row_factory = sqlite3.Row
    return g.bunker_db

def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()
    bunker_db = g.pop('bunker_db', None)
    if bunker_db is not None:
        bunker_db.close()

def init_db():
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'jugador',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS maquinas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            dificultad TEXT NOT NULL,
            clase TEXT NOT NULL,
            color TEXT NOT NULL,
            autor TEXT NOT NULL,
            enlace_autor TEXT NOT NULL,
            fecha TEXT NOT NULL,
            imagen TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            link_descarga TEXT NOT NULL,
            posicion TEXT NOT NULL DEFAULT 'izquierda'
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS writeups_subidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            maquina TEXT NOT NULL,
            autor TEXT NOT NULL,
            url TEXT NOT NULL,
            tipo TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(maquina, autor, url)
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS writeups_recibidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            maquina TEXT NOT NULL,
            autor TEXT NOT NULL,
            url TEXT NOT NULL,
            tipo TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS ranking_writeups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            puntos INTEGER NOT NULL
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS ranking_creadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            maquinas INTEGER NOT NULL
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS maquina_claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            maquina_nombre TEXT NOT NULL,
            contacto TEXT NOT NULL,
            prueba TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS nombre_claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            nombre_solicitado TEXT NOT NULL,
            nombre_actual TEXT NOT NULL,
            motivo TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS writeup_edit_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            writeup_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            maquina_original TEXT NOT NULL,
            autor_original TEXT NOT NULL,
            url_original TEXT NOT NULL,
            tipo_original TEXT NOT NULL,
            maquina_nueva TEXT NOT NULL,
            autor_nuevo TEXT NOT NULL,
            url_nueva TEXT NOT NULL,
            tipo_nuevo TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS machine_edit_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id INTEGER NOT NULL,
            origen TEXT NOT NULL,
            autor TEXT NOT NULL,
            nuevos_datos TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS username_change_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            old_username TEXT NOT NULL,
            requested_username TEXT NOT NULL,
            reason TEXT,
            contacto_opcional TEXT,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            processed_by INTEGER,
            processed_at TEXT,
            decision_reason TEXT
        )
        """
    )
    
    # Merged from init_ratings_db.py
    db.execute('''
    CREATE TABLE IF NOT EXISTS puntuaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        maquina_nombre TEXT NOT NULL,
        dificultad_score INTEGER,
        aprendizaje_score INTEGER,
        realismo_score INTEGER,
        conocimiento_score INTEGER,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(usuario_id, maquina_nombre)
    )
    ''')

    db.execute('''
    CREATE TABLE IF NOT EXISTS maquinas_hechas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        machine_name TEXT NOT NULL,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, machine_name),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    db.execute('''
    CREATE INDEX IF NOT EXISTS idx_maquinas_hechas_user_id 
    ON maquinas_hechas(user_id)
    ''')

    try:
        db.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'jugador'")
    except sqlite3.OperationalError:
        pass

    try:
        db.execute("ALTER TABLE username_change_requests ADD COLUMN contacto_opcional TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        db.execute("ALTER TABLE users ADD COLUMN recovery_pin_hash TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        db.execute("ALTER TABLE users ADD COLUMN recovery_pin_created_at TIMESTAMP")
    except sqlite3.OperationalError:
        pass

    try:
        db.execute("ALTER TABLE users ADD COLUMN biography TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        db.execute("ALTER TABLE users ADD COLUMN linkedin_url TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        db.execute("ALTER TABLE users ADD COLUMN github_url TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        db.execute("ALTER TABLE users ADD COLUMN youtube_url TEXT")
    except sqlite3.OperationalError:
        pass

    db.commit()


def init_bunker_db():
    db = get_bunker_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS maquinas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            dificultad TEXT NOT NULL,
            clase TEXT NOT NULL,
            color TEXT NOT NULL,
            autor TEXT NOT NULL,
            enlace_autor TEXT NOT NULL,
            fecha TEXT NOT NULL,
            imagen TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            link_descarga TEXT NOT NULL,
            posicion TEXT NOT NULL DEFAULT 'izquierda'
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS writeups_subidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            maquina TEXT NOT NULL,
            autor TEXT NOT NULL,
            url TEXT NOT NULL,
            tipo TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(maquina, autor, url)
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS writeups_recibidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            maquina TEXT NOT NULL,
            autor TEXT NOT NULL,
            url TEXT NOT NULL,
            tipo TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS bunker_access_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            token TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            activo INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    db.commit()
