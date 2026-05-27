let currentChatUser = null;
let chatPollingInterval = null;
let unreadPollingInterval = null;

document.addEventListener('DOMContentLoaded', function () {
    startUnreadPolling();
    checkUnread();

    const modal = document.getElementById('messagingModal');
    if (modal) {
        modal.addEventListener('click', function (e) {
            if (e.target === modal) closeMessagingModal();
        });
    }

    const searchInput = document.getElementById('newMsgUser');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function (e) {
            searchUsers(e.target.value);
        }, 300));
    }
});

/* ── Helpers ── */

function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

function avatarColor(username) {
    const colors = ['#6366f1','#8b5cf6','#3b82f6','#06b6d4','#10b981','#f59e0b','#ef4444','#ec4899','#14b8a6','#f97316'];
    let hash = 0;
    for (let i = 0; i < username.length; i++) {
        hash = username.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
}

function avatarInitial(username) {
    return username ? username.charAt(0).toUpperCase() : '?';
}

function formatMsgTime(isoStr) {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    const wasYesterday = d.toDateString() === yesterday.toDateString();

    if (sameDay) return d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    if (wasYesterday) return 'Ayer';
    return d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' });
}

function formatDateLabel(isoStr) {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    if (sameDay) return 'Hoy';
    if (d.toDateString() === yesterday.toDateString()) return 'Ayer';
    return d.toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' });
}

function setAvatar(el, username) {
    if (!el) return;
    el.textContent = avatarInitial(username);
    el.style.background = avatarColor(username);
}

/* ── Modal open/close ── */

function openMessagingModal() {
    document.getElementById('messagingModal').classList.add('visible');
    loadConversations();
}

function closeMessagingModal() {
    document.getElementById('messagingModal').classList.remove('visible');
    stopChatPolling();
    currentChatUser = null;
    document.getElementById('msgSidebar').classList.remove('hidden');
    document.getElementById('msgContent').classList.remove('active');
    cancelNewMessage();
}

/* ── Unread badge ── */

function startUnreadPolling() {
    if (unreadPollingInterval) clearInterval(unreadPollingInterval);
    unreadPollingInterval = setInterval(checkUnread, 30000);
}

function checkUnread() {
    fetch('/api/messages/unread_count')
        .then(res => res.json())
        .then(data => {
            const badge = document.getElementById('msg-badge');
            if (!badge) return;
            if (data.count > 0) {
                badge.innerText = data.count > 99 ? '99+' : data.count;
                badge.style.display = 'block';
            } else {
                badge.style.display = 'none';
            }
        })
        .catch(err => console.error('Error polling unread:', err));
}

/* ── Conversations ── */

function loadConversations() {
    const list = document.getElementById('msgList');
    list.innerHTML = '<div class="msg-state-text">Cargando...</div>';

    fetch('/api/messages/conversations')
        .then(res => res.json())
        .then(data => {
            list.innerHTML = '';
            if (data.conversations.length === 0) {
                list.innerHTML = '<div class="msg-state-text">No tienes conversaciones.<br>¡Inicia una nueva!</div>';
                return;
            }

            data.conversations.forEach(c => {
                const item = document.createElement('div');
                item.className = 'msg-contact' + (c.unread > 0 ? ' unread' : '');

                const avatarEl = document.createElement('div');
                avatarEl.className = 'msg-avatar msg-avatar-list';
                setAvatar(avatarEl, c.username);

                item.innerHTML = `
                    <div class="msg-contact-info">
                        <div class="msg-contact-top">
                            <span class="msg-contact-name">${escapeHtml(c.username)}</span>
                            <span class="msg-contact-time">${formatMsgTime(c.timestamp)}</span>
                        </div>
                        <div class="msg-contact-bottom">
                            <span class="msg-contact-last">${escapeHtml(c.last_message)}</span>
                            ${c.unread > 0 ? `<span class="msg-unread-badge">${c.unread > 99 ? '99+' : c.unread}</span>` : ''}
                        </div>
                    </div>
                `;

                item.prepend(avatarEl);
                item.onclick = () => openChat(c.username);
                list.appendChild(item);
            });
        })
        .catch(() => {
            list.innerHTML = '<div class="msg-state-text" style="color:#ef4444;">Error al cargar</div>';
        });
}

/* ── New message search ── */

function showNewMessageInput() {
    document.getElementById('msgList').style.display = 'none';
    document.getElementById('msgNew').style.display = 'block';
    document.querySelectorAll('.msg-new-btn').forEach(b => b.style.display = 'none');
    const input = document.getElementById('newMsgUser');
    input.value = '';
    document.getElementById('searchResults').innerHTML = '';
    input.focus();
}

function cancelNewMessage() {
    document.getElementById('msgNew').style.display = 'none';
    document.getElementById('msgList').style.display = 'block';
    document.querySelectorAll('.msg-new-btn').forEach(b => b.style.display = 'flex');
    document.getElementById('newMsgUser').value = '';
    document.getElementById('searchResults').innerHTML = '';
}

function showBroadcastInput() {
    document.getElementById('msgList').style.display = 'none';
    document.getElementById('msgBroadcast').style.display = 'block';
    document.querySelectorAll('.msg-new-btn').forEach(b => b.style.display = 'none');
    document.getElementById('broadcastContent').value = '';
    document.getElementById('broadcastContent').focus();
}

function cancelBroadcast() {
    document.getElementById('msgBroadcast').style.display = 'none';
    document.getElementById('msgList').style.display = 'block';
    document.querySelectorAll('.msg-new-btn').forEach(b => b.style.display = 'flex');
    document.getElementById('broadcastContent').value = '';
}

function sendBroadcast() {
    const content = document.getElementById('broadcastContent').value.trim();
    if (!content) return;
    if (!confirm('⚠️ ¿Estás seguro de enviar este mensaje a TODOS los usuarios?')) return;

    fetch('/api/messages/broadcast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
        body: JSON.stringify({ content, receiver: '_broadcast_' })
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert(`Difusión enviada a ${data.count} usuarios.`);
                cancelBroadcast();
            } else {
                alert(data.message);
            }
        })
        .catch(() => alert('Error de red'));
}

