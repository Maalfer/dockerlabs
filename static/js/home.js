function updateGridLayout() {
    const items = document.querySelectorAll('.maquina-item');
    const visibleItems = Array.from(items).filter(item => item.style.display !== 'none');

    // Remove the class from all items first
    items.forEach(item => item.classList.remove('last-visible-odd'));

    // If there's an odd number of visible items, add the class to the last one
    if (visibleItems.length % 2 === 1 && visibleItems.length > 0) {
        visibleItems[visibleItems.length - 1].classList.add('last-visible-odd');
    }
}

function updateButtonCount(buttonId, filterClass) {
    document.querySelectorAll('#filtro-dificultad > button').forEach((e) => e.classList.remove('selected'));
    document.querySelector('#filtro-dificultad > button#' + buttonId).classList.add('selected');
    const searchInput = document.getElementById('buscador');
    const items = document.querySelectorAll('.maquina-item');
    const buttons = document.querySelectorAll('#filtro-dificultad button');
    let itemCount = 0;
    items.forEach(item => {
        const itemName = item.querySelector('span').textContent.toLowerCase();
        const isVisible = item.classList.contains(filterClass) || filterClass === 'todos';

        if (itemName.includes(searchInput.value.toLowerCase()) && isVisible) {
            item.style.display = 'flex';
            itemCount++;
        } else {
            item.style.display = 'none';
        }
    });

    const button = document.getElementById(buttonId);
    button.textContent = `${button.textContent.split(' (')[0]} (${itemCount})`;

    // Update grid layout after filtering
    updateGridLayout();
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

function filterByCompleted() {
    const items = document.querySelectorAll('.maquina-item');
    let count = 0;
    items.forEach(item => {
        if (item.classList.contains('completada')) {
            item.style.display = 'flex';
            count++;
        } else {
            item.style.display = 'none';
        }
    });
    document.querySelectorAll('#filtro-dificultad > button').forEach((e) => e.classList.remove('selected'));
    updateGridLayout();
}

function filterByUncompleted() {
    const items = document.querySelectorAll('.maquina-item');
    let count = 0;
    items.forEach(item => {
        if (!item.classList.contains('completada')) {
            item.style.display = 'flex';
            count++;
        } else {
            item.style.display = 'none';
        }
    });
    document.querySelectorAll('#filtro-dificultad > button').forEach((e) => e.classList.remove('selected'));
    updateGridLayout();
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

        button.textContent = `${button.textContent.split(' (')[0]} (${itemCount})`;
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
    const leftColumn = document.querySelector('.columna-izquierda');
    const rightColumn = document.querySelector('.columna-derecha');

    if (!leftColumn || !rightColumn) {
        const items = Array.from(document.querySelectorAll('.maquina-item'));
        items.sort((a, b) => {
            const getDate = (element) => {
                const onclick = element.getAttribute('onclick');
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

        if (order === 'reset') {
            location.reload();
            return;
        }

        items.forEach(item => list.appendChild(item));
        return;
    }



    updateAllButtonCounts();
}

document.addEventListener('DOMContentLoaded', () => {
    updateAllButtonCounts();
});

document.getElementById('buscador').addEventListener('input', () => {
    updateAllButtonCounts();

    // Re-apply the current filter to update grid visibility
    const selectedBtn = document.querySelector('#filtro-dificultad > button.selected');
    if (selectedBtn) {
        switch (selectedBtn.id) {
            case 'boton-muy-facil': botonmuyfacil(); break;
            case 'boton-facil': botonfacil(); break;
            case 'boton-medio': botonmedio(); break;
            case 'boton-dificil': botondificil(); break;
            case 'boton-todos': botontodos(); break;
        }
    }
});

function filterByCategory(category) {
    const items = document.querySelectorAll('.maquina-item');
    items.forEach(item => {
        const itemCategory = item.getAttribute('data-category');
        if (category === '' || itemCategory === category) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
    document.querySelectorAll('#filtro-dificultad button').forEach(btn => btn.classList.remove('selected'));
    document.getElementById('boton-todos').classList.add('selected');
    updateGridLayout();
}
