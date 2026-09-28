function mostrarPanelMaquinas(origen) {
    const panelDocker = document.getElementById('panel-docker');
    const panelBunker = document.getElementById('panel-bunker');
    const btnDocker = document.getElementById('btn-docker');
    const btnBunker = document.getElementById('btn-bunker');

    if (origen === 'docker') {
        panelDocker.style.display = 'block';
        panelBunker.style.display = 'none';

        btnDocker.classList.add('active');
        btnBunker.classList.remove('active', 'bunker-active');
    } else {
        panelDocker.style.display = 'none';
        panelBunker.style.display = 'block';

        btnBunker.classList.add('active', 'bunker-active');
        btnDocker.classList.remove('active');
    }
}

// Search functionality
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    
    if (searchInput) {
        // Search on Enter key press
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
        
        // Optional: Search with debounce on typing
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(performSearch, 500);
        });
    }
});

function performSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchTerm = searchInput.value.trim();
    
    // Get current URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    
    // Update or add search parameter
    if (searchTerm) {
        urlParams.set('search', searchTerm);
    } else {
        urlParams.delete('search');
    }
    
    // Reset to page 1 when searching
    urlParams.set('page', '1');
    
    // Reload page with new parameters
    window.location.href = `${window.location.pathname}?${urlParams.toString()}`;
}

// Upload machine logo via AJAX
function uploadMachineLogo(machineId, origen) {
    const fileInput = document.getElementById(`logo-input-${origen}-${machineId}`);
    const file = fileInput.files[0];

    if (!file) {
        alert('No se seleccionó ningún archivo');
        return;
    }

    const formData = new FormData();
    formData.append('logo', file);
    formData.append('machine_id', machineId);
    formData.append('origen', origen);
    formData.append('csrf_token', getCsrfToken());

    // Show loading indicator
    const previewEl = document.getElementById(`preview-${origen}-${machineId}`);
    const filenameEl = document.getElementById(`filename-${origen}-${machineId}`);

    // Optimistic UI update or spinner could go here

    fetch('/api/gestion-maquinas/upload-logo', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error: ' + data.error);
            } else {
                // Update preview with the image_url from the response
                previewEl.src = data.image_url;
                previewEl.style.display = 'block';
                const placeholder = document.getElementById(`placeholder-${origen}-${machineId}`);
                if (placeholder) placeholder.style.display = 'none';

                // Show success message
                showToast(data.message);
            }
        })
        .catch(error => {
            alert('Error al subir la imagen: ' + error);
        });
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.style.cssText = 'position: fixed; bottom: 20px; right: 20px; background: #10b981; color: white; padding: 12px 24px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); z-index: 10010; animation: slideIn 0.3s forwards; font-weight: 500;';
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Add keyframes for toast
const style = document.createElement('style');
style.innerHTML = `
    @keyframes slideIn { from { transform: translateY(100%); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
    @keyframes slideOut { from { transform: translateY(0); opacity: 1; } to { transform: translateY(100%); opacity: 0; } }
`;
document.head.appendChild(style);

// === Difficulty Coloring ===
function updateDifficultyColor(select) {
    const value = select.value;
    // Remove old classes
    select.classList.remove('text-green', 'text-blue', 'text-yellow', 'text-red');

    // Add new class based on value
    if (value === 'Muy Fácil') select.classList.add('text-green');
    else if (value === 'Fácil') select.classList.add('text-blue');
    else if (value === 'Medio') select.classList.add('text-yellow');
    else if (value === 'Difícil') select.classList.add('text-red');
}

// === Toggle filter row visibility ===
function toggleFilters(tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;

    const filterRow = table.querySelector('.filter-row');
    if (!filterRow) return;

    if (filterRow.style.display === 'none') {
        filterRow.style.display = '';
    } else {
        filterRow.style.display = 'none';
    }
}

