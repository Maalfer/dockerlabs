import os
import shutil
import tempfile
import unittest


try:
    import sqlalchemy  # noqa: F401
    _HAS_SQLALCHEMY = True
except Exception:
    _HAS_SQLALCHEMY = False


@unittest.skipUnless(_HAS_SQLALCHEMY, "SQLAlchemy is not installed; skipping register tests")
class RegisterTermsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dockerlabs.app import app

        cls.app = app
        cls.app.config["TESTING"] = True

        cls.db_path = cls.app.config["DATABASE"]
        cls._db_backup_dir = tempfile.mkdtemp(prefix="dockerlabs_test_db_backup_terms_")
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

    def test_register_rejected_if_terms_missing(self):
        self._set_csrf()

        payload = {
            "csrf_token": "test_csrf_token",
            "username": "terms_missing_user",
            "email": "terms_missing_user@example.com",
            "password": "TestPass123!",
            "password2": "TestPass123!",
            # intentionally no "terms"
        }

        resp = self.client.post("/register", data=payload)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            b"Debes aceptar los T\xc3\xa9rminos y Condiciones para registrarte.",
            resp.data,
        )

        from dockerlabs.models import User

        with self.app.app_context():
            user = User.query.filter_by(username="terms_missing_user").first()
            self.assertIsNone(user)


if __name__ == "__main__":
    unittest.main()
