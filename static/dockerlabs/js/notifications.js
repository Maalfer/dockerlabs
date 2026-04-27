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

// ==================== INVITACIONES TAB ====================

let currentNotificationsTab = 'notificaciones';

function switchNotificationsTab(tab) {
    currentNotificationsTab = tab;
    const btnNotif = document.getElementById('tab-btn-notificaciones');
    const btnInvit = document.getElementById('tab-btn-invitaciones');
    const btnSolic = document.getElementById('tab-btn-solicitudes');

    if (tab === 'notificaciones') {
        btnNotif.style.background = 'rgba(59, 130, 246, 0.15)';
        btnNotif.style.color = '#3b82f6';
        btnInvit.style.background = 'transparent';
        btnInvit.style.color = '#64748b';
        if (btnSolic) {
            btnSolic.style.background = 'transparent';
            btnSolic.style.color = '#64748b';
        }
        document.getElementById('tab-notificaciones').style.display = 'block';
        document.getElementById('tab-invitaciones').style.display = 'none';
        if (document.getElementById('tab-solicitudes')) {
            document.getElementById('tab-solicitudes').style.display = 'none';
        }
        loadNotifications();
    } else if (tab === 'invitaciones') {
        btnInvit.style.background = 'rgba(139, 92, 246, 0.15)';
        btnInvit.style.color = '#8b5cf6';
        btnNotif.style.background = 'transparent';
        btnNotif.style.color = '#64748b';
        if (btnSolic) {
            btnSolic.style.background = 'transparent';
            btnSolic.style.color = '#64748b';
        }
        document.getElementById('tab-notificaciones').style.display = 'none';
        document.getElementById('tab-invitaciones').style.display = 'block';
        if (document.getElementById('tab-solicitudes')) {
            document.getElementById('tab-solicitudes').style.display = 'none';
        }
        loadInvitaciones();
    } else if (tab === 'solicitudes') {
        if (btnSolic) {
            btnSolic.style.background = 'rgba(34, 197, 94, 0.15)';
            btnSolic.style.color = '#22c55e';
        }
        btnNotif.style.background = 'transparent';
        btnNotif.style.color = '#64748b';
        btnInvit.style.background = 'transparent';
        btnInvit.style.color = '#64748b';
        document.getElementById('tab-notificaciones').style.display = 'none';
        document.getElementById('tab-invitaciones').style.display = 'none';
        if (document.getElementById('tab-solicitudes')) {
            document.getElementById('tab-solicitudes').style.display = 'block';
        }
        loadSolicitudes();
    }
}

