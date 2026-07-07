import os
from datetime import datetime
from typing import Optional
from urllib.parse import quote

import secrets
from fastapi import Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from werkzeug.utils import secure_filename

from sqlalchemy.exc import IntegrityError

from bunkerlabs.models import BunkerAccessLog, BunkerAccessToken, BunkerResource
from dockerlabs.models import Machine


def register_bunkerlabs_pages_routes(
    pages_router,
    get_session,
    verify_csrf_token,
    require_auth_and_role,
    encode_session_cookie,
    templates,
    db,
    url_for,
):
    @pages_router.get("/bunkerlabs/login", response_class=HTMLResponse)
    @pages_router.post("/bunkerlabs/login", response_class=HTMLResponse)
    async def bunkerlabs_login_page(
        request: Request,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        # Máquina compartida a resaltar tras el acceso (se conserva a través del login)
        maquina = (request.query_params.get("maquina") or "").strip()

        def _bunker_home_url(nombre):
            return "/bunkerlabs?maquina=" + quote(nombre, safe="") if nombre else "/bunkerlabs"

        if session.get("bunkerlabs_ok"):
            return RedirectResponse(url=_bunker_home_url(maquina), status_code=302)

        error = None

        if request.method == "POST":
            form = await request.form()
            token_introducido = (form.get("password") or "").strip()
            maquina = (form.get("maquina") or maquina or "").strip()

            if not token_introducido:
                error = "Debes introducir una contraseña de acceso."
            else:
                token_obj = BunkerAccessToken.query.filter_by(token=token_introducido, activo=1).first()
                if token_obj:
                    docker_username = session.get("username")
                    if docker_username:
                        token_obj.nombre = docker_username
                        token_obj.last_accessed = datetime.utcnow()
                        db.session.add(
                            BunkerAccessLog(token_id=token_obj.id, user_nombre=docker_username, accessed_at=datetime.utcnow())
                        )
                        db.session.commit()
                        session["bunkerlabs_nombre"] = docker_username
                    else:
                        session["bunkerlabs_nombre"] = token_obj.nombre
                        token_obj.last_accessed = datetime.utcnow()
                        db.session.add(
                            BunkerAccessLog(token_id=token_obj.id, user_nombre=token_obj.nombre, accessed_at=datetime.utcnow())
                        )
                        db.session.commit()

                    session["bunkerlabs_ok"] = True
                    session["bunkerlabs_id"] = token_obj.id
                    cookie = encode_session_cookie(session)
                    resp = RedirectResponse(url=_bunker_home_url(maquina), status_code=302)
                    resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
                    return resp
                else:
                    error = "Contraseña incorrecta o inactiva."

        csrf_token = session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            session["csrf_token"] = csrf_token

        context = {
            "error": error,
            "session": session,
            "csrf_token_value": csrf_token,
            "maquina": maquina,
            "g": {"csp_nonce": secrets.token_urlsafe(32)},
        }

        response = templates.TemplateResponse(request, "bunkerlabs/login-bunkerlabs.html", context)
        response.set_cookie("session", encode_session_cookie(session), httponly=True, secure=True, path="/", samesite="lax")
        return response

    @pages_router.get("/bunkerlabs/guest")
    def bunkerlabs_guest(
        request: Request,
        maquina: Optional[str] = None,
        session: dict = Depends(get_session),
    ):
        is_unauthenticated = session.get("user_id") is None
        session["bunkerlabs_ok"] = True
        session["bunkerlabs_guest"] = True
        session["bunkerlabs_nombre"] = "Invitado"
        session["bunkerlabs_id"] = None
        session["bunkerlabs_unauthenticated"] = is_unauthenticated
        cookie = encode_session_cookie(session)
        destino = "/bunkerlabs?maquina=" + quote(maquina.strip(), safe="") if maquina and maquina.strip() else "/bunkerlabs"
        resp = RedirectResponse(url=destino, status_code=302)
        resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
        return resp

    @pages_router.get("/bunkerlabs/logout")
    def bunkerlabs_logout(request: Request, session: dict = Depends(get_session)):
        for key in ("bunkerlabs_ok", "bunkerlabs_guest", "bunkerlabs_nombre", "bunkerlabs_id"):
            session.pop(key, None)
        cookie = encode_session_cookie(session)
        resp = RedirectResponse(url="/bunkerlabs/login", status_code=302)
        resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
        return resp

    @pages_router.get("/bunkerlabs", response_class=HTMLResponse)
    @pages_router.get("/bunkerlabs/", response_class=HTMLResponse)
    async def bunkerlabs_home(
        request: Request,
        token: Optional[str] = None,
        maquina: Optional[str] = None,
        session: dict = Depends(get_session),
    ):
        if token:
            token_obj = BunkerAccessToken.query.filter_by(token=token, activo=1).first()
            if token_obj:
                docker_username = session.get("username")
                docker_user_id = session.get("user_id")
                if docker_username and docker_user_id:
                    token_obj.nombre = docker_username
                    session["bunkerlabs_nombre"] = docker_username
                    session["bunkerlabs_anonymous"] = False
                else:
                    session["bunkerlabs_nombre"] = "Anónimo"
                    session["bunkerlabs_anonymous"] = True
                session["bunkerlabs_ok"] = True
                token_obj.last_accessed = datetime.utcnow()
                db.session.add(
                    BunkerAccessLog(
                        token_id=token_obj.id,
                        user_nombre=session["bunkerlabs_nombre"],
                        accessed_at=datetime.utcnow(),
                    )
                )
                db.session.commit()
                cookie = encode_session_cookie(session)
                resp = RedirectResponse(url="/bunkerlabs", status_code=302)
                resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
                return resp
            else:
                session["_flashes"] = [("error", "El enlace de acceso no es válido o está inactivo.")]
                cookie = encode_session_cookie(session)
                resp = RedirectResponse(url="/bunkerlabs/login", status_code=302)
                resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
                return resp

        if "bunkerlabs_nombre" not in session or not session.get("bunkerlabs_ok"):
            # Enlace compartido: si llega alguien por ?maquina= sin sesión de bunker,
            # se le concede acceso de invitado automáticamente y se le lleva a la
            # máquina resaltada (aunque como invitado no pueda descargarla).
            if maquina and maquina.strip():
                session["bunkerlabs_ok"] = True
                session["bunkerlabs_guest"] = True
                session["bunkerlabs_nombre"] = session.get("username") or "Invitado"
                session["bunkerlabs_id"] = None
                session["bunkerlabs_unauthenticated"] = session.get("user_id") is None
                cookie = encode_session_cookie(session)
                resp = RedirectResponse(
                    url="/bunkerlabs?maquina=" + quote(maquina.strip(), safe=""),
                    status_code=302,
                )
                resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
                return resp
            return RedirectResponse(url="/bunkerlabs/login", status_code=302)

        maquinas = Machine.query.filter_by(origen="bunker").order_by(Machine.id.asc()).all()

        current_user_role = session.get("role", "")
        csrf_token = session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            session["csrf_token"] = csrf_token
        return templates.TemplateResponse(
            request,
            "bunkerlabs/home.html",
            {
                "maquinas": maquinas,
                "is_guest": session.get("bunkerlabs_guest", False),
                "is_anonymous": session.get("bunkerlabs_anonymous", False),
                "is_unauthenticated_guest": session.get("bunkerlabs_unauthenticated", False),
                "session": session,
                "url_for": url_for,
                "current_user_role": current_user_role,
                "csrf_token_value": csrf_token,
                "g": {"csp_nonce": secrets.token_urlsafe(32)},
            },
        )

    @pages_router.get("/bunkerlabs/empezar", response_class=HTMLResponse)
    async def bunkerlabs_empezar(request: Request, session: dict = Depends(get_session)):
        """Sección 'Empezar de 0': labs de iniciación que se descargan como .py.
        Mismo gate de acceso que el resto de /bunkerlabs (PIN/login)."""
        if "bunkerlabs_nombre" not in session or not session.get("bunkerlabs_ok"):
            return RedirectResponse(url="/bunkerlabs/login", status_code=302)

        maquinas = Machine.query.filter_by(origen="empezar").order_by(Machine.id.asc()).all()

        current_user_role = session.get("role", "")
        csrf_token = session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            session["csrf_token"] = csrf_token
        return templates.TemplateResponse(
            request,
            "bunkerlabs/empezar.html",
            {
                "maquinas": maquinas,
                "is_guest": session.get("bunkerlabs_guest", False),
                "session": session,
                "url_for": url_for,
                "current_user_role": current_user_role,
                "csrf_token_value": csrf_token,
                "g": {"csp_nonce": secrets.token_urlsafe(32)},
            },
        )

    @pages_router.get("/bunkerlabs/empezar/descargar/{machine_id}")
    def descargar_empezar(machine_id: int, request: Request, session: dict = Depends(get_session)):
        """Descarga directa del .py de un lab de iniciación (gated como /bunkerlabs)."""
        if "bunkerlabs_nombre" not in session or not session.get("bunkerlabs_ok"):
            return RedirectResponse(url="/bunkerlabs/login", status_code=302)

        lab = Machine.query.filter_by(id=machine_id, origen="empezar").first()
        if not lab or not lab.script_path:
            raise HTTPException(status_code=404, detail="Script no encontrado")

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        full_path = os.path.join(base_dir, lab.script_path)
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="Script no encontrado")

        safe = secure_filename(lab.nombre) or "lab"
        return FileResponse(
            full_path,
            media_type="text/x-python",
            filename=f"{safe}.py",
            headers={"Content-Disposition": f'attachment; filename="{safe}.py"'},
        )

    @pages_router.get("/bunkerlabs/accesos")
    def accesos_bunkerlabs_redirect():
        return RedirectResponse(url="/bunkerlabs/gestion", status_code=301)

    @pages_router.get("/bunkerlabs/gestion", response_class=HTMLResponse)
    @pages_router.post("/bunkerlabs/gestion", response_class=HTMLResponse)
    async def gestion_bunkerlabs(
        request: Request,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        ok, redir = require_auth_and_role(session, ["admin"])
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
                    db.session.add(BunkerAccessToken(nombre=nombre, token=password))
                    db.session.commit()
                    success = f"Acceso creado correctamente para {nombre}"
                except IntegrityError:
                    db.session.rollback()
                    error = "Error: Esa contraseña ya existe."

        tokens = BunkerAccessToken.query.order_by(BunkerAccessToken.created_at.desc()).all()
        real_machines = Machine.query.filter_by(origen="bunker", clase="real").order_by(Machine.nombre.asc()).all()
        bunker_machines = Machine.query.filter_by(origen="bunker").order_by(Machine.nombre.asc()).all()
        recursos = BunkerResource.query.order_by(BunkerResource.created_at.desc()).all()

        csrf_token = session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            session["csrf_token"] = csrf_token

        context = {
            "tokens": tokens,
            "error": error,
            "success": success,
            "real_machines": real_machines,
            "bunker_machines": bunker_machines,
            "recursos": recursos,
            "session": session,
            "csrf_token_value": csrf_token,
            "g": {"csp_nonce": secrets.token_urlsafe(32)},
        }

        response = templates.TemplateResponse(request, "bunkerlabs/gestion.html", context)
        response.set_cookie("session", encode_session_cookie(session), httponly=True, secure=True, path="/", samesite="lax")
        return response

    @pages_router.post("/bunkerlabs/gestion/{token_id}/delete")
    def delete_bunker_token(
        token_id: int,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        ok, redir = require_auth_and_role(session, ["admin"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        token_obj = BunkerAccessToken.query.get(token_id)
        if token_obj:
            db.session.delete(token_obj)
            db.session.commit()
        return RedirectResponse(url="/bunkerlabs/gestion", status_code=302)

    @pages_router.get("/bunkerlabs/recursos", response_class=HTMLResponse)
    async def bunkerlabs_recursos(
        request: Request,
        session: dict = Depends(get_session),
    ):

        recursos = BunkerResource.query.order_by(BunkerResource.created_at.desc()).all()
        current_user_role = session.get("role", "")
        csrf_token = session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            session["csrf_token"] = csrf_token

        return templates.TemplateResponse(
            request,
            "bunkerlabs/recursos.html",
            {
                "recursos": recursos,
                "session": session,
                "current_user_role": current_user_role,
                "csrf_token_value": csrf_token,
                "url_for": url_for,
                "g": {"csp_nonce": secrets.token_urlsafe(32)},
            },
        )

    @pages_router.post("/bunkerlabs/admin/recursos/add")
    async def add_bunker_recurso(
        request: Request,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        ok, redir = require_auth_and_role(session, ["admin"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        form = await request.form()
        titulo = (form.get("titulo") or "").strip()
        descripcion = (form.get("descripcion") or "").strip() or None
        url_val = (form.get("url") or "").strip()

        if not titulo or not url_val:
            session["_flashes"] = [("error", "El título y la URL son obligatorios.")]
        else:
            try:
                db.session.add(BunkerResource(titulo=titulo, descripcion=descripcion, url=url_val))
                db.session.commit()
                session["_flashes"] = [("success", f"Recurso '{titulo}' añadido correctamente.")]
            except Exception as e:
                db.session.rollback()
                session["_flashes"] = [("error", f"Error al añadir recurso: {str(e)}")]

        cookie = encode_session_cookie(session)
        resp = RedirectResponse(url="/bunkerlabs/gestion", status_code=302)
        resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
        return resp

    @pages_router.post("/bunkerlabs/admin/recursos/delete/{recurso_id}")
    def delete_bunker_recurso(
        recurso_id: int,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        ok, redir = require_auth_and_role(session, ["admin"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        recurso = BunkerResource.query.get(recurso_id)
        if recurso:
            try:
                db.session.delete(recurso)
                db.session.commit()
                session["_flashes"] = [("success", "Recurso eliminado correctamente.")]
            except Exception as e:
                db.session.rollback()
                session["_flashes"] = [("error", f"Error al eliminar recurso: {str(e)}")]
        else:
            session["_flashes"] = [("error", "Recurso no encontrado.")]

        cookie = encode_session_cookie(session)
        resp = RedirectResponse(url="/bunkerlabs/gestion", status_code=302)
        resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
        return resp

    @pages_router.post("/bunkerlabs/admin/recursos/edit/{recurso_id}")
    async def edit_bunker_recurso(
        recurso_id: int,
        request: Request,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        ok, redir = require_auth_and_role(session, ["admin"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        form = await request.form()
        titulo = (form.get("titulo") or "").strip()
        descripcion = (form.get("descripcion") or "").strip() or None
        url_val = (form.get("url") or "").strip()

        recurso = BunkerResource.query.get(recurso_id)
        if not recurso:
            session["_flashes"] = [("error", "Recurso no encontrado.")]
        elif not titulo or not url_val:
            session["_flashes"] = [("error", "El título y la URL son obligatorios.")]
        else:
            try:
                recurso.titulo = titulo
                recurso.descripcion = descripcion
                recurso.url = url_val
                db.session.commit()
                session["_flashes"] = [("success", "Recurso actualizado correctamente.")]
            except Exception as e:
                db.session.rollback()
                session["_flashes"] = [("error", f"Error al actualizar recurso: {str(e)}")]

        cookie = encode_session_cookie(session)
        resp = RedirectResponse(url="/bunkerlabs/gestion", status_code=302)
        resp.set_cookie("session", cookie, httponly=True, secure=True, path="/", samesite="lax")
        return resp

