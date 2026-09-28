"""Recursos de raiz para navegadores y buscadores: favicon, robots y sitemap.

Van en rutas de primer nivel (/favicon.ico, /robots.txt, /sitemap.xml) porque
es donde los clientes las piden por convencion; nginx no las intercepta, asi
que las sirve la aplicacion.
"""

import os
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from fastapi import Request
from fastapi.responses import FileResponse, PlainTextResponse, Response

from dockerlabs.extensions import db
from dockerlabs.models import CreatorRanking, User, WriteupRanking

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_FAVICON = os.path.join(_BASE_DIR, "static", "dockerlabs", "images", "logos", "favicon.ico")

SITIO = "https://dockerlabs.es"

# Paginas publicas indexables. Se excluyen a proposito los flujos de
# autenticacion (login, registro, recuperacion) por ser contenido sin valor
# de busqueda, y todo lo que exige sesion.
PAGINAS_PUBLICAS = [
    ("/",                        "daily",   "1.0"),
    ("/estadisticas",            "daily",   "0.8"),
    ("/instrucciones-uso",       "monthly", "0.7"),
    ("/como-se-crea-una-maquina", "monthly", "0.7"),
    ("/enviar-maquina",          "monthly", "0.6"),
    ("/agradecimientos",         "monthly", "0.5"),
    ("/equipo",                  "monthly", "0.5"),
    ("/soporte",                 "monthly", "0.5"),
    ("/terminos-condiciones",    "yearly",  "0.3"),
    ("/condiciones-uso",         "yearly",  "0.3"),
    ("/politica-privacidad",     "yearly",  "0.3"),
    ("/politica-cookies",        "yearly",  "0.3"),
]

# Prefijos que ningun buscador debe rastrear: API, zona privada y area gated.
RUTAS_PRIVADAS = [
    "/api/",
    "/go/",
    "/add-maquina",
    "/bug-bounty",
    "/bunkerlabs",
    "/certificados",
    "/dashboard",
    "/gestion-maquinas",
    "/gestion-usuarios",
    "/logout",
    "/maquinas-hechas",
    "/pending-machines",
    "/user-pending",
    "/writeups-analisis",
    "/writeups-publicados",
    "/writeups-recibidos",
    "/login",
    "/register",
    "/recover",
    "/reset-password",
    "/verify-email",
    "/fastapi-docs",
    "/fastapi-openapi.json",
    "/redoc",
]


def _slugs_con_contenido():
    """Slugs de perfiles que merece la pena indexar.

    Solo los usuarios que aparecen en algun ranking (crean maquinas o publican
    writeups). Incluir los ~3.500 registrados llenaria el sitemap de perfiles
    vacios, que es justo lo que penalizan los buscadores.
    """
    nombres = set()
    for (n,) in db.session.query(CreatorRanking.nombre).all():
        if n:
            nombres.add(n.lower())
    for (n,) in db.session.query(WriteupRanking.nombre).all():
        if n:
            nombres.add(n.lower())
    if not nombres:
        return []

    slugs = []
    for slug, username in db.session.query(User.slug, User.username).filter(User.slug.isnot(None)).all():
        if username and username.lower() in nombres and slug:
            slugs.append(slug)
    return sorted(set(slugs))


def register_seo_routes(pages_router):
    """Registra las rutas de raiz para navegadores y buscadores."""

    @pages_router.get("/favicon.ico", include_in_schema=False)
    def favicon():
        if not os.path.isfile(_FAVICON):
            return Response(status_code=404)
        return FileResponse(
            _FAVICON,
            media_type="image/x-icon",
            headers={"Cache-Control": "public, max-age=604800"},   # 7 dias
        )

    @pages_router.get("/robots.txt", include_in_schema=False)
    def robots():
        lineas = ["User-agent: *", "Allow: /"]
        lineas += ["Disallow: %s" % p for p in RUTAS_PRIVADAS]
        lineas += ["", "Sitemap: %s/sitemap.xml" % SITIO, ""]
        return PlainTextResponse(
            "\n".join(lineas),
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @pages_router.get("/sitemap.xml", include_in_schema=False)
    def sitemap(request: Request):
        hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        partes = ['<?xml version="1.0" encoding="UTF-8"?>',
                  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']

        for ruta, frecuencia, prioridad in PAGINAS_PUBLICAS:
            partes.append(
                "  <url><loc>%s%s</loc><lastmod>%s</lastmod>"
                "<changefreq>%s</changefreq><priority>%s</priority></url>"
                % (SITIO, escape(ruta), hoy, frecuencia, prioridad)
            )

        try:
            for slug in _slugs_con_contenido():
                partes.append(
                    "  <url><loc>%s/perfil/%s</loc><lastmod>%s</lastmod>"
                    "<changefreq>weekly</changefreq><priority>0.6</priority></url>"
                    % (SITIO, escape(slug), hoy)
                )
        except Exception:
            # Un fallo consultando perfiles no debe dejar el sitio sin sitemap:
            # se sirve al menos el bloque de paginas estaticas.
            db.session.rollback()

        partes.append("</urlset>")
        return Response(
            "\n".join(partes),
            media_type="application/xml",
            headers={"Cache-Control": "public, max-age=3600"},
        )
