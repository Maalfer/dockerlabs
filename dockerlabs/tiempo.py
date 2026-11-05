"""Fechas en UTC para toda la app.

La BD guarda los instantes como DATETIME sin zona horaria, en UTC. Hasta ahora
se obtenían con `datetime.utcnow()`, obsoleto desde Python 3.12. `utcnow()`
devuelve exactamente lo mismo (UTC, naive), así que las comparaciones con lo
que ya hay guardado siguen funcionando igual. Úsalo siempre en lugar de
`datetime.utcnow()` o `datetime.now()`.
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Instante actual en UTC, sin zona horaria (como se guarda en la BD)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
