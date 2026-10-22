"""Tests de dockerlabs/routes/perfil.py — contraseña, perfil, redes y foto."""
import io
import uuid

import pytest

from tests.factories import make_certificate, make_machine, make_user, make_writeup

pytestmark = pytest.mark.integration


class TestChangePassword:
    def test_correct_current_password_succeeds_and_refreshes_cookie(self, client, login_as, db):
        user = make_user(db, password="OldPassw0rd!")
        original_version = user.session_version
        csrf = login_as(user)

        r = client.post("/api/change_password", json={
            "current_password": "OldPassw0rd!",
            "new_password": "NewPassw0rd!",
            "confirm_password": "NewPassw0rd!",
        }, headers={"X-CSRFToken": csrf})
        assert r.status_code == 200
        assert r.json()["success"] is True
        assert "session" in r.cookies  # cookie refrescada en la respuesta

        db.session.rollback()
        from dockerlabs.models import User
        refreshed = User.query.get(user.id)
        assert refreshed.session_version == original_version + 1

        # El MISMO client, sin volver a hacer login, sigue autenticado: la
        # cookie que TestClient acaba de guardar ya trae el session_version
        # nuevo.
        r2 = client.get(f"/api/completed_machines/{user.username}")
        assert r2.status_code == 200

    def test_wrong_current_password_rejected(self, client, login_as, db):
        user = make_user(db, password="OldPassw0rd!")
        csrf = login_as(user)

        r = client.post("/api/change_password", json={
            "current_password": "NotTheRealOne!",
            "new_password": "NewPassw0rd!",
            "confirm_password": "NewPassw0rd!",
        }, headers={"X-CSRFToken": csrf})
        assert r.status_code == 400

    def test_mismatched_confirmation_rejected(self, client, login_as, db):
        user = make_user(db, password="OldPassw0rd!")
        csrf = login_as(user)

        r = client.post("/api/change_password", json={
            "current_password": "OldPassw0rd!",
            "new_password": "NewPassw0rd!",
            "confirm_password": "Different1!",
        }, headers={"X-CSRFToken": csrf})
        assert r.status_code == 400

    def test_weak_new_password_rejected(self, client, login_as, db):
        user = make_user(db, password="OldPassw0rd!")
        csrf = login_as(user)

        r = client.post("/api/change_password", json={
            "current_password": "OldPassw0rd!",
            "new_password": "alllowercase",
            "confirm_password": "alllowercase",
        }, headers={"X-CSRFToken": csrf})
        assert r.status_code == 400


class TestUpdateProfile:
    def test_biography_html_is_sanitized(self, client, login_as, db):
        user = make_user(db)
        csrf = login_as(user)

        r = client.post("/api/update_profile", json={
            "biography": "<script>alert(1)</script>Hola <b>mundo</b>",
            "nombre_diploma": None,
        }, headers={"X-CSRFToken": csrf})
        assert r.status_code == 200

        db.session.rollback()
        from dockerlabs.models import User
        refreshed = User.query.get(user.id)
        assert "<script>" not in refreshed.biography
        assert "<b>" not in refreshed.biography
        assert "Hola" in refreshed.biography and "mundo" in refreshed.biography

    def test_changing_nombre_diploma_triggers_certificate_resync_without_error(self, client, login_as, db):
        user = make_user(db)
        machine = make_machine(db, origen="docker")
        make_writeup(db, maquina=machine.nombre, autor=user.username)
        make_certificate(db, user=user, machine_name=machine.nombre)
        csrf = login_as(user)

        r = client.post("/api/update_profile", json={
            "biography": "bio",
            "nombre_diploma": "Nombre Nuevo Para El Diploma",
        }, headers={"X-CSRFToken": csrf})
        # La resincronización corre como BackgroundTask (síncrona bajo
        # TestClient) y está envuelta en sync_user_certificates_safe, que
        # nunca debe tumbar la respuesta aunque el renderizado falle (p.ej.
        # en este entorno de test no existe la fuente DejaVuSans-Bold del
        # VPS en /usr/share/fonts/..., así que el PDF no llega a regenerarse
        # de verdad, pero el endpoint sigue respondiendo 200 sin error).
        assert r.status_code == 200
        assert r.json()["success"] is True

        db.session.rollback()
        from dockerlabs.models import User
        refreshed = User.query.get(user.id)
        assert refreshed.nombre_diploma == "Nombre Nuevo Para El Diploma"

    def test_updating_profile_without_changing_nombre_diploma_does_not_error(self, client, login_as, db):
        user = make_user(db, nombre_diploma="Ya Fijado")
        csrf = login_as(user)

        r = client.post("/api/update_profile", json={
            "biography": "otra bio",
            "nombre_diploma": "Ya Fijado",
        }, headers={"X-CSRFToken": csrf})
        assert r.status_code == 200
        assert r.json()["success"] is True


class TestUpdateSocialLinks:
    def test_valid_urls_accepted(self, client, login_as, db):
        user = make_user(db)
        csrf = login_as(user)

        r = client.post("/api/update_social_links", json={
            "linkedin_url": "https://linkedin.com/in/someone",
            "github_url": "https://github.com/someone",
            "youtube_url": "https://youtube.com/someone",
        }, headers={"X-CSRFToken": csrf})
        assert r.status_code == 200

        db.session.rollback()
        from dockerlabs.models import User
        refreshed = User.query.get(user.id)
        assert refreshed.linkedin_url == "https://linkedin.com/in/someone"

    def test_dangerous_url_rejected(self, client, login_as, db):
        user = make_user(db)
        csrf = login_as(user)

        r = client.post("/api/update_social_links", json={
            "linkedin_url": "javascript:alert(1)",
        }, headers={"X-CSRFToken": csrf})
        assert r.status_code == 400


