"""Repara las colisiones de `cert_id` y hace la columna única.

`cert_id` solo tiene 24 bits de hash: con unos miles de certificados las
colisiones son probables, y `/api/certificado/pdf/<ID>` resolvía con `.first()`,
sirviendo el diploma de otra persona. Se conserva el ID del certificado más
antiguo (el que pudo publicarse) y se reasigna el segundo.

    venv/bin/python fix_cert_id_collisions.py [--dry-run]
"""
import sys

sys.path.insert(0, '/var/www/dockerlabs')

from dotenv import load_dotenv
load_dotenv('/var/www/dockerlabs/.env')

from sqlalchemy import func, inspect, text

from dockerlabs.database import _request_scope_id, engine
_request_scope_id.set(object())

from dockerlabs.extensions import db
from dockerlabs.models import Certificate, User
from dockerlabs.routes.certificados import ensure_certificate

DRY = '--dry-run' in sys.argv


def colisiones():
    dupes = (
        db.session.query(Certificate.cert_id)
        .group_by(Certificate.cert_id)
        .having(func.count(Certificate.id) > 1)
        .all()
    )
    return [c for (c,) in dupes]


def main():
    ids = colisiones()
    print(f"cert_id colisionados: {len(ids)}")

    for cert_id in ids:
        filas = (
            Certificate.query.filter_by(cert_id=cert_id)
            .order_by(Certificate.id.asc()).all()
        )
        conserva, resto = filas[0], filas[1:]
        print(f"\n{cert_id}:")
        print(f"  conserva  id={conserva.id}  {conserva.username}/{conserva.machine_name}")
        for cert in resto:
            print(f"  reasigna  id={cert.id}  {cert.username}/{cert.machine_name}", end='')
            if DRY:
                print("  (dry-run)")
                continue
            user = User.query.get(cert.user_id)
            if not user:
                print("  ! sin usuario, se borra")
                db.session.delete(cert)
                db.session.commit()
                continue
            nuevo = ensure_certificate(user, cert.machine_name, force=True)
            print(f"  ->  {nuevo.cert_id}")

    if DRY:
        return

    restantes = colisiones()
    if restantes:
        print(f"\n! quedan colisiones: {restantes}. No se crea el índice único.")
        return

    idx = {i['name'] for i in inspect(engine).get_indexes('certificados')}
    with engine.begin() as conn:
        if 'idx_certificados_cert_id' in idx:
            conn.execute(text('DROP INDEX idx_certificados_cert_id ON certificados'))
            print("\n· índice no único eliminado")
        if 'ix_certificados_cert_id' not in idx:
            conn.execute(text('CREATE UNIQUE INDEX ix_certificados_cert_id ON certificados (cert_id)'))
            print("✓ índice ÚNICO creado sobre cert_id")

    print(f"\ntotal certificados: {Certificate.query.count()}")


if __name__ == '__main__':
    main()
