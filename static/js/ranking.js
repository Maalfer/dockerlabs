// Utility function to escape HTML and prevent XSS attacks
function escapeHtml(text) {
    if (!text) return text;
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function openBiographyModal(authorName, biography, profileImageUrl) {
    const nombre = (authorName || '').trim();
    if (!nombre) return;

    const bioText = (biography || 'Este usuario aún no ha agregado una biografía.').trim();

    // Escape HTML to prevent XSS attacks
    const escapedNombre = escapeHtml(nombre);
    const escapedBioText = escapeHtml(bioText);
    const escapedProfileImageUrl = escapeHtml(profileImageUrl);

    var overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay';
    overlayDiv.style.position = 'fixed';
    overlayDiv.style.top = '0';
    overlayDiv.style.left = '0';
    overlayDiv.style.width = '100%';
    overlayDiv.style.height = '100%';
    overlayDiv.style.background = 'radial-gradient(circle at top, rgba(15,23,42,0.92), rgba(15,23,42,0.96))';
    overlayDiv.style.zIndex = '10001';
    overlayDiv.style.opacity = '0';
    overlayDiv.style.transition = 'opacity 0.3s ease';
    overlayDiv.style.backdropFilter = 'blur(4px)';

    var popupDiv = document.createElement('div');
    popupDiv.className = 'popup';
    popupDiv.style.background = 'radial-gradient(circle at top left, #0f172a 0%, #020617 60%)';
    popupDiv.style.color = '#e5e7eb';
    popupDiv.style.border = '2px solid rgba(59,130,246,0.95)';
    popupDiv.style.borderRadius = '12px';
    popupDiv.style.boxShadow = '0 16px 40px rgba(0, 0, 0, 0.75)';
    popupDiv.style.position = 'absolute';
    popupDiv.style.left = '50%';
    popupDiv.style.top = '50%';
    popupDiv.style.transform = 'translate(-50%, -50%) scale(0.96)';
    popupDiv.style.padding = '22px 24px';
    popupDiv.style.width = '480px';
    popupDiv.style.maxWidth = '95vw';
    popupDiv.style.maxHeight = '80vh';
    popupDiv.style.overflowY = 'auto';
    popupDiv.style.opacity = '0';
    popupDiv.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
    popupDiv.style.textAlign = 'left';

    var closeButton = document.createElement('button');
    closeButton.innerHTML = '&times;';
    closeButton.classList.add('modal-close-button');
    closeButton.addEventListener('click', function () {
        document.body.removeChild(overlayDiv);
    });

    var contenido = `
        <div style="display: flex; flex-direction: column; gap: 16px;">
            <div style="display: flex; align-items: center; gap: 14px;">
                <img 
                    src="${escapedProfileImageUrl}" 
                    alt="${escapedNombre}" 
                    style="width: 64px; height: 64px; border-radius: 999px; border: 2px solid rgba(96,165,250,0.9); object-fit: cover;"
                >
                <div>
                    <h2 style="
                        margin: 0 0 4px;
                        font-size: 1.05rem;
                        text-transform: uppercase;
                        letter-spacing: 0.16em;
                        background: linear-gradient(135deg, var(--primary-blue-light), var(--accent-cyan));
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        background-clip: text;
                    ">
                        ${escapedNombre}
                    </h2>
                    <p style="margin: 0; font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.12em;">
                        Biografía
                    </p>
                </div>
            </div>
            <hr style="border: 0; border-top: 1px solid rgba(51,65,85,0.9); margin: 4px 0;">
            <div style="
                padding: 12px 14px;
                border-radius: 8px;
                background: rgba(15,23,42,0.95);
                border: 1px solid rgba(51,65,85,0.95);
                font-size: 0.88rem;
                line-height: 1.6;
                color: var(--text-primary);
                white-space: pre-wrap;
                word-wrap: break-word;
                text-align: left;
            ">
                ${escapedBioText}
            </div>
        </div>
    `;

    popupDiv.innerHTML = contenido;
    popupDiv.appendChild(closeButton);

    overlayDiv.appendChild(popupDiv);
    document.body.appendChild(overlayDiv);

    requestAnimationFrame(function () {
        overlayDiv.style.opacity = '1';
        popupDiv.style.opacity = '1';
        popupDiv.style.transform = 'translate(-50%, -50%) scale(1)';
    });

    overlayDiv.addEventListener('click', function (e) {
        if (e.target === overlayDiv) {
            document.body.removeChild(overlayDiv);
        }
    });
}

function getSocialLinksHtml(data) {
    const linkedin = data.linkedin_url;
    const github = data.github_url;
    const youtube = data.youtube_url;

    // If no social links, return empty string
    if (!linkedin && !github && !youtube) {
        return '';
    }

    let socialHtml = `
        <div style="
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 8px 12px;
            border-radius: 8px;
            background: rgba(15,23,42,0.95);
            border: 1px solid rgba(51,65,85,0.95);
            margin-top: 8px;
        ">
            <span style="font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.1em;">
                Redes:
            </span>
            <div style="display: flex; gap: 10px;">
    `;

    if (linkedin) {
        socialHtml += `
            <a href="${escapeHtml(linkedin)}" target="_blank" rel="noopener noreferrer" 
               style="color: #0077B5; font-size: 1.3rem; transition: transform 0.2s;"
               onmouseover="this.style.transform='scale(1.15)'"
               onmouseout="this.style.transform='scale(1)'"
               title="LinkedIn">
                <i class="bi bi-linkedin"></i>
            </a>
        `;
    }

    if (github) {
        socialHtml += `
            <a href="${escapeHtml(github)}" target="_blank" rel="noopener noreferrer" 
               style="color: #e5e7eb; font-size: 1.3rem; transition: transform 0.2s;"
               onmouseover="this.style.transform='scale(1.15)'"
               onmouseout="this.style.transform='scale(1)'"
               title="GitHub">
                <i class="bi bi-github"></i>
            </a>
        `;
    }

    if (youtube) {
        socialHtml += `
            <a href="${escapeHtml(youtube)}" target="_blank" rel="noopener noreferrer" 
               style="color: #FF0000; font-size: 1.3rem; transition: transform 0.2s;"
               onmouseover="this.style.transform='scale(1.15)'"
               onmouseout="this.style.transform='scale(1)'"
               title="YouTube">
                <i class="bi bi-youtube"></i>
            </a>
        `;
    }

    socialHtml += `
            </div>
        </div>
    `;

    return socialHtml;
}

function openAuthorProfileModal(authorName) {
    const nombre = (authorName || '').trim();
    if (!nombre) return;

    fetch('/api/author_profile?nombre=' + encodeURIComponent(nombre))
        .then(response => response.json().then(data => ({ ok: response.ok, data })))
        .then(result => {
            if (!result.ok) {
                alert(result.data && result.data.error ? result.data.error : 'Error al cargar el perfil del autor.');
                return;
            }

            const data = result.data;

            var overlayDiv = document.createElement('div');
            overlayDiv.className = 'overlay';
            overlayDiv.style.position = 'fixed';
            overlayDiv.style.top = '0';
            overlayDiv.style.left = '0';
            overlayDiv.style.width = '100%';
            overlayDiv.style.height = '100%';
            overlayDiv.style.background = 'radial-gradient(circle at top, rgba(15,23,42,0.92), rgba(15,23,42,0.96))';
            overlayDiv.style.zIndex = '10000';
            overlayDiv.style.opacity = '0';
            overlayDiv.style.transition = 'opacity 0.3s ease';
            overlayDiv.style.backdropFilter = 'blur(4px)';

            var popupDiv = document.createElement('div');
            popupDiv.className = 'popup';
            popupDiv.style.background = 'radial-gradient(circle at top left, #0f172a 0%, #020617 60%)';
            popupDiv.style.color = '#e5e7eb';
            popupDiv.style.border = '2px solid rgba(59,130,246,0.95)';
            popupDiv.style.borderRadius = '12px';
            popupDiv.style.boxShadow = '0 16px 40px rgba(0, 0, 0, 0.75)';
            popupDiv.style.position = 'absolute';
            popupDiv.style.left = '50%';
            popupDiv.style.top = '50%';
            popupDiv.style.transform = 'translate(-50%, -50%) scale(0.96)';
            popupDiv.style.padding = '22px 24px';
            popupDiv.style.width = '520px';
            popupDiv.style.maxWidth = '95vw';
            popupDiv.style.maxHeight = '80vh';
            popupDiv.style.overflowY = 'auto';
            popupDiv.style.opacity = '0';
            popupDiv.style.transition = 'opacity 0.25s ease, transform 0.25s ease';

            var closeButton = document.createElement('button');
            closeButton.innerHTML = '&times;';
            closeButton.classList.add('modal-close-button');
            closeButton.addEventListener('click', function () {
                document.body.removeChild(overlayDiv);
            });

            var maquinasHtml = '';
            if (data.maquinas && data.maquinas.length > 0) {
                maquinasHtml += '<div style="margin-top: 14px;">';
                maquinasHtml += '<h3 style="font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--text-muted); margin-bottom: 6px;">Máquinas creadas</h3>';
                maquinasHtml += '<ul style="list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px;">';

                data.maquinas.forEach(function (m) {
                    maquinasHtml += `
                        <li style="
                            display: flex;
                            align-items: center;
                            gap: 10px;
                            padding: 6px 8px;
                            border-radius: 8px;
                            background: rgba(15,23,42,0.95);
                            border: 1px solid rgba(51,65,85,0.95);
                        ">
                            ${m.imagen_url ? `
                                <img src="${escapeHtml(m.imagen_url)}" alt="${escapeHtml(m.nombre)}" style="width: 40px; height: 40px; border-radius: 8px; object-fit: cover; border: 1px solid rgba(148,163,184,0.7);">
                            ` : ''}
                            <div style="flex: 1;">
                                <div style="font-weight: 600; font-size: 0.86rem; color: var(--text-primary);">${escapeHtml(m.nombre)}</div>
                                <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.12em;">${escapeHtml(m.dificultad)}</div>
                            </div>
                        </li>
                    `;
                });

                maquinasHtml += '</ul></div>';
            } else {
                maquinasHtml += `
                    <div style="margin-top: 14px;">
                        <h3 style="font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--text-muted); margin-bottom: 6px;">Máquinas creadas</h3>
                        <p style="font-size: 0.8rem; color: var(--text-secondary);">Este autor aún no tiene máquinas registradas.</p>
                    </div>
                `;
            }

            var writeupsHtml = '';
            if (data.writeups && data.writeups.length > 0) {
                writeupsHtml += '<div style="margin-top: 16px;">';
                writeupsHtml += '<h3 style="font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--text-muted); margin-bottom: 6px;">Writeups enviados</h3>';
                writeupsHtml += '<ul style="list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px;">';

                data.writeups.forEach(function (w) {
                    writeupsHtml += `
                        <li style="
                            padding: 6px 8px;
                            border-radius: 8px;
                            background: rgba(15,23,42,0.95);
                            border: 1px solid rgba(51,65,85,0.95);
                        ">
                            <div style="font-weight: 600; font-size: 0.84rem; color: var(--text-primary); margin-bottom: 2px;">
                                ${escapeHtml(w.maquina)}
                            </div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 4px;">
                                ${escapeHtml(w.tipo || '')}
                            </div>
                            <a href="${escapeHtml(w.url)}" target="_blank" rel="noopener noreferrer" style="font-size: 0.75rem; color: var(--accent-cyan); text-decoration: none;">
                                Ver writeup ↗
                            </a>
                        </li>
                    `;
                });

                writeupsHtml += '</ul></div>';
            } else {
                writeupsHtml += `
                    <div style="margin-top: 16px;">
                        <h3 style="font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--text-muted); margin-bottom: 6px;">Writeups enviados</h3>
                        <p style="font-size: 0.8rem; color: var(--text-secondary);">Este autor aún no ha enviado writeups.</p>
                    </div>
                `;
            }

            var contenido = `
                <div style="display: flex; flex-direction: column; gap: 14px;">
                    <div style="display: flex; align-items: center; gap: 14px;">
                        <img 
                            src="${escapeHtml(data.profile_image_url)}" 
                            alt="${escapeHtml(data.nombre)}" 
                            style="width: 64px; height: 64px; border-radius: 999px; border: 2px solid rgba(96,165,250,0.9); object-fit: cover; cursor: pointer;"
                            class="author-profile-photo"
                            data-author="${escapeHtml(data.nombre)}"
                            data-biography="${escapeHtml(data.biography || '')}"
                        >
                        <div>
                            <h2 
                                style="
                                    margin: 0 0 4px;
                                    font-size: 1.05rem;
                                    text-transform: uppercase;
                                    letter-spacing: 0.16em;
                                    background: linear-gradient(135deg, var(--primary-blue-light), var(--accent-cyan));
                                    -webkit-background-clip: text;
                                    -webkit-text-fill-color: transparent;
                                    background-clip: text;
                                    cursor: pointer;
                                "
                                class="author-profile-name"
                                data-author="${escapeHtml(data.nombre)}"
                                data-biography="${escapeHtml(data.biography || '')}"
                            >
                                ${escapeHtml(data.nombre)}
                            </h2>
                            <p style="margin: 0; font-size: 0.8rem; color: var(--text-muted);">
                                Máquinas: ${data.maquinas ? data.maquinas.length : 0} · Writeups: ${data.writeups ? data.writeups.length : 0}
                            </p>
                        </div>
                    </div>
                    ${getSocialLinksHtml(data)}
                    ${maquinasHtml}
                    ${writeupsHtml}
                </div>
            `;

            popupDiv.innerHTML = contenido;
            popupDiv.appendChild(closeButton);

            overlayDiv.appendChild(popupDiv);
            document.body.appendChild(overlayDiv);

            // Add click handlers for name and photo
            const profileName = popupDiv.querySelector('.author-profile-name');
            const profilePhoto = popupDiv.querySelector('.author-profile-photo');

            if (profileName) {
                profileName.addEventListener('click', function (e) {
                    e.stopPropagation();
                    openBiographyModal(data.nombre, data.biography, data.profile_image_url);
                });
            }

            if (profilePhoto) {
                profilePhoto.addEventListener('click', function (e) {
                    e.stopPropagation();
                    openBiographyModal(data.nombre, data.biography, data.profile_image_url);
                });
            }

            requestAnimationFrame(function () {
                overlayDiv.style.opacity = '1';
                popupDiv.style.opacity = '1';
                popupDiv.style.transform = 'translate(-50%, -50%) scale(1)';
            });

            overlayDiv.addEventListener('click', function (e) {
                if (e.target === overlayDiv) {
                    document.body.removeChild(overlayDiv);
                }
            });
        })
        .catch(function () {
            alert('Se produjo un error al cargar el perfil del autor.');
        });
}

function ranking() {
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

    var popupDiv = document.createElement('div');
    popupDiv.className = 'popup';
    popupDiv.style.width = 'min(420px, 92vw)';
    popupDiv.style.maxHeight = '80vh';
    popupDiv.style.background = 'radial-gradient(circle at top left, #0f172a 0%, #020617 60%)';
    popupDiv.style.color = '#e5e7eb';
    popupDiv.style.border = '2px solid rgba(59, 130, 246, 0.95)';
    popupDiv.style.borderRadius = '12px';
    popupDiv.style.boxShadow = '0 16px 40px rgba(0, 0, 0, 0.75)';
    popupDiv.style.position = 'fixed';
    popupDiv.style.top = '50%';
    popupDiv.style.left = '50%';
    popupDiv.style.transform = 'translate(-50%, -60%)';
    popupDiv.style.zIndex = '9999';
    popupDiv.style.padding = '22px 24px';
    popupDiv.style.textAlign = 'left';
    popupDiv.style.overflowY = 'auto';
    popupDiv.style.transition = 'opacity 0.3s ease, transform 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55)';
    popupDiv.style.opacity = '0';

    var closeButton = document.createElement('button');
    closeButton.innerHTML = '&times;';
    closeButton.classList.add('modal-close-button');
    closeButton.addEventListener('click', function () {
        closePopup();
    });

    var contenidoPopup = `
        <div style="margin-bottom: 8px; text-align: center;">
            <h1 style="
                margin: 0 0 4px;
                font-size: 1.05rem;
                letter-spacing: 0.14em;
                text-transform: uppercase;
                background: linear-gradient(135deg, var(--primary-blue-light), var(--accent-cyan));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            ">
                CLASIFICACIÓN
            </h1>
            <p style="
                margin: 0;
                font-size: 0.75rem;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.16em;
            ">
                Writeups de la comunidad
            </p>
        </div>

        <hr style="border: 0; border-top: 1px solid rgba(51,65,85,0.9); margin: 10px 0 10px;">

        <div style="
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 12px;
        ">
            <span style="
                font-size: 0.8rem;
                color: var(--text-secondary);
            ">
                Buscar por nombre
            </span>
            <div style="
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 4px 8px;
                border-radius: 999px;
                border: 1px solid rgba(148,163,184,0.6);
                background-color: rgba(15,23,42,0.98);
            ">
                <input
                    id="rankingSearchInput"
                    type="text"
                    placeholder="Ej: Pylon"
                    style="
                        border: none;
                        outline: none;
                        background: transparent;
                        color: var(--text-primary);
                        font-size: 0.8rem;
                        width: 150px;
                    "
                >
                <button
                    type="button"
                    id="rankingSearchButton"
                    style="
                        border: none;
                        background: none;
                        cursor: pointer;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: var(--text-secondary);
                        padding: 0;
                    "
                    title="Buscar"
                >
                    <i class="bi bi-search"></i>
                </button>
            </div>
        </div>
    `;

    fetch('/api/ranking_writeups')
        .then(response => {
            if (!response.ok) {
                throw new Error('No se pudo cargar el ranking desde la API');
            }
            return response.json();
        })
        .then(data => {
            data.sort((a, b) => b.puntos - a.puntos);

            var rankingList = `
                <ul style="
                    list-style: none;
                    padding: 0;
                    margin: 0;
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                ">
            `;

            data.forEach((item, index) => {
                let color = 'var(--text-secondary)';
                if (index === 0) color = 'gold';
                else if (index === 1) color = 'silver';
                else if (index === 2) color = '#cd7f32';

                let medal = '';
                if (index === 0) medal = '🥇';
                else if (index === 1) medal = '🥈';
                else if (index === 2) medal = '🥉';

                let positionSuffix = (index + 1) + 'º';

                rankingList += `
                    <li
                        class="ranking-author-item"
                        data-nombre="${(item.nombre || '').toLowerCase()}"
                        data-autor="${item.nombre}"
                        style="
                            margin: 0;
                            padding: 8px 10px;
                            border-radius: 10px;
                            background: radial-gradient(circle at top left, rgba(15,23,42,0.98) 0%, rgba(15,23,42,1) 55%);
                            border: 1px solid rgba(51,65,85,0.95);
                            display: flex;
                            align-items: center;
                            justify-content: space-between;
                            gap: 8px;
                            box-shadow: 0 6px 18px rgba(15,23,42,0.9);
                            position: relative;
                            overflow: hidden;
                            cursor: pointer;
                        "
                    >
                        <span style="
                            min-width: 52px;
                            display: inline-flex;
                            align-items: center;
                            justify-content: center;
                            font-weight: 700;
                            font-size: 0.8rem;
                            color: ${color};
                            padding: 4px 8px;
                            border-radius: 999px;
                            border: 1px solid ${color};
                            background: rgba(15,23,42,0.96);
                            text-shadow: 0 1px 3px rgba(0,0,0,0.6);
                        ">
                            ${medal ? medal + ' ' : ''}${positionSuffix}
                        </span>

                        <span style="
                            flex: 1;
                            text-align: left;
                            font-weight: 600;
                            font-size: 0.86rem;
                            color: var(--text-primary);
                            text-shadow: 0 1px 3px rgba(0,0,0,0.55);
                            white-space: nowrap;
                            overflow: hidden;
                            text-overflow: ellipsis;
                        ">
                            ${item.nombre}
                        </span>

                        <span style="
                            font-size: 0.8rem;
                            font-weight: 600;
                            color: ${color};
                            white-space: nowrap;
                        ">
                            ${item.puntos} pts
                        </span>
                    </li>
                `;
            });

            rankingList += '</ul>';

            contenidoPopup += rankingList;
            popupDiv.innerHTML = contenidoPopup;
            popupDiv.appendChild(closeButton);

            const authorItems = popupDiv.querySelectorAll('.ranking-author-item');
            authorItems.forEach(function (li) {
                li.addEventListener('click', function () {
                    const autor = this.getAttribute('data-autor') || '';
                    if (autor) {
                        openAuthorProfileModal(autor);
                    }
                });
            });

            const searchInput = popupDiv.querySelector('#rankingSearchInput');
            const searchButton = popupDiv.querySelector('#rankingSearchButton');

            function aplicarFiltroRanking() {
                if (!searchInput) return;
                const termino = searchInput.value.trim().toLowerCase();

                const items = popupDiv.querySelectorAll('ul li');
                items.forEach(li => {
                    const nombre = (li.dataset.nombre || li.textContent || '').toLowerCase();
                    if (!termino || nombre.includes(termino)) {
                        li.style.display = 'flex';
                    } else {
                        li.style.display = 'none';
                    }
                });
            }

            if (searchInput && searchButton) {
                searchButton.addEventListener('click', aplicarFiltroRanking);
                searchInput.addEventListener('keydown', function (e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        aplicarFiltroRanking();
                    }
                });
                searchInput.addEventListener('input', aplicarFiltroRanking);
            }
        })
        .catch(error => {
            console.error('Error al cargar el ranking:', error);
            contenidoPopup += '<p style="margin: 0; font-size: 0.85rem; color: var(--accent-red); text-align: center;">Error al cargar el ranking.</p>';
            popupDiv.innerHTML = contenidoPopup;
            popupDiv.appendChild(closeButton);
        });

    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

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
}

