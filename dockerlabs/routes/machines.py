import secrets
from typing import Optional

from fastapi import Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from dockerlabs.models import Category, CompletedMachine, Machine, MachineClaim, MachineEditRequest, User

limiter = None

def configure_limiter(global_limiter):
    """Configura el limiter global desde asgi.py"""
    global limiter
    limiter = global_limiter


class ActualizarMaquinaRequest(BaseModel):
    id: int
    origen: str
    nombre: str
    dificultad: str
    autor: str
    enlace_autor: Optional[str] = ""
    fecha: str
    imagen: Optional[str] = ""
    descripcion: str
    link_descarga: str
    categoria: Optional[str] = ""


class ReclamarMaquinaRequest(BaseModel):
    maquina_nombre: str
    contacto: str
    prueba: str


class AddMaquinaRequest(BaseModel):
    nombre: str
    dificultad: Optional[str] = ""
    autor: str
    fecha: str
    descripcion: str
    link_descarga: str
    imagen: Optional[str] = ""
    destino: Optional[str] = "docker"
    pin: Optional[str] = ""
    entorno_real: Optional[bool] = False
    categoria: Optional[str] = ""


def _difficulty_to_color_clase(dificultad: str):
    d = dificultad.strip().lower()
    if "muy" in d:
        return "muy-facil", "Muy Fácil", "#43959b"
    elif "facil" in d or "fácil" in d:
        return "facil", "Fácil", "#8bc34a"
    elif "medio" in d:
        return "medio", "Medio", "#e0a553"
    else:
        return "dificil", "Difícil", "#d83c31"