async function loadInvitaciones() {
    const container = document.getElementById('invitacionesList');
    if (!container) return;

    container.innerHTML = `
        <div style="padding: 3rem 2rem; text-align: center; color: #64748b;">
            <div style="background: rgba(139, 92, 246, 0.1); padding: 2rem; border-radius: 20px; display: inline-block; margin-bottom: 1.5rem;">
                <i class="bi bi-arrow-repeat" style="font-size: 4rem; color: #8b5cf6; animation: spin 1s linear infinite;"></i>
            </div>
            <p style="font-size: 1.2rem; margin-bottom: 0.5rem; color: #94a3b8;">Cargando invitaciones...</p>
        </div>
    `;

    try {
        const response = await fetch('/api/equipos/invitaciones/mis-invitaciones');
        const data = await response.json();

        if (data.success) {
            updateInvitacionesBadge(data.invitaciones.length);

            if (data.invitaciones.length === 0) {
                container.innerHTML = `
                    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 300px; padding: 3rem 2rem; text-align: center; color: #64748b;">
                        <div style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(59, 130, 246, 0.15)); padding: 3rem; border-radius: 50%; margin-bottom: 2rem; backdrop-filter: blur(10px); box-shadow: 0 8px 32px rgba(139, 92, 246, 0.2);">
                            <i class="bi bi-envelope-slash" style="font-size: 5rem; color: #8b5cf6; opacity: 0.7;"></i>
                        </div>
                        <p style="font-size: 1.5rem; margin-bottom: 0.75rem; color: #f8fafc; font-weight: 700;">No tienes invitaciones</p>
                        <p style="font-size: 1rem; opacity: 0.7; max-width: 450px; line-height: 1.6; color: #94a3b8;">Las invitaciones a equipos aparecerán aquí cuando alguien te invite.</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = data.invitaciones.map(inv => `
                <div class="notification-item" data-invitation-id="${inv.id}" style="border-left: 3px solid #8b5cf6;">
                    <div class="notification-header">
                        <div class="notification-title" style="color: #8b5cf6;">
                            <i class="bi bi-people-fill"></i>
                            Invitación a equipo
                        </div>
                        <div class="notification-meta">
                            <span class="notification-date">
                                <i class="bi bi-clock"></i> ${formatDate(inv.created_at)}
                            </span>
                        </div>
                    </div>
                    <div class="notification-content">
                        <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;">
                            ${inv.team.imagen_url ? `
                                <img src="${inv.team.imagen_url}" style="width: 48px; height: 48px; border-radius: 12px; object-fit: cover; border: 2px solid #8b5cf6;">
                            ` : `
                                <div style="width: 48px; height: 48px; border-radius: 12px; background: linear-gradient(135deg, #3b82f6, #8b5cf6); display: flex; align-items: center; justify-content: center;">
                                    <i class="bi bi-people-fill" style="font-size: 1.5rem; color: white;"></i>
                                </div>
                            `}
                            <div>
                                <div style="font-weight: 600; color: #f1f5f9; font-size: 1.1rem;">${escapeHtml(inv.team.nombre)}</div>
                                <div style="font-size: 0.85rem; color: #64748b;">
                                    ${inv.team.member_count}/${inv.team.max_members} miembros
                                </div>
                            </div>
                        </div>
                        <p style="color: #94a3b8; margin: 0;">
                            <i class="bi bi-person"></i> Invitado por <strong style="color: #f1f5f9;">${escapeHtml(inv.invited_by)}</strong>
                        </p>
                    </div>
                    <div class="notification-actions" style="display: flex; gap: 0.5rem; margin-top: 0.75rem;">
                        <button class="notification-mark-read-btn" onclick="responderInvitacionNotif(${inv.id}, true)" style="background: #8b5cf6; color: white;">
                            <i class="bi bi-check-lg"></i> Aceptar
                        </button>
                        <button class="notification-delete-btn" onclick="responderInvitacionNotif(${inv.id}, false)" style="background: transparent; color: #64748b; border: 1px solid #334155;">
                            <i class="bi bi-x-lg"></i> Rechazar
                        </button>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = `
                <div style="padding: 2rem; text-align: center; color: #ef4444;">
                    <i class="bi bi-exclamation-triangle" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                    <p>Error al cargar invitaciones</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error al cargar invitaciones:', error);
        container.innerHTML = `
            <div style="padding: 2rem; text-align: center; color: #ef4444;">
                <i class="bi bi-exclamation-triangle" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                <p>Error al cargar invitaciones</p>
            </div>
        `;
    }
}

async function responderInvitacionNotif(invitationId, accept) {
    try {
        const response = await fetch('/api/equipos/invitaciones/responder', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                invitation_id: invitationId,
                accept: accept
            })
        });

        const data = await response.json();

        if (data.success) {
            alert(data.message);
            // Reload invitaciones
            loadInvitaciones();
        } else {
            alert('Error: ' + data.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al procesar la invitación');
    }
}

function updateInvitacionesBadge(count) {
    const badge = document.getElementById('invitaciones-badge');
    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline' : 'none';
    }
}

async function loadSolicitudes() {
    const container = document.getElementById('solicitudesList');
    if (!container) return;

    container.innerHTML = `
        <div style="padding: 3rem 2rem; text-align: center; color: #64748b;">
            <div style="background: rgba(34, 197, 94, 0.1); padding: 2rem; border-radius: 20px; display: inline-block; margin-bottom: 1.5rem;">
                <i class="bi bi-arrow-repeat" style="font-size: 4rem; color: #22c55e; animation: spin 1s linear infinite;"></i>
            </div>
            <p style="font-size: 1.2rem; margin-bottom: 0.5rem; color: #94a3b8;">Cargando solicitudes...</p>
        </div>
    `;

    try {
        // First get user's team
        const teamResponse = await fetch('/api/equipos/mi-equipo/info');
        const teamData = await teamResponse.json();

        if (!teamData.success || !teamData.tiene_equipo) {
            container.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 300px; padding: 3rem 2rem; text-align: center; color: #64748b;">
                    <div style="background: linear-gradient(135deg, rgba(34, 197, 94, 0.15), rgba(59, 130, 246, 0.15)); padding: 3rem; border-radius: 50%; margin-bottom: 2rem; backdrop-filter: blur(10px); box-shadow: 0 8px 32px rgba(34, 197, 94, 0.2);">
                        <i class="bi bi-people" style="font-size: 5rem; color: #22c55e; opacity: 0.7;"></i>
                    </div>
                    <p style="font-size: 1.5rem; margin-bottom: 0.75rem; color: #f8fafc; font-weight: 700;">No tienes equipo</p>
                    <p style="font-size: 1rem; opacity: 0.7; max-width: 450px; line-height: 1.6; color: #94a3b8;">Las solicitudes para unirse a tu equipo aparecerán aquí cuando seas miembro de uno.</p>
                </div>
            `;
            return;
        }

        const teamId = teamData.team.id;

        // Get join requests for the team
        const response = await fetch(`/api/equipos/${teamId}/solicitudes`);
        const data = await response.json();

        if (data.success) {
            updateSolicitudesBadge(data.solicitudes.length);

            if (data.solicitudes.length === 0) {
                container.innerHTML = `
                    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 300px; padding: 3rem 2rem; text-align: center; color: #64748b;">
                        <div style="background: linear-gradient(135deg, rgba(34, 197, 94, 0.15), rgba(59, 130, 246, 0.15)); padding: 3rem; border-radius: 50%; margin-bottom: 2rem; backdrop-filter: blur(10px); box-shadow: 0 8px 32px rgba(34, 197, 94, 0.2);">
                            <i class="bi bi-inbox" style="font-size: 5rem; color: #22c55e; opacity: 0.7;"></i>
                        </div>
                        <p style="font-size: 1.5rem; margin-bottom: 0.75rem; color: #f8fafc; font-weight: 700;">No hay solicitudes</p>
                        <p style="font-size: 1rem; opacity: 0.7; max-width: 450px; line-height: 1.6; color: #94a3b8;">Las solicitudes para unirse a tu equipo aparecerán aquí.</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = data.solicitudes.map(req => `
                <div class="notification-item" data-request-id="${req.id}" style="border-left: 3px solid #22c55e;">
                    <div class="notification-header">
                        <div class="notification-title" style="color: #22c55e;">
                            <i class="bi bi-person-plus-fill"></i>
                            Solicitud para unirse
                        </div>
                        <div class="notification-meta">
                            <span class="notification-date">
                                <i class="bi bi-clock"></i> ${formatDate(req.created_at)}
                            </span>
                        </div>
                    </div>
                    <div class="notification-content">
                        <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;">
                            <img src="${req.user.profile_image_url}" style="width: 48px; height: 48px; border-radius: 50%; object-fit: cover; border: 2px solid #22c55e;">
                            <div>
                                <div style="font-weight: 600; color: #f1f5f9; font-size: 1.1rem;">${escapeHtml(req.user.username)}</div>
                                <div style="font-size: 0.85rem; color: #64748b;">
                                    ${req.user.puntos} pts
                                </div>
                            </div>
                        </div>
                        <p style="color: #94a3b8; margin: 0;">
                            Quiere unirse a tu equipo
                        </p>
                    </div>
                    <div class="notification-actions" style="display: flex; gap: 0.5rem; margin-top: 0.75rem;">
                        <button class="notification-mark-read-btn" onclick="responderSolicitudNotif(${req.id}, true)" style="background: #22c55e; color: white;">
                            <i class="bi bi-check-lg"></i> Aceptar
                        </button>
                        <button class="notification-delete-btn" onclick="responderSolicitudNotif(${req.id}, false)" style="background: transparent; color: #64748b; border: 1px solid #334155;">
                            <i class="bi bi-x-lg"></i> Rechazar
                        </button>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = `
                <div style="padding: 2rem; text-align: center; color: #ef4444;">
                    <i class="bi bi-exclamation-triangle" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                    <p>Error al cargar solicitudes</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error al cargar solicitudes:', error);
        container.innerHTML = `
            <div style="padding: 2rem; text-align: center; color: #ef4444;">
                <i class="bi bi-exclamation-triangle" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                <p>Error al cargar solicitudes</p>
            </div>
        `;
    }
}

async function responderSolicitudNotif(requestId, accept) {
    try {
        const response = await fetch('/api/equipos/solicitudes/responder', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                request_id: requestId,
                accept: accept
            })
        });

        const data = await response.json();

        if (data.success) {
            alert(data.message);
            loadSolicitudes();
        } else {
            alert('Error: ' + data.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al procesar la solicitud');
    }
}

function updateSolicitudesBadge(count) {
    const badge = document.getElementById('solicitudes-badge');
    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline' : 'none';
    }
}

// Update original loadNotifications to also update badges
const originalLoadNotifications = loadNotifications;
loadNotifications = async function() {
    await originalLoadNotifications();
    // Also load invitaciones count for badge
    try {
        const response = await fetch('/api/equipos/invitaciones/mis-invitaciones');
        const data = await response.json();
        if (data.success) {
            updateInvitacionesBadge(data.invitaciones.length);
        }
    } catch (e) {
        // Silent fail for badge update
    }
    // Load solicitudes count for badge
    try {
        const teamResponse = await fetch('/api/equipos/mi-equipo/info');
        const teamData = await teamResponse.json();
        if (teamData.success && teamData.tiene_equipo) {
            const teamId = teamData.team.id;
            const solicResponse = await fetch(`/api/equipos/${teamId}/solicitudes`);
            const solicData = await solicResponse.json();
            if (solicData.success) {
                updateSolicitudesBadge(solicData.solicitudes.length);
            }
        }
    } catch (e) {
        // Silent fail for badge update
    }
};

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

    // Cargar conteo de invitaciones
    fetch('/api/equipos/invitaciones/mis-invitaciones')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateInvitacionesBadge(data.invitaciones.length);
            }
        })
        .catch(error => console.error('Error al cargar invitaciones inicial:', error));

    // Cargar conteo de solicitudes
    fetch('/api/equipos/mi-equipo/info')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.tiene_equipo) {
                const teamId = data.team.id;
                fetch(`/api/equipos/${teamId}/solicitudes`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            updateSolicitudesBadge(data.solicitudes.length);
                        }
                    })
                    .catch(error => console.error('Error al cargar solicitudes inicial:', error));
            }
        })
        .catch(error => console.error('Error al cargar equipo inicial:', error));

    // Event listener para botón de toggle
    const toggleBtn = document.getElementById('toggleReadNotifications');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleReadNotifications);
    }
});
