import os
import shutil
import tempfile
import unittest

try:
    import sqlalchemy  # noqa: F401
    _HAS_SQLALCHEMY = True
except Exception:
    _HAS_SQLALCHEMY = False


@unittest.skipUnless(_HAS_SQLALCHEMY, "SQLAlchemy is not installed; skipping update user role tests")
class UpdateUserRoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dockerlabs.app import app

        cls.app = app
        cls.app.config["TESTING"] = True

        cls.db_path = cls.app.config["DATABASE"]
        cls._db_backup_dir = tempfile.mkdtemp(prefix="dockerlabs_test_db_backup_role_")
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

    def _set_admin_session(self, user_id, username):
        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["username"] = username
            sess["role"] = "admin"
            sess["csrf_token"] = "test_csrf_token"

    def _set_moderator_session(self, user_id, username):
        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["username"] = username
            sess["role"] = "moderador"
            sess["csrf_token"] = "test_csrf_token"

    def test_admin_can_update_user_role(self):
        """Test that an admin can successfully update a user's role."""
        from dockerlabs.models import User

        # Create admin user
        admin_id = self._create_test_user("test_admin", "admin@test.com", "admin")
        # Create regular user
        user_id = self._create_test_user("test_user", "user@test.com", "jugador")

        # Set admin session
        self._set_admin_session(admin_id, "test_admin")

        # Update user role to moderador
        payload = {
            "role": "moderador"
        }

        resp = self.client.post(
            f"/api/admin/update_user_role/{user_id}",
            json=payload,
            headers={"X-CSRFToken": "test_csrf_token"}
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("actualizado", data.get("message", ""))

        # Verify role was updated in database
        with self.app.app_context():
            user = User.query.get(user_id)
            self.assertEqual(user.role, "moderador")

    def test_moderator_cannot_assign_admin_role(self):
        """Test that a moderator cannot assign admin role to users."""
        from dockerlabs.models import User

        # Create moderator user
        mod_id = self._create_test_user("test_mod", "mod@test.com", "moderador")
        # Create regular user
        user_id = self._create_test_user("test_user2", "user2@test.com", "jugador")

        # Set moderator session
        self._set_moderator_session(mod_id, "test_mod")

        # Try to assign admin role
        payload = {
            "role": "admin"
        }

        resp = self.client.post(
            f"/api/admin/update_user_role/{user_id}",
            json=payload,
            headers={"X-CSRFToken": "test_csrf_token"}
        )

        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertIn("moderadores no pueden asignar rol de admin", data.get("error", ""))

        # Verify role was NOT updated
        with self.app.app_context():
            user = User.query.get(user_id)
            self.assertEqual(user.role, "jugador")

    def test_moderator_can_assign_moderator_role(self):
        """Test that a moderator can assign moderator role to regular users."""
        from dockerlabs.models import User

        # Create moderator user
        mod_id = self._create_test_user("test_mod2", "mod2@test.com", "moderador")
        # Create regular user
        user_id = self._create_test_user("test_user3", "user3@test.com", "jugador")

        # Set moderator session
        self._set_moderator_session(mod_id, "test_mod2")

        # Assign moderator role
        payload = {
            "role": "moderador"
        }

        resp = self.client.post(
            f"/api/admin/update_user_role/{user_id}",
            json=payload,
            headers={"X-CSRFToken": "test_csrf_token"}
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))

        # Verify role was updated
        with self.app.app_context():
            user = User.query.get(user_id)
            self.assertEqual(user.role, "moderador")

    def test_unauthenticated_user_cannot_update_role(self):
        """Test that unauthenticated users cannot update roles."""
        from dockerlabs.models import User

        # Create user without setting session
        user_id = self._create_test_user("test_user4", "user4@test.com", "jugador")

        payload = {
            "role": "admin"
        }

        resp = self.client.post(
            f"/api/admin/update_user_role/{user_id}",
            json=payload,
            headers={"X-CSRFToken": "test_csrf_token"}
        )

        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertIn("Acceso denegado", data.get("error", ""))

    def test_invalid_role_rejected(self):
        """Test that invalid role values are rejected."""
        from dockerlabs.models import User

        # Create admin user
        admin_id = self._create_test_user("test_admin2", "admin2@test.com", "admin")
        # Create regular user
        user_id = self._create_test_user("test_user5", "user5@test.com", "jugador")

        # Set admin session
        self._set_admin_session(admin_id, "test_admin2")

        # Try to assign invalid role
        payload = {
            "role": "superadmin"
        }

        resp = self.client.post(
            f"/api/admin/update_user_role/{user_id}",
            json=payload,
            headers={"X-CSRFToken": "test_csrf_token"}
        )

        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn("Rol inválido", data.get("error", ""))

    def test_nonexistent_user_returns_404(self):
        """Test that updating a non-existent user returns 404."""
        # Create admin user
        admin_id = self._create_test_user("test_admin3", "admin3@test.com", "admin")

        # Set admin session
        self._set_admin_session(admin_id, "test_admin3")

        # Try to update non-existent user
        payload = {
            "role": "moderador"
        }

        resp = self.client.post(
            "/api/admin/update_user_role/99999",
            json=payload,
            headers={"X-CSRFToken": "test_csrf_token"}
        )

        self.assertEqual(resp.status_code, 404)
        data = resp.get_json()
        self.assertIn("Usuario no encontrado", data.get("error", ""))


if __name__ == "__main__":
    unittest.main()
