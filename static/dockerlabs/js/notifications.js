// Sistema de notificaciones
let notifications = [];
let unreadCount = 0;
let showReadNotifications = false;

// Cargar notificaciones al abrir el modal
function openNotificationsModal() {
    document.getElementById('notificationsModal').classList.add('visible');
    showReadNotifications = false; // Resetear estado al abrir
    loadNotifications();
}

function closeNotificationsModal() {
    document.getElementById('notificationsModal').classList.remove('visible');
}

// Cargar notificaciones desde la API
async function loadNotifications() {
    try {
        const response = await fetch('/api/notifications');
        const data = await response.json();

        if (data.success) {
            notifications = data.notifications;
            unreadCount = data.unread_count;
            renderNotifications();
            updateBadge();
        }
    } catch (error) {
        console.error('Error al cargar notificaciones:', error);
        document.getElementById('notificationsList').innerHTML = `
            <div style="padding: 2rem; text-align: center; color: #ef4444;">
                <i class="bi bi-exclamation-triangle" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                <p>Error al cargar notificaciones</p>
            </div>
        `;
    }
}

// Renderizar notificaciones en el modal
function renderNotifications() {
    const container = document.getElementById('notificationsList');
    const toggleBtn = document.getElementById('toggleReadNotifications');

    // Separar notificaciones leídas y no leídas
    const unreadNotifications = notifications.filter(n => !n.read);
    const readNotifications = notifications.filter(n => n.read);

    // Configurar marked
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true,
            gfm: true
        });
    }

    // Renderizar notificaciones no leídas
    let html = unreadNotifications.map(notif => renderNotificationItem(notif)).join('');

    // Si no hay notificaciones no leídas y no se están mostrando las leídas, mostrar mensaje
    if (unreadNotifications.length === 0 && !showReadNotifications) {
        if (readNotifications.length > 0) {
            // Hay notificaciones leídas pero no nuevas
            html = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 400px; padding: 3rem 2rem; text-align: center; color: #64748b;">
                    <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(139, 92, 246, 0.15)); padding: 3rem; border-radius: 50%; margin-bottom: 2rem; backdrop-filter: blur(10px); box-shadow: 0 8px 32px rgba(59, 130, 246, 0.2);">
                        <i class="bi bi-check-circle" style="font-size: 5rem; color: #10b981; opacity: 0.7;"></i>
                    </div>
                    <p style="font-size: 1.5rem; margin-bottom: 0.75rem; color: #f8fafc; font-weight: 700;">¡Todo al día!</p>
                    <p style="font-size: 1rem; opacity: 0.7; max-width: 450px; line-height: 1.6; color: #94a3b8;">No tienes notificaciones nuevas. Puedes ver tus notificaciones anteriores usando el botón de abajo.</p>
                </div>
            `;
        } else {
            // No hay notificaciones en absoluto
            html = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 400px; padding: 3rem 2rem; text-align: center; color: #64748b;">
                    <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(139, 92, 246, 0.15)); padding: 3rem; border-radius: 50%; margin-bottom: 2rem; backdrop-filter: blur(10px); box-shadow: 0 8px 32px rgba(59, 130, 246, 0.2);">
                        <i class="bi bi-bell-slash" style="font-size: 5rem; color: #3b82f6; opacity: 0.7;"></i>
                    </div>
                    <p style="font-size: 1.5rem; margin-bottom: 0.75rem; color: #f8fafc; font-weight: 700;">No hay notificaciones</p>
                    <p style="font-size: 1rem; opacity: 0.7; max-width: 450px; line-height: 1.6; color: #94a3b8;">Las notificaciones de admin y moderadores aparecerán aquí cuando te envíen mensajes importantes.</p>
                </div>
            `;
        }
    }

    // Renderizar notificaciones leídas si están expandidas
    if (showReadNotifications && readNotifications.length > 0) {
        if (unreadNotifications.length > 0) {
            html += `
                <div class="read-notifications-section" style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 2px solid #334155;">
                    <div style="display: flex; align-items: center; gap: 0.5rem; color: #94a3b8; font-weight: 600; margin-bottom: 1rem;">
                        <i class="bi bi-archive"></i>
                        <span>Notificaciones leídas (${readNotifications.length})</span>
                    </div>
                    ${readNotifications.map(notif => renderNotificationItem(notif)).join('')}
                </div>
            `;
        } else {
            // Solo hay notificaciones leídas, mostrarlas sin separador
            html = `
                <div class="read-notifications-section" style="padding-top: 1rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem; color: #94a3b8; font-weight: 600; margin-bottom: 1rem;">
                        <i class="bi bi-archive"></i>
                        <span>Notificaciones leídas (${readNotifications.length})</span>
                    </div>
                    ${readNotifications.map(notif => renderNotificationItem(notif)).join('')}
                </div>
            `;
        }
    }

    container.innerHTML = html;

    // Mostrar/ocultar botón de toggle según si hay notificaciones leídas
    if (readNotifications.length > 0) {
        toggleBtn.style.display = 'flex';
        toggleBtn.querySelector('span').textContent = showReadNotifications ? 'Ocultar notificaciones leídas' : 'Ver notificaciones leídas';
        toggleBtn.querySelector('i').className = showReadNotifications ? 'bi bi-chevron-up' : 'bi bi-chevron-down';
    } else {
        toggleBtn.style.display = 'none';
    }
}

