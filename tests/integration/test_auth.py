"""Tests de dockerlabs/routes/auth.py — alta, acceso y recuperación de contraseña.

Endpoints públicos (sin sesión): POST /api/auth/login, /api/auth/register,
/api/auth/forgot-password, /api/auth/reset-password, y GET /verify-email.
"""
import uuid
from datetime import datetime, timedelta

import pytest

from tests.factories import (
    make_machine,
    make_password_reset_token,
    make_user,
    make_writeup,
)

pytestmark = pytest.mark.integration


def _uname(prefix="u"):
    """Username único válido para /api/auth/register (<=20 chars, regex-safe)."""
    return f"{prefix}{uuid.uuid4().hex[:10]}"


def _register_payload(**overrides):
    base = {
        "username": _uname(),
        "email": f"{uuid.uuid4().hex[:10]}@example.test",
        "password": "Str0ngPassw0rd!",
        "password2": "Str0ngPassw0rd!",
        "terms": True,
    }
    base.update(overrides)
    return base


class TestLogin:
    def test_correct_credentials_returns_200_and_authenticates(self, client, db):
        user = make_user(db, password="Str0ngPassw0rd!")
        r = client.post("/api/auth/login", json={"username": user.username, "password": "Str0ngPassw0rd!"})
        assert r.status_code == 200
        assert r.json()["success"] is True
        assert "session" in r.cookies

        # La cookie de sesión recién fijada autentica la siguiente petición.
        r2 = client.get(f"/api/completed_machines/{user.username}")
        assert r2.status_code == 200

    def test_wrong_password_returns_401_generic_message(self, client, db):
        user = make_user(db, password="Str0ngPassw0rd!")
        r = client.post("/api/auth/login", json={"username": user.username, "password": "WrongPassword1!"})
        assert r.status_code == 401
        assert r.json()["success"] is False
        return r.json()["message"]

    def test_unknown_user_and_wrong_password_return_identical_message(self, client, db):
        # No debe poder distinguirse si el usuario existe o no (anti username-enumeration).
        user = make_user(db, password="Str0ngPassw0rd!")

        r_wrong_pw = client.post("/api/auth/login", json={"username": user.username, "password": "WrongPassword1!"})
        r_unknown = client.post("/api/auth/login", json={"username": f"nope_{uuid.uuid4().hex[:8]}", "password": "WrongPassword1!"})

        assert r_wrong_pw.status_code == r_unknown.status_code == 401
        assert r_wrong_pw.json() == r_unknown.json()

    def test_missing_fields_rejected(self, client):
        r = client.post("/api/auth/login", json={})
        # Validación de pydantic (campos obligatorios ausentes): FastAPI responde 422.
        assert r.status_code == 422


