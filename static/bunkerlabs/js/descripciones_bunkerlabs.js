// Utility function to escape HTML and prevent XSS attacks
function escapeHtml(text) {
    if (!text) return text;
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function descripcion(nombre, descripcionTexto) {
    // Crear el contenedor del overlay
    var overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay';
    overlayDiv.style.position = 'fixed';
    overlayDiv.style.top = '0';
    overlayDiv.style.left = '0';
    overlayDiv.style.width = '100%';
    overlayDiv.style.height = '100%';
    overlayDiv.style.background = 'rgba(0, 0, 0, 0.5)';
    overlayDiv.style.zIndex = '9998';
    overlayDiv.style.opacity = '0';
    overlayDiv.style.transition = 'opacity 0.3s ease';

    // Crear el contenedor del popup
    var popupDiv = document.createElement('div');
    popupDiv.className = 'popup';
    popupDiv.style.width = '360px';
    popupDiv.style.backgroundColor = '#101016';
    popupDiv.style.color = '#ffffff';
    popupDiv.style.border = '1px solid #cccccc';
    popupDiv.style.borderRadius = '10px';
    popupDiv.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.2)';
    popupDiv.style.position = 'fixed';
    popupDiv.style.top = '50%';
    popupDiv.style.left = '50%';
    popupDiv.style.transform = 'translate(-50%, -50%)';
    popupDiv.style.zIndex = '9999';
    popupDiv.style.padding = '20px';
    popupDiv.style.textAlign = 'center';
    popupDiv.style.transition = 'opacity 0.3s ease, transform 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55)';
    popupDiv.style.opacity = '0';
    popupDiv.style.transform = 'translate(-50%, -60%)';

    // Crear el botÃ³n de cierre
    var closeButton = document.createElement('button');
    closeButton.classList.add('modal-close-button');
    closeButton.innerHTML = '&times;';
    closeButton.style.position = 'absolute';
    closeButton.style.top = '10px';
    closeButton.style.right = '15px';
    closeButton.style.background = 'none';
    closeButton.style.border = 'none';
    closeButton.style.color = '#ffffff';
    closeButton.style.fontSize = '24px';
    closeButton.style.cursor = 'pointer';
    closeButton.addEventListener('click', function () {
        closePopup();
    });

    // Escape user-generated content to prevent XSS
    const escapedNombre = escapeHtml(nombre);
    const escapedDescripcion = escapeHtml(descripcionTexto);

    // Crear el contenido del popup con la descripciÃ³n pasada como parÃ¡metro
    var contenidoPopup = `
        <h2 style="margin-bottom: 10px;">Aprendizaje en ${escapedNombre}</h2>
        <p style="font-size: 14px; color: #ccc;">${escapedDescripcion}</p>
    `;

    popupDiv.innerHTML = contenidoPopup;
    popupDiv.appendChild(closeButton);
    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

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

    // FunciÃ³n para cerrar el popup
    function closePopup() {
        popupDiv.style.opacity = '0';
        popupDiv.style.transform = 'translate(-50%, -60%)';
        overlayDiv.style.opacity = '0';
        setTimeout(function () {
            document.body.removeChild(popupDiv);
            document.body.removeChild(overlayDiv);
        }, 300);
    }
}