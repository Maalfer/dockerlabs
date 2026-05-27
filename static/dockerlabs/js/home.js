const ITEMS_PER_PAGE = 50;
let currentPage = 1;
let currentFilter = { difficulty: 'todos', category: '', completed: null }; // null = all, true = completed, false = uncompleted

// Debounce: evita llamadas en ráfaga que provocan forced reflow
function debounce(fn, delay) {
    let timer;
    return function(...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

function updateGridLayout() {
    const items = document.querySelectorAll('.maquina-item');
    const visibleItems = Array.from(items).filter(item => item.style.display !== 'none');

    // Lectura de estado ANTES de cualquier escritura (evita forced reflow)
    const hasOdd = visibleItems.length % 2 === 1 && visibleItems.length > 0;
    const lastItem = hasOdd ? visibleItems[visibleItems.length - 1] : null;

    // Agrupar todas las escrituras DOM en un rAF para evitar forzar recalculo de layout
    requestAnimationFrame(() => {
        // Remove class from all items first
        items.forEach(item => item.classList.remove('last-visible-odd'));
        // If there's an odd number of visible items, add the class to the last one
        if (lastItem) {
            lastItem.classList.add('last-visible-odd');
        }
    });
}

function setFiltroLabel(texto, color) {
    const label = document.getElementById('filtro-label');
    const btn = document.getElementById('filtro-dificultad-btn');
    label.textContent = texto;
    btn.style.color = color;
    btn.style.borderColor = color;
}

function getFilteredItems() {
    const searchInput = document.getElementById('buscador');
    const searchTerm = (searchInput?.value || '').toLowerCase();
    const items = document.querySelectorAll('.maquina-item');
    return Array.from(items).filter(item => {
        const itemName = item.querySelector('span')?.textContent?.toLowerCase() || '';
        const itemCategory = item.getAttribute('data-category') || '';
        const isCompleted = item.classList.contains('completada');
        const difficultyClass = ['muy-facil', 'facil', 'medio', 'dificil'].find(c => item.classList.contains(c)) || 'todos';

        const matchSearch = itemName.includes(searchTerm);
        const matchDifficulty = currentFilter.difficulty === 'todos' || difficultyClass === currentFilter.difficulty;
        const matchCategory = !currentFilter.category || itemCategory === currentFilter.category;
        const matchCompleted = currentFilter.completed === null || (currentFilter.completed === true && isCompleted) || (currentFilter.completed === false && !isCompleted);

        return matchSearch && matchDifficulty && matchCategory && matchCompleted;
    });
}

function renderPagination(filteredItems) {
    const totalItems = filteredItems.length;
    const totalPages = Math.max(1, Math.ceil(totalItems / ITEMS_PER_PAGE));
    const container = document.getElementById('pagination-container');
    if (!container) return;

    container.innerHTML = '';
    container.style.display = 'flex';

    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    const end = Math.min(start + ITEMS_PER_PAGE, totalItems);
    const wrapper = document.createElement('div');
    wrapper.className = 'pagination-wrapper';

    const info = document.createElement('span');
    info.className = 'pagination-info';
    info.textContent = `${start + 1}-${end} de ${totalItems}`;
    wrapper.appendChild(info);

    const nav = document.createElement('nav');
    nav.className = 'pagination-nav';
    nav.setAttribute('aria-label', 'Paginación');

    const prevBtn = document.createElement('button');
    prevBtn.className = 'pagination-btn';
    prevBtn.innerHTML = '&laquo; Anterior';
    prevBtn.disabled = currentPage <= 1;
    prevBtn.onclick = () => { if (currentPage > 1) goToPage(currentPage - 1); };
    nav.appendChild(prevBtn);

    const pagesWrap = document.createElement('span');
    pagesWrap.className = 'pagination-pages';
    const maxVisible = 5;
    let pageStart = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let pageEnd = Math.min(totalPages, pageStart + maxVisible - 1);
    if (pageEnd - pageStart < maxVisible - 1) pageStart = Math.max(1, pageEnd - maxVisible + 1);
    for (let i = pageStart; i <= pageEnd; i++) {
        const btn = document.createElement('button');
        btn.className = 'pagination-btn' + (i === currentPage ? ' active' : '');
        btn.textContent = i;
        btn.onclick = () => goToPage(i);
        pagesWrap.appendChild(btn);
    }
    nav.appendChild(pagesWrap);

    const nextBtn = document.createElement('button');
    nextBtn.className = 'pagination-btn';
    nextBtn.innerHTML = 'Siguiente &raquo;';
    nextBtn.disabled = currentPage >= totalPages;
    nextBtn.onclick = () => { if (currentPage < totalPages) goToPage(currentPage + 1); };
    nav.appendChild(nextBtn);

    wrapper.appendChild(nav);
    container.appendChild(wrapper);
}

function goToPage(page) {
    const filtered = getFilteredItems();
    const totalPages = Math.max(1, Math.ceil(filtered.length / ITEMS_PER_PAGE));
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    applyPagination();
}

function applyPagination() {
    const filtered = getFilteredItems();
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;
    const pageItems = filtered.slice(start, end);

    const allItems = document.querySelectorAll('.maquina-item');
    const pageSet = new Set(pageItems);
    allItems.forEach(item => {
        item.style.display = pageSet.has(item) ? 'flex' : 'none';
    });

    updateGridLayout();
    renderPagination(filtered);
}

function updateButtonCount(buttonId, filterClass) {
    document.querySelectorAll('.dificultad-item').forEach(e => e.classList.remove('active'));
    const btn = document.getElementById(buttonId);
    if (btn) btn.classList.add('active');
    
    currentFilter.difficulty = filterClass;
    currentFilter.completed = null;
    currentPage = 1;
    applyPagination();

    updateAllButtonCounts();
}

function botonmuyfacil() {
    updateButtonCount('boton-muy-facil', 'muy-facil');
}

function botonfacil() {
    updateButtonCount('boton-facil', 'facil');
}

function botonmedio() {
    updateButtonCount('boton-medio', 'medio');
}

function botondificil() {
    updateButtonCount('boton-dificil', 'dificil');
}

function botontodos() {
    updateButtonCount('boton-todos', 'todos');
}

function filterByCompleted(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    currentFilter.completed = true;
    currentFilter.difficulty = 'todos';
    currentPage = 1;
    document.querySelectorAll('.dificultad-item').forEach(e => e.classList.remove('active'));
    applyPagination();
    updateAllButtonCounts();
    
    // Cerrar dropdown
    const dropdown = document.querySelector('.btn-filter');
    if (dropdown) {
        const bsDropdown = bootstrap.Dropdown.getInstance(dropdown);
        if (bsDropdown) bsDropdown.hide();
    }
}

function filterByUncompleted(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    currentFilter.completed = false;
    currentFilter.difficulty = 'todos';
    currentPage = 1;
    document.querySelectorAll('.dificultad-item').forEach(e => e.classList.remove('active'));
    applyPagination();
    updateAllButtonCounts();
    
    // Cerrar dropdown
    const dropdown = document.querySelector('.btn-filter');
    if (dropdown) {
        const bsDropdown = bootstrap.Dropdown.getInstance(dropdown);
        if (bsDropdown) bsDropdown.hide();
    }
}

function updateAllButtonCounts() {
    const buttons = [
        { id: 'boton-muy-facil', class: 'muy-facil' },
        { id: 'boton-facil', class: 'facil' },
        { id: 'boton-medio', class: 'medio' },
        { id: 'boton-dificil', class: 'dificil' },
        { id: 'boton-todos', class: 'todos' }
    ];

    const searchInput = document.getElementById('buscador');
    const items = document.querySelectorAll('.maquina-item');

    buttons.forEach(btn => {
        const button = document.getElementById(btn.id);
        let itemCount = 0;

        items.forEach(item => {
            const itemName = item.querySelector('span').textContent.toLowerCase();
            const isVisible = item.classList.contains(btn.class) || btn.class === 'todos';

            if (itemName.includes(searchInput.value.toLowerCase()) && isVisible) {
                itemCount++;
            }
        });

        if (button) {
            const countSpan = button.querySelector('.count');
            if (countSpan) {
                countSpan.textContent = ` (${itemCount})`;
            }
        }
    });

    // Call updateGridLayout only once after all counts are updated
    updateGridLayout();
}

let currentSortOrder = 'reset';

function sortByDate(order) {
    currentSortOrder = order;

    if (order === 'reset') {
        location.reload();
        return;
    }

    const list = document.querySelector('.lista');
    if (!list) {
        console.error('No se encontró el contenedor .lista');
        return;
    }

    const items = Array.from(document.querySelectorAll('.maquina-item'));
    
    items.sort((a, b) => {
        const getDate = (element) => {
            const onclick = element.getAttribute('onclick') || '';
            const match = onclick.match(/["'](\d{2}\/\d{2}\/\d{4})["']/) || onclick.match(/(\d{2}\/\d{2}\/\d{4})/);
            if (match) {
                const [day, month, year] = match[1].split('/');
                return new Date(`${year}-${month}-${day}`);
            }
            return new Date(0);
        };

        const dateA = getDate(a);
        const dateB = getDate(b);

        if (order === 'recent') {
            return dateB - dateA;
        } else if (order === 'oldest') {
            return dateA - dateB;
        } else {
            return 0;
        }
    });

    // DocumentFragment: un único reflow en vez de uno por item
    const frag = document.createDocumentFragment();
    items.forEach(item => frag.appendChild(item));
    list.appendChild(frag);
    
    currentPage = 1;
    applyPagination();
    updateAllButtonCounts();
}

document.addEventListener('DOMContentLoaded', () => {
    // rAF: batching del render inicial en un único frame — evita forced reflow
    requestAnimationFrame(() => {
        updateAllButtonCounts();
        applyPagination();
    });
});

const buscador = document.getElementById('buscador');
if (buscador) {
    // debounce 150ms: evita applyPagination+updateAllButtonCounts en cada tecla (forced reflow)
    buscador.addEventListener('input', debounce(() => {
        currentPage = 1;
        applyPagination();
        updateAllButtonCounts();
    }, 150));
}

function filterByCategory(category, event) {
    // Prevenir comportamiento por defecto si se pasó el evento
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    currentFilter.category = category;
    currentFilter.difficulty = 'todos';
    currentFilter.completed = null;
    currentPage = 1;
    
    // Resetear botones de dificultad
    document.querySelectorAll('.dificultad-item').forEach(btn => btn.classList.remove('active'));
    const todosBtn = document.getElementById('boton-todos');
    if (todosBtn) todosBtn.classList.add('active');
    
    applyPagination();
    updateAllButtonCounts();
    
    // Cerrar dropdown de Bootstrap manualmente
    const dropdown = document.querySelector('.btn-category');
    if (dropdown) {
        const bsDropdown = bootstrap.Dropdown.getInstance(dropdown);
        if (bsDropdown) bsDropdown.hide();
    }
}
