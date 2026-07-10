"""Migración: columna users.slug + tabla certificados.

Idempotente: se puede volver a ejecutar sin efectos.
    venv/bin/python migrate_slugs_certs.py
"""
import sys

sys.path.insert(0, '/var/www/dockerlabs')

from dotenv import load_dotenv
load_dotenv('/var/www/dockerlabs/.env')

from sqlalchemy import inspect, text

from dockerlabs.database import engine, init_db
from dockerlabs.slugs import slugify, unique_slug


def add_slug_column(conn):
    cols = {c['name'] for c in inspect(engine).get_columns('users')}
    if 'slug' in cols:
        print('· users.slug ya existe')
        return
    conn.execute(text('ALTER TABLE users ADD COLUMN slug VARCHAR(64) NULL'))
    conn.execute(text('CREATE UNIQUE INDEX ix_users_slug ON users (slug)'))
    print('✓ users.slug creada + índice único')


def backfill(conn):
    rows = conn.execute(
        text("SELECT id, username FROM users WHERE slug IS NULL OR slug = '' ORDER BY id")
    ).fetchall()
    if not rows:
        print('· sin usuarios pendientes de slug')
        return
    for uid, username in rows:
        slug = unique_slug(conn, slugify(username), exclude_id=uid)
        conn.execute(
            text('UPDATE users SET slug = :slug WHERE id = :id'),
            {'slug': slug, 'id': uid},
        )
        print(f'  {uid:>5}  {username!r} → /u/{slug}')
    print(f'✓ {len(rows)} slug(s) asignados')


if __name__ == '__main__':
    # create_all crea la tabla `certificados` (y solo esa, el resto ya existe).
    init_db()
    print('✓ init_db() ejecutado (tabla certificados)')

    with engine.begin() as conn:
        add_slug_column(conn)
        backfill(conn)

    with engine.connect() as conn:
        total = conn.execute(text('SELECT COUNT(*) FROM users')).scalar()
        con_slug = conn.execute(text('SELECT COUNT(*) FROM users WHERE slug IS NOT NULL')).scalar()
        print(f'\nResumen: {con_slug}/{total} usuarios con slug')
