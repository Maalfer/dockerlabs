document.addEventListener('DOMContentLoaded', function () {
    // Search filter
    const searchInput = document.getElementById('search');
    if (searchInput) {
        searchInput.addEventListener('input', filterItems);
    }

    // Filter buttons
    const filterButtons = document.querySelectorAll('.btn-filter');
    filterButtons.forEach(btn => {
        btn.addEventListener('click', function () {
            const difficulty = this.getAttribute('data-difficulty');
            filterDifficulty(difficulty);
        });
    });

    // Machine item clicks (Presentation)
    const items = document.querySelectorAll('.item-selectable');
    items.forEach(item => {
        item.addEventListener('click', function (e) {
            // Avoid triggering if clicking on action buttons
            if (e.target.closest('.actions')) return;

            const name = this.getAttribute('data-nombre');
            const size = this.getAttribute('data-tamanio');
            const cssClass = this.getAttribute('data-clase');
            const color = this.getAttribute('data-color');
            const author = this.getAttribute('data-autor');
            const authorLink = this.getAttribute('data-enlace-autor');
            const date = this.getAttribute('data-fecha');
            const image = this.getAttribute('data-imagen');
            const desc = this.getAttribute('data-descripcion');

            if (typeof presentacion === 'function') {
                presentacion(name, '', size, cssClass, color, author, authorLink, date, image, desc);
            }
        });
    });

    // Resaltar la máquina compartida cuando se llega mediante ?maquina=...
    highlightSharedMachine();

    const downloadBtns = document.querySelectorAll('.btn-download');
    const isGuest = document.querySelector('.machines-grid')?.getAttribute('data-is-guest') === 'true';

    downloadBtns.forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            const link = this.getAttribute('data-link');

            if (link) {
                window.open(link, '_blank');
            } else if (isGuest) {
                alert('El modo de prueba no permite descargar máquinas.');
            }
        });
    });
});

let currentFilter = 'all';

function filterDifficulty(category) {
    currentFilter = category;

    // Update active state of buttons
    const buttons = document.querySelectorAll('.btn-filter');
    buttons.forEach(btn => {
        if (btn.getAttribute('data-difficulty') === category) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Show/hide Real Environments banner
    const realBanner = document.getElementById('real-env-banner');
    if (realBanner) {
        if (category === 'real') {
            realBanner.style.display = 'block';
        } else {
            realBanner.style.display = 'none';
        }
    }

    filterItems();
}

function filterItems() {
    const searchInput = document.getElementById('search');
    if (!searchInput) return;

    const searchQuery = searchInput.value.toLowerCase();
    const items = document.querySelectorAll('.item');

    items.forEach(item => {
        const span = item.querySelector('span');
        if (!span) return;

        const itemName = span.textContent.toLowerCase();
        // Check if item has the class corresponding to the filter, or if filter is 'all'
        const matchesDifficulty = currentFilter === 'all' || item.classList.contains(currentFilter);
        const matchesSearch = itemName.includes(searchQuery);

        if (matchesDifficulty && matchesSearch) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}

// Resalta ("fosforito") la máquina que llega compartida por enlace y abre su modal
function highlightSharedMachine() {
    let sharedRaw;
    try {
        sharedRaw = new URLSearchParams(window.location.search).get('maquina');
    } catch (e) {
        return;
    }
    if (!sharedRaw) return;

    // Limpiar la URL para que un refresco no vuelva a disparar el efecto
    try {
        window.history.replaceState({}, document.title, window.location.pathname);
    } catch (e) { /* noop */ }

    const target = sharedRaw.trim().toLowerCase();
    const items = document.querySelectorAll('.item-selectable');
    let matched = null;
    items.forEach(item => {
        const name = (item.getAttribute('data-nombre') || '').trim().toLowerCase();
        if (!matched && name === target) matched = item;
    });
    if (!matched) return;

    // Marca visual
    matched.classList.add('shared-highlight');

    // Chip flotante "Compartida"
    if (!matched.querySelector('.shared-badge')) {
        const badge = document.createElement('div');
        badge.className = 'shared-badge';
        badge.innerHTML = '<i class="bi bi-stars"></i> Compartida';
        matched.appendChild(badge);
    }

    // Desplazar suavemente hasta la máquina
    setTimeout(() => {
        matched.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 250);

    // Abrir el modal de presentación automáticamente (salvo que esté bloqueada para invitados)
    if (!matched.classList.contains('locked-guest-item')) {
        setTimeout(() => {
            matched.click();
        }, 1100);
    }
}
