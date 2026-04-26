import unittest


try:
    import sqlalchemy  # noqa: F401
    _HAS_SQLALCHEMY = True
except Exception:
    _HAS_SQLALCHEMY = False


@unittest.skipUnless(_HAS_SQLALCHEMY, "SQLAlchemy is not installed; skipping swagger access tests")
class SwaggerAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dockerlabs.app import app

        cls.app = app
        cls.app.config["TESTING"] = True

    def setUp(self):
        self.client = self.app.test_client()

        from dockerlabs.extensions import db as alchemy_db
        from dockerlabs.models import User
        from werkzeug.security import generate_password_hash

        with self.app.app_context():
            admin = User.query.filter_by(username="admin_swagger").first()
            if not admin:
                admin = User(
                    username="admin_swagger",
                    email="admin_swagger@example.com",
                    password_hash=generate_password_hash("AdminTest123!"),
                    role="admin",
                )
                alchemy_db.session.add(admin)
                alchemy_db.session.commit()

            moderador = User.query.filter_by(username="mod_swagger").first()
            if not moderador:
                moderador = User(
                    username="mod_swagger",
                    email="mod_swagger@example.com",
                    password_hash=generate_password_hash("ModTest123!"),
                    role="moderador",
                )
                alchemy_db.session.add(moderador)
                alchemy_db.session.commit()

            jugador = User.query.filter_by(username="jug_swagger").first()
            if not jugador:
                jugador = User(
                    username="jug_swagger",
                    email="jug_swagger@example.com",
                    password_hash=generate_password_hash("JugadorTest123!"),
                    role="jugador",
                )
                alchemy_db.session.add(jugador)
                alchemy_db.session.commit()

            self.admin_id = admin.id
            self.mod_id = moderador.id
            self.jug_id = jugador.id

    def _login_as(self, user_id, username, csrf_token="test_csrf_token"):
        with self.client.session_transaction() as sess:
            sess["csrf_token"] = csrf_token
            sess["user_id"] = user_id
            sess["username"] = username
            sess["_user_id"] = str(user_id)
            sess["_fresh"] = True

    def test_swagger_requires_login(self):
        resp = self.client.get("/docs/", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

        resp = self.client.get("/apispec.json", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

    def test_swagger_forbidden_for_jugador(self):
        self._login_as(self.jug_id, "jug_swagger")

        resp = self.client.get("/docs/", follow_redirects=False)
        self.assertEqual(resp.status_code, 403)

        resp = self.client.get("/apispec.json", follow_redirects=False)
        self.assertEqual(resp.status_code, 403)

    def test_swagger_allowed_for_moderador(self):
        self._login_as(self.mod_id, "mod_swagger")

        resp = self.client.get("/docs/", follow_redirects=False)
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get("/apispec.json", follow_redirects=False)
        self.assertEqual(resp.status_code, 200)

    def test_swagger_allowed_for_admin(self):
        self._login_as(self.admin_id, "admin_swagger")

        resp = self.client.get("/docs/", follow_redirects=False)
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get("/apispec.json", follow_redirects=False)
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
