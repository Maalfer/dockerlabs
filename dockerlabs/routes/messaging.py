import re
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import and_, or_
from slowapi import Limiter
from slowapi.util import get_remote_address

from dockerlabs.models import Mensajeria, User

limiter = None

def configure_limiter(global_limiter):
    """Configura el limiter global desde asgi.py"""
    global limiter
    limiter = global_limiter


class SendMessageRequest(BaseModel):
    receiver: str
    content: str


class SendMessageResponse(BaseModel):
    success: bool
    message: Optional[str] = None


class ConversationResponse(BaseModel):
    username: str
    unread: int
    last_message: str
    timestamp: str


class ConversationsListResponse(BaseModel):
    conversations: List[ConversationResponse]


class ChatMessageResponse(BaseModel):
    sender: str
    content: str
    timestamp: str
    mine: bool


class ChatResponse(BaseModel):
    messages: List[ChatMessageResponse]


class UnreadCountResponse(BaseModel):
    count: int


class SearchUsersResponse(BaseModel):
    users: List[dict]


class BroadcastResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    count: Optional[int] = None


class SimpleSuccessResponse(BaseModel):
    success: bool
    message: Optional[str] = None


def register_messaging_routes(api_router, get_flask_session, verify_csrf_token, alchemy_db):
    @api_router.post("/messages/send", response_model=SendMessageResponse)
    def api_send_message(
        request: Request,
        data: SendMessageRequest,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """
        Enviar mensaje a otro usuario.
        Rate limit: 30 por minuto.
        """
        user_id = flask_session.get("user_id")
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        receiver_username = data.receiver.strip() if data.receiver else ""
        content = data.content.strip() if data.content else ""

        if not receiver_username or not content:
            return JSONResponse(
                status_code=400, content={"success": False, "message": "Hay cierta información que no se permite enviar 😉"}
            )

        if len(content) > 1000:
            return JSONResponse(status_code=400, content={"success": False, "message": "Mensaje demasiado largo"})

        url_pattern = re.compile(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
        if url_pattern.search(content):
            return JSONResponse(status_code=400, content={"success": False, "message": "No se permiten enlaces"})

        receiver = User.query.filter_by(username=receiver_username).first()
        if not receiver:
            return JSONResponse(status_code=404, content={"success": False, "message": "Usuario no encontrado"})

        if receiver.id == user_id:
            return JSONResponse(
                status_code=400, content={"success": False, "message": "No puedes enviarte mensajes a ti mismo"}
            )

        sender_id = user_id
        receiver_id = receiver.id

        msgs_query = Mensajeria.query.filter(
            or_(
                and_(Mensajeria.sender_id == sender_id, Mensajeria.receiver_id == receiver_id),
                and_(Mensajeria.sender_id == receiver_id, Mensajeria.receiver_id == sender_id),
            )
        ).order_by(Mensajeria.timestamp.asc())

        count = msgs_query.count()

        if count >= 100:
            to_delete_count = count - 99
            oldest_msgs = msgs_query.limit(to_delete_count).all()
            for m in oldest_msgs:
                alchemy_db.session.delete(m)

        new_msg = Mensajeria(sender_id=sender_id, receiver_id=receiver_id, content=content)
        alchemy_db.session.add(new_msg)
        alchemy_db.session.commit()

        return {"success": True}

    @api_router.get("/messages/conversations", response_model=ConversationsListResponse)
    def api_get_conversations(request: Request, flask_session: dict = Depends(get_flask_session)):
        """Obtener lista de conversaciones del usuario."""
        user_id = flask_session.get("user_id")
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        sent_subquery = alchemy_db.session.query(Mensajeria.receiver_id).filter(
            Mensajeria.sender_id == user_id,
            Mensajeria.deleted_by_sender == False,  # noqa: E712
        )

        received_subquery = alchemy_db.session.query(Mensajeria.sender_id).filter(
            Mensajeria.receiver_id == user_id,
            Mensajeria.deleted_by_receiver == False,  # noqa: E712
        )

        subquery = sent_subquery.union(received_subquery).subquery()
        contact_ids = [row[0] for row in alchemy_db.session.query(subquery).all()]

        contacts = []
        for cid in contact_ids:
            user = User.query.get(cid)
            if user:
                unread = Mensajeria.query.filter_by(
                    sender_id=cid, receiver_id=user_id, read=False, deleted_by_receiver=False
                ).count()

                last_msg = Mensajeria.query.filter(
                    or_(
                        and_(
                            Mensajeria.sender_id == user_id,
                            Mensajeria.receiver_id == cid,
                            Mensajeria.deleted_by_sender == False,  # noqa: E712
                        ),
                        and_(
                            Mensajeria.sender_id == cid,
                            Mensajeria.receiver_id == user_id,
                            Mensajeria.deleted_by_receiver == False,  # noqa: E712
                        ),
                    )
                ).order_by(Mensajeria.timestamp.desc()).first()

                if last_msg:
                    contacts.append(
                        {
                            "username": user.username,
                            "unread": unread,
                            "last_message": last_msg.content[:30] + "..." if len(last_msg.content) > 30 else last_msg.content,
                            "timestamp": last_msg.timestamp.isoformat(),
                        }
                    )

        contacts.sort(key=lambda x: x["timestamp"] or "", reverse=True)
        return {"conversations": contacts}

    @api_router.get("/messages/chat/{username}", response_model=ChatResponse)
    def api_get_chat(request: Request, username: str, flask_session: dict = Depends(get_flask_session)):
        """Obtener mensajes de una conversación específica."""
        user_id = flask_session.get("user_id")
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        other_user = User.query.filter_by(username=username).first()
        if not other_user:
            return JSONResponse(status_code=404, content={"success": False, "message": "Usuario no encontrado"})

        other_id = other_user.id

        messages = Mensajeria.query.filter(
            or_(
                and_(
                    Mensajeria.sender_id == user_id,
                    Mensajeria.receiver_id == other_id,
                    Mensajeria.deleted_by_sender == False,  # noqa: E712
                ),
                and_(
                    Mensajeria.sender_id == other_id,
                    Mensajeria.receiver_id == user_id,
                    Mensajeria.deleted_by_receiver == False,  # noqa: E712
                ),
            )
        ).order_by(Mensajeria.timestamp.asc()).all()

        unread_msgs = Mensajeria.query.filter_by(
            sender_id=other_id, receiver_id=user_id, read=False, deleted_by_receiver=False
        ).all()

        for m in unread_msgs:
            m.read = True
        alchemy_db.session.commit()

        result_messages = [
            {"sender": m.sender.username, "content": m.content, "timestamp": m.timestamp.isoformat(), "mine": m.sender_id == user_id}
            for m in messages
        ]

        return {"messages": result_messages}

    @api_router.post("/messages/delete_conversation/{username}", response_model=SimpleSuccessResponse)
    def api_delete_conversation(
        request: Request,
        username: str,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """Eliminar una conversación (soft delete)."""
        user_id = flask_session.get("user_id")
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        other_user = User.query.filter_by(username=username).first()
        if not other_user:
            return JSONResponse(status_code=404, content={"success": False, "message": "Usuario no encontrado"})

        other_id = other_user.id

        sent_msgs = Mensajeria.query.filter_by(sender_id=user_id, receiver_id=other_id).all()
        for m in sent_msgs:
            m.deleted_by_sender = True

        received_msgs = Mensajeria.query.filter_by(sender_id=other_id, receiver_id=user_id).all()
        for m in received_msgs:
            m.deleted_by_receiver = True

        alchemy_db.session.commit()
        return {"success": True}

    @api_router.get("/messages/unread_count", response_model=UnreadCountResponse)
    def api_unread_count(request: Request, flask_session: dict = Depends(get_flask_session)):
        """Obtener cantidad de mensajes no leídos."""
        user_id = flask_session.get("user_id")
        if not user_id:
            return JSONResponse(status_code=401, content={"count": 0})

        count = Mensajeria.query.filter_by(receiver_id=user_id, read=False, deleted_by_receiver=False).count()
        return {"count": count}

    @api_router.get("/messages/search_users", response_model=SearchUsersResponse)
    def api_search_users(request: Request, q: str = "", flask_session: dict = Depends(get_flask_session)):
        """Buscar usuarios por nombre."""
        user_id = flask_session.get("user_id")
        if not user_id:
            return JSONResponse(status_code=401, content={"users": []})

        query = q.strip()
        if not query:
            return {"users": []}

        users = User.query.filter(User.username.ilike(f"%{query}%"), User.id != user_id).limit(10).all()
        return {"users": [{"username": u.username} for u in users]}

    @api_router.post("/messages/broadcast", response_model=BroadcastResponse)
    def api_broadcast_message(
        request: Request,
        data: SendMessageRequest,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """
        Enviar mensaje broadcast a todos los usuarios (solo admin).
        Rate limit: 1 por 5 minutos.
        """
        user_id = flask_session.get("user_id")
        role = flask_session.get("role", "")

        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        if role != "admin":
            return JSONResponse(status_code=403, content={"success": False, "message": "Acceso denegado"})

        content = data.content.strip() if data.content else ""

        if not content:
            return JSONResponse(status_code=400, content={"success": False, "message": "El mensaje no puede estar vacío"})

        if len(content) > 1000:
            return JSONResponse(status_code=400, content={"success": False, "message": "Mensaje demasiado largo"})

        url_pattern = re.compile(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
        if url_pattern.search(content):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "No se permiten enlaces en difusiones"},
            )

        sender_id = user_id
        users = User.query.filter(User.id != sender_id).all()

        new_messages = []
        for user in users:
            new_messages.append(
                Mensajeria(
                    sender_id=sender_id,
                    receiver_id=user.id,
                    content=content,
                    timestamp=datetime.utcnow(),
                    read=False,
                )
            )

        alchemy_db.session.add_all(new_messages)
        alchemy_db.session.commit()

        return {"success": True, "count": len(new_messages)}