function searchUsers(query) {
    const results = document.getElementById('searchResults');
    if (!query) { results.innerHTML = ''; return; }

    fetch(`/api/messages/search_users?q=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(data => {
            results.innerHTML = '';
            if (data.users.length === 0) {
                results.innerHTML = '<div class="msg-search-result-item" style="color:#64748b;cursor:default;">Sin resultados</div>';
                return;
            }
            data.users.forEach(u => {
                const div = document.createElement('div');
                div.className = 'msg-search-result-item';

                const avatarEl = document.createElement('div');
                avatarEl.className = 'msg-avatar msg-avatar-sm';
                setAvatar(avatarEl, u.username);

                div.appendChild(avatarEl);
                div.appendChild(document.createTextNode(escapeHtml(u.username)));
                div.onclick = () => { cancelNewMessage(); openChat(u.username); };
                results.appendChild(div);
            });
        })
        .catch(() => {});
}

/* ── Open / close chat ── */

function openChat(username) {
    currentChatUser = username;

    const nameEl = document.getElementById('chatUserName');
    if (nameEl) nameEl.textContent = username;

    setAvatar(document.getElementById('chatUserAvatar'), username);

    const inputArea = document.getElementById('inputArea');
    if (inputArea) inputArea.style.display = 'flex';

    const messageInput = document.getElementById('messageInput');
    if (messageInput) messageInput.focus();

    const deleteBtn = document.getElementById('deleteChatBtn');
    if (deleteBtn) deleteBtn.style.display = 'flex';

    document.getElementById('msgSidebar').classList.add('hidden');
    document.getElementById('msgContent').classList.add('active');

    loadMessages();
    stopChatPolling();
    chatPollingInterval = setInterval(loadMessages, 5000);
}

function backToSidebar() {
    document.getElementById('msgContent').classList.remove('active');
    document.getElementById('msgSidebar').classList.remove('hidden');

    const deleteBtn = document.getElementById('deleteChatBtn');
    if (deleteBtn) deleteBtn.style.display = 'none';

    stopChatPolling();
    currentChatUser = null;
    loadConversations();
}

function deleteCurrentChat() {
    if (!currentChatUser) return;
    if (!confirm('¿Eliminar esta conversación? Solo afectará tu historial.')) return;

    fetch(`/api/messages/delete_conversation/${currentChatUser}`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken() }
    })
        .then(res => res.json())
        .then(data => { if (data.success) backToSidebar(); else alert('Error al eliminar'); })
        .catch(() => alert('Error de red'));
}

function stopChatPolling() {
    if (chatPollingInterval) clearInterval(chatPollingInterval);
}

/* ── Messages ── */

function loadMessages() {
    if (!currentChatUser) return;
    const container = document.getElementById('chatMessages');

    fetch(`/api/messages/chat/${currentChatUser}`)
        .then(res => {
            if (res.status === 404) throw new Error('Usuario no encontrado');
            return res.json();
        })
        .then(data => {
            renderMessages(data.messages);
            checkUnread();
        })
        .catch(err => {
            container.innerHTML = `<div class="msg-state-text" style="color:#ef4444;">${escapeHtml(err.message)}</div>`;
        });
}

function renderMessages(messages) {
    const container = document.getElementById('chatMessages');
    const atBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 40;

    if (messages.length === 0) {
        container.innerHTML = `
            <div class="msg-empty-state">
                <i class="bi bi-chat-dots"></i>
                <p>¡Sé el primero en decir hola! 👋</p>
            </div>`;
        return;
    }

    let html = '';
    let lastDateLabel = '';

    messages.forEach(m => {
        const cls = m.mine ? 'sent' : 'received';
        const time = formatMsgTime(m.timestamp);
        const dateLabel = formatDateLabel(m.timestamp);

        if (dateLabel !== lastDateLabel) {
            html += `<div class="msg-date-sep">${escapeHtml(dateLabel)}</div>`;
            lastDateLabel = dateLabel;
        }

        html += `
            <div class="msg-bubble-wrap ${cls}">
                <div class="msg-message ${cls}">${escapeHtml(m.content)}</div>
                <span class="msg-bubble-time">${time}</span>
            </div>`;
    });

    container.innerHTML = html;
    if (atBottom) container.scrollTop = container.scrollHeight;
}

/* ── Send ── */

function sendMessage() {
    const input = document.getElementById('messageInput');
    const content = input.value.trim();
    if (!content || !currentChatUser) return;

    const btn = document.querySelector('.msg-send-btn');
    if (btn) btn.disabled = true;

    fetch('/api/messages/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
        body: JSON.stringify({ receiver: currentChatUser, content })
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                input.value = '';
                loadMessages();
            } else {
                alert(data.message);
            }
        })
        .catch(() => alert('Error de conexión'))
        .finally(() => { if (btn) btn.disabled = false; });
}

function handleEnter(e) {
    if (e.key === 'Enter') sendMessage();
}
