from typing import List, Optional

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from bunkerlabs.models import BunkerAccessToken
from dockerlabs.models import Machine


class BunkerAccessLogEntry(BaseModel):
    nombre: str
    fecha: str


class BunkerAccessLogsResponse(BaseModel):
    logs: List[BunkerAccessLogEntry]


class BunkerWriteupItem(BaseModel):
    id: int
    autor: str
    url: str
    tipo: str
    locked: bool
    created_at: Optional[str] = None


class BunkerWriteupsResponse(BaseModel):
    writeups: List[BunkerWriteupItem]


class ToggleLockResponse(BaseModel):
    message: str
    locked: bool


def register_bunker_api_routes(api_router, get_flask_session, verify_csrf_token, alchemy_db):
    @api_router.get("/bunker/logs/{token_id}", response_model=BunkerAccessLogsResponse)
    def api_get_bunker_access_logs(request: Request, token_id: int, flask_session: dict = Depends(get_flask_session)):
        role = flask_session.get("role", "")
        if role != "admin":
            raise HTTPException(status_code=403, detail="Acceso denegado")

        from bunkerlabs.models import BunkerAccessLog

        logs = BunkerAccessLog.query.filter_by(token_id=token_id).order_by(BunkerAccessLog.accessed_at.desc()).all()
        result = []
        for log in logs:
            result.append({"nombre": log.user_nombre, "fecha": log.accessed_at.strftime("%d-%m-%Y %H:%M:%S")})
        return {"logs": result}

    @api_router.delete("/bunker/logs/{token_id}")
    def api_delete_bunker_access_logs(
        request: Request,
        token_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        role = flask_session.get("role", "")
        if role != "admin":
            raise HTTPException(status_code=403, detail="Acceso denegado")

        from bunkerlabs.models import BunkerAccessLog

        try:
            BunkerAccessLog.query.filter_by(token_id=token_id).delete()
            alchemy_db.session.commit()
            return {"message": "Historial eliminado correctamente"}
        except Exception:
            alchemy_db.session.rollback()
            raise HTTPException(status_code=500, detail="Error al eliminar el historial")

    @api_router.get("/bunker/writeups/{maquina_nombre}", response_model=BunkerWriteupsResponse)
    def api_get_bunker_writeups(request: Request, maquina_nombre: str, flask_session: dict = Depends(get_flask_session)):
        from bunkerlabs.models import BunkerWriteup

        writeups = BunkerWriteup.query.filter_by(maquina=maquina_nombre).order_by(BunkerWriteup.created_at.desc()).all()
        result = []
        for w in writeups:
            result.append(
                {
                    "id": w.id,
                    "autor": w.autor,
                    "url": w.url,
                    "tipo": w.tipo,
                    "locked": w.locked,
                    "created_at": w.created_at.isoformat() if w.created_at else None,
                }
            )
        return {"writeups": result}

    @api_router.post("/bunker/admin/writeups/toggle-lock/{writeup_id}", response_model=ToggleLockResponse)
    def api_toggle_writeup_lock(
        request: Request,
        writeup_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        role = flask_session.get("role", "")
        if role != "admin":
            raise HTTPException(status_code=403, detail="Acceso denegado")

        from bunkerlabs.models import BunkerWriteup

        writeup = BunkerWriteup.query.get(writeup_id)
        if not writeup:
            raise HTTPException(status_code=404, detail="Writeup no encontrado")

        try:
            writeup.locked = not writeup.locked
            alchemy_db.session.commit()
            return {"message": "Estado actualizado", "locked": writeup.locked}
        except Exception as e:
            alchemy_db.session.rollback()
            raise HTTPException(status_code=500, detail=str(e))
