// Utility function to escape HTML and prevent XSS attacks
function escapeHtml(text) {
    if (!text) return text;
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function presentacion(nombre, dificultad, tamaño, clase, color, autor_nombre, autor_enlace, fecha, imagen) {
    // Crear el contenedor del overlay
    var overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay';
    overlayDiv.style.position = 'fixed';
    overlayDiv.style.top = '0';
    overlayDiv.style.left = '0';
    overlayDiv.style.width = '100%';
    overlayDiv.style.height = '100%';
    overlayDiv.style.background = 'radial-gradient(circle at top, rgba(15,23,42,0.92), rgba(15,23,42,0.96))';
    overlayDiv.style.zIndex = '9998';
    overlayDiv.style.opacity = '0';
    overlayDiv.style.transition = 'opacity 0.3s ease';
    overlayDiv.style.backdropFilter = 'blur(4px)';

    // Crear el contenedor del popup
    var popupDiv = document.createElement('div');
    popupDiv.className = 'popup';
    popupDiv.style.background = 'radial-gradient(circle at top left, #0f172a 0%, #020617 60%)';
    popupDiv.style.color = '#e5e7eb';
    popupDiv.style.border = '2px solid rgba(59,130,246,0.95)';
    popupDiv.style.borderRadius = '12px';
    popupDiv.style.boxShadow = '0 16px 40px rgba(0, 0, 0, 0.75)';
    popupDiv.style.position = 'absolute';
    popupDiv.style.left = '50%';
    popupDiv.style.transform = 'translate(-50%, -60%)';
    popupDiv.style.zIndex = '9999';
    popupDiv.style.padding = '22px 24px';
    popupDiv.style.textAlign = 'left';
    popupDiv.style.overflowY = 'auto';
    popupDiv.style.transition = 'opacity 0.3s ease, transform 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55)';
    popupDiv.style.opacity = '0';
    popupDiv.style.fontFamily = 'Fira Code, monospace';
    popupDiv.style.width = 'min(520px, 92vw)';
    popupDiv.style.maxHeight = '80vh';

    // Ajustar la posición del popup en función del scroll actual
    var scrollY = window.scrollY;
    popupDiv.style.top = `${scrollY + window.innerHeight / 2}px`;

    // Crear el botón de cierre
    var closeButton = document.createElement('button');
    closeButton.innerHTML = '&times;';
    closeButton.classList.add('modal-close-button');
    closeButton.addEventListener('click', function () {
        closePopup();
    });

    // Crear el contenedor del contenido
    var contentDiv = document.createElement('div');
    contentDiv.style.display = 'flex';
    contentDiv.style.flexDirection = 'column';
    contentDiv.style.alignItems = 'stretch';
    contentDiv.style.width = '100%';

    // Crear el título
    var titulo = document.createElement('h1');
    titulo.textContent = nombre;
    titulo.style.width = '100%';
    titulo.style.textAlign = 'center';
    titulo.style.margin = '0 0 8px';
    titulo.style.fontSize = '1.05rem';
    titulo.style.letterSpacing = '0.10em';
    titulo.style.textTransform = 'uppercase';
    titulo.style.background = 'linear-gradient(135deg, var(--primary-blue-light), var(--accent-cyan))';
    titulo.style.webkitBackgroundClip = 'text';
    titulo.style.webkitTextFillColor = 'transparent';
    titulo.style.backgroundClip = 'text';

    // Líneas para evitar el XSS

    const escapedNombre = escapeHtml(nombre);
    const escapedDificultad = escapeHtml(dificultad);
    const escapedColor = escapeHtml(color);
    const escapedAutorNombre = escapeHtml(autor_nombre);
    const escapedAutorEnlace = escapeHtml(autor_enlace);
    const escapedFecha = escapeHtml(fecha);

    // Subtítulo (dificultad en cabecera)
    var subtitulo = document.createElement('p');
    subtitulo.style.margin = '0 0 14px';
    subtitulo.style.fontSize = '0.8rem';
    subtitulo.style.color = 'var(--text-muted)';
    subtitulo.style.textAlign = 'center';
    subtitulo.style.textTransform = 'uppercase';
    subtitulo.style.letterSpacing = '0.16em';
    subtitulo.innerHTML = `Máquina • <span style="color:${escapedColor}; font-weight:700;">${escapedDificultad}</span>`;

    // Línea divisoria
    var separator = document.createElement('hr');
    separator.style.border = '0';
    separator.style.borderTop = '1px solid rgba(51,65,85,0.9)';
    separator.style.margin = '8px 0 16px';

    // Crear el contenedor de la imagen y la información
    var infoContainer = document.createElement('div');
    infoContainer.style.display = 'flex';
    infoContainer.style.width = '100%';
    infoContainer.style.flexDirection = 'row';
    infoContainer.style.alignItems = 'center';
    infoContainer.style.marginTop = '4px';
    infoContainer.style.gap = '18px';

    // Obtener la URL base de Flask para imágenes
    var imagenUrl = "/static/images/" + imagen;

    // Crear la imagen
    var imagenElem = document.createElement('img');
    imagenElem.src = imagenUrl;
    imagenElem.alt = 'DockerLabs';
    imagenElem.style.width = '140px';
    imagenElem.style.height = '140px';
    imagenElem.style.borderRadius = '12px';
    imagenElem.style.objectFit = 'cover';
    imagenElem.style.border = '1px solid rgba(148,163,184,0.7)';
    imagenElem.style.boxShadow = '0 8px 24px rgba(15,23,42,0.9)';

    // Crear la información
    var infoDiv = document.createElement('div');
    infoDiv.style.flex = '1';
    infoDiv.style.display = 'flex';
    infoDiv.style.flexDirection = 'column';
    infoDiv.style.gap = '6px';
    infoDiv.style.fontSize = '0.9rem';

    infoDiv.innerHTML = `
        <p style="margin: 0;">
            <span style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--text-muted);">Autor</span><br>
            <a href="${escapedAutorEnlace}" target="_blank" style="color: var(--primary-blue-light); text-decoration: none; font-weight: 600;">
                ${escapedAutorNombre}
            </a>
        </p>
        <p style="margin: 0;">
            <span style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--text-muted);">Dificultad</span><br>
            <span style="
                display: inline-block;
                margin-top: 2px;
                padding: 4px 10px;
                border-radius: 999px;
                background: ${escapedColor};
                color: #000;
                font-weight: 700;
                font-size: 0.78rem;
                text-transform: uppercase;
                letter-spacing: 0.1em;
                box-shadow: 0 3px 12px rgba(0,0,0,0.45);
            ">
                ${escapedDificultad}
            </span>
        </p>
        <p style="margin: 0;">
            <span style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--text-muted);">Fecha de creación</span><br>
            <span style="font-weight: 500; color: var(--text-primary);">${escapedFecha}</span>
        </p>
    `;

    // Añadir la imagen y la información al contenedor
    infoContainer.appendChild(imagenElem);
    infoContainer.appendChild(infoDiv);

    // Añadir todo al contenido
    contentDiv.appendChild(titulo);
    contentDiv.appendChild(subtitulo);
    contentDiv.appendChild(separator);
    contentDiv.appendChild(infoContainer);

    popupDiv.appendChild(contentDiv);
    popupDiv.appendChild(closeButton);

    // Añadir el popup y el overlay al body
    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

    // Ajustar el tamaño del popup al cargar la página y al redimensionar la ventana
    ajustarPopup(popupDiv, infoContainer, imagenElem, infoDiv);
    window.addEventListener('resize', function () {
        ajustarPopup(popupDiv, infoContainer, imagenElem, infoDiv);
    });

    // Función para cerrar el popup
    function closePopup() {
        popupDiv.style.opacity = '0';
        popupDiv.style.transform = 'translate(-50%, -60%)';
        overlayDiv.style.opacity = '0';
        setTimeout(function () {
            if (popupDiv.parentNode) {
                document.body.removeChild(popupDiv);
            }
            if (overlayDiv.parentNode) {
                document.body.removeChild(overlayDiv);
            }
        }, 300);
    }

    // Mostrar el popup y el overlay
    setTimeout(function () {
        popupDiv.style.opacity = '1';
        popupDiv.style.transform = 'translate(-50%, -50%)';
        overlayDiv.style.opacity = '1';
    }, 10);

    // Cerrar el popup si se hace clic en el overlay
    overlayDiv.addEventListener('click', function (event) {
        if (event.target === overlayDiv) {
            closePopup();
        }
    });
}

// Función para ajustar el diseño del popup en función del tamaño de la pantalla
function ajustarPopup(popupDiv, infoContainer, imagenElem, infoDiv) {
    var width = window.innerWidth;

    if (width <= 600) { // Ajustar para pantallas pequeñas
        popupDiv.style.width = '90%';
        popupDiv.style.maxHeight = '80vh';
        popupDiv.style.padding = '16px 16px 18px';
        popupDiv.style.fontSize = '14px';

        infoContainer.style.flexDirection = 'column';
        infoContainer.style.alignItems = 'center';
        infoContainer.style.gap = '14px';

        imagenElem.style.marginBottom = '4px';
        infoDiv.style.marginLeft = '0';
        infoDiv.style.textAlign = 'center';
    } else {
        popupDiv.style.width = '520px';
        popupDiv.style.maxHeight = '80vh';
        popupDiv.style.padding = '22px 24px';
        popupDiv.style.fontSize = '15px';

        infoContainer.style.flexDirection = 'row';
        infoContainer.style.alignItems = 'center';
        infoContainer.style.gap = '18px';

        imagenElem.style.marginBottom = '0';
        infoDiv.style.marginLeft = '4px';
        infoDiv.style.textAlign = 'left';
    }
}
