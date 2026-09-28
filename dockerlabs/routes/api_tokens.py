"""Tokens de API de administrador (sección "Tokens de API" en /dashboard).

Solo accesible para role == 'admin'. Sigue el patrón de
gestion-maquinas.dockerlabs.es: el token en claro se devuelve UNA sola vez,
al generarlo; en BD solo se guarda su hash (dockerlabs.token_auth). El uso
del token por cabecera lo acepta de forma centralizada `get_session()` en
routers.py, así que no hay que tocar cada ruta admin una por una.
"""
from datetime import datetime

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from dockerlabs.models import ApiToken
from dockerlabs.token_auth import generate_api_token, hash_api_token, token_display_prefix


class CreateTokenRequest(BaseModel):
    label: str = Field(default="", max_length=120)


def _require_admin(session: dict):
    """Devuelve (ok, respuesta_de_error). No usa require_auth_and_role porque
    ese helper está pensado para páginas HTML (redirige); aquí queremos JSON
    con 401/403, igual que admin_usuarios.py y notifications.py."""
    if not session.get("user_id"):
        return False, JSONResponse(status_code=401, content={"error": "No autenticado"})
    if session.get("role") != "admin":
        return False, JSONResponse(status_code=403, content={"error": "Acceso denegado: requiere rol admin"})
    return True, None


def _serialize(token: ApiToken) -> dict:
    return {
        "id": token.id,
        "label": token.label,
        "token_prefix": token.token_prefix,
        "created_at": token.created_at.isoformat() if token.created_at else None,
        "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
        "revoked_at": token.revoked_at.isoformat() if token.revoked_at else None,
    }


def register_api_tokens_routes(api_router, get_session, verify_csrf_token, db):

    @api_router.get("/admin/tokens")
    async def list_api_tokens(session: dict = Depends(get_session)):
        ok, err = _require_admin(session)
        if not ok:
            return err
        tokens = ApiToken.query.order_by(ApiToken.created_at.desc()).all()
        return {"tokens": [_serialize(t) for t in tokens]}

    @api_router.post("/admin/tokens")
    async def create_api_token(
        request: Request,
        data: CreateTokenRequest,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        ok, err = _require_admin(session)
        if not ok:
            return err

        label = (data.label or "").strip() or "Sin nombre"
        plain_token = generate_api_token()

        token_row = ApiToken(
            admin_user_id=session["user_id"],
            label=label,
            token_hash=hash_api_token(plain_token),
            token_prefix=token_display_prefix(plain_token),
        )
        db.session.add(token_row)
        db.session.commit()

        # El valor en claro solo se devuelve aquí, una vez; no se guarda en
        # ningún sitio (ni en BD ni en logs).
        return {
            "success": True,
            "token": plain_token,
            "id": token_row.id,
            "label": token_row.label,
            "token_prefix": token_row.token_prefix,
            "created_at": token_row.created_at.isoformat(),
        }

    @api_router.post("/admin/tokens/{token_id}/revoke")
    async def revoke_api_token(
        token_id: int,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        ok, err = _require_admin(session)
        if not ok:
            return err

        token_row = ApiToken.query.get(token_id)
        if not token_row:
            return JSONResponse(status_code=404, content={"error": "Token no encontrado"})

        if token_row.revoked_at is None:
            token_row.revoked_at = datetime.utcnow()
            db.session.commit()

        return {"success": True, "id": token_row.id, "revoked_at": token_row.revoked_at.isoformat()}
