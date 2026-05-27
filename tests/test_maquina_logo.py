import io
import unittest
import os
import tempfile
import shutil

try:
    import sqlalchemy  # noqa: F401
    from PIL import Image
    _HAS_DEPS = True
except Exception:
    _HAS_DEPS = False


@unittest.skipUnless(_HAS_DEPS, "Dependencies not installed; skipping logo tests")
class MachineLogoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dockerlabs.app import app

        cls.app = app
        cls.app.config["TESTING"] = True
        
        # Setup temporary DB for testing
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
        from dockerlabs.models import User, Machine
        from werkzeug.security import generate_password_hash

        with self.app.app_context():
            # Setup admin user
            admin = User.query.filter_by(username="admin_test_logo").first()
            if not admin:
                admin = User(
                    username="admin_test_logo",
                    email="admin_test_logo@example.com",
                    password_hash=generate_password_hash("AdminTest123!"),
                    role="admin",
                )
                alchemy_db.session.add(admin)
                alchemy_db.session.commit()

            self.admin_id = admin.id
            self.admin_username = admin.username
            
            # Setup a test machine
            machine = Machine.query.filter_by(nombre="test_logo_machine").first()
            if not machine:
                machine = Machine(
                    nombre="test_logo_machine",
                    dificultad="Fácil",
                    clase="Linux",
                    autor="Admin",
                    origen="docker",
                    color="#ffffff",
                    enlace_autor="",
                    fecha="2026-01-01",
                    imagen="dockerlabs/images/logos/test.jpg",
                    descripcion="Desc",
                    link_descarga="Link"
                )
                alchemy_db.session.add(machine)
                alchemy_db.session.commit()
            
            self.machine_id = machine.id

    def _login_as(self, user_id, username, csrf_token="test_csrf_token"):
        with self.client.session_transaction() as sess:
            sess["csrf_token"] = csrf_token
            sess["user_id"] = user_id
            sess["username"] = username
            sess["_user_id"] = str(user_id)
            sess["_fresh"] = True

    def test_upload_and_serve_machine_logo(self):
        self._login_as(self.admin_id, self.admin_username)

        # 1. Create a dummy image
        img_byte_arr = io.BytesIO()
        img = Image.new('RGB', (100, 100), color='red')
        img.save(img_byte_arr, format='JPEG')
        img_bytes = img_byte_arr.getvalue()
        
        # 2. Upload the logo
        data = {
            "csrf_token": "test_csrf_token",
            "machine_id": str(self.machine_id),
            "origen": "docker",
            "logo": (io.BytesIO(img_bytes), "test_logo.jpg")
        }
        
        response = self.client.post("/gestion-maquinas/upload-logo", data=data, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertIn("image_url", json_data)
        
        # 3. Verify it was saved in DB
        from dockerlabs.models import Machine
        with self.app.app_context():
            maq = Machine.query.get(self.machine_id)
            self.assertIsNotNone(maq.logo_data)
            self.assertEqual(maq.logo_mime, "image/jpeg")
            self.assertEqual(maq.logo_data, img_bytes)

        # 4. Fetch the logo from the serve endpoint
        serve_resp = self.client.get(f"/img/maquina/{self.machine_id}")
        self.assertEqual(serve_resp.status_code, 200)
        self.assertEqual(serve_resp.mimetype, "image/jpeg")
        self.assertEqual(serve_resp.data, img_bytes)

if __name__ == "__main__":
    unittest.main()
