// Utility function to escape HTML and prevent XSS attacks
function escapeHtml(text) {
    if (!text) return text;
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function presentacion(nombre, dificultad, tamaño, clase, color, autor_nombre, autor_enlace, fecha, imagen, descripcion) {
    // Escapar variables
    const escapedNombre = escapeHtml(nombre);
    const escapedDificultad = escapeHtml(dificultad);
    const escapedColor = escapeHtml(color); // El color viene de backend (ej: #f87171)
    const escapedAutorNombre = escapeHtml(autor_nombre);
    const escapedAutorEnlace = escapeHtml(autor_enlace);
    const escapedFecha = escapeHtml(fecha);
    const escapedImagen = escapeHtml(imagen);
    const escapedDescripcion = escapeHtml(descripcion);

    // 1. Overlay
    var overlayDiv = document.createElement('div');
    overlayDiv.className = 'bunker-modal-overlay';

    // 2. Popup
    var popupDiv = document.createElement('div');
    popupDiv.className = 'bunker-modal-popup';

    // 3. Botón cerrar
    var closeButton = document.createElement('button');
    closeButton.className = 'bunker-modal-close';
    closeButton.innerHTML = '&times;';
    closeButton.addEventListener('click', closePopup);

    // 4. Estructura interna
    var contentDiv = document.createElement('div');
    contentDiv.className = 'bunker-modal-content';

    // 5. Título
    var titulo = document.createElement('h1');
    titulo.className = 'bunker-modal-title';
    titulo.textContent = escapedNombre;

    // 6. Subtítulo
    var subtitulo = document.createElement('p');
    subtitulo.className = 'bunker-modal-subtitle';
    if (dificultad) {
        // Usamos el color dinámico solo aquí
        subtitulo.innerHTML = `MÁQUINA • <span style="color: ${escapedColor}">${escapedDificultad}</span>`;
    } else {
        subtitulo.innerHTML = `MÁQUINA BUNKERLABS`;
    }

    // 7. Separador
    var separator = document.createElement('div');
    separator.className = 'bunker-modal-separator';

    // 8. Cuerpo (Imagen + Info)
    var bodyDiv = document.createElement('div');
    bodyDiv.className = 'bunker-modal-body';

    // Imagen
    function sanitizeImagePath(path) {
        if (!path) return 'dockerlabs/images/logos/logo.png';
        path = path.replace(/\.\./g, '');
        path = path.replace(/^\/+/, '');
        path = path.replace(/[^a-zA-Z0-9\-_./]/g, '');
        return path;
    }
    var sanitizedImagePath = sanitizeImagePath(escapedImagen);
    var imagenUrl;

    imagenUrl = "/static/" + sanitizedImagePath;

    var imagenElem = document.createElement('img');
    imagenElem.className = 'bunker-modal-image';
    imagenElem.src = imagenUrl;
    imagenElem.alt = escapedNombre;
    // Borde brillante dinámico basado en dificultad si existe
    if (dificultad && escapedColor) {
        imagenElem.style.borderColor = escapedColor;
        imagenElem.style.boxShadow = `0 10px 30px ${escapedColor}40`; // 40 = 25% opacity hex
    }

    // Info Textual
    var infoDiv = document.createElement('div');
    infoDiv.className = 'bunker-modal-info';

    // Autor
    infoDiv.innerHTML = `
        <div class="bunker-modal-row">
            <span class="bunker-modal-label">Autor</span>
            <span class="bunker-modal-value">
                <a href="${escapedAutorEnlace}" target="_blank">${escapedAutorNombre}</a>
            </span>
        </div>
    `;

    // Dificultad Badge (Solo si existe)
    if (dificultad) {
        infoDiv.innerHTML += `
        <div class="bunker-modal-row">
            <span class="bunker-modal-label">Dificultad</span>
            <div>
                <span class="bunker-modal-badge" style="background: ${escapedColor}; box-shadow: 0 0 15px ${escapedColor}">
                    ${escapedDificultad}
                </span>
            </div>
        </div>
        `;
    }

    // Fecha
    infoDiv.innerHTML += `
        <div class="bunker-modal-row">
            <span class="bunker-modal-label">Fecha de lanzamiento</span>
            <span class="bunker-modal-value">${escapedFecha}</span>
        </div>
    `;

    // Ensamblaje
    bodyDiv.appendChild(imagenElem);
    bodyDiv.appendChild(infoDiv);

    // 9. Descripción (Nueva sección)
    var descDiv = document.createElement('div');
    descDiv.style.width = '100%';
    descDiv.style.marginTop = '1.5rem';
    descDiv.innerHTML = `
        <div class="bunker-modal-separator"></div>
        <p class="bunker-modal-label" style="margin-bottom: 0.5rem; text-align: center;">Sobre esta máquina</p>
        <p style="
            font-size: 0.95rem; 
            line-height: 1.6; 
            color: #cbd5e1; 
            text-align: justify; 
            background: rgba(255, 255, 255, 0.03); 
            padding: 1rem; 
            border-radius: 8px; 
            border: 1px solid rgba(255, 255, 255, 0.05);
        ">
            ${escapedDescripcion || 'Sin descripción disponible.'}
        </p>
    `;

    contentDiv.appendChild(titulo);
    contentDiv.appendChild(subtitulo);
    contentDiv.appendChild(separator);
    contentDiv.appendChild(bodyDiv);
    contentDiv.appendChild(descDiv); // Append description

    popupDiv.appendChild(closeButton);
    popupDiv.appendChild(contentDiv);

    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

    // Listeners
    overlayDiv.addEventListener('click', function (e) {
        if (e.target === overlayDiv) closePopup();
    });

    function closePopup() {
        // Animaciones de salida (reverse)
        // Eliminamos la animación de entrada para que no bloquee la transición
        popupDiv.style.animation = 'none';

        overlayDiv.style.opacity = '0';
        popupDiv.style.opacity = '0';
        popupDiv.style.transform = 'translate(-50%, -48%) scale(0.98)';

        setTimeout(() => {
            if (popupDiv.parentNode) document.body.removeChild(popupDiv);
            if (overlayDiv.parentNode) document.body.removeChild(overlayDiv);
        }, 150);
    }

    // Mostrar
    setTimeout(function () {
        popupDiv.style.opacity = '1';
        popupDiv.style.transform = 'translate(-50%, -50%)';
        overlayDiv.style.opacity = '1';
    }, 10);
}

// Función para ajustar el diseño del popup en función del tamaño de la pantalla
function ajustarPopup(popupDiv, infoContainer, imagenElem, infoDiv) {
    // La nueva estructura CSS maneja la mayoría de esto, pero mantenemos compatibilidad básica si se llama
    // El CSS ya tiene media queries, así que esta función puede ser simplificada o eliminada en el futuro.
}