// === Column filtering & Initialization ===
document.addEventListener('DOMContentLoaded', function () {
    // Initialize difficulty colors
    document.querySelectorAll('select[name="dificultad"]').forEach(s => {
        updateDifficultyColor(s);
        s.addEventListener('change', (e) => updateDifficultyColor(e.target));
    });

    // Initialize filters
    const filters = document.querySelectorAll('.column-filter');
    filters.forEach(filter => {
        filter.addEventListener('input', applyColumnFilters);
        filter.addEventListener('change', applyColumnFilters);
    });

    function applyColumnFilters() {
        const tables = ['tablaDocker', 'tablaBunker'];

        tables.forEach(tableId => {
            const table = document.getElementById(tableId);
            if (!table) return;

            const rows = table.querySelectorAll('tbody tr');
            const tableFilters = table.querySelectorAll('.column-filter');

            const filterValues = {};
            tableFilters.forEach(f => {
                const column = f.dataset.column;
                filterValues[column] = f.value.trim().toLowerCase();
            });

            rows.forEach(row => {
                let show = true;

                const getValue = (index, selector) => {
                    const cell = row.cells[index];
                    if (!cell) return '';
                    const input = cell.querySelector(selector);
                    return (input?.value || cell.textContent || '').trim().toLowerCase();
                };

                if (filterValues.nombre && !getValue(0, 'input[name="nombre"]').includes(filterValues.nombre)) show = false;
                if (filterValues.dificultad && getValue(1, 'select[name="dificultad"]') !== filterValues.dificultad) show = false;
                if (filterValues.autor && !getValue(2, 'input[name="autor"]').includes(filterValues.autor)) show = false;

                row.style.display = show ? '' : 'none';
            });
        });
    }
});

// === Guest Access Toggle ===
function toggleGuestAccess(machineId, btn) {
    if (!confirm('¿Quieres cambiar el estado de acceso para invitados de esta máquina?')) return;

    const data = new FormData();
    data.append('id', machineId);
    data.append('csrf_token', getCsrfToken()); // Helper function assumed to exist or need implementation

    fetch('/api/gestion-maquinas/toggle-guest-access', {
        method: 'POST',
        body: data
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error: ' + data.error);
            } else {
                // Update UI
                const icon = btn.querySelector('i');
                if (data.guest_access) {
                    // Unlocked
                    icon.className = 'bi bi-unlock-fill text-success';
                    btn.title = 'Acceso permitido a invitados';
                    btn.dataset.active = 'true';
                    showToast('Máquina desbloqueada para invitados');
                } else {
                    // Locked
                    icon.className = 'bi bi-lock-fill text-danger';
                    btn.title = 'Acceso bloqueado a invitados';
                    btn.dataset.active = 'false';
                    showToast('Máquina bloqueada para invitados');
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Ocurrió un error al intentar cambiar el estado.');
        });
}

// === Modal de estadisticas de maquina (writeups, descargas, valoracion) ===
let lastStatsModalTrigger = null;

document.addEventListener('DOMContentLoaded', function () {
    // Delegacion: cualquier boton .machine-name-link, en cualquiera de las
    // dos tablas, abre el modal con el id/nombre que lleva en sus data-*.
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.machine-name-link');
        if (btn) openMachineStatsModal(btn.dataset.machineId, btn.dataset.machineName, btn);
    });

    const statsModal = document.getElementById('machineStatsModal');
    if (statsModal) {
        // Cerrar al hacer clic en el backdrop (mismo patron que el resto de
        // modales del sitio, definidos en base.html).
        statsModal.addEventListener('click', function (e) {
            if (e.target === statsModal) closeMachineStatsModal();
        });
    }

    // Cerrar con Escape y devolver el foco al boton que abrio el modal.
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && statsModal && statsModal.classList.contains('visible')) {
            closeMachineStatsModal();
        }
    });
});

function closeMachineStatsModal() {
    closeModal('machineStatsModal');
    if (lastStatsModalTrigger) {
        lastStatsModalTrigger.focus();
        lastStatsModalTrigger = null;
    }
}

function openMachineStatsModal(machineId, machineName, triggerEl) {
    lastStatsModalTrigger = triggerEl || null;

    const subtitle = document.getElementById('machineStatsModalSubtitle');
    const body = document.getElementById('machineStatsModalBody');
    if (subtitle) subtitle.textContent = machineName || '';
    if (body) {
        body.innerHTML = '';
        const loading = document.createElement('div');
        loading.className = 'machine-stats-loading';
        loading.textContent = 'Cargando...';
        body.appendChild(loading);
    }

    openModal('machineStatsModal');

    const closeBtn = document.querySelector('#machineStatsModal .modal-close-button');
    if (closeBtn) closeBtn.focus();

    fetch(`/api/gestion-maquinas/machine-stats/${encodeURIComponent(machineId)}`)
        .then(response => response.json().then(data => ({ ok: response.ok, data })))
        .then(({ ok, data }) => {
            if (!body) return;
            body.innerHTML = '';

            if (!ok || data.error) {
                const err = document.createElement('div');
                err.className = 'machine-stats-error';
                err.textContent = data.error || 'No se pudieron cargar las estadísticas.';
                body.appendChild(err);
                return;
            }

            body.appendChild(buildStatCard('bi-file-earmark-text', data.writeups, 'Writeups publicados'));
            body.appendChild(buildStatCard('bi-download', data.descargas, 'Descargas'));

            const ratingLabel = data.rating_count > 0
                ? `Valoración (${data.rating_count} ${data.rating_count === 1 ? 'voto' : 'votos'})`
                : 'Valoración (sin votos)';
            body.appendChild(buildStatCard('bi-star-fill', `${data.rating_avg} / 5`, ratingLabel));
        })
        .catch(() => {
            if (!body) return;
            body.innerHTML = '';
            const err = document.createElement('div');
            err.className = 'machine-stats-error';
            err.textContent = 'Error de red al cargar las estadísticas.';
            body.appendChild(err);
        });
}

