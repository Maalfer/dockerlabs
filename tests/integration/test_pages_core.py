"""Tests de dockerlabs/routes/pages_core.py: /go/<destino>, index, /dashboard,
/logout, /confirm-email-change y /reset-password.

`_GO_DESTINOS` y `_GO_BOTS` viven como variables de cierre DENTRO de
`register_pages_core_routes` (no son atributos de módulo), así que no se
pueden importar: se copian aquí tal cual estaban en el source en el momento
de escribir este fichero (ver dockerlabs/routes/pages_core.py líneas ~29-33).
Si el source cambia esos valores, estos tests hay que actualizarlos a mano.
"""
import re

import pytest

from tests.factories import make_completed_machine, make_email_change_token, make_machine, make_password_reset_token, make_user

pytestmark = pytest.mark.integration

_GO_DESTINOS_VALIDOS = {
    "newsletter": "https://elrincondelhacker.es/newsletter",
    "academia": "https://elrincondelhacker.es/",
}
_GO_BOTS = ("bot", "crawl", "spider", "curl", "wget", "python-requests", "headless", "preview", "monitor", "facebookexternalhit")


class TestGoExterno:
    def test_unknown_destino_is_404(self, client):
        r = client.get("/go/no-existe", follow_redirects=False)
        assert r.status_code == 404

    @pytest.mark.parametrize("destino,base", list(_GO_DESTINOS_VALIDOS.items()))
    def test_valid_destino_redirects_with_utm_and_no_store(self, client, destino, base):
        r = client.get(f"/go/{destino}", follow_redirects=False)
        assert r.status_code == 302
        location = r.headers["location"]
        assert location == f"{base}?utm_source=dockerlabs&utm_medium=footer&utm_campaign={destino}"
        assert r.headers.get("cache-control") == "no-store"

    def test_origen_param_is_forwarded_when_whitelisted(self, client):
        r = client.get("/go/newsletter?o=home-boton", follow_redirects=False)
        assert r.status_code == 302
        assert "utm_medium=home-boton" in r.headers["location"]

    def test_sqli_like_origen_param_bucketed_as_otro(self, client, db):
        from dockerlabs.models import OutboundClickLog

        r = client.get("/go/newsletter?o=' OR 1=1", follow_redirects=False)
        assert r.status_code == 302
        assert "utm_medium=otro" in r.headers["location"]

        db.session.rollback()  # la petición corrió en otra transacción (ver conftest/gotcha REPEATABLE READ)
        row = OutboundClickLog.query.order_by(OutboundClickLog.id.desc()).first()
        assert row is not None
        assert row.origen == "otro"
        assert row.destino == "newsletter"

    def test_xss_like_origen_param_bucketed_as_otro(self, client, db):
        from dockerlabs.models import OutboundClickLog

        r = client.get("/go/academia?o=<script>alert(1)</script>", follow_redirects=False)
        assert r.status_code == 302
        assert "utm_medium=otro" in r.headers["location"]

        db.session.rollback()
        row = OutboundClickLog.query.order_by(OutboundClickLog.id.desc()).first()
        assert row is not None
        assert row.origen == "otro"

    def test_bot_user_agent_does_not_create_log_row(self, client, db):
        from dockerlabs.models import OutboundClickLog

        db.session.rollback()
        before = OutboundClickLog.query.count()

        bot_ua = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        assert any(b in bot_ua.lower() for b in _GO_BOTS)  # confirma que el UA elegido sí matchea el filtro real
        r = client.get("/go/newsletter", headers={"User-Agent": bot_ua}, follow_redirects=False)
        assert r.status_code == 302  # el bot sigue siendo redirigido; solo no se cuenta

        db.session.rollback()
        after = OutboundClickLog.query.count()
        assert after == before

    def test_normal_user_agent_creates_log_row(self, client, db):
        from dockerlabs.models import OutboundClickLog

        db.session.rollback()
        before = OutboundClickLog.query.count()

        # El TestClient por defecto manda "User-Agent: testclient", que no
        # contiene ninguno de los marcadores de bot: cuenta como "navegador normal".
        r = client.get("/go/newsletter", follow_redirects=False)
        assert r.status_code == 302

        db.session.rollback()
        after = OutboundClickLog.query.count()
        assert after == before + 1

    def test_db_error_while_logging_never_breaks_the_redirect(self, client, db, monkeypatch):
        """El except Exception de go_externo() debe tragarse cualquier fallo al
        loguear el clic. Se fuerza simulando un fallo en db.session.add (el mismo
        objeto scoped_session que usa la app, importado del mismo sitio), sin
        tocar nada del código de aplicación."""

        def _boom(*_a, **_k):
            raise RuntimeError("fallo de BD simulado")

        monkeypatch.setattr(db.session, "add", _boom)
        r = client.get("/go/academia", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"].startswith("https://elrincondelhacker.es/")


class TestIndexPage:
    def test_top_2_newest_machines_appear_first(self, client, db):
        m_old = make_machine(db, nombre="MachineOld", fecha="01/01/2020")
        m_mid = make_machine(db, nombre="MachineMid", fecha="15/06/2022")
        m_new2 = make_machine(db, nombre="MachineNew2", fecha="10/03/2024")
        m_new1 = make_machine(db, nombre="MachineNew1", fecha="20/09/2025")

        r = client.get("/")
        assert r.status_code == 200
        ids_in_order = re.findall(r'data-id="(\d+)"', r.text)
        assert ids_in_order[:2] == [str(m_new1.id), str(m_new2.id)]
        # El resto sigue también en orden descendente de fecha
        assert ids_in_order[2:4] == [str(m_mid.id), str(m_old.id)]

    def test_unparseable_fecha_is_silently_skipped_not_crashing(self, client, db):
        good = make_machine(db, nombre="MachineGood", fecha="01/01/2024")
        bad = make_machine(db, nombre="MachineBadFecha", fecha="not-a-date")

        r = client.get("/")
        assert r.status_code == 200
        assert f'data-id="{good.id}"' in r.text
        assert f'data-id="{bad.id}"' not in r.text

    def test_logged_in_user_sees_completed_machine_marked(self, client, login_as, db):
        user = make_user(db, role="jugador")
        m1 = make_machine(db, nombre="MachineDone", fecha="01/01/2024")
        make_machine(db, nombre="MachineNotDone", fecha="02/01/2024")
        make_completed_machine(db, user_id=user.id, machine_name=m1.nombre)
        login_as(user)

        r = client.get("/")
        assert r.status_code == 200

        pairs = re.findall(r'class="maquina-item ([^"]*)"\s+data-id="(\d+)"', r.text)
        completed_ids = {mid for cls, mid in pairs if "completada" in cls}
        assert str(m1.id) in completed_ids


class TestDashboard:
    def test_logged_out_redirects_to_login(self, client):
        r = client.get("/dashboard", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/login"

    def test_role_outside_allowed_set_is_403(self, client, login_as, db):
        # El esquema no restringe `role` a nivel de BD; si existiera un rol
        # fuera de admin/moderador/jugador, el código sí lo rechaza con 403.
        user = make_user(db, role="baneado")
        login_as(user)
        r = client.get("/dashboard")
        assert r.status_code == 403

    @pytest.mark.parametrize("role", ["admin", "moderador", "jugador"])
    def test_allowed_roles_can_access(self, client, login_as, db, role):
        user = make_user(db, role=role)
        login_as(user)
        r = client.get("/dashboard")
        assert r.status_code == 200

    def test_api_tokens_section_only_for_admin(self, client, login_as, db):
        # NOTA: "Tokens de API" en texto plano NO sirve de marcador por sí solo:
        # el <script> del dashboard trae un comentario JS con ese mismo texto
        # que SIEMPRE se renderiza, sea cual sea el rol (no está dentro del
        # {% if %}). El marcador fiable es un id del HTML que sí vive dentro
        # del bloque `{% if current_user_role == 'admin' %}` (ver plantilla).
        admin = make_user(db, role="admin")
        login_as(admin)
        r = client.get("/dashboard")
        assert 'id="apiTokensTableBody"' in r.text

    @pytest.mark.parametrize("role", ["moderador", "jugador"])
    def test_api_tokens_section_hidden_for_non_admin(self, client, login_as, db, role):
        user = make_user(db, role=role)
        login_as(user)
        r = client.get("/dashboard")
        assert 'id="apiTokensTableBody"' not in r.text


class TestLogout:
    def test_logout_sends_a_real_cookie_deletion_header(self, client, login_as, db):
        """NOTA (hallazgo de infraestructura de test, no de la app): el
        TestClient de Starlette (vía httpx -> http.cookiejar stdlib) NO
        actualiza su jar local cuando recibe un Set-Cookie ya caducado
        (Max-Age=0): `CookieJar.extract_cookies` simplemente descarta la
        cookie entrante por estar expirada, pero no por ello BORRA la que ya
        tenía guardada con el mismo nombre (se comprobó aislado contra
        `http.cookiejar.CookieJar` directamente). Un navegador real SÍ borra
        la cookie al ver `Max-Age=0` (ahí está la semántica real de RFC 6265
        que importa). Por eso este test valida la cabecera Set-Cookie real
        que manda el servidor, no el estado del jar del TestClient."""
        user = make_user(db, role="jugador")
        login_as(user)

        r_before = client.get("/dashboard")
        assert r_before.status_code == 200

        r_logout = client.get("/logout", follow_redirects=False)
        assert r_logout.status_code == 302
        set_cookie = r_logout.headers.get("set-cookie", "")
        assert 'session=""' in set_cookie
        assert "max-age=0" in set_cookie.lower()

        # Simula lo que SÍ haría un navegador real al honrar ese Max-Age=0
        # (el TestClient no lo hace solo, ver nota de clase): limpiamos la
        # cookie a mano y comprobamos que, sin ella, el acceso queda cortado.
        client.cookies.delete("session")
        r_after = client.get("/dashboard", follow_redirects=False)
        assert r_after.status_code == 302
        assert r_after.headers["location"] == "/login"

    def test_old_cookie_value_replayed_manually_still_authenticates(self, client, login_as, db):
        """NOTA sobre el comportamiento real: las sesiones son cookies firmadas
        stateless (itsdangerous), sin almacén de sesiones server-side. /logout
        solo le dice al NAVEGADOR que la borre (Max-Age=0); no invalida el
        valor firmado en sí. Por tanto, si un atacante ya capturó el valor de
        la cookie ANTES del logout, reenviarlo a mano sigue autenticando
        (misma firma, mismo session_version en BD) — no hay revocación
        server-side de sesiones individuales, solo el `session_version`
        global que usan cambio de contraseña/email. Se documenta así en vez
        de asumir que /logout revoca el token, que no es lo que hace el
        código."""
        user = make_user(db, role="jugador")
        login_as(user)
        old_cookie_value = client.cookies.get("session")

        client.get("/logout")

        client.cookies.set("session", old_cookie_value)  # replay explícito del valor capturado
        r = client.get("/dashboard")
        assert r.status_code == 200  # la cookie vieja sigue siendo válida: ver nota arriba


class TestConfirmEmailChange:
    def _manual_login(self, test_client, auth, user, sid):
        cookie = auth.create_session_cookie(
            user.id, user.username, user.role, _id=sid, session_version=user.session_version
        )
        test_client.cookies.set("session", cookie)

    def test_requesting_session_stays_logged_in_other_device_logged_out(self, client, db, auth):
        from fastapi.testclient import TestClient
        import asgi

        user = make_user(db, role="jugador", email="old@example.test")
        other_client = TestClient(asgi.app)

        self._manual_login(client, auth, user, "sid-device-a")
        self._manual_login(other_client, auth, user, "sid-device-b")

        tok = make_email_change_token(db, user_id=user.id, new_email="new@example.test")

        r = client.get(f"/confirm-email-change?token={tok.token}")
        assert r.status_code == 200
        assert "new@example.test" in r.text

        # El propio dispositivo que confirmó sigue autenticado (se le refrescó
        # la cookie con el session_version nuevo para evitar auto-logout).
        r_self = client.get("/dashboard")
        assert r_self.status_code == 200

        # El "otro dispositivo" (misma cuenta, cookie vieja) queda invalidado:
        # session_version ya no coincide con el de BD.
        r_other = other_client.get("/dashboard", follow_redirects=False)
        assert r_other.status_code == 302
        assert r_other.headers["location"] == "/login"

    def test_token_for_email_already_claimed_by_another_user_is_rejected(self, client, db):
        user = make_user(db, role="jugador", email="requester@example.test")
        make_user(db, role="jugador", email="taken@example.test")
        tok = make_email_change_token(db, user_id=user.id, new_email="taken@example.test")

        r = client.get(f"/confirm-email-change?token={tok.token}")
        assert r.status_code == 200
        assert "ya esta registrado" in r.text or "ya está registrado" in r.text

        db.session.rollback()
        from dockerlabs.models import User

        refreshed = User.query.get(user.id)
        assert refreshed.email == "requester@example.test"  # no se aplicó el cambio

    def test_missing_token_shows_error(self, client):
        r = client.get("/confirm-email-change")
        assert r.status_code == 200
        assert "Enlace invalido" in r.text


class TestResetPasswordPage:
    def test_missing_token_shows_error(self, client):
        r = client.get("/reset-password")
        assert r.status_code == 200
        assert "Enlace invalido" in r.text

    def test_unknown_token_shows_error(self, client):
        r = client.get("/reset-password?token=does-not-exist")
        assert r.status_code == 200
        assert "Enlace invalido o ya utilizado" in r.text

    def test_valid_token_renders_reset_form(self, client, db):
        user = make_user(db, role="jugador")
        tok = make_password_reset_token(db, user_id=user.id)

        r = client.get(f"/reset-password?token={tok.token}")
        assert r.status_code == 200
        assert "Introduce tu nueva contraseña" in r.text

    def test_expired_token_shows_error(self, client, db):
        from datetime import datetime, timedelta

        user = make_user(db, role="jugador")
        tok = make_password_reset_token(db, user_id=user.id, expires_at=datetime.utcnow() - timedelta(hours=1))

        r = client.get(f"/reset-password?token={tok.token}")
        assert r.status_code == 200
        assert "El enlace ha expirado" in r.text

    def test_used_token_shows_error(self, client, db):
        user = make_user(db, role="jugador")
        tok = make_password_reset_token(db, user_id=user.id, used=True)

        r = client.get(f"/reset-password?token={tok.token}")
        assert r.status_code == 200
        assert "Enlace invalido o ya utilizado" in r.text
