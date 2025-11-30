function createPopup(contenidoPopup) {
    const style = document.createElement('style');
    style.textContent = `
        @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;700&display=swap');
        .overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 9998;
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        .overlay.visible {
            opacity: 1;
        }
        .popup {
            background-color: #171724;
            color: #ffffff;
            border: 2px solid #b7cfdd;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 9999;
            padding: 20px;
            text-align: center;
            max-width: 90%;
            max-height: 80%;
            overflow-y: auto;
            opacity: 0;
            transform: translate(-50%, -60%);
            transition: opacity 0.3s ease, transform 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55);
            font-family: 'Fira Code', monospace;
        }
        .popup.visible {
            opacity: 1;
            transform: translate(-50%, -50%);
        }
        .popup p, .popup h1 {
            font-family: 'Fira Code', monospace;
        }
        .popup ul {
            list-style-type: none;
            padding: 0;
        }
        .popup li {
            margin: 10px 0;
        }
        .popup a {
            color: white;
            text-decoration: none;
            transition: transform 0.3s ease;
            display: inline-block;
        }
        .popup a:hover {
            transform: scale(1.1);
        }
    `;
    document.head.appendChild(style);

    const overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay';

    const popupDiv = document.createElement('div');
    popupDiv.className = 'popup';

    const closeButton = document.createElement('button');
    closeButton.innerHTML = '&times;';
    closeButton.className = 'modal-close-button';
    closeButton.addEventListener('click', closePopup);

    popupDiv.innerHTML = contenidoPopup;
    popupDiv.appendChild(closeButton);

    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

    setTimeout(() => {
        popupDiv.classList.add('visible');
        overlayDiv.classList.add('visible');
    }, 10);

    overlayDiv.addEventListener('click', (event) => {
        if (event.target === overlayDiv) {
            closePopup();
        }
    });

    function closePopup() {
        popupDiv.classList.remove('visible');
        overlayDiv.classList.remove('visible');
        setTimeout(() => {
            document.body.removeChild(popupDiv);
            document.body.removeChild(overlayDiv);
        }, 300);
    }
}

function showEnlaces(machine) {
    fetch(`/api/writeups/${encodeURIComponent(machine)}`)
        .then(response => {
            if (!response.ok) {
                throw new Error("Error HTTP " + response.status);
            }
            return response.json();
        })
        .then(enlaces => {
            let content = "<ul>";

            if (!enlaces || enlaces.length === 0) {
                content += "<li>No hay enlaces disponibles.</li>";
            } else {
                for (let i = 0; i < enlaces.length; i++) {
                    const enlace = enlaces[i];
                    const icono = enlace.type || "🔗";
                    const nombre = enlace.name || "Autor desconocido";
                    const url = enlace.url || "#";
                    content += `<li>${icono} <a href="${url}" target="_blank" rel="noopener noreferrer">${nombre}</a></li>`;
                }
            }

            content += "</ul>";
            createPopup(content);
        })
        .catch(error => {
            console.error('Error loading the links:', error);
            createPopup("<p>Error al cargar los enlaces de esta máquina.</p>");
        });
}
