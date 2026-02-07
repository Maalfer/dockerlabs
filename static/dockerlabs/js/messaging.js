let currentChatUser = null;
let chatPollingInterval = null;
let unreadPollingInterval = null;

document.addEventListener('DOMContentLoaded', function () {
    startUnreadPolling();
    // Also poll immediately
    checkUnread();

    // Close modal when clicking outside
    const modal = document.getElementById('messagingModal');
    if (modal) {
        modal.addEventListener('click', function (e) {
            if (e.target === modal) closeMessagingModal();
        });
    }

    // Live search listener
    const searchInput = document.getElementById('newMsgUser');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function (e) {
            searchUsers(e.target.value);
        }, 300));
    }
});

function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

function openMessagingModal() {
    document.getElementById('messagingModal').classList.add('visible');
    loadConversations();
}

function closeMessagingModal() {
    document.getElementById('messagingModal').classList.remove('visible');
    stopChatPolling();
    currentChatUser = null;
    // Reset view
    document.getElementById('msgSidebar').classList.remove('hidden');
    document.getElementById('msgContent').classList.remove('active');
    cancelNewMessage(); // Reset new message view
}

function startUnreadPolling() {
    if (unreadPollingInterval) clearInterval(unreadPollingInterval);
    unreadPollingInterval = setInterval(checkUnread, 30000); // Check every 30s
}

function checkUnread() {
    fetch('/api/messages/unread_count')
        .then(res => res.json())
        .then(data => {
            const badge = document.getElementById('msg-badge');
            if (data.count > 0) {
                badge.innerText = data.count > 99 ? '99+' : data.count;
                badge.style.display = 'block';
            } else {
                badge.style.display = 'none';
            }
        })
        .catch(err => console.error('Error polling unread:', err));
}

function loadConversations() {
    const list = document.getElementById('msgList');
    list.innerHTML = '<div style="padding:1rem;text-align:center;color:#94a3b8;">Cargando...</div>';

    fetch('/api/messages/conversations')
        .then(res => res.json())
        .then(data => {
            list.innerHTML = '';
            if (data.conversations.length === 0) {
                list.innerHTML = '<div style="padding:1rem;text-align:center;color:#64748b;">No tienes conversaciones. <br>¡Inicia una nueva!</div>';
                return;
            }

            data.conversations.forEach(c => {
                const item = document.createElement('div');
                item.className = 'msg-contact';
                if (c.unread > 0) item.style.borderLeft = '3px solid #ef4444';

                item.innerHTML = `
                    <span class="name">
                        ${escapeHtml(c.username)}
                        ${c.unread > 0 ? `<span style="background:#ef4444;color:white;border-radius:50%;padding:1px 5px;font-size:0.7rem;margin-left:5px;">${c.unread}</span>` : ''}
                    </span>
                    <span class="last-msg">${escapeHtml(c.last_message)}</span>
                `;
                item.onclick = () => openChat(c.username); // keeping raw username for ID is fine if treated as string
                list.appendChild(item);
            });
        })
        .catch(err => {
            console.error(err);
            list.innerHTML = '<div style="padding:1rem;text-align:center;color:#ef4444;">Error al cargar</div>';
        });
}

function showNewMessageInput() {
    document.getElementById('msgList').style.display = 'none';
    document.getElementById('msgNew').style.display = 'block';

    // Hide the "New Message" button temporarily
    document.querySelectorAll('.msg-new-btn').forEach(b => b.style.display = 'none');

    document.getElementById('newMsgUser').focus();
    document.getElementById('newMsgUser').value = '';
    document.getElementById('searchResults').innerHTML = '';
}

function cancelNewMessage() {
    document.getElementById('msgNew').style.display = 'none';
    document.getElementById('msgList').style.display = 'block';
    document.querySelectorAll('.msg-new-btn').forEach(b => b.style.display = 'block');
    document.getElementById('newMsgUser').value = '';
    document.getElementById('searchResults').innerHTML = '';
}

function showBroadcastInput() {
    document.getElementById('msgList').style.display = 'none';
    document.getElementById('msgBroadcast').style.display = 'block';
    document.querySelectorAll('.msg-new-btn').forEach(b => b.style.display = 'none');
    document.getElementById('broadcastContent').focus();
    document.getElementById('broadcastContent').value = '';
}

function cancelBroadcast() {
    document.getElementById('msgBroadcast').style.display = 'none';
    document.getElementById('msgList').style.display = 'block';
    document.querySelectorAll('.msg-new-btn').forEach(b => b.style.display = 'block');
    document.getElementById('broadcastContent').value = '';
}

function sendBroadcast() {
    const content = document.getElementById('broadcastContent').value.trim();
    if (!content) return;

    if (!confirm('⚠️ ¿Estás SEGURO de enviar este mensaje a TODOS los usuarios?')) return;

    fetch('/api/messages/broadcast', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ content: content })
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert(`Difusión enviada exitosamente a ${data.count} usuarios.`);
                cancelBroadcast();
            } else {
                alert(data.message);
            }
        })
        .catch(err => console.error(err));
}

