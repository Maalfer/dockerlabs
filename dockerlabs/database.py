from .extensions import db as alchemy_db
from .models import User, Machine, Category, Mensajeria
from bunkerlabs.models import BunkerAccessToken, BunkerSolve, BunkerAccessLog, BunkerWriteup
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-64000")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.execute("PRAGMA mmap_size=3000000000")
    cursor.close()

def init_db():
    alchemy_db.create_all()