function rankingautores() {
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

    var popupDiv = document.createElement('div');
    popupDiv.className = 'popup';
    popupDiv.style.width = 'min(420px, 92vw)';
    popupDiv.style.maxHeight = '80vh';
    popupDiv.style.background = 'radial-gradient(circle at top left, #0f172a 0%, #020617 60%)';
    popupDiv.style.color = '#e5e7eb';
    popupDiv.style.border = '2px solid rgba(59, 130, 246, 0.95)';
    popupDiv.style.borderRadius = '12px';
    popupDiv.style.boxShadow = '0 16px 40px rgba(0, 0, 0, 0.75)';
    popupDiv.style.position = 'fixed';
    popupDiv.style.top = '50%';
    popupDiv.style.left = '50%';
    popupDiv.style.transform = 'translate(-50%, -60%)';
    popupDiv.style.zIndex = '9999';
    popupDiv.style.padding = '22px 24px';
    popupDiv.style.textAlign = 'left';
    popupDiv.style.overflowY = 'auto';
    popupDiv.style.transition = 'opacity 0.3s ease, transform 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55)';
    popupDiv.style.opacity = '0';

    var closeButton = document.createElement('button');
    closeButton.innerHTML = '&times;';
    closeButton.classList.add('modal-close-button');
    closeButton.addEventListener('click', function () {
        closePopup();
    });

    var contenidoPopup = `
        <div style="margin-bottom: 8px; text-align: center;">
            <h1 style="
                margin: 0 0 4px;
                font-size: 1.05rem;
                letter-spacing: 0.14em;
                text-transform: uppercase;
                background: linear-gradient(135deg, var(--primary-blue-light), var(--accent-cyan));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            ">
                CLASIFICACIÓN AUTORES
            </h1>
            <p style="
                margin: 0;
                font-size: 0.75rem;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.16em;
            ">
                Máquinas creadas
            </p>
        </div>

        <hr style="border: 0; border-top: 1px solid rgba(51,65,85,0.9); margin: 10px 0 10px;">

        <div style="
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 12px;
        ">
            <span style="
                font-size: 0.8rem;
                color: var(--text-secondary);
            ">
                Buscar autor
            </span>
            <div style="
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 4px 8px;
                border-radius: 999px;
                border: 1px solid rgba(148,163,184,0.6);
                background-color: rgba(15,23,42,0.98);
            ">
                <input
                    id="rankingAutoresSearchInput"
                    type="text"
                    placeholder="Ej: d1se0"
                    style="
                        border: none;
                        outline: none;
                        background: transparent;
                        color: var(--text-primary);
                        font-size: 0.8rem;
                        width: 150px;
                    "
                >
                <button
                    type="button"
                    id="rankingAutoresSearchButton"
                    style="
                        border: none;
                        background: none;
                        cursor: pointer;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: var(--text-secondary);
                        padding: 0;
                    "
                    title="Buscar"
                >
                    <i class="bi bi-search"></i>
                </button>
            </div>
        </div>
    `;

    fetch('/api/ranking_creadores')
        .then(response => {
            if (!response.ok) {
                throw new Error('No se pudo cargar el ranking de autores desde la API');
            }
            return response.json();
        })
        .then(data => {
            data.sort((a, b) => b.maquinas - a.maquinas);

            var rankingList = `
                <ul style="
                    list-style: none;
                    padding: 0;
                    margin: 0;
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                ">
            `;

            data.forEach((item, index) => {
                let color = 'var(--text-secondary)';
                if (index === 0) color = 'gold';
                else if (index === 1) color = 'silver';
                else if (index === 2) color = '#cd7f32';

                let medal = '';
                if (index === 0) medal = '🥇';
                else if (index === 1) medal = '🥈';
                else if (index === 2) medal = '🥉';

                let positionSuffix = (index + 1) + 'º';

                rankingList += `
                    <li
                        class="ranking-author-item"
                        data-nombre="${(item.nombre || '').toLowerCase()}"
                        data-autor="${item.nombre}"
                        style="
                            margin: 0;
                            padding: 8px 10px;
                            border-radius: 10px;
                            background: radial-gradient(circle at top left, rgba(15,23,42,0.98) 0%, rgba(15,23,42,1) 55%);
                            border: 1px solid rgba(51,65,85,0.95);
                            display: flex;
                            align-items: center;
                            justify-content: space-between;
                            gap: 8px;
                            box-shadow: 0 6px 18px rgba(15,23,42,0.9);
                            position: relative;
                            overflow: hidden;
                            cursor: pointer;
                        "
                    >
                        <span style="
                            min-width: 52px;
                            display: inline-flex;
                            align-items: center;
                            justify-content: center;
                            font-weight: 700;
                            font-size: 0.8rem;
                            color: ${color};
                            padding: 4px 8px;
                            border-radius: 999px;
                            border: 1px solid ${color};
                            background: rgba(15,23,42,0.96);
                            text-shadow: 0 1px 3px rgba(0,0,0,0.6);
                        ">
                            ${medal ? medal + ' ' : ''}${positionSuffix}
                        </span>

                        <span style="
                            flex: 1;
                            text-align: left;
                            font-weight: 600;
                            font-size: 0.86rem;
                            color: var(--text-primary);
                            text-shadow: 0 1px 3px rgba(0,0,0,0.55);
                            white-space: nowrap;
                            overflow: hidden;
                            text-overflow: ellipsis;
                        ">
                            ${item.nombre}
                        </span>

                        <span style="
                            font-size: 0.8rem;
                            font-weight: 600;
                            color: ${color};
                            white-space: nowrap;
                        ">
                            ${item.maquinas} máquinas
                        </span>
                    </li>
                `;
            });

            rankingList += '</ul>';

            contenidoPopup += rankingList;
            popupDiv.innerHTML = contenidoPopup;
            popupDiv.appendChild(closeButton);

            const authorItems = popupDiv.querySelectorAll('.ranking-author-item');
            authorItems.forEach(function (li) {
                li.addEventListener('click', function () {
                    const autor = this.getAttribute('data-autor') || '';
                    if (autor) {
                        openAuthorProfileModal(autor);
                    }
                });
            });

            const searchInputAutores = popupDiv.querySelector('#rankingAutoresSearchInput');
            const searchButtonAutores = popupDiv.querySelector('#rankingAutoresSearchButton');

            function aplicarFiltroRankingAutores() {
                if (!searchInputAutores) return;
                const termino = searchInputAutores.value.trim().toLowerCase();

                const items = popupDiv.querySelectorAll('ul li');
                items.forEach(li => {
                    const nombre = (li.dataset.nombre || li.textContent || '').toLowerCase();
                    if (!termino || nombre.includes(termino)) {
                        li.style.display = 'flex';
                    } else {
                        li.style.display = 'none';
                    }
                });
            }

            if (searchInputAutores && searchButtonAutores) {
                searchButtonAutores.addEventListener('click', aplicarFiltroRankingAutores);
                searchInputAutores.addEventListener('keydown', function (e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        aplicarFiltroRankingAutores();
                    }
                });
                searchInputAutores.addEventListener('input', aplicarFiltroRankingAutores);
            }
        })
        .catch(error => {
            console.error('Error al cargar el ranking de autores:', error);
            contenidoPopup += '<p style="margin: 0; font-size: 0.85rem; color: var(--accent-red); text-align: center;">Error al cargar el ranking.</p>';
            popupDiv.innerHTML = contenidoPopup;
            popupDiv.appendChild(closeButton);
        });

    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

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
}
