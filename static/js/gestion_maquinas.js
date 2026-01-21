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

    fetch('/gestion-maquinas/upload-logo', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error: ' + data.error);
            } else {
                // Update hidden field
                const hiddenField = document.querySelector(`.imagen-field-${machineId}`);
                if (hiddenField) {
                    hiddenField.value = data.image_path;
                }

                // Update preview
                previewEl.src = `/static/images/${data.image_path}`;
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
    toast.style.cssText = 'position: fixed; bottom: 20px; right: 20px; background: #10b981; color: white; padding: 12px 24px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); z-index: 9999; animation: slideIn 0.3s forwards; font-weight: 500;';
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

                if (filterValues.nombre && !getValue(1, 'input[name="nombre"]').includes(filterValues.nombre)) show = false;
                if (filterValues.dificultad && getValue(2, 'select[name="dificultad"]') !== filterValues.dificultad) show = false;
                if (filterValues.autor && !getValue(3, 'input[name="autor"]').includes(filterValues.autor)) show = false;
                if (filterValues.fecha && !getValue(5, 'input[name="fecha"]').includes(filterValues.fecha)) show = false;

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

    fetch('/gestion-maquinas/toggle-guest-access', {
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

function getCsrfToken() {
    return document.querySelector('input[name="csrf_token"]')?.value || '';
}
