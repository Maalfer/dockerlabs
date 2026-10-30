// === Rechazar maquina pendiente via AJAX ===
// El <form> de "Eliminar" de cada tarjeta es un <form method="POST"> normal:
// sin esto, al enviarlo el navegador navega a la respuesta JSON cruda de la
// API (`/api/admin/pending-machines/{id}/reject`) y la pinta como si fuera la
// pagina entera. Se intercepta para enviarlo con fetch y mostrar el resultado
// como un toast, quitando la tarjeta de la lista si se elimina con exito.
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.pm-reject-form').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();

            const btn = form.querySelector('button[type="submit"]');
            if (btn) btn.disabled = true;

            fetch(form.action, { method: 'POST', body: new FormData(form) })
                .then(response => response.json().then(data => ({ ok: response.ok, data })))
                .then(({ ok, data }) => {
                    if (!ok || data.error) {
                        showToast(data.error || 'No se pudo eliminar la máquina.', 'error');
                        if (btn) btn.disabled = false;
                        return;
                    }

                    showToast(data.message || 'Máquina eliminada correctamente.');

                    const card = form.closest('.pm-card');
                    if (card) card.remove();
                    updatePendingCount();
                })
                .catch(() => {
                    showToast('Error de red al comunicar con el servidor.', 'error');
                    if (btn) btn.disabled = false;
                });
        });
    });
});

function updatePendingCount() {
    const counter = document.querySelector('.pending-count');
    if (!counter) return;
    const remaining = document.querySelectorAll('.pm-card').length;
    counter.innerHTML = `<i class="bi bi-hdd-stack"></i> ${remaining} máquina${remaining !== 1 ? 's' : ''}`;

    if (remaining === 0) {
        const grid = document.querySelector('.pending-grid');
        if (grid) {
            grid.outerHTML = `
                <div class="pending-empty">
                    <i class="bi bi-check2-circle"></i>
                    <p>No hay máquinas pendientes de revisión</p>
                    <span>// todo está al día</span>
                </div>`;
        }
    }
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    const bg = type === 'error' ? '#dc3545' : '#10b981';
    toast.style.cssText = `position: fixed; bottom: 20px; right: 20px; background: ${bg}; color: white; padding: 12px 24px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); z-index: 10010; animation: slideIn 0.3s forwards; font-weight: 500;`;
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

const _pendingToastStyle = document.createElement('style');
_pendingToastStyle.innerHTML = `
    @keyframes slideIn { from { transform: translateY(100%); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
    @keyframes slideOut { from { transform: translateY(0); opacity: 1; } to { transform: translateY(100%); opacity: 0; } }
`;
document.head.appendChild(_pendingToastStyle);
