"""Administracion de usuarios: cambio de rol y borrado."""


from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from dockerlabs.extensions import db
from dockerlabs.models import User


class UpdateRoleRequest(BaseModel):
    role: str


def register_admin_usuarios_routes(api_router, get_session, verify_csrf_token):
    """Registra las rutas de este modulo en el router recibido."""

    @api_router.post("/admin/update_user_role/{user_id}")
    async def api_update_user_role(request: Request, user_id: int, data: UpdateRoleRequest, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
        caller_id = session.get('user_id')
        caller_role = session.get('role', '').strip().lower()

        if not caller_id or caller_role not in ('admin', 'moderador'):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        nuevo_rol = data.role.strip().lower()
        if nuevo_rol not in ('jugador', 'moderador', 'admin'):
            return JSONResponse(status_code=400, content={"error": "Rol inválido"})

        # Los moderadores no pueden asignar rol de admin
        if caller_role == 'moderador' and nuevo_rol == 'admin':
            return JSONResponse(status_code=403, content={"error": "Los moderadores no pueden asignar rol de admin"})

        user = User.query.get(user_id)
        if not user:
            return JSONResponse(status_code=404, content={"error": "Usuario no encontrado"})

        # Un moderador no puede modificar el rol de un administrador
        if caller_role == "moderador" and user.role == "admin":
            return JSONResponse(status_code=403, content={"error": "Los moderadores no pueden modificar a un administrador"})
        # No degradar al último administrador (evita el lockout total)
        if user.role == "admin" and nuevo_rol != "admin" and User.query.filter_by(role="admin").count() <= 1:
            return JSONResponse(status_code=400, content={"error": "No se puede degradar al último administrador."})

        user.role = nuevo_rol
        db.session.commit()
        return {"message": f"Rol de {user.username} actualizado a {nuevo_rol}", "success": True}

    @api_router.post("/admin/delete_user/{user_id}")
    async def api_delete_user(request: Request, user_id: int, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
        caller_id = session.get('user_id')
        caller_role = session.get('role', '')
        if not caller_id or caller_role not in ('admin',):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        if caller_id == user_id:
            return JSONResponse(status_code=400, content={"error": "No puedes eliminar tu propia cuenta desde aquí."})


        user = User.query.get(user_id)
        if not user:
            return JSONResponse(status_code=404, content={"error": "Usuario no encontrado."})
        if user.role == 'admin':
            admin_count = User.query.filter_by(role='admin').count()
            if admin_count <= 1:
                return JSONResponse(status_code=400, content={"error": "No se puede eliminar al último administrador."})
        try:
            db.session.delete(user)
            db.session.commit()
            return {"message": "Usuario eliminado correctamente.", "success": True}
        except Exception as e:
            db.session.rollback()
            return JSONResponse(status_code=500, content={"error": f"Error al eliminar el usuario: {str(e)}"})
