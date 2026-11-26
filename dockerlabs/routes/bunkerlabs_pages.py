from typing import Optional
from urllib.parse import quote

import secrets
from fastapi import Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

import logging

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from bunkerlabs.models import BunkerAccessLog, BunkerAccessToken
from dockerlabs.models import Machine, MachineDownloadLog
from dockerlabs.tiempo import utcnow

logger = logging.getLogger(__name__)


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
    # ------------------------------------------------------------------
    # Modelo de acceso a BunkerLabs
    #
    # Un PIN (BunkerAccessToken) es una LLAVE compartida, no una identidad:
    # cualquiera que lo conozca entra, tenga o no cuenta en DockerLabs, y nadie
    # es «dueño» de un PIN. Por eso la sesión solo guarda QUÉ acceso se tiene:
    #
    #   bunkerlabs_ok     True si hay acceso concedido
    #   bunkerlabs_guest  True si es el acceso de invitado (sin PIN, catálogo limitado)
    #   bunkerlabs_id     id del PIN usado (para poder revocarlo: si se desactiva
    #                     o se borra, quien entró con él pierde el acceso)
    #
    # QUIÉN es la persona no se guarda aquí: se calcula en cada página a partir
    # de la sesión de DockerLabs (username si la hay; si no, «Anónimo» o
    # «Invitado»). El nombre del PIN es solo una etiqueta para el administrador
    # y nunca se muestra a quien lo usa. Las claves antiguas bunkerlabs_nombre /
    # _anonymous / _unauthenticated ya no se escriben; se limpian al conceder
    # o cerrar el acceso.
    # ------------------------------------------------------------------
    _CLAVES_BUNKER = (
        "bunkerlabs_ok", "bunkerlabs_guest", "bunkerlabs_id",
        "bunkerlabs_nombre", "bunkerlabs_anonymous", "bunkerlabs_unauthenticated",
    )

    def _limpiar_acceso(session: dict) -> None:
        for key in _CLAVES_BUNKER:
            session.pop(key, None)

    def _conceder_acceso(session: dict, token_obj=None) -> None:
        """Con PIN (token_obj) concede acceso completo; sin él, acceso de invitado."""
        _limpiar_acceso(session)
        session["bunkerlabs_ok"] = True
        if token_obj is None:
            session["bunkerlabs_guest"] = True
        else:
            session["bunkerlabs_id"] = token_obj.id

    def _registrar_entrada(session: dict, token_obj) -> None:
        """Anota la entrada en el historial del PIN: quién fue, si se sabe."""
        quien = session.get("username") if session.get("user_id") else None
        token_obj.last_accessed = utcnow()
        db.session.add(BunkerAccessLog(token_id=token_obj.id, user_nombre=quien or "Anónimo", accessed_at=utcnow()))
        db.session.commit()

    def _pin_valido(pin: str):
        pin = (pin or "").strip()
        if not pin or len(pin) > 255:
            return None
        return BunkerAccessToken.query.filter_by(token=pin, activo=1).first()

    def _acceso_vigente(session: dict) -> bool:
        """¿Sigue teniendo acceso? Si entró con un PIN que ya no existe o está
        desactivado, se le retira (la sesión queda limpia; quien llama debe
        reenviar la cookie con `_respuesta`)."""
        if not session.get("bunkerlabs_ok"):
            return False
        token_id = session.get("bunkerlabs_id")
        if token_id is not None:
            activo = db.session.query(BunkerAccessToken.activo).filter(BunkerAccessToken.id == token_id).scalar()
            if not activo:
                _limpiar_acceso(session)
                session["_flashes"] = [("error", "El acceso con el que entraste ya no está activo. Introduce uno válido.")]
                return False
        return True

    def _respuesta(session: dict, url: str):
        resp = RedirectResponse(url=url, status_code=302)
        resp.set_cookie("session", encode_session_cookie(session), httponly=True, secure=True, path="/", samesite="lax")
        return resp

    def _bunker_home_url(nombre):
        nombre = (nombre or "").strip()
        return "/bunkerlabs?maquina=" + quote(nombre, safe="") if nombre else "/bunkerlabs"

    @pages_router.get("/bunkerlabs/login", response_class=HTMLResponse)
    @pages_router.post("/bunkerlabs/login", response_class=HTMLResponse)
    async def bunkerlabs_login_page(
        request: Request,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        # Máquina compartida a resaltar tras el acceso (se conserva a través del login)
        maquina = (request.query_params.get("maquina") or "").strip()

        # Quien ya tiene acceso completo no necesita el formulario. El invitado sí:
        # aquí es donde cambia su acceso de prueba por uno con PIN.
        if request.method == "GET" and _acceso_vigente(session) and not session.get("bunkerlabs_guest"):
            return RedirectResponse(url=_bunker_home_url(maquina), status_code=302)

        # Avisos dejados por otra ruta (enlace directo inválido, PIN desactivado...)
        avisos = session.pop("_flashes", None) or []
        error = avisos[0][1] if avisos and len(avisos[0]) > 1 else None

        if request.method == "POST":
            form = await request.form()
            pin = (form.get("password") or "").strip()
            maquina = (form.get("maquina") or maquina or "").strip()

            if not pin:
                error = "Debes introducir una contraseña de acceso."
            else:
                token_obj = _pin_valido(pin)
                if token_obj:
                    _conceder_acceso(session, token_obj)
                    _registrar_entrada(session, token_obj)
                    return _respuesta(session, _bunker_home_url(maquina))
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
        # No se degrada a invitado a quien ya entró con un PIN válido.
        if not (_acceso_vigente(session) and not session.get("bunkerlabs_guest")):
            _conceder_acceso(session)
        return _respuesta(session, _bunker_home_url(maquina))

    @pages_router.get("/bunkerlabs/logout")
    def bunkerlabs_logout(request: Request, session: dict = Depends(get_session)):
        _limpiar_acceso(session)
        return _respuesta(session, "/bunkerlabs/login")

    @pages_router.get("/bunkerlabs", response_class=HTMLResponse)
    @pages_router.get("/bunkerlabs/", response_class=HTMLResponse)
    async def bunkerlabs_home(
        request: Request,
        token: Optional[str] = None,
        maquina: Optional[str] = None,
        session: dict = Depends(get_session),
    ):
        # Enlace directo (?token=PIN): equivale a teclear el PIN en el formulario.
        if token:
            token_obj = _pin_valido(token)
            if token_obj:
                _conceder_acceso(session, token_obj)
                _registrar_entrada(session, token_obj)
                # Se redirige para que el PIN no se quede en la barra de direcciones
                return _respuesta(session, _bunker_home_url(maquina))
            session["_flashes"] = [("error", "El enlace de acceso no es válido o está inactivo.")]
            return _respuesta(session, "/bunkerlabs/login")

        if not _acceso_vigente(session):
            # Enlace compartido: si llega alguien por ?maquina= sin acceso al búnker,
            # se le concede el de invitado automáticamente y se le lleva a la
            # máquina resaltada (aunque como invitado no pueda descargarla).
            if maquina and maquina.strip() and not session.get("_flashes"):
                _conceder_acceso(session)
                return _respuesta(session, _bunker_home_url(maquina))
            return _respuesta(session, "/bunkerlabs/login")

        maquinas = Machine.query.filter_by(origen="bunker").order_by(Machine.id.asc()).all()

        current_user_role = session.get("role", "")
        csrf_token = session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            session["csrf_token"] = csrf_token

        # Los avisos de «anónimo» / «invitado sin cuenta» se deciden aquí, en cada
        # visita, con el estado real de la sesión de DockerLabs (get_session() ya
        # revalida user_id contra la BD): no se guardan en la cookie, así que
        # desaparecen en cuanto la persona inicia sesión.
        docker_logged_in = bool(session.get("user_id"))
        es_invitado = bool(session.get("bunkerlabs_guest"))

        return templates.TemplateResponse(
            request,
            "bunkerlabs/home.html",
            {
                "maquinas": maquinas,
                "is_guest": es_invitado,
                "is_anonymous": not es_invitado and not docker_logged_in,
                "is_unauthenticated_guest": es_invitado and not docker_logged_in,
                "session": session,
                "url_for": url_for,
                "current_user_role": current_user_role,
                "csrf_token_value": csrf_token,
            },
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
            elif len(nombre) > 60:
                error = "El nombre es demasiado largo (máximo 60 caracteres)."
            elif len(password) < 4 or len(password) > 128:
                error = "La contraseña debe tener entre 4 y 128 caracteres."
            elif any(c.isspace() for c in password):
                error = "La contraseña no puede contener espacios (se usa también en el enlace directo)."
            else:
                try:
                    db.session.add(BunkerAccessToken(nombre=nombre, token=password))
                    db.session.commit()
                    success = f"Acceso creado correctamente para {nombre}"
                except IntegrityError:
                    db.session.rollback()
                    error = "Error: Esa contraseña ya existe."

        tokens = BunkerAccessToken.query.order_by(BunkerAccessToken.created_at.desc()).all()

        # Uso de cada acceso: nº de entradas, personas distintas y última entrada.
        ahora = utcnow()
        uso = {
            tid: {"accesos": n, "personas": personas, "ultimo": ultimo}
            for tid, n, personas, ultimo in db.session.query(
                BunkerAccessLog.token_id,
                func.count(BunkerAccessLog.id),
                func.count(func.distinct(BunkerAccessLog.user_nombre)),
                func.max(BunkerAccessLog.accessed_at),
            ).group_by(BunkerAccessLog.token_id).all()
        }

        def hace(fecha):
            if not fecha:
                return "nunca"
            seg = max(0, (ahora - fecha).total_seconds())
            if seg < 3600:
                return "hace un momento" if seg < 120 else f"hace {int(seg // 60)} min"
            if seg < 86400:
                return f"hace {int(seg // 3600)} h"
            dias = int(seg // 86400)
            if dias == 1:
                return "ayer"
            if dias < 60:
                return f"hace {dias} días"
            if dias < 730:
                return f"hace {dias // 30} meses"
            return f"hace {dias // 365} años"

        filas = []
        for t in tokens:
            u = uso.get(t.id, {"accesos": 0, "personas": 0, "ultimo": None})
            ultimo = u["ultimo"] or t.last_accessed
            filas.append({
                "t": t,
                "accesos": u["accesos"],
                "personas": u["personas"],
                "ultimo": ultimo,
                "ultimo_txt": hace(ultimo),
                "creado_txt": hace(t.created_at) if t.created_at else "",
                "sin_uso": u["accesos"] == 0 and not ultimo,
            })
        from datetime import timedelta
        resumen = {
            "total": len(tokens),
            "activos": sum(1 for t in tokens if t.activo),
            "accesos": sum(u["accesos"] for u in uso.values()),
            "semana": db.session.query(func.count(BunkerAccessLog.id)).filter(
                BunkerAccessLog.accessed_at >= ahora - timedelta(days=7)).scalar() or 0,
        }
        real_machines = Machine.query.filter_by(origen="bunker", clase="real").order_by(Machine.nombre.asc()).all()
        bunker_machines = Machine.query.filter_by(origen="bunker").order_by(Machine.nombre.asc()).all()

        csrf_token = session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            session["csrf_token"] = csrf_token

        context = {
            "tokens": tokens,
            "filas": filas,
            "resumen": resumen,
            "error": error,
            "success": success,
            "real_machines": real_machines,
            "bunker_machines": bunker_machines,
            "session": session,
            "csrf_token_value": csrf_token,
        }

        response = templates.TemplateResponse(request, "bunkerlabs/gestion.html", context)
        response.set_cookie("session", encode_session_cookie(session), httponly=True, secure=True, path="/", samesite="lax")
        return response

    def _quiere_json(request: Request) -> bool:
        return "application/json" in (request.headers.get("accept") or "")

    @pages_router.post("/bunkerlabs/gestion/{token_id}/delete")
    def delete_bunker_token(
        request: Request,
        token_id: int,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        ok, _ = require_auth_and_role(session, ["admin"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        token_obj = db.session.get(BunkerAccessToken, token_id)
        if token_obj:
            try:
                # El historial referencia al token (clave foránea sin cascada): hay que
                # borrarlo antes, o MariaDB rechaza el DELETE y la petición acaba en 500.
                BunkerAccessLog.query.filter_by(token_id=token_id).delete(synchronize_session=False)
                db.session.delete(token_obj)
                db.session.commit()
            except Exception:
                db.session.rollback()
                logger.exception("No se pudo eliminar el acceso de BunkerLabs %s", token_id)
                if _quiere_json(request):
                    return JSONResponse(status_code=500, content={"error": "No se pudo eliminar el acceso"})
        if _quiere_json(request):
            if not token_obj:
                return JSONResponse(status_code=404, content={"error": "Ese acceso ya no existe"})
            return {"success": True, "message": "Acceso eliminado"}
        return RedirectResponse(url="/bunkerlabs/gestion", status_code=302)

    @pages_router.post("/bunkerlabs/gestion/{token_id}/toggle")
    def toggle_bunker_token(
        token_id: int,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """Activa o desactiva un acceso sin borrarlo (ni su historial)."""
        ok, _ = require_auth_and_role(session, ["admin"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
        token_obj = db.session.get(BunkerAccessToken, token_id)
        if not token_obj:
            return JSONResponse(status_code=404, content={"error": "Ese acceso ya no existe"})
        token_obj.activo = 0 if token_obj.activo else 1
        db.session.commit()
        return {"success": True, "activo": bool(token_obj.activo),
                "message": "Acceso activado" if token_obj.activo else "Acceso desactivado"}

    @pages_router.get("/bunkerlabs/maquinas/{machine_id}/descargar", response_class=HTMLResponse)
    def bunkerlabs_descargar_page(machine_id: int, request: Request, session: dict = Depends(get_session)):
        if not _acceso_vigente(session):
            return _respuesta(session, "/bunkerlabs/login")

        maquina = Machine.query.filter_by(id=machine_id, origen="bunker").first()
        if not maquina:
            return RedirectResponse(url="/bunkerlabs", status_code=302)

        # Mismo criterio que la home: el invitado solo descarga las marcadas con guest_access
        if session.get("bunkerlabs_guest") and not maquina.guest_access:
            return RedirectResponse(url="/bunkerlabs?maquina=" + quote(maquina.nombre, safe=""), status_code=302)

        # Incremento atomico en SQL (no leer-y-escribir en Python): con
        # concurrencia alta en maquinas populares, leer el valor y volver a
        # escribirlo chocaba con el snapshot isolation de MariaDB y lanzaba
        # "Error 1020: Record has changed since last read", tirando la
        # pagina de descarga con un 500.
        from dockerlabs.traffic import is_human_navigation
        if is_human_navigation(request):
            db.session.query(Machine).filter(Machine.id == maquina.id).update(
                {Machine.descargas: func.coalesce(Machine.descargas, 0) + 1},
                synchronize_session=False,
            )
            db.session.add(MachineDownloadLog(machine_id=maquina.id))
            db.session.commit()

        csrf_token = session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            session["csrf_token"] = csrf_token
        return templates.TemplateResponse(
            request,
            "bunkerlabs/descargar.html",
            {
                "maquina": maquina,
                "session": session,
                "url_for": url_for,
                "current_user_role": session.get("role", ""),
                "csrf_token_value": csrf_token,
            },
        )
