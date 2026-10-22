"""
Factories para crear filas de BD con defaults sensatos en los tests.

Todas devuelven el objeto ya commiteado. Usan Faker para generar
username/email/nombre de máquina únicos y evitar colisiones entre tests (las
columnas `username`, `email`, `nombre` de máquina, etc. son `unique=True`).

No se importa nada de `dockerlabs.*` a nivel de módulo por el mismo motivo que
en `conftest.py`: `DATABASE_URL` todavía no está fijada cuando pytest
recolecta este fichero.
"""
from __future__ import annotations

from faker import Faker

_faker = Faker()


def make_user(db, *, role="jugador", password="Str0ngPassw0rd!", **overrides):
    from dockerlabs.models import User
    from werkzeug.security import generate_password_hash

    defaults = {
        "username": overrides.pop("username", f"user_{_faker.unique.user_name()}"[:32]),
        "email": overrides.pop("email", _faker.unique.email()),
        "password_hash": generate_password_hash(password),
        "role": role,
    }
    defaults.update(overrides)
    user = User(**defaults)
    db.session.add(user)
    db.session.commit()
    return user


def make_machine(db, *, origen="docker", **overrides):
    from dockerlabs.models import Machine

    nombre = overrides.pop("nombre", f"Machine{_faker.unique.random_int(min=1, max=999999)}")
    defaults = {
        "nombre": nombre,
        "dificultad": "Fácil",
        "clase": "facil",
        "color": "#8bc34a",
        "autor": "AutorTest",
        "enlace_autor": "",
        "fecha": "01/01/2026",
        "imagen": "dockerlabs/images/logos/logo.png",
        "descripcion": "Descripción de prueba",
        "link_descarga": "https://example.test/machine.zip",
        "guest_access": False,
        "origen": origen,
        "descargas": 0,
    }
    defaults.update(overrides)
    machine = Machine(**defaults)
    db.session.add(machine)
    db.session.commit()
    return machine


def make_writeup(db, *, maquina, autor, **overrides):
    from dockerlabs.models import Writeup

    defaults = {
        "maquina": maquina,
        "autor": autor,
        "url": overrides.pop("url", f"https://blog.test/{_faker.unique.slug()}"),
        "tipo": "texto",
    }
    defaults.update(overrides)
    writeup = Writeup(**defaults)
    db.session.add(writeup)
    db.session.commit()
    return writeup


def make_pending_writeup(db, *, maquina, autor, **overrides):
    from dockerlabs.models import PendingWriteup

    defaults = {
        "maquina": maquina,
        "autor": autor,
        "url": overrides.pop("url", f"https://blog.test/{_faker.unique.slug()}"),
        "tipo": "texto",
    }
    defaults.update(overrides)
    writeup = PendingWriteup(**defaults)
    db.session.add(writeup)
    db.session.commit()
    return writeup


def make_bunker_token(db, *, nombre="Invitado", **overrides):
    from bunkerlabs.models import BunkerAccessToken

    defaults = {
        "nombre": nombre,
        "token": overrides.pop("token", f"pin-{_faker.unique.password(length=12, special_chars=False)}"),
        "activo": 1,
    }
    defaults.update(overrides)
    token = BunkerAccessToken(**defaults)
    db.session.add(token)
    db.session.commit()
    return token


def make_pending_machine_submission(db, **overrides):
    from dockerlabs.models import PendingMachineSubmission

    defaults = {
        "nombre": overrides.pop("nombre", f"Submission{_faker.unique.random_int(min=1, max=999999)}"),
        "link_maquina": "https://example.test/machine.zip",
        "dificultad": "Fácil",
        "discord_user": "autor#0001",
        "estado": "pendiente",
    }
    defaults.update(overrides)
    submission = PendingMachineSubmission(**defaults)
    db.session.add(submission)
    db.session.commit()
    return submission


def make_rating(db, *, usuario_id, maquina_nombre, **overrides):
    from dockerlabs.models import Rating

    defaults = {
        "usuario_id": usuario_id,
        "maquina_nombre": maquina_nombre,
        "dificultad_score": 3,
        "aprendizaje_score": 3,
        "recomendaria_score": 3,
        "diversion_score": 3,
    }
    defaults.update(overrides)
    rating = Rating(**defaults)
    db.session.add(rating)
    db.session.commit()
    return rating


