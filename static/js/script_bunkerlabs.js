function filterList() {
    const searchQuery = document.getElementById('search').value.toLowerCase();
    const filter = document.getElementById('filter').value;
    const items = document.querySelectorAll('.item');

    items.forEach(item => {
        const itemName = item.querySelector('span').textContent.toLowerCase();
        const itemDifficulty = item.classList.contains(filter) || filter === 'todos';

        if (itemName.includes(searchQuery) && itemDifficulty) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}

function botonmuyfacil() {
    const searchQuery = document.getElementById('search').value.toLowerCase();
    const filter = 'muy-facil';
    const items = document.querySelectorAll('.item');

    items.forEach(item => {
        const itemName = item.querySelector('span').textContent.toLowerCase();
        const itemDifficulty = item.classList.contains(filter);

        if (itemName.includes(searchQuery) && itemDifficulty) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}

function botonfacil() {
    const searchQuery = document.getElementById('search').value.toLowerCase();
    const filter = 'facil';
    const items = document.querySelectorAll('.item');

    items.forEach(item => {
        const itemName = item.querySelector('span').textContent.toLowerCase();
        const itemDifficulty = item.classList.contains(filter);

        if (itemName.includes(searchQuery) && itemDifficulty) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}

function botonmedio() {
    const searchQuery = document.getElementById('search').value.toLowerCase();
    const filter = 'medio';
    const items = document.querySelectorAll('.item');

    items.forEach(item => {
        const itemName = item.querySelector('span').textContent.toLowerCase();
        const itemDifficulty = item.classList.contains(filter);

        if (itemName.includes(searchQuery) && itemDifficulty) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}

function botondificil() {
    const searchQuery = document.getElementById('search').value.toLowerCase();
    const filter = 'dificil';
    const items = document.querySelectorAll('.item');

    items.forEach(item => {
        const itemName = item.querySelector('span').textContent.toLowerCase();
        const itemDifficulty = item.classList.contains(filter);

        if (itemName.includes(searchQuery) && itemDifficulty) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}

function botontodos() {
    const searchQuery = document.getElementById('search').value.toLowerCase();
    const items = document.querySelectorAll('.item');

    items.forEach(item => {
        const itemName = item.querySelector('span').textContent.toLowerCase();

        if (itemName.includes(searchQuery)) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}
