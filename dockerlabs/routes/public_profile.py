"""API pública de perfil de usuario: `GET /u/<slug>` → JSON.

Devuelve, sin autenticación, todo el progreso público de un usuario: las
máquinas que ha resuelto con su ficha completa, las que ha creado, sus writeups
y sus certificados (PDF e imagen ya archivados).

Las consultas van por lotes: cargar el catálogo de máquinas y las categorías de
una vez evita una consulta por cada máquina resuelta.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import func

from dockerlabs.models import (
    Category, Certificate, CompletedMachine, CreatorRanking, Machine, User,
    Writeup, WriteupRanking,
)
from dockerlabs.routes.certificados import certificate_id

MAX_ITEMS = 1000

# BunkerLabs es de acceso restringido: de sus máquinas solo se expone que
# fueron resueltas, nunca su descripción ni su enlace de descarga.
PUBLIC_ORIGINS = ('docker', 'empezar')

# El catálogo sobre el que se mide el porcentaje de progreso.
CATALOGO_ORIGEN = 'docker'

# `dificultad` está sin normalizar en la base ('Fácil' y 'Facil' conviven), pero
# `clase` sí lo está. Se agrupa por clase y se muestra la etiqueta canónica.
ETIQUETA_CLASE = {
    'muy-facil': 'Muy Fácil',
    'facil':     'Fácil',
    'medio':     'Medio',
    'dificil':   'Difícil',
}
ORDEN_CLASES = ('muy-facil', 'facil', 'medio', 'dificil')


def _iso(dt):
    return dt.isoformat() + 'Z' if dt else None


def register_public_profile_routes(pages_router, db):

    def _ranking_position(model, points_column, username):
        row = model.query.filter(func.lower(model.nombre) == username.lower()).first()
        if not row:
            return None, 0
        value = getattr(row, points_column)
        better = (
            db.session.query(func.count(model.id))
            .filter(getattr(model, points_column) > value)
            .scalar()
        )
        return (better or 0) + 1, value

    def _machine_json(m, categoria, *, completa=True):
        """Ficha de una máquina. `completa=False` para las de BunkerLabs."""
        base = {
            "id":         m.id,
            "nombre":     m.nombre,
            "dificultad": m.dificultad,
            "clase":      m.clase,
            "color":      m.color,
            "origen":     m.origen,
            "categoria":  categoria,
            "logo_url":   f"/img/maquina/{m.id}",
        }
        if not completa:
            return base
        base.update({
            "autor":        m.autor,
            "enlace_autor": m.enlace_autor,
            "fecha":        m.fecha,
            "descripcion":  m.descripcion,
            "descarga":     m.link_descarga,
        })
        return base

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
        ulower = username.lower()

        # --- Catálogo completo, una sola vez -------------------------------
        maquinas = Machine.query.all()
        por_nombre = {m.nombre.lower(): m for m in maquinas}

        categorias = {
            (c.machine_id, c.origen): c.categoria
            for c in Category.query.all()
        }

        def categoria_de(m):
            return categorias.get((m.id, m.origen))

        # --- Writeups y certificados del usuario ---------------------------
        writeups = (
            Writeup.query
            .filter(func.lower(Writeup.autor) == ulower)
            .order_by(Writeup.created_at.desc())
            .limit(MAX_ITEMS)
            .all()
        )
        writeup_por_maquina = {}
        for w in writeups:
            writeup_por_maquina.setdefault(w.maquina.lower(), w)

        certs = {
            c.machine_name.lower(): c
            for c in Certificate.query.filter_by(user_id=user.id).all()
        }

        def certificado_de(nombre_maquina):
            cert = certs.get(nombre_maquina.lower())
            if not cert:
                return None
            return {
                "cert_id":    cert.cert_id,
                "emitido_el": _iso(cert.created_at),
                "pdf_url":    f"/api/certificado/pdf/{cert.cert_id}",
                "imagen_url": f"/api/certificado/imagen/{cert.cert_id}",
                "verify_url": f"/api/certificado/verificar/{cert.cert_id}",
            }

        # --- Máquinas resueltas --------------------------------------------
        completadas = (
            CompletedMachine.query
            .filter(CompletedMachine.user_id == user.id)
            .order_by(CompletedMachine.completed_at.desc())
            .limit(MAX_ITEMS)
            .all()
        )

        maquinas_hechas = []
        for cm in completadas:
            m = por_nombre.get(cm.machine_name.lower())
            if m:
                item = _machine_json(m, categoria_de(m), completa=(m.origen in PUBLIC_ORIGINS))
            else:
                # La máquina se borró del catálogo pero la resolución persiste.
                item = {"id": None, "nombre": cm.machine_name, "dificultad": "",
                        "clase": "", "color": "#64748b", "origen": None,
                        "categoria": None, "logo_url": None}
            wu = writeup_por_maquina.get(cm.machine_name.lower())
            item["completada_el"] = _iso(cm.completed_at)
            item["writeup_url"]   = wu.url if wu else None
            item["certificado"]   = certificado_de(cm.machine_name)
            maquinas_hechas.append(item)

        # --- Máquinas creadas ------------------------------------------------
        creadas = [
            m for m in maquinas
            if m.autor and m.autor.lower() == ulower and m.origen in PUBLIC_ORIGINS
        ]
        creadas.sort(key=lambda m: m.id, reverse=True)
        maquinas_creadas = [_machine_json(m, categoria_de(m)) for m in creadas]

        # --- Writeups ---------------------------------------------------------
        writeups_json = [
            {
                "maquina":      w.maquina,
                "url":          w.url,
                "tipo":         w.tipo,
                "publicado_el": _iso(w.created_at),
                "logo_url":     (f"/img/maquina/{por_nombre[w.maquina.lower()].id}"
                                 if w.maquina.lower() in por_nombre else None),
            }
            for w in writeups
        ]

        # --- Certificados -----------------------------------------------------
        # Cada writeup publicado da derecho a un certificado; el PDF y la imagen
        # se archivan al publicarlo, así que `generado` es true salvo rarezas.
        certificados = []
        vistos = set()
        for w in writeups:
            clave = w.maquina.lower()
            if clave in vistos:
                continue
            vistos.add(clave)

            m = por_nombre.get(clave)
            cert = certs.get(clave)
            cid = cert.cert_id if cert else certificate_id(username, w.maquina)

            certificados.append({
                "cert_id":    cid,
                "maquina":    m.nombre if m else w.maquina,
                "dificultad": m.dificultad if m else "",
                "logo_url":   f"/img/maquina/{m.id}" if m else None,
                "generado":   bool(cert),
                "emitido_el": _iso(cert.created_at) if cert else None,
                "pdf_url":    f"/api/certificado/pdf/{cid}" if cert else None,
                "imagen_url": f"/api/certificado/imagen/{cid}" if cert else None,
                "verify_url": f"/api/certificado/verificar/{cid}",
            })

        # --- Progreso sobre el catálogo público -------------------------------
        catalogo = [m for m in maquinas if m.origen == CATALOGO_ORIGEN]
        hechas_catalogo = {
            cm.machine_name.lower() for cm in completadas
            if (por_nombre.get(cm.machine_name.lower()) is not None
                and por_nombre[cm.machine_name.lower()].origen == CATALOGO_ORIGEN)
        }

        conteo = {}
        for m in catalogo:
            clase = (m.clase or '').lower()
            slot = conteo.setdefault(clase, {"hechas": 0, "totales": 0})
            slot["totales"] += 1
            if m.nombre.lower() in hechas_catalogo:
                slot["hechas"] += 1

        # Orden estable de fácil a difícil; lo desconocido, al final.
        claves = [c for c in ORDEN_CLASES if c in conteo]
        claves += sorted(c for c in conteo if c not in ORDEN_CLASES)
        por_dificultad = {
            ETIQUETA_CLASE.get(c, c or "Sin clasificar"): conteo[c] for c in claves
        }

        total_catalogo = len(catalogo)
        pos_writeups, puntos = _ranking_position(WriteupRanking, 'puntos', username)
        pos_creadores, _     = _ranking_position(CreatorRanking, 'maquinas', username)

        estadisticas = {
            "maquinas_hechas":          len(maquinas_hechas),
            "maquinas_creadas":         len(maquinas_creadas),
            "writeups_publicados":      len(writeups_json),
            "certificados_disponibles": len(certificados),
            "certificados_generados":   sum(1 for c in certificados if c["generado"]),
            "puntos_writeups":          puntos,
            "ranking_writeups":         pos_writeups,
            "ranking_creadores":        pos_creadores,
        }

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
            "progreso": {
                "catalogo":        CATALOGO_ORIGEN,
                "maquinas_totales": total_catalogo,
                "maquinas_hechas":  len(hechas_catalogo),
                "porcentaje":       round(len(hechas_catalogo) * 100 / total_catalogo, 1) if total_catalogo else 0.0,
                "por_dificultad":   por_dificultad,
            },
            "estadisticas":     estadisticas,
            "maquinas_hechas":  maquinas_hechas,
            "maquinas_creadas": maquinas_creadas,
            "writeups":         writeups_json,
            "certificados":     certificados,
        })
