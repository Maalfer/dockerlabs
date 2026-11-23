"""Páginas públicas de información y legales: cada entrada de `_PAGINAS` es
una ruta y su plantilla."""
import secrets
import time

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

# ruta → plantilla
_PAGINAS = {
    "/soporte": "dockerlabs/info/soporte.html",
    "/herramientas-comunidad": "dockerlabs/info/herramientas_comunidad.html",
    "/agradecimientos": "dockerlabs/info/agradecimientos.html",
    "/autoria": "dockerlabs/info/autoria.html",
    "/terminos-condiciones": "dockerlabs/info/terminos-condiciones.html",
    "/politica-privacidad": "politicas/politica_privacidad.html",
    "/politica-cookies": "politicas/politica_cookies.html",
    "/condiciones-uso": "politicas/condiciones_uso.html",
}


def register_pages_info_routes(pages_router, get_session, templates, url_for):
    def _contexto(session: dict, **extra) -> dict:
        return {"url_for": url_for, "session": session, "current_user_role": session.get("role", ""), **extra}

    def _pagina(plantilla: str):
        def vista(request: Request, session: dict = Depends(get_session)):
            return templates.TemplateResponse(request, plantilla, _contexto(session))
        return vista

    for ruta, plantilla in _PAGINAS.items():
        pages_router.add_api_route(
            ruta,
            _pagina(plantilla),
            methods=["GET"],
            response_class=HTMLResponse,
            name="info" + ruta.replace("/", "_").replace("-", "_"),
        )

    # /equipo: cifras públicas agregadas (máquinas, usuarios, writeups), cacheadas 10 min.
    _cifras_cache = {"t": 0.0, "datos": None}

    def _cifras() -> dict:
        ahora = time.time()
        if _cifras_cache["datos"] is None or ahora - _cifras_cache["t"] > 600:
            from dockerlabs.models import Machine, User, Writeup
            try:
                _cifras_cache["datos"] = {
                    "maquinas": Machine.query.filter_by(origen="docker").count(),
                    "usuarios": User.query.count(),
                    "writeups": Writeup.query.count(),
                }
                _cifras_cache["t"] = ahora
            except Exception:
                return _cifras_cache["datos"] or {}
        return _cifras_cache["datos"]

    @pages_router.get("/equipo", response_class=HTMLResponse)
    def equipo_page(request: Request, session: dict = Depends(get_session)):
        return templates.TemplateResponse(request, "dockerlabs/equipo.html", _contexto(session, cifras=_cifras()))

    @pages_router.get("/instrucciones-uso", include_in_schema=False)
    def instrucciones_uso_retirada():
        # Página retirada: su contenido vive en la guía de ayuda (botón «?» del inicio).
        # 301 para que los enlaces y resultados de búsqueda antiguos no acaben en un 404.
        return RedirectResponse(url="/", status_code=301)

    @pages_router.get("/como-se-crea-una-maquina", include_in_schema=False)
    def como_se_crea_retirada():
        # Página unificada con /enviar-maquina («Crear y enviar una máquina»).
        # 301 para que enlaces y resultados de búsqueda antiguos lleguen a la nueva.
        return RedirectResponse(url="/enviar-maquina", status_code=301)

    @pages_router.get("/enviar-maquina", response_class=HTMLResponse)
    def enviar_maquina_page(request: Request, session: dict = Depends(get_session)):
        # El formulario de propuesta necesita token CSRF (sin sesión, uno de un solo uso)
        csrf_token = session.get("csrf_token") or secrets.token_urlsafe(32)
        return templates.TemplateResponse(
            request,
            "dockerlabs/info/enviar_maquina.html",
            _contexto(session, csrf_token_value=csrf_token),
        )

    @pages_router.get("/bug-bounty")
    def bug_bounty_page():
        # Se conserva la URL para no romper enlaces existentes
        return RedirectResponse(url="/", status_code=302)
