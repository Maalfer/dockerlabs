"""API pública de perfil de usuario: `GET /u/<slug>` → JSON.

Devuelve, sin autenticación, el perfil completo de un usuario: máquinas
resueltas, máquinas creadas, writeups publicados y certificados (con el enlace
al PDF archivado en el momento en que el usuario lo generó).
"""

import os

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import func

from dockerlabs.models import (
    Certificate, CompletedMachine, CreatorRanking, Machine, User,
    Writeup, WriteupRanking,
)
from dockerlabs.routes.certificados import certificate_id

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

MAX_ITEMS = 1000

# BunkerLabs es de acceso restringido: sus máquinas no se exponen aquí.
PUBLIC_ORIGINS = ('docker', 'empezar')


def _iso(dt):
    return dt.isoformat() + 'Z' if dt else None


def register_public_profile_routes(pages_router, db):

    def _ranking_position(model, points_column, username):
        row = model.query.filter(
            func.lower(model.nombre) == username.lower()
        ).first()
        if not row:
            return None, 0

        value = getattr(row, points_column)
        better = (
            db.session.query(func.count(model.id))
            .filter(getattr(model, points_column) > value)
            .scalar()
        )
        return (better or 0) + 1, value

    @pages_router.get("/u/{slug}", include_in_schema=True, tags=["API Pública"])
    def api_public_profile(slug: str, request: Request):
        raw = (slug or '').strip().lower()
        if not raw or len(raw) > 64:
            return JSONResponse(status_code=404, content={"error": "Perfil no encontrado", "slug": slug})

        user = User.query.filter(func.lower(User.slug) == raw).first()
        if not user:
            # Compatibilidad: aceptar también el nombre de usuario literal.
            user = User.query.filter(func.lower(User.username) == raw).first()
        if not user:
            return JSONResponse(status_code=404, content={"error": "Perfil no encontrado", "slug": slug})

        username = user.username

        # --- Máquinas resueltas -------------------------------------------
        completed_rows = (
            db.session.query(
                CompletedMachine.machine_name,
                CompletedMachine.completed_at,
                Machine.id,
                Machine.dificultad,
                Machine.color,
                Machine.origen,
            )
            .outerjoin(Machine, CompletedMachine.machine_name == Machine.nombre)
            .filter(CompletedMachine.user_id == user.id)
            .order_by(CompletedMachine.completed_at.desc())
            .limit(MAX_ITEMS)
            .all()
        )
        maquinas_hechas = [
            {
                "nombre":       nombre,
                "dificultad":   dificultad or "",
                "color":        color or "#64748b",
                "origen":       origen or "docker",
                "imagen_url":   f"/img/maquina/{mid}" if mid else None,
                "completada_el": _iso(completed_at),
            }
            for nombre, completed_at, mid, dificultad, color, origen in completed_rows
        ]

        # --- Máquinas creadas ---------------------------------------------
        created = (
            Machine.query
            .filter(func.lower(Machine.autor) == username.lower())
            .filter(Machine.origen.in_(PUBLIC_ORIGINS))
            .order_by(Machine.id.desc())
            .limit(MAX_ITEMS)
            .all()
        )
        maquinas_creadas = [
            {
                "id":          m.id,
                "nombre":      m.nombre,
                "dificultad":  m.dificultad,
                "clase":       m.clase,
                "color":       m.color,
                "origen":      m.origen,
                "fecha":       m.fecha,
                "descripcion": m.descripcion,
                "imagen_url":  f"/img/maquina/{m.id}",
                "descarga":    m.link_descarga,
            }
            for m in created
        ]

        # --- Writeups publicados ------------------------------------------
        writeups = (
            Writeup.query
            .filter(func.lower(Writeup.autor) == username.lower())
            .order_by(Writeup.created_at.desc())
            .limit(MAX_ITEMS)
            .all()
        )
        writeups_json = [
            {
                "maquina":      w.maquina,
                "url":          w.url,
                "tipo":         w.tipo,
                "publicado_el": _iso(w.created_at),
            }
            for w in writeups
        ]

        # --- Certificados ---------------------------------------------------
        # Cada writeup publicado da derecho a un certificado; `generado` indica
        # si el usuario ya lo emitió (y por tanto existe el PDF archivado).
        emitidos = {
            c.machine_name: c
            for c in Certificate.query.filter_by(user_id=user.id).all()
        }

        certificados = []
        vistos = set()
        for w in writeups:
            if w.maquina in vistos:
                continue
            vistos.add(w.maquina)

            machine = Machine.query.filter(
                func.lower(Machine.nombre) == func.lower(w.maquina)
            ).first()
            cid  = certificate_id(username, w.maquina)
            cert = emitidos.get(w.maquina)

            certificados.append({
                "cert_id":     cid,
                "maquina":     machine.nombre if machine else w.maquina,
                "dificultad":  machine.dificultad if machine else "",
                "generado":    bool(cert),
                "emitido_el":  _iso(cert.created_at) if cert else None,
                "pdf_url":     f"/api/certificado/pdf/{cid}" if cert else None,
                "verify_url":  f"/api/certificado/verificar/{cid}",
            })

        pos_writeups, puntos = _ranking_position(WriteupRanking, 'puntos', username)
        pos_creadores, _     = _ranking_position(CreatorRanking, 'maquinas', username)

        return JSONResponse(content={
            "slug":     user.slug or raw,
            "username": username,
            "perfil": {
                "id":            user.id,
                "rol":           user.role,
                "biografia":     user.biography or "",
                "miembro_desde": _iso(user.created_at),
                "avatar_url":    f"/img/perfil/{user.id}",
                "perfil_url":    f"/u/{user.slug or raw}",
                "redes": {
                    "linkedin": user.linkedin_url or None,
                    "github":   user.github_url or None,
                    "youtube":  user.youtube_url or None,
                },
            },
            "estadisticas": {
                "maquinas_hechas":          len(maquinas_hechas),
                "maquinas_creadas":         len(maquinas_creadas),
                "writeups_publicados":      len(writeups_json),
                "certificados_disponibles": len(certificados),
                "certificados_generados":   sum(1 for c in certificados if c["generado"]),
                "puntos_writeups":          puntos,
                "ranking_writeups":         pos_writeups,
                "ranking_creadores":        pos_creadores,
            },
            "maquinas_hechas":  maquinas_hechas,
            "maquinas_creadas": maquinas_creadas,
            "writeups":         writeups_json,
            "certificados":     certificados,
        })