class TestRequestEmailChange:
    def _clear_rate_limit(self):
        from dockerlabs.routes import perfil as perfil_routes
        perfil_routes._email_change_hits.clear()

    def test_wrong_current_password_rejected(self, client, login_as, db, mock_smtp):
        self._clear_rate_limit()
        user = make_user(db, password="MyPassw0rd!")
        csrf = login_as(user)

        r = client.post("/api/request_email_change", json={
            "current_password": "NotTheRealOne!",
            "new_email": "nuevo@example.test",
        }, headers={"X-CSRFToken": csrf})
        assert r.status_code == 400

    def test_without_smtp_configured_returns_503(self, client, login_as, db, monkeypatch):
        self._clear_rate_limit()
        monkeypatch.delenv("SMTP_FROM", raising=False)
        monkeypatch.delenv("SMTP_USER", raising=False)
        user = make_user(db, password="MyPassw0rd!")
        csrf = login_as(user)

        r = client.post("/api/request_email_change", json={
            "current_password": "MyPassw0rd!",
            "new_email": "nuevo@example.test",
        }, headers={"X-CSRFToken": csrf})
        assert r.status_code == 503

    def test_new_email_same_as_current_rejected(self, client, login_as, db, mock_smtp):
        self._clear_rate_limit()
        user = make_user(db, password="MyPassw0rd!")
        csrf = login_as(user)

        r = client.post("/api/request_email_change", json={
            "current_password": "MyPassw0rd!",
            "new_email": user.email,
        }, headers={"X-CSRFToken": csrf})
        assert r.status_code == 400

    def test_new_email_already_taken_by_another_user_rejected(self, client, login_as, db, mock_smtp):
        self._clear_rate_limit()
        user = make_user(db, password="MyPassw0rd!")
        other = make_user(db)
        csrf = login_as(user)

        r = client.post("/api/request_email_change", json={
            "current_password": "MyPassw0rd!",
            "new_email": other.email,
        }, headers={"X-CSRFToken": csrf})
        assert r.status_code == 400

    def test_success_sends_two_emails(self, client, login_as, db, mock_smtp):
        self._clear_rate_limit()
        user = make_user(db, password="MyPassw0rd!")
        csrf = login_as(user)
        new_email = f"{uuid.uuid4().hex[:10]}@example.test"

        r = client.post("/api/request_email_change", json={
            "current_password": "MyPassw0rd!",
            "new_email": new_email,
        }, headers={"X-CSRFToken": csrf})
        assert r.status_code == 200
        assert r.json()["success"] is True

        assert len(mock_smtp) == 2
        recipients = {m["to"] for m in mock_smtp}
        assert new_email in recipients
        assert user.email in recipients

    def test_rate_limited_after_three_requests(self, client, login_as, db, mock_smtp):
        self._clear_rate_limit()
        user = make_user(db, password="MyPassw0rd!")
        csrf = login_as(user)

        for i in range(3):
            r = client.post("/api/request_email_change", json={
                "current_password": "MyPassw0rd!",
                "new_email": f"{uuid.uuid4().hex[:10]}@example.test",
            }, headers={"X-CSRFToken": csrf})
            assert r.status_code == 200, f"la petición {i + 1} debería haber pasado"

        r4 = client.post("/api/request_email_change", json={
            "current_password": "MyPassw0rd!",
            "new_email": f"{uuid.uuid4().hex[:10]}@example.test",
        }, headers={"X-CSRFToken": csrf})
        assert r4.status_code == 429


class TestUploadProfilePhoto:
    def _png_bytes(self, size=(10, 10)):
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", size, "blue").save(buf, format="PNG")
        return buf.getvalue()

    def test_valid_image_saved_as_webp_and_replaces_old_photo(self, client, login_as, db):
        user = make_user(db)
        csrf = login_as(user)

        r = client.post(
            "/api/upload-profile-photo",
            files={"photo": ("avatar.png", self._png_bytes(), "image/png")},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 200
        assert "image_url" in r.json()

        db.session.rollback()
        from dockerlabs.models import User
        refreshed = User.query.get(user.id)
        first_path = refreshed.profile_image_path
        assert first_path is not None
        assert first_path.endswith(".webp")
        assert refreshed.profile_image_mime == "image/webp"

        # Subir una segunda foto reemplaza la anterior (ruta distinta, por el
        # timestamp en el nombre de fichero).
        import time
        time.sleep(1.1)
        r2 = client.post(
            "/api/upload-profile-photo",
            files={"photo": ("avatar2.png", self._png_bytes(), "image/png")},
            headers={"X-CSRFToken": csrf},
        )
        assert r2.status_code == 200

        db.session.rollback()
        refreshed2 = User.query.get(user.id)
        assert refreshed2.profile_image_path != first_path

    def test_oversized_image_rejected(self, client, login_as, db):
        user = make_user(db)
        csrf = login_as(user)

        oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * (6 * 1024 * 1024)
        r = client.post(
            "/api/upload-profile-photo",
            files={"photo": ("big.png", oversized, "image/png")},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 400
        assert "grande" in r.json()["error"]

    def test_non_image_rejected(self, client, login_as, db):
        user = make_user(db)
        csrf = login_as(user)

        r = client.post(
            "/api/upload-profile-photo",
            files={"photo": ("not_an_image.png", b"this is not an image at all", "image/png")},
            headers={"X-CSRFToken": csrf},
        )
        assert r.status_code == 400
