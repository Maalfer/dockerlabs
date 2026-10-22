"""
Fixtures raíz del suite de tests de DockerLabs.

IMPORTANTE: este fichero NO debe importar nada de `dockerlabs.*`/`bunkerlabs.*`
a nivel de módulo. `dockerlabs/database.py` lee `DATABASE_URL` del entorno en
el momento en que se importa y lanza `RuntimeError` si no está definida, así
que esa variable tiene que quedar fijada ANTES de la primera importación de
`asgi`/`dockerlabs.*` — lo hace la fixture `_test_database` de aquí abajo. Por
eso todos los imports de la app viven dentro de funciones, nunca en la
cabecera del fichero.
"""
from __future__ import annotations

import os
import socket
import subprocess
import time
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILES = ["-f", "docker-compose.yml", "-f", "tests/docker-compose.test.yml"]

TEST_DB_HOST = os.environ.get("TEST_DB_HOST", "127.0.0.1")
TEST_DB_PORT = int(os.environ.get("TEST_DB_PORT", "3307"))
TEST_DB_USER = os.environ.get("TEST_DB_USER", "dockerlabs")
TEST_DB_PASSWORD = os.environ.get("DB_PASSWORD", "dockerlabs_test_pw")
TEST_DB_ROOT_PASSWORD = os.environ.get("DB_ROOT_PASSWORD", "dockerlabs_test_root_pw")
TEST_DB_NAME = os.environ.get("TEST_DB_NAME", "dockerlabs_test")

