from typing import Optional
from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from dockerlabs.models import Notification, NotificationRead, NotificationReaction, User

ALLOWED_EMOJIS = {"👍", "❤️", "😂", "😮", "😢", "🔥", "🎉", "👀"}


class SendNotificationRequest(BaseModel):
    title: str
    content: str
    receiver_id: Optional[int] = None
    notification_type: Optional[str] = None


def register_notification_routes(api_router, get_flask_session, verify_csrf_token, alchemy_db):
    @api_router.post("/notifications/send")
    def api_send_notification(
        request: Request,
        request_data: SendNotificationRequest,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
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

        try:
            notification = Notification(
                sender_id=user_id,
                receiver_id=request_data.receiver_id,
                title=request_data.title,
                content=request_data.content,
                notification_type=request_data.notification_type,
            )
            alchemy_db.session.add(notification)
            alchemy_db.session.commit()
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"success": False, "message": f"Error al enviar: {str(e)}"})

        return {"success": True, "message": "Notificación enviada"}

    @api_router.get("/notifications")
    def api_get_notifications(request: Request, flask_session: dict = Depends(get_flask_session)):
        """Obtener notificaciones del usuario."""
        user_id = flask_session.get("user_id")
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        notifications = Notification.query.options(
            selectinload(Notification.reactions)
        ).filter(
            or_(Notification.receiver_id == user_id, Notification.receiver_id == None)  # noqa: E711
        ).order_by(Notification.created_at.desc()).limit(50).all()

        # Cargar todos los remitentes en una sola consulta (evita N+1)
        sender_ids = {n.sender_id for n in notifications if n.sender_id}
        senders = {u.id: u for u in User.query.filter(User.id.in_(sender_ids)).all()} if sender_ids else {}

        # Estado 'leído' por-usuario de las notificaciones globales (broadcast)
        broadcast_ids = [n.id for n in notifications if n.receiver_id is None]
        read_broadcast_ids = set()
        if broadcast_ids:
            read_broadcast_ids = {
                r.notification_id for r in NotificationRead.query.filter(
                    NotificationRead.user_id == user_id,
                    NotificationRead.notification_id.in_(broadcast_ids),
                ).all()
            }

        result = []
        for notif in notifications:
            sender = senders.get(notif.sender_id)

            # Agrupar reacciones por emoji con conteo e indicador de si el usuario actual reaccionó
            reactions_by_emoji = {}
            for reaction in notif.reactions:
                emoji = reaction.emoji
                if emoji not in reactions_by_emoji:
                    reactions_by_emoji[emoji] = {"emoji": emoji, "count": 0, "user_reacted": False}
                reactions_by_emoji[emoji]["count"] += 1
                if reaction.user_id == user_id:
                    reactions_by_emoji[emoji]["user_reacted"] = True

            result.append(
                {
                    "id": notif.id,
                    "title": notif.title,
                    "content": notif.content,
                    "created_at": notif.created_at.isoformat(),
                    "read": (notif.id in read_broadcast_ids) if notif.receiver_id is None else notif.read,
                    "sender": sender.username if sender else "Desconocido",
                    "notification_type": notif.notification_type,
                    "is_global": notif.receiver_id is None,
                    "reactions": list(reactions_by_emoji.values()),
                }
            )

        # No leídas: dirigidas (columna read) + globales no leídas por ESTE usuario
        unread_targeted = Notification.query.filter(
            Notification.receiver_id == user_id,
            Notification.read == False,  # noqa: E712
        ).count()
        read_global_subq = alchemy_db.session.query(NotificationRead.notification_id).filter(
            NotificationRead.user_id == user_id
        ).scalar_subquery()
        unread_global = Notification.query.filter(
            Notification.receiver_id == None,  # noqa: E711
            Notification.id.notin_(read_global_subq),
        ).count()
        unread_count = unread_targeted + unread_global

        return {"success": True, "notifications": result, "unread_count": unread_count}

    @api_router.post("/notifications/{notification_id}/read")
    def api_mark_notification_read(request: Request, notification_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
        """Marcar notificación como leída."""
        user_id = flask_session.get("user_id")
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        notification = Notification.query.get(notification_id)
        if not notification:
            return JSONResponse(status_code=404, content={"success": False, "message": "Notificación no encontrada"})

        if flask_session.get("role") != "admin" and notification.receiver_id is not None and notification.receiver_id != user_id:
            return JSONResponse(status_code=403, content={"success": False, "message": "No autorizado"})

        try:
            if notification.receiver_id is None:
                # Global: marcar leído por-usuario (idempotente)
                exists = NotificationRead.query.filter_by(
                    notification_id=notification_id, user_id=user_id
                ).first()
                if not exists:
                    alchemy_db.session.add(NotificationRead(notification_id=notification_id, user_id=user_id))
                    alchemy_db.session.commit()
            else:
                notification.read = True
                alchemy_db.session.commit()
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"success": False, "message": f"Error: {str(e)}"})
        return {"success": True}

    class ReactRequest(BaseModel):
        emoji: str

    @api_router.post("/notifications/{notification_id}/react")
    def api_react_notification(
        request: Request,
        notification_id: int,
        request_data: ReactRequest,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """Toggle una reacción emoji en una notificación."""
        user_id = flask_session.get("user_id")
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        if request_data.emoji not in ALLOWED_EMOJIS:
            return JSONResponse(status_code=400, content={"success": False, "message": "Emoji no permitido"})

        notification = Notification.query.get(notification_id)
        if not notification:
            return JSONResponse(status_code=404, content={"success": False, "message": "Notificación no encontrada"})

        if flask_session.get("role") != "admin" and notification.receiver_id is not None and notification.receiver_id != user_id:
            return JSONResponse(status_code=403, content={"success": False, "message": "No autorizado"})

        existing = NotificationReaction.query.filter_by(
            notification_id=notification_id,
            user_id=user_id,
            emoji=request_data.emoji,
        ).first()

        try:
            if existing:
                alchemy_db.session.delete(existing)
                reacted = False
            else:
                reaction = NotificationReaction(
                    notification_id=notification_id,
                    user_id=user_id,
                    emoji=request_data.emoji,
                )
                alchemy_db.session.add(reaction)
                reacted = True
            alchemy_db.session.commit()
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"success": False, "message": f"Error: {str(e)}"})

        # Devolver conteo actualizado para este emoji
        count = NotificationReaction.query.filter_by(
            notification_id=notification_id,
            emoji=request_data.emoji,
        ).count()

        return {"success": True, "reacted": reacted, "emoji": request_data.emoji, "count": count}

    @api_router.delete("/notifications/{notification_id}")
    def api_delete_notification(request: Request, notification_id: int, flask_session: dict = Depends(get_flask_session), csrf_ok: bool = Depends(verify_csrf_token)):
        """Eliminar notificación."""
        user_id = flask_session.get("user_id")
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        notification = Notification.query.get(notification_id)
        if not notification:
            return JSONResponse(status_code=404, content={"success": False, "message": "Notificación no encontrada"})

        if flask_session.get("role") != "admin" and notification.receiver_id != user_id:
            return JSONResponse(status_code=403, content={"success": False, "message": "No autorizado"})

        try:
            alchemy_db.session.delete(notification)
            alchemy_db.session.commit()
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(status_code=500, content={"success": False, "message": f"Error: {str(e)}"})
        return {"success": True, "message": "Notificación eliminada"}

