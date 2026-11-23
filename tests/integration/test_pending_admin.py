"""Tests de dockerlabs/routes/pending_admin.py — revisión de envíos pendientes
(PendingMachineSubmission).
"""
import pytest

from tests.factories import make_pending_machine_submission, make_user

pytestmark = pytest.mark.integration


def _jugador(db, **kw):
    return make_user(db, role="jugador", **kw)


def _admin(db, **kw):
    return make_user(db, role="admin", **kw)


def _moderador(db, **kw):
    return make_user(db, role="moderador", **kw)


class TestApprove:
    def test_admin_can_approve(self, client, login_as, db):
        from dockerlabs.models import PendingMachineSubmission

        admin = _admin(db)
        sub = make_pending_machine_submission(db, nombre="PendingOne")
        csrf = login_as(admin)

        r = client.post(f"/api/admin/pending-machines/{sub.id}/approve", headers={"X-CSRFToken": csrf})
        assert r.status_code == 200
        assert r.json()["success"] is True

        db.session.rollback()
        row = db.session.get(PendingMachineSubmission, sub.id)
        assert row.estado == "aprobado"
        assert row.reviewed_at is not None

    def test_moderador_can_approve(self, client, login_as, db):
        mod = _moderador(db)
        sub = make_pending_machine_submission(db)
        csrf = login_as(mod)

        r = client.post(f"/api/admin/pending-machines/{sub.id}/approve", headers={"X-CSRFToken": csrf})
        assert r.status_code == 200

    def test_jugador_rejected(self, client, login_as, db):
        user = _jugador(db)
        sub = make_pending_machine_submission(db)
        csrf = login_as(user)

        r = client.post(f"/api/admin/pending-machines/{sub.id}/approve", headers={"X-CSRFToken": csrf})
        assert r.status_code == 403

    def test_anonymous_rejected(self, client, db):
        sub = make_pending_machine_submission(db)
        r = client.post(f"/api/admin/pending-machines/{sub.id}/approve")
        assert r.status_code == 403  # get_session() -> role="" -> fuera de ("admin","moderador")

    def test_nonexistent_id_404(self, client, login_as, db):
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post("/api/admin/pending-machines/999999/approve", headers={"X-CSRFToken": csrf})
        assert r.status_code == 404

    def test_approve_does_not_create_machine_or_category_row(self, client, login_as, db):
        # NOTA (hallazgo): aprobar una submission no crea una fila
        # Machine/Category — si no hay otro proceso que lo haga, "aprobar" no
        # publica la máquina en el catálogo público. Confirmar con el equipo
        # si es intencional. Este test fija (pin) el comportamiento actual.
        from dockerlabs.models import Category, Machine

        admin = _admin(db)
        sub = make_pending_machine_submission(db, nombre="NuncaSeCreaComoMaquina")
        csrf = login_as(admin)

        machines_before = Machine.query.count()
        categories_before = Category.query.count()

        r = client.post(f"/api/admin/pending-machines/{sub.id}/approve", headers={"X-CSRFToken": csrf})
        assert r.status_code == 200

        db.session.rollback()
        assert Machine.query.count() == machines_before
        assert Category.query.count() == categories_before
        assert Machine.query.filter_by(nombre="NuncaSeCreaComoMaquina").first() is None


