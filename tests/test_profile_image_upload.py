import os
import shutil
import tempfile
import unittest
import io

try:
    import sqlalchemy  # noqa: F401
    _HAS_SQLALCHEMY = True
except Exception:
    _HAS_SQLALCHEMY = False


@unittest.skipUnless(_HAS_SQLALCHEMY, "SQLAlchemy is not installed; skipping profile image upload tests")
class ProfileImageUploadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dockerlabs.app import app

        cls.app = app
        cls.app.config["TESTING"] = True

        cls.db_path = cls.app.config["DATABASE"]
        cls._db_backup_dir = tempfile.mkdtemp(prefix="dockerlabs_test_db_backup_profile_")
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

    def _create_test_image(self, format="PNG"):
        """Create a simple test image in memory."""
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        img_io = io.BytesIO()
        img.save(img_io, format=format)
        img_io.seek(0)
        return img_io

    def test_authenticated_user_can_upload_profile_image(self):
        """Test that an authenticated user can upload a profile image."""
        user_id = self._create_test_user("test_profile_user", "profile@test.com")
        self._set_user_session(user_id, "test_profile_user")

        # Create a test PNG image
        image_data = self._create_test_image("PNG")
        
        data = {
            'photo': (io.BytesIO(image_data.read()), 'test_profile.png')
        }

        resp = self.client.post(
            "/api/upload-profile-photo",
            data=data,
            content_type="multipart/form-data",
            headers={"X-CSRFToken": "test_csrf_token"}
        )

        self.assertEqual(resp.status_code, 200)
        response_data = resp.get_json()
        self.assertIn("message", response_data)
        self.assertIn("image_url", response_data)
        self.assertIn("actualizada correctamente", response_data["message"])

    def test_unauthenticated_user_cannot_upload_image(self):
        """Test that unauthenticated users cannot upload profile images."""
        image_data = self._create_test_image("PNG")
        
        data = {
            'photo': (io.BytesIO(image_data.read()), 'test_profile.png')
        }

        resp = self.client.post(
            "/api/upload-profile-photo",
            data=data,
            content_type="multipart/form-data",
            headers={"X-CSRFToken": "test_csrf_token"}
        )

        self.assertEqual(resp.status_code, 401)
        response_data = resp.get_json()
        self.assertIn("error", response_data)
        self.assertIn("Debes iniciar sesión", response_data["error"])

    def test_invalid_file_type_rejected(self):
        """Test that non-image files are rejected."""
        user_id = self._create_test_user("test_profile_user2", "profile2@test.com")
        self._set_user_session(user_id, "test_profile_user2")

        # Create a text file instead of an image
        text_data = io.BytesIO(b"This is not an image")
        
        data = {
            'photo': (text_data, 'test.txt')
        }

        resp = self.client.post(
            "/api/upload-profile-photo",
            data=data,
            content_type="multipart/form-data",
            headers={"X-CSRFToken": "test_csrf_token"}
        )

        self.assertEqual(resp.status_code, 400)
        response_data = resp.get_json()
        self.assertIn("error", response_data)

    def test_file_too_large_rejected(self):
        """Test that files larger than 5MB are rejected."""
        user_id = self._create_test_user("test_profile_user3", "profile3@test.com")
        self._set_user_session(user_id, "test_profile_user3")

        # Create a large file (>5MB)
        large_data = io.BytesIO(b'x' * (6 * 1024 * 1024))
        
        data = {
            'photo': (large_data, 'large.png')
        }

        resp = self.client.post(
            "/api/upload-profile-photo",
            data=data,
            content_type="multipart/form-data",
            headers={"X-CSRFToken": "test_csrf_token"}
        )

        self.assertEqual(resp.status_code, 400)
        response_data = resp.get_json()
        self.assertIn("error", response_data)
        self.assertIn("demasiado grande", response_data["error"])

    def test_invalid_csrf_token_rejected(self):
        """Test that invalid CSRF token is rejected."""
        user_id = self._create_test_user("test_profile_user4", "profile4@test.com")
        self._set_user_session(user_id, "test_profile_user4")

        image_data = self._create_test_image("PNG")
        
        data = {
            'photo': (io.BytesIO(image_data.read()), 'test_profile.png')
        }

        resp = self.client.post(
            "/api/upload-profile-photo",
            data=data,
            content_type="multipart/form-data",
            headers={"X-CSRFToken": "invalid_token"}
        )

        self.assertEqual(resp.status_code, 403)

    def test_missing_file_rejected(self):
        """Test that requests without a file are rejected."""
        user_id = self._create_test_user("test_profile_user5", "profile5@test.com")
        self._set_user_session(user_id, "test_profile_user5")

        data = {}

        resp = self.client.post(
            "/api/upload-profile-photo",
            data=data,
            content_type="multipart/form-data",
            headers={"X-CSRFToken": "test_csrf_token"}
        )

        self.assertEqual(resp.status_code, 400)
        response_data = resp.get_json()
        self.assertIn("error", response_data)

    def test_various_image_formats_accepted(self):
        """Test that various image formats are accepted."""
        user_id = self._create_test_user("test_profile_user6", "profile6@test.com")
        self._set_user_session(user_id, "test_profile_user6")

        formats = ["PNG", "JPEG", "GIF", "WEBP"]
        
        for fmt in formats:
            image_data = self._create_test_image(fmt)
            
            ext_map = {"PNG": ".png", "JPEG": ".jpg", "GIF": ".gif", "WEBP": ".webp"}
            filename = f"test{ext_map[fmt]}"
            
            data = {
                'photo': (io.BytesIO(image_data.read()), filename)
            }

            resp = self.client.post(
                "/api/upload-profile-photo",
                data=data,
                content_type="multipart/form-data",
                headers={"X-CSRFToken": "test_csrf_token"}
            )

            self.assertEqual(resp.status_code, 200, f"Failed for format {fmt}")
            response_data = resp.get_json()
            self.assertIn("message", response_data)


if __name__ == "__main__":
    unittest.main()