function searchUsers(query) {
    const results = document.getElementById('searchResults');
    if (!query) {
        results.innerHTML = '';
        return;
    }

    fetch(`/api/messages/search_users?q=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(data => {
            results.innerHTML = '';
            if (data.users.length === 0) {
                results.innerHTML = '<div style="padding:0.5rem;color:#94a3b8;">No se encontraron usuarios</div>';
                return;
            }

            data.users.forEach(u => {
                const div = document.createElement('div');
                div.className = 'search-result-item';
                div.style.padding = '0.5rem';
                div.style.cursor = 'pointer';
                div.style.borderBottom = '1px solid #334155';
                div.style.color = '#e2e8f0';
                div.innerText = u.username; // innerText is safe, but consistency is good.
                div.innerHTML = escapeHtml(u.username); // forcing escape
                div.onmouseover = () => div.style.background = '#334155';
                div.onmouseout = () => div.style.background = 'transparent';
                div.onclick = () => {
                    cancelNewMessage();
                    openChat(u.username);
                };
                results.appendChild(div);
            });
        })
        .catch(err => console.error(err));
}

function openChat(username) {
    currentChatUser = username;
    document.getElementById('chatUserName').innerText = username;
    document.getElementById('inputArea').style.display = 'flex';
    document.getElementById('messageInput').focus();

    const deleteBtn = document.getElementById('deleteChatBtn');
    if (deleteBtn) deleteBtn.style.display = 'block';

    // Mobile handling
    document.getElementById('msgSidebar').classList.add('hidden');
    document.getElementById('msgContent').classList.add('active');

    loadMessages();

    // Start polling for this chat
    stopChatPolling();
    chatPollingInterval = setInterval(loadMessages, 5000); // Poll chat every 5s
}

function backToSidebar() {
    document.getElementById('msgContent').classList.remove('active');
    document.getElementById('msgSidebar').classList.remove('hidden');

    const deleteBtn = document.getElementById('deleteChatBtn');
    if (deleteBtn) deleteBtn.style.display = 'none';

    stopChatPolling();
    currentChatUser = null;
    loadConversations(); // Refresh list to update unread/last msg
}

function deleteCurrentChat() {
    if (!currentChatUser) return;
    if (!confirm('¿Seguro que quieres eliminar esta conversación? Esta acción solo afectará tu historial.')) return;

    fetch(`/api/messages/delete_conversation/${currentChatUser}`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                backToSidebar();
            } else {
                alert('Error al eliminar');
            }
        })
        .catch(err => console.error(err));
}

function stopChatPolling() {
    if (chatPollingInterval) clearInterval(chatPollingInterval);
}

function loadMessages() {
    if (!currentChatUser) return;

    const container = document.getElementById('chatMessages');
    // Only show loading if empty
    if (container.innerHTML.trim() === '' || container.innerText.includes('Selecciona')) {
        container.innerHTML = '<div style="padding:1rem;text-align:center;color:#94a3b8;">Cargando mensajes...</div>';
    }

    fetch(`/api/messages/chat/${currentChatUser}`)
        .then(res => {
            if (res.status === 404) throw new Error("Usuario no encontrado");
            return res.json();
        })
        .then(data => {
            // Check if we are still on the same chat
            if (currentChatUser !== currentChatUser) return;

            renderMessages(data.messages);

            // Mark as read locally (update badge)
            checkUnread();
        })
        .catch(err => {
            container.innerHTML = `<div style="padding:1rem;text-align:center;color:#ef4444;">${err.message}</div>`;
        });
}

function renderMessages(messages) {
    const container = document.getElementById('chatMessages');
    const wasScrolledToBottom = container.scrollHeight - container.scrollTop === container.clientHeight;

    // Simple render: clear and redraw (inefficient but safe for now)
    // Optimization: Diffing. For now, let's just render.
    // To prevent flicker, maybe build string first.

    if (messages.length === 0) {
        container.innerHTML = '<div style="padding:1rem;text-align:center;color:#64748b;">No hay mensajes aún. ¡Di hola! 👋</div>';
        return;
    }

    let html = '';
    messages.forEach(m => {
        const cls = m.mine ? 'sent' : 'received';
        html += `<div class="msg-message ${cls}">${escapeHtml(m.content)}</div>`;
    });

    // Only update DOM if changed to avoid scroll jitter (simple check length)
    // Actually, full redraw might lose scroll position if we don't handle it.
    // Let's replace content.
    container.innerHTML = html;

    // Scroll to bottom if it was at bottom or if it's first load
    container.scrollTop = container.scrollHeight;
}

function sendMessage() {
    const input = document.getElementById('messageInput');
    const content = input.value.trim();
    if (!content) return;

    // Optimistic UI? No, let's wait for server response to ensure validation passes.

    fetch('/api/messages/send', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            receiver: currentChatUser,
            content: content
        })
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                input.value = '';
                loadMessages(); // Refresh immediately
            } else {
                alert(data.message); // Simple alert for error
            }
        })
        .catch(err => console.error(err));
}

function handleEnter(e) {
    if (e.key === 'Enter') sendMessage();
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
