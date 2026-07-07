from typing import List, Optional

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from bunkerlabs.models import BunkerAccessLog


class BunkerAccessLogEntry(BaseModel):
    nombre: str
    fecha: str


class BunkerAccessLogsResponse(BaseModel):
    logs: List[BunkerAccessLogEntry]


def register_bunker_api_routes(api_router, get_session, verify_csrf_token, db):
    @api_router.get("/bunker/logs/{token_id}", response_model=BunkerAccessLogsResponse)
    def api_get_bunker_access_logs(request: Request, token_id: int, session: dict = Depends(get_session)):
        role = session.get("role", "")
        if role != "admin":
            raise HTTPException(status_code=403, detail="Acceso denegado")

        logs = BunkerAccessLog.query.filter_by(token_id=token_id).order_by(BunkerAccessLog.accessed_at.desc()).all()
        result = []
        for log in logs:
            result.append({"nombre": log.user_nombre, "fecha": log.accessed_at.strftime("%d-%m-%Y %H:%M:%S")})
        return {"logs": result}

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
            BunkerAccessLog.query.filter_by(token_id=token_id).delete()
            db.session.commit()
            return {"message": "Historial eliminado correctamente"}
        except Exception:
            db.session.rollback()
            raise HTTPException(status_code=500, detail="Error al eliminar el historial")