def make_completed_machine(db, *, user_id, machine_name, **overrides):
    from dockerlabs.models import CompletedMachine

    defaults = {"user_id": user_id, "machine_name": machine_name}
    defaults.update(overrides)
    row = CompletedMachine(**defaults)
    db.session.add(row)
    db.session.commit()
    return row


def make_notification(db, *, sender_id, receiver_id=None, **overrides):
    from dockerlabs.models import Notification

    defaults = {
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "title": overrides.pop("title", "Título de prueba"),
        "content": "Contenido de prueba",
    }
    defaults.update(overrides)
    notif = Notification(**defaults)
    db.session.add(notif)
    db.session.commit()
    return notif


def make_notification_reaction(db, *, notification_id, user_id, emoji="👍", **overrides):
    from dockerlabs.models import NotificationReaction

    defaults = {"notification_id": notification_id, "user_id": user_id, "emoji": emoji}
    defaults.update(overrides)
    row = NotificationReaction(**defaults)
    db.session.add(row)
    db.session.commit()
    return row


def make_notification_read(db, *, notification_id, user_id, **overrides):
    from dockerlabs.models import NotificationRead

    row = NotificationRead(notification_id=notification_id, user_id=user_id, **overrides)
    db.session.add(row)
    db.session.commit()
    return row


def make_certificate(db, *, user, machine_name, **overrides):
    """No usa ensure_certificate() a propósito: crea la fila directamente
    para tests que solo necesitan que el certificado YA exista (p.ej. probar
    los endpoints públicos de verificar/pdf/imagen), sin depender de que haya
    un writeup real ni renderizar un PDF/WebP de verdad."""
    from dockerlabs.models import Certificate

    defaults = {
        "cert_id": overrides.pop("cert_id", f"DL-{_faker.unique.hexify(text='^^^^^^', upper=True)}"),
        "user_id": user.id,
        "username": user.username,
        "machine_name": machine_name,
        "pdf_path": overrides.pop("pdf_path", f"uploads/certificados/user_{user.id}/test-{machine_name}.pdf"),
        "image_path": overrides.pop("image_path", f"uploads/certificados/user_{user.id}/test-{machine_name}.webp"),
    }
    defaults.update(overrides)
    cert = Certificate(**defaults)
    db.session.add(cert)
    db.session.commit()
    return cert


def make_category(db, *, machine_id, origen, categoria, **overrides):
    from dockerlabs.models import Category

    row = Category(machine_id=machine_id, origen=origen, categoria=categoria, **overrides)
    db.session.add(row)
    db.session.commit()
    return row


def make_email_verification_token(db, *, username, email, **overrides):
    from datetime import datetime, timedelta

    from dockerlabs.models import EmailVerificationToken
    from werkzeug.security import generate_password_hash

    defaults = {
        "token": overrides.pop("token", _faker.unique.uuid4()),
        "username": username,
        "email": email,
        "password_hash": generate_password_hash("Str0ngPassw0rd!"),
        "expires_at": datetime.utcnow() + timedelta(hours=24),
    }
    defaults.update(overrides)
    row = EmailVerificationToken(**defaults)
    db.session.add(row)
    db.session.commit()
    return row


def make_password_reset_token(db, *, user_id, **overrides):
    from datetime import datetime, timedelta

    from dockerlabs.models import PasswordResetToken

    defaults = {
        "token": overrides.pop("token", _faker.unique.uuid4()),
        "user_id": user_id,
        "expires_at": datetime.utcnow() + timedelta(hours=1),
        "used": False,
    }
    defaults.update(overrides)
    row = PasswordResetToken(**defaults)
    db.session.add(row)
    db.session.commit()
    return row


def make_email_change_token(db, *, user_id, new_email, **overrides):
    from datetime import datetime, timedelta

    from dockerlabs.models import EmailChangeToken

    defaults = {
        "token": overrides.pop("token", _faker.unique.uuid4()),
        "user_id": user_id,
        "new_email": new_email,
        "expires_at": datetime.utcnow() + timedelta(hours=1),
        "used": False,
    }
    defaults.update(overrides)
    row = EmailChangeToken(**defaults)
    db.session.add(row)
    db.session.commit()
    return row
