// Construye y muestra el modal de presentación de una máquina.
// Todas las variables dinámicas se escapan con escapeHtml() para evitar XSS.
function presentacion(nombre, dificultad, tamaño, clase, color, autor_nombre, autor_enlace, fecha, imagen, descripcion) {
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

    // 2. Popup (grid: imagen | contenido, igual que el modal de DockerLabs)
    var popupDiv = document.createElement('div');
    popupDiv.className = 'bunker-modal-popup';

    // 3. Columna izquierda: imagen
    var imageContainer = document.createElement('div');
    imageContainer.className = 'bunker-modal-image-container';

    var imagenUrl;
    if (!escapedImagen) {
        imagenUrl = "/static/dockerlabs/images/logos/logo_120.png";
    } else if (escapedImagen.includes('/img/')) {
        imagenUrl = escapedImagen;
    } else {
        function sanitizeImagePath(path) {
            path = path.replace(/\.\./g, '');
            path = path.replace(/^\/+/, '');
            path = path.replace(/[^a-zA-Z0-9\-_./]/g, '');
            return path;
        }
        imagenUrl = "/static/" + sanitizeImagePath(escapedImagen);
    }

    var imagenElem = document.createElement('img');
    imagenElem.className = 'bunker-modal-image';
    imagenElem.src = imagenUrl;
    imagenElem.alt = escapedNombre;
    // Borde brillante dinámico basado en dificultad si existe
    if (dificultad && escapedColor) {
        imagenElem.style.borderColor = escapedColor;
        imagenElem.style.boxShadow = `0 10px 30px rgba(0, 0, 0, 0.5), 0 0 24px ${escapedColor}40`; // 40 = 25% opacity hex
    }

    imageContainer.appendChild(imagenElem);

    // 4. Columna derecha: contenido
    var contentDiv = document.createElement('div');
    contentDiv.className = 'bunker-modal-content';

    // Botón cerrar
    var closeButton = document.createElement('button');
    closeButton.className = 'bunker-modal-close';
    closeButton.innerHTML = '&times;';
    closeButton.addEventListener('click', closePopup);

    // Botón compartir (arriba a la izquierda de la columna de contenido)
    var shareButton = document.createElement('button');
    shareButton.className = 'bunker-modal-share';
    shareButton.type = 'button';
    shareButton.setAttribute('aria-label', 'Compartir máquina');
    shareButton.innerHTML = '<i class="bi bi-share-fill"></i><span class="bunker-share-text">Compartir</span>';

    // Tooltip de feedback ("¡Enlace copiado!")
    var shareToast = document.createElement('span');
    shareToast.className = 'bunker-share-toast';
    shareButton.appendChild(shareToast);

    shareButton.addEventListener('click', function (e) {
        e.stopPropagation();
        // El enlace usa el dominio público de BunkerLabs
        var shareUrl = window.location.origin + '/bunkerlabs?maquina=' + encodeURIComponent(nombre);

        function showCopied(ok) {
            shareToast.textContent = ok ? '¡Enlace copiado!' : 'Copia manual: ' + shareUrl;
            shareButton.classList.add('copied');
            setTimeout(function () { shareButton.classList.remove('copied'); }, 2200);
        }

        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(shareUrl).then(function () {
                showCopied(true);
            }).catch(function () {
                fallbackCopy(shareUrl, showCopied);
            });
        } else {
            fallbackCopy(shareUrl, showCopied);
        }
    });

    function fallbackCopy(text, cb) {
        try {
            var ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.focus();
            ta.select();
            var ok = document.execCommand('copy');
            document.body.removeChild(ta);
            cb(ok);
        } catch (err) {
            cb(false);
        }
    }

    // Título
    var titulo = document.createElement('h1');
    titulo.className = 'bunker-modal-title';
    titulo.textContent = escapedNombre;

    // Subtítulo
    var subtitulo = document.createElement('p');
    subtitulo.className = 'bunker-modal-subtitle';
    if (dificultad) {
        // Usamos el color dinámico solo aquí
        subtitulo.innerHTML = `MÁQUINA • <span style="color: ${escapedColor}">${escapedDificultad}</span>`;
    } else {
        subtitulo.innerHTML = `MÁQUINA BUNKERLABS`;
    }

    // Separador
    var separator = document.createElement('div');
    separator.className = 'bunker-modal-separator';

    // Info (Autor / Dificultad / Fecha)
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

    // Descripción
    var descDiv = document.createElement('div');
    descDiv.className = 'bunker-modal-description';
    descDiv.innerHTML = `
        <p class="bunker-modal-description-label">Sobre esta máquina</p>
        <p class="bunker-modal-description-text">${escapedDescripcion || 'Sin descripción disponible.'}</p>
    `;

    // Ensamblaje columna derecha
    contentDiv.appendChild(closeButton);
    contentDiv.appendChild(shareButton);
    contentDiv.appendChild(titulo);
    contentDiv.appendChild(subtitulo);
    contentDiv.appendChild(separator);
    contentDiv.appendChild(infoDiv);
    contentDiv.appendChild(descDiv);

    // Ensamblaje popup
    popupDiv.appendChild(imageContainer);
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