class TestRegisterWithoutSmtp:
    def test_happy_path_creates_user_directly_as_jugador(self, client, db, monkeypatch):
        # Nos aseguramos de que el entorno de shell no tenga SMTP configurado
        # para este test (is_smtp_configured() debe dar False).
        monkeypatch.delenv("SMTP_HOST", raising=False)
        monkeypatch.delenv("SMTP_USER", raising=False)
        monkeypatch.delenv("SMTP_FROM", raising=False)

        payload = _register_payload()
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert not body.get("verify_email")

        from dockerlabs.models import User
        db.session.rollback()
        user = User.query.filter_by(username=payload["username"]).first()
        assert user is not None
        assert user.role == "jugador"

        # Puede iniciar sesión inmediatamente.
        r2 = client.post("/api/auth/login", json={"username": payload["username"], "password": payload["password"]})
        assert r2.status_code == 200

    def test_username_too_long_rejected(self, client, monkeypatch):
        monkeypatch.delenv("SMTP_FROM", raising=False)
        payload = _register_payload(username="a" * 21)
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 400
        assert "20 caracteres" in r.json()["message"]

    def test_email_too_long_rejected(self, client, monkeypatch):
        monkeypatch.delenv("SMTP_FROM", raising=False)
        payload = _register_payload(email=("a" * 30) + "@example.test")
        assert len(payload["email"]) > 35
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 400
        assert "35 caracteres" in r.json()["message"]

    def test_passwords_dont_match_rejected(self, client, monkeypatch):
        monkeypatch.delenv("SMTP_FROM", raising=False)
        payload = _register_payload(password2="Otra1234!")
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 400
        assert "no coinciden" in r.json()["message"]

    def test_weak_password_rejected(self, client, monkeypatch):
        monkeypatch.delenv("SMTP_FROM", raising=False)
        payload = _register_payload(password="alllowercase", password2="alllowercase")
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 400
        assert "mayúscula" in r.json()["message"]

    def test_terms_not_accepted_rejected(self, client, monkeypatch):
        monkeypatch.delenv("SMTP_FROM", raising=False)
        payload = _register_payload(terms=False)
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 400
        assert "Términos" in r.json()["message"]

    @pytest.mark.parametrize("reserved", ["admin", "root", "system", "default", "balulero", "default-profile", "logo", "pingu", "ADMIN"])
    def test_reserved_username_rejected(self, client, monkeypatch, reserved):
        monkeypatch.delenv("SMTP_FROM", raising=False)
        payload = _register_payload(username=reserved)
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 400
        assert "reservado" in r.json()["message"]

    @pytest.mark.parametrize("bad_username", ["ab/cd", "ab\\cd", "ab.cd", "a..b"])
    def test_username_with_special_path_chars_rejected(self, client, monkeypatch, bad_username):
        monkeypatch.delenv("SMTP_FROM", raising=False)
        payload = _register_payload(username=bad_username)
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 400
        assert "caracteres especiales" in r.json()["message"]

    def test_username_with_regex_invalid_chars_rejected(self, client, monkeypatch):
        monkeypatch.delenv("SMTP_FROM", raising=False)
        payload = _register_payload(username="user name")
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 400
        assert "letras, números" in r.json()["message"]

    def test_duplicate_username_rejected(self, client, db, monkeypatch):
        monkeypatch.delenv("SMTP_FROM", raising=False)
        # username explícito y corto: el default de make_user() (vía Faker)
        # puede superar los 20 caracteres que exige /api/auth/register ANTES
        # de comprobar duplicados, lo que haría caer en el mensaje de
        # longitud en vez del de "ya están registrados".
        existing = make_user(db, username=_uname("dup"))
        payload = _register_payload(username=existing.username)
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 400
        assert "ya están registrados" in r.json()["message"]

    def test_duplicate_email_rejected(self, client, db, monkeypatch):
        monkeypatch.delenv("SMTP_FROM", raising=False)
        existing = make_user(db)
        payload = _register_payload(email=existing.email)
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 400
        assert "ya están registrados" in r.json()["message"]

    def test_username_squatting_machine_autor_rejected(self, client, db, monkeypatch):
        monkeypatch.delenv("SMTP_FROM", raising=False)
        squatted = _uname("sq")
        make_machine(db, autor=squatted)
        payload = _register_payload(username=squatted)
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 400
        assert "autor de máquina" in r.json()["message"]

    def test_username_squatting_writeup_autor_rejected(self, client, db, monkeypatch):
        monkeypatch.delenv("SMTP_FROM", raising=False)
        squatted = _uname("sq")
        machine = make_machine(db)
        make_writeup(db, maquina=machine.nombre, autor=squatted)
        payload = _register_payload(username=squatted)
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 400
        assert "autor de máquina" in r.json()["message"]


class TestRegisterWithSmtp:
    def test_happy_path_creates_pending_token_and_sends_email(self, client, db, mock_smtp):
        payload = _register_payload()
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["verify_email"] is True

        # No se crea el User todavía.
        from dockerlabs.models import EmailVerificationToken, User
        db.session.rollback()
        assert User.query.filter_by(username=payload["username"]).first() is None
        pending = EmailVerificationToken.query.filter_by(username=payload["username"]).first()
        assert pending is not None
        assert pending.email == payload["email"]

        assert len(mock_smtp) == 1
        assert mock_smtp[0]["to"] == payload["email"]
        assert "Verifica tu cuenta" in mock_smtp[0]["subject"]
        assert pending.token in mock_smtp[0]["html"]

        # Completar el registro a través del enlace de verificación.
        r2 = client.get(f"/verify-email?token={pending.token}")
        assert r2.status_code == 200

        db.session.rollback()
        user = User.query.filter_by(username=payload["username"]).first()
        assert user is not None
        assert user.role == "jugador"
        assert EmailVerificationToken.query.filter_by(username=payload["username"]).first() is None

        r3 = client.post("/api/auth/login", json={"username": payload["username"], "password": payload["password"]})
        assert r3.status_code == 200


