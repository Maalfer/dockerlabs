import sqlite3
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
