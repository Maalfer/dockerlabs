"""Tests del endpoint SSE de análisis de writeups y sus rutas hermanas, en
dockerlabs/routes/writeups.py (todas en `api_router`, prefijo `/api`):

  GET  /api/writeups-analisis                (SSE, admin/moderador)
  POST /api/writeups-analisis/dismiss/{id}   (admin/moderador, CSRF)
  POST /api/writeups-analisis/delete-batch   (admin/moderador, CSRF)

El endpoint SSE hace peticiones HTTP salientes reales con `httpx` para
comprobar si cada writeup sigue vivo; aquí se parchea siempre
`httpx.AsyncClient` y `dockerlabs.validators.is_public_http_url` para que
ningún test dispare tráfico de red real.
"""
import json

import pytest

from tests.conftest import csrf_headers
from tests.factories import make_machine, make_user, make_writeup

pytestmark = pytest.mark.integration

ANALISIS_URL = "/api/writeups-analisis"


def _admin(db):
    return make_user(db, role="admin")


def _jugador(db):
    return make_user(db, role="jugador")


def _consume_sse(response):
    """El TestClient (sin usar `.stream()`) devuelve el `StreamingResponse`
    ya totalmente bufferizado en `response.text`; cada evento SSE ocupa una
    única línea `data: {...}` seguida de una línea en blanco."""
    events = []
    for line in response.text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: "):]))
    return events


class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class _FakeAsyncClient:
    """Doble mínimo de `httpx.AsyncClient` usado como context manager async,
    con `head`/`get` devolviendo un status fijo configurable por test."""

    _status = 200

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def head(self, url):
        return _FakeResponse(self._status)

    async def get(self, url):
        return _FakeResponse(self._status)


def _make_fake_async_client(status_code):
    class _Client(_FakeAsyncClient):
        _status = status_code

    return _Client


class TestRoleGating:
    def test_anonymous_forbidden(self, client):
        r = client.get(ANALISIS_URL)
        assert r.status_code == 403

    def test_jugador_forbidden(self, client, login_as, db):
        jugador = _jugador(db)
        login_as(jugador)
        r = client.get(ANALISIS_URL)
        assert r.status_code == 403


class TestSSRFGuard:
    def test_blocked_url_never_reaches_http_client(self, client, login_as, db, monkeypatch):
        admin = _admin(db)
        maquina = make_machine(db)
        make_writeup(db, maquina=maquina.nombre, autor=maquina.autor, url="http://internal.example.test/secret")

        monkeypatch.setattr("dockerlabs.validators.is_public_http_url", lambda url: (False, "blocked"))

        class _ExplodingAsyncClient:
            def __init__(self, *args, **kwargs):
                raise AssertionError(
                    "httpx.AsyncClient no deberia instanciarse nunca: el guard "
                    "SSRF (is_public_http_url) tiene que cortar antes de llegar "
                    "a hacer la peticion HTTP real"
                )

        monkeypatch.setattr("httpx.AsyncClient", _ExplodingAsyncClient)

        login_as(admin)
        r = client.get(ANALISIS_URL)
        assert r.status_code == 200
        events = _consume_sse(r)
        complete = [e for e in events if e["type"] == "complete"]
        assert complete, events
        assert complete[-1]["total_rotos"] == 0


class TestStatusDetection:
    def test_404_is_recorded_as_broken(self, client, login_as, db, monkeypatch):
        from dockerlabs.models import WriteupAnalysisResult

        admin = _admin(db)
        maquina = make_machine(db)
        writeup = make_writeup(db, maquina=maquina.nombre, autor=maquina.autor, url="https://ok.example.test/404")

        monkeypatch.setattr("dockerlabs.validators.is_public_http_url", lambda url: (True, None))
        monkeypatch.setattr("httpx.AsyncClient", _make_fake_async_client(404))

        login_as(admin)
        r = client.get(ANALISIS_URL)
        assert r.status_code == 200
        events = _consume_sse(r)
        complete = [e for e in events if e["type"] == "complete"][-1]
        assert complete["total_rotos"] == 1
        assert complete["rotos"][0]["id"] == writeup.id

        db.session.rollback()
        saved = WriteupAnalysisResult.query.filter_by(writeup_id=writeup.id).first()
        assert saved is not None
        assert saved.status == 404
        assert saved.dismissed is False

    def test_200_is_not_recorded_as_broken(self, client, login_as, db, monkeypatch):
        from dockerlabs.models import WriteupAnalysisResult

        admin = _admin(db)
        maquina = make_machine(db)
        writeup = make_writeup(db, maquina=maquina.nombre, autor=maquina.autor, url="https://ok.example.test/200")

        monkeypatch.setattr("dockerlabs.validators.is_public_http_url", lambda url: (True, None))
        monkeypatch.setattr("httpx.AsyncClient", _make_fake_async_client(200))

        login_as(admin)
        r = client.get(ANALISIS_URL)
        assert r.status_code == 200
        events = _consume_sse(r)
        complete = [e for e in events if e["type"] == "complete"][-1]
        assert complete["total_rotos"] == 0

        db.session.rollback()
        assert WriteupAnalysisResult.query.filter_by(writeup_id=writeup.id).first() is None


