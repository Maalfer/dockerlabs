import os
import shutil
import tempfile
import unittest

try:
    import sqlalchemy  # noqa: F401
    _HAS_SQLALCHEMY = True
except Exception:
    _HAS_SQLALCHEMY = False


@unittest.skipUnless(_HAS_SQLALCHEMY, "SQLAlchemy is not installed; skipping machine submission tests")
class MachineSubmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dockerlabs.app import app

        cls.app = app
        cls.app.config["TESTING"] = True

        cls.db_path = cls.app.config["DATABASE"]
        cls._db_backup_dir = tempfile.mkdtemp(prefix="dockerlabs_test_db_backup_submission_")
        cls._db_backup_path = os.path.join(cls._db_backup_dir, "dockerlabs.db")

        if os.path.exists(cls.db_path):
            shutil.copyfile(cls.db_path, cls._db_backup_path)
        else:
            open(cls._db_backup_path, "ab").close()

    @classmethod
    def tearDownClass(cls):
        try:
            if os.path.exists(cls._db_backup_path):
                shutil.copyfile(cls._db_backup_path, cls.db_path)
        finally:
            shutil.rmtree(cls._db_backup_dir, ignore_errors=True)

    def setUp(self):
        self.client = self.app.test_client()

    def _set_csrf(self, csrf_token="test_csrf_token"):
        with self.client.session_transaction() as sess:
            sess["csrf_token"] = csrf_token

    def _create_test_user(self, username, email, role="jugador"):
        from dockerlabs.models import User
        from werkzeug.security import generate_password_hash

        with self.app.app_context():
            existing = User.query.filter_by(username=username).first()
            if existing:
                self.app.app_context().delete(existing)
                self.app.app_context().commit()
            
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash("TestPass123!"),
                role=role
            )
            self.app.app_context().add(user)
            self.app.app_context().commit()
            return user.id

    def _set_user_session(self, user_id, username):
        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["username"] = username
            sess["role"] = "jugador"
            sess["csrf_token"] = "test_csrf_token"

    def test_authenticated_user_can_submit_machine(self):
        """Test that an authenticated user can submit a machine with valid CSRF token."""
        from dockerlabs.models import PendingMachineSubmission

        # Create test user
        user_id = self._create_test_user("test_submitter", "submitter@test.com")
        self._set_user_session(user_id, "test_submitter")

        # Submit machine
        payload = {
            "nombre": "Test Machine",
            "link_maquina": "https://example.com/machine.zip",
            "dificultad": "Medio",
            "discord_user": "testuser#1234",
            "categoria": "Web",
            "tags": "web, linux",
            "descripcion": "A test machine for submission",
            "notas": "Test notes",
            "writeup_url": "https://example.com/writeup.pdf"
        }

        resp = self.client.post(
            "/api/submit-machine",
            json=payload,
            headers={"X-CSRFToken": "test_csrf_token"}
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("pendiente de revisión", data.get("message", ""))

        # Verify submission was saved to database
        with self.app.app_context():
            submission = PendingMachineSubmission.query.filter_by(
                nombre="Test Machine",
                autor_solicitante="test_submitter"
            ).first()
            self.assertIsNotNone(submission)
            self.assertEqual(submission.estado, "pendiente")
            self.assertEqual(submission.link_maquina, "https://example.com/machine.zip")

    def test_unauthenticated_user_cannot_submit_machine(self):
        """Test that unauthenticated users cannot submit machines."""
        payload = {
            "nombre": "Test Machine",
            "link_maquina": "https://example.com/machine.zip",
            "dificultad": "Medio",
            "discord_user": "testuser#1234",
            "categoria": "Web",
            "descripcion": "A test machine",
            "writeup_url": "https://example.com/writeup.pdf"
        }

        resp = self.client.post(
            "/api/submit-machine",
            json=payload,
            headers={"X-CSRFToken": "test_csrf_token"}
        )

        self.assertEqual(resp.status_code, 401)
        data = resp.get_json()
        self.assertIn("Debes iniciar sesión", data.get("error", ""))

    def test_invalid_csrf_token_rejected(self):
        """Test that invalid CSRF token is rejected."""
        user_id = self._create_test_user("test_submitter2", "submitter2@test.com")
        self._set_user_session(user_id, "test_submitter2")

        payload = {
            "nombre": "Test Machine",
            "link_maquina": "https://example.com/machine.zip",
            "dificultad": "Medio",
            "discord_user": "testuser#1234",
            "categoria": "Web",
            "descripcion": "A test machine",
            "writeup_url": "https://example.com/writeup.pdf"
        }

        resp = self.client.post(
            "/api/submit-machine",
            json=payload,
            headers={"X-CSRFToken": "invalid_token"}
        )

        self.assertEqual(resp.status_code, 403)

    def test_missing_required_field_rejected(self):
        """Test that missing required fields are rejected."""
        user_id = self._create_test_user("test_submitter3", "submitter3@test.com")
        self._set_user_session(user_id, "test_submitter3")

        # Missing required field: nombre
        payload = {
            "link_maquina": "https://example.com/machine.zip",
            "dificultad": "Medio",
            "discord_user": "testuser#1234",
            "categoria": "Web",
            "descripcion": "A test machine",
            "writeup_url": "https://example.com/writeup.pdf"
        }

        resp = self.client.post(
            "/api/submit-machine",
            json=payload,
            headers={"X-CSRFToken": "test_csrf_token"}
        )

        # FastAPI/Pydantic should return 422 for validation errors
        self.assertIn(resp.status_code, [400, 422])

    def test_optional_fields_are_optional(self):
        """Test that optional fields can be omitted."""
        from dockerlabs.models import PendingMachineSubmission

        user_id = self._create_test_user("test_submitter4", "submitter4@test.com")
        self._set_user_session(user_id, "test_submitter4")

        # Only required fields
        payload = {
            "nombre": "Minimal Machine",
            "link_maquina": "https://example.com/machine.zip",
            "dificultad": "Fácil",
            "discord_user": "minimal#1234",
            "categoria": "Misc",
            "descripcion": "Minimal submission",
            "writeup_url": "https://example.com/writeup.pdf"
        }

        resp = self.client.post(
            "/api/submit-machine",
            json=payload,
            headers={"X-CSRFToken": "test_csrf_token"}
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))

        # Verify submission was saved
        with self.app.app_context():
            submission = PendingMachineSubmission.query.filter_by(
                nombre="Minimal Machine"
            ).first()
            self.assertIsNotNone(submission)
            self.assertIsNone(submission.tags)
            self.assertIsNone(submission.notas)

    def test_csrf_token_from_form_data(self):
        """Test that CSRF token can be sent via form data (multipart/form-data)."""
        from dockerlabs.models import PendingMachineSubmission

        user_id = self._create_test_user("test_submitter5", "submitter5@test.com")
        self._set_user_session(user_id, "test_submitter5")

        payload = {
            "nombre": "Form Data Machine",
            "link_maquina": "https://example.com/machine.zip",
            "dificultad": "Difícil",
            "discord_user": "formuser#1234",
            "categoria": "Services",
            "descripcion": "Form data submission",
            "writeup_url": "https://example.com/writeup.pdf",
            "csrf_token": "test_csrf_token"
        }

        resp = self.client.post(
            "/api/submit-machine",
            data=payload,
            content_type="multipart/form-data"
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))

        # Verify submission was saved
        with self.app.app_context():
            submission = PendingMachineSubmission.query.filter_by(
                nombre="Form Data Machine"
            ).first()
            self.assertIsNotNone(submission)


if __name__ == "__main__":
    unittest.main()
