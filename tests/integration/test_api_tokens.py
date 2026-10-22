"""Tests de dockerlabs/routes/api_tokens.py — tokens de API de administrador.

Doble cobertura intencional: además de probar la gestión de tokens por sí
misma, estos tests fijan el contrato de autenticación por cabecera
(`Authorization: Bearer <token>`) que usan TODAS las demás rutas admin vía
`get_session()` — y que ya verificamos a mano contra producción en esta misma
sesión (subida de logo a PinguinoExaminador/Bigbank).
"""
import pytest

from tests.factories import make_user

pytestmark = pytest.mark.integration


def _jugador(db):
    return make_user(db, role="jugador")


def _admin(db):
    return make_user(db, role="admin")


class TestListAndCreate:
    def test_anonymous_gets_401(self, client):
        r = client.get("/api/admin/tokens")
        assert r.status_code == 401

    def test_jugador_gets_403(self, client, login_as, db):
        user = _jugador(db)
        csrf = login_as(user)
        r = client.get("/api/admin/tokens", headers={"X-CSRFToken": csrf})
        assert r.status_code == 403

    def test_moderador_gets_403(self, client, login_as, db):
        mod = make_user(db, role="moderador")
        csrf = login_as(mod)
        r = client.get("/api/admin/tokens", headers={"X-CSRFToken": csrf})
        assert r.status_code == 403

    def test_admin_can_list_empty(self, client, login_as, db):
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.get("/api/admin/tokens", headers={"X-CSRFToken": csrf})
        assert r.status_code == 200
        assert r.json() == {"tokens": []}

    def test_admin_can_create_token(self, client, login_as, db):
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(
            "/api/admin/tokens",
            json={"label": "mi token de test"},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["label"] == "mi token de test"
        assert body["token"].startswith("dlab_")
        assert body["token_prefix"] == body["token"][:12]

    def test_create_without_csrf_header_is_rejected(self, client, login_as, db):
        admin = _admin(db)
        login_as(admin)  # cookie puesta, pero no mandamos el header CSRF
        r = client.post("/api/admin/tokens", json={"label": "sin csrf"})
        assert r.status_code == 403

    def test_plaintext_token_never_persisted_but_hash_verifies(self, client, login_as, db):
        from dockerlabs.models import ApiToken
        from dockerlabs.token_auth import verify_api_token

        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post("/api/admin/tokens", json={"label": "x"}, headers={"X-CSRFToken": csrf})
        plaintext = r.json()["token"]

        # NOTA: la petición HTTP corre en una sesión/transacción distinta
        # (ver DBSessionMiddleware + scoped_session por request en
        # dockerlabs/database.py). Bajo REPEATABLE READ (default de
        # MariaDB/InnoDB), si la sesión de este test ya tenía una transacción
        # abierta seguiría viendo el estado de ANTES del commit ajeno; hay
        # que cerrarla explícitamente para empezar una nueva que sí lo vea.
        db.session.rollback()
        row = ApiToken.query.filter_by(label="x").first()
        assert plaintext not in row.token_hash
        assert verify_api_token(row.token_hash, plaintext) is True
        assert verify_api_token(row.token_hash, plaintext + "x") is False

    def test_created_token_defaults_to_not_revoked(self, client, login_as, db):
        from dockerlabs.models import ApiToken

        admin = _admin(db)
        csrf = login_as(admin)
        client.post("/api/admin/tokens", json={"label": "x"}, headers={"X-CSRFToken": csrf})
        db.session.rollback()  # ver nota en test_plaintext_token_never_persisted_but_hash_verifies
        row = ApiToken.query.filter_by(label="x").first()
        assert row.revoked_at is None

    def test_missing_label_defaults_to_sin_nombre(self, client, login_as, db):
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post("/api/admin/tokens", json={}, headers={"X-CSRFToken": csrf})
        assert r.json()["label"] == "Sin nombre"


class TestRevoke:
    def test_admin_can_revoke_own_token(self, client, login_as, db, admin_api_token):
        from dockerlabs.models import ApiToken

        admin = _admin(db)
        _, _headers = admin_api_token(admin, label="a revocar")
        row = ApiToken.query.filter_by(label="a revocar").first()

        csrf = login_as(admin)
        r = client.post(f"/api/admin/tokens/{row.id}/revoke", headers={"X-CSRFToken": csrf})
        assert r.status_code == 200

        db.session.rollback()  # ver nota más arriba sobre REPEATABLE READ
        db.session.refresh(row)
        assert row.revoked_at is not None

    def test_revoke_is_idempotent(self, client, login_as, db, admin_api_token):
        from dockerlabs.models import ApiToken

        admin = _admin(db)
        admin_api_token(admin, label="doble revocacion")
        row = ApiToken.query.filter_by(label="doble revocacion").first()
        csrf = login_as(admin)

        r1 = client.post(f"/api/admin/tokens/{row.id}/revoke", headers={"X-CSRFToken": csrf})
        db.session.rollback()
        db.session.refresh(row)
        first_revoked_at = row.revoked_at

        r2 = client.post(f"/api/admin/tokens/{row.id}/revoke", headers={"X-CSRFToken": csrf})
        db.session.rollback()
        db.session.refresh(row)

        assert r1.status_code == r2.status_code == 200
        assert row.revoked_at == first_revoked_at  # no se pisa con un segundo revoke


class TestHeaderAuthentication:
    """El token de API por cabecera es el mecanismo real que usamos para
    automatizar subidas de logo/máquinas contra producción en esta sesión:
    aquí se fija como contrato con test."""

    def test_valid_bearer_token_grants_admin_access(self, client, db, admin_api_token):
        admin = _admin(db)
        _token, headers = admin_api_token(admin)
        r = client.get("/api/admin/tokens", headers=headers)
        assert r.status_code == 200

    def test_header_auth_bypasses_csrf_for_post(self, client, db, admin_api_token):
        # A diferencia de la cookie de sesión, el token de API no necesita
        # X-CSRFToken (get_session() lo resuelve antes de llegar a la cookie).
        admin = _admin(db)
        _token, headers = admin_api_token(admin)
        r = client.post("/api/admin/tokens", json={"label": "via header"}, headers=headers)
        assert r.status_code == 200

    def test_x_admin_token_header_also_works(self, client, db, admin_api_token):
        admin = _admin(db)
        token, _ = admin_api_token(admin)
        r = client.get("/api/admin/tokens", headers={"X-Admin-Token": token})
        assert r.status_code == 200

    def test_revoked_token_is_rejected(self, client, db, admin_api_token):
        from dockerlabs.models import ApiToken
        from datetime import datetime

        admin = _admin(db)
        token, headers = admin_api_token(admin)
        row = ApiToken.query.filter_by(admin_user_id=admin.id).first()
        row.revoked_at = datetime.utcnow()
        db.session.commit()

        r = client.get("/api/admin/tokens", headers=headers)
        assert r.status_code == 401

    def test_garbage_token_is_rejected(self, client):
        r = client.get("/api/admin/tokens", headers={"Authorization": "Bearer dlab_garbage_not_real"})
        assert r.status_code == 401

    def test_token_owner_demoted_from_admin_loses_access(self, client, db, admin_api_token):
        admin = _admin(db)
        _token, headers = admin_api_token(admin)
        admin.role = "jugador"
        db.session.commit()

        r = client.get("/api/admin/tokens", headers=headers)
        assert r.status_code == 401
