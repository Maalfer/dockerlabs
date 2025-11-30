// Utility function to escape HTML and prevent XSS attacks
function escapeHtml(text) {
    if (!text) return text;
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function presentacion(nombre, dificultad, color, autor_nombre, autor_enlace, fecha, imagen, categoria = '', isMostRecent = false) {
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

    // Define border colors based on difficulty
    const difficultyColors = {
        'Muy Fácil': { border: '#06b6d4', shadow: '0 16px 40px rgba(6, 182, 212, 0.4)' },  // Cyan
        'Fácil': { border: '#8bc34a', shadow: '0 16px 40px rgba(139, 195, 74, 0.4)' },      // Light green
        'Medio': { border: '#e0a553', shadow: '0 16px 40px rgba(224, 165, 83, 0.4)' },      // Yellow/amber
        'Difícil': { border: '#d83c31', shadow: '0 16px 40px rgba(216, 60, 49, 0.4)' }      // Red
    };

    // Apply border based on priority: most recent > difficulty > default
    if (isMostRecent) {
        popupDiv.style.border = '2px solid #ff8c00';
        popupDiv.style.boxShadow = '0 16px 40px rgba(255, 140, 0, 0.4)';
    } else if (difficultyColors[dificultad]) {
        popupDiv.style.border = `2px solid ${difficultyColors[dificultad].border}`;
        popupDiv.style.boxShadow = difficultyColors[dificultad].shadow;
    } else {
        popupDiv.style.border = '2px solid rgba(59,130,246,0.95)';
        popupDiv.style.boxShadow = '0 16px 40px rgba(0, 0, 0, 0.75)';
    }

    popupDiv.style.borderRadius = '12px';
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
    closeButton.classList.add('boton-cerrar-modal');
    closeButton.addEventListener('click', function () {
        closePopup();
    });

    // Crear el contenedor del contenido
    var contentDiv = document.createElement('div');
    contentDiv.style.display = 'flex';
    contentDiv.style.flexDirection = 'column';
    contentDiv.style.alignItems = 'stretch';
    contentDiv.style.width = '100%';

    // Escape user-generated content to prevent XSS
    const escapedNombre = escapeHtml(nombre);
    const escapedDificultad = escapeHtml(dificultad);
    const escapedColor = escapeHtml(color);
    const escapedAutorNombre = escapeHtml(autor_nombre);
    const escapedFecha = escapeHtml(fecha);

    // Crear el título
    var titulo = document.createElement('h1');
    titulo.textContent = nombre; // textContent is safe
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

    // Subtítulo (dificultad en cabecera)
    var subtitulo = document.createElement('p');
    subtitulo.style.margin = '0 0 8px';
    subtitulo.style.fontSize = '0.8rem';
    subtitulo.style.color = 'var(--text-muted)';
    subtitulo.style.textAlign = 'center';
    subtitulo.style.textTransform = 'uppercase';
    subtitulo.style.letterSpacing = '0.16em';
    const categoryText = categoria && categoria.trim() !== '' ? categoria : 'Máquina';
    subtitulo.innerHTML = `${escapeHtml(categoryText)} • <span style="color:${escapedColor}; font-weight:700;">${escapedDificultad}</span>`;

    // --- RATING SECTION ---
    var ratingContainer = document.createElement('div');
    ratingContainer.style.display = 'flex';
    ratingContainer.style.justifyContent = 'center';
    ratingContainer.style.alignItems = 'center';
    ratingContainer.style.gap = '10px';
    ratingContainer.style.marginBottom = '14px';

    var starsDisplay = document.createElement('div');
    starsDisplay.id = 'machine-avg-rating';
    starsDisplay.style.color = '#f59e0b'; // Gold color
    starsDisplay.innerHTML = 'Cargando...';

    var rateButton = document.createElement('button');
    rateButton.textContent = 'Puntuar';
    rateButton.className = 'btn btn-sm btn-outline-primary';
    rateButton.style.fontSize = '0.75rem';
    rateButton.style.padding = '2px 8px';
    rateButton.onclick = function () {
        openRatingModal(nombre);
    };

    ratingContainer.appendChild(starsDisplay);
    ratingContainer.appendChild(rateButton);
    // ----------------------

    // --- COMPLETED CHECKBOX SECTION ---
    var completedContainer = document.createElement('div');
    completedContainer.style.display = 'flex';
    completedContainer.style.justifyContent = 'center';
    completedContainer.style.alignItems = 'center';
    completedContainer.style.gap = '8px';
    completedContainer.style.marginBottom = '14px';
    completedContainer.style.padding = '8px 12px';
    completedContainer.style.borderRadius = '8px';
    completedContainer.style.background = 'rgba(59,130,246,0.08)';
    completedContainer.style.border = '1px solid rgba(59,130,246,0.2)';
    completedContainer.style.transition = 'all 0.3s ease';

    // Only show if user is logged in
    if (currentUser) {
        var checkboxWrapper = document.createElement('label');
        checkboxWrapper.style.display = 'flex';
        checkboxWrapper.style.alignItems = 'center';
        checkboxWrapper.style.gap = '8px';
        checkboxWrapper.style.cursor = 'pointer';
        checkboxWrapper.style.userSelect = 'none';

        var checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = 'machine-completed-checkbox';
        checkbox.style.width = '18px';
        checkbox.style.height = '18px';
        checkbox.style.cursor = 'pointer';
        checkbox.style.accentColor = '#3b82f6';

        var checkboxLabel = document.createElement('span');
        checkboxLabel.textContent = 'Máquina completada';
        checkboxLabel.style.fontSize = '0.85rem';
        checkboxLabel.style.color = 'var(--text-primary)';
        checkboxLabel.style.fontWeight = '500';

        // Arrow icon button to navigate to completed machines page
        var arrowLink = document.createElement('a');
        arrowLink.href = '/maquinas-hechas';
        arrowLink.style.display = 'flex';
        arrowLink.style.alignItems = 'center';
        arrowLink.style.justifyContent = 'center';
        arrowLink.style.marginLeft = '8px';
        arrowLink.style.color = 'var(--primary-blue-light)';
        arrowLink.style.textDecoration = 'none';
        arrowLink.style.fontSize = '1.1rem';
        arrowLink.style.transition = 'all 0.2s ease';
        arrowLink.style.padding = '2px';
        arrowLink.title = 'Ver mis máquinas completadas';

        arrowLink.onmouseover = function () {
            this.style.transform = 'translateX(3px)';
            this.style.color = 'var(--accent-cyan)';
        };
        arrowLink.onmouseout = function () {
            this.style.transform = 'translateX(0)';
            this.style.color = 'var(--primary-blue-light)';
        };

        var arrowIcon = document.createElement('i');
        arrowIcon.className = 'bi bi-arrow-right-circle-fill';
        arrowLink.appendChild(arrowIcon);

        // Fetch current completion status
        fetch(`/api/completed_machines/${encodeURIComponent(nombre)}`)
            .then(response => response.json())
            .then(data => {
                if (data.completed) {
                    checkbox.checked = true;
                    completedContainer.style.background = 'rgba(34,197,94,0.12)';
                    completedContainer.style.border = '1px solid rgba(34,197,94,0.3)';
                }
            })
            .catch(err => console.error('Error fetching completion status:', err));

        // Handle checkbox change
        checkbox.addEventListener('change', function () {
            const isChecked = this.checked;

            // Update visual feedback immediately
            if (isChecked) {
                completedContainer.style.background = 'rgba(34,197,94,0.12)';
                completedContainer.style.border = '1px solid rgba(34,197,94,0.3)';
            } else {
                completedContainer.style.background = 'rgba(59,130,246,0.08)';
                completedContainer.style.border = '1px solid rgba(59,130,246,0.2)';
            }

            // Send to API
            fetch('/api/toggle_completed_machine', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    machine_name: nombre
                })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Sync checkbox state with server response
                        checkbox.checked = data.completed;
                        if (data.completed) {
                            completedContainer.style.background = 'rgba(34,197,94,0.12)';
                            completedContainer.style.border = '1px solid rgba(34,197,94,0.3)';
                        } else {
                            completedContainer.style.background = 'rgba(59,130,246,0.08)';
                            completedContainer.style.border = '1px solid rgba(59,130,246,0.2)';
                        }
                    } else {
                        // Revert on error
                        checkbox.checked = !isChecked;
                        alert('Error al actualizar el estado: ' + (data.error || 'Error desconocido'));
                    }
                })
                .catch(err => {
                    // Revert on error
                    checkbox.checked = !isChecked;
                    console.error('Error toggling completion:', err);
                    alert('Error de conexión al actualizar el estado');
                });
        });

        checkboxWrapper.appendChild(checkbox);
        checkboxWrapper.appendChild(checkboxLabel);
        completedContainer.appendChild(checkboxWrapper);
        completedContainer.appendChild(arrowLink);
    }
    // ----------------------


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

    // Contenedor para autor con placeholder para redes sociales
    var autorHTML = `
        <p style="margin: 0;">
            <span style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--text-muted);">Autor</span><br>
            <span style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <a href="#" onclick="openAuthorProfileModal('${escapedAutorNombre}'); return false;" style="color: var(--primary-blue-light); text-decoration: none; font-weight: 600; cursor: pointer;">
                    ${escapedAutorNombre}
                </a>
                <span id="author-social-links" style="display: flex; gap: 6px;"></span>
            </span>
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

    infoDiv.innerHTML = autorHTML;

    // Fetch social media links for the author
    fetch(`/api/author_profile?nombre=${encodeURIComponent(autor_nombre)}`)
        .then(response => response.json())
        .then(data => {
            const socialLinksContainer = infoDiv.querySelector('#author-social-links');
            if (socialLinksContainer && (data.linkedin_url || data.github_url || data.youtube_url)) {
                let socialHTML = '';

                if (data.linkedin_url) {
                    socialHTML += `
                        <a href="${escapeHtml(data.linkedin_url)}" target="_blank" rel="noopener noreferrer" 
                           style="color: #0077B5; font-size: 1.1rem; transition: transform 0.2s;"
                           onmouseover="this.style.transform='scale(1.15)'"
                           onmouseout="this.style.transform='scale(1)'"
                           title="LinkedIn">
                            <i class="bi bi-linkedin"></i>
                        </a>
                    `;
                }

                if (data.github_url) {
                    socialHTML += `
                        <a href="${escapeHtml(data.github_url)}" target="_blank" rel="noopener noreferrer" 
                           style="color: #e5e7eb; font-size: 1.1rem; transition: transform 0.2s;"
                           onmouseover="this.style.transform='scale(1.15)'"
                           onmouseout="this.style.transform='scale(1)'"
                           title="GitHub">
                            <i class="bi bi-github"></i>
                        </a>
                    `;
                }

                if (data.youtube_url) {
                    socialHTML += `
                        <a href="${escapeHtml(data.youtube_url)}" target="_blank" rel="noopener noreferrer" 
                           style="color: #FF0000; font-size: 1.1rem; transition: transform 0.2s;"
                           onmouseover="this.style.transform='scale(1.15)'"
                           onmouseout="this.style.transform='scale(1)'"
                           title="YouTube">
                            <i class="bi bi-youtube"></i>
                        </a>
                    `;
                }

                socialLinksContainer.innerHTML = socialHTML;
            }
        })
        .catch(err => {
            console.error('Error fetching author social links:', err);
        });

    // Añadir la imagen y la información al contenedor
    infoContainer.appendChild(imagenElem);
    infoContainer.appendChild(infoDiv);

    // Añadir todo al contenido
    contentDiv.appendChild(titulo);
    contentDiv.appendChild(subtitulo);
    contentDiv.appendChild(ratingContainer); // Add rating container
    if (currentUser) {
        contentDiv.appendChild(completedContainer); // Add completed checkbox
    }
    contentDiv.appendChild(separator);
    contentDiv.appendChild(infoContainer);

    popupDiv.appendChild(contentDiv);
    popupDiv.appendChild(closeButton);

    // Añadir el popup y el overlay al body
    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

    // Fetch rating data
    fetchRating(nombre, starsDisplay);

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

function fetchRating(machineName, displayElement) {
    fetch(`/api/get_machine_rating/${machineName}`)
        .then(response => response.json())
        .then(data => {
            const stars = renderStars(data.average);
            displayElement.innerHTML = `${stars} <span style="font-size: 0.8em; color: #9ca3af;">(${data.count})</span>`;
        })
        .catch(err => {
            console.error('Error fetching rating:', err);
            displayElement.textContent = 'Error al cargar puntuación';
        });
}

function renderStars(rating) {
    let starsHtml = '';
    for (let i = 1; i <= 5; i++) {
        if (i <= Math.round(rating)) {
            starsHtml += '<i class="bi bi-star-fill"></i>';
        } else {
            starsHtml += '<i class="bi bi-star"></i>';
        }
    }
    return starsHtml;
}

function openRatingModal(machineName) {
    // Check if user is logged in (simple check via global variable set in template)
    if (!currentUser) {
        alert("Debes iniciar sesión para puntuar.");
        return;
    }

    // REQUIREMENT: Check if user has completed the machine before allowing rating
    fetch(`/api/completed_machines/${encodeURIComponent(machineName)}`)
        .then(response => response.json())
        .then(data => {
            if (!data.completed) {
                alert("Debes marcar la máquina como completada antes de poder puntuarla.");
                return;
            }

            // Machine is completed, proceed with opening the rating modal
            showRatingModal(machineName);
        })
        .catch(err => {
            console.error('Error checking completion status:', err);
            alert("Error al verificar el estado de completitud.");
        });
}

function showRatingModal(machineName) {
    // Create modal elements similar to presentacion()
    var overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay-rating';
    overlayDiv.style.position = 'fixed';
    overlayDiv.style.top = '0';
    overlayDiv.style.left = '0';
    overlayDiv.style.width = '100%';
    overlayDiv.style.height = '100%';
    overlayDiv.style.background = 'rgba(0,0,0,0.8)';
    overlayDiv.style.zIndex = '10000'; // Higher than presentation modal
    overlayDiv.style.display = 'flex';
    overlayDiv.style.justifyContent = 'center';
    overlayDiv.style.alignItems = 'center';

    var modalDiv = document.createElement('div');
    modalDiv.style.background = '#0f172a';
    modalDiv.style.padding = '20px';
    modalDiv.style.borderRadius = '12px';
    modalDiv.style.border = '1px solid #3b82f6';
    modalDiv.style.width = 'min(400px, 90%)';
    modalDiv.style.color = 'white';
    modalDiv.style.textAlign = 'center';

    var title = document.createElement('h3');
    title.textContent = `Puntuar ${machineName}`; // Use already escaped nombre variable
    title.style.marginBottom = '20px';
    modalDiv.appendChild(title);

    const criteria = [
        { id: 'dificultad_score', label: 'Dificultad Acorde' },
        { id: 'aprendizaje_score', label: 'Aprendizaje' },
        { id: 'recomendaria_score', label: 'Recomendaría la Máquina' },
        { id: 'diversion_score', label: 'Diversión' }
    ];

    var scores = {};

    criteria.forEach(c => {
        var row = document.createElement('div');
        row.style.marginBottom = '15px';
        row.style.display = 'flex';
        row.style.justifyContent = 'space-between';
        row.style.alignItems = 'center';

        var label = document.createElement('span');
        label.textContent = c.label;
        label.style.fontSize = '0.9rem';

        var starsContainer = document.createElement('div');
        starsContainer.style.color = '#f59e0b';
        starsContainer.style.cursor = 'pointer';

        // Create 5 stars for input
        for (let i = 1; i <= 5; i++) {
            let star = document.createElement('i');
            star.className = 'bi bi-star';
            star.style.marginRight = '2px';
            star.dataset.value = i;
            star.dataset.criteria = c.id;

            star.onmouseover = function () { highlightStars(starsContainer, i); };
            star.onmouseout = function () { highlightStars(starsContainer, scores[c.id] || 0); };
            star.onclick = function () {
                scores[c.id] = i;
                highlightStars(starsContainer, i);
            };

            starsContainer.appendChild(star);
        }

        row.appendChild(label);
        row.appendChild(starsContainer);
        modalDiv.appendChild(row);
    });

    var btnContainer = document.createElement('div');
    btnContainer.style.marginTop = '20px';
    btnContainer.style.display = 'flex';
    btnContainer.style.justifyContent = 'space-between';

    var cancelBtn = document.createElement('button');
    cancelBtn.textContent = 'Cancelar';
    cancelBtn.className = 'btn btn-secondary btn-sm';
    cancelBtn.onclick = function () { document.body.removeChild(overlayDiv); };

    var saveBtn = document.createElement('button');
    saveBtn.textContent = 'Guardar';
    saveBtn.className = 'btn btn-primary btn-sm';
    saveBtn.onclick = function () {
        // Validate all scores selected
        if (Object.keys(scores).length < 4) {
            alert("Por favor valora todos los puntos.");
            return;
        }

        // Send to API
        fetch('/api/rate_machine', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                maquina_nombre: machineName,
                ...scores
            })
        })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    alert("Puntuación guardada!");
                    document.body.removeChild(overlayDiv);
                    // Refresh rating display in parent modal
                    const starsDisplay = document.getElementById('machine-avg-rating');
                    if (starsDisplay) fetchRating(machineName, starsDisplay);
                } else {
                    alert("Error: " + data.message);
                }
            })
            .catch(err => alert("Error de red"));
    };

    btnContainer.appendChild(cancelBtn);
    btnContainer.appendChild(saveBtn);
    modalDiv.appendChild(btnContainer);

    overlayDiv.appendChild(modalDiv);
    document.body.appendChild(overlayDiv);

    // Close modal when clicking outside
    overlayDiv.addEventListener('click', function (event) {
        if (event.target === overlayDiv) {
            document.body.removeChild(overlayDiv);
        }
    });

    // Fetch existing user rating if any
    fetch(`/api/get_machine_rating/${machineName}`)
        .then(res => res.json())
        .then(data => {
            if (data.user_rating) {
                scores = {
                    dificultad_score: data.user_rating.dificultad,
                    aprendizaje_score: data.user_rating.aprendizaje,
                    recomendaria_score: data.user_rating.recomendaria,
                    diversion_score: data.user_rating.diversion
                };
                // Update UI stars
                const starContainers = modalDiv.querySelectorAll('div[style*="cursor: pointer"]');
                criteria.forEach((c, idx) => {
                    highlightStars(starContainers[idx], scores[c.id]);
                });
            }
        });
}

function highlightStars(container, value) {
    const stars = container.children;
    for (let i = 0; i < stars.length; i++) {
        if (i < value) {
            stars[i].className = 'bi bi-star-fill';
        } else {
            stars[i].className = 'bi bi-star';
        }
    }
}
