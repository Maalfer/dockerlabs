from typing import Optional
from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from dockerlabs.models import Notification, User

limiter = None

def configure_limiter(global_limiter):
    """Configura el limiter global desde asgi.py"""
    global limiter
    limiter = global_limiter


class SendNotificationRequest(BaseModel):
    title: str
    content: str
    receiver_id: Optional[int] = None
    notification_type: Optional[str] = None


def register_notification_routes(api_router, get_flask_session, alchemy_db):
    @api_router.post("/notifications/send")
    def api_send_notification(
        request: Request,
        request_data: SendNotificationRequest,
        flask_session: dict = Depends(get_flask_session),
    ):
        """Enviar una notificación (solo admin/moderador)."""
        user_id = flask_session.get("user_id")
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        user = User.query.get(user_id)
        if not user or user.role not in ["admin", "moderador"]:
            return JSONResponse(status_code=403, content={"success": False, "message": "No tienes permisos"})

        if not request_data.title or not request_data.content:
            return JSONResponse(status_code=400, content={"success": False, "message": "Título y contenido son requeridos"})

        if len(request_data.title) > 200:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Título demasiado largo (máximo 200 caracteres)"},
            )

        notification = Notification(
            sender_id=user_id,
            receiver_id=request_data.receiver_id,
            title=request_data.title,
            content=request_data.content,
            notification_type=request_data.notification_type
        )
        alchemy_db.session.add(notification)
        alchemy_db.session.commit()

        return {"success": True, "message": "Notificación enviada"}

    @api_router.get("/notifications")
    def api_get_notifications(request: Request, flask_session: dict = Depends(get_flask_session)):
        """Obtener notificaciones del usuario."""
        user_id = flask_session.get("user_id")
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        # Get notifications for this user (either global or user-specific)
        notifications = Notification.query.filter(
            (Notification.receiver_id == user_id) | (Notification.receiver_id == None)
        ).order_by(Notification.created_at.desc()).limit(50).all()
        result = []
        for notif in notifications:
            sender = User.query.get(notif.sender_id)
            result.append(
                {
                    "id": notif.id,
                    "title": notif.title,
                    "content": notif.content,
                    "created_at": notif.created_at.isoformat(),
                    "read": notif.read,
                    "sender": sender.username if sender else "Desconocido",
                    "notification_type": notif.notification_type,
                }
            )

        unread_count = Notification.query.filter_by(receiver_id=user_id, read=False).count()
        return {"success": True, "notifications": result, "unread_count": unread_count}

    @api_router.post("/notifications/{notification_id}/read")
    def api_mark_notification_read(request: Request, notification_id: int, flask_session: dict = Depends(get_flask_session)):
        """Marcar notificación como leída."""
        user_id = flask_session.get("user_id")
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        notification = Notification.query.get(notification_id)
        if not notification:
            return JSONResponse(status_code=404, content={"success": False, "message": "Notificación no encontrada"})

        notification.read = True
        alchemy_db.session.commit()
        return {"success": True}

    @api_router.delete("/notifications/{notification_id}")
    def api_delete_notification(request: Request, notification_id: int, flask_session: dict = Depends(get_flask_session)):
        """Eliminar notificación."""
        user_id = flask_session.get("user_id")
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        notification = Notification.query.get(notification_id)
        if not notification:
            return JSONResponse(status_code=404, content={"success": False, "message": "Notificación no encontrada"})

        alchemy_db.session.delete(notification)
        alchemy_db.session.commit()
        return {"success": True, "message": "Notificación eliminada"}

