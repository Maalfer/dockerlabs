import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'dockerlabs.db')

# StaticPool para SQLite: cada hilo tiene su propia conexión persistente
# Elimina problemas de QueuePool agotado con muchas peticiones concurrentes (imágenes)
engine = create_engine(
    f"sqlite:///{DATABASE_PATH}",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    pool_pre_ping=True,
    echo=False
)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-64000")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.execute("PRAGMA mmap_size=3000000000")
    cursor.close()

db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

class _Base:
    query = db_session.query_property()

Base = declarative_base(cls=_Base)

def init_db():
    import dockerlabs.models
    import bunkerlabs.models
    Base.metadata.create_all(bind=engine)
