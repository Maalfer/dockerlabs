from datetime import datetime
from typing import List, Optional

from fastapi import Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func

from dockerlabs.models import Machine, PendingWriteup, User, Writeup, WriteupAnalysisResult, WriteupEditRequest, WriteupRanking, WriteupReport


class SubmitWriteupRequest(BaseModel):
    maquina: str
    url: str
    tipo: str


class UpdateWriteupRequest(BaseModel):
    url: str
    tipo: str


class UpdateWriteupRecibidoRequest(BaseModel):
    maquina: str
    autor: str
    url: str
    tipo: str


class ReportWriteupRequest(BaseModel):
    reason: Optional[str] = "Sin motivo especificado"


class WriteupItem(BaseModel):
    id: int
    maquina: str
    autor: str
    url: str
    tipo: str
    created_at: Optional[datetime] = None


class MaquinaWriteupItem(BaseModel):
    maquina: str
    total: int
    imagen: Optional[str] = None


class MaquinasWriteupsResponse(BaseModel):
    maquinas: List[MaquinaWriteupItem]


def register_writeup_routes(api_router, get_flask_session, verify_csrf_token, alchemy_db):
    @api_router.post("/submit_writeup")
    async def api_submit_writeup(
        request: Request,
        data: SubmitWriteupRequest,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        import logging
        logger = logging.getLogger(__name__)

        user_id = flask_session.get("user_id")
        autor = flask_session.get("username", "").strip()
        logger.info(f"Submit writeup attempt - user_id: {user_id}, autor: {autor}, maquina: {data.maquina}")

        if not user_id or not autor:
            logger.warning(f"Submit writeup failed - no user_id or autor: user_id={user_id}, autor={autor}")
            return JSONResponse(status_code=403, content={"error": "Debes iniciar sesión"})

        maquina = data.maquina.strip()
        url = data.url.strip()
        tipo = data.tipo.strip().lower()

        logger.info(f"Validating writeup data - maquina: {maquina}, url: {url}, tipo: {tipo}")

        from dockerlabs import validators

        valid, err = validators.validate_machine_name(maquina)
        if not valid:
            logger.warning(f"Machine name validation failed: {err}")
            return JSONResponse(status_code=400, content={"error": f"Campo 'maquina' inválido: {err}"})
        valid, err = validators.validate_url(url)
        if not valid:
            logger.warning(f"URL validation failed: {err}")
            return JSONResponse(status_code=400, content={"error": f"URL inválida: {err}"})
        valid, err = validators.validate_writeup_type(tipo)
        if not valid:
            logger.warning(f"Writeup type validation failed: {err}")
            return JSONResponse(status_code=400, content={"error": f"Tipo inválido: {err}"})

        tipo = "video" if tipo == "video" else "texto"

        machine = Machine.query.filter_by(nombre=maquina).first()
        if not machine:
            logger.warning(f"Machine not found: {maquina}")
            return JSONResponse(status_code=400, content={"error": "La máquina especificada no existe"})
        try:
            new_pending = PendingWriteup(maquina=maquina, autor=autor, url=url, tipo=tipo)
            alchemy_db.session.add(new_pending)
            alchemy_db.session.commit()
            logger.info(f"Writeup submitted successfully - autor={autor}, maquina={maquina}")
            return {"message": "Writeup enviado correctamente"}
        except Exception as e:
            alchemy_db.session.rollback()
            logger.error(f"Error saving writeup: {str(e)}", exc_info=True)
            return JSONResponse(status_code=500, content={"error": f"Error al guardar: {str(e)}"})

    @api_router.post("/writeups/recibidos/aprobar-todos")
    async def api_approve_all_writeups_recibidos(
        request: Request,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        caller_role = flask_session.get("role", "")
        if caller_role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        alchemy_db.session.rollback()

        try:
            pending_list = PendingWriteup.query.order_by(PendingWriteup.id.asc()).all()
            if not pending_list:
                return {"message": "No hay writeups pendientes.", "aprobados": 0}

            aprobados = 0
            seen = set()  # deduplicate within this batch
            for pending in pending_list:
                autor_real = pending.autor
                usuario = User.query.filter(func.lower(User.username) == func.lower(autor_real)).first()
                if usuario:
                    autor_real = usuario.username

                key = (pending.maquina, autor_real, pending.url)
                already_published = Writeup.query.filter_by(maquina=pending.maquina, autor=autor_real, url=pending.url).first()
                if not already_published and key not in seen:
                    alchemy_db.session.add(Writeup(maquina=pending.maquina, autor=autor_real, url=pending.url, tipo=pending.tipo))
                    seen.add(key)

                alchemy_db.session.delete(pending)
                aprobados += 1

            alchemy_db.session.commit()

            from dockerlabs.writeups import recalcular_ranking_writeups
            recalcular_ranking_writeups()

            return {"message": f"{aprobados} writeup(s) aprobado(s) correctamente.", "aprobados": aprobados}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": f"Error al aprobar todos: {str(e)}"})

    @api_router.post("/writeups/recibidos/{writeup_id}/aprobar")
    async def api_approve_writeup_recibido(
        request: Request,
        writeup_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        caller_role = flask_session.get("role", "")
        if caller_role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        alchemy_db.session.rollback()

        try:
            pending = PendingWriteup.query.get(writeup_id)
            if not pending:
                return JSONResponse(status_code=404, content={"error": "Writeup no encontrado"})

            autor_real = pending.autor
            usuario = User.query.filter(func.lower(User.username) == func.lower(autor_real)).first()
            if usuario:
                autor_real = usuario.username

            if not Writeup.query.filter_by(maquina=pending.maquina, autor=autor_real, url=pending.url).first():
                new_writeup = Writeup(maquina=pending.maquina, autor=autor_real, url=pending.url, tipo=pending.tipo)
                alchemy_db.session.add(new_writeup)

            alchemy_db.session.delete(pending)
            alchemy_db.session.commit()

            from dockerlabs.writeups import recalcular_ranking_writeups

            recalcular_ranking_writeups()
            return {"message": "Writeup aprobado y movido a publicados."}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": f"Error al aprobar: {str(e)}"})

    @api_router.post("/writeups/edit-requests/{request_id}/approve")
    async def api_approve_writeup_edit(
        request: Request,
        request_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        caller_role = flask_session.get("role", "")
        if caller_role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        req = WriteupEditRequest.query.get(request_id)
        if not req or req.estado != "pendiente":
            return JSONResponse(status_code=404, content={"error": "Petición no encontrada o ya procesada"})

        writeup = Writeup.query.get(req.writeup_id)
        if not writeup:
            return JSONResponse(status_code=404, content={"error": "Writeup original no encontrado"})

        try:
            writeup.maquina = req.maquina_nueva or writeup.maquina
            writeup.autor = req.autor_nuevo or writeup.autor
            writeup.url = req.url_nueva or writeup.url
            writeup.tipo = req.tipo_nuevo or writeup.tipo
            req.estado = "aprobada"
            alchemy_db.session.commit()
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": f"Error al aprobar edición: {str(e)}"})

        from dockerlabs.writeups import recalcular_ranking_writeups

        recalcular_ranking_writeups()
        return {"message": "Petición de edición aprobada.", "success": True}

    @api_router.post("/writeups/edit-requests/{request_id}/reject")
    async def api_reject_writeup_edit(
        request: Request,
        request_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        caller_role = flask_session.get("role", "")
        if caller_role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        req = WriteupEditRequest.query.get(request_id)
        if req:
            try:
                req.estado = "rechazada"
                alchemy_db.session.commit()
            except Exception as e:
                alchemy_db.session.rollback()
                return JSONResponse(status_code=500, content={"error": f"Error al rechazar: {str(e)}"})
        return {"message": "Petición rechazada.", "success": True}

    @api_router.post("/writeups/edit-requests/{request_id}/revert")
    async def api_revert_writeup_edit(
        request: Request,
        request_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        caller_role = flask_session.get("role", "")
        if caller_role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        req = WriteupEditRequest.query.get(request_id)
        if req:
            try:
                req.estado = "pendiente"
                alchemy_db.session.commit()
            except Exception as e:
                alchemy_db.session.rollback()
                return JSONResponse(status_code=500, content={"error": f"Error al revertir: {str(e)}"})
        return {"message": "Petición revertida a pendiente.", "success": True}

    @api_router.post("/writeups/subidos/{writeup_id}/update")
    async def api_update_writeup_subido(
        request: Request,
        writeup_id: int,
        data: UpdateWriteupRequest,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        user_id = flask_session.get("user_id")
        username = flask_session.get("username", "").strip()
        caller_role = flask_session.get("role", "")
        if not user_id:
            return JSONResponse(status_code=403, content={"error": "Debes iniciar sesión."})

        from dockerlabs import validators

        valid, err = validators.validate_url(data.url)
        if not valid:
            return JSONResponse(status_code=400, content={"error": f"URL inválida: {err}"})
        valid, err = validators.validate_writeup_type(data.tipo)
        if not valid:
            return JSONResponse(status_code=400, content={"error": f"Tipo inválido: {err}"})

        writeup = Writeup.query.get(writeup_id)
        if not writeup:
            return JSONResponse(status_code=404, content={"error": "Writeup no encontrado"})

        maquina_db = (writeup.maquina or "").strip()
        autor_db = (writeup.autor or "").strip()

        if caller_role in ("admin", "moderador"):
            try:
                writeup.url = data.url
                writeup.tipo = data.tipo
                alchemy_db.session.commit()
                from dockerlabs.writeups import recalcular_ranking_writeups

                recalcular_ranking_writeups()
                return {"message": "Writeup actualizado correctamente"}
            except Exception as e:
                alchemy_db.session.rollback()
                return JSONResponse(status_code=500, content={"error": str(e)})

        if not username or username.lower() != autor_db.lower():
            return JSONResponse(status_code=403, content={"error": "No tienes permiso para modificar este writeup."})

        try:
            edit_request = WriteupEditRequest(
                writeup_id=writeup.id,
                user_id=user_id,
                username=username,
                maquina_original=maquina_db,
                autor_original=autor_db,
                url_original=writeup.url,
                tipo_original=writeup.tipo,
                maquina_nueva=maquina_db,
                autor_nuevo=autor_db,
                url_nueva=data.url,
                tipo_nuevo=data.tipo,
            )
            alchemy_db.session.add(edit_request)
            alchemy_db.session.commit()
            return {"message": "Tu petición de cambio ha sido enviada para revisión."}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})

    @api_router.post("/writeups/subidos/{writeup_id}/delete")
    async def api_delete_writeup_subido(
        request: Request,
        writeup_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        caller_role = flask_session.get("role", "")
        if caller_role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        writeup = Writeup.query.get(writeup_id)
        if not writeup:
            return JSONResponse(status_code=404, content={"error": "Writeup no encontrado"})
        alchemy_db.session.delete(writeup)
        alchemy_db.session.commit()
        from dockerlabs.writeups import recalcular_ranking_writeups

        recalcular_ranking_writeups()
        return {"message": "Writeup eliminado correctamente"}

    @api_router.delete("/writeups_subidos/{writeup_id}")
    async def api_delete_writeup_subido_delete(
        request: Request,
        writeup_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        caller_role = flask_session.get("role", "")
        if caller_role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        writeup = Writeup.query.get(writeup_id)
        if not writeup:
            return JSONResponse(status_code=404, content={"error": "Writeup no encontrado"})
        try:
            alchemy_db.session.delete(writeup)
            alchemy_db.session.commit()
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": f"Error al eliminar: {str(e)}"})
        from dockerlabs.writeups import recalcular_ranking_writeups

        recalcular_ranking_writeups()
        return {"message": "Writeup eliminado correctamente"}

    @api_router.post("/writeups/recibidos/{writeup_id}/update")
    async def api_update_writeup_recibido(
        request: Request,
        writeup_id: int,
        data: UpdateWriteupRecibidoRequest,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        caller_role = flask_session.get("role", "")
        if caller_role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        from dockerlabs import validators

        for val_fn, field in [
            (validators.validate_machine_name, data.maquina),
            (validators.validate_author_name, data.autor),
            (validators.validate_url, data.url),
            (validators.validate_writeup_type, data.tipo),
        ]:
            valid, err = val_fn(field)
            if not valid:
                return JSONResponse(status_code=400, content={"error": err})

        pending = PendingWriteup.query.get(writeup_id)
        if not pending:
            return JSONResponse(status_code=404, content={"error": "Writeup no encontrado"})
        try:
            pending.maquina = data.maquina
            pending.autor = data.autor
            pending.url = data.url
            pending.tipo = data.tipo
            alchemy_db.session.commit()
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": f"Error al actualizar: {str(e)}"})
        return {"message": "Writeup actualizado correctamente"}

    @api_router.post("/writeups/recibidos/{writeup_id}/delete")
    async def api_delete_writeup_recibido(
        request: Request,
        writeup_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        caller_role = flask_session.get("role", "")
        if caller_role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        pending = PendingWriteup.query.get(writeup_id)
        if not pending:
            return JSONResponse(status_code=404, content={"error": "Writeup no encontrado"})
        try:
            alchemy_db.session.delete(pending)
            alchemy_db.session.commit()
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": f"Error al eliminar: {str(e)}"})
        return {"message": "Writeup eliminado correctamente"}

    @api_router.delete("/writeups/recibidos/{writeup_id}")
    async def api_delete_writeup_recibido_delete(
        request: Request,
        writeup_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        caller_role = flask_session.get("role", "")
        if caller_role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        pending = PendingWriteup.query.get(writeup_id)
        if not pending:
            return JSONResponse(status_code=404, content={"error": "Writeup no encontrado"})
        try:
            alchemy_db.session.delete(pending)
            alchemy_db.session.commit()
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": f"Error al eliminar: {str(e)}"})
        return {"message": "Writeup eliminado correctamente"}

    @api_router.get("/writeups/{maquina_nombre}")
    def api_writeups_maquina(request: Request, maquina_nombre: str, flask_session: dict = Depends(get_flask_session)):
        results = (
            alchemy_db.session.query(Writeup.id, Writeup.autor, Writeup.url, Writeup.tipo, User.id)
            .outerjoin(User, func.lower(User.username) == func.lower(Writeup.autor))
            .filter(Writeup.maquina == maquina_nombre)
            .order_by(Writeup.created_at.desc(), Writeup.id.desc())
            .all()
        )

        writeups = []
        for wid, autor, url, tipo, uid in results:
            tipo_raw = (tipo or "").strip().lower()
            tipo_emoji = "🎥" if tipo_raw == "video" else "📝"
            writeups.append({"id": wid, "name": autor, "url": url, "type": tipo_emoji, "es_usuario_registrado": bool(uid)})
        return writeups

    @api_router.post("/writeups/{writeup_id}/report")
    def api_report_writeup(request: Request, writeup_id: int, data: ReportWriteupRequest, flask_session: dict = Depends(get_flask_session)):
        user_id = flask_session.get("user_id")
        if not user_id:
            return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión para reportar"})

        if not Writeup.query.get(writeup_id):
            return JSONResponse(status_code=404, content={"error": "Writeup no encontrado"})
        try:
            report = WriteupReport(writeup_id=writeup_id, reporter_id=user_id, reason=data.reason)
            alchemy_db.session.add(report)
            alchemy_db.session.commit()
            return {"message": "Reporte enviado correctamente"}
        except Exception:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": "Error al guardar el reporte"})

    @api_router.post("/writeups/reports/{report_id}/ignore")
    async def api_ignore_report(
        request: Request,
        report_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        caller_role = flask_session.get("role", "")
        if caller_role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        report = WriteupReport.query.get(report_id)
        if report:
            alchemy_db.session.delete(report)
            alchemy_db.session.commit()
        return {"message": "Reporte ignorado/eliminado correctamente"}

    @api_router.get("/admin/writeup_reports")
    def api_get_reports(request: Request, flask_session: dict = Depends(get_flask_session)):
        caller_role = flask_session.get("role", "")
        if caller_role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        reports_orm = WriteupReport.query.order_by(WriteupReport.created_at.desc()).all()
        reports = []
        for r in reports_orm:
            writeup_data = {}
            if r.writeup:
                writeup_data = {
                    "id": r.writeup.id,
                    "autor": r.writeup.autor,
                    "maquina": r.writeup.maquina,
                    "url": r.writeup.url,
                    "tipo": r.writeup.tipo,
                }
            reports.append(
                {
                    "id": r.id,
                    "reason": r.reason,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "reporter_name": r.reporter.username if r.reporter else "Unknown",
                    "writeup": writeup_data,
                }
            )
        return reports

    @api_router.get("/writeups/recibidos/list")
    def api_list_writeups_recibidos(request: Request, flask_session: dict = Depends(get_flask_session)):
        caller_role = flask_session.get("role", "")
        username = (flask_session.get("username") or "").strip()

        query = (
            alchemy_db.session.query(PendingWriteup, Machine.id, Machine.imagen)
            .outerjoin(Machine, PendingWriteup.maquina == Machine.nombre)
        )

        if caller_role not in ("admin", "moderador"):
            if not username:
                return JSONResponse(status_code=401, content=[])
            query = query.filter(PendingWriteup.autor == username)

        results = query.order_by(PendingWriteup.created_at.desc(), PendingWriteup.id.desc()).all()

        writeups = []
        for pw, machine_id, imagen in results:
            image_url = f"/img/maquina/{machine_id}" if machine_id else None
            writeups.append(
                {
                    "id": pw.id,
                    "maquina": pw.maquina,
                    "autor": pw.autor,
                    "url": pw.url,
                    "tipo": pw.tipo,
                    "created_at": pw.created_at.isoformat() if pw.created_at else None,
                    "imagen": image_url,
                }
            )
        return writeups

    @api_router.get("/author_profile")
    def api_author_profile(request: Request, nombre: str, flask_session: dict = Depends(get_flask_session)):
        if not nombre:
            return JSONResponse(status_code=400, content={"error": "Nombre requerido"})

        from dockerlabs.auth import get_profile_image_url

        maquinas_orm = Machine.query.filter_by(autor=nombre).order_by(Machine.fecha.desc()).all()
        maquinas = [{"nombre": m.nombre, "dificultad": m.dificultad, "imagen_url": f"/img/maquina/{m.id}"} for m in maquinas_orm]

        writeups_orm = Writeup.query.filter_by(autor=nombre).order_by(Writeup.created_at.desc()).all()
        writeups = [{"maquina": w.maquina, "url": w.url, "tipo": w.tipo} for w in writeups_orm]

        user = User.query.filter(func.lower(User.username) == func.lower(nombre)).first()
        user_id = user.id if user else None
        profile_image_url = get_profile_image_url(username=nombre, user_id=user_id)

        return {
            "nombre": nombre,
            "profile_image_url": profile_image_url,
            "maquinas": maquinas,
            "writeups": writeups,
            "biography": user.biography if user else None,
            "linkedin_url": user.linkedin_url if user else None,
            "github_url": user.github_url if user else None,
            "youtube_url": user.youtube_url if user else None,
        }

    @api_router.get("/writeups_subidos", response_model=List[WriteupItem])
    def api_list_writeups_subidos(
        request: Request,
        maquina: Optional[str] = None,
        filter_mode: Optional[str] = None,
        flask_session: dict = Depends(get_flask_session),
    ):
        user_id = flask_session.get("user_id")
        role = flask_session.get("role", "")
        username = (flask_session.get("username") or "").strip()

        query = Writeup.query

        if user_id and role in ["admin", "moderador"]:
            if filter_mode == "mine" and username:
                query = query.filter_by(autor=username)
            if maquina:
                query = query.filter_by(maquina=maquina)
        else:
            if maquina:
                query = query.filter_by(maquina=maquina)

        writeups_objs = query.order_by(Writeup.created_at.desc(), Writeup.id.desc()).all()

        result = []
        for w in writeups_objs:
            result.append(
                {
                    "id": w.id,
                    "maquina": w.maquina,
                    "autor": w.autor,
                    "url": w.url,
                    "tipo": w.tipo,
                    "created_at": w.created_at,
                }
            )

        return result


    @api_router.get("/writeups-analisis")
    async def api_analisis_writeups(
        request: Request,
        flask_session: dict = Depends(get_flask_session),
    ):
        """Comprueba el estado HTTP de todos los writeups publicados.
        Emite Server-Sent Events con progreso en tiempo real.
        El cliente puede cancelar cerrando la conexión."""
        import asyncio
        import httpx
        import json as _json

        caller_role = flask_session.get("role", "")
        if caller_role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        writeups = Writeup.query.order_by(Writeup.id.asc()).all()
        total = len(writeups)

        TIMEOUT = 10.0
        CONCURRENCY = 20
        USER_AGENT = "DockerLabs-WriteupChecker/1.0"

        async def event_generator():
            if total == 0:
                yield f"data: {_json.dumps({'type': 'complete', 'total_analizados': 0, 'total_rotos': 0, 'rotos': []})}\n\n"
                return

            sem = asyncio.Semaphore(CONCURRENCY)
            queue: asyncio.Queue = asyncio.Queue()

            async def check_url(w):
                async with sem:
                    # Anti-SSRF: no consultar URLs que resuelvan a hosts internos
                    from dockerlabs import validators as _v
                    _ok, _ = await asyncio.to_thread(_v.is_public_http_url, w.url)
                    if not _ok:
                        return None
                    try:
                        async with httpx.AsyncClient(
                            follow_redirects=True,
                            timeout=TIMEOUT,
                            headers={"User-Agent": USER_AGENT},
                        ) as client:
                            try:
                                resp = await client.head(w.url)
                                status = resp.status_code
                                if status == 405:
                                    resp = await client.get(w.url)
                                    status = resp.status_code
                            except Exception:
                                resp = await client.get(w.url)
                                status = resp.status_code
                            if status == 404:
                                return {"id": w.id, "maquina": w.maquina, "autor": w.autor, "url": w.url, "tipo": w.tipo, "status": status, "error": None}
                    except httpx.TimeoutException:
                        return None
                    except Exception as e:
                        return None
                    return None

            async def check_and_enqueue(w):
                result = await check_url(w)
                await queue.put(result)

            tasks = [asyncio.create_task(check_and_enqueue(w)) for w in writeups]
            checked = 0
            broken = []

            try:
                while checked < total:
                    if await request.is_disconnected():
                        for t in tasks:
                            t.cancel()
                        return

                    try:
                        result = await asyncio.wait_for(queue.get(), timeout=0.3)
                    except asyncio.TimeoutError:
                        continue

                    checked += 1
                    if result is not None:
                        broken.append(result)

                    percent = int(checked / total * 100)
                    yield f"data: {_json.dumps({'type': 'progress', 'checked': checked, 'total': total, 'percent': percent, 'broken_count': len(broken)})}\n\n"

                yield f"data: {_json.dumps({'type': 'complete', 'total_analizados': total, 'total_rotos': len(broken), 'rotos': broken})}\n\n"

                # Persistir resultados en BD para que sobrevivan recargas
                from datetime import datetime as _dt
                _analyzed_at = _dt.utcnow()
                try:
                    WriteupAnalysisResult.query.delete()
                    for _w in broken:
                        alchemy_db.session.add(WriteupAnalysisResult(
                            writeup_id=_w['id'],
                            maquina=_w['maquina'],
                            autor=_w['autor'],
                            url=_w['url'],
                            tipo=_w['tipo'],
                            status=_w.get('status'),
                            error=_w.get('error'),
                            dismissed=False,
                            analyzed_at=_analyzed_at,
                        ))
                    alchemy_db.session.commit()
                except Exception:
                    alchemy_db.session.rollback()

            except asyncio.CancelledError:
                for t in tasks:
                    t.cancel()

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @api_router.get("/writeups-analisis/results")
    async def api_analisis_results_saved(
        request: Request,
        flask_session: dict = Depends(get_flask_session),
    ):
        """Devuelve los resultados del último análisis guardados en BD."""
        caller_role = flask_session.get("role", "")
        if caller_role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        all_results = WriteupAnalysisResult.query.order_by(WriteupAnalysisResult.id.asc()).all()
        if not all_results:
            return JSONResponse(content={"has_results": False, "rotos": [], "analyzed_at": None,
                                         "total_analizados": 0, "total_dismissed": 0})

        analyzed_at = all_results[0].analyzed_at.isoformat() if all_results[0].analyzed_at else None
        total_analizados = Writeup.query.count()
        total_dismissed = sum(1 for r in all_results if r.dismissed)

        rotos = [
            {"id": r.writeup_id, "maquina": r.maquina, "autor": r.autor,
             "url": r.url, "tipo": r.tipo, "status": r.status, "error": r.error}
            for r in all_results if not r.dismissed and r.status == 404
        ]
        return JSONResponse(content={
            "has_results": True,
            "rotos": rotos,
            "analyzed_at": analyzed_at,
            "total_analizados": total_analizados,
            "total_dismissed": total_dismissed,
        })

    @api_router.post("/writeups-analisis/dismiss/{writeup_id}")
    async def api_analisis_dismiss(
        request: Request,
        writeup_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """Marca un resultado de análisis como falso positivo (lo oculta sin eliminar el writeup)."""
        caller_role = flask_session.get("role", "")
        if caller_role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        result = WriteupAnalysisResult.query.filter_by(writeup_id=writeup_id, dismissed=False).first()
        if not result:
            return JSONResponse(status_code=404, content={"error": "Resultado no encontrado"})
        result.dismissed = True
        try:
            alchemy_db.session.commit()
            return {"ok": True}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})

    @api_router.post("/writeups-analisis/delete-batch")
    async def api_delete_writeups_batch(
        request: Request,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """Elimina múltiples writeups publicados por ID."""
        caller_role = flask_session.get("role", "")
        if caller_role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        body = await request.json()
        ids = body.get("ids", [])
        if not ids or not isinstance(ids, list):
            return JSONResponse(status_code=400, content={"error": "Se requiere una lista de IDs"})

        try:
            deleted = 0
            for wid in ids:
                w = Writeup.query.get(int(wid))
                if w:
                    alchemy_db.session.delete(w)
                    deleted += 1
            # Limpiar también los resultados de análisis de los writeups eliminados
            for wid in ids:
                WriteupAnalysisResult.query.filter_by(writeup_id=int(wid)).delete()
            alchemy_db.session.commit()
            from dockerlabs.writeups import recalcular_ranking_writeups
            recalcular_ranking_writeups()
            return {"message": f"{deleted} writeup(s) eliminados correctamente", "deleted": deleted}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"error": f"Error al eliminar: {str(e)}"})

    @api_router.get("/writeups_subidos/maquinas", response_model=MaquinasWriteupsResponse)
    def api_list_maquinas_writeups_subidos(
        request: Request,
        filter_mode: Optional[str] = None,
        flask_session: dict = Depends(get_flask_session),
    ):
        user_id = flask_session.get("user_id")
        role = flask_session.get("role", "")
        username = (flask_session.get("username") or "").strip()

        query = (
            alchemy_db.session.query(Writeup.maquina, func.count().label("total"), Machine.imagen, Machine.logo_path, Machine.id)
            .outerjoin(Machine, Writeup.maquina == Machine.nombre)
            .filter(Writeup.maquina != None, Writeup.maquina != "")  # noqa: E711
        )

        if user_id and role in ["admin", "moderador"]:
            if filter_mode == "mine" and username:
                query = query.filter(Writeup.autor == username)

        results = query.group_by(Writeup.maquina, Machine.imagen, Machine.logo_path, Machine.id).order_by(func.lower(Writeup.maquina)).all()

        maquinas = []
        for maquina_nombre, total, imagen, logo_path, machine_id in results:
            imagen_url = None
            
            # Usar el endpoint dinámico que sirve desde el sistema correcto (nuevo o antiguo)
            if machine_id:
                imagen_url = f"/img/maquina/{machine_id}"
            # Fallback al sistema antiguo (imagen estática)
            elif imagen:
                imagen_rel = imagen.strip()
                if imagen_rel.startswith("dockerlabs/") or imagen_rel.startswith("bunkerlabs/"):
                    static_path = imagen_rel
                elif "/" in imagen_rel:
                    static_path = f"dockerlabs/images/{imagen_rel}"
                else:
                    static_path = f"dockerlabs/images/logos/{imagen_rel}"
                imagen_url = f"/static/{static_path}"

            maquinas.append({"maquina": maquina_nombre, "total": total, "imagen": imagen_url})

        return {"maquinas": maquinas}

