import io
import os
import shutil
import sqlite3
import tempfile
import unittest
import zipfile


try:
    import sqlalchemy  # noqa: F401
    _HAS_SQLALCHEMY = True
except Exception:
    _HAS_SQLALCHEMY = False


@unittest.skipUnless(_HAS_SQLALCHEMY, "SQLAlchemy is not installed; skipping backups tests")
class BackupsAdminTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from asgi import fastapi_app as app

        cls.app = app
        cls.app.config["TESTING"] = True

        cls.db_path = cls.app.config["DATABASE"]
        cls._db_backup_dir = tempfile.mkdtemp(prefix="dockerlabs_test_db_backup_")
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

        from dockerlabs.extensions import db as alchemy_db
        from dockerlabs.models import User
        from werkzeug.security import generate_password_hash

        with self.app.app_context():
            admin = User.query.filter_by(username="admin_test").first()
            if not admin:
                admin = User(
                    username="admin_test",
                    email="admin_test@example.com",
                    password_hash=generate_password_hash("AdminTest123!"),
                    role="admin",
                )
                alchemy_db.session.add(admin)
                alchemy_db.session.commit()

            jugador = User.query.filter_by(username="jugador_test").first()
            if not jugador:
                jugador = User(
                    username="jugador_test",
                    email="jugador_test@example.com",
                    password_hash=generate_password_hash("JugadorTest123!"),
                    role="jugador",
                )
                alchemy_db.session.add(jugador)
                alchemy_db.session.commit()

            self.admin_id = admin.id
            self.admin_username = admin.username
            self.jugador_id = jugador.id
            self.jugador_username = jugador.username

    def _login_as(self, user_id, username, csrf_token="test_csrf_token"):
        with self.client.session_transaction() as sess:
            sess["csrf_token"] = csrf_token
            sess["user_id"] = user_id
            sess["username"] = username
            sess["_user_id"] = str(user_id)
            sess["_fresh"] = True

    def test_backups_page_forbidden_for_non_admin(self):
        self._login_as(self.jugador_id, self.jugador_username)
        resp = self.client.get("/backups")
        self.assertEqual(resp.status_code, 403)

    def test_backups_page_available_for_admin(self):
        self._login_as(self.admin_id, self.admin_username)
        resp = self.client.get("/backups")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Backups", resp.data)

    def test_download_backup_zip(self):
        self._login_as(self.admin_id, self.admin_username)
        resp = self.client.post("/backups/download", data={"csrf_token": "test_csrf_token"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, "application/zip")

        zf = zipfile.ZipFile(io.BytesIO(resp.data), "r")
        names = zf.namelist()
        self.assertTrue(any(n.lower().endswith(".db") for n in names))
        # Verificar que el backup incluya la carpeta almacenamiento
        self.assertTrue(any("almacenamiento" in n for n in names))

    def test_restore_roundtrip(self):
        self._login_as(self.admin_id, self.admin_username)

        download = self.client.post("/backups/download", data={"csrf_token": "test_csrf_token"})
        self.assertEqual(download.status_code, 200)

        db_path = self.app.config["DATABASE"]
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                ("restore_tmp_user", "restore_tmp_user@example.com", "x", "jugador"),
            )
            conn.commit()

        with sqlite3.connect(db_path) as conn:
            cur = conn.execute("SELECT COUNT(*) FROM users WHERE username=?", ("restore_tmp_user",))
            self.assertEqual(cur.fetchone()[0], 1)

        data = {
            "csrf_token": "test_csrf_token",
            "backup_zip": (io.BytesIO(download.data), "backup.zip"),
        }
        restore = self.client.post("/backups/restore", data=data, content_type="multipart/form-data")
        self.assertEqual(restore.status_code, 302)

        with sqlite3.connect(db_path) as conn:
            cur = conn.execute("SELECT COUNT(*) FROM users WHERE username=?", ("restore_tmp_user",))
            self.assertEqual(cur.fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