// Renderizar un item de notificación individual
function renderNotificationItem(notif) {
    const renderedContent = typeof marked !== 'undefined' ? marked.parse(notif.content) : escapeHtml(notif.content);

    return `
    <div class="notification-item ${notif.read ? 'read' : 'unread'}" data-id="${notif.id}">
        <div class="notification-header">
            <div class="notification-title">
                <i class="bi bi-bell${notif.read ? '' : '-fill'}"></i>
                ${escapeHtml(notif.title)}
            </div>
            <div class="notification-meta">
                <span class="notification-sender">
                    <i class="bi bi-person"></i> ${escapeHtml(notif.sender)}
                </span>
                <span class="notification-date">
                    <i class="bi bi-clock"></i> ${formatDate(notif.created_at)}
                </span>
            </div>
        </div>
        <div class="notification-content markdown-content">
            ${renderedContent}
        </div>
        <div class="notification-actions" style="display: flex; gap: 0.5rem; margin-top: 0.75rem;">
            ${!notif.read ? `
                <button class="notification-mark-read-btn" onclick="markAsRead(${notif.id})">
                    <i class="bi bi-check2-all"></i> Marcar como leída
                </button>
            ` : `
                <div style="display: flex; align-items: center; gap: 0.4rem; color: #94a3b8; font-size: 0.8rem;">
                    <i class="bi bi-check-circle"></i> Leída
                </div>
            `}
            ${notif.read ? `
                <button class="notification-delete-btn" onclick="deleteNotification(${notif.id})" title="Eliminar notificación">
                    <i class="bi bi-trash"></i>
                </button>
            ` : ''}
        </div>
    </div>
    `;
}

// Toggle notificaciones leídas
function toggleReadNotifications() {
    showReadNotifications = !showReadNotifications;
    renderNotifications();
}

// Eliminar notificación
async function deleteNotification(notificationId) {
    if (!confirm('¿Estás seguro de que quieres eliminar esta notificación?')) {
        return;
    }

    try {
        const response = await fetch(`/api/notifications/${notificationId}`, {
            method: 'DELETE'
        });
        const data = await response.json();

        if (data.success) {
            // Eliminar localmente
            notifications = notifications.filter(n => n.id !== notificationId);
            renderNotifications();
            updateBadge();
        } else {
            alert('Error: ' + data.message);
        }
    } catch (error) {
        console.error('Error al eliminar notificación:', error);
        alert('Error al eliminar la notificación');
    }
}

// Marcar notificación como leída
async function markAsRead(notificationId) {
    try {
        const response = await fetch(`/api/notifications/${notificationId}/read`, {
            method: 'POST'
        });
        const data = await response.json();

        if (data.success) {
            // Actualizar localmente
            const notif = notifications.find(n => n.id === notificationId);
            if (notif) {
                notif.read = true;
                unreadCount--;
                renderNotifications();
                updateBadge();
            }
        }
    } catch (error) {
        console.error('Error al marcar notificación como leída:', error);
    }
}

// Actualizar badge de notificaciones
function updateBadge() {
    const badge = document.getElementById('notification-badge');
    if (badge) {
        badge.textContent = unreadCount;
        badge.style.display = unreadCount > 0 ? 'inline' : 'none';
    }
}

// Formatear fecha
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Ahora mismo';
    if (diffMins < 60) return `Hace ${diffMins} min`;
    if (diffHours < 24) return `Hace ${diffHours} h`;
    if (diffDays < 7) return `Hace ${diffDays} días`;
    
    return date.toLocaleDateString('es-ES', { 
        day: '2-digit', 
        month: 'short', 
        year: 'numeric' 
    });
}

// Escapar HTML para prevenir XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Cargar notificaciones periódicamente (cada 30 segundos)
setInterval(() => {
    if (document.getElementById('notificationsModal').classList.contains('visible')) {
        loadNotifications();
    } else {
        // Solo actualizar el badge si el modal está cerrado
        fetch('/api/notifications')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    unreadCount = data.unread_count;
                    updateBadge();
                }
            })
            .catch(error => console.error('Error al actualizar badge:', error));
    }
}, 30000);

// Inicializar al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    // Cargar badge inicial
    fetch('/api/notifications')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                unreadCount = data.unread_count;
                updateBadge();
            }
        })
        .catch(error => console.error('Error al cargar badge inicial:', error));

    // Event listener para botón de toggle
    const toggleBtn = document.getElementById('toggleReadNotifications');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleReadNotifications);
    }
});
