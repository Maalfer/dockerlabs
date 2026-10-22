"""Tests de dockerlabs/routes/admin_usuarios.py — cambio de rol y borrado."""
import pytest

from tests.factories import make_user

pytestmark = pytest.mark.integration


class TestUpdateUserRole:
    def test_admin_can_promote_jugador_to_moderador(self, client, login_as, db):
        admin = make_user(db, role="admin")
        jugador = make_user(db, role="jugador")
        csrf = login_as(admin)

        r = client.post(f"/api/admin/update_user_role/{jugador.id}", json={"role": "moderador"}, headers={"X-CSRFToken": csrf})
        assert r.status_code == 200
        assert r.json()["success"] is True

        db.session.rollback()
        from dockerlabs.models import User
        assert User.query.get(jugador.id).role == "moderador"

    def test_admin_can_promote_moderador_to_admin(self, client, login_as, db):
        admin = make_user(db, role="admin")
        mod = make_user(db, role="moderador")
        csrf = login_as(admin)

        r = client.post(f"/api/admin/update_user_role/{mod.id}", json={"role": "admin"}, headers={"X-CSRFToken": csrf})
        assert r.status_code == 200

        db.session.rollback()
        from dockerlabs.models import User
        assert User.query.get(mod.id).role == "admin"

    def test_admin_can_demote_admin_to_jugador_when_another_admin_remains(self, client, login_as, db):
        admin = make_user(db, role="admin")
        other_admin = make_user(db, role="admin")
        csrf = login_as(admin)

        r = client.post(f"/api/admin/update_user_role/{other_admin.id}", json={"role": "jugador"}, headers={"X-CSRFToken": csrf})
        assert r.status_code == 200

        db.session.rollback()
        from dockerlabs.models import User
        assert User.query.get(other_admin.id).role == "jugador"

    def test_moderador_cannot_set_role_to_admin(self, client, login_as, db):
        mod = make_user(db, role="moderador")
        jugador = make_user(db, role="jugador")
        csrf = login_as(mod)

        r = client.post(f"/api/admin/update_user_role/{jugador.id}", json={"role": "admin"}, headers={"X-CSRFToken": csrf})
        assert r.status_code == 403

    def test_moderador_cannot_modify_a_current_admin(self, client, login_as, db):
        mod = make_user(db, role="moderador")
        admin = make_user(db, role="admin")
        csrf = login_as(mod)

        r = client.post(f"/api/admin/update_user_role/{admin.id}", json={"role": "moderador"}, headers={"X-CSRFToken": csrf})
        assert r.status_code == 403

    def test_last_remaining_admin_cannot_be_demoted(self, client, login_as, db):
        from dockerlabs.models import User

        sole_admin = make_user(db, role="admin")
        assert User.query.filter_by(role="admin").count() == 1
        csrf = login_as(sole_admin)

        r = client.post(f"/api/admin/update_user_role/{sole_admin.id}", json={"role": "jugador"}, headers={"X-CSRFToken": csrf})
        assert r.status_code == 400

        db.session.rollback()
        assert User.query.get(sole_admin.id).role == "admin"

        # Con un segundo admin presente, la degradación del primero sí procede.
        second_admin = make_user(db, role="admin")
        r2 = client.post(f"/api/admin/update_user_role/{sole_admin.id}", json={"role": "jugador"}, headers={"X-CSRFToken": csrf})
        assert r2.status_code == 200

    def test_jugador_gets_403(self, client, login_as, db):
        jugador = make_user(db, role="jugador")
        target = make_user(db, role="jugador")
        csrf = login_as(jugador)

        r = client.post(f"/api/admin/update_user_role/{target.id}", json={"role": "moderador"}, headers={"X-CSRFToken": csrf})
        assert r.status_code == 403

    def test_anonymous_gets_401_or_403(self, client, db):
        target = make_user(db, role="jugador")
        r = client.post(f"/api/admin/update_user_role/{target.id}", json={"role": "moderador"})
        assert r.status_code in (401, 403)


