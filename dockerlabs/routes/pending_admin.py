"""Revisión de envíos de máquinas (PendingMachineSubmission).

Un envío pasa por tres estados: «pendiente» (en cola), «aprobado» (la máquina
ya se añadió a la plataforma) y «rechazado». La cola de /pending-machines solo
enseña los pendientes; los otros dos quedan archivados en sus pestañas hasta
que alguien los limpia.
"""
from typing import Optional

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func

from dockerlabs.models import PendingMachineSubmission
from dockerlabs.tiempo import utcnow

ESTADOS = ("pendiente", "aprobado", "rechazado")
ROLES_REVISION = ("admin", "moderador")


class EstadoRequest(BaseModel):
    estado: str


class LimpiarRequest(BaseModel):
    estado: str
    # Solo los revisados hace más de N días (None o 0 = todos los de ese estado)
    dias: Optional[int] = None


def contar_por_estado(db):
    """{'pendiente': n, 'aprobado': n, 'rechazado': n, 'todas': n}"""
    filas = (
        db.session.query(PendingMachineSubmission.estado, func.count(PendingMachineSubmission.id))
        .group_by(PendingMachineSubmission.estado)
        .all()
    )
    cuenta = {e: 0 for e in ESTADOS}
    total = 0
    for estado, n in filas:
        total += n
        if estado in cuenta:
            cuenta[estado] += n
    cuenta["todas"] = total
    return cuenta


def marcar_publicadas(db, nombre, revisor_id=None):
    """Al publicar una máquina, da por añadidos los envíos pendientes con ese
    mismo nombre (sin distinguir mayúsculas). Devuelve cuántos ha marcado."""
    clave = (nombre or "").strip().lower()
    if not clave:
        return 0
    envios = (
        PendingMachineSubmission.query
        .filter(
            func.lower(func.trim(PendingMachineSubmission.nombre)) == clave,
            PendingMachineSubmission.estado == "pendiente",
        )
        .all()
    )
    for sub in envios:
        sub.estado = "aprobado"
        sub.reviewed_at = utcnow()
        sub.reviewed_by = revisor_id
    if envios:
        db.session.commit()
    return len(envios)


def register_pending_admin_routes(api_router, get_session, verify_csrf_token, db):
    def _denegado(session):
        if session.get("role", "") not in ROLES_REVISION:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
        return None

    def _aplica_estado(sub, estado, session):
        sub.estado = estado
        if estado == "pendiente":
            sub.reviewed_at = None
            sub.reviewed_by = None
        else:
            sub.reviewed_at = utcnow()
            sub.reviewed_by = session.get("user_id")

    @api_router.post("/admin/pending-machines/limpiar")
    async def api_limpiar_pending_machines(
        request: Request,
        data: LimpiarRequest,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """Borra de golpe los envíos ya revisados de un estado. Nunca toca los pendientes."""
        denegado = _denegado(session)
        if denegado:
            return denegado
        if data.estado not in ("aprobado", "rechazado"):
            return JSONResponse(status_code=400, content={"error": "Solo se pueden limpiar envíos añadidos o rechazados"})

        consulta = PendingMachineSubmission.query.filter(PendingMachineSubmission.estado == data.estado)
        if data.dias and data.dias > 0:
            from datetime import timedelta
            limite = utcnow() - timedelta(days=data.dias)
            fecha = func.coalesce(PendingMachineSubmission.reviewed_at, PendingMachineSubmission.submitted_at)
            consulta = consulta.filter(fecha < limite)
        eliminadas = consulta.delete(synchronize_session=False)
        db.session.commit()
        return {
            "success": True,
            "eliminadas": eliminadas,
            "message": f"{eliminadas} envío{'s' if eliminadas != 1 else ''} eliminado{'s' if eliminadas != 1 else ''}",
            "counts": contar_por_estado(db),
        }

    @api_router.post("/admin/pending-machines/{machine_id}/estado")
    async def api_estado_pending_machine(
        request: Request,
        machine_id: int,
        data: EstadoRequest,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """Cambia el estado de un envío: añadido, rechazado o de vuelta a la cola."""
        denegado = _denegado(session)
        if denegado:
            return denegado
        if data.estado not in ESTADOS:
            return JSONResponse(status_code=400, content={"error": "Estado no válido"})

        sub = db.session.get(PendingMachineSubmission, machine_id)
        if not sub:
            return JSONResponse(status_code=404, content={"error": "Máquina pendiente no encontrada"})
        anterior = sub.estado
        _aplica_estado(sub, data.estado, session)
        db.session.commit()
        mensajes = {
            "aprobado": "Marcada como añadida",
            "rechazado": "Envío rechazado",
            "pendiente": "Devuelta a pendientes",
        }
        return {
            "success": True,
            "message": mensajes[data.estado],
            "estado": data.estado,
            "anterior": anterior,
            "counts": contar_por_estado(db),
        }

    @api_router.post("/admin/pending-machines/{machine_id}/approve")
    async def api_approve_pending_machine(
        request: Request,
        machine_id: int,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        denegado = _denegado(session)
        if denegado:
            return denegado

        sub = db.session.get(PendingMachineSubmission, machine_id)
        if not sub:
            return JSONResponse(status_code=404, content={"error": "Máquina pendiente no encontrada"})
        _aplica_estado(sub, "aprobado", session)
        db.session.commit()
        return {"message": "Máquina aprobada", "success": True}

    @api_router.post("/admin/pending-machines/{machine_id}/reject")
    async def api_reject_pending_machine(
        request: Request,
        machine_id: int,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """Elimina el envío definitivamente (en cualquier estado)."""
        denegado = _denegado(session)
        if denegado:
            return denegado

        sub = db.session.get(PendingMachineSubmission, machine_id)
        if not sub:
            return JSONResponse(status_code=404, content={"error": "Máquina pendiente no encontrada"})
        db.session.delete(sub)
        db.session.commit()
        return {"message": "Máquina rechazada y eliminada", "success": True, "counts": contar_por_estado(db)}