def register_machine_routes(
    api_router,
    pages_router,
    get_flask_session,
    verify_csrf_token,
    require_auth_and_role,
    set_flask_session_cookie,
    templates,
    alchemy_db,
    url_for,
):
    @api_router.post("/gestion-maquinas/actualizar")
    async def api_actualizar_maquina(
        request: Request,
        id: int = Form(...),
        origen: str = Form(...),
        nombre: str = Form(...),
        dificultad: str = Form(...),
        autor: str = Form(...),
        enlace_autor: str = Form(""),
        fecha: str = Form(...),
        imagen: str = Form(""),
        descripcion: str = Form(...),
        link_descarga: str = Form(...),
        categoria: str = Form(""),
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """API: Actualizar datos de una máquina."""
        role = flask_session.get("role", "")
        username = (flask_session.get("username") or "").strip()
        user_id = flask_session.get("user_id")

        if not user_id:
            return JSONResponse(status_code=401, content={"error": "No autenticado"})
        if origen not in ("docker", "bunker"):
            return JSONResponse(status_code=400, content={"error": "Origen inválido"})

        clase, dificultad_texto, color = _difficulty_to_color_clase(dificultad)

        maquina = Machine.query.get(id)
        if not maquina:
            return JSONResponse(status_code=404, content={"error": "Máquina no encontrada"})

        if role not in ("admin", "moderador"):
            if role == "jugador" and maquina.autor == username:
                import json as _json

                nuevos_datos = _json.dumps(
                    {
                        "nombre": nombre,
                        "dificultad": dificultad_texto,
                        "clase": clase,
                        "color": color,
                        "autor": autor,
                        "enlace_autor": enlace_autor,
                        "fecha": fecha,
                        "imagen": imagen,
                        "descripcion": descripcion,
                        "link_descarga": link_descarga,
                    }
                )
                try:
                    edit_req = MachineEditRequest(
                        machine_id=id,
                        origen=origen,
                        autor=username,
                        nuevos_datos=nuevos_datos,
                        estado="pendiente",
                    )
                    alchemy_db.session.add(edit_req)
                    alchemy_db.session.commit()
                    return {"success": True, "message": "Solicitud de edición enviada para revisión"}
                except Exception as e:
                    alchemy_db.session.rollback()
                    return JSONResponse(status_code=500, content={"error": str(e)})
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        try:
            maquina.nombre = nombre
            maquina.dificultad = dificultad_texto
            maquina.clase = clase
            maquina.color = color
            maquina.autor = autor
            maquina.enlace_autor = enlace_autor or ""
            maquina.fecha = fecha
            maquina.imagen = imagen or ""
            maquina.descripcion = descripcion
            maquina.link_descarga = link_descarga
            alchemy_db.session.commit()

            cat_obj = Category.query.filter_by(machine_id=id, origen=origen).first()
            if categoria:
                if cat_obj:
                    cat_obj.categoria = categoria
                else:
                    alchemy_db.session.add(Category(machine_id=id, origen=origen, categoria=categoria))
            else:
                if cat_obj:
                    alchemy_db.session.delete(cat_obj)
            alchemy_db.session.commit()

            if origen == "docker":
                from dockerlabs.maquinas import recalcular_ranking_creadores

                recalcular_ranking_creadores()

            return {"success": True, "message": "Máquina actualizada correctamente"}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})

    @api_router.post("/gestion-maquinas/eliminar")
    async def api_eliminar_maquina(
        request: Request,
        id: int = Form(...),
        origen: str = Form(...),
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """API: Eliminar una máquina. Solo admin/moderador."""
        role = flask_session.get("role", "")
        user_id = flask_session.get("user_id")
        if not user_id or role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
        if origen not in ("docker", "bunker"):
            return JSONResponse(status_code=400, content={"error": "Origen inválido"})

        maquina = Machine.query.get(id)
        if not maquina:
            return JSONResponse(status_code=404, content={"error": "Máquina no encontrada"})
        try:
            if origen == "bunker":
                from bunkerlabs.models import BunkerSolve

                BunkerSolve.query.filter_by(machine_id=id).delete()
            alchemy_db.session.delete(maquina)
            alchemy_db.session.commit()
            if origen == "docker":
                from dockerlabs.maquinas import recalcular_ranking_creadores

                recalcular_ranking_creadores()
            return {"success": True, "message": "Máquina eliminada correctamente"}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})

    @pages_router.get("/add-maquina", response_class=HTMLResponse)
    def add_maquina_page_get(request: Request, flask_session: dict = Depends(get_flask_session)):
        """Página de añadir máquina. Solo admin."""
        ok, redir = require_auth_and_role(flask_session, ["admin"])
        if not ok:
            return redir
        current_user_role = flask_session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/info/add-maquina.html",
            {"error": None, "session": flask_session, "url_for": url_for, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @api_router.post("/add-maquina")
    async def api_add_maquina(
        request: Request,
        data: AddMaquinaRequest,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """API: Añadir una nueva máquina. Solo admin."""
        role = flask_session.get("role", "")
        user_id = flask_session.get("user_id")
        if not user_id or role != "admin":
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        if not User.query.filter_by(username=data.autor).first():
            return JSONResponse(status_code=400, content={"error": "El autor no es un usuario registrado"})

        try:
            from datetime import datetime as _dt

            fecha = _dt.strptime(data.fecha, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return JSONResponse(status_code=400, content={"error": "Formato de fecha inválido (YYYY-MM-DD)"})

        user_obj = User.query.get(user_id)
        enlace_autor = ""
        if user_obj:
            enlace_autor = user_obj.youtube_url or user_obj.github_url or user_obj.linkedin_url or ""

        imagen = data.imagen or "dockerlabs/images/logos/logo.png"

        if data.destino == "bunker" and data.entorno_real:
            clase, dificultad_texto, color = "real", "Real", "#ffffff"
        else:
            clase, dificultad_texto, color = _difficulty_to_color_clase(data.dificultad)

        try:
            new_machine = Machine(
                nombre=data.nombre,
                dificultad=dificultad_texto,
                clase=clase,
                color=color,
                autor=data.autor,
                enlace_autor=enlace_autor,
                fecha=fecha,
                imagen=imagen,
                descripcion=data.descripcion,
                link_descarga=data.link_descarga,
                pin=data.pin if data.destino == "bunker" else None,
                origen=data.destino or "docker",
            )
            alchemy_db.session.add(new_machine)
            alchemy_db.session.commit()
            if data.destino == "docker":
                from dockerlabs.maquinas import recalcular_ranking_creadores

                recalcular_ranking_creadores()
            redirect_url = "/bunkerlabs" if data.destino == "bunker" else "/"
            return {"success": True, "message": "Máquina añadida correctamente", "redirect_url": redirect_url}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})

    @api_router.post("/reclamar-maquina")
    async def api_reclamar_maquina(
        request: Request,
        data: ReclamarMaquinaRequest,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """API: Reclamar autoría de una máquina."""
        user_id = flask_session.get("user_id")
        username = (flask_session.get("username") or "").strip()
        role = flask_session.get("role", "")
        if not user_id or role not in ("jugador", "admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        try:
            alchemy_db.session.add(
                MachineClaim(
                    user_id=user_id,
                    username=username,
                    maquina_nombre=data.maquina_nombre,
                    contacto=data.contacto,
                    prueba=data.prueba,
                    estado="pendiente",
                )
            )
            alchemy_db.session.commit()
            return {"success": True, "message": "Reclamación enviada correctamente"}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})

    @api_router.post("/claims/{claim_id}/approve")
    async def api_approve_claim(
        request: Request,
        claim_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """API: Aprobar reclamación de máquina. Solo admin."""
        ok, _ = require_auth_and_role(flask_session, ["admin"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
        claim = MachineClaim.query.get(claim_id)
        if not claim:
            return JSONResponse(status_code=404, content={"error": "No encontrada"})
        try:
            maquina = Machine.query.filter_by(nombre=claim.maquina_nombre).first()
            if maquina:
                maquina.autor = claim.username
            claim.estado = "aprobada"
            alchemy_db.session.commit()
            from dockerlabs.maquinas import recalcular_ranking_creadores

            recalcular_ranking_creadores()
            return {"success": True}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})

    @api_router.post("/claims/{claim_id}/reject")
    async def api_reject_claim(
        request: Request,
        claim_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """API: Rechazar reclamación. Solo admin."""
        ok, _ = require_auth_and_role(flask_session, ["admin"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
        claim = MachineClaim.query.get(claim_id)
        if not claim:
            return JSONResponse(status_code=404, content={"error": "No encontrada"})
        try:
            alchemy_db.session.delete(claim)
            alchemy_db.session.commit()
            return {"success": True}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})

    @api_router.post("/claims/{claim_id}/revert")
    async def api_revert_claim(
        request: Request,
        claim_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """API: Revertir reclamación a pendiente. Admin/moderador."""
        ok, _ = require_auth_and_role(flask_session, ["admin", "moderador"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
        claim = MachineClaim.query.get(claim_id)
        if not claim:
            return JSONResponse(status_code=404, content={"error": "No encontrada"})
        claim.estado = "pendiente"
        alchemy_db.session.commit()
        return {"success": True}

    @api_router.post("/machine-edit-requests/{request_id}/approve")
    async def api_approve_machine_edit(
        request: Request,
        request_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """API: Aprobar edición de máquina. Admin/moderador."""
        ok, _ = require_auth_and_role(flask_session, ["admin", "moderador"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
        req = MachineEditRequest.query.get(request_id)
        if not req:
            return JSONResponse(status_code=404, content={"error": "No encontrada"})
        try:
            import json as _json

            nuevos = _json.loads(req.nuevos_datos)
        except Exception:
            nuevos = {}
        maquina = Machine.query.get(req.machine_id)
        if maquina:
            for field in (
                "nombre",
                "dificultad",
                "clase",
                "color",
                "autor",
                "enlace_autor",
                "fecha",
                "imagen",
                "descripcion",
                "link_descarga",
            ):
                val = nuevos.get(field)
                if val:
                    setattr(maquina, field, val)
            alchemy_db.session.commit()
            if req.origen == "docker":
                from dockerlabs.maquinas import recalcular_ranking_creadores

                recalcular_ranking_creadores()
        req.estado = "aprobada"
        alchemy_db.session.commit()
        return {"success": True}

    @api_router.post("/machine-edit-requests/{request_id}/reject")
    async def api_reject_machine_edit(
        request: Request,
        request_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """API: Rechazar edición de máquina. Admin/moderador."""
        ok, _ = require_auth_and_role(flask_session, ["admin", "moderador"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
        req = MachineEditRequest.query.get(request_id)
        if not req:
            return JSONResponse(status_code=404, content={"error": "No encontrada"})
        req.estado = "rechazada"
        alchemy_db.session.commit()
        return {"success": True}

    @api_router.post("/machine-edit-requests/{request_id}/revert")
    async def api_revert_machine_edit(
        request: Request,
        request_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """API: Revertir edición a pendiente. Admin/moderador."""
        ok, _ = require_auth_and_role(flask_session, ["admin", "moderador"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
        req = MachineEditRequest.query.get(request_id)
        if not req:
            return JSONResponse(status_code=404, content={"error": "No encontrada"})
        req.estado = "pendiente"
        alchemy_db.session.commit()
        return {"success": True}

    @pages_router.get("/maquinas-hechas", response_class=HTMLResponse)
    def maquinas_hechas_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        """Página de máquinas completadas por el usuario."""
        user_id = flask_session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/login", status_code=302)

        results = (
            alchemy_db.session.query(
                CompletedMachine.machine_name,
                CompletedMachine.completed_at,
                Machine.id,
                Machine.dificultad,
                Machine.color,
                Machine.imagen,
                Machine.clase,
                Machine.autor,
            )
            .outerjoin(Machine, CompletedMachine.machine_name == Machine.nombre)
            .filter(CompletedMachine.user_id == user_id)
            .order_by(CompletedMachine.completed_at.desc())
            .all()
        )

        completed_machines = []
        for row in results:
            completed_machines.append(
                {
                    "machine_name": row.machine_name,
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                    "machine_id": row.id,
                    "machine_logo_url": f"/img/maquina/{row.id}" if row.id else "/static/dockerlabs/images/logos/logo.png",
                    "dificultad": row.dificultad,
                    "color": row.color,
                    "imagen": row.imagen,
                    "clase": row.clase,
                    "autor": row.autor,
                }
            )

        total_machines = Machine.query.filter_by(origen="docker").count()
        completed_count = len(completed_machines)
        completion_percentage = round((completed_count / total_machines * 100), 1) if total_machines > 0 else 0

        current_user_role = flask_session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/user/maquinas_hechas.html",
            {
                "completed_machines": completed_machines,
                "total_machines": total_machines,
                "completed_count": completed_count,
                "completion_percentage": completion_percentage,
                "session": flask_session,
                "url_for": url_for,
                "current_user_role": current_user_role,
                "g": {"csp_nonce": secrets.token_urlsafe(32)},
            },
        )

