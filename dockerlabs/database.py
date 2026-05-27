import os
import contextvars
from sqlalchemy import create_engine, String
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from sqlalchemy.ext.compiler import compiles

# La aplicación usa MariaDB/MySQL. La cadena de conexión se toma de
# DATABASE_URL (definida en .env), p.ej.:
#   mysql+pymysql://usuario:clave@127.0.0.1/dockerlabs?charset=utf8mb4
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL no está definida. Configúrala en .env, por ejemplo: "
        "mysql+pymysql://usuario:clave@127.0.0.1/dockerlabs?charset=utf8mb4"
    )


# En MySQL/MariaDB un VARCHAR exige longitud. Varios modelos declaran
# db.String sin longitud; para esos casos emitimos VARCHAR(255) al crear el
# esquema. No afecta a las consultas en runtime.
@compiles(String, "mysql")
@compiles(String, "mariadb")
def _compile_unbounded_varchar(element, compiler, **kw):
    if element.length is None:
        return "VARCHAR(255)"
    return compiler.visit_VARCHAR(element, **kw)


engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False,
)

# Ámbito de la sesión por REQUEST (no por hilo).
#
# FastAPI ejecuta los endpoints síncronos (def) en un threadpool, mientras que
# el middleware de limpieza corre en el hilo del event loop. Con un
# scoped_session indexado por hilo (el comportamiento por defecto), la sesión
# creada en el hilo worker nunca se eliminaba desde el event loop, así que su
# conexión quedaba retenida hasta agotar el QueuePool (TimeoutError). Esto pasó
# inadvertido con SQLite y afloró al migrar a MariaDB.
#
# Indexando la sesión por un contextvar propio del request (que anyio copia al
# hilo worker al ejecutar el endpoint síncrono), tanto el worker como el event
# loop ven la MISMA sesión, y db_session.remove() la limpia correctamente.
_request_scope_id = contextvars.ContextVar("db_request_scope_id", default=None)


def _current_scope():
    return _request_scope_id.get()


db_session = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine),
    scopefunc=_current_scope,
)

class _Base:
    query = db_session.query_property()

Base = declarative_base(cls=_Base)

def init_db():
    import dockerlabs.models
    import bunkerlabs.models
    # Con varios workers de uvicorn, todos ejecutan create_all a la vez; el
    # checkfirst tiene una carrera al crear una tabla NUEVA (uno la crea y
    # los demás reciben 'table already exists'). Toleramos esa carrera para
    # no tumbar workers en el primer arranque tras añadir un modelo.
    from sqlalchemy.exc import OperationalError
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
    except OperationalError as e:
        if 'already exists' not in str(e).lower():
            raise
