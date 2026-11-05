"""Páginas públicas de información y legales: cada entrada de `_PAGINAS` es
una ruta y su plantilla."""
import secrets

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

# ruta → plantilla
_PAGINAS = {
    "/instrucciones-uso": "dockerlabs/info/instrucciones_uso.html",
    "/soporte": "dockerlabs/info/soporte.html",
    "/equipo": "dockerlabs/equipo.html",
    "/como-se-crea-una-maquina": "dockerlabs/info/como_se_crea_una_maquina.html",
    "/agradecimientos": "dockerlabs/info/agradecimientos.html",
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