class TestDeleteUser:
    def test_admin_can_delete_jugador(self, client, login_as, db):
        admin = make_user(db, role="admin")
        jugador = make_user(db, role="jugador")
        jugador_id = jugador.id  # ver nota más abajo: leído ANTES del DELETE
        csrf = login_as(admin)

        r = client.post(f"/api/admin/delete_user/{jugador_id}", headers={"X-CSRFToken": csrf})
        assert r.status_code == 200
        assert r.json()["success"] is True

        db.session.rollback()
        from dockerlabs.models import User
        # NOTA: usamos `jugador_id` (un int ya leído), no `jugador.id`: tras
        # el DELETE real + rollback(), `jugador` queda expirado en el
        # identity map de esta sesión, así que acceder a `jugador.id` ahora
        # dispara un refresh que SQLAlchemy no puede completar (la fila ya no
        # existe) y lanza ObjectDeletedError en vez de darnos el id. Tampoco
        # usamos User.query.get(): por el mismo motivo de identity map,
        # intentaría refrescar el objeto en vez de devolver None.
        assert User.query.filter_by(id=jugador_id).first() is None

    def test_admin_cannot_delete_self(self, client, login_as, db):
        admin = make_user(db, role="admin")
        make_user(db, role="admin")  # para no confundir con el caso "último admin"
        csrf = login_as(admin)

        r = client.post(f"/api/admin/delete_user/{admin.id}", headers={"X-CSRFToken": csrf})
        assert r.status_code == 400
        assert "propia cuenta" in r.json()["error"]

    def test_cannot_delete_last_admin(self, client, login_as, db):
        from dockerlabs.models import User

        sole_admin = make_user(db, role="admin")
        other_admin = make_user(db, role="admin")
        csrf = login_as(sole_admin)

        # Borrar al otro admin funciona (quedan 2 -> 1).
        r = client.post(f"/api/admin/delete_user/{other_admin.id}", headers={"X-CSRFToken": csrf})
        assert r.status_code == 200
        db.session.rollback()  # ver nota REPEATABLE READ en test_api_tokens.py
        assert User.query.filter_by(role="admin").count() == 1

        # NOTA sobre el orden de guards en delete_user: el check "no puedes
        # eliminar tu propia cuenta" va ANTES que el de "último administrador".
        # Como la ruta exige caller_role == 'admin', la única forma de que haya
        # un solo admin en BD en el momento de la llamada es que el propio
        # caller sea ese admin (nadie más con rol admin podría estar
        # autenticado para intentarlo) — así que el guard de "último admin"
        # nunca se alcanza en la práctica para delete_user: siempre gana antes
        # el guard de autoeliminación. Documentado aquí en vez de asumido.
        r_self = client.post(f"/api/admin/delete_user/{sole_admin.id}", headers={"X-CSRFToken": csrf})
        assert r_self.status_code == 400
        assert "propia cuenta" in r_self.json()["error"]

    def test_jugador_gets_403(self, client, login_as, db):
        jugador = make_user(db, role="jugador")
        target = make_user(db, role="jugador")
        csrf = login_as(jugador)

        r = client.post(f"/api/admin/delete_user/{target.id}", headers={"X-CSRFToken": csrf})
        assert r.status_code == 403

    def test_anonymous_gets_401_or_403(self, client, db):
        target = make_user(db, role="jugador")
        r = client.post(f"/api/admin/delete_user/{target.id}")
        assert r.status_code in (401, 403)

    def test_moderador_gets_403(self, client, login_as, db):
        mod = make_user(db, role="moderador")
        target = make_user(db, role="jugador")
        csrf = login_as(mod)

        r = client.post(f"/api/admin/delete_user/{target.id}", headers={"X-CSRFToken": csrf})
        assert r.status_code == 403
