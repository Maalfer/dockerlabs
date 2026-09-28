"""Generación y verificación de tokens de API de administrador.

Mismo esquema que gestion-maquinas.dockerlabs.es (pbkdf2_hmac con salt por
token): el token en claro solo se devuelve UNA vez, al crearlo; en BD solo
vive `token_hash` (nunca el token en claro). No es reversible.

El token no sustituye al modelo de sesión: cuando se envía por cabecera
(`Authorization: Bearer <token>` o `X-Admin-Token`), `get_session()` en
routers.py lo valida contra `ApiToken` y, si es válido, construye una
sesión equivalente a la de un admin logueado por cookie. Así todas las
rutas que ya comprueban `session.get('role')` (directamente o vía
`require_auth_and_role`) quedan cubiertas sin tocarlas una por una.
"""
import hashlib
import hmac
import os
import secrets

PBKDF2_ITERATIONS = 390_000
TOKEN_PREFIX = "dlab_"


def generate_api_token() -> str:
    """Token aleatorio de alta entropía, listo para mostrar al admin."""
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_api_token(token: str) -> str:
    """Hash con salt aleatorio; formato 'pbkdf2$iteraciones$salt_hex$hash_hex'."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", token.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_api_token(stored_hash: str, token: str) -> bool:
    """Compara `token` contra `stored_hash` en tiempo constante."""
    try:
        method, iterations, salt_hex, hash_hex = stored_hash.split("$")
    except (ValueError, AttributeError):
        return False
    if method != "pbkdf2":
        return False
    try:
        salt = bytes.fromhex(salt_hex)
        iterations = int(iterations)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", token.encode(), salt, iterations)
    return hmac.compare_digest(digest.hex(), hash_hex)


def token_display_prefix(token: str) -> str:
    """Fragmento no sensible del token para mostrarlo en la lista (p.ej.
    'dlab_ab12cd34…'), suficiente para reconocerlo sin poder reconstruirlo."""
    return token[:12]