TEST_DATABASE_URL = (
    f"mysql+pymysql://{TEST_DB_USER}:{TEST_DB_PASSWORD}"
    f"@{TEST_DB_HOST}:{TEST_DB_PORT}/{TEST_DB_NAME}?charset=utf8mb4"
)


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _ensure_docker_db_running() -> None:
    """Levanta el servicio 'db' de docker-compose (con el override de test)
    si todavía no es alcanzable en el puerto esperado. Idempotente: si ya
    está arriba de una ejecución anterior, no hace nada."""
    if _port_open(TEST_DB_HOST, TEST_DB_PORT):
        return

    env = {**os.environ, "DB_PASSWORD": TEST_DB_PASSWORD, "DB_ROOT_PASSWORD": TEST_DB_ROOT_PASSWORD}
    subprocess.run(
        ["docker", "compose", *COMPOSE_FILES, "up", "-d", "db"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
    )

    for _ in range(60):
        if _port_open(TEST_DB_HOST, TEST_DB_PORT):
            # El puerto puede abrirse un instante antes de que MariaDB acepte
            # conexiones reales; probamos una conexión de verdad.
            try:
                import pymysql

                conn = pymysql.connect(
                    host=TEST_DB_HOST, port=TEST_DB_PORT,
                    user=TEST_DB_USER, password=TEST_DB_PASSWORD,
                    database=TEST_DB_NAME, charset="utf8mb4",
                    connect_timeout=2,
                )
                conn.close()
                return
            except Exception:
                pass
        time.sleep(1)

    raise RuntimeError(
        f"La MariaDB de test no respondió en {TEST_DB_HOST}:{TEST_DB_PORT} tras 60s. "
        "Revisa 'docker compose ps' / 'docker logs dockerlabs-db-1'."
    )


@pytest.fixture(scope="session", autouse=True)
def _test_database():
    """Arranca (si hace falta) la MariaDB de test vía Docker Compose, fija
    DATABASE_URL, importa la app (dispara init_db()) y la deja lista para
    todo el run de pytest."""
    _ensure_docker_db_running()
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ.setdefault("SECRET_KEY", "dockerlabs-test-secret-key")

    import asgi  # noqa: F401  (importar ya ejecuta init_db())

    yield asgi

    # No se para el contenedor al final: se reutiliza entre ejecuciones.
    # `docker compose -f docker-compose.yml -f tests/docker-compose.test.yml down -v`
    # lo tira abajo manualmente (documentado en tests/README.md).


@pytest.fixture(autouse=True)
def _truncate_between_tests(_test_database):
    """Deja la base de datos de test vacía antes de CADA test, sin depender
    de rollback de transacción (la app hace commits reales dentro de los
    endpoints). Se ejecuta tras el test anterior, nunca antes del primero
    útil — así el estado queda limpio independientemente del orden."""
    yield
    import sqlalchemy
    from dockerlabs.database import engine, db_session

    db_session.remove()
    with engine.begin() as conn:
        conn.execute(sqlalchemy.text("SET FOREIGN_KEY_CHECKS=0"))
        insp = sqlalchemy.inspect(engine)
        for table in insp.get_table_names():
            conn.execute(sqlalchemy.text(f"TRUNCATE TABLE `{table}`"))
        conn.execute(sqlalchemy.text("SET FOREIGN_KEY_CHECKS=1"))


@pytest.fixture(autouse=True)
def _reset_rate_limit_store(_test_database):
    """El middleware ASGI de rate limiting (asgi.rate_limit_store) es un dict
    a nivel de módulo/proceso, no algo que la app resetee por request. El
    `client` fixture reutiliza siempre la misma IP falsa ("testclient", fija
    en la clase `TestClient` de Starlette), así que sin esto los hits se
    acumulan request a request A TRAVÉS de todos los ficheros de test del
    mismo proceso de pytest y, pasados varios cientos, el suite entero empieza
    a recibir 429 en vez de las respuestas reales que cada test espera.
    `tests/integration/test_rate_limiting.py` ya gestiona su propio
    snapshot/restore local para sus tests específicos del propio limitador;
    esto no interfiere con ello, solo evita que el resto del suite lo sufra."""
    _test_database.rate_limit_store.clear()
    yield


@pytest.fixture(autouse=True)
def _no_real_network(monkeypatch):
    """Por defecto ningún test debe abrir un socket SMTP real ni llamar al
    webhook de Discord real. Los tests que quieran aserciones sobre ESE
    envío parchean estos mismos objetos con su propio mock explícito (ver
    `mock_smtp` / `mock_discord` más abajo); esta fixture solo evita que un
    test que NO pensaba en ello dispare tráfico de red de verdad."""
    import smtplib
    import dockerlabs.discord_notify as discord_notify

    monkeypatch.setattr(smtplib, "SMTP", MagicMock(side_effect=AssertionError(
        "Se intentó abrir una conexión SMTP real en un test; usa la fixture mock_smtp."
    )))

    async def _no_discord(*args, **kwargs):
        return None

    monkeypatch.setattr(discord_notify, "_send", _no_discord)


@pytest.fixture
def mock_smtp(monkeypatch):
    """Sustituye smtplib.SMTP por un doble que registra los mensajes enviados
    sin abrir ningún socket. Devuelve la lista (mutable) de llamadas:
    cada entrada es {"to": str, "subject": str, "html": str}."""
    sent = []

    class _FakeSMTP:
        def __init__(self, host, port, timeout=10):
            self.host, self.port = host, port

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def ehlo(self):
            pass

        def starttls(self, context=None):
            pass

        def login(self, user, password):
            pass

        def sendmail(self, from_addr, to_addrs, msg_string):
            # dockerlabs/email.py llama a server.sendmail(from_addr, to_addr,
            # msg.as_string()), no a send_message(msg): el mensaje llega aquí
            # ya serializado a texto y hay que re-parsearlo.
            import email as _email_module

            parsed = _email_module.message_from_string(msg_string)
            html = parsed.get_payload()
            if parsed.is_multipart():
                for part in parsed.walk():
                    if part.get_content_type() == "text/html":
                        payload = part.get_payload(decode=True)
                        html = payload.decode(part.get_content_charset() or "utf-8")
            sent.append({
                "to": parsed["To"],
                "subject": parsed["Subject"],
                "html": html,
            })

    import smtplib

    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("SMTP_FROM", "noreply@dockerlabs.test")
    return sent


@pytest.fixture
def mock_discord(monkeypatch):
    """Sustituye dockerlabs.discord_notify._send por un stub que registra los
    embeds enviados. Devuelve la lista (mutable) de embeds."""
    sent = []

    async def _fake_send(embed):
        sent.append(embed)
        return None

    import dockerlabs.discord_notify as discord_notify

    monkeypatch.setattr(discord_notify, "_send", _fake_send)
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.test/webhook")
    return sent


@pytest.fixture
def client(_test_database):
    """TestClient contra la app ASGI real (mismos middlewares que producción:
    DBSessionMiddleware, rate limiting, cabeceras de seguridad)."""
    from fastapi.testclient import TestClient

    # base_url HTTPS: la cookie de sesión real se fija con `secure=True`
    # (routes/auth.py, correcto en producción, que siempre va por TLS detrás
    # de nginx). httpx respeta el atributo Secure al reenviar cookies: con el
    # "http://testserver" por defecto de TestClient, cualquier test que haga
    # login vía POST /api/auth/login real y confíe en que la cookie de la
    # respuesta autentique la siguiente petición la perdería en route (el
    # jar de cookies no la reenvía sobre http). No afecta a `login_as`, que
    # fija la cookie directamente con `client.cookies.set(...)`.
    with TestClient(_test_database.app, base_url="https://testserver") as c:
        yield c


@pytest.fixture
def db():
    """Acceso directo a `dockerlabs.extensions.db` para que los tests puedan
    crear/leer filas sin pasar por un endpoint HTTP cuando haga falta."""
    from dockerlabs.extensions import db as _db

    return _db


@pytest.fixture
def auth():
    """Expone los helpers de sesión/CSRF reales de la app (no reinventados):
    `create_session_cookie` y `compute_csrf_token` de `dockerlabs.routers`."""
    from dockerlabs import routers

    return routers


@pytest.fixture
def login_as(client, auth):
    """Fixture-factory: `login_as(user)` deja al `client` autenticado como
    ese usuario (cookie de sesión real, firmada con la clave real de la BD de
    test) y devuelve el token CSRF que hay que mandar en las peticiones de
    escritura. `login_as(user, role="moderador")` fuerza un rol distinto al
    guardado en BD (útil para probar la revalidación de rol de `get_session`)."""

    def _login(user, role: str | None = None, session_version: int | None = None):
        sid = f"test-sid-{uuid.uuid4().hex}"
        cookie = auth.create_session_cookie(
            user.id,
            user.username,
            role or user.role,
            _id=sid,
            session_version=user.session_version if session_version is None else session_version,
        )
        client.cookies.set("session", cookie)
        return auth.compute_csrf_token(sid)

    return _login


@pytest.fixture
def admin_api_token(db):
    """Fixture-factory: `admin_api_token(admin_user, label="...")` crea una
    fila `ApiToken` real (mismo esquema pbkdf2 que /dashboard) y devuelve el
    token en claro + los headers listos para usar: `Authorization: Bearer`.
    Replica el patrón ya verificado a mano contra producción para probar el
    acceso por cabecera (bypassa CSRF por diseño, ver routers.get_session)."""

    def _make(admin_user, label="pytest"):
        from dockerlabs.models import ApiToken
        from dockerlabs.token_auth import generate_api_token, hash_api_token, token_display_prefix

        token = generate_api_token()
        row = ApiToken(
            admin_user_id=admin_user.id,
            label=label,
            token_hash=hash_api_token(token),
            token_prefix=token_display_prefix(token),
        )
        db.session.add(row)
        db.session.commit()
        return token, {"Authorization": f"Bearer {token}"}

    return _make


def csrf_headers(csrf_token: str) -> dict:
    return {"X-CSRFToken": csrf_token}
