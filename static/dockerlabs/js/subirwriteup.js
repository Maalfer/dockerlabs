function subirwriteup(nombre) {
    // No escapar HTML aquí - el nombre se envía tal cual a la API
    // La sanitización se hace en el backend si es necesario

    // Check if user is authenticated
    if (typeof currentUser === "undefined" || currentUser === "") {
        showLoginRequiredModal();
        return;
    }

    // Inject Styles (if not already present, though duplicating is safe as it overwrites)
    const styleId = 'minimal-modal-styles-subir';
    if (!document.getElementById(styleId)) {
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            .overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(15, 23, 42, 0.6);
                backdrop-filter: blur(12px);
                z-index: 10000;
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
                z-index: 10001;
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
                margin-bottom: 1.5rem;
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

            .popup-subtitle {
                margin-top: 0.25rem;
                font-size: 0.875rem;
                color: #94a3b8;
            }

            /* Form Styles */
            .form-group {
                margin-bottom: 1rem;
            }
            
            .input-minimal {
                width: 100%;
                padding: 0.75rem 1rem;
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #f1f5f9;
                font-size: 0.95rem;
                font-family: 'Inter', sans-serif;
                transition: all 0.2s ease;
                outline: none;
                box-sizing: border-box; /* Update: Ensure padding doesn't affect width */
            }

            .input-minimal:focus {
                border-color: #3b82f6;
                box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
            }
            
            .input-minimal::placeholder {
                color: #64748b;
            }

            .btn-primary {
                width: 100%;
                padding: 0.85rem;
                background: linear-gradient(135deg, #3b82f6, #2563eb);
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 0.95rem;
                cursor: pointer;
                transition: all 0.2s;
                font-family: 'Inter', sans-serif;
                margin-top: 0.5rem;
            }

            .btn-primary:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
                background: linear-gradient(135deg, #2563eb, #1d4ed8);
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

            .btn-loader {
                display: inline-flex;
                align-items: center;
                gap: 4px;
            }
            .loader-dot {
                width: 6px;
                height: 6px;
                background: currentColor;
                border-radius: 50%;
                animation: loader-bounce 1.4s infinite ease-in-out both;
            }
            .loader-dot:nth-child(1) { animation-delay: -0.32s; }
            .loader-dot:nth-child(2) { animation-delay: -0.16s; }
            @keyframes loader-bounce {
                0%, 80%, 100% { transform: scale(0); }
                40% { transform: scale(1); }
            }
        `;
        document.head.appendChild(style);
    }

    // Create Modal Structure
    const overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay';

    const popupDiv = document.createElement('div');
    popupDiv.className = 'popup';

    // Header
    const headerDiv = document.createElement('div');
    headerDiv.className = 'popup-header';
    const escapedNombre = nombre.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    headerDiv.innerHTML = `
        <h2 class="popup-title">
            <i class="bi bi-send-fill" style="color: #3b82f6;"></i>
            Envía tu Writeup
        </h2>
        <p class="popup-subtitle">Comparte tu recurso de la máquina <strong>${escapedNombre}</strong></p>
    `;

    // Close Button
    const closeButton = document.createElement('button');
    closeButton.className = 'modal-close-button';
    closeButton.innerHTML = '&times;';
    closeButton.addEventListener('click', closePopup);

    // Form Container
    const formContainer = document.createElement('div');
    formContainer.className = 'form-container';

    // Autor Input
    const inputAutor = document.createElement('input');
    inputAutor.className = 'input-minimal';
    inputAutor.id = 'autor';
    inputAutor.type = 'text';
    if (typeof currentUser !== "undefined" && currentUser !== "") {
        inputAutor.value = currentUser;
        inputAutor.readOnly = true;
        inputAutor.style.opacity = '0.7';
        inputAutor.style.cursor = 'not-allowed';
    } else {
        inputAutor.placeholder = 'Autor';
    }

    // URL Input
    const inputUrl = document.createElement('input');
    inputUrl.className = 'input-minimal';
    inputUrl.id = 'url';
    inputUrl.type = 'text';
    inputUrl.placeholder = 'URL del writeup';

    // Type Select
    const selectTipo = document.createElement('select');
    selectTipo.className = 'input-minimal';
    selectTipo.id = 'tipo';

    const optionVideo = document.createElement('option');
    optionVideo.value = 'video';
    optionVideo.textContent = 'Video';
    selectTipo.appendChild(optionVideo);

    const optionTexto = document.createElement('option');
    optionTexto.value = 'texto';
    optionTexto.textContent = 'Texto';
    selectTipo.appendChild(optionTexto);

    // Submit Button
    const enviarButton = document.createElement('button');
    enviarButton.className = 'btn-primary';
    enviarButton.textContent = 'Enviar Writeup';

    // Bind click event
    enviarButton.addEventListener('click', function () {
        let url = inputUrl.value;
        let tipo = selectTipo.value;
        let csrfToken = document.querySelector('meta[name="csrf-token"]') ? document.querySelector('meta[name="csrf-token"]').content : '';

        // Simple validation
        if (!url) {
            alert("Por favor introduce una URL.");
            return;
        }

        // Show loading animation
        enviarButton.disabled = true;
        enviarButton.innerHTML = `
            <span class="btn-loader">
                <span class="loader-dot"></span>
                <span class="loader-dot"></span>
                <span class="loader-dot"></span>
            </span>
        `;

        fetch('/api/submit_writeup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ maquina: nombre, url, tipo })
        })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw new Error(err.error || `Error ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    showErrorModal(data.error);
                } else {
                    showSuccessModal(data.message);
                    closePopup();
                }
            })
            .catch(error => {
                showErrorModal(`Error al enviar el writeup: ${error.message}`);
                console.error(error);
            })
            .finally(() => {
                // Restore button
                enviarButton.disabled = false;
                enviarButton.textContent = 'Enviar Writeup';
            });
    });

    // Assemble Form
    formContainer.appendChild(inputAutor);
    formContainer.appendChild(inputUrl);
    formContainer.appendChild(selectTipo);
    formContainer.appendChild(enviarButton);

    // Assemble Popup
    popupDiv.appendChild(closeButton);
    popupDiv.appendChild(headerDiv);
    popupDiv.appendChild(formContainer);

    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

    // Animation
    setTimeout(function () {
        popupDiv.classList.add('visible');
        overlayDiv.classList.add('visible');
    }, 10);

    // Close logic
    overlayDiv.addEventListener('click', function (event) {
        if (event.target === overlayDiv) closePopup();
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

// Login Required Modal Function
function showLoginRequiredModal() {
    // Reuse styles from subirwriteup if possible, or ensure they are injected.
    // Since subirwriteup injects them, we can check/inject again or assume common usage.
    // For safety, let's just ensure the style element exists (same ID).
    const styleId = 'minimal-modal-styles-subir';
    if (!document.getElementById(styleId)) {
        // ... (Logic to inject style would go here, but for brevity/DRY, 
        // we assume subirwriteup or writeups has run or we duplicate the minimal set here if needed independent usage)
        // Ideally we'd move styles to a shared CSS file, but following the established pattern:
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            .overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); z-index: 10000; opacity: 0; transition: opacity 0.2s ease; }
            .overlay.visible { opacity: 1; }
            .popup { background: #1e293b; color: #f1f5f9; border: 1px solid rgba(148, 163, 184, 0.1); border-radius: 12px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); position: fixed; top: 50%; left: 50%; transform: translate(-50%, -48%) scale(0.96); z-index: 10001; padding: 1.5rem; width: min(420px, 90vw); text-align: center; opacity: 0; font-family: 'Fira Code', monospace; transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1); }
            .popup.visible { opacity: 1; transform: translate(-50%, -50%) scale(1); }
            .popup-header { margin-bottom: 1.5rem; text-align: left; padding-bottom: 1rem; border-bottom: 1px solid rgba(148, 163, 184, 0.1); }
            .popup-title { margin: 0; font-size: 1.25rem; font-weight: 600; color: #f8fafc; display: flex; align-items: center; gap: 0.5rem; }
            .btn-primary { width: 100%; padding: 0.85rem; background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.2s; font-family: 'Fira Code', monospace; margin-bottom: 0.75rem; }
            .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3); }
            .btn-secondary { width: 100%; padding: 0.85rem; background: transparent; border: 1px solid #334155; color: #94a3b8; border-radius: 8px; font-size: 0.95rem; cursor: pointer; transition: all 0.2s; font-family: 'Fira Code', monospace; }
            .btn-secondary:hover { border-color: #475569; color: #f1f5f9; background: rgba(255,255,255,0.02); }
            .modal-close-button { position: absolute; top: 1.25rem; right: 1.25rem; background: transparent; border: none; color: #64748b; font-size: 1.25rem; cursor: pointer; padding: 4px; line-height: 1; border-radius: 4px; transition: color 0.1s; }
            .modal-close-button:hover { color: #f1f5f9; background: rgba(255,255,255,0.05); }
        `;
        document.head.appendChild(style);
    }

    const overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay';

    const popupDiv = document.createElement('div');
    popupDiv.className = 'popup';

    const headerDiv = document.createElement('div');
    headerDiv.className = 'popup-header';
    headerDiv.style.borderBottomColor = 'rgba(239, 68, 68, 0.2)'; // Red tint for error/warning
    headerDiv.innerHTML = `
        <h2 class="popup-title" style="color: #ef4444;">
            <i class="bi bi-lock-fill"></i>
            Autenticación requerida
        </h2>
    `;

    const message = document.createElement('p');
    message.textContent = 'Debes iniciar sesión para enviar writeups';
    message.style.marginBottom = '1.5rem';
    message.style.color = '#94a3b8';
    message.style.fontSize = '0.95rem';

    const closeButton = document.createElement('button');
    closeButton.innerHTML = '&times;';
    closeButton.className = 'modal-close-button';
    closeButton.addEventListener('click', () => closePopup());

    const loginButton = document.createElement('button');
    loginButton.textContent = 'Iniciar Sesión';
    loginButton.className = 'btn-primary';
    loginButton.addEventListener('click', () => window.location.href = '/login');

    const registerButton = document.createElement('button');
    registerButton.textContent = 'Registrarse';
    registerButton.className = 'btn-secondary';
    registerButton.addEventListener('click', () => window.location.href = '/register');

    popupDiv.appendChild(closeButton);
    popupDiv.appendChild(headerDiv);
    popupDiv.appendChild(message);
    popupDiv.appendChild(loginButton);
    popupDiv.appendChild(registerButton);

    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

    setTimeout(() => {
        popupDiv.classList.add('visible');
        overlayDiv.classList.add('visible');
    }, 10);

    overlayDiv.addEventListener('click', (event) => {
        if (event.target === overlayDiv) closePopup();
    });

    function closePopup() {
        popupDiv.classList.remove('visible');
        overlayDiv.classList.remove('visible');
        setTimeout(() => {
            if (popupDiv.parentNode) document.body.removeChild(popupDiv);
            if (overlayDiv.parentNode) document.body.removeChild(overlayDiv);
        }, 300);
    }
}

// Success Modal Function
function showSuccessModal(message) {
    const styleId = 'success-modal-styles';
    if (!document.getElementById(styleId)) {
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            .success-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(16, 185, 129, 0.15);
                backdrop-filter: blur(8px);
                z-index: 10000;
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            .success-overlay.visible { opacity: 1; }
            .success-modal {
                background: linear-gradient(135deg, #064e3b 0%, #065f46 100%);
                color: #ecfdf5;
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 16px;
                box-shadow: 0 25px 50px -12px rgba(16, 185, 129, 0.25);
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -48%) scale(0.92);
                z-index: 10001;
                padding: 2rem;
                width: min(400px, 90vw);
                text-align: center;
                opacity: 0;
                font-family: 'Fira Code', monospace;
                transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            }
            .success-modal.visible {
                opacity: 1;
                transform: translate(-50%, -50%) scale(1);
            }
            .success-icon {
                width: 80px;
                height: 80px;
                background: linear-gradient(135deg, #10b981, #059669);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 1.5rem;
                font-size: 2.5rem;
                box-shadow: 0 0 30px rgba(16, 185, 129, 0.4);
                animation: success-pulse 2s infinite;
            }
            @keyframes success-pulse {
                0%, 100% { box-shadow: 0 0 30px rgba(16, 185, 129, 0.4); }
                50% { box-shadow: 0 0 50px rgba(16, 185, 129, 0.6); }
            }
            .success-title {
                font-size: 1.5rem;
                font-weight: 700;
                margin: 0 0 0.75rem 0;
                color: #6ee7b7;
            }
            .success-message {
                font-size: 1rem;
                color: #a7f3d0;
                margin: 0 0 1.5rem 0;
                line-height: 1.5;
            }
            .success-btn {
                background: linear-gradient(135deg, #10b981, #059669);
                color: white;
                border: none;
                padding: 0.85rem 2rem;
                border-radius: 8px;
                font-weight: 600;
                font-size: 0.95rem;
                cursor: pointer;
                transition: all 0.2s;
                font-family: 'Fira Code', monospace;
            }
            .success-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(16, 185, 129, 0.4);
            }
        `;
        document.head.appendChild(style);
    }

    const overlay = document.createElement('div');
    overlay.className = 'success-overlay';

    const modal = document.createElement('div');
    modal.className = 'success-modal';
    modal.innerHTML = `
        <div class="success-icon">✓</div>
        <h3 class="success-title">¡Éxito!</h3>
        <p class="success-message">${message}</p>
        <button class="success-btn">Aceptar</button>
    `;

    const btn = modal.querySelector('.success-btn');
    btn.addEventListener('click', closeSuccessModal);

    document.body.appendChild(overlay);
    document.body.appendChild(modal);

    setTimeout(() => {
        overlay.classList.add('visible');
        modal.classList.add('visible');
    }, 10);

    function closeSuccessModal() {
        overlay.classList.remove('visible');
        modal.classList.remove('visible');
        setTimeout(() => {
            if (overlay.parentNode) document.body.removeChild(overlay);
            if (modal.parentNode) document.body.removeChild(modal);
        }, 300);
    }
}

// Error Modal Function
function showErrorModal(message) {
    const styleId = 'error-modal-styles';
    if (!document.getElementById(styleId)) {
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            .error-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(239, 68, 68, 0.15);
                backdrop-filter: blur(8px);
                z-index: 10000;
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            .error-overlay.visible { opacity: 1; }
            .error-modal {
                background: linear-gradient(135deg, #7f1d1d 0%, #991b1b 100%);
                color: #fef2f2;
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 16px;
                box-shadow: 0 25px 50px -12px rgba(239, 68, 68, 0.25);
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -48%) scale(0.92);
                z-index: 10001;
                padding: 2rem;
                width: min(400px, 90vw);
                text-align: center;
                opacity: 0;
                font-family: 'Fira Code', monospace;
                transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            }
            .error-modal.visible {
                opacity: 1;
                transform: translate(-50%, -50%) scale(1);
            }
            .error-icon {
                width: 80px;
                height: 80px;
                background: linear-gradient(135deg, #ef4444, #dc2626);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 1.5rem;
                font-size: 2.5rem;
                box-shadow: 0 0 30px rgba(239, 68, 68, 0.4);
                animation: error-pulse 2s infinite;
            }
            @keyframes error-pulse {
                0%, 100% { box-shadow: 0 0 30px rgba(239, 68, 68, 0.4); }
                50% { box-shadow: 0 0 50px rgba(239, 68, 68, 0.6); }
            }
            .error-title {
                font-size: 1.5rem;
                font-weight: 700;
                margin: 0 0 0.75rem 0;
                color: #fca5a5;
            }
            .error-message {
                font-size: 1rem;
                color: #fecaca;
                margin: 0 0 1.5rem 0;
                line-height: 1.5;
            }
            .error-btn {
                background: linear-gradient(135deg, #ef4444, #dc2626);
                color: white;
                border: none;
                padding: 0.85rem 2rem;
                border-radius: 8px;
                font-weight: 600;
                font-size: 0.95rem;
                cursor: pointer;
                transition: all 0.2s;
                font-family: 'Fira Code', monospace;
            }
            .error-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(239, 68, 68, 0.4);
            }
        `;
        document.head.appendChild(style);
    }

    const overlay = document.createElement('div');
    overlay.className = 'error-overlay';

    const modal = document.createElement('div');
    modal.className = 'error-modal';
    modal.innerHTML = `
        <div class="error-icon">✕</div>
        <h3 class="error-title">Error</h3>
        <p class="error-message">${message}</p>
        <button class="error-btn">Aceptar</button>
    `;

    const btn = modal.querySelector('.error-btn');
    btn.addEventListener('click', closeErrorModal);

    document.body.appendChild(overlay);
    document.body.appendChild(modal);

    setTimeout(() => {
        overlay.classList.add('visible');
        modal.classList.add('visible');
    }, 10);

    function closeErrorModal() {
        overlay.classList.remove('visible');
        modal.classList.remove('visible');
        setTimeout(() => {
            if (overlay.parentNode) document.body.removeChild(overlay);
            if (modal.parentNode) document.body.removeChild(modal);
        }, 300);
    }
}
