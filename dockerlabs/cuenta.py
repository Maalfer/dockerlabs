"""Eliminación definitiva de una cuenta por su propio titular (art. 17 RGPD).

``db.session.delete(user)`` por sí solo deja huérfanos los datos que se
enlazan por *nombre* y no por clave ajena (rankings, writeups, autoría de
máquinas, valoraciones) y no borra los ficheros del disco. Esta función hace el
borrado completo en una única transacción y retira los ficheros después del
``commit``.

Criterio:
* Se BORRAN: cuenta, progreso, valoraciones, diplomas (BD y ficheros), foto de
  perfil, notificaciones, rankings y writeups propios.
* Se ANONIMIZAN (son contenido comunitario que no debe romperse): las máquinas
  de las que es autor y sus propuestas pendientes -> «Usuario eliminado».
"""
import logging
import os

from sqlalchemy import func

from dockerlabs.extensions import db

logger = logging.getLogger(__name__)

ANONIMO = "Usuario eliminado"


def _quitar_fichero(ruta_absoluta: str) -> None:
    try:
        os.remove(ruta_absoluta)
    except OSError:
        pass


def eliminar_cuenta(user, base_dir: str) -> dict:
    """Borra ``user`` y todo lo suyo. Devuelve datos para el aviso por correo."""
    from dockerlabs.models import (
        Certificate, CreatorRanking, EmailVerificationToken, Machine,
        PendingMachineSubmission, PendingWriteup, Rating, Writeup,
        WriteupAnalysisResult, WriteupRanking,
    )
    from dockerlabs.routes.certificados import abspath_for, author_matches_user

    uid, nombre, email = user.id, user.username, user.email
    minus = nombre.lower()
    ficheros = []

    # Foto de perfil (solo si cuelga de uploads/: nunca se borra fuera).
    if user.profile_image_path:
        raiz = os.path.realpath(os.path.join(base_dir, "uploads"))
        ruta = os.path.realpath(os.path.join(base_dir, user.profile_image_path))
        if ruta.startswith(raiz + os.sep):
            ficheros.append(ruta)

    # Diplomas: WebP archivado y, en filas antiguas, PDF legacy (las filas
    # caen en cascada).
    for cert in Certificate.query.filter_by(user_id=uid).all():
        for rel in (cert.pdf_path, cert.image_path):
            if rel:
                ficheros.append(abspath_for(rel))

    try:
        # Datos enlazados por nombre o id sin clave ajena.
        Rating.query.filter_by(usuario_id=uid).delete(synchronize_session=False)
        WriteupRanking.query.filter(func.lower(WriteupRanking.nombre) == minus).delete(synchronize_session=False)
        CreatorRanking.query.filter(func.lower(CreatorRanking.nombre) == minus).delete(synchronize_session=False)
        EmailVerificationToken.query.filter(
            (func.lower(EmailVerificationToken.email) == (email or "").lower())
            | (func.lower(EmailVerificationToken.username) == minus)
        ).delete(synchronize_session=False)

        # Writeups propios: se borran (enlazan a su web personal).
        for w in Writeup.query.filter(func.lower(Writeup.autor) == minus).all():
            if author_matches_user(w.autor, user):
                WriteupAnalysisResult.query.filter_by(writeup_id=w.id).delete(synchronize_session=False)
                db.session.delete(w)
        for w in PendingWriteup.query.filter(func.lower(PendingWriteup.autor) == minus).all():
            if author_matches_user(w.autor, user):
                db.session.delete(w)

        # Máquinas de su autoría: se conservan, sin su nombre.
        for m in Machine.query.filter(func.lower(Machine.autor) == minus).all():
            if author_matches_user(m.autor, user):
                m.autor = ANONIMO
                m.enlace_autor = ""
        for p in PendingMachineSubmission.query.filter(
                func.lower(PendingMachineSubmission.autor_solicitante) == minus).all():
            p.autor_solicitante = ANONIMO
            p.discord_user = ANONIMO

        db.session.delete(user)   # cascada: certificados, hechas, notificaciones, tokens...
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    for ruta in ficheros:
        _quitar_fichero(ruta)
    logger.info("Cuenta eliminada por su titular (user_id=%s)", uid)
    return {"email": email, "username": nombre}
