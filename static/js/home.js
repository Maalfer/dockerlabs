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
}

function updateAllButtonCounts() {
    botonmuyfacil();
    botonfacil();
    botonmedio();
    botondificil();
    botontodos();
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

    const items = Array.from(document.querySelectorAll('.maquina-item'));

    const allItems = items.map(item => {
        const onclickAttr = item.getAttribute('onclick');
        const dateMatch = onclickAttr.match(/["'](\d{2}\/\d{2}\/\d{4})["']/) || onclickAttr.match(/(\d{2}\/\d{2}\/\d{4})/);
        const dateStr = dateMatch ? dateMatch[1] : '';

        let dateObj = new Date(0);
        if (dateStr) {
            const parts = dateStr.split('/');
            if (parts.length === 3) {
                dateObj = new Date(parts[2], parts[1] - 1, parts[0]);
            }
        }

        return {
            element: item,
            date: dateObj
        };
    });

    allItems.sort((a, b) => {
        if (order === 'recent') {
            return b.date - a.date;
        } else {
            return a.date - b.date;
        }
    });

    leftColumn.innerHTML = '';
    rightColumn.innerHTML = '';

    allItems.forEach((item, index) => {
        if (index % 2 === 0) {
            leftColumn.appendChild(item.element);
        } else {
            rightColumn.appendChild(item.element);
        }
    });

    updateAllButtonCounts();
}

document.addEventListener('DOMContentLoaded', () => {
    updateAllButtonCounts();
});

document.getElementById('buscador').addEventListener('input', () => {
    updateAllButtonCounts();
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
}
