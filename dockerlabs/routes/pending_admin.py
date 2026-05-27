from datetime import datetime

from fastapi import Depends, Request
from fastapi.responses import JSONResponse

from dockerlabs.models import PendingMachineSubmission


def register_pending_admin_routes(api_router, get_flask_session, verify_csrf_token, alchemy_db):
    @api_router.post("/admin/pending-machines/{machine_id}/approve")
    async def api_approve_pending_machine(
        request: Request,
        machine_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        caller_role = flask_session.get("role", "")
        if caller_role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        sub = PendingMachineSubmission.query.get(machine_id)
        if not sub:
            return JSONResponse(status_code=404, content={"error": "Máquina pendiente no encontrada"})
        sub.estado = "aprobado"
        sub.reviewed_at = datetime.utcnow()
        alchemy_db.session.commit()
        return {"message": "Máquina aprobada", "success": True}

    @api_router.post("/admin/pending-machines/{machine_id}/reject")
    async def api_reject_pending_machine(
        request: Request,
        machine_id: int,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        caller_role = flask_session.get("role", "")
        if caller_role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        sub = PendingMachineSubmission.query.get(machine_id)
        if not sub:
            return JSONResponse(status_code=404, content={"error": "Máquina pendiente no encontrada"})
        alchemy_db.session.delete(sub)
        alchemy_db.session.commit()
        return {"message": "Máquina rechazada y eliminada", "success": True}