class TestReject:
    def test_admin_can_reject_deletes_row_entirely(self, client, login_as, db):
        from dockerlabs.models import PendingMachineSubmission

        admin = _admin(db)
        sub = make_pending_machine_submission(db, nombre="PendingToReject")
        sub_id = sub.id  # leído ANTES del reject, ver nota más abajo
        csrf = login_as(admin)

        r = client.post(f"/api/admin/pending-machines/{sub_id}/reject", headers={"X-CSRFToken": csrf})
        assert r.status_code == 200
        assert r.json()["success"] is True

        db.session.rollback()
        # NOTA: usamos `sub_id` (int ya leído), no `sub.id`: tras el reject
        # real + rollback(), `sub` queda expirado en el identity map de esta
        # sesión (viene de make_pending_machine_submission() en este mismo
        # test), así que acceder a `sub.id` dispararía un refresh imposible
        # (la fila ya no existe) y SQLAlchemy lanzaría ObjectDeletedError. Por
        # el mismo motivo tampoco usamos .query.get(): refrescaría el objeto
        # del identity map en vez de devolver None.
        assert PendingMachineSubmission.query.filter_by(id=sub_id).first() is None

    def test_moderador_can_reject(self, client, login_as, db):
        from dockerlabs.models import PendingMachineSubmission

        mod = _moderador(db)
        sub = make_pending_machine_submission(db)
        sub_id = sub.id  # leído ANTES del reject, ver nota en el test anterior
        csrf = login_as(mod)

        r = client.post(f"/api/admin/pending-machines/{sub_id}/reject", headers={"X-CSRFToken": csrf})
        assert r.status_code == 200

        db.session.rollback()
        assert PendingMachineSubmission.query.filter_by(id=sub_id).first() is None

    def test_jugador_rejected(self, client, login_as, db):
        user = _jugador(db)
        sub = make_pending_machine_submission(db)
        csrf = login_as(user)

        r = client.post(f"/api/admin/pending-machines/{sub.id}/reject", headers={"X-CSRFToken": csrf})
        assert r.status_code == 403

    def test_anonymous_rejected(self, client, db):
        sub = make_pending_machine_submission(db)
        r = client.post(f"/api/admin/pending-machines/{sub.id}/reject")
        assert r.status_code == 403

    def test_nonexistent_id_404(self, client, login_as, db):
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post("/api/admin/pending-machines/999999/reject", headers={"X-CSRFToken": csrf})
        assert r.status_code == 404


class TestEstado:
    def _post(self, client, sub_id, estado, csrf):
        return client.post(f"/api/admin/pending-machines/{sub_id}/estado", json={"estado": estado},
                           headers={"X-CSRFToken": csrf})

    def test_moderador_can_reject_and_restore(self, client, login_as, db):
        from dockerlabs.models import PendingMachineSubmission

        mod = _moderador(db)
        sub = make_pending_machine_submission(db)
        sub_id = sub.id
        csrf = login_as(mod)

        r = self._post(client, sub_id, "rechazado", csrf)
        assert r.status_code == 200
        assert r.json()["counts"]["rechazado"] == 1
        db.session.expire_all()
        row = db.session.get(PendingMachineSubmission, sub_id)
        assert row.estado == "rechazado" and row.reviewed_at is not None and row.reviewed_by == mod.id

        r = self._post(client, sub_id, "pendiente", csrf)
        assert r.status_code == 200
        db.session.expire_all()
        row = db.session.get(PendingMachineSubmission, sub_id)
        assert row.estado == "pendiente" and row.reviewed_at is None and row.reviewed_by is None

    def test_invalid_state_is_rejected(self, client, login_as, db):
        sub = make_pending_machine_submission(db)
        csrf = login_as(_admin(db))
        assert self._post(client, sub.id, "publicada", csrf).status_code == 400

    def test_jugador_is_forbidden(self, client, login_as, db):
        sub = make_pending_machine_submission(db)
        csrf = login_as(_jugador(db))
        assert self._post(client, sub.id, "aprobado", csrf).status_code == 403


class TestLimpiar:
    def test_only_deletes_requested_state_and_never_pending(self, client, login_as, db):
        from dockerlabs.models import PendingMachineSubmission

        make_pending_machine_submission(db, estado="aprobado")
        make_pending_machine_submission(db, estado="aprobado")
        make_pending_machine_submission(db, estado="rechazado")
        make_pending_machine_submission(db, estado="pendiente")
        csrf = login_as(_admin(db))

        r = client.post("/api/admin/pending-machines/limpiar", json={"estado": "aprobado"}, headers={"X-CSRFToken": csrf})
        assert r.status_code == 200
        assert r.json()["eliminadas"] == 2
        db.session.expire_all()
        assert sorted(p.estado for p in PendingMachineSubmission.query.all()) == ["pendiente", "rechazado"]

        r = client.post("/api/admin/pending-machines/limpiar", json={"estado": "pendiente"}, headers={"X-CSRFToken": csrf})
        assert r.status_code == 400
        db.session.expire_all()
        assert PendingMachineSubmission.query.count() == 2

    def test_jugador_is_forbidden(self, client, login_as, db):
        csrf = login_as(_jugador(db))
        r = client.post("/api/admin/pending-machines/limpiar", json={"estado": "aprobado"}, headers={"X-CSRFToken": csrf})
        assert r.status_code == 403
