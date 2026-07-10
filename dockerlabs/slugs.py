"""Slugs públicos de perfil de usuario (rutas `/u/<slug>`).

El slug se deriva del nombre de usuario y se mantiene sincronizado con él
mediante eventos de SQLAlchemy, de modo que cualquier punto del código que
cree o renombre un `User` obtiene un slug válido sin tener que acordarse.
"""

import re
import unicodedata

from sqlalchemy import event, inspect, text

MAX_SLUG_LEN = 60

_NON_SLUG_RE = re.compile(r'[^a-z0-9]+')

# Slugs que colisionarían con recursos servidos bajo el mismo espacio de nombres
# o que se reservan por coherencia con los nombres de usuario prohibidos.
RESERVED_SLUGS = frozenset({
    'admin', 'root', 'system', 'default', 'default-profile',
    'api', 'static', 'img', 'u', 'null', 'undefined',
})


def slugify(value: str) -> str:
    """Convierte un texto libre en un slug ASCII seguro para URLs."""
    normalized = unicodedata.normalize('NFKD', value or '')
    ascii_only = normalized.encode('ascii', 'ignore').decode('ascii').lower()
    return _NON_SLUG_RE.sub('-', ascii_only).strip('-')[:MAX_SLUG_LEN].strip('-')


def _slug_taken(connection, slug: str, exclude_id) -> bool:
    rows = connection.execute(
        text('SELECT id FROM users WHERE slug = :slug'), {'slug': slug}
    ).fetchall()
    return any(row[0] != exclude_id for row in rows)


def unique_slug(connection, base: str, exclude_id=None) -> str:
    """Devuelve `base` o `base-N`, el primero que no esté ocupado."""
    if not base or base in RESERVED_SLUGS:
        base = f'user-{base}' if base else 'user'

    candidate = base
    counter = 2
    while _slug_taken(connection, candidate, exclude_id):
        suffix = f'-{counter}'
        candidate = base[:MAX_SLUG_LEN - len(suffix)] + suffix
        counter += 1
    return candidate


def register_slug_events(user_model) -> None:
    """Asigna el slug al insertar y lo regenera al cambiar el nombre de usuario.

    Las consultas se hacen sobre la `connection` del flush en curso y no sobre
    `db.session`, para no disparar un autoflush reentrante dentro del evento.
    """

    @event.listens_for(user_model, 'before_insert')
    def _assign_slug(mapper, connection, target):
        if not target.slug:
            target.slug = unique_slug(connection, slugify(target.username))

    @event.listens_for(user_model, 'before_update')
    def _resync_slug(mapper, connection, target):
        renamed = inspect(target).attrs.username.history.has_changes()
        if renamed or not target.slug:
            target.slug = unique_slug(
                connection, slugify(target.username), exclude_id=target.id
            )
