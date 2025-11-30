function subirwriteup(nombre) {
    function escapeHTML(str) {
        if (typeof str !== "string") return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    nombre = escapeHTML(nombre);

    var overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay';
    overlayDiv.style.position = 'fixed';
    overlayDiv.style.top = '0';
    overlayDiv.style.left = '0';
    overlayDiv.style.width = '100%';
    overlayDiv.style.height = '100%';
    overlayDiv.style.background = 'radial-gradient(circle at top, rgba(2, 6, 23, 0.95), rgba(2, 6, 23, 0.98))';
    overlayDiv.style.backdropFilter = 'blur(8px)';
    overlayDiv.style.zIndex = '9998';
    overlayDiv.style.opacity = '0';
    overlayDiv.style.transition = 'opacity 0.3s ease';

    var popupDiv = document.createElement('div');
    popupDiv.className = 'popup';
    popupDiv.style.width = 'min(450px, 90vw)';
    popupDiv.style.background = 'linear-gradient(135deg, #0a1120 0%, #020617 100%)';
    popupDiv.style.color = '#f9fafb';
    popupDiv.style.border = '1px solid #3b82f6';
    popupDiv.style.borderRadius = '16px';
    popupDiv.style.boxShadow = '0 20px 60px rgba(0, 0, 0, 0.7), 0 0 40px rgba(59, 130, 246, 0.3)';
    popupDiv.style.position = 'fixed';
    popupDiv.style.top = '50%';
    popupDiv.style.left = '50%';
    popupDiv.style.transform = 'translate(-50%, -50%)';
    popupDiv.style.zIndex = '9999';
    popupDiv.style.padding = '2rem';
    popupDiv.style.textAlign = 'center';
    popupDiv.style.overflowY = 'auto';
    popupDiv.style.maxHeight = '90vh';
    popupDiv.style.transition = 'opacity 0.3s ease, transform 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55)';
    popupDiv.style.opacity = '0';
    popupDiv.style.transform = 'translate(-50%, -60%)';
    popupDiv.style.fontFamily = "'Fira Code', monospace";

    var closeButton = document.createElement('button');
    closeButton.classList.add('modal-close-button');
    closeButton.innerHTML = '&times;';
    closeButton.style.position = 'absolute';
    closeButton.style.top = '1rem';
    closeButton.style.right = '1.2rem';
    closeButton.style.fontSize = '1.8rem';
    closeButton.style.color = '#94a3b8';
    closeButton.style.cursor = 'pointer';
    closeButton.style.background = 'none';
    closeButton.style.border = 'none';
    closeButton.style.transition = 'all 0.2s ease';
    closeButton.style.width = '36px';
    closeButton.style.height = '36px';
    closeButton.style.borderRadius = '8px';
    closeButton.style.display = 'flex';
    closeButton.style.alignItems = 'center';
    closeButton.style.justifyContent = 'center';
    closeButton.addEventListener('mouseover', function () {
        this.style.color = '#ef4444';
        this.style.background = 'rgba(239, 68, 68, 0.1)';
        this.style.transform = 'scale(1.1)';
    });
    closeButton.addEventListener('mouseout', function () {
        this.style.color = '#94a3b8';
        this.style.background = 'none';
        this.style.transform = 'scale(1)';
    });
    closeButton.addEventListener('click', function () {
        closePopup();
    });

    // Icon
    var iconDiv = document.createElement('div');
    iconDiv.style.width = '64px';
    iconDiv.style.height = '64px';
    iconDiv.style.margin = '0 auto 1.5rem';
    iconDiv.style.background = 'linear-gradient(135deg, #3b82f6, #1d4ed8)';
    iconDiv.style.borderRadius = '16px';
    iconDiv.style.display = 'flex';
    iconDiv.style.alignItems = 'center';
    iconDiv.style.justifyContent = 'center';
    iconDiv.style.fontSize = '2rem';
    iconDiv.style.boxShadow = '0 0 30px rgba(59, 130, 246, 0.5)';
    iconDiv.innerHTML = '<i class="bi bi-file-earmark-text-fill" style="color: white;"></i>';

    // Title
    var titulo = document.createElement('h2');
    titulo.textContent = 'Envía tu Writeup';
    titulo.style.marginBottom = '0.5rem';
    titulo.style.fontSize = '1.5rem';
    titulo.style.fontWeight = '700';
    titulo.style.background = 'linear-gradient(135deg, #60a5fa, #22d3ee)';
    titulo.style.webkitBackgroundClip = 'text';
    titulo.style.backgroundClip = 'text';
    titulo.style.webkitTextFillColor = 'transparent';
    titulo.style.letterSpacing = '0.02em';

    // Subtitle
    var subtitulo = document.createElement('p');
    subtitulo.textContent = nombre;
    subtitulo.style.marginBottom = '0.5rem';
    subtitulo.style.fontSize = '0.95rem';
    subtitulo.style.color = '#64748b';
    subtitulo.style.fontWeight = '600';

    // Description
    var descripcion = document.createElement('p');
    descripcion.textContent = 'Comparte tu recurso con la comunidad';
    descripcion.style.marginBottom = '2rem';
    descripcion.style.fontSize = '0.85rem';
    descripcion.style.color = '#94a3b8';
    descripcion.style.fontWeight = '400';

    // Form container
    var formContainer = document.createElement('div');
    formContainer.style.textAlign = 'left';
    formContainer.style.display = 'flex';
    formContainer.style.flexDirection = 'column';
    formContainer.style.gap = '1rem';

    // Input Autor
    var inputAutor = document.createElement('input');
    inputAutor.id = 'autor';
    inputAutor.type = 'text';
    if (typeof currentUser !== "undefined" && currentUser !== "") {
        inputAutor.value = currentUser;
        inputAutor.readOnly = true;
    } else {
        inputAutor.placeholder = 'Autor';
    }
    inputAutor.style.width = '100%';
    inputAutor.style.padding = '0.9rem 1.1rem';
    inputAutor.style.border = '1px solid #334155';
    inputAutor.style.background = '#0f172a';
    inputAutor.style.color = '#f9fafb';
    inputAutor.style.borderRadius = '10px';
    inputAutor.style.fontSize = '0.9rem';
    inputAutor.style.outline = 'none';
    inputAutor.style.transition = 'all 0.3s ease';
    inputAutor.style.fontFamily = "'Fira Code', monospace";
    inputAutor.addEventListener('focus', function () {
        this.style.borderColor = '#3b82f6';
        this.style.boxShadow = '0 0 0 3px rgba(59, 130, 246, 0.2)';
        this.style.background = '#020617';
    });
    inputAutor.addEventListener('blur', function () {
        this.style.borderColor = '#334155';
        this.style.boxShadow = 'none';
        this.style.background = '#0f172a';
    });

    // Input URL
    var inputUrl = document.createElement('input');
    inputUrl.id = 'url';
    inputUrl.type = 'text';
    inputUrl.placeholder = 'URL del writeup';
    inputUrl.style.width = '100%';
    inputUrl.style.padding = '0.9rem 1.1rem';
    inputUrl.style.border = '1px solid #334155';
    inputUrl.style.background = '#0f172a';
    inputUrl.style.color = '#f9fafb';
    inputUrl.style.borderRadius = '10px';
    inputUrl.style.fontSize = '0.9rem';
    inputUrl.style.outline = 'none';
    inputUrl.style.transition = 'all 0.3s ease';
    inputUrl.style.fontFamily = "'Fira Code', monospace";
    inputUrl.addEventListener('focus', function () {
        this.style.borderColor = '#3b82f6';
        this.style.boxShadow = '0 0 0 3px rgba(59, 130, 246, 0.2)';
        this.style.background = '#020617';
    });
    inputUrl.addEventListener('blur', function () {
        this.style.borderColor = '#334155';
        this.style.boxShadow = 'none';
        this.style.background = '#0f172a';
    });

    // Select Tipo
    var selectTipo = document.createElement('select');
    selectTipo.id = 'tipo';
    selectTipo.style.width = '100%';
    selectTipo.style.padding = '0.9rem 1.1rem';
    selectTipo.style.border = '1px solid #334155';
    selectTipo.style.background = '#0f172a';
    selectTipo.style.color = '#f9fafb';
    selectTipo.style.borderRadius = '10px';
    selectTipo.style.fontSize = '0.9rem';
    selectTipo.style.outline = 'none';
    selectTipo.style.cursor = 'pointer';
    selectTipo.style.transition = 'all 0.3s ease';
    selectTipo.style.fontFamily = "'Fira Code', monospace";
    selectTipo.addEventListener('focus', function () {
        this.style.borderColor = '#3b82f6';
        this.style.boxShadow = '0 0 0 3px rgba(59, 130, 246, 0.2)';
        this.style.background = '#020617';
    });
    selectTipo.addEventListener('blur', function () {
        this.style.borderColor = '#334155';
        this.style.boxShadow = 'none';
        this.style.background = '#0f172a';
    });

    var optionVideo = document.createElement('option');
    optionVideo.value = 'video';
    optionVideo.textContent = 'Video';
    selectTipo.appendChild(optionVideo);

    var optionTexto = document.createElement('option');
    optionTexto.value = 'texto';
    optionTexto.textContent = 'Texto';
    selectTipo.appendChild(optionTexto);

    formContainer.appendChild(inputAutor);
    formContainer.appendChild(inputUrl);
    formContainer.appendChild(selectTipo);

    // Button
    var enviarButton = document.createElement('button');
    enviarButton.id = 'enviarButton';
    enviarButton.textContent = 'Enviar Writeup';
    enviarButton.style.width = '100%';
    enviarButton.style.padding = '1rem';
    enviarButton.style.marginTop = '0.5rem';
    enviarButton.style.border = 'none';
    enviarButton.style.background = 'linear-gradient(135deg, #3b82f6, #1d4ed8)';
    enviarButton.style.color = 'white';
    enviarButton.style.fontSize = '1rem';
    enviarButton.style.fontWeight = '600';
    enviarButton.style.cursor = 'pointer';
    enviarButton.style.borderRadius = '10px';
    enviarButton.style.transition = 'all 0.3s ease';
    enviarButton.style.boxShadow = '0 4px 15px rgba(59, 130, 246, 0.4)';
    enviarButton.style.letterSpacing = '0.03em';
    enviarButton.style.fontFamily = "'Fira Code', monospace";
    enviarButton.addEventListener('mouseover', function () {
        this.style.background = 'linear-gradient(135deg, #60a5fa, #3b82f6)';
        this.style.transform = 'translateY(-2px)';
        this.style.boxShadow = '0 6px 25px rgba(59, 130, 246, 0.6)';
    });
    enviarButton.addEventListener('mouseout', function () {
        this.style.background = 'linear-gradient(135deg, #3b82f6, #1d4ed8)';
        this.style.transform = 'translateY(0)';
        this.style.boxShadow = '0 4px 15px rgba(59, 130, 246, 0.4)';
    });

    popupDiv.appendChild(closeButton);
    popupDiv.appendChild(iconDiv);
    popupDiv.appendChild(titulo);
    popupDiv.appendChild(subtitulo);
    popupDiv.appendChild(descripcion);
    popupDiv.appendChild(formContainer);
    popupDiv.appendChild(enviarButton);
    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

    setTimeout(function () {
        popupDiv.style.opacity = '1';
        popupDiv.style.transform = 'translate(-50%, -50%)';
        overlayDiv.style.opacity = '1';
    }, 10);

    overlayDiv.addEventListener('click', function (event) {
        if (event.target === overlayDiv) {
            closePopup();
        }
    });

    function closePopup() {
        popupDiv.style.opacity = '0';
        popupDiv.style.transform = 'translate(-50%, -60%)';
        overlayDiv.style.opacity = '0';
        setTimeout(function () {
            document.body.removeChild(popupDiv);
            document.body.removeChild(overlayDiv);
        }, 300);
    }


    enviarButton.addEventListener('click', function () {
        let autor = document.getElementById('autor').value;
        let url = document.getElementById('url').value;
        let tipo = document.getElementById('tipo').value;

        let csrfToken = document.querySelector('meta[name="csrf-token"]').content;

        fetch('/subirwriteups', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ maquina: nombre, autor, url, tipo })
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(`Error: ${data.error}`);
                } else {
                    alert(data.message);
                    closePopup();
                }
            })
            .catch(error => {
                alert('Error al enviar el writeup.');
                console.error(error);
            });
    });
}
