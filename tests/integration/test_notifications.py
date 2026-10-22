"""Tests de dockerlabs/routes/notifications.py — sistema de notificaciones.

Cubre: envío (solo admin/moderador, con revalidación de rol en vivo vía
get_session), listado con cálculo mixto de leído/no-leído (dirigidas vs.
globales/broadcast), marcar como leído, reacciones (whitelist + toggle) y
borrado (ownership global vs. dirigida).
"""
import pytest

from tests.factories import (
    make_notification,
    make_notification_read,
    make_notification_reaction,
    make_user,
)

pytestmark = pytest.mark.integration


def _jugador(db, **kw):
    return make_user(db, role="jugador", **kw)


def _admin(db, **kw):
    return make_user(db, role="admin", **kw)


def _moderador(db, **kw):
    return make_user(db, role="moderador", **kw)


class TestSendNotification:
    def test_anonymous_gets_401(self, client):
        r = client.post("/api/notifications/send", json={"title": "t", "content": "c"})
        assert r.status_code == 401

    def test_jugador_gets_403(self, client, login_as, db):
        user = _jugador(db)
        csrf = login_as(user)
        r = client.post(
            "/api/notifications/send",
            json={"title": "t", "content": "c"},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 403

    def test_admin_can_send(self, client, login_as, db):
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(
            "/api/notifications/send",
            json={"title": "Aviso", "content": "Contenido"},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_moderador_can_send(self, client, login_as, db):
        mod = _moderador(db)
        csrf = login_as(mod)
        r = client.post(
            "/api/notifications/send",
            json={"title": "Aviso", "content": "Contenido"},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 200

    def test_missing_title_rejected(self, client, login_as, db):
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(
            "/api/notifications/send",
            json={"title": "", "content": "c"},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 400

    def test_missing_content_rejected(self, client, login_as, db):
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(
            "/api/notifications/send",
            json={"title": "t", "content": ""},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 400

    def test_title_over_200_chars_rejected(self, client, login_as, db):
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(
            "/api/notifications/send",
            json={"title": "A" * 201, "content": "c"},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 400

    def test_title_exactly_200_chars_accepted(self, client, login_as, db):
        admin = _admin(db)
        csrf = login_as(admin)
        r = client.post(
            "/api/notifications/send",
            json={"title": "A" * 200, "content": "c"},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 200

    def test_receiver_none_creates_broadcast_visible_to_multiple_users(self, client, login_as, db):
        from dockerlabs.models import Notification

        admin = _admin(db)
        user_a = _jugador(db)
        user_b = _jugador(db)
        csrf = login_as(admin)
        r = client.post(
            "/api/notifications/send",
            json={"title": "Global", "content": "Para todos", "receiver_id": None},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 200
        db.session.rollback()
        notif = Notification.query.filter_by(title="Global").first()
        assert notif.receiver_id is None

        # Visible (via GET /api/notifications) para ambos usuarios normales.
        for user in (user_a, user_b):
            csrf_u = login_as(user)
            resp = client.get("/api/notifications", headers={"X-CSRFToken": csrf_u})
            titles = [n["title"] for n in resp.json()["notifications"]]
            assert "Global" in titles

    def test_receiver_id_creates_targeted_notification_visible_only_to_receiver(self, client, login_as, db):
        from dockerlabs.models import Notification

        admin = _admin(db)
        receiver = _jugador(db)
        other = _jugador(db)
        csrf = login_as(admin)
        r = client.post(
            "/api/notifications/send",
            json={"title": "Solo para ti", "content": "Contenido", "receiver_id": receiver.id},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 200
        db.session.rollback()
        notif = Notification.query.filter_by(title="Solo para ti").first()
        assert notif.receiver_id == receiver.id

        csrf_r = login_as(receiver)
        resp_r = client.get("/api/notifications", headers={"X-CSRFToken": csrf_r})
        assert "Solo para ti" in [n["title"] for n in resp_r.json()["notifications"]]

        csrf_o = login_as(other)
        resp_o = client.get("/api/notifications", headers={"X-CSRFToken": csrf_o})
        assert "Solo para ti" not in [n["title"] for n in resp_o.json()["notifications"]]


class TestRoleRevalidationOnSend:
    """Mismo patrón que test_api_tokens.py::TestHeaderAuthentication: get_session()
    revalida el rol contra BD en cada petición, así que una cookie vieja que
    afirma un rol que ya no es real no basta (ni aunque el forjado sea vía
    login_as(user, role=...), que simula exactamente una cookie desincronizada
    de la BD)."""

    def test_demoted_user_loses_access_even_with_forged_admin_cookie(self, client, login_as, db):
        user = _jugador(db)
        # Forjamos una cookie que AFIRMA rol admin (como si fuera una cookie
        # vieja emitida cuando el usuario sí era admin).
        csrf = login_as(user, role="admin")

        # La fila real en BD sigue siendo "jugador": get_session() debe
        # revalidar y descartar el rol de la cookie.
        r = client.post(
            "/api/notifications/send",
            json={"title": "t", "content": "c"},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 403

    def test_promoted_then_demoted_admin_loses_access_mid_session(self, client, login_as, db):
        admin = _admin(db)
        csrf = login_as(admin)
        # Confirmar que, de entrada, sí puede.
        r1 = client.post(
            "/api/notifications/send",
            json={"title": "t1", "content": "c"},
            headers={"X-CSRFToken": csrf},
        )
        assert r1.status_code == 200

        # Degradar en BD (la cookie/CSRF ya emitidos no cambian).
        admin.role = "jugador"
        db.session.commit()

        r2 = client.post(
            "/api/notifications/send",
            json={"title": "t2", "content": "c"},
            headers={"X-CSRFToken": csrf},
        )
        assert r2.status_code == 403


class TestGetNotifications:
    def test_anonymous_gets_401(self, client):
        r = client.get("/api/notifications")
        assert r.status_code == 401

    def test_mixed_scenario_unread_count_and_per_notification_state(self, client, login_as, db):
        """Escenario para UN usuario (`me`):
        - targeted-unread (de otro admin)
        - targeted-read (ya marcada read=True)
        - global-unread-by-this-user (nadie ha creado NotificationRead para él)
        - global-already-read-by-this-user (existe NotificationRead(me))
        - global-read-by-a-DIFFERENT-user-only (existe NotificationRead(otro),
          pero sigue sin leer para `me`)
        """
        admin = _admin(db)
        me = _jugador(db)
        other_user = _jugador(db)

        targeted_unread = make_notification(db, sender_id=admin.id, receiver_id=me.id, title="T-unread")
        targeted_read = make_notification(db, sender_id=admin.id, receiver_id=me.id, title="T-read", read=True)
        global_unread_for_me = make_notification(db, sender_id=admin.id, receiver_id=None, title="G-unread-me")
        global_read_by_me = make_notification(db, sender_id=admin.id, receiver_id=None, title="G-read-me")
        make_notification_read(db, notification_id=global_read_by_me.id, user_id=me.id)
        global_read_by_other_only = make_notification(db, sender_id=admin.id, receiver_id=None, title="G-read-other-only")
        make_notification_read(db, notification_id=global_read_by_other_only.id, user_id=other_user.id)

        csrf = login_as(me)
        r = client.get("/api/notifications", headers={"X-CSRFToken": csrf})
        assert r.status_code == 200
        body = r.json()

        by_title = {n["title"]: n for n in body["notifications"]}
        assert by_title["T-unread"]["read"] is False
        assert by_title["T-read"]["read"] is True
        assert by_title["G-unread-me"]["read"] is False
        assert by_title["G-read-me"]["read"] is True
        # No leída-por-mí-mismo aunque otro usuario sí la marcó como leída.
        assert by_title["G-read-other-only"]["read"] is False

        # unread_count = targeted-unread (1: T-unread) + global-unread-para-mí
        # (2: G-unread-me, G-read-other-only).
        expected_unread = 1 + 2
        assert body["unread_count"] == expected_unread

    def test_reactions_grouped_by_emoji_with_counts_and_user_reacted_flag(self, client, login_as, db):
        admin = _admin(db)
        me = _jugador(db)
        other_user = _jugador(db)

        notif = make_notification(db, sender_id=admin.id, receiver_id=None, title="Con reacciones")
        make_notification_reaction(db, notification_id=notif.id, user_id=me.id, emoji="👍")
        make_notification_reaction(db, notification_id=notif.id, user_id=other_user.id, emoji="👍")
        make_notification_reaction(db, notification_id=notif.id, user_id=other_user.id, emoji="❤️")

        csrf = login_as(me)
        r = client.get("/api/notifications", headers={"X-CSRFToken": csrf})
        body = r.json()
        target = next(n for n in body["notifications"] if n["title"] == "Con reacciones")
        reactions = {rx["emoji"]: rx for rx in target["reactions"]}

        assert reactions["👍"]["count"] == 2
        assert reactions["👍"]["user_reacted"] is True  # `me` reaccionó con 👍
        assert reactions["❤️"]["count"] == 1
        assert reactions["❤️"]["user_reacted"] is False  # `me` no reaccionó con ❤️


class TestMarkRead:
    def test_anonymous_gets_401(self, client, db):
        admin = _admin(db)
        notif = make_notification(db, sender_id=admin.id, receiver_id=None)
        r = client.post(f"/api/notifications/{notif.id}/read")
        assert r.status_code == 401

    def test_nonexistent_notification_404(self, client, login_as, db):
        user = _jugador(db)
        csrf = login_as(user)
        r = client.post("/api/notifications/999999/read", headers={"X-CSRFToken": csrf})
        assert r.status_code == 404

    def test_targeted_notification_sets_read_true(self, client, login_as, db):
        from dockerlabs.models import Notification

        admin = _admin(db)
        receiver = _jugador(db)
        notif = make_notification(db, sender_id=admin.id, receiver_id=receiver.id)

        csrf = login_as(receiver)
        r = client.post(f"/api/notifications/{notif.id}/read", headers={"X-CSRFToken": csrf})
        assert r.status_code == 200

        db.session.rollback()
        row = Notification.query.get(notif.id)
        assert row.read is True

    def test_global_notification_creates_notification_read_row(self, client, login_as, db):
        from dockerlabs.models import NotificationRead

        admin = _admin(db)
        user = _jugador(db)
        notif = make_notification(db, sender_id=admin.id, receiver_id=None)

        csrf = login_as(user)
        r = client.post(f"/api/notifications/{notif.id}/read", headers={"X-CSRFToken": csrf})
        assert r.status_code == 200

        db.session.rollback()
        row = NotificationRead.query.filter_by(notification_id=notif.id, user_id=user.id).first()
        assert row is not None

    def test_global_notification_read_twice_is_idempotent_no_duplicate(self, client, login_as, db):
        from dockerlabs.models import NotificationRead

        admin = _admin(db)
        user = _jugador(db)
        notif = make_notification(db, sender_id=admin.id, receiver_id=None)
        csrf = login_as(user)

        r1 = client.post(f"/api/notifications/{notif.id}/read", headers={"X-CSRFToken": csrf})
        r2 = client.post(f"/api/notifications/{notif.id}/read", headers={"X-CSRFToken": csrf})
        assert r1.status_code == 200
        assert r2.status_code == 200

        db.session.rollback()
        rows = NotificationRead.query.filter_by(notification_id=notif.id, user_id=user.id).all()
        assert len(rows) == 1

    def test_non_owner_non_admin_on_targeted_notification_rejected(self, client, login_as, db):
        admin = _admin(db)
        receiver = _jugador(db)
        stranger = _jugador(db)
        notif = make_notification(db, sender_id=admin.id, receiver_id=receiver.id)

        csrf = login_as(stranger)
        r = client.post(f"/api/notifications/{notif.id}/read", headers={"X-CSRFToken": csrf})
        assert r.status_code == 403

    def test_any_user_on_global_notification_allowed(self, client, login_as, db):
        admin = _admin(db)
        anyone = _jugador(db)
        notif = make_notification(db, sender_id=admin.id, receiver_id=None)

        csrf = login_as(anyone)
        r = client.post(f"/api/notifications/{notif.id}/read", headers={"X-CSRFToken": csrf})
        assert r.status_code == 200


class TestReact:
    def test_allowed_emoji_accepted(self, client, login_as, db):
        admin = _admin(db)
        user = _jugador(db)
        notif = make_notification(db, sender_id=admin.id, receiver_id=None)
        csrf = login_as(user)

        r = client.post(
            f"/api/notifications/{notif.id}/react",
            json={"emoji": "🔥"},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 200
        assert r.json()["reacted"] is True

    def test_disallowed_emoji_rejected(self, client, login_as, db):
        admin = _admin(db)
        user = _jugador(db)
        notif = make_notification(db, sender_id=admin.id, receiver_id=None)
        csrf = login_as(user)

        r = client.post(
            f"/api/notifications/{notif.id}/react",
            json={"emoji": "🐸"},  # no está en ALLOWED_EMOJIS
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 400

    def test_disallowed_arbitrary_string_rejected(self, client, login_as, db):
        admin = _admin(db)
        user = _jugador(db)
        notif = make_notification(db, sender_id=admin.id, receiver_id=None)
        csrf = login_as(user)

        r = client.post(
            f"/api/notifications/{notif.id}/react",
            json={"emoji": "<script>alert(1)</script>"},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 400

    def test_reacting_twice_with_same_emoji_toggles_removal(self, client, login_as, db):
        from dockerlabs.models import NotificationReaction

        admin = _admin(db)
        user = _jugador(db)
        notif = make_notification(db, sender_id=admin.id, receiver_id=None)
        csrf = login_as(user)

        r1 = client.post(
            f"/api/notifications/{notif.id}/react",
            json={"emoji": "👍"},
            headers={"X-CSRFToken": csrf},
        )
        assert r1.json()["reacted"] is True
        db.session.rollback()
        assert NotificationReaction.query.filter_by(notification_id=notif.id, user_id=user.id, emoji="👍").count() == 1

        r2 = client.post(
            f"/api/notifications/{notif.id}/react",
            json={"emoji": "👍"},
            headers={"X-CSRFToken": csrf},
        )
        assert r2.json()["reacted"] is False
        db.session.rollback()
        assert NotificationReaction.query.filter_by(notification_id=notif.id, user_id=user.id, emoji="👍").count() == 0

    def test_non_owner_non_admin_on_targeted_notification_rejected(self, client, login_as, db):
        admin = _admin(db)
        receiver = _jugador(db)
        stranger = _jugador(db)
        notif = make_notification(db, sender_id=admin.id, receiver_id=receiver.id)
        csrf = login_as(stranger)

        r = client.post(
            f"/api/notifications/{notif.id}/react",
            json={"emoji": "👍"},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 403

    def test_any_user_on_global_notification_allowed(self, client, login_as, db):
        admin = _admin(db)
        anyone = _jugador(db)
        notif = make_notification(db, sender_id=admin.id, receiver_id=None)
        csrf = login_as(anyone)

        r = client.post(
            f"/api/notifications/{notif.id}/react",
            json={"emoji": "😮"},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 200


class TestDeleteNotification:
    def test_admin_can_delete_any(self, client, login_as, db):
        from dockerlabs.models import Notification

        sender_admin = _admin(db)
        receiver = _jugador(db)
        notif = make_notification(db, sender_id=sender_admin.id, receiver_id=receiver.id)
        notif_id = notif.id  # leído ANTES del DELETE, ver nota más abajo

        other_admin = _admin(db)
        csrf = login_as(other_admin)
        r = client.delete(f"/api/notifications/{notif_id}", headers={"X-CSRFToken": csrf})
        assert r.status_code == 200

        db.session.rollback()
        # NOTA: usamos `notif_id` (int ya leído), no `notif.id`: tras el
        # DELETE real + rollback(), `notif` queda expirado en el identity map
        # de esta sesión (se creó en este mismo test), así que acceder a
        # `notif.id` ahora dispararía un refresh imposible (la fila ya no
        # existe) y SQLAlchemy lanzaría ObjectDeletedError. Por el mismo
        # motivo tampoco usamos Notification.query.get(): intentaría
        # refrescar el objeto del identity map en vez de devolver None.
        assert Notification.query.filter_by(id=notif_id).first() is None

    def test_receiver_can_delete_own_targeted_notification(self, client, login_as, db):
        from dockerlabs.models import Notification

        admin = _admin(db)
        receiver = _jugador(db)
        notif = make_notification(db, sender_id=admin.id, receiver_id=receiver.id)
        notif_id = notif.id  # leído ANTES del DELETE, ver nota en el test anterior

        csrf = login_as(receiver)
        r = client.delete(f"/api/notifications/{notif_id}", headers={"X-CSRFToken": csrf})
        assert r.status_code == 200

        db.session.rollback()
        assert Notification.query.filter_by(id=notif_id).first() is None

    def test_non_admin_can_never_delete_a_global_notification(self, client, login_as, db):
        """Clave: receiver_id es None en una global, así que `receiver_id !=
        user_id` es SIEMPRE true para un no-admin (None != <cualquier id>),
        aunque esa misma persona pueda verla, leerla y reaccionar a ella."""
        from dockerlabs.models import Notification

        admin = _admin(db)
        someone = _jugador(db)
        notif = make_notification(db, sender_id=admin.id, receiver_id=None, title="Global borrable?")

        csrf = login_as(someone)
        r = client.delete(f"/api/notifications/{notif.id}", headers={"X-CSRFToken": csrf})
        assert r.status_code == 403

        db.session.rollback()
        assert Notification.query.get(notif.id) is not None

    def test_nonexistent_notification_404(self, client, login_as, db):
        user = _jugador(db)
        csrf = login_as(user)
        r = client.delete("/api/notifications/999999", headers={"X-CSRFToken": csrf})
        assert r.status_code == 404
