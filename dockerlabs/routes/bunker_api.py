from datetime import datetime
from typing import List, Optional

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from dockerlabs.models import CompletedMachine, Machine, User

limiter = None

def configure_limiter(global_limiter):
    """Configura el limiter global desde asgi.py"""
    global limiter
    limiter = global_limiter


class FlagValidationRequest(BaseModel):
    maquina_nombre: str
    pin: str


class FlagValidationResponse(BaseModel):
    message: str
    puntos: Optional[int] = None


class RankingEntry(BaseModel):
    id: int
    nombre: str
    puntos: int


class RankingResponse(BaseModel):
    ranking: List[RankingEntry]


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


class UpdateFlagRequest(BaseModel):
    flag: str


class UpdateFlagResponse(BaseModel):
    success: bool
    message: str
    machine_id: int
    machine_name: str


def register_bunker_api_routes(api_router, get_flask_session, verify_csrf_token, alchemy_db):
    @api_router.post("/bunker/validate-flag", response_model=FlagValidationResponse)
    def api_validate_flag(request: Request, data: FlagValidationRequest, flask_session: dict = Depends(get_flask_session)):
        user_id = flask_session.get("user_id")

        if not user_id and not flask_session.get("bunkerlabs_guest"):
            raise HTTPException(status_code=401, detail="Sesión no válida")

        PUNTOS_MAP = {"Muy Fácil": 10, "Fácil": 20, "Medio": 30, "Difícil": 40}

        maquina = Machine.query.filter_by(nombre=data.maquina_nombre.strip(), origen="bunker").first()

        if not maquina:
            raise HTTPException(status_code=404, detail="Máquina no encontrada")

        if flask_session.get("bunkerlabs_guest"):
            if not maquina.guest_access:
                raise HTTPException(status_code=403, detail="Los invitados no pueden subir flags")
            if maquina.pin == data.pin.strip():
                return {"message": "¡Flag correcta! (Modo invitado: no se guarda el progreso)"}
            raise HTTPException(status_code=401, detail="Flag incorrecta")

        if maquina.pin != data.pin.strip():
            raise HTTPException(status_code=401, detail="Flag incorrecta")

        ya_completada = CompletedMachine.query.filter_by(user_id=user_id, machine_name=maquina.nombre).first()
        if ya_completada:
            return {"message": "Flag correcta, pero ya habías completado esta máquina"}

        puntos = PUNTOS_MAP.get(maquina.dificultad, 0)

        try:
            completed = CompletedMachine(user_id=user_id, machine_name=maquina.nombre, completed_at=datetime.utcnow())
            alchemy_db.session.add(completed)
            user = User.query.get(user_id)
            if user:
                user.puntos = (user.puntos or 0) + puntos
            alchemy_db.session.commit()
            return {"message": f"¡Flag correcta! Has ganado {puntos} puntos", "puntos": puntos}
        except Exception:
            alchemy_db.session.rollback()
            raise HTTPException(status_code=500, detail="Error al procesar la flag")

    @api_router.get("/bunker/ranking", response_model=RankingResponse)
    def api_bunker_ranking(request: Request, flask_session: dict = Depends(get_flask_session)):
        users = User.query.filter(User.puntos > 0).order_by(User.puntos.desc()).all()
        ranking = []
        for idx, user in enumerate(users, start=1):
            ranking.append({"id": idx, "nombre": user.username or "Unknown", "puntos": user.puntos or 0})
        return {"ranking": ranking}

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

    @api_router.post("/bunker/admin/machines/update-flag/{machine_id}", response_model=UpdateFlagResponse)
    def api_update_machine_flag(
        request: Request,
        machine_id: int,
        data: UpdateFlagRequest,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        role = flask_session.get("role", "")
        if role != "admin":
            raise HTTPException(status_code=403, detail="Acceso denegado")

        machine = Machine.query.get(machine_id)
        if not machine or machine.origen != "bunker":
            raise HTTPException(status_code=404, detail="Máquina no encontrada")
        if not data.flag.strip():
            raise HTTPException(status_code=400, detail="La flag no puede estar vacía")

        try:
            machine.pin = data.flag.strip()
            alchemy_db.session.commit()
            return {
                "success": True,
                "message": f"Flag actualizada para {machine.nombre}",
                "machine_id": machine_id,
                "machine_name": machine.nombre,
            }
        except Exception as e:
            alchemy_db.session.rollback()
            raise HTTPException(status_code=500, detail=str(e))

