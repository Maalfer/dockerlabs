"""Fechas en UTC sin zona horaria, como se guardan en la BD."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Instante actual en UTC, naive. Úsalo en vez de datetime.utcnow()/now()."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
