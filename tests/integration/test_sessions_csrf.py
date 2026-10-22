"""Tests cross-cutting de sesión/CSRF: get_session, verify_csrf_token,
create_session_cookie y compute_csrf_token (dockerlabs/routers.py).

Vehículo principal: /api/admin/tokens (admin-only, GET sin CSRF / POST con
CSRF) ya cubierto funcionalmente en test_api_tokens.py; aquí se prueba el
comportamiento de sesión en sí, no la feature de tokens.
"""
import pytest

from tests.factories import make_user

pytestmark = pytest.mark.integration


def _admin(db):
    return make_user(db, role="admin")


class TestCsrfOnWriteEndpoints:
    def test_get_never_requires_csrf_even_logged_in(self, client, login_as, db):
        admin = _admin(db)
        login_as(admin)  # cookie puesta, csrf token ignorado para GET
        r = client.get("/api/admin/tokens")
        assert r.status_code == 200

    def test_post_without_csrf_header_rejected(self, client, login_as, db):
        admin = _admin(db)
        login_as(admin)
        r = client.post("/api/admin/tokens", json={"label": "x"})
        assert r.status_code == 403

    def test_post_with_wrong_csrf_token_rejected(self, client, login_as, db):
        admin = _admin(db)
        login_as(admin)
        r = client.post("/api/admin/tokens", json={"label": "x"}, headers={"X-CSRFToken": "not-the-real-token"})
        assert r.status_code == 403

    def test_post_with_correct_csrf_token_succeeds(self, client, login_as, db):
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post("/api/admin/tokens", json={"label": "x"}, headers={"X-CSRFToken": csrf})
        assert r.status_code == 200


class TestCsrfSkippedForAnonymous:
    def test_anonymous_public_post_route_skips_csrf_check(self, client):
        # POST /bunkerlabs/login no requiere sesión previa (es el propio punto
        # de entrada) y usa verify_csrf_token como dependencia; sin cookie de
        # sesión, get_session() devuelve {} (sin csrf_token), así que
        # verify_csrf_token lo deja pasar sin exigir ningún header.
        r = client.post("/bunkerlabs/login", data={"password": "lo-que-sea-invalido"})
        assert r.status_code != 403


class TestSessionVersionRevalidation:
    def test_stale_session_version_is_treated_as_invalid(self, client, login_as, db):
        admin = _admin(db)
        # Cookie firmada con un session_version anterior al real en BD (simula
        # un cambio de contraseña/email ocurrido después de emitir la cookie).
        login_as(admin, session_version=admin.session_version - 1)
        r = client.get("/api/admin/tokens")
        assert r.status_code == 401

    def test_matching_session_version_is_valid(self, client, login_as, db):
        admin = _admin(db)
        login_as(admin, session_version=admin.session_version)
        r = client.get("/api/admin/tokens")
        assert r.status_code == 200


class TestRoleRevalidation:
    def test_forged_admin_role_in_cookie_is_overridden_by_real_db_role(self, client, login_as, db):
        jugador = make_user(db, role="jugador")
        # La cookie AFIRMA admin, pero la fila real en BD sigue siendo jugador.
        login_as(jugador, role="admin")
        r = client.get("/api/admin/tokens")
        assert r.status_code == 403

    def test_real_admin_role_from_db_grants_access(self, client, login_as, db):
        admin = _admin(db)
        login_as(admin, role="admin")
        r = client.get("/api/admin/tokens")
        assert r.status_code == 200


class TestDeletedUser:
    def test_cookie_for_deleted_user_is_treated_as_logged_out(self, client, login_as, db):
        admin = _admin(db)
        login_as(admin)

        from dockerlabs.models import User
        db.session.delete(User.query.get(admin.id))
        db.session.commit()

        r = client.get("/api/admin/tokens")
        assert r.status_code == 401


class TestTamperedCookie:
    def test_tampered_cookie_is_treated_as_unauthenticated_not_500(self, client, login_as, db):
        admin = _admin(db)
        login_as(admin)

        good_cookie = client.cookies.get("session")
        assert good_cookie
        # Cambiamos un carácter del payload firmado: la firma deja de validar.
        tampered = good_cookie[:-5] + ("a" if good_cookie[-5] != "a" else "b") + good_cookie[-4:]
        client.cookies.set("session", tampered)

        r = client.get("/api/admin/tokens")
        assert r.status_code == 401
