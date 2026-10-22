"""Tests de dockerlabs/routes/bunkerlabs_pages.py — páginas de BunkerLabs.

IMPORTANTE (ver nota al final del fichero): la suite de tests de esta sesión
fue encargada asumiendo que `bunkerlabs_home` ya combinaba los flags
`bunkerlabs_anonymous`/`bunkerlabs_unauthenticated` guardados en sesión con una
comprobación EN VIVO de `session.get("user_id")`, y que `bunkerlabs_logout` ya
limpiaba esos dos flags. Al leer el código fuente real de
`dockerlabs/routes/bunkerlabs_pages.py` en ESTE clon, ninguna de las dos cosas
está así: `bunkerlabs_home` lee `is_anonymous`/`is_unauthenticated_guest`
directamente de los flags guardados en sesión sin ninguna comprobación en
vivo, y `bunkerlabs_logout` solo limpia
`("bunkerlabs_ok", "bunkerlabs_guest", "bunkerlabs_nombre", "bunkerlabs_id")`,
sin tocar `bunkerlabs_anonymous` ni `bunkerlabs_unauthenticated`. Los dos tests
de regresión de abajo están escritos para afirmar el comportamiento CORRECTO
(el que se pidió proteger) y por tanto están en rojo contra el código actual;
no se ha debilitado la aserción ni se ha tocado `dockerlabs/routes/
bunkerlabs_pages.py` para forzarlos a pasar (está fuera de alcance tocar
fuente de aplicación). Ver el resumen final para más detalle.
"""
import uuid

import pytest

from tests.factories import make_bunker_token, make_machine, make_user

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# El bug de regresión: flags de bunker "congelados" de una visita anónima
# anterior, que sobreviven a un login real posterior.
# ---------------------------------------------------------------------------


class TestAnonymousFlagStaleness:
    def test_regression_live_login_clears_stale_anonymous_banner(self, client, auth, db):
        """Escenario exacto del bug: el usuario visitó /bunkerlabs como
        invitado/anónimo en algún momento (quedan `bunkerlabs_anonymous=True` y
        `bunkerlabs_unauthenticated=True` en la sesión) y DESPUÉS inició sesión
        de verdad en DockerLabs (`session["user_id"]` ya está puesto). La
        home de BunkerLabs no debe seguir mostrando el banner de "anónimo"/
        "invitado sin cuenta": el usuario ya no lo es."""
        user = make_user(db, role="jugador")
        sid = f"test-sid-{uuid.uuid4().hex}"
        cookie = auth.create_session_cookie(
            user.id,
            user.username,
            user.role,
            existing_session={
                "bunkerlabs_ok": True,
                "bunkerlabs_anonymous": True,
                "bunkerlabs_unauthenticated": True,
                "bunkerlabs_nombre": "Anónimo",
            },
            _id=sid,
        )
        client.cookies.set("session", cookie)

        r = client.get("/bunkerlabs")
        assert r.status_code == 200
        html = r.text.lower()
        assert "accediendo como usuario anónimo" not in html, (
            "Regresión: la sesión tiene user_id de un login real pero sigue "
            "mostrando el banner de anónimo porque bunkerlabs_home() no "
            "combina el flag guardado con una comprobación en vivo de "
            "session.get('user_id')."
        )
        assert "accediendo como invitado sin cuenta" not in html, (
            "Regresión: mismo problema con bunkerlabs_unauthenticated."
        )

    def test_negative_control_genuinely_anonymous_session_shows_banner(self, client, auth):
        """Control negativo: una sesión de bunker REALMENTE anónima (sin
        user_id en absoluto) sí debe mostrar el banner. Esto confirma que el
        test anterior falla por el flag obsoleto y no porque el banner esté
        roto en general."""
        session_dict = {
            "bunkerlabs_ok": True,
            "bunkerlabs_anonymous": True,
            "bunkerlabs_unauthenticated": True,
            "bunkerlabs_nombre": "Anónimo",
        }
        cookie = auth.encode_session_cookie(session_dict)
        client.cookies.set("session", cookie)

        r = client.get("/bunkerlabs")
        assert r.status_code == 200
        assert "accediendo como usuario anónimo" in r.text.lower()

    def test_regression_logout_clears_anonymous_and_unauthenticated_flags(self, client, auth):
        """`bunkerlabs_logout` debe limpiar TODOS los flags de bunker de la
        sesión, incluidos `bunkerlabs_anonymous`/`bunkerlabs_unauthenticated`;
        si no, el banner puede quedar "congelado" para la siguiente visita
        aunque el usuario haya cerrado sesión de bunker."""
        session_dict = {
            "bunkerlabs_ok": True,
            "bunkerlabs_guest": True,
            "bunkerlabs_anonymous": True,
            "bunkerlabs_unauthenticated": True,
            "bunkerlabs_nombre": "Invitado",
            "bunkerlabs_id": None,
        }
        cookie = auth.encode_session_cookie(session_dict)
        client.cookies.set("session", cookie)

        r = client.get("/bunkerlabs/logout", follow_redirects=False)
        assert r.status_code == 302

        # Leer el Set-Cookie de ESTA respuesta directamente (no
        # client.cookies.get, que aquí puede ambigüar entre cookies con
        # distinto path/domain en el jar y lanzar CookieConflict).
        new_cookie = r.cookies["session"]
        payload = auth.get_session_serializer().loads(new_cookie)
        for key in ("bunkerlabs_ok", "bunkerlabs_guest", "bunkerlabs_nombre", "bunkerlabs_id"):
            assert key not in payload
        for key in ("bunkerlabs_anonymous", "bunkerlabs_unauthenticated"):
            assert key not in payload, (
                f"Regresión: bunkerlabs_logout() no limpia '{key}'; queda "
                "congelado para la próxima sesión que reutilice esta cookie."
            )


