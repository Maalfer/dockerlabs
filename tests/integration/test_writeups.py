"""Tests de dockerlabs/routes/writeups.py — envío, aprobación, borrado y
listado de writeups (sin cubrir el endpoint SSE de análisis, que vive en
test_writeups_analisis.py).

Rutas cubiertas (todas en `api_router`, prefijo `/api`):
  POST   /api/submit_writeup
  POST   /api/writeups/recibidos/{id}/aprobar
  POST   /api/writeups/recibidos/aprobar-todos
  POST   /api/writeups/subidos/{id}/delete
  DELETE /api/writeups_subidos/{id}
  POST   /api/writeups/{id}/report
  GET    /api/writeups/{maquina_nombre}
"""
import pytest

from tests.conftest import csrf_headers
from tests.factories import make_machine, make_pending_writeup, make_user, make_writeup

pytestmark = pytest.mark.integration


def _admin(db):
    return make_user(db, role="admin")


def _jugador(db, **overrides):
    return make_user(db, role="jugador", **overrides)


@pytest.fixture
def _fast_diploma(monkeypatch):
    """`ensure_certificate()` renderiza un PNG real con PIL usando una fuente
    TTF cuya ruta está hardcodeada a una ubicación de Linux
    (`/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`) que no existe en
    esta máquina de test. `ensure_certificate_safe()` traga cualquier
    excepción (nunca debe tumbar una aprobación de writeup), así que sin este
    parche el certificado simplemente nunca se emitiría *en este entorno* y
    el test estaría probando el font-not-found, no la lógica de negocio.
    Se sustituye `render_diploma` por una imagen mínima: la renderización en
    sí la cubre el archivo de tests dedicado a certificados."""
    from PIL import Image

    import dockerlabs.routes.certificados as certificados_mod

    def _fake_render(display_name, display_machine, cert_id, date_str):
        return Image.new("RGB", (10, 10), "white")

    monkeypatch.setattr(certificados_mod, "render_diploma", _fake_render)


SUBMIT_URL = "/api/submit_writeup"
APROBAR_TODOS_URL = "/api/writeups/recibidos/aprobar-todos"


def _aprobar_url(writeup_id):
    return f"/api/writeups/recibidos/{writeup_id}/aprobar"


