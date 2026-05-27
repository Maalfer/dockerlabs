from datetime import datetime
from typing import Optional

import secrets
from fastapi import Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from bunkerlabs.models import BunkerAccessLog, BunkerAccessToken, BunkerResource
from dockerlabs.models import Machine


def register_bunkerlabs_pages_routes(
    pages_router,
    get_flask_session,
    verify_csrf_token,
    require_auth_and_role,
    set_flask_session_cookie,
    templates,
    alchemy_db,
    url_for,
):
    @pages_router.get("/bunkerlabs/login", response_class=HTMLResponse)
    @pages_router.post("/bunkerlabs/login", response_class=HTMLResponse)
    async def bunkerlabs_login_page(
        request: Request,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """Login de BunkerLabs."""
        if flask_session.get("bunkerlabs_ok"):
            return RedirectResponse(url="/bunkerlabs", status_code=302)

        error = None

        if request.method == "POST":
            form = await request.form()
            token_introducido = (form.get("password") or "").strip()

            if not token_introducido:
                error = "Debes introducir una contraseña de acceso."
            else:
                token_obj = BunkerAccessToken.query.filter_by(token=token_introducido, activo=1).first()
                if token_obj:
                    docker_username = flask_session.get("username")
                    if docker_username:
                        token_obj.nombre = docker_username
                        token_obj.last_accessed = datetime.utcnow()
                        alchemy_db.session.add(
                            BunkerAccessLog(token_id=token_obj.id, user_nombre=docker_username, accessed_at=datetime.utcnow())
                        )
                        alchemy_db.session.commit()
                        flask_session["bunkerlabs_nombre"] = docker_username
                    else:
                        flask_session["bunkerlabs_nombre"] = token_obj.nombre
                        token_obj.last_accessed = datetime.utcnow()
                        alchemy_db.session.add(
                            BunkerAccessLog(token_id=token_obj.id, user_nombre=token_obj.nombre, accessed_at=datetime.utcnow())
                        )
                        alchemy_db.session.commit()

                    flask_session["bunkerlabs_ok"] = True
                    flask_session["bunkerlabs_id"] = token_obj.id
                    cookie = set_flask_session_cookie(flask_session)
                    resp = RedirectResponse(url="/bunkerlabs", status_code=302)
                    resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
                    return resp
                else:
                    error = "Contraseña incorrecta o inactiva."

        csrf_token = flask_session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            flask_session["csrf_token"] = csrf_token

        context = {
            "error": error,
            "session": flask_session,
            "csrf_token_value": csrf_token,
            "g": {"csp_nonce": secrets.token_urlsafe(32)},
        }

        response = templates.TemplateResponse(request, "bunkerlabs/login-bunkerlabs.html", context)
        response.set_cookie("session", set_flask_session_cookie(flask_session), httponly=True, secure=True, path="/", samesite="lax")
        return response

    @pages_router.get("/bunkerlabs/guest")
    def bunkerlabs_guest(request: Request, flask_session: dict = Depends(get_flask_session)):
        """Acceso en modo invitado a BunkerLabs."""
        is_unauthenticated = flask_session.get("user_id") is None
        flask_session["bunkerlabs_ok"] = True
        flask_session["bunkerlabs_guest"] = True
        flask_session["bunkerlabs_nombre"] = "Invitado"
        flask_session["bunkerlabs_id"] = None
        flask_session["bunkerlabs_unauthenticated"] = is_unauthenticated
        cookie = set_flask_session_cookie(flask_session)
        resp = RedirectResponse(url="/bunkerlabs", status_code=302)
        resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
        return resp

    @pages_router.get("/bunkerlabs/logout")
    def bunkerlabs_logout(request: Request, flask_session: dict = Depends(get_flask_session)):
        """Logout de BunkerLabs. Limpia las claves de sesión de BunkerLabs."""
        for key in ("bunkerlabs_ok", "bunkerlabs_guest", "bunkerlabs_nombre", "bunkerlabs_id"):
            flask_session.pop(key, None)
        cookie = set_flask_session_cookie(flask_session)
        resp = RedirectResponse(url="/bunkerlabs/login", status_code=302)
        resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
        return resp

    @pages_router.get("/bunkerlabs", response_class=HTMLResponse)
    @pages_router.get("/bunkerlabs/", response_class=HTMLResponse)
    async def bunkerlabs_home(
        request: Request,
        token: Optional[str] = None,
        flask_session: dict = Depends(get_flask_session),
    ):
        """Página principal de BunkerLabs."""
        if token:
            token_obj = BunkerAccessToken.query.filter_by(token=token, activo=1).first()
            if token_obj:
                docker_username = flask_session.get("username")
                docker_user_id = flask_session.get("user_id")
                if docker_username and docker_user_id:
                    token_obj.nombre = docker_username
                    flask_session["bunkerlabs_nombre"] = docker_username
                    flask_session["bunkerlabs_anonymous"] = False
                else:
                    flask_session["bunkerlabs_nombre"] = "Anónimo"
                    flask_session["bunkerlabs_anonymous"] = True
                flask_session["bunkerlabs_ok"] = True
                token_obj.last_accessed = datetime.utcnow()
                alchemy_db.session.add(
                    BunkerAccessLog(
                        token_id=token_obj.id,
                        user_nombre=flask_session["bunkerlabs_nombre"],
                        accessed_at=datetime.utcnow(),
                    )
                )
                alchemy_db.session.commit()
                cookie = set_flask_session_cookie(flask_session)
                resp = RedirectResponse(url="/bunkerlabs", status_code=302)
                resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
                return resp
            else:
                flask_session["_flashes"] = [("error", "El enlace de acceso no es válido o está inactivo.")]
                cookie = set_flask_session_cookie(flask_session)
                resp = RedirectResponse(url="/bunkerlabs/login", status_code=302)
                resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
                return resp

        if "bunkerlabs_nombre" not in flask_session or not flask_session.get("bunkerlabs_ok"):
            return RedirectResponse(url="/bunkerlabs/login", status_code=302)

        maquinas = Machine.query.filter_by(origen="bunker").order_by(Machine.id.asc()).all()

        current_user_role = flask_session.get("role", "")
        csrf_token = flask_session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            flask_session["csrf_token"] = csrf_token
        return templates.TemplateResponse(
            request,
            "bunkerlabs/home.html",
            {
                "maquinas": maquinas,
                "is_guest": flask_session.get("bunkerlabs_guest", False),
                "is_anonymous": flask_session.get("bunkerlabs_anonymous", False),
                "is_unauthenticated_guest": flask_session.get("bunkerlabs_unauthenticated", False),
                "session": flask_session,
                "url_for": url_for,
                "current_user_role": current_user_role,
                "csrf_token_value": csrf_token,
                "g": {"csp_nonce": secrets.token_urlsafe(32)},
            },
        )

    @pages_router.get("/bunkerlabs/accesos")
    def accesos_bunkerlabs_redirect():
        return RedirectResponse(url="/bunkerlabs/gestion", status_code=301)

    @pages_router.get("/bunkerlabs/gestion", response_class=HTMLResponse)
    @pages_router.post("/bunkerlabs/gestion", response_class=HTMLResponse)
    async def gestion_bunkerlabs(
        request: Request,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """Gestión de BunkerLabs. Solo admin."""
        ok, redir = require_auth_and_role(flask_session, ["admin"])
        if not ok:
            return redir

        error = None
        success = None

        if request.method == "POST":
            form = await request.form()
            nombre = (form.get("nombre") or "").strip()
            password = (form.get("password") or "").strip()

            if not nombre or not password:
                error = "El nombre y la contraseña son obligatorios."
            else:
                try:
                    from sqlalchemy.exc import IntegrityError as _IE

                    alchemy_db.session.add(BunkerAccessToken(nombre=nombre, token=password))
                    alchemy_db.session.commit()
                    success = f"Acceso creado correctamente para {nombre}"
                except _IE:
                    alchemy_db.session.rollback()
                    error = "Error: Esa contraseña ya existe."

        from bunkerlabs.models import BunkerWriteup

        tokens = BunkerAccessToken.query.order_by(BunkerAccessToken.created_at.desc()).all()
        real_machines = Machine.query.filter_by(origen="bunker", clase="real").order_by(Machine.nombre.asc()).all()
        writeups = BunkerWriteup.query.order_by(BunkerWriteup.created_at.desc()).all()
        bunker_machines = Machine.query.filter_by(origen="bunker").order_by(Machine.nombre.asc()).all()
        recursos = BunkerResource.query.order_by(BunkerResource.created_at.desc()).all()

        csrf_token = flask_session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            flask_session["csrf_token"] = csrf_token

        context = {
            "tokens": tokens,
            "error": error,
            "success": success,
            "real_machines": real_machines,
            "writeups": writeups,
            "bunker_machines": bunker_machines,
            "recursos": recursos,
            "session": flask_session,
            "csrf_token_value": csrf_token,
            "g": {"csp_nonce": secrets.token_urlsafe(32)},
        }

        response = templates.TemplateResponse(request, "bunkerlabs/gestion.html", context)
        response.set_cookie("session", set_flask_session_cookie(flask_session), httponly=True, secure=True, path="/", samesite="lax")
        return response

    @pages_router.post("/bunkerlabs/gestion/{token_id}/delete")
    def delete_bunker_token(
        token_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """Eliminar token de acceso a BunkerLabs. Solo admin."""
        ok, redir = require_auth_and_role(flask_session, ["admin"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        token_obj = BunkerAccessToken.query.get(token_id)
        if token_obj:
            alchemy_db.session.delete(token_obj)
            alchemy_db.session.commit()
        return RedirectResponse(url="/bunkerlabs/gestion", status_code=302)

    @pages_router.post("/bunkerlabs/admin/writeups/add")
    async def add_bunker_writeup(
        request: Request,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """Añadir writeup para máquina de Entornos Reales. Solo admin."""
        ok, redir = require_auth_and_role(flask_session, ["admin"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        form = await request.form()
        maquina = (form.get("maquina") or "").strip()
        autor = (form.get("autor") or "").strip()
        url_val = (form.get("url") or "").strip()
        tipo = (form.get("tipo") or "").strip()
        locked = "locked" in form

        if not all([maquina, autor, url_val, tipo]) or tipo not in ["texto", "video"]:
            flask_session["_flashes"] = [("error", "Todos los campos son obligatorios y el tipo debe ser texto o video.")]
            cookie = set_flask_session_cookie(flask_session)
            resp = RedirectResponse(url="/bunkerlabs/accesos", status_code=302)
            resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
            return resp

        from bunkerlabs.models import BunkerWriteup
        from sqlalchemy.exc import IntegrityError as _IE

        try:
            alchemy_db.session.add(BunkerWriteup(maquina=maquina, autor=autor, url=url_val, tipo=tipo, locked=locked))
            alchemy_db.session.commit()
            flask_session["_flashes"] = [("success", f"Writeup añadido correctamente para {maquina}")]
        except _IE:
            alchemy_db.session.rollback()
            flask_session["_flashes"] = [("error", "Error: Este writeup ya existe.")]
        except Exception as e:
            alchemy_db.session.rollback()
            flask_session["_flashes"] = [("error", f"Error al añadir writeup: {str(e)}")]

        cookie = set_flask_session_cookie(flask_session)
        resp = RedirectResponse(url="/bunkerlabs/gestion", status_code=302)
        resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
        return resp

    @pages_router.post("/bunkerlabs/admin/writeups/delete/{writeup_id}")
    def delete_bunker_writeup(
        writeup_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """Eliminar writeup de BunkerLabs. Solo admin."""
        ok, redir = require_auth_and_role(flask_session, ["admin"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        from bunkerlabs.models import BunkerWriteup

        writeup = BunkerWriteup.query.get(writeup_id)
        if writeup:
            try:
                alchemy_db.session.delete(writeup)
                alchemy_db.session.commit()
                flask_session["_flashes"] = [("success", "Writeup eliminado correctamente.")]
            except Exception as e:
                alchemy_db.session.rollback()
                flask_session["_flashes"] = [("error", f"Error al eliminar writeup: {str(e)}")]
        else:
            flask_session["_flashes"] = [("error", "Writeup no encontrado.")]

        cookie = set_flask_session_cookie(flask_session)
        resp = RedirectResponse(url="/bunkerlabs/gestion", status_code=302)
        resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
        return resp

    # ─── BunkerLabs Recursos ────────────────────────────────────────────────────

    @pages_router.get("/bunkerlabs/recursos", response_class=HTMLResponse)
    async def bunkerlabs_recursos(
        request: Request,
        flask_session: dict = Depends(get_flask_session),
    ):
        """Página pública de recursos de BunkerLabs. Accesible con enlace directo."""

        recursos = BunkerResource.query.order_by(BunkerResource.created_at.desc()).all()
        current_user_role = flask_session.get("role", "")
        csrf_token = flask_session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            flask_session["csrf_token"] = csrf_token

        return templates.TemplateResponse(
            request,
            "bunkerlabs/recursos.html",
            {
                "recursos": recursos,
                "session": flask_session,
                "current_user_role": current_user_role,
                "csrf_token_value": csrf_token,
                "url_for": url_for,
                "g": {"csp_nonce": secrets.token_urlsafe(32)},
            },
        )

    @pages_router.post("/bunkerlabs/admin/recursos/add")
    async def add_bunker_recurso(
        request: Request,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """Añadir recurso a BunkerLabs. Solo admin."""
        ok, redir = require_auth_and_role(flask_session, ["admin"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        form = await request.form()
        titulo = (form.get("titulo") or "").strip()
        descripcion = (form.get("descripcion") or "").strip() or None
        url_val = (form.get("url") or "").strip()

        if not titulo or not url_val:
            flask_session["_flashes"] = [("error", "El título y la URL son obligatorios.")]
        else:
            try:
                alchemy_db.session.add(BunkerResource(titulo=titulo, descripcion=descripcion, url=url_val))
                alchemy_db.session.commit()
                flask_session["_flashes"] = [("success", f"Recurso '{titulo}' añadido correctamente.")]
            except Exception as e:
                alchemy_db.session.rollback()
                flask_session["_flashes"] = [("error", f"Error al añadir recurso: {str(e)}")]

        cookie = set_flask_session_cookie(flask_session)
        resp = RedirectResponse(url="/bunkerlabs/gestion", status_code=302)
        resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
        return resp

    @pages_router.post("/bunkerlabs/admin/recursos/delete/{recurso_id}")
    def delete_bunker_recurso(
        recurso_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """Eliminar recurso de BunkerLabs. Solo admin."""
        ok, redir = require_auth_and_role(flask_session, ["admin"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        recurso = BunkerResource.query.get(recurso_id)
        if recurso:
            try:
                alchemy_db.session.delete(recurso)
                alchemy_db.session.commit()
                flask_session["_flashes"] = [("success", "Recurso eliminado correctamente.")]
            except Exception as e:
                alchemy_db.session.rollback()
                flask_session["_flashes"] = [("error", f"Error al eliminar recurso: {str(e)}")]
        else:
            flask_session["_flashes"] = [("error", "Recurso no encontrado.")]

        cookie = set_flask_session_cookie(flask_session)
        resp = RedirectResponse(url="/bunkerlabs/gestion", status_code=302)
        resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
        return resp

    @pages_router.post("/bunkerlabs/admin/recursos/edit/{recurso_id}")
    async def edit_bunker_recurso(
        recurso_id: int,
        request: Request,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """Editar recurso de BunkerLabs. Solo admin."""
        ok, redir = require_auth_and_role(flask_session, ["admin"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        form = await request.form()
        titulo = (form.get("titulo") or "").strip()
        descripcion = (form.get("descripcion") or "").strip() or None
        url_val = (form.get("url") or "").strip()

        recurso = BunkerResource.query.get(recurso_id)
        if not recurso:
            flask_session["_flashes"] = [("error", "Recurso no encontrado.")]
        elif not titulo or not url_val:
            flask_session["_flashes"] = [("error", "El título y la URL son obligatorios.")]
        else:
            try:
                recurso.titulo = titulo
                recurso.descripcion = descripcion
                recurso.url = url_val
                alchemy_db.session.commit()
                flask_session["_flashes"] = [("success", "Recurso actualizado correctamente.")]
            except Exception as e:
                alchemy_db.session.rollback()
                flask_session["_flashes"] = [("error", f"Error al actualizar recurso: {str(e)}")]

        cookie = set_flask_session_cookie(flask_session)
        resp = RedirectResponse(url="/bunkerlabs/gestion", status_code=302)
        resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
        return resp

