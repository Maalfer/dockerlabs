"""Tests de dockerlabs/routes/bunker_api.py — API de logs de acceso a BunkerLabs.

Ambos endpoints son solo-admin: `role != "admin"` basta para el 403 (a
diferencia de otras rutas admin/moderador compartidas, aquí moderador también
queda fuera, verificado leyendo el source: `if role != "admin": raise
HTTPException(403)`).
"""
import pytest

from tests.factories import make_bunker_token, make_user

pytestmark = pytest.mark.integration


class TestGetLogs:
    def test_anonymous_rejected(self, client, db):
        token = make_bunker_token(db)
        r = client.get(f"/api/bunker/logs/{token.id}")
        assert r.status_code == 403

    def test_jugador_rejected(self, client, login_as, db):
        token = make_bunker_token(db)
        jugador = make_user(db, role="jugador")
        login_as(jugador)
        r = client.get(f"/api/bunker/logs/{token.id}")
        assert r.status_code == 403

    def test_moderador_rejected(self, client, login_as, db):
        """Verificado en el source: este endpoint exige role == 'admin'
        exactamente, así que moderador (que en otras rutas comparte acceso
        con admin) también queda fuera aquí."""
        token = make_bunker_token(db)
        mod = make_user(db, role="moderador")
        login_as(mod)
        r = client.get(f"/api/bunker/logs/{token.id}")
        assert r.status_code == 403

    def test_admin_can_list_logs(self, client, login_as, db):
        from bunkerlabs.models import BunkerAccessLog
        token = make_bunker_token(db)
        db.session.add(BunkerAccessLog(token_id=token.id, user_nombre="alguien"))
        db.session.commit()
        admin = make_user(db, role="admin")
        login_as(admin)

        r = client.get(f"/api/bunker/logs/{token.id}")
        assert r.status_code == 200
        body = r.json()
        assert len(body["logs"]) == 1
        assert body["logs"][0]["nombre"] == "alguien"

    def test_admin_sees_empty_list_for_token_without_logs(self, client, login_as, db):
        token = make_bunker_token(db)
        admin = make_user(db, role="admin")
        login_as(admin)

        r = client.get(f"/api/bunker/logs/{token.id}")
        assert r.status_code == 200
        assert r.json() == {"logs": []}


class TestDeleteLogs:
    def test_anonymous_rejected(self, client, db):
        token = make_bunker_token(db)
        r = client.delete(f"/api/bunker/logs/{token.id}")
        assert r.status_code == 403

    def test_jugador_rejected(self, client, login_as, db):
        token = make_bunker_token(db)
        jugador = make_user(db, role="jugador")
        csrf = login_as(jugador)
        r = client.delete(f"/api/bunker/logs/{token.id}", headers={"X-CSRFToken": csrf})
        assert r.status_code == 403

    def test_moderador_rejected(self, client, login_as, db):
        token = make_bunker_token(db)
        mod = make_user(db, role="moderador")
        csrf = login_as(mod)
        r = client.delete(f"/api/bunker/logs/{token.id}", headers={"X-CSRFToken": csrf})
        assert r.status_code == 403

    def test_admin_without_csrf_rejected(self, client, login_as, db):
        token = make_bunker_token(db)
        admin = make_user(db, role="admin")
        login_as(admin)  # cookie puesta, sin header CSRF

        r = client.delete(f"/api/bunker/logs/{token.id}")
        assert r.status_code == 403

    def test_admin_with_csrf_deletes_logs(self, client, login_as, db):
        from bunkerlabs.models import BunkerAccessLog
        token = make_bunker_token(db)
        db.session.add(BunkerAccessLog(token_id=token.id, user_nombre="alguien"))
        db.session.commit()
        admin = make_user(db, role="admin")
        csrf = login_as(admin)

        r = client.delete(f"/api/bunker/logs/{token.id}", headers={"X-CSRFToken": csrf})
        assert r.status_code == 200

        db.session.rollback()
        assert BunkerAccessLog.query.filter_by(token_id=token.id).count() == 0

    def test_admin_delete_only_affects_its_own_token(self, client, login_as, db):
        from bunkerlabs.models import BunkerAccessLog
        token_a = make_bunker_token(db)
        token_b = make_bunker_token(db)
        db.session.add(BunkerAccessLog(token_id=token_a.id, user_nombre="a"))
        db.session.add(BunkerAccessLog(token_id=token_b.id, user_nombre="b"))
        db.session.commit()
        admin = make_user(db, role="admin")
        csrf = login_as(admin)

        r = client.delete(f"/api/bunker/logs/{token_a.id}", headers={"X-CSRFToken": csrf})
        assert r.status_code == 200

        db.session.rollback()
        assert BunkerAccessLog.query.filter_by(token_id=token_a.id).count() == 0
        assert BunkerAccessLog.query.filter_by(token_id=token_b.id).count() == 1