class TestDismiss:
    def _url(self, writeup_id):
        return f"/api/writeups-analisis/dismiss/{writeup_id}"

    def test_jugador_forbidden(self, client, login_as, db):
        jugador = _jugador(db)
        csrf = login_as(jugador)
        r = client.post(self._url(1), headers=csrf_headers(csrf))
        assert r.status_code == 403

    def test_admin_marks_result_dismissed(self, client, login_as, db):
        from dockerlabs.models import WriteupAnalysisResult

        admin = _admin(db)
        maquina = make_machine(db)
        writeup = make_writeup(db, maquina=maquina.nombre, autor=maquina.autor)
        result = WriteupAnalysisResult(
            writeup_id=writeup.id, maquina=maquina.nombre, autor=maquina.autor,
            url=writeup.url, tipo=writeup.tipo, status=404, dismissed=False,
        )
        db.session.add(result)
        db.session.commit()

        csrf = login_as(admin)
        r = client.post(self._url(writeup.id), headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text

        db.session.rollback()
        refreshed = WriteupAnalysisResult.query.filter_by(writeup_id=writeup.id).first()
        assert refreshed.dismissed is True

    def test_nonexistent_result_404(self, client, login_as, db):
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(self._url(999999), headers=csrf_headers(csrf))
        assert r.status_code == 404


class TestDeleteBatch:
    URL = "/api/writeups-analisis/delete-batch"

    def test_jugador_forbidden(self, client, login_as, db):
        jugador = _jugador(db)
        csrf = login_as(jugador)
        r = client.post(self.URL, json={"ids": [1]}, headers=csrf_headers(csrf))
        assert r.status_code == 403

    def test_empty_list_rejected(self, client, login_as, db):
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(self.URL, json={"ids": []}, headers=csrf_headers(csrf))
        assert r.status_code == 400

    def test_missing_ids_key_rejected(self, client, login_as, db):
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(self.URL, json={}, headers=csrf_headers(csrf))
        assert r.status_code == 400

    def test_deletes_given_ids(self, client, login_as, db):
        from dockerlabs.models import Writeup

        admin = _admin(db)
        maquina = make_machine(db)
        w1 = make_writeup(db, maquina=maquina.nombre, autor=maquina.autor)
        w2 = make_writeup(db, maquina=maquina.nombre, autor=maquina.autor)
        w1_id, w2_id = w1.id, w2.id  # ver nota en TestEliminar.test_admin_can_delete
        # (test_machines_crud.py): tras borrarlas y hacer rollback(), tocar
        # `.id` sobre los objetos ORM ya expirados/borrados revienta con
        # ObjectDeletedError en vez de devolver None.
        csrf = login_as(admin)
        r = client.post(self.URL, json={"ids": [w1_id, w2_id]}, headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text
        assert r.json()["deleted"] == 2
        db.session.rollback()
        assert Writeup.query.filter_by(id=w1_id).first() is None
        assert Writeup.query.filter_by(id=w2_id).first() is None

    def test_non_numeric_id_aborts_whole_batch_with_500(self, client, login_as, db):
        # HALLAZGO: el parseo `int(wid)` de cada id vive DENTRO del mismo
        # try/except genérico que hace los deletes y el commit (ver
        # api_delete_writeups_batch en dockerlabs/routes/writeups.py). Un id
        # no numérico dispara un ValueError de Python sin ningún manejo
        # específico; lo atrapa el `except Exception` de la ruta, que hace
        # rollback y devuelve 500 con el texto crudo de la excepción (p.ej.
        # "invalid literal for int() with base 10: ..."), filtrando detalle
        # interno al cliente en vez de un 400 de validación. Además, como
        # todo vive en una única transacción, el id numérico válido que iba
        # ANTES en la lista tampoco se borra: el commit nunca se alcanza.
        # Se fija aquí el comportamiento ACTUAL, sin "arreglarlo".
        from dockerlabs.models import Writeup

        admin = _admin(db)
        maquina = make_machine(db)
        w1 = make_writeup(db, maquina=maquina.nombre, autor=maquina.autor)
        csrf = login_as(admin)
        r = client.post(
            self.URL,
            json={"ids": [w1.id, "not-a-number"]},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 500
        assert "invalid literal" in r.json()["error"]
        db.session.rollback()
        assert Writeup.query.get(w1.id) is not None  # nada se borro: rollback de todo el batch