class TestForgotPassword:
    def test_without_smtp_returns_503(self, client, monkeypatch):
        monkeypatch.delenv("SMTP_FROM", raising=False)
        monkeypatch.delenv("SMTP_USER", raising=False)
        r = client.post("/api/auth/forgot-password", json={"email": "whoever@example.test"})
        assert r.status_code == 503

    def test_generic_message_same_for_real_and_fake_email(self, client, db, mock_smtp):
        user = make_user(db)

        r_real = client.post("/api/auth/forgot-password", json={"email": user.email})
        r_fake = client.post("/api/auth/forgot-password", json={"email": "doesnotexist@example.test"})

        assert r_real.status_code == r_fake.status_code == 200
        assert r_real.json() == r_fake.json()

    def test_requesting_twice_leaves_only_one_active_token(self, client, db, mock_smtp):
        from dockerlabs.models import PasswordResetToken

        user = make_user(db)
        client.post("/api/auth/forgot-password", json={"email": user.email})
        client.post("/api/auth/forgot-password", json={"email": user.email})

        db.session.rollback()
        tokens = PasswordResetToken.query.filter_by(user_id=user.id, used=False).all()
        assert len(tokens) == 1


class TestResetPassword:
    def test_valid_token_resets_password_and_bumps_session_version(self, client, db):
        user = make_user(db, password="OldPassw0rd!")
        original_version = user.session_version
        token_row = make_password_reset_token(db, user_id=user.id)

        r = client.post("/api/auth/reset-password", json={
            "token": token_row.token, "password": "NewPassw0rd!", "password2": "NewPassw0rd!",
        })
        assert r.status_code == 200
        assert r.json()["success"] is True

        db.session.rollback()
        from dockerlabs.models import PasswordResetToken, User
        refreshed = User.query.get(user.id)
        assert refreshed.session_version == original_version + 1

        used_token = PasswordResetToken.query.filter_by(token=token_row.token).first()
        assert used_token.used is True

        # Nueva contraseña funciona.
        r_login = client.post("/api/auth/login", json={"username": user.username, "password": "NewPassw0rd!"})
        assert r_login.status_code == 200

        # Reutilizar el mismo token ya usado se rechaza.
        r_reuse = client.post("/api/auth/reset-password", json={
            "token": token_row.token, "password": "OtraNueva1!", "password2": "OtraNueva1!",
        })
        assert r_reuse.status_code == 400

    def test_expired_token_rejected(self, client, db):
        user = make_user(db)
        token_row = make_password_reset_token(db, user_id=user.id, expires_at=datetime.utcnow() - timedelta(hours=1))

        r = client.post("/api/auth/reset-password", json={
            "token": token_row.token, "password": "NewPassw0rd!", "password2": "NewPassw0rd!",
        })
        assert r.status_code == 400
        assert "expirado" in r.json()["message"]

    def test_already_used_token_rejected(self, client, db):
        user = make_user(db)
        token_row = make_password_reset_token(db, user_id=user.id, used=True)

        r = client.post("/api/auth/reset-password", json={
            "token": token_row.token, "password": "NewPassw0rd!", "password2": "NewPassw0rd!",
        })
        assert r.status_code == 400
        assert "invalido" in r.json()["message"] or "inválido" in r.json()["message"]

    def test_mismatched_passwords_rejected(self, client, db):
        user = make_user(db)
        token_row = make_password_reset_token(db, user_id=user.id)
        r = client.post("/api/auth/reset-password", json={
            "token": token_row.token, "password": "NewPassw0rd!", "password2": "Different1!",
        })
        assert r.status_code == 400
