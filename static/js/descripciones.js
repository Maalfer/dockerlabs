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
    overlayDiv.style.background = 'radial-gradient(circle at top, rgba(15, 23, 42, 0.92), rgba(15, 23, 42, 0.98))';
    overlayDiv.style.zIndex = '9998';
    overlayDiv.style.opacity = '0';
    overlayDiv.style.transition = 'opacity 0.3s ease';
    overlayDiv.style.backdropFilter = 'blur(6px)';
    overlayDiv.style.webkitBackdropFilter = 'blur(6px)';

    // Crear el contenedor del popup
    var popupDiv = document.createElement('div');
    popupDiv.className = 'popup';
    popupDiv.style.width = '380px';
    popupDiv.style.maxWidth = 'calc(100% - 32px)';
    popupDiv.style.maxHeight = '80%';
    popupDiv.style.background = 'radial-gradient(circle at top left, #0f172a 0%, #020617 60%)';
    popupDiv.style.color = '#e5e7eb';
    popupDiv.style.border = '1.5px solid rgba(59, 130, 246, 0.95)';
    popupDiv.style.borderRadius = '12px';
    popupDiv.style.boxShadow = '0 18px 45px rgba(0, 0, 0, 0.85)';
    popupDiv.style.position = 'fixed';
    popupDiv.style.top = '50%';
    popupDiv.style.left = '50%';
    popupDiv.style.transform = 'translate(-50%, -50%)';
    popupDiv.style.zIndex = '9999';
    popupDiv.style.padding = '22px 24px 20px';
    popupDiv.style.textAlign = 'left';
    popupDiv.style.transition = 'opacity 0.3s ease, transform 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55)';
    popupDiv.style.opacity = '0';
    popupDiv.style.transform = 'translate(-50%, -60%)';
    popupDiv.style.fontFamily = '"Fira Code", monospace';
    popupDiv.style.lineHeight = '1.5';
    popupDiv.style.overflowY = 'auto';
    popupDiv.style.fontSize = '0.9rem';

    // Crear el botón de cierre
    var closeButton = document.createElement('button');
    closeButton.classList.add('modal-close-button');
    closeButton.innerHTML = '&times;';
    closeButton.style.position = 'absolute';
    closeButton.style.top = '10px';
    closeButton.style.right = '10px';
    closeButton.style.width = '26px';
    closeButton.style.height = '26px';
    closeButton.style.display = 'flex';
    closeButton.style.alignItems = 'center';
    closeButton.style.justifyContent = 'center';
    closeButton.style.borderRadius = '9999px';
    closeButton.style.border = '1px solid rgba(148, 163, 184, 0.8)';
    closeButton.style.background = 'radial-gradient(circle at top, #020617, #020617)';
    closeButton.style.color = '#ffffff';
    closeButton.style.fontSize = '18px';
    closeButton.style.fontWeight = '700';
    closeButton.style.lineHeight = '0';
    closeButton.style.cursor = 'pointer';
    closeButton.style.boxShadow = '0 8px 20px rgba(0, 0, 0, 0.85)';
    closeButton.style.transition = 'all 0.2s ease';
    closeButton.addEventListener('mouseover', function () {
        closeButton.style.backgroundColor = '#ef4444';
        closeButton.style.borderColor = 'rgba(248, 113, 113, 0.95)';
        closeButton.style.boxShadow = '0 0 18px rgba(248, 113, 113, 0.8), 0 10px 22px rgba(0, 0, 0, 0.85)';
        closeButton.style.transform = 'scale(1.05)';
    });
    closeButton.addEventListener('mouseout', function () {
        closeButton.style.background = 'radial-gradient(circle at top, #020617, #020617)';
        closeButton.style.border = '1px solid rgba(148, 163, 184, 0.8)';
        closeButton.style.boxShadow = '0 8px 20px rgba(0, 0, 0, 0.85)';
        closeButton.style.transform = 'scale(1)';
    });
    closeButton.addEventListener('click', function () {
        closePopup();
    });

    // Escape user-generated content to prevent XSS
    const escapedNombre = escapeHtml(nombre);
    const escapedDescripcion = escapeHtml(descripcionTexto);

    // Crear el contenido del popup con la descripción pasada como parámetro
    var contenidoPopup = `
        <h2 style="margin: 0 0 10px; font-size: 1rem; color: #e5e7eb;">Aprendizaje en ${escapedNombre}</h2>
        <p style="font-size: 0.86rem; color: #cbd5e1; margin: 0;">
            ${escapedDescripcion}
        </p>
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

    // Función para cerrar el popup
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
