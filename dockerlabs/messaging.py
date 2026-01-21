from flask import Blueprint, request, jsonify, session, g
from .extensions import db
from .models import User, Mensajeria
from flask_login import login_required
from sqlalchemy import or_, and_, func
from datetime import datetime
import re
from .decorators import csrf_protect
from bunkerlabs.extensions import limiter

messaging_bp = Blueprint('messaging', __name__)

@messaging_bp.route('/api/messages/send', methods=['POST'])
@login_required
@csrf_protect
@limiter.limit("30 per minute")
def send_message():
    data = request.get_json()
    receiver_username = data.get('receiver')
    content = data.get('content', '').strip()

    if not receiver_username or not content:
        return jsonify({'success': False, 'message': 'Hay cierta información que no se permite enviar 😉'}), 400

    if len(content) > 1000:
        return jsonify({'success': False, 'message': 'Mensaje demasiado largo'}), 400

    # Link validation (Basic Regex)
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    if url_pattern.search(content):
        return jsonify({'success': False, 'message': 'No se permiten enlaces'}), 400

    receiver = User.query.filter_by(username=receiver_username).first()
    if not receiver:
        return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404

    if receiver.id == g.user.id:
        return jsonify({'success': False, 'message': 'No puedes enviarte mensajes a ti mismo'}), 400

    # FIFO Limit: Check count of messages between these two users
    # We want to keep max 100 messages total per conversation (or maybe 100 is too low? User said 100. Let's stick to 100).
    # "conversaciones como maximo van a tener 100 mensajes, a partir de ahi los mensajes antiguos se van a ir eliminando"
    
    sender_id = g.user.id
    receiver_id = receiver.id
    
    # Get all messages between sender and receiver ordered by time
    msgs_query = Mensajeria.query.filter(
        or_(
            and_(Mensajeria.sender_id == sender_id, Mensajeria.receiver_id == receiver_id),
            and_(Mensajeria.sender_id == receiver_id, Mensajeria.receiver_id == sender_id)
        )
    ).order_by(Mensajeria.timestamp.asc())
    
    count = msgs_query.count()
    
    if count >= 100:
        # Delete oldest
        # We need to delete (count - 99) oldest messages to make room for 1 new one = 100
        to_delete_count = count - 99
        oldest_msgs = msgs_query.limit(to_delete_count).all()
        for m in oldest_msgs:
            db.session.delete(m)

    new_msg = Mensajeria(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=content
    )
    db.session.add(new_msg)
    db.session.commit()

    return jsonify({'success': True})

@messaging_bp.route('/api/messages/conversations', methods=['GET'])
@login_required
def get_conversations():
    user_id = g.user.id
    
    # Identify all users we have exchanged messages with, excluding deleted conversations
    # For sent messages: check if deleted_by_sender is False
    sent_subquery = db.session.query(Mensajeria.receiver_id).filter(
        Mensajeria.sender_id == user_id, 
        Mensajeria.deleted_by_sender == False
    )
    
    # For received messages: check if deleted_by_receiver is False
    received_subquery = db.session.query(Mensajeria.sender_id).filter(
        Mensajeria.receiver_id == user_id, 
        Mensajeria.deleted_by_receiver == False
    )
    
    subquery = sent_subquery.union(received_subquery).subquery()
    
    contact_ids = [row[0] for row in db.session.query(subquery).all()]
    
    contacts = []
    for cid in contact_ids:
        user = User.query.get(cid)
        if user:
            # Count unread from this user (ensure not deleted)
            unread = Mensajeria.query.filter_by(
                sender_id=cid, 
                receiver_id=user_id, 
                read=False,
                deleted_by_receiver=False
            ).count()
            
            # Get last message (ensure not deleted)
            last_msg = Mensajeria.query.filter(
                or_(
                    and_(Mensajeria.sender_id == user_id, Mensajeria.receiver_id == cid, Mensajeria.deleted_by_sender == False),
                    and_(Mensajeria.sender_id == cid, Mensajeria.receiver_id == user_id, Mensajeria.deleted_by_receiver == False)
                )
            ).order_by(Mensajeria.timestamp.desc()).first()
            
            if last_msg:
                contacts.append({
                    'username': user.username,
                    'unread': unread,
                    'last_message': last_msg.content[:30] + '...' if len(last_msg.content) > 30 else last_msg.content,
                    'timestamp': last_msg.timestamp.isoformat()
                })
            
    # Sort by timestamp desc
    contacts.sort(key=lambda x: x['timestamp'] or '', reverse=True)
    
    return jsonify({'conversations': contacts})

