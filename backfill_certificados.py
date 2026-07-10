"""Emite por adelantado el PDF de todo certificado que ya corresponda.

Un certificado corresponde en cuanto hay un writeup publicado de una máquina
por un usuario registrado. Idempotente: los diplomas ya archivados se saltan.

    venv/bin/python backfill_certificados.py            # emite los que falten
    venv/bin/python backfill_certificados.py --force    # re-renderiza todos
    venv/bin/python backfill_certificados.py --dry-run  # solo cuenta
"""
import sys
import time

sys.path.insert(0, '/var/www/dockerlabs')

from dotenv import load_dotenv
load_dotenv('/var/www/dockerlabs/.env')

from sqlalchemy import func

from dockerlabs.database import db_session, _request_scope_id
_request_scope_id.set(object())

from dockerlabs.extensions import db
from dockerlabs.models import Certificate, User, Writeup
from dockerlabs.routes.certificados import (
    _remove_file, author_matches_user, ensure_certificate,
)

FORCE = '--force' in sys.argv
DRY = '--dry-run' in sys.argv


def main():
    pares = (
        db.session.query(Writeup.autor, Writeup.maquina)
        .distinct()
        .all()
    )

    # Mapa usuario-por-nombre en memoria: evita una consulta por writeup. La
    # pertenencia la decide author_matches_user(), la misma regla que aplica la
    # aplicación en caliente, para que script y runtime no puedan divergir.
    todos = User.query.all()
    por_minusculas = {}
    for u in todos:
        por_minusculas.setdefault(u.username.lower(), []).append(u)

    pendientes = []
    huerfanos = set()
    ambiguos = set()
    for autor, maquina in pares:
        candidatos = por_minusculas.get((autor or '').lower(), [])
        elegidos = [u for u in candidatos if author_matches_user(autor, u)]
        if len(elegidos) == 1:
            pendientes.append((elegidos[0], maquina))
        elif candidatos:
            ambiguos.add(autor)
        else:
            huerfanos.add(autor)

    print(f"pares (autor, máquina):   {len(pares)}")
    print(f"con usuario registrado:   {len(pendientes)}")
    print(f"autores sin cuenta:       {len(huerfanos)} (sin diploma: no hay a quién asignarlo)")
    if ambiguos:
        print(f"autores ambiguos:         {len(ambiguos)} {sorted(ambiguos)} (varias cuentas difieren solo en mayúsculas)")
    print(f"ya emitidos previamente:  {Certificate.query.count()}")
    if DRY:
        return

    print(f"\nEmitiendo{' (force)' if FORCE else ''}…")
    t0 = time.time()
    emitidos = fallidos = 0
    for i, (user, maquina) in enumerate(pendientes, 1):
        try:
            if ensure_certificate(user, maquina, force=FORCE):
                emitidos += 1
        except Exception as e:
            db.session.rollback()
            fallidos += 1
            print(f"  ! {user.username} / {maquina}: {type(e).__name__}: {e}")

        if i % 250 == 0 or i == len(pendientes):
            dt = time.time() - t0
            print(f"  {i}/{len(pendientes)}  ({dt:.0f}s, {i/max(dt,0.001):.0f}/s)")

    # Retirar filas que ya no corresponden a nadie: writeups borrados, o
    # atribuciones de una pasada anterior con otra regla de pertenencia.
    esperados = set()
    for user, maquina in pendientes:
        cert = Certificate.query.filter(
            Certificate.user_id == user.id,
            func.lower(Certificate.machine_name) == maquina.lower(),
        ).first()
        if cert:
            esperados.add(cert.id)

    retirados = 0
    for cert in Certificate.query.all():
        if cert.id not in esperados:
            print(f"  - retirado {cert.cert_id} {cert.username}/{cert.machine_name}")
            _remove_file(cert.pdf_path)
            db.session.delete(cert)
            retirados += 1
    if retirados:
        db.session.commit()

    print(f"\n✓ {emitidos} certificados en disco, {fallidos} fallidos, {retirados} retirados")
    print(f"  total en BD: {Certificate.query.count()}")


if __name__ == '__main__':
    main()
