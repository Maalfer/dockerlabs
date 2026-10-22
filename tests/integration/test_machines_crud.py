"""Tests de dockerlabs/routes/machines.py — CRUD de máquinas (actualizar,
eliminar, alta vía /add-maquina, página de descarga).

Rutas cubiertas (todas montadas o bien en `api_router`, prefijo `/api`, o en
`pages_router`, sin prefijo — ver `dockerlabs/routers.py`):
  POST /api/gestion-maquinas/actualizar
  POST /api/gestion-maquinas/eliminar
  GET  /add-maquina
  POST /api/add-maquina
  GET  /maquinas/{id}/descargar
"""
import pytest

from tests.conftest import csrf_headers
from tests.factories import make_machine, make_user

pytestmark = pytest.mark.integration

# NOTA: `dockerlabs.models` (y cualquier otro import de `dockerlabs.*`) se
# importa SIEMPRE dentro de cada test, nunca a nivel de módulo: igual que en
# conftest.py/factories.py, `DATABASE_URL` todavía no está fijada cuando
# pytest recolecta este fichero si el import se hiciera arriba.


def _admin(db):
    return make_user(db, role="admin")


def _mod(db):
    return make_user(db, role="moderador")


def _jugador(db, **overrides):
    return make_user(db, role="jugador", **overrides)


def _edit_payload(maquina, **overrides):
    payload = {
        "id": str(maquina.id),
        "origen": maquina.origen,
        "nombre": maquina.nombre,
        "dificultad": maquina.dificultad,
        "autor": maquina.autor,
        "enlace_autor": maquina.enlace_autor or "",
        "fecha": maquina.fecha,
        "imagen": "",
        "descripcion": maquina.descripcion,
        "link_descarga": maquina.link_descarga,
        "categoria": "",
    }
    payload.update(overrides)
    return payload


ACTUALIZAR_URL = "/api/gestion-maquinas/actualizar"
ELIMINAR_URL = "/api/gestion-maquinas/eliminar"