class TestSubmitWriteup:
    def test_requires_login(self, client, db):
        maquina = make_machine(db)
        r = client.post(SUBMIT_URL, json={"maquina": maquina.nombre, "url": "https://blog.test/x", "tipo": "texto"})
        assert r.status_code == 403

    def test_validates_maquina_name(self, client, login_as, db):
        user = _jugador(db)
        csrf = login_as(user)
        r = client.post(
            SUBMIT_URL, json={"maquina": "", "url": "https://blog.test/x", "tipo": "texto"},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 400

    def test_validates_url(self, client, login_as, db):
        maquina = make_machine(db)
        user = _jugador(db)
        csrf = login_as(user)
        r = client.post(
            SUBMIT_URL, json={"maquina": maquina.nombre, "url": "javascript:alert(1)", "tipo": "texto"},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 400

    def test_validates_tipo(self, client, login_as, db):
        maquina = make_machine(db)
        user = _jugador(db)
        csrf = login_as(user)
        r = client.post(
            SUBMIT_URL, json={"maquina": maquina.nombre, "url": "https://blog.test/x", "tipo": "pdf"},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 400

    def test_nonexistent_machine_rejected(self, client, login_as, db):
        user = _jugador(db)
        csrf = login_as(user)
        r = client.post(
            SUBMIT_URL, json={"maquina": "NoExisteDeVerdad", "url": "https://blog.test/x", "tipo": "texto"},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 400
        assert "no existe" in r.json()["error"].lower()

    def test_machine_name_lookup_is_actually_case_insensitive_at_db_level(self, client, login_as, db):
        # NOTA / hallazgo de testing: la tarea original asumía que esta ruta
        # exige coincidencia EXACTA de mayúsculas/minúsculas con el nombre de
        # la máquina. Se comprobó lo contrario: la columna `maquinas.nombre`
        # usa la collation por defecto de MariaDB en esta BD
        # (utf8mb4_uca1400_ai_ci -- "ci" = case insensitive, "ai" = accent
        # insensitive), así que `Machine.query.filter_by(nombre=...)` iguala
        # "acme" con "Acme" a nivel SQL aunque el código Python no haga
        # ningún `.lower()` explícito. Se fija aquí el comportamiento REAL
        # (aceptado), no el asumido originalmente.
        make_machine(db, nombre="Acme")
        user = _jugador(db)
        csrf = login_as(user)
        r = client.post(
            SUBMIT_URL, json={"maquina": "acme", "url": "https://blog.test/x", "tipo": "texto"},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 200, r.text

    def test_creates_pending_not_published(self, client, login_as, db):
        from dockerlabs.models import PendingWriteup, Writeup

        maquina = make_machine(db)
        user = _jugador(db)
        csrf = login_as(user)
        r = client.post(
            SUBMIT_URL, json={"maquina": maquina.nombre, "url": "https://blog.test/pendiente", "tipo": "video"},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 200, r.text
        db.session.rollback()
        pending = PendingWriteup.query.filter_by(maquina=maquina.nombre, autor=user.username).first()
        assert pending is not None
        assert pending.tipo == "video"
        assert Writeup.query.filter_by(maquina=maquina.nombre, autor=user.username).first() is None


class TestApproveSingle:
    def test_jugador_forbidden(self, client, login_as, db):
        maquina = make_machine(db)
        pending = make_pending_writeup(db, maquina=maquina.nombre, autor=maquina.autor)
        user = _jugador(db)
        csrf = login_as(user)
        r = client.post(_aprobar_url(pending.id), headers=csrf_headers(csrf))
        assert r.status_code == 403

    def test_moves_pending_to_published(self, client, login_as, db):
        from dockerlabs.models import PendingWriteup, Writeup

        maquina = make_machine(db, origen="docker", autor="WriterOne")
        pending = make_pending_writeup(db, maquina=maquina.nombre, autor="WriterOne")
        pending_id = pending.id  # capturado ANTES de aprobar: la ruta borra
        # esta fila y, tras el rollback, volver a leer `pending.id` sobre el
        # objeto ORM expirado dispararía ObjectDeletedError en vez de un None.
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(_aprobar_url(pending_id), headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text
        db.session.rollback()
        assert PendingWriteup.query.filter_by(id=pending_id).first() is None
        assert Writeup.query.filter_by(maquina=maquina.nombre, autor="WriterOne").first() is not None

    def test_triggers_writeup_ranking_recalculation(self, client, login_as, db):
        from dockerlabs.models import WriteupRanking

        maquina = make_machine(db, origen="docker", autor="WriterTwo", dificultad="Fácil")
        pending = make_pending_writeup(db, maquina=maquina.nombre, autor="WriterTwo")
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(_aprobar_url(pending.id), headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text
        db.session.rollback()
        ranking = WriteupRanking.query.filter_by(nombre="WriterTwo").first()
        assert ranking is not None
        assert ranking.puntos == 2  # "Fácil" vale 2 puntos

    def test_docker_origin_emits_certificate(self, client, login_as, db, _fast_diploma):
        from dockerlabs.models import Certificate

        author = make_user(db, role="jugador", username="DocAuthorCert")
        maquina = make_machine(db, origen="docker", autor=author.username)
        pending = make_pending_writeup(db, maquina=maquina.nombre, autor=author.username)
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(_aprobar_url(pending.id), headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text
        db.session.rollback()
        cert = Certificate.query.filter_by(machine_name=maquina.nombre, user_id=author.id).first()
        assert cert is not None
        assert cert.username == author.username

    def test_bunker_origin_does_not_emit_certificate(self, client, login_as, db, _fast_diploma):
        from dockerlabs.models import Certificate

        author = make_user(db, role="jugador", username="BunkAuthorCert")
        maquina = make_machine(db, origen="bunker", autor=author.username)
        pending = make_pending_writeup(db, maquina=maquina.nombre, autor=author.username)
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(_aprobar_url(pending.id), headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text
        db.session.rollback()
        assert Certificate.query.filter_by(machine_name=maquina.nombre, user_id=author.id).first() is None

    def test_never_calls_discord(self, client, login_as, db, mock_discord):
        maquina = make_machine(db, origen="docker")
        pending = make_pending_writeup(db, maquina=maquina.nombre, autor=maquina.autor)
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(_aprobar_url(pending.id), headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text
        assert mock_discord == []


class TestApproveAll:
    def test_jugador_forbidden(self, client, login_as, db):
        user = _jugador(db)
        csrf = login_as(user)
        r = client.post(APROBAR_TODOS_URL, headers=csrf_headers(csrf))
        assert r.status_code == 403

    def test_no_pending_writeups(self, client, login_as, db):
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(APROBAR_TODOS_URL, headers=csrf_headers(csrf))
        assert r.status_code == 200
        assert r.json()["aprobados"] == 0

    def test_exactly_ten_does_not_notify(self, client, login_as, db, mock_discord):
        # Umbral exacto: el código usa `if len(nuevos) > 10`, estrictamente
        # mayor que 10 -- 10 aprobaciones de golpe NO disparan Discord.
        maquina = make_machine(db, origen="docker")
        for i in range(10):
            make_pending_writeup(db, maquina=maquina.nombre, autor=f"Writer{i}")
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(APROBAR_TODOS_URL, headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text
        assert r.json()["aprobados"] == 10
        assert mock_discord == []

    def test_exactly_eleven_notifies_once(self, client, login_as, db, mock_discord):
        maquina = make_machine(db, origen="docker")
        for i in range(11):
            make_pending_writeup(db, maquina=maquina.nombre, autor=f"Writer{i}")
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(APROBAR_TODOS_URL, headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text
        assert r.json()["aprobados"] == 11
        assert len(mock_discord) == 1

    def test_dedup_already_published_triple_is_not_duplicated(self, client, login_as, db, mock_discord):
        from dockerlabs.models import PendingWriteup, Writeup

        maquina = make_machine(db, origen="docker", autor="Dup")
        make_writeup(db, maquina=maquina.nombre, autor="Dup", url="https://blog.test/dup")
        make_pending_writeup(db, maquina=maquina.nombre, autor="Dup", url="https://blog.test/dup")
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(APROBAR_TODOS_URL, headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text
        # El pendiente se consume (cuenta como "aprobado") aunque no genere
        # una fila nueva: ya había un writeup publicado idéntico.
        assert r.json()["aprobados"] == 1
        db.session.rollback()
        assert Writeup.query.filter_by(maquina=maquina.nombre, autor="Dup", url="https://blog.test/dup").count() == 1
        assert PendingWriteup.query.count() == 0


class TestDeleteWriteupSubido:
    """Ambas rutas de borrado de un writeup publicado deben comportarse
    igual: se verifica expresamente que no es solo una suposición."""

    @pytest.mark.parametrize(
        "path_tpl,method_name",
        [
            ("/api/writeups/subidos/{id}/delete", "post"),
            ("/api/writeups_subidos/{id}", "delete"),
        ],
    )
    def test_both_routes_delete_recalculate_and_revoke_certificate(
        self, client, login_as, db, path_tpl, method_name
    ):
        from dockerlabs.models import Certificate, Writeup, WriteupRanking
        from tests.factories import make_certificate

        author = make_user(db, role="jugador", username="DelAuthor")
        maquina = make_machine(db, origen="docker", autor=author.username, dificultad="Fácil")
        writeup = make_writeup(db, maquina=maquina.nombre, autor=author.username)
        writeup_id = writeup.id  # ver nota en TestEliminar.test_admin_can_delete
        make_certificate(db, user=author, machine_name=maquina.nombre)

        admin = _admin(db)
        csrf = login_as(admin)
        method = getattr(client, method_name)
        r = method(path_tpl.format(id=writeup_id), headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text

        db.session.rollback()
        assert Writeup.query.filter_by(id=writeup_id).first() is None
        assert WriteupRanking.query.filter_by(nombre=author.username).first() is None
        assert Certificate.query.filter_by(user_id=author.id, machine_name=maquina.nombre).first() is None

    def test_jugador_forbidden(self, client, login_as, db):
        maquina = make_machine(db)
        writeup = make_writeup(db, maquina=maquina.nombre, autor=maquina.autor)
        user = _jugador(db)
        csrf = login_as(user)
        r = client.post(f"/api/writeups/subidos/{writeup.id}/delete", headers=csrf_headers(csrf))
        assert r.status_code == 403


class TestReportWriteup:
    def test_requires_login(self, client, db):
        maquina = make_machine(db)
        writeup = make_writeup(db, maquina=maquina.nombre, autor=maquina.autor)
        r = client.post(f"/api/writeups/{writeup.id}/report", json={"reason": "spam"})
        assert r.status_code == 401

    def test_succeeds_without_csrf_header(self, client, login_as, db):
        # HALLAZGO: a diferencia de TODAS sus rutas hermanas de escritura
        # (aprobar, borrar, dismiss, delete-batch...), esta ruta
        # (`api_report_writeup` en dockerlabs/routes/writeups.py) NO declara
        # `csrf_ok: bool = Depends(verify_csrf_token)` en su firma. Una
        # sesión autenticada por cookie puede por tanto reportar un writeup
        # sin enviar `X-CSRFToken`, lo que en teoría permite que un sitio de
        # terceros fuerce esta petición desde el navegador de la víctima
        # (CSRF clásico, impacto bajo: solo crea una fila `WriteupReport`).
        # Se fija aquí el comportamiento ACTUAL (acepta sin CSRF) sin
        # "arreglar" nada en el código de la app -- fuera de alcance de este
        # archivo de tests.
        maquina = make_machine(db)
        writeup = make_writeup(db, maquina=maquina.nombre, autor=maquina.autor)
        user = _jugador(db)
        login_as(user)  # cookie puesta, pero no se manda X-CSRFToken
        r = client.post(f"/api/writeups/{writeup.id}/report", json={"reason": "spam"})
        assert r.status_code == 200, r.text

    def test_nonexistent_writeup_404(self, client, login_as, db):
        user = _jugador(db)
        login_as(user)
        r = client.post("/api/writeups/999999/report", json={"reason": "spam"})
        assert r.status_code == 404


class TestGetWriteupsByMachine:
    def test_public_and_emoji_mapping(self, client, db):
        maquina = make_machine(db, nombre="EmojiMachine")
        make_writeup(db, maquina="EmojiMachine", autor="VideoAuthor", tipo="video")
        make_writeup(db, maquina="EmojiMachine", autor="TextAuthor", tipo="texto")

        r = client.get("/api/writeups/EmojiMachine")
        assert r.status_code == 200
        body = r.json()
        by_name = {item["name"]: item["type"] for item in body}
        assert by_name["VideoAuthor"] == "🎥"
        assert by_name["TextAuthor"] == "📝"