@messaging_bp.route('/api/messages/chat/<username>', methods=['GET'])
@login_required
def get_chat(username):
    other_user = User.query.filter_by(username=username).first()
    if not other_user:
        return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
    user_id = g.user.id
    other_id = other_user.id
    
    messages = Mensajeria.query.filter(
        or_(
            and_(Mensajeria.sender_id == user_id, Mensajeria.receiver_id == other_id, Mensajeria.deleted_by_sender == False),
            and_(Mensajeria.sender_id == other_id, Mensajeria.receiver_id == user_id, Mensajeria.deleted_by_receiver == False)
        )
    ).order_by(Mensajeria.timestamp.asc()).all()
    
    # Mark as read (messages sent by other_user to me)
    unread_msgs = Mensajeria.query.filter_by(
        sender_id=other_id, 
        receiver_id=user_id, 
        read=False,
        deleted_by_receiver=False
    ).all()
    
    for m in unread_msgs:
        m.read = True
    db.session.commit()
    
    return jsonify({
        'messages': [{
            'sender': m.sender.username,
            'content': m.content,
            'timestamp': m.timestamp.isoformat(),
            'mine': m.sender_id == user_id
        } for m in messages]
    })

@messaging_bp.route('/api/messages/delete_conversation/<username>', methods=['POST'])
@login_required
@csrf_protect
def delete_conversation(username):
    other_user = User.query.filter_by(username=username).first()
    if not other_user:
        return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
    user_id = g.user.id
    other_id = other_user.id
    
    # Find sent messages to mark as deleted by sender
    sent_msgs = Mensajeria.query.filter_by(sender_id=user_id, receiver_id=other_id).all()
    for m in sent_msgs:
        m.deleted_by_sender = True
        
    # Find received messages to mark as deleted by receiver
    received_msgs = Mensajeria.query.filter_by(sender_id=other_id, receiver_id=user_id).all()
    for m in received_msgs:
        m.deleted_by_receiver = True
        
    db.session.commit()
    return jsonify({'success': True})

@messaging_bp.route('/api/messages/unread_count', methods=['GET'])
@login_required
def get_unread_count():
    count = Mensajeria.query.filter_by(
        receiver_id=g.user.id, 
        read=False,
        deleted_by_receiver=False
    ).count()
    return jsonify({'count': count})

@messaging_bp.route('/api/messages/search_users', methods=['GET'])
@login_required
def search_users():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'users': []})
    
    # Filter users by name, exclude current user
    users = User.query.filter(User.username.ilike(f'%{query}%'), User.id != g.user.id).limit(10).all()
    
    return jsonify({'users': [{'username': u.username} for u in users]})

@messaging_bp.route('/api/messages/broadcast', methods=['POST'])
@login_required
@csrf_protect
@limiter.limit("1 per 5 minutes")
def broadcast_message():
    if g.user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    data = request.get_json()
    content = data.get('content', '').strip()

    if not content:
        return jsonify({'success': False, 'message': 'El mensaje no puede estar vacío'}), 400

    if len(content) > 1000:
        return jsonify({'success': False, 'message': 'Mensaje demasiado largo'}), 400
        
    # Link validation
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    if url_pattern.search(content):
        return jsonify({'success': False, 'message': 'No se permiten enlaces en difusiones'}), 400

    sender_id = g.user.id
    users = User.query.filter(User.id != sender_id).all()
    
    new_messages = []
    for user in users:
        new_messages.append(Mensajeria(
            sender_id=sender_id,
            receiver_id=user.id,
            content=content,
            timestamp=datetime.utcnow(),
            read=False
        ))
    
    # Bulk save if possible, or add all
    # db.session.bulk_save_objects(new_messages) # bulk_save doesn't handle relationships/events sometimes well, but for simple insert it is fine. 
    # Let's use simple add_all for compatibility and safety with current setup
    db.session.add_all(new_messages)
    db.session.commit()

    return jsonify({'success': True, 'count': len(new_messages)})
