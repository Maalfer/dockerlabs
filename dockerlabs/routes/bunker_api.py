from typing import List

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from bunkerlabs.models import BunkerAccessLog
import logging

logger = logging.getLogger(__name__)


class BunkerAccessLogEntry(BaseModel):
    nombre: str
    fecha: str


class BunkerAccessLogsResponse(BaseModel):
    logs: List[BunkerAccessLogEntry]
    total: int = 0


MAX_LOGS = 300  # el historial puede tener miles de entradas: se devuelven las más recientes


def register_bunker_api_routes(api_router, get_session, verify_csrf_token, db):
    @api_router.get("/bunker/logs/{token_id}", response_model=BunkerAccessLogsResponse)
    def api_get_bunker_access_logs(request: Request, token_id: int, session: dict = Depends(get_session)):
        role = session.get("role", "")
        if role != "admin":
            raise HTTPException(status_code=403, detail="Acceso denegado")

        consulta = BunkerAccessLog.query.filter_by(token_id=token_id)
        total = consulta.count()
        logs = consulta.order_by(BunkerAccessLog.accessed_at.desc(), BunkerAccessLog.id.desc()).limit(MAX_LOGS).all()
        result = []
        for log in logs:
            fecha = log.accessed_at.strftime("%d-%m-%Y %H:%M:%S") if log.accessed_at else "-"
            result.append({"nombre": log.user_nombre, "fecha": fecha})
        return {"logs": result, "total": total}

    @api_router.delete("/bunker/logs/{token_id}")
    def api_delete_bunker_access_logs(
        request: Request,
        token_id: int,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        role = session.get("role", "")
        if role != "admin":
            raise HTTPException(status_code=403, detail="Acceso denegado")

        try:
            borrados = BunkerAccessLog.query.filter_by(token_id=token_id).delete()
            db.session.commit()
            return {"message": "Historial eliminado correctamente", "eliminados": borrados}
        except Exception:
            logger.exception("Error inesperado en api_delete_bunker_access_logs")
            db.session.rollback()
            raise HTTPException(status_code=500, detail="Error al eliminar el historial")
