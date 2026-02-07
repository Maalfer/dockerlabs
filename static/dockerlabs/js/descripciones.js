// Utility function to escape HTML and prevent XSS attacks
function escapeHtml(text) {
    if (!text) return text;
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function descripcion(nombre, descripcionTexto) {
    // Inject Styles (if not already present)
    const styleId = 'minimal-modal-styles-desc';
    if (!document.getElementById(styleId)) {
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

            .overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(15, 23, 42, 0.6);
                backdrop-filter: blur(12px);
                z-index: 9998;
                opacity: 0;
                transition: opacity 0.2s ease;
            }

            .overlay.visible {
                opacity: 1;
            }

            .popup {
                background: #1e293b;
                color: #f1f5f9;
                border: 1px solid rgba(148, 163, 184, 0.1);
                border-radius: 12px;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -48%) scale(0.96);
                z-index: 9999;
                padding: 1.5rem;
                width: min(440px, 90vw);
                max-height: 85vh;
                overflow-y: auto;
                opacity: 0;
                font-family: 'Inter', sans-serif;
                transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            }

            .popup.visible {
                opacity: 1;
                transform: translate(-50%, -50%) scale(1);
            }

            .popup-header {
                margin-bottom: 1rem;
                text-align: left;
                padding-bottom: 1rem;
                border-bottom: 1px solid rgba(148, 163, 184, 0.1);
            }

            .popup-title {
                margin: 0;
                font-size: 1.25rem;
                font-weight: 600;
                color: #f8fafc;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }

            .popup-description {
                font-size: 0.95rem;
                line-height: 1.6;
                color: #cbd5e1;
            }

            .modal-close-button {
                position: absolute;
                top: 1.25rem;
                right: 1.25rem;
                background: transparent;
                border: none;
                color: #64748b;
                font-size: 1.25rem;
                cursor: pointer;
                padding: 4px;
                line-height: 1;
                border-radius: 4px;
                transition: color 0.1s;
            }

            .modal-close-button:hover {
                color: #f1f5f9;
                background: rgba(255,255,255,0.05);
            }
        `;
        document.head.appendChild(style);
    }

    // Modal Elements
    const overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay';

    const popupDiv = document.createElement('div');
    popupDiv.className = 'popup';

    // Escape Content
    const escapedNombre = escapeHtml(nombre);
    const escapedDescripcion = escapeHtml(descripcionTexto);

    // Structure
    const closeButton = document.createElement('button');
    closeButton.className = 'modal-close-button';
    closeButton.innerHTML = '&times;';
    closeButton.addEventListener('click', closePopup);

    const headerDiv = document.createElement('div');
    headerDiv.className = 'popup-header';
    headerDiv.innerHTML = `
        <h2 class="popup-title">
            <i class="bi bi-info-circle-fill" style="color: #3b82f6;"></i>
            Aprendizaje previsto
        </h2>
    `;

    // Check if description is empty
    let contentHtml = '';
    if (!escapedDescripcion || escapedDescripcion.trim() === '') {
        contentHtml = `<p class="popup-description" style="font-style: italic; color: #64748b;">No hay descripción disponible para ${escapedNombre}.</p>`;
    } else {
        contentHtml = `<div class="popup-description">${escapedDescripcion}</div>`;
    }

    popupDiv.appendChild(closeButton);
    popupDiv.appendChild(headerDiv);

    // We append the content HTML string by setting innerHTML of a new div or appending to popup
    const contentDiv = document.createElement('div');
    contentDiv.innerHTML = contentHtml;
    popupDiv.appendChild(contentDiv);

    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

    // Animation
    setTimeout(function () {
        popupDiv.classList.add('visible');
        overlayDiv.classList.add('visible');
    }, 10);

    // Close Logic
    overlayDiv.addEventListener('click', function (event) {
        if (event.target === overlayDiv) {
            closePopup();
        }
    });

    function closePopup() {
        popupDiv.classList.remove('visible');
        overlayDiv.classList.remove('visible');
        setTimeout(function () {
            if (popupDiv.parentNode) document.body.removeChild(popupDiv);
            if (overlayDiv.parentNode) document.body.removeChild(overlayDiv);
        }, 300);
    }
}