class TestActualizarPermisos:
    def test_admin_can_edit_any_machine(self, client, login_as, db):
        from dockerlabs.models import Machine
        maquina = make_machine(db, autor="OtroAutor")
        admin = _admin(db)
        csrf = login_as(admin)
        payload = _edit_payload(maquina, nombre="EditadoPorAdmin")
        r = client.post(ACTUALIZAR_URL, data=payload, headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text
        db.session.rollback()
        assert Machine.query.get(maquina.id).nombre == "EditadoPorAdmin"

    def test_moderador_can_edit_any_machine(self, client, login_as, db):
        from dockerlabs.models import Machine
        maquina = make_machine(db, autor="OtroAutor2")
        mod = _mod(db)
        csrf = login_as(mod)
        payload = _edit_payload(maquina, nombre="EditadoPorMod")
        r = client.post(ACTUALIZAR_URL, data=payload, headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text
        db.session.rollback()
        assert Machine.query.get(maquina.id).nombre == "EditadoPorMod"

    def test_jugador_can_edit_own_machine(self, client, login_as, db):
        from dockerlabs.models import Machine
        jugador = _jugador(db)
        maquina = make_machine(db, autor=jugador.username)
        csrf = login_as(jugador)
        payload = _edit_payload(maquina, nombre="EditadoPorDueno")
        r = client.post(ACTUALIZAR_URL, data=payload, headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text
        db.session.rollback()
        assert Machine.query.get(maquina.id).nombre == "EditadoPorDueno"

    def test_jugador_cannot_edit_others_machine(self, client, login_as, db):
        from dockerlabs.models import Machine
        jugador = _jugador(db)
        maquina = make_machine(db, autor="NoEsElJugador")
        csrf = login_as(jugador)
        payload = _edit_payload(maquina, nombre="Intento")
        r = client.post(ACTUALIZAR_URL, data=payload, headers=csrf_headers(csrf))
        assert r.status_code == 403
        db.session.rollback()
        assert Machine.query.get(maquina.id).nombre == maquina.nombre  # sin cambios

    def test_jugador_submitting_different_autor_does_not_reassign_authorship(self, client, login_as, db):
        from dockerlabs.models import Machine
        jugador = _jugador(db)
        maquina = make_machine(db, autor=jugador.username)
        csrf = login_as(jugador)
        payload = _edit_payload(maquina, autor="UsuarioRobado")
        r = client.post(ACTUALIZAR_URL, data=payload, headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text
        db.session.rollback()
        assert Machine.query.get(maquina.id).autor == jugador.username


class TestActualizarValidaciones:
    @pytest.mark.parametrize("bad_nombre", ["<script>", 'nombre"malo', "nombre'malo", "nombre`malo"])
    def test_nombre_dangerous_chars_rejected(self, client, login_as, db, bad_nombre):
        maquina = make_machine(db)
        admin = _admin(db)
        csrf = login_as(admin)
        payload = _edit_payload(maquina, nombre=bad_nombre)
        r = client.post(ACTUALIZAR_URL, data=payload, headers=csrf_headers(csrf))
        assert r.status_code == 400

    def test_link_descarga_invalid_rejected(self, client, login_as, db):
        maquina = make_machine(db)
        admin = _admin(db)
        csrf = login_as(admin)
        payload = _edit_payload(maquina, link_descarga="javascript:alert(1)")
        r = client.post(ACTUALIZAR_URL, data=payload, headers=csrf_headers(csrf))
        assert r.status_code == 400
        assert "descarga" in r.json()["error"].lower()

    def test_enlace_autor_invalid_rejected(self, client, login_as, db):
        maquina = make_machine(db)
        admin = _admin(db)
        csrf = login_as(admin)
        payload = _edit_payload(maquina, enlace_autor="javascript:alert(1)")
        r = client.post(ACTUALIZAR_URL, data=payload, headers=csrf_headers(csrf))
        assert r.status_code == 400
        assert "autor" in r.json()["error"].lower()


class TestActualizarRecalculoRanking:
    def test_bunker_edit_does_not_trigger_creator_ranking(self, client, login_as, db):
        from dockerlabs.models import CreatorRanking
        maquina = make_machine(db, origen="bunker", autor="AutorBunkerRanking")
        admin = _admin(db)
        csrf = login_as(admin)
        payload = _edit_payload(maquina, descripcion="otra descripcion")
        r = client.post(ACTUALIZAR_URL, data=payload, headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text
        db.session.rollback()
        assert CreatorRanking.query.filter_by(nombre="AutorBunkerRanking").first() is None

    def test_docker_edit_triggers_creator_ranking(self, client, login_as, db):
        from dockerlabs.models import CreatorRanking
        maquina = make_machine(db, origen="docker", autor="AutorDockerRanking")
        admin = _admin(db)
        csrf = login_as(admin)
        payload = _edit_payload(maquina, descripcion="otra descripcion")
        r = client.post(ACTUALIZAR_URL, data=payload, headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text
        db.session.rollback()
        row = CreatorRanking.query.filter_by(nombre="AutorDockerRanking").first()
        assert row is not None
        assert row.maquinas == 1

    def test_categoria_field_creates_and_clears_category_row(self, client, login_as, db):
        from dockerlabs.models import Category
        maquina = make_machine(db, origen="docker")
        admin = _admin(db)
        csrf = login_as(admin)

        payload = _edit_payload(maquina, categoria="web")
        r = client.post(ACTUALIZAR_URL, data=payload, headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text
        db.session.rollback()
        cat = Category.query.filter_by(machine_id=maquina.id, origen="docker").first()
        assert cat is not None and cat.categoria == "web"

        payload2 = _edit_payload(maquina, categoria="")
        r2 = client.post(ACTUALIZAR_URL, data=payload2, headers=csrf_headers(csrf))
        assert r2.status_code == 200, r2.text
        db.session.rollback()
        assert Category.query.filter_by(machine_id=maquina.id, origen="docker").first() is None


class TestEliminar:
    def test_admin_can_delete(self, client, login_as, db):
        # NOTA: `maquina_id`/`origen` se capturan en variables ANTES de borrar
        # la fila. Tras `db.session.rollback()`, el objeto ORM `maquina`
        # queda expirado; si la fila ya no existe (la borramos), tocar
        # CUALQUIER atributo suyo (incluido `.id`) dispara un refresh que
        # revienta con `ObjectDeletedError` en vez de devolver None. Por eso
        # nunca se vuelve a leer un atributo de `maquina` después del borrado.
        from dockerlabs.models import Machine
        maquina = make_machine(db)
        maquina_id, origen = maquina.id, maquina.origen
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(ELIMINAR_URL, data={"id": str(maquina_id), "origen": origen}, headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text
        db.session.rollback()
        assert Machine.query.filter_by(id=maquina_id).first() is None

    def test_moderador_can_delete(self, client, login_as, db):
        from dockerlabs.models import Machine
        maquina = make_machine(db)
        maquina_id, origen = maquina.id, maquina.origen
        mod = _mod(db)
        csrf = login_as(mod)
        r = client.post(ELIMINAR_URL, data={"id": str(maquina_id), "origen": origen}, headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text
        db.session.rollback()
        assert Machine.query.filter_by(id=maquina_id).first() is None

    def test_jugador_forbidden_even_for_own_machine(self, client, login_as, db):
        from dockerlabs.models import Machine
        jugador = _jugador(db)
        maquina = make_machine(db, autor=jugador.username)
        csrf = login_as(jugador)
        r = client.post(ELIMINAR_URL, data={"id": str(maquina.id), "origen": maquina.origen}, headers=csrf_headers(csrf))
        assert r.status_code == 403
        db.session.rollback()
        assert Machine.query.get(maquina.id) is not None


class TestAddMaquinaPage:
    """GET /add-maquina usa `require_auth_and_role`, que SIEMPRE redirige
    (302) en vez de devolver 401/403: sin sesión -> /login, con sesión pero
    rol no permitido -> /."""

    def test_admin_sees_page(self, client, login_as, db):
        admin = _admin(db)
        login_as(admin)
        r = client.get("/add-maquina")
        assert r.status_code == 200

    def test_jugador_redirected_to_home(self, client, login_as, db):
        jugador = _jugador(db)
        login_as(jugador)
        r = client.get("/add-maquina", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/"

    def test_anonymous_redirected_to_login(self, client):
        r = client.get("/add-maquina", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/login"


class TestAddMaquinaApi:
    def _payload(self, autor, **overrides):
        payload = {
            "nombre": "MaquinaNueva",
            "dificultad": "Fácil",
            "autor": autor,
            "fecha": "2026-03-05",
            "descripcion": "descripcion de prueba",
            "link_descarga": "https://example.test/nueva.zip",
            "imagen": "",
            "destino": "docker",
            "categoria": "",
        }
        payload.update(overrides)
        return payload

    def test_jugador_forbidden(self, client, login_as, db):
        jugador = _jugador(db)
        csrf = login_as(jugador)
        r = client.post("/api/add-maquina", json=self._payload(jugador.username), headers=csrf_headers(csrf))
        assert r.status_code == 403

    def test_autor_must_be_registered_user(self, client, login_as, db):
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post("/api/add-maquina", json=self._payload("usuario_fantasma_404"), headers=csrf_headers(csrf))
        assert r.status_code == 400
        assert "autor" in r.json()["error"].lower()

    def test_fecha_parses_iso_format(self, client, login_as, db, mock_discord):
        from dockerlabs.models import Machine
        admin = _admin(db)
        author = make_user(db, role="jugador")
        csrf = login_as(admin)
        r = client.post("/api/add-maquina", json=self._payload(author.username, nombre="FechaOk"), headers=csrf_headers(csrf))
        assert r.status_code == 200, r.text
        db.session.rollback()
        maquina = Machine.query.filter_by(nombre="FechaOk").first()
        assert maquina.fecha == "05/03/2026"

    def test_invalid_fecha_rejected(self, client, login_as, db):
        admin = _admin(db)
        author = make_user(db, role="jugador")
        csrf = login_as(admin)
        r = client.post(
            "/api/add-maquina",
            json=self._payload(author.username, fecha="no-es-una-fecha"),
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 400

    def test_notify_new_machine_fires_once_with_name(self, client, login_as, db, mock_discord):
        admin = _admin(db)
        author = make_user(db, role="jugador")
        csrf = login_as(admin)
        r = client.post(
            "/api/add-maquina",
            json=self._payload(author.username, nombre="MaquinaConNotificacion"),
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 200, r.text
        assert len(mock_discord) == 1
        assert mock_discord[0]["title"] == "MaquinaConNotificacion"

    def test_destino_bunker_redirect_url(self, client, login_as, db, mock_discord):
        # NOTA: esta ruta no hace un 3xx real; `redirect_url` viaja en el
        # cuerpo JSON para que el frontend navegue con JS. No hay cabecera
        # Location que inspeccionar aquí (a diferencia de /maquinas/{id}/descargar).
        admin = _admin(db)
        author = make_user(db, role="jugador")
        csrf = login_as(admin)
        r = client.post(
            "/api/add-maquina",
            json=self._payload(author.username, nombre="MaquinaBunker", destino="bunker"),
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 200, r.text
        assert r.json()["redirect_url"] == "/bunkerlabs"

    def test_destino_default_redirect_url(self, client, login_as, db, mock_discord):
        admin = _admin(db)
        author = make_user(db, role="jugador")
        csrf = login_as(admin)
        r = client.post(
            "/api/add-maquina",
            json=self._payload(author.username, nombre="MaquinaDocker"),
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 200, r.text
        assert r.json()["redirect_url"] == "/"


class TestDescargarMaquina:
    def test_public_no_login_needed(self, client, db):
        maquina = make_machine(db, origen="docker")
        r = client.get(f"/maquinas/{maquina.id}/descargar")
        assert r.status_code == 200

    def test_increments_counter_and_logs_each_call(self, client, db):
        from dockerlabs.models import Machine, MachineDownloadLog
        maquina = make_machine(db, origen="docker")
        for _ in range(3):
            r = client.get(f"/maquinas/{maquina.id}/descargar")
            assert r.status_code == 200
        db.session.rollback()
        assert Machine.query.get(maquina.id).descargas == 3
        assert MachineDownloadLog.query.filter_by(machine_id=maquina.id).count() == 3

    def test_bunker_origin_redirects_to_bunker_download(self, client, db):
        maquina = make_machine(db, origen="bunker")
        r = client.get(f"/maquinas/{maquina.id}/descargar", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == f"/bunkerlabs/maquinas/{maquina.id}/descargar"

    def test_nonexistent_id_404(self, client, db):
        r = client.get("/maquinas/999999/descargar")
        assert r.status_code == 404
