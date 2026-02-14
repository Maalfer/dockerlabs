// Utility function to escape HTML and prevent XSS attacks
// Inject Shared Styles
function injectRankingStyles() {
    const styleId = 'minimal-ranking-styles-v2';
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
                pointer-events: none; /* Block interactions when hidden */
                transition: opacity 0.2s ease;
            }

            .overlay.visible {
                opacity: 1;
                pointer-events: auto; /* Enable when visible */
            }

            .popup {
                background: #1e293b;
                color: #f1f5f9;
                border: 1px solid rgba(148, 163, 184, 0.1);
                border-radius: 16px;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -48%) scale(0.96);
                z-index: 9999;
                padding: 2rem;
                width: min(520px, 92vw);
                max-height: 85vh;
                overflow-y: auto;
                opacity: 0;
                pointer-events: none; /* Block interactions when hidden */
                font-family: 'Inter', sans-serif;
                transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            }

            .popup.visible {
                opacity: 1;
                transform: translate(-50%, -50%) scale(1);
                pointer-events: auto; /* Enable when visible */
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
                z-index: 10;
            }

            .modal-close-button:hover {
                color: #f1f5f9;
                background: rgba(255,255,255,0.05);
            }

            .modal-header {
                text-align: center;
                margin-bottom: 1.5rem;
                display: flex;
                flex-direction: column;
                align-items: center;
            }

            .modal-title {
                margin: 0;
                font-size: 1.25rem;
                font-weight: 700;
                color: #ffffff;
                letter-spacing: -0.01em;
            }

            .modal-subtitle {
                margin: 0.25rem 0 0;
                font-size: 0.8rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: #64748b;
                font-weight: 600;
            }

            /* Search Bar */
            .ranking-search-container {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 1rem;
                gap: 1rem;
            }

            .search-wrapper {
                display: flex;
                align-items: center;
                background: rgba(15, 23, 42, 0.5);
                border: 1px solid #334155;
                border-radius: 999px;
                padding: 0.35rem 1rem;
                flex: 1;
                transition: border-color 0.2s;
            }

            .search-wrapper:focus-within {
                border-color: #3b82f6;
            }

            .search-input {
                background: transparent;
                border: none;
                color: #f1f5f9;
                font-size: 0.875rem;
                width: 100%;
                outline: none;
                font-family: 'Inter', sans-serif;
            }
            
            .search-icon-btn {
                background: none;
                border: none;
                color: #64748b;
                cursor: pointer;
                padding: 0;
                display: flex;
            }

            /* List Items */
            .ranking-list {
                list-style: none;
                padding: 0;
                margin: 0;
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }

            .ranking-item {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0.75rem 1rem;
                background: rgba(30, 41, 59, 0.4);
                border: 1px solid rgba(148, 163, 184, 0.05); /* very subtle */
                border-radius: 12px;
                transition: all 0.2s ease;
                cursor: pointer;
            }

            .ranking-item:hover {
                background: rgba(30, 41, 59, 1);
                border-color: #334155;
                transform: translateY(-1px);
            }

            .rank-badge {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                min-width: 2rem;
                height: 2rem;
                border-radius: 8px;
                background: rgba(15, 23, 42, 0.5);
                color: #94a3b8;
                font-weight: 700;
                font-size: 0.875rem;
                margin-right: 1rem;
            }

            .rank-1 { color: #facc15; background: rgba(250, 204, 21, 0.1); border: 1px solid rgba(250, 204, 21, 0.2); }
            .rank-2 { color: #e2e8f0; background: rgba(226, 232, 240, 0.1); border: 1px solid rgba(226, 232, 240, 0.2); }
            .rank-3 { color: #ca8a04; background: rgba(202, 138, 4, 0.1); border: 1px solid rgba(202, 138, 4, 0.2); }

            .user-info {
                flex: 1;
                display: flex;
                flex-direction: column;
            }

            .user-name {
                font-weight: 600;
                color: #f1f5f9;
                font-size: 0.95rem;
            }

            .user-points {
                font-weight: 700;
                color: #60a5fa;
                font-size: 0.9rem;
            }

            /* Author Profile Specific */
            .profile-header {
                display: flex;
                align-items: center;
                gap: 1.5rem;
                margin-bottom: 1.5rem;
            }

            .profile-avatar {
                width: 72px;
                height: 72px;
                border-radius: 50%;
                border: 2px solid #3b82f6;
                object-fit: cover;
                cursor: pointer;
                transition: transform 0.2s;
            }
            .profile-avatar:hover { transform: scale(1.05); }

            .profile-details h2 {
                margin: 0;
                font-size: 1.25rem;
                font-weight: 700;
                color: #f8fafc;
                cursor: pointer; 
            }
            .profile-details h2:hover { color: #60a5fa; }

            .profile-stats {
                margin-top: 0.25rem;
                font-size: 0.85rem;
                color: #94a3b8;
            }

            .social-bar {
                display: flex;
                gap: 1rem;
                margin-bottom: 1.5rem;
                padding: 0.75rem 1.5rem;
                background: rgba(15, 23, 42, 0.5);
                border-radius: 999px;
                justify-content: center;
                width: fit-content;
                margin-left: auto;
                margin-right: auto;
            }
            
            .section-title {
                font-size: 0.75rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: #64748b;
                margin-bottom: 0.75rem;
                font-weight: 600;
            }

            .mini-list-item {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                padding: 0.5rem 0.75rem;
                background: rgba(30, 41, 59, 0.3);
                border: 1px solid transparent;
                border-radius: 8px;
                margin-bottom: 0.5rem;
            }
            
            .mini-list-item:hover {
                border-color: #334155;
            }
            
            .mini-img {
                width: 32px;
                height: 32px;
                border-radius: 6px;
                object-fit: cover;
            }
        `;
        document.head.appendChild(style);
    }
}


function openBiographyModal(authorName, biography, profileImageUrl) {
    injectRankingStyles();
    const nombre = (authorName || '').trim();
    if (!nombre) return;
    const bioText = (biography || 'Este usuario aún no ha agregado una biografía.').trim();

    // Elements
    var overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay';
    overlayDiv.style.zIndex = '10060'; // High z-index for 3rd level

    var popupDiv = document.createElement('div');
    popupDiv.className = 'popup';
    popupDiv.style.width = 'min(440px, 90%)';
    popupDiv.style.zIndex = '10061';

    var closeButton = document.createElement('button');
    closeButton.className = 'modal-close-button';
    closeButton.innerHTML = '&times;';
    closeButton.onclick = closePopup;

    const content = `
        <div class="modal-header">
            <h2 class="modal-title">Biografía</h2>
        </div>
        
        <div style="display: flex; flex-direction: column; align-items: center; gap: 1rem; text-align: center;">
            <img src="${escapeHtml(profileImageUrl)}" style="width: 80px; height: 80px; border-radius: 50%; border: 2px solid #3b82f6; object-fit: cover;">
            
            <div>
                <h3 style="margin: 0; color: #f1f5f9; font-size: 1.1rem;">${escapeHtml(nombre)}</h3>
            </div>
            
            <div style="
                background: rgba(15, 23, 42, 0.5);
                padding: 1rem;
                border-radius: 8px;
                border: 1px solid #334155;
                width: 100%;
                text-align: left;
                font-size: 0.9rem;
                line-height: 1.6;
                color: #cbd5e1;
                white-space: pre-wrap;
            ">
                ${escapeHtml(bioText)}
            </div>
        </div>
    `;

    popupDiv.innerHTML = content;
    popupDiv.appendChild(closeButton);
    overlayDiv.appendChild(popupDiv);
    document.body.appendChild(overlayDiv);

    setTimeout(() => {
        popupDiv.classList.add('visible');
        overlayDiv.classList.add('visible');
    }, 10);

    overlayDiv.onclick = (e) => { if (e.target === overlayDiv) closePopup(); };

    function closePopup() {
        popupDiv.classList.remove('visible');
        overlayDiv.classList.remove('visible');
        setTimeout(() => {
            if (popupDiv.parentNode) document.body.removeChild(popupDiv);
            if (overlayDiv.parentNode) document.body.removeChild(overlayDiv);
        }, 300);
    }
}


function getSocialLinksHtml(data) {
    const linkedin = data.linkedin_url;
    const github = data.github_url;
    const youtube = data.youtube_url;

    if (!linkedin && !github && !youtube) return '';

    let html = '<div class="social-bar">';

    if (linkedin) html += `<a href="${escapeHtml(linkedin)}" target="_blank" style="color: #0077b5; font-size: 1.25rem;"><i class="bi bi-linkedin"></i></a>`;
    if (github) html += `<a href="${escapeHtml(github)}" target="_blank" style="color: #f1f5f9; font-size: 1.25rem;"><i class="bi bi-github"></i></a>`;
    if (youtube) html += `<a href="${escapeHtml(youtube)}" target="_blank" style="color: #ef4444; font-size: 1.25rem;"><i class="bi bi-youtube"></i></a>`;

    html += '</div>';
    return html;
}

function openAuthorProfileModal(authorName) {
    injectRankingStyles();
    const nombre = (authorName || '').trim();
    if (!nombre) return;

    fetch('/api/author_profile?nombre=' + encodeURIComponent(nombre))
        .then(response => response.json().then(data => ({ ok: response.ok, data })))
        .then(result => {
            if (!result.ok) {
                alert(result.data.error || 'Error al cargar perfil.');
                return;
            }
            const data = result.data;

            var overlayDiv = document.createElement('div');
            overlayDiv.className = 'overlay';
            overlayDiv.style.zIndex = '10050'; // Higher z-index for 2nd level

            var popupDiv = document.createElement('div');
            popupDiv.className = 'popup';
            popupDiv.style.zIndex = '10051';

            var closeButton = document.createElement('button');
            closeButton.className = 'modal-close-button';
            closeButton.innerHTML = '&times;';
            closeButton.onclick = closePopup;

            // --- Structure Content ---

            // Machines List
            let maquinasHtml = '<div style="margin-top: 1.5rem;">';
            if (data.maquinas && data.maquinas.length > 0) {
                maquinasHtml += '<div class="section-title">Máquinas Creadas</div>';
                data.maquinas.forEach(m => {
                    maquinasHtml += `
                        <div class="mini-list-item">
                            ${m.imagen_url ? `<img src="${escapeHtml(m.imagen_url)}" class="mini-img">` : ''}
                            <div style="flex:1;">
                                <div style="font-weight: 600; font-size: 0.9rem; color: #f1f5f9;">${escapeHtml(m.nombre)}</div>
                                <div style="font-size: 0.75rem; color: #64748b; text-transform: uppercase;">${escapeHtml(m.dificultad)}</div>
                            </div>
                        </div>
                    `;
                });
            } else {
                maquinasHtml += '<div class="section-title">Máquinas Creadas</div><p style="font-size: 0.85rem; color: #64748b; font-style: italic;">Sin máquinas registradas.</p>';
            }
            maquinasHtml += '</div>';

            // Writeups List
            let writeupsHtml = '<div style="margin-top: 1.5rem;">';
            if (data.writeups && data.writeups.length > 0) {
                writeupsHtml += '<div class="section-title">Writeups Enviados</div>';
                data.writeups.forEach(w => {
                    writeupsHtml += `
                        <div class="mini-list-item" style="justify-content: space-between;">
                            <div>
                                <div style="font-weight: 600; font-size: 0.9rem; color: #f1f5f9;">${escapeHtml(w.maquina)}</div>
                                <div style="font-size: 0.75rem; color: #64748b;">${escapeHtml(w.tipo || '')}</div>
                            </div>
                            <a href="${escapeHtml(w.url)}" target="_blank" style="font-size: 0.8rem; color: #3b82f6; text-decoration: none;">Ver ↗</a>
                        </div>
                     `;
                });
            } else {
                writeupsHtml += '<div class="section-title">Writeups Enviados</div><p style="font-size: 0.85rem; color: #64748b; font-style: italic;">Sin writeups enviados.</p>';
            }
            writeupsHtml += '</div>';

            const content = `
                <div class="profile-header">
                    <img src="${escapeHtml(data.profile_image_url)}" class="profile-avatar" id="profile-photo-trigger">
                    <div class="profile-details">
                        <h2 id="profile-name-trigger">${escapeHtml(data.nombre)}</h2>
                        <div class="profile-stats">
                            Máquinas: <b>${data.maquinas ? data.maquinas.length : 0}</b> · Writeups: <b>${data.writeups ? data.writeups.length : 0}</b>
                        </div>
                    </div>
                </div>
                
                ${getSocialLinksHtml(data)}
                
                <div style="height: 1px; background: #334155; width: 100%; margin: 1rem 0;"></div>
                
                ${maquinasHtml}
                ${writeupsHtml}
            `;

            popupDiv.innerHTML = content;
            popupDiv.appendChild(closeButton);
            overlayDiv.appendChild(popupDiv);
            document.body.appendChild(overlayDiv);

            // Click triggers for bio
            const openBio = () => openBiographyModal(data.nombre, data.biography, data.profile_image_url);
            popupDiv.querySelector('#profile-photo-trigger').onclick = openBio;
            popupDiv.querySelector('#profile-name-trigger').onclick = openBio;

            setTimeout(() => {
                popupDiv.classList.add('visible');
                overlayDiv.classList.add('visible');
            }, 10);

            overlayDiv.onclick = (e) => { if (e.target === overlayDiv) closePopup(); };

            function closePopup() {
                popupDiv.classList.remove('visible');
                overlayDiv.classList.remove('visible');
                setTimeout(() => {
                    if (popupDiv.parentNode) document.body.removeChild(popupDiv);
                    if (overlayDiv.parentNode) document.body.removeChild(overlayDiv);
                }, 300);
            }

        })
        .catch(err => alert("Error cargando perfil"));
}


function ranking() {
    injectRankingStyles();

    var overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay';

    var popupDiv = document.createElement('div');
    popupDiv.className = 'popup';

    var closeButton = document.createElement('button');
    closeButton.className = 'modal-close-button';
    closeButton.innerHTML = '&times;';
    closeButton.onclick = closePopup;

    const navAndSearchHTML = `
        <div class="modal-header">
            <h1 class="modal-title">Clasificación</h1>
            <div class="modal-subtitle">Writeups de la comunidad</div>
        </div>

        <div class="ranking-search-container">
            <span style="font-size: 0.8rem; color: #64748b; font-weight: 500;">Filtrar</span>
            <div class="search-wrapper">
                <input type="text" id="rankingSearchInput" class="search-input" placeholder="Buscar usuario...">
                <button id="rankingSearchButton" class="search-icon-btn"><i class="bi bi-search"></i></button>
            </div>
        </div>
        <div id="ranking-list-container"></div>
    `;

    popupDiv.innerHTML = navAndSearchHTML;
    popupDiv.appendChild(closeButton);

    fetch('/api/ranking_writeups')
        .then(res => {
            if (!res.ok) throw new Error('Error API');
            return res.json();
        })
        .then(data => {
            data.sort((a, b) => b.puntos - a.puntos);

            const listContainer = popupDiv.querySelector('#ranking-list-container');
            const ul = document.createElement('ul');
            ul.className = 'ranking-list';

            data.forEach((item, index) => {
                const li = document.createElement('li');
                li.className = 'ranking-item';
                li.dataset.nombre = (item.nombre || '').toLowerCase();

                let badgeClass = 'rank-badge';
                let icon = '#' + (index + 1);

                if (index === 0) { badgeClass += ' rank-1'; icon = '🥇'; }
                else if (index === 1) { badgeClass += ' rank-2'; icon = '🥈'; }
                else if (index === 2) { badgeClass += ' rank-3'; icon = '🥉'; }

                li.innerHTML = `
                    <div class="${badgeClass}">${icon}</div>
                     ${item.imagen_url ? `<img src="${escapeHtml(item.imagen_url)}" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover; margin-right: 12px;">` : ''}
                    <div class="user-info">
                        <span class="user-name">${escapeHtml(item.nombre)}</span>
                    </div>
                    <div class="user-points">${item.puntos} pts</div>
                `;

                li.onclick = () => openAuthorProfileModal(item.nombre);
                ul.appendChild(li);
            });
            listContainer.appendChild(ul);

            // Search Logic
            const searchInput = popupDiv.querySelector('#rankingSearchInput');
            const filterList = () => {
                const term = searchInput.value.toLowerCase();
                ul.querySelectorAll('li').forEach(li => {
                    const name = li.dataset.nombre;
                    li.style.display = name.includes(term) ? 'flex' : 'none';
                });
            };
            searchInput.oninput = filterList;

        })
        .catch(err => {
            console.error(err);
            popupDiv.innerHTML += `<p style="text-align:center; color: #ef4444;">Error cargando ranking.</p>`;
        });

    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

    setTimeout(() => {
        popupDiv.classList.add('visible');
        overlayDiv.classList.add('visible');
    }, 10);

    overlayDiv.onclick = (e) => { if (e.target === overlayDiv) closePopup(); };

    function closePopup() {
        popupDiv.classList.remove('visible');
        overlayDiv.classList.remove('visible');
        setTimeout(() => {
            if (popupDiv.parentNode) document.body.removeChild(popupDiv);
            if (overlayDiv.parentNode) document.body.removeChild(overlayDiv);
        }, 300);
    }
}


function rankingautores() {
    injectRankingStyles();

    var overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay';

    var popupDiv = document.createElement('div');
    popupDiv.className = 'popup';

    var closeButton = document.createElement('button');
    closeButton.className = 'modal-close-button';
    closeButton.innerHTML = '&times;';
    closeButton.onclick = closePopup;

    const navAndSearchHTML = `
        <div class="modal-header">
            <h1 class="modal-title">Clasificación Autores</h1>
            <div class="modal-subtitle">Máquinas Creadas</div>
        </div>

        <div class="ranking-search-container">
            <span style="font-size: 0.8rem; color: #64748b; font-weight: 500;">Filtrar</span>
            <div class="search-wrapper">
                <input type="text" id="rankingAutoresSearchInput" class="search-input" placeholder="Buscar autor...">
                <button class="search-icon-btn"><i class="bi bi-search"></i></button>
            </div>
        </div>
        <div id="ranking-list-container"></div>
    `;

    popupDiv.innerHTML = navAndSearchHTML;
    popupDiv.appendChild(closeButton);

    fetch('/api/ranking_autores')
        .then(res => {
            if (!res.ok) throw new Error('Error API');
            return res.json();
        })
        .then(data => {
            // Sort by machines count (descending)
            data.sort((a, b) => b.maquinas - a.maquinas);

            const listContainer = popupDiv.querySelector('#ranking-list-container');
            const ul = document.createElement('ul');
            ul.className = 'ranking-list';

            data.forEach((item, index) => {
                const li = document.createElement('li');
                li.className = 'ranking-item';
                li.dataset.nombre = (item.autor || '').toLowerCase();

                let badgeClass = 'rank-badge';
                let icon = '#' + (index + 1);

                if (index === 0) { badgeClass += ' rank-1'; icon = '🥇'; }
                else if (index === 1) { badgeClass += ' rank-2'; icon = '🥈'; }
                else if (index === 2) { badgeClass += ' rank-3'; icon = '🥉'; }

                li.innerHTML = `
                    <div class="${badgeClass}">${icon}</div>
                     ${item.imagen ? `<img src="${escapeHtml(item.imagen)}" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover; margin-right: 12px;">` : ''}
                    <div class="user-info">
                        <span class="user-name">${escapeHtml(item.autor)}</span>
                    </div>
                    <div class="user-points" style="color: #22d3ee;">${item.maquinas} máq.</div>
                `;

                li.onclick = () => openAuthorProfileModal(item.autor);
                ul.appendChild(li);
            });
            listContainer.appendChild(ul);

            // Search Logic
            const searchInput = popupDiv.querySelector('#rankingAutoresSearchInput');
            const filterList = () => {
                const term = searchInput.value.toLowerCase();
                ul.querySelectorAll('li').forEach(li => {
                    const name = li.dataset.nombre;
                    li.style.display = name.includes(term) ? 'flex' : 'none';
                });
            };
            searchInput.oninput = filterList;

        })
        .catch(err => {
            console.error(err);
            popupDiv.innerHTML += `<p style="text-align:center; color: #ef4444;">Error cargando ranking.</p>`;
        });

    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

    setTimeout(() => {
        popupDiv.classList.add('visible');
        overlayDiv.classList.add('visible');
    }, 10);

    overlayDiv.onclick = (e) => { if (e.target === overlayDiv) closePopup(); };

    function closePopup() {
        popupDiv.classList.remove('visible');
        overlayDiv.classList.remove('visible');
        setTimeout(() => {
            if (popupDiv.parentNode) document.body.removeChild(popupDiv);
            if (overlayDiv.parentNode) document.body.removeChild(overlayDiv);
        }, 300);
    }
}
