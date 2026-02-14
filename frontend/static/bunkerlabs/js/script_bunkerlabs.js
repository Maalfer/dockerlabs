document.addEventListener('DOMContentLoaded', function () {
    // Search filter
    const searchInput = document.getElementById('search');
    if (searchInput) {
        searchInput.addEventListener('input', filterItems);
    }

    // Ranking button
    const rankingBtn = document.getElementById('btn-ranking');
    if (rankingBtn) {
        rankingBtn.addEventListener('click', () => {
            if (typeof ranking === 'function') ranking();
        });
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

    // Upload (Flag) buttons
    const uploadBtns = document.querySelectorAll('.btn-upload');
    uploadBtns.forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            const name = this.getAttribute('data-nombre');
            if (typeof subir_flag === 'function') subir_flag(name);
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

// Writeup Modal Functions
function openWriteupModal(machineName) {
    const modal = document.getElementById('writeupModal');
    const title = document.getElementById('writeup-machine-title');
    const content = document.getElementById('writeup-content');

    title.textContent = `Writeups - ${machineName}`;
    content.innerHTML = '<p class="loading-text">Cargando writeups...</p>';
    modal.style.display = 'block';

    // Cargar writeups desde la API
    fetch(`/bunkerlabs/api/writeups/${encodeURIComponent(machineName)}`)
        .then(response => response.json())
        .then(data => {
            if (data.writeups && data.writeups.length > 0) {
                const writeupsByType = {
                    texto: data.writeups.filter(w => w.tipo === 'texto'),
                    video: data.writeups.filter(w => w.tipo === 'video')
                };

                let html = '';

                if (writeupsByType.texto.length > 0) {
                    html += '<h4 class="writeup-section-title">📄 Writeups en Texto</h4><ul class="writeup-list">';
                    writeupsByType.texto.forEach(w => {
                        if (w.locked) {
                            html += `<li class="locked"><i class="bi bi-lock-fill"></i> <span class="locked-text">${w.autor} (Bloqueado)</span></li>`;
                        } else {
                            html += `<li><a href="${w.url}" target="_blank" rel="noopener noreferrer">${w.autor}</a></li>`;
                        }
                    });
                    html += '</ul>';
                }

                if (writeupsByType.video.length > 0) {
                    html += '<h4 class="writeup-section-title">🎥 Writeups en Vídeo</h4><ul class="writeup-list">';
                    writeupsByType.video.forEach(w => {
                        if (w.locked) {
                            html += `<li class="locked"><i class="bi bi-lock-fill"></i> <span class="locked-text">${w.autor} (Bloqueado)</span></li>`;
                        } else {
                            html += `<li><a href="${w.url}" target="_blank" rel="noopener noreferrer">${w.autor}</a></li>`;
                        }
                    });
                    html += '</ul>';
                }

                content.innerHTML = html;
            } else {
                content.innerHTML = '<p class="no-writeups">No hay writeups disponibles para esta máquina.</p>';
            }
        })
        .catch(error => {
            console.error('Error loading writeups:', error);
            content.innerHTML = '<p class="error-text">Error al cargar writeups. Inténtalo de nuevo.</p>';
        });
}

function closeWriteupModal() {
    const modal = document.getElementById('writeupModal');
    modal.style.display = 'none';
}

// Event listeners
document.addEventListener('DOMContentLoaded', function () {
    // Click en botones de writeup
    document.addEventListener('click', function (e) {
        if (e.target.closest('.btn-writeup')) {
            const button = e.target.closest('.btn-writeup');
            const machineName = button.getAttribute('data-nombre');
            openWriteupModal(machineName);
        }
    });

    // Cerrar modal al hacer clic fuera
    window.addEventListener('click', function (e) {
        const modal = document.getElementById('writeupModal');
        if (e.target === modal) {
            closeWriteupModal();
        }
    });
});