# ---------------------------------------------------------------------------
# /bunkerlabs/login
# ---------------------------------------------------------------------------


class TestLoginPage:
    def test_get_redirects_immediately_if_already_has_access(self, client, auth):
        cookie = auth.encode_session_cookie({"bunkerlabs_ok": True})
        client.cookies.set("session", cookie)

        r = client.get("/bunkerlabs/login", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/bunkerlabs"

    def test_post_correct_token_grants_access_and_logs(self, client, db):
        token = make_bunker_token(db, nombre="Invitado", token="pin-correcto-1")

        r = client.post("/bunkerlabs/login", data={"password": "pin-correcto-1"}, follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"].startswith("/bunkerlabs")

        cookie = r.cookies["session"]
        from dockerlabs import routers
        payload = routers.get_session_serializer().loads(cookie)
        assert payload.get("bunkerlabs_ok") is True

        db.session.rollback()
        from bunkerlabs.models import BunkerAccessLog
        assert BunkerAccessLog.query.filter_by(token_id=token.id).count() == 1

    def test_post_wrong_token_shows_error_without_granting_access(self, client, db):
        make_bunker_token(db, token="pin-correcto-2")

        r = client.post("/bunkerlabs/login", data={"password": "esto-no-es-el-pin"})
        assert r.status_code == 200
        assert "incorrecta" in r.text.lower()

        # Confirmar que NO se concedió acceso: un GET posterior debe seguir
        # mostrando el formulario de login (no redirigir a /bunkerlabs).
        r2 = client.get("/bunkerlabs/login", follow_redirects=False)
        assert r2.status_code == 200


# ---------------------------------------------------------------------------
# /bunkerlabs/guest
# ---------------------------------------------------------------------------


class TestGuestAccess:
    def test_grants_access_unconditionally_without_token(self, client, auth):
        r = client.get("/bunkerlabs/guest", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/bunkerlabs"

        cookie = r.cookies["session"]
        payload = auth.get_session_serializer().loads(cookie)
        assert payload["bunkerlabs_ok"] is True
        assert payload["bunkerlabs_guest"] is True


# ---------------------------------------------------------------------------
# /bunkerlabs (enlace compartido ?token=... y ?maquina=...)
# ---------------------------------------------------------------------------


class TestSharedLinkAutoAuth:
    def test_valid_active_token_autogrants_access_and_logs(self, client, db):
        token = make_bunker_token(db, nombre="Compartido", token="shared-token-ok")

        r = client.get("/bunkerlabs", params={"token": "shared-token-ok"})
        assert r.status_code == 200

        db.session.rollback()
        from bunkerlabs.models import BunkerAccessLog
        assert BunkerAccessLog.query.filter_by(token_id=token.id).count() == 1

    def test_invalid_token_redirects_to_login_with_error(self, client):
        r = client.get("/bunkerlabs", params={"token": "no-existe-este-token"}, follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/bunkerlabs/login"

    def test_inactive_token_redirects_to_login_with_error(self, client, db):
        make_bunker_token(db, token="shared-token-inactivo", activo=0)

        r = client.get("/bunkerlabs", params={"token": "shared-token-inactivo"}, follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/bunkerlabs/login"

    def test_maquina_param_without_bunker_session_autogrants_guest(self, client, db, auth):
        make_machine(db, origen="bunker", nombre="MaquinaCompartidaX")

        r = client.get("/bunkerlabs", params={"maquina": "MaquinaCompartidaX"}, follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/bunkerlabs?maquina=MaquinaCompartidaX"

        cookie = r.cookies["session"]
        payload = auth.get_session_serializer().loads(cookie)
        assert payload["bunkerlabs_ok"] is True
        assert payload["bunkerlabs_guest"] is True


# ---------------------------------------------------------------------------
# /bunkerlabs/maquinas/{id}/descargar
# ---------------------------------------------------------------------------


class TestDescargarMaquina:
    def test_guest_blocked_from_non_guest_access_machine(self, client, db, auth):
        maquina = make_machine(db, origen="bunker", guest_access=False, nombre="RestringidaInvitado")
        cookie = auth.encode_session_cookie({"bunkerlabs_ok": True, "bunkerlabs_guest": True})
        client.cookies.set("session", cookie)

        r = client.get(f"/bunkerlabs/maquinas/{maquina.id}/descargar", follow_redirects=False)
        assert r.status_code == 302
        assert "maquina=" in r.headers["location"]

        db.session.rollback()
        db.session.refresh(maquina)
        assert maquina.descargas == 0

    def test_guest_can_download_guest_access_machine_and_it_counts(self, client, db, auth):
        maquina = make_machine(db, origen="bunker", guest_access=True, nombre="PermitidaInvitado")
        cookie = auth.encode_session_cookie({"bunkerlabs_ok": True, "bunkerlabs_guest": True})
        client.cookies.set("session", cookie)

        r = client.get(f"/bunkerlabs/maquinas/{maquina.id}/descargar")
        assert r.status_code == 200

        db.session.rollback()
        db.session.refresh(maquina)
        assert maquina.descargas == 1

        from dockerlabs.models import MachineDownloadLog
        assert MachineDownloadLog.query.filter_by(machine_id=maquina.id).count() == 1

    def test_non_guest_session_download_increments_and_logs(self, client, db, auth):
        maquina = make_machine(db, origen="bunker", guest_access=False, nombre="DescargaNormal")
        cookie = auth.encode_session_cookie({"bunkerlabs_ok": True})
        client.cookies.set("session", cookie)

        r = client.get(f"/bunkerlabs/maquinas/{maquina.id}/descargar")
        assert r.status_code == 200

        db.session.rollback()
        db.session.refresh(maquina)
        assert maquina.descargas == 1


# ---------------------------------------------------------------------------
# /bunkerlabs/gestion
# ---------------------------------------------------------------------------


class TestGestion:
    def test_anonymous_redirected_to_login(self, client):
        r = client.get("/bunkerlabs/gestion", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/login"

    def test_non_admin_redirected_home(self, client, login_as, db):
        jugador = make_user(db, role="jugador")
        login_as(jugador)
        r = client.get("/bunkerlabs/gestion", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/"

    def test_admin_can_create_token(self, client, login_as, db):
        admin = make_user(db, role="admin")
        csrf = login_as(admin)

        r = client.post(
            "/bunkerlabs/gestion",
            data={"nombre": "Nuevo Acceso", "password": "pin-nuevo-acceso"},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 200
        assert "creado correctamente" in r.text.lower()

        db.session.rollback()
        from bunkerlabs.models import BunkerAccessToken
        assert BunkerAccessToken.query.filter_by(token="pin-nuevo-acceso").first() is not None

    def test_duplicate_token_value_shows_friendly_error_not_500(self, client, login_as, db):
        make_bunker_token(db, token="pin-duplicado")
        admin = make_user(db, role="admin")
        csrf = login_as(admin)

        r = client.post(
            "/bunkerlabs/gestion",
            data={"nombre": "Otro Nombre", "password": "pin-duplicado"},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 200
        assert "ya existe" in r.text.lower()


class TestDeleteToken:
    def test_admin_with_csrf_deletes_token(self, client, login_as, db):
        admin = make_user(db, role="admin")
        token = make_bunker_token(db)
        token_id = token.id  # leer el PK ANTES del rollback (ver nota abajo)
        csrf = login_as(admin)

        r = client.post(
            f"/bunkerlabs/gestion/{token_id}/delete",
            headers={"X-CSRFToken": csrf},
            follow_redirects=False,
        )
        assert r.status_code == 302

        db.session.rollback()
        from bunkerlabs.models import BunkerAccessToken
        # OJO: tras el rollback, `token` queda expirado; tocar CUALQUIER
        # atributo suyo (incluido .id) dispara un refresh desde BD, y como la
        # fila ya no existe (el endpoint la borró) eso lanza ObjectDeletedError
        # en vez de simplemente devolver None. Por eso se guardó `token_id`
        # ANTES del rollback y se consulta por filter_by(), no por .get() ni
        # tocando el objeto expirado.
        assert BunkerAccessToken.query.filter_by(id=token_id).first() is None

    def test_without_csrf_rejected(self, client, login_as, db):
        admin = make_user(db, role="admin")
        token = make_bunker_token(db)
        login_as(admin)

        r = client.post(f"/bunkerlabs/gestion/{token.id}/delete")
        assert r.status_code == 403

    def test_non_admin_rejected(self, client, login_as, db):
        jugador = make_user(db, role="jugador")
        token = make_bunker_token(db)
        csrf = login_as(jugador)

        r = client.post(f"/bunkerlabs/gestion/{token.id}/delete", headers={"X-CSRFToken": csrf})
        assert r.status_code == 403