function buildStatCard(iconClass, value, label) {
    const card = document.createElement('div');
    card.className = 'machine-stat-card';

    const icon = document.createElement('i');
    icon.className = `bi ${iconClass} machine-stat-icon`;
    icon.setAttribute('aria-hidden', 'true');

    const valueEl = document.createElement('div');
    valueEl.className = 'machine-stat-value';
    valueEl.textContent = value;

    const labelEl = document.createElement('div');
    labelEl.className = 'machine-stat-label';
    labelEl.textContent = label;

    const textWrap = document.createElement('div');
    textWrap.appendChild(valueEl);
    textWrap.appendChild(labelEl);

    card.appendChild(icon);
    card.appendChild(textWrap);
    return card;
}

// === Modal de detalles editables (enlace autor, descripcion, link
// descarga). Estos campos ya no se muestran en la tabla porque no entraban;
// siguen viviendo como inputs ocultos dentro del <form> de cada fila, y
// este modal solo es una vista/edicion ampliada de esos mismos campos. ===
let currentDetailsRow = null; // { form, enlaceInput, descTextarea, linkInput }

document.addEventListener('DOMContentLoaded', function () {
    const detailsModal = document.getElementById('machineDetailsModal');
    if (detailsModal) {
        detailsModal.addEventListener('click', function (e) {
            if (e.target === detailsModal) closeMachineDetailsModal();
        });
    }

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && detailsModal && detailsModal.classList.contains('visible')) {
            closeMachineDetailsModal();
        }
    });
});

function openMachineDetailsModal(triggerBtn) {
    const row = triggerBtn.closest('tr');
    if (!row) return;

    const form = row.querySelector('form.d-contents');
    const nameBtn = row.querySelector('.machine-name-link');
    if (!form) return;

    const enlaceInput = form.querySelector('[name="enlace_autor"]');
    const descTextarea = form.querySelector('[name="descripcion"]');
    const linkInput = form.querySelector('[name="link_descarga"]');

    currentDetailsRow = { form, enlaceInput, descTextarea, linkInput, triggerBtn };

    const subtitle = document.getElementById('machineDetailsModalSubtitle');
    if (subtitle) subtitle.textContent = nameBtn ? nameBtn.dataset.machineName : '';

    document.getElementById('detailsEnlaceAutor').value = enlaceInput ? enlaceInput.value : '';
    document.getElementById('detailsDescripcion').value = descTextarea ? descTextarea.value : '';
    document.getElementById('detailsLinkDescarga').value = linkInput ? linkInput.value : '';

    openModal('machineDetailsModal');
    document.getElementById('detailsEnlaceAutor').focus();
}

function closeMachineDetailsModal() {
    closeModal('machineDetailsModal');
    if (currentDetailsRow && currentDetailsRow.triggerBtn) {
        currentDetailsRow.triggerBtn.focus();
    }
    currentDetailsRow = null;
}

function saveMachineDetailsModal() {
    if (!currentDetailsRow) return;
    const { form, enlaceInput, descTextarea, linkInput } = currentDetailsRow;

    if (enlaceInput) enlaceInput.value = document.getElementById('detailsEnlaceAutor').value;
    if (descTextarea) descTextarea.value = document.getElementById('detailsDescripcion').value;
    if (linkInput) linkInput.value = document.getElementById('detailsLinkDescarga').value;

    closeModal('machineDetailsModal');
    currentDetailsRow = null;

    // Mismo submit que dispara el boton "Guardar" de la fila: un POST de
    // formulario normal (sin AJAX), asi que se guardan a la vez todos los
    // campos de la fila (nombre, dificultad, autor, categoria, etc.).
    form.requestSubmit();
}
