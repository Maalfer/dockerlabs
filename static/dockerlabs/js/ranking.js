// Utility function to escape HTML and prevent XSS attacks
// Inject Shared Styles
function injectRankingStyles() {
    const styleId = 'minimal-ranking-styles-v2';
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
                z-index: 10001;
                padding: 2rem;
                width: min(520px, 92vw);
                max-width: 100%;
                box-sizing: border-box;
                max-height: 85vh;
                overflow-y: auto;
                overflow-x: hidden;
                opacity: 0;
                pointer-events: none; /* Block interactions when hidden */
                font-family: 'Fira Code', monospace;
                transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
                scrollbar-width: thin;
                scrollbar-color: rgba(59, 130, 246, 0.35) transparent;
            }

            .popup::-webkit-scrollbar {
                width: 8px;
            }

            .popup::-webkit-scrollbar-track {
                background: transparent;
            }

            .popup::-webkit-scrollbar-thumb {
                background: rgba(59, 130, 246, 0.3);
                border-radius: 10px;
                border: 2px solid transparent;
                background-clip: padding-box;
            }

            .popup::-webkit-scrollbar-thumb:hover {
                background: rgba(59, 130, 246, 0.55);
                background-clip: padding-box;
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
                min-width: 0;
                box-sizing: border-box;
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
                min-width: 0;
                box-sizing: border-box;
            }

            .ranking-item > img {
                flex-shrink: 0;
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
                flex-shrink: 0;
            }

            .rank-1 { color: #facc15; background: rgba(250, 204, 21, 0.1); border: 1px solid rgba(250, 204, 21, 0.2); }
            .rank-2 { color: #e2e8f0; background: rgba(226, 232, 240, 0.1); border: 1px solid rgba(226, 232, 240, 0.2); }
            .rank-3 { color: #ca8a04; background: rgba(202, 138, 4, 0.1); border: 1px solid rgba(202, 138, 4, 0.2); }

            .user-info {
                flex: 1;
                display: flex;
                flex-direction: column;
                min-width: 0;
            }

            .user-name {
                font-weight: 600;
                color: #f1f5f9;
                font-size: 0.95rem;
                overflow-wrap: anywhere;
                word-break: break-word;
            }

            .user-points {
                font-weight: 700;
                color: #60a5fa;
                font-size: 0.9rem;
                flex-shrink: 0;
                white-space: nowrap;
                margin-left: 0.75rem;
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
                flex-shrink: 0;
            }
            .profile-avatar:hover { transform: scale(1.05); }

            .profile-details {
                flex: 1;
                min-width: 0;
            }

            .profile-details h2 {
                margin: 0;
                font-size: 1.25rem;
                font-weight: 700;
                color: #f8fafc;
                cursor: pointer;
                overflow-wrap: anywhere;
                word-break: break-word;
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
                min-width: 0;
                box-sizing: border-box;
            }

            .mini-list-item:hover {
                border-color: #334155;
            }

            .mini-list-item > div {
                min-width: 0;
                overflow-wrap: anywhere;
                word-break: break-word;
            }

            .mini-list-item > a {
                flex-shrink: 0;
                white-space: nowrap;
            }

            .mini-img {
                width: 32px;
                height: 32px;
                border-radius: 6px;
                object-fit: cover;
                flex-shrink: 0;
            }

            .author-pager {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.75rem;
                margin-top: 0.75rem;
            }

            .author-pager:empty {
                display: none;
            }

            .author-pager-btn {
                background: rgba(30, 41, 59, 0.6);
                border: 1px solid #334155;
                color: #cbd5e1;
                border-radius: 8px;
                min-width: 2rem;
                height: 2rem;
                padding: 0 0.6rem;
                cursor: pointer;
                font-size: 0.95rem;
                line-height: 1;
                transition: all 0.15s ease;
            }

            .author-pager-btn:hover:not(:disabled) {
                background: rgba(59, 130, 246, 0.15);
                border-color: #3b82f6;
                color: #f1f5f9;
            }

            .author-pager-btn:disabled {
                opacity: 0.4;
                cursor: default;
            }

            .author-pager-info {
                font-size: 0.8rem;
                color: #94a3b8;
                font-weight: 600;
                min-width: 3.5rem;
                text-align: center;
            }

            /* Solo la lista del ranking hace scroll (queda acotada); así el
               paginador siempre es visible justo debajo, sin que ningún ítem
               asome por debajo de él. */
            #ranking-ul {
                max-height: max(140px, calc(85vh - 340px));
                overflow-y: auto;
                scrollbar-width: thin;
                scrollbar-color: rgba(59, 130, 246, 0.35) transparent;
            }

            #ranking-pager {
                padding-top: 0.75rem;
                border-top: 1px solid rgba(148, 163, 184, 0.12);
            }
            /* Ayuda de la clasificación («?» junto al título) */
            .ranking-search-container[hidden], #ranking-list-container[hidden], .rk-ayuda[hidden] { display: none !important; }
            .rk-titulo-fila { display: flex; align-items: center; justify-content: center; gap: 0.55rem; }
            .rk-ayuda-btn {
                display: inline-grid; place-items: center; flex: 0 0 auto; width: 30px; height: 30px; padding: 0;
                border: 1px solid rgba(148, 163, 184, 0.6); border-radius: 50%;
                background: rgba(255, 255, 255, 0.07); color: #e2e8f0; font: 700 0.95rem/1 inherit; cursor: pointer;
                transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
            }
            .rk-ayuda-btn:hover { background: rgba(59, 130, 246, 0.3); border-color: #93c5fd; color: #fff; }
            .rk-ayuda-btn:focus-visible, .rk-volver:focus-visible, .rk-ayuda a:focus-visible { outline: 3px solid #93c5fd; outline-offset: 2px; }
            .rk-ayuda-btn[aria-expanded="true"] { background: #1d4ed8; border-color: #1d4ed8; color: #fff; }
            @media (pointer: coarse) { .rk-ayuda-btn { width: 40px; height: 40px; } }

            .rk-ayuda {
                text-align: left; font-size: 0.9rem; line-height: 1.55; color: #cbd5e1;
                max-height: max(180px, calc(85vh - 190px)); overflow-y: auto; padding-right: 0.25rem;
                scrollbar-width: thin; scrollbar-color: rgba(59, 130, 246, 0.35) transparent;
            }
            .rk-ayuda h2 { margin: 0 0 0.6rem; font-size: 1rem; color: #fff; outline: none; }
            .rk-ayuda h3 { margin: 1rem 0 0.45rem; font-size: 0.74rem; letter-spacing: 0.07em; text-transform: uppercase; color: #94a3b8; }
            .rk-ayuda p { margin: 0 0 0.5rem; }
            .rk-ayuda a { color: #7dd3fc; text-underline-offset: 3px; }
            .rk-ayuda strong { color: #fff; }
            .rk-puntos { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.4rem; margin: 0.6rem 0 0; padding: 0; list-style: none; }
            .rk-puntos li { display: flex; align-items: center; justify-content: space-between; padding: 0.45rem 0.75rem; border: 1px solid rgba(148, 163, 184, 0.28); border-radius: 10px; background: rgba(255, 255, 255, 0.04); cursor: default; }
            .rk-puntos b { color: #4ade80; }
            .rk-pasos { margin: 0; padding-left: 1.75rem; }
            .rk-pasos li { margin: 0.4rem 0; }
            .rk-nota { margin: 0.8rem 0 0; font-size: 0.8rem; color: #a3b1c6; }
            .rk-tuyo { margin-top: 1rem; padding: 0.8rem 0.95rem; border: 1px solid rgba(96, 165, 250, 0.5); border-radius: 12px; background: rgba(59, 130, 246, 0.1); }
            .rk-tuyo h3 { margin-top: 0; color: #bfdbfe; }
            .rk-tuyo ul { margin: 0.35rem 0 0; padding-left: 1.15rem; }
            .rk-tuyo li { margin: 0.25rem 0; cursor: default; }
            .rk-volver { width: 100%; min-height: 42px; margin-top: 1rem; border: 1px solid rgba(148, 163, 184, 0.6); border-radius: 10px; background: rgba(255, 255, 255, 0.07); color: #f1f5f9; font: 600 0.9rem inherit; cursor: pointer; }
            .rk-volver:hover { background: rgba(255, 255, 255, 0.14); }
            @media (max-width: 420px) { .rk-puntos { grid-template-columns: 1fr; } }
            @media (prefers-reduced-motion: reduce) { .rk-ayuda-btn { transition: none; } }
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
                box-sizing: border-box;
                text-align: left;
                font-size: 0.9rem;
                line-height: 1.6;
                color: #cbd5e1;
                white-space: pre-wrap;
                overflow-wrap: anywhere;
                word-break: break-word;
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

            // Machines List (paginada: se listan por páginas para no volcar
            // todas las máquinas de golpe cuando un autor tiene muchas).
            const MACHINES_PAGE_SIZE = 8;
            const authorMachines = Array.isArray(data.maquinas) ? data.maquinas : [];
            let authorMachinesPage = 0;

            function machineItemHtml(m) {
                return `
                        <div class="mini-list-item">
                            ${m.imagen_url ? `<img src="${escapeHtml(m.imagen_url)}" class="mini-img">` : ''}
                            <div style="flex:1;">
                                <div style="font-weight: 600; font-size: 0.9rem; color: #f1f5f9;">${escapeHtml(m.nombre)}</div>
                                <div style="font-size: 0.75rem; color: #64748b; text-transform: uppercase;">${escapeHtml(m.dificultad)}</div>
                            </div>
                        </div>
                    `;
            }

            let maquinasHtml = '<div style="margin-top: 1.5rem;"><div class="section-title">Máquinas Creadas</div>';
            if (authorMachines.length > 0) {
                maquinasHtml += '<div id="author-machines-list"></div><div id="author-machines-pager" class="author-pager"></div>';
            } else {
                maquinasHtml += '<p style="font-size: 0.85rem; color: #64748b; font-style: italic;">Sin máquinas registradas.</p>';
            }
            maquinasHtml += '</div>';

            // Writeups List (paginada, igual que las máquinas)
            const WRITEUPS_PAGE_SIZE = 8;
            const authorWriteups = Array.isArray(data.writeups) ? data.writeups : [];
            let authorWriteupsPage = 0;

            function writeupItemHtml(w) {
                return `
                        <div class="mini-list-item" style="justify-content: space-between;">
                            <div>
                                <div style="font-weight: 600; font-size: 0.9rem; color: #f1f5f9;">${escapeHtml(w.maquina)}</div>
                                <div style="font-size: 0.75rem; color: #64748b;">${escapeHtml(w.tipo || '')}</div>
                            </div>
                            <a href="${escapeHtml(w.url)}" target="_blank" style="font-size: 0.8rem; color: #3b82f6; text-decoration: none;">Ver ↗</a>
                        </div>
                     `;
            }

            let writeupsHtml = '<div style="margin-top: 1.5rem;"><div class="section-title">Writeups Enviados</div>';
            if (authorWriteups.length > 0) {
                writeupsHtml += '<div id="author-writeups-list"></div><div id="author-writeups-pager" class="author-pager"></div>';
            } else {
                writeupsHtml += '<p style="font-size: 0.85rem; color: #64748b; font-style: italic;">Sin writeups enviados.</p>';
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

            // Render paginado de las máquinas creadas
            function renderAuthorMachinesPage() {
                const listEl = popupDiv.querySelector('#author-machines-list');
                const pagerEl = popupDiv.querySelector('#author-machines-pager');
                if (!listEl) return;
                const total = authorMachines.length;
                const pages = Math.max(1, Math.ceil(total / MACHINES_PAGE_SIZE));
                if (authorMachinesPage < 0) authorMachinesPage = 0;
                if (authorMachinesPage > pages - 1) authorMachinesPage = pages - 1;
                const start = authorMachinesPage * MACHINES_PAGE_SIZE;
                listEl.innerHTML = authorMachines
                    .slice(start, start + MACHINES_PAGE_SIZE)
                    .map(machineItemHtml)
                    .join('');
                if (!pagerEl) return;
                if (pages > 1) {
                    pagerEl.innerHTML =
                        '<button class="author-pager-btn" data-dir="prev"' + (authorMachinesPage === 0 ? ' disabled' : '') + '>←</button>' +
                        '<span class="author-pager-info">' + (authorMachinesPage + 1) + ' / ' + pages + '</span>' +
                        '<button class="author-pager-btn" data-dir="next"' + (authorMachinesPage >= pages - 1 ? ' disabled' : '') + '>→</button>';
                    const prevBtn = pagerEl.querySelector('[data-dir="prev"]');
                    const nextBtn = pagerEl.querySelector('[data-dir="next"]');
                    if (prevBtn) prevBtn.onclick = () => { authorMachinesPage--; renderAuthorMachinesPage(); };
                    if (nextBtn) nextBtn.onclick = () => { authorMachinesPage++; renderAuthorMachinesPage(); };
                } else {
                    pagerEl.innerHTML = '';
                }
            }
            renderAuthorMachinesPage();

            // Render paginado de los writeups enviados
            function renderAuthorWriteupsPage() {
                const listEl = popupDiv.querySelector('#author-writeups-list');
                const pagerEl = popupDiv.querySelector('#author-writeups-pager');
                if (!listEl) return;
                const total = authorWriteups.length;
                const pages = Math.max(1, Math.ceil(total / WRITEUPS_PAGE_SIZE));
                if (authorWriteupsPage < 0) authorWriteupsPage = 0;
                if (authorWriteupsPage > pages - 1) authorWriteupsPage = pages - 1;
                const start = authorWriteupsPage * WRITEUPS_PAGE_SIZE;
                listEl.innerHTML = authorWriteups
                    .slice(start, start + WRITEUPS_PAGE_SIZE)
                    .map(writeupItemHtml)
                    .join('');
                if (!pagerEl) return;
                if (pages > 1) {
                    pagerEl.innerHTML =
                        '<button class="author-pager-btn" data-dir="prev"' + (authorWriteupsPage === 0 ? ' disabled' : '') + '>←</button>' +
                        '<span class="author-pager-info">' + (authorWriteupsPage + 1) + ' / ' + pages + '</span>' +
                        '<button class="author-pager-btn" data-dir="next"' + (authorWriteupsPage >= pages - 1 ? ' disabled' : '') + '>→</button>';
                    const prevBtn = pagerEl.querySelector('[data-dir="prev"]');
                    const nextBtn = pagerEl.querySelector('[data-dir="next"]');
                    if (prevBtn) prevBtn.onclick = () => { authorWriteupsPage--; renderAuthorWriteupsPage(); };
                    if (nextBtn) nextBtn.onclick = () => { authorWriteupsPage++; renderAuthorWriteupsPage(); };
                } else {
                    pagerEl.innerHTML = '';
                }
            }
            renderAuthorWriteupsPage();

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


/* ───────────────────────────────────────────────────────────────────────────
   Ayuda de las clasificaciones: icono «?» junto al título.
   Cambia el modal a una vista de ayuda con las reglas reales de puntos, los
   pasos para subir puestos y un bloque personalizado (tu puesto y a cuál te
   llevaría tu siguiente writeup / máquina), calculado con los datos del propio
   ranking y con el mismo desempate (alfabético) que el servidor.
   ─────────────────────────────────────────────────────────────────────────── */
function rkNombre(item, tipo) { return String((tipo === 'writeups' ? item.nombre : item.autor) || ''); }
function rkValor(item, tipo) { return Number(tipo === 'writeups' ? item.puntos : item.maquinas) || 0; }
function rkPlural(n, uno, varios) { return n + ' ' + (n === 1 ? uno : varios); }

/* Puesto que tendría `usuario` si su marcador pasara a `valor`. */
function rkPuestoCon(data, tipo, usuario, valor) {
    const u = usuario.toLowerCase();
    let puesto = 1;
    data.forEach(function (it) {
        const n = rkNombre(it, tipo).toLowerCase();
        if (n === u) return;
        const v = rkValor(it, tipo);
        if (v > valor || (v === valor && n < u)) puesto++;
    });
    return puesto;
}

const RK_HTML_WRITEUPS =
    '<p>Aquí puntúa quien comparte sus soluciones. <strong>Cada writeup publicado suma puntos</strong> según la dificultad de la máquina:</p>' +
    '<ul class="rk-puntos">' +
    '<li><span>Muy fácil</span><b>+1</b></li><li><span>Fácil</span><b>+2</b></li>' +
    '<li><span>Medio</span><b>+3</b></li><li><span>Difícil</span><b>+4</b></li></ul>' +
    '<h3>Cómo subir puestos</h3>' +
    '<ol class="rk-pasos">' +
    '<li><strong>Resuelve una máquina</strong> de DockerLabs.</li>' +
    '<li><strong>Sube tu writeup</strong> con el botón de subir (<i class="bi bi-upload" aria-hidden="true"></i> «Subir writeup») de su tarjeta. Tienes que haber iniciado sesión.</li>' +
    '<li><strong>El equipo lo revisa.</strong> Cuando se aprueba y se publica, se suman tus puntos y la clasificación se actualiza.</li></ol>' +
    '<p class="rk-nota">Da igual que sea texto o vídeo: lo que cuenta es la dificultad de la máquina. En caso de empate, se ordena alfabéticamente.</p>';

const RK_HTML_AUTORES =
    '<p>Aquí puntúa quien crea máquinas. <strong>Cada máquina publicada en DockerLabs suma 1</strong> a su autor (las de BunkerLabs no cuentan).</p>' +
    '<h3>Cómo subir puestos</h3>' +
    '<ol class="rk-pasos">' +
    '<li><strong>Crea tu máquina.</strong> Si no sabes por dónde empezar, mira <a href="/enviar-maquina">Crear y enviar una máquina</a>.</li>' +
    '<li><strong>Envíala</strong> desde el formulario de <a href="/enviar-maquina#enviar">esa misma página</a>.</li>' +
    '<li><strong>El equipo la revisa.</strong> Cuando se aprueba y se publica en DockerLabs, sumas una máquina y subes en la clasificación.</li></ol>' +
    '<p class="rk-nota">En caso de empate, se ordena alfabéticamente.</p>';

function rkMontarAyuda(popupDiv, closeButton, tipo, cerrarModal) {
    const esWriteups = tipo === 'writeups';
    const previo = document.activeElement;
    let data = null;
    const q = function (sel) { return popupDiv.querySelector(sel); };   // siempre se vuelve a buscar: el .catch del modal reescribe el HTML

    // El modal pasa a ser un diálogo accesible: nombre, rol y cierre por teclado.
    popupDiv.setAttribute('role', 'dialog');
    popupDiv.setAttribute('aria-modal', 'true');
    const titulo = q('.modal-title');
    if (titulo) { titulo.id = 'rk-titulo'; popupDiv.setAttribute('aria-labelledby', 'rk-titulo'); }
    closeButton.type = 'button';
    closeButton.setAttribute('aria-label', 'Cerrar clasificación');

    const panel = document.createElement('div');
    panel.id = 'rk-ayuda-panel';
    panel.className = 'rk-ayuda';
    panel.hidden = true;
    panel.setAttribute('role', 'region');
    panel.setAttribute('aria-label', 'Cómo funciona la clasificación');
    const buscador = q('.ranking-search-container');
    buscador.parentNode.insertBefore(panel, buscador);

    function abierta() { const b = q('.rk-ayuda-btn'); return !!b && b.getAttribute('aria-expanded') === 'true'; }

    function parrafo(html) { const p = document.createElement('p'); p.className = 'rk-tuyo-linea'; p.innerHTML = html; return p; }
    function esc(t) { return String(t).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

    /* Bloque «tu situación»: solo con datos reales; nunca promete nada que no se pueda calcular. */
    function personal() {
        const caja = document.createElement('div');
        caja.className = 'rk-tuyo';
        const titulo = document.createElement('h3');
        titulo.textContent = 'Tu situación';
        caja.append(titulo);
        const usuario = (typeof currentUser !== 'undefined' ? String(currentUser || '') : '').trim();
        if (!usuario) {
            caja.append(parrafo('<a href="/login">Inicia sesión</a> para ver tu puesto y a cuál subirías con tu próximo ' + (esWriteups ? 'writeup' : 'envío') + '.'));
            return caja;
        }
        if (!data) { caja.append(parrafo('Calculando tu posición…')); return caja; }

        const idx = data.findIndex(function (it) { return rkNombre(it, tipo).toLowerCase() === usuario.toLowerCase(); });
        const mio = idx >= 0 ? rkValor(data[idx], tipo) : 0;
        const puesto = idx + 1;

        if (esWriteups) {
            if (idx >= 0) {
                caja.append(parrafo('Estás en el puesto <strong>#' + puesto + '</strong> con <strong>' + rkPlural(mio, 'punto', 'puntos') + '</strong>.'));
                if (puesto > 1) {
                    const sup = data[puesto - 2], falta = rkValor(sup, tipo) - mio;
                    if (falta > 0) caja.append(parrafo('Te ' + (falta === 1 ? 'falta ' : 'faltan ') + '<strong>' + rkPlural(falta, 'punto', 'puntos') + '</strong> para alcanzar a ' + esc(rkNombre(sup, tipo)) + '.'));
                } else {
                    caja.append(parrafo('¡Vas primero! Mantén la ventaja subiendo más writeups.'));
                }
            } else {
                caja.append(parrafo('Todavía no estás en la clasificación. Tu primer writeup publicado te haría entrar.'));
            }
            const ul = document.createElement('ul');
            [[4, 'una máquina difícil'], [2, 'una fácil']].forEach(function (par) {
                const nuevo = rkPuestoCon(data, tipo, usuario, mio + par[0]);
                const base = 'Un writeup de ' + par[1] + ' (<strong>+' + par[0] + '</strong>) ';
                const li = document.createElement('li');
                if (idx < 0 || nuevo < puesto) {
                    li.innerHTML = base + 'te llevaría al puesto <strong>#' + nuevo + '</strong>.';
                } else {
                    // No cambia de puesto: se dice cuánto falta para alcanzar al siguiente, que es lo útil.
                    const sup = puesto > 1 ? data[puesto - 2] : null;
                    const resto = sup ? rkValor(sup, tipo) - (mio + par[0]) : 0;
                    li.innerHTML = resto > 0
                        ? base + 'te acercaría: te quedarían <strong>' + rkPlural(resto, 'punto', 'puntos') + '</strong> para alcanzar a ' + esc(rkNombre(sup, tipo)) + '.'
                        : base + 'te mantendría en el puesto <strong>#' + nuevo + '</strong> con más ventaja.';
                }
                ul.append(li);
            });
            caja.append(ul);
        } else {
            if (idx >= 0) {
                caja.append(parrafo('Estás en el puesto <strong>#' + puesto + '</strong> con <strong>' + rkPlural(mio, 'máquina', 'máquinas') + '</strong>.'));
                const nuevo = rkPuestoCon(data, tipo, usuario, mio + 1);
                caja.append(parrafo(nuevo < puesto
                    ? 'Con una máquina más subirías al puesto <strong>#' + nuevo + '</strong>.'
                    : 'Con una máquina más seguirías en el puesto <strong>#' + nuevo + '</strong>, pero sumarías ventaja.'));
            } else {
                const nuevo = rkPuestoCon(data, tipo, usuario, 1);
                caja.append(parrafo('Todavía no estás en la clasificación. Tu primera máquina publicada te haría entrar en el puesto <strong>#' + nuevo + '</strong>.'));
            }
        }
        return caja;
    }

    function pintar() {
        const p = q('#rk-ayuda-panel');
        if (!p) return;
        p.replaceChildren();
        const h = document.createElement('h2');
        h.tabIndex = -1;
        h.textContent = '¿Cómo funciona esta clasificación?';
        const cuerpo = document.createElement('div');
        cuerpo.innerHTML = esWriteups ? RK_HTML_WRITEUPS : RK_HTML_AUTORES;
        const volver = document.createElement('button');
        volver.type = 'button';
        volver.className = 'rk-volver';
        volver.textContent = 'Volver a la clasificación';
        p.append(h, cuerpo, personal(), volver);
    }

    function alternar(forzar) {
        const abrir = typeof forzar === 'boolean' ? forzar : !abierta();
        const boton = q('.rk-ayuda-btn'), p = q('#rk-ayuda-panel');
        if (!boton || !p) return;
        boton.setAttribute('aria-expanded', abrir ? 'true' : 'false');
        p.hidden = !abrir;
        [q('.ranking-search-container'), q('#ranking-list-container')].forEach(function (el) { if (el) el.hidden = abrir; });
        if (abrir) { pintar(); const h = p.querySelector('h2'); if (h) h.focus(); }
        else boton.focus();
    }

    // Delegación: el botón sobrevive aunque el modal reescriba su HTML.
    popupDiv.addEventListener('click', function (e) {
        if (e.target.closest('.rk-ayuda-btn')) alternar();
        else if (e.target.closest('.rk-volver')) alternar(false);
    });

    function alTeclear(e) {
        if (e.key !== 'Escape') return;
        e.stopPropagation();
        if (abierta()) alternar(false); else cerrarModal();
    }
    document.addEventListener('keydown', alTeclear);
    setTimeout(function () { closeButton.focus({ preventScroll: true }); }, 60);

    return {
        setData: function (d) { data = d; if (abierta()) pintar(); },
        destruir: function () {
            document.removeEventListener('keydown', alTeclear);
            if (previo && previo.isConnected && previo.focus) previo.focus({ preventScroll: true });
        },
    };
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
            <div class="rk-titulo-fila">
                <h1 class="modal-title">Clasificación</h1>
                <button type="button" class="rk-ayuda-btn" aria-expanded="false" aria-controls="rk-ayuda-panel"
                        aria-label="¿Cómo funciona esta clasificación?" title="¿Cómo funciona?"><span aria-hidden="true">?</span></button>
            </div>
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
    const rkAyuda = rkMontarAyuda(popupDiv, closeButton, 'writeups', () => closePopup());

    fetch('/api/ranking_writeups')
        .then(res => {
            if (!res.ok) throw new Error('Error API');
            return res.json();
        })
        .then(data => {
            data.sort((a, b) => b.puntos - a.puntos);
            rkAyuda.setData(data);
            // Posición global precalculada: no cambia al filtrar ni paginar.
            data.forEach((item, i) => { item._rank = i + 1; });

            const RANK_PAGE_SIZE = 10;
            let rankPage = 0;
            let rankTerm = '';

            const listContainer = popupDiv.querySelector('#ranking-list-container');
            listContainer.innerHTML = '<ul class="ranking-list" id="ranking-ul"></ul><div id="ranking-pager" class="author-pager"></div>';
            const ul = listContainer.querySelector('#ranking-ul');
            const pagerEl = listContainer.querySelector('#ranking-pager');

            function badgeFor(rank) {
                if (rank === 1) return { cls: 'rank-badge rank-1', icon: '🥇' };
                if (rank === 2) return { cls: 'rank-badge rank-2', icon: '🥈' };
                if (rank === 3) return { cls: 'rank-badge rank-3', icon: '🥉' };
                return { cls: 'rank-badge', icon: '#' + rank };
            }

            function render() {
                const filtered = rankTerm
                    ? data.filter(it => (it.nombre || '').toLowerCase().includes(rankTerm))
                    : data;
                const pages = Math.max(1, Math.ceil(filtered.length / RANK_PAGE_SIZE));
                if (rankPage > pages - 1) rankPage = pages - 1;
                if (rankPage < 0) rankPage = 0;
                const start = rankPage * RANK_PAGE_SIZE;
                const slice = filtered.slice(start, start + RANK_PAGE_SIZE);

                ul.innerHTML = '';
                if (slice.length === 0) {
                    const li = document.createElement('li');
                    li.style.cssText = 'justify-content:center; color:#64748b; cursor:default;';
                    li.textContent = 'Sin resultados.';
                    ul.appendChild(li);
                } else {
                    slice.forEach(item => {
                        const b = badgeFor(item._rank);
                        const li = document.createElement('li');
                        li.className = 'ranking-item';
                        li.innerHTML = `
                    <div class="${b.cls}">${b.icon}</div>
                     ${item.imagen_url ? `<img src="${escapeHtml(item.imagen_url)}" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover; margin-right: 12px;">` : ''}
                    <div class="user-info">
                        <span class="user-name">${escapeHtml(item.nombre)}</span>
                    </div>
                    <div class="user-points">${item.puntos} pts</div>
                `;
                        li.onclick = () => openAuthorProfileModal(item.nombre);
                        ul.appendChild(li);
                    });
                }

                if (pages > 1) {
                    pagerEl.innerHTML =
                        '<button class="author-pager-btn" data-dir="prev"' + (rankPage === 0 ? ' disabled' : '') + '>←</button>' +
                        '<span class="author-pager-info">' + (rankPage + 1) + ' / ' + pages + '</span>' +
                        '<button class="author-pager-btn" data-dir="next"' + (rankPage >= pages - 1 ? ' disabled' : '') + '>→</button>';
                    const prevBtn = pagerEl.querySelector('[data-dir="prev"]');
                    const nextBtn = pagerEl.querySelector('[data-dir="next"]');
                    if (prevBtn) prevBtn.onclick = () => { rankPage--; render(); };
                    if (nextBtn) nextBtn.onclick = () => { rankPage++; render(); };
                } else {
                    pagerEl.innerHTML = '';
                }
            }

            const searchInput = popupDiv.querySelector('#rankingSearchInput');
            searchInput.oninput = () => { rankTerm = searchInput.value.toLowerCase(); rankPage = 0; render(); };

            render();

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
        rkAyuda.destruir();
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
            <div class="rk-titulo-fila">
                <h1 class="modal-title">Clasificación Autores</h1>
                <button type="button" class="rk-ayuda-btn" aria-expanded="false" aria-controls="rk-ayuda-panel"
                        aria-label="¿Cómo funciona esta clasificación?" title="¿Cómo funciona?"><span aria-hidden="true">?</span></button>
            </div>
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
    const rkAyuda = rkMontarAyuda(popupDiv, closeButton, 'autores', () => closePopup());

    fetch('/api/ranking_autores')
        .then(res => {
            if (!res.ok) throw new Error('Error API');
            return res.json();
        })
        .then(data => {
            // Sort by machines count (descending)
            data.sort((a, b) => b.maquinas - a.maquinas);
            rkAyuda.setData(data);
            // Posición global precalculada: no cambia al filtrar ni paginar.
            data.forEach((item, i) => { item._rank = i + 1; });

            const RANK_PAGE_SIZE = 10;
            let rankPage = 0;
            let rankTerm = '';

            const listContainer = popupDiv.querySelector('#ranking-list-container');
            listContainer.innerHTML = '<ul class="ranking-list" id="ranking-ul"></ul><div id="ranking-pager" class="author-pager"></div>';
            const ul = listContainer.querySelector('#ranking-ul');
            const pagerEl = listContainer.querySelector('#ranking-pager');

            function badgeFor(rank) {
                if (rank === 1) return { cls: 'rank-badge rank-1', icon: '🥇' };
                if (rank === 2) return { cls: 'rank-badge rank-2', icon: '🥈' };
                if (rank === 3) return { cls: 'rank-badge rank-3', icon: '🥉' };
                return { cls: 'rank-badge', icon: '#' + rank };
            }

            function render() {
                const filtered = rankTerm
                    ? data.filter(it => (it.autor || '').toLowerCase().includes(rankTerm))
                    : data;
                const pages = Math.max(1, Math.ceil(filtered.length / RANK_PAGE_SIZE));
                if (rankPage > pages - 1) rankPage = pages - 1;
                if (rankPage < 0) rankPage = 0;
                const start = rankPage * RANK_PAGE_SIZE;
                const slice = filtered.slice(start, start + RANK_PAGE_SIZE);

                ul.innerHTML = '';
                if (slice.length === 0) {
                    const li = document.createElement('li');
                    li.style.cssText = 'justify-content:center; color:#64748b; cursor:default;';
                    li.textContent = 'Sin resultados.';
                    ul.appendChild(li);
                } else {
                    slice.forEach(item => {
                        const b = badgeFor(item._rank);
                        const li = document.createElement('li');
                        li.className = 'ranking-item';
                        li.innerHTML = `
                    <div class="${b.cls}">${b.icon}</div>
                     ${item.imagen ? `<img src="${escapeHtml(item.imagen)}" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover; margin-right: 12px;">` : ''}
                    <div class="user-info">
                        <span class="user-name">${escapeHtml(item.autor)}</span>
                    </div>
                    <div class="user-points" style="color: #22d3ee;">${item.maquinas} máq.</div>
                `;
                        li.onclick = () => openAuthorProfileModal(item.autor);
                        ul.appendChild(li);
                    });
                }

                if (pages > 1) {
                    pagerEl.innerHTML =
                        '<button class="author-pager-btn" data-dir="prev"' + (rankPage === 0 ? ' disabled' : '') + '>←</button>' +
                        '<span class="author-pager-info">' + (rankPage + 1) + ' / ' + pages + '</span>' +
                        '<button class="author-pager-btn" data-dir="next"' + (rankPage >= pages - 1 ? ' disabled' : '') + '>→</button>';
                    const prevBtn = pagerEl.querySelector('[data-dir="prev"]');
                    const nextBtn = pagerEl.querySelector('[data-dir="next"]');
                    if (prevBtn) prevBtn.onclick = () => { rankPage--; render(); };
                    if (nextBtn) nextBtn.onclick = () => { rankPage++; render(); };
                } else {
                    pagerEl.innerHTML = '';
                }
            }

            const searchInput = popupDiv.querySelector('#rankingAutoresSearchInput');
            searchInput.oninput = () => { rankTerm = searchInput.value.toLowerCase(); rankPage = 0; render(); };

            render();

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
        rkAyuda.destruir();
        popupDiv.classList.remove('visible');
        overlayDiv.classList.remove('visible');
        setTimeout(() => {
            if (popupDiv.parentNode) document.body.removeChild(popupDiv);
            if (overlayDiv.parentNode) document.body.removeChild(overlayDiv);
        }, 300);
    }
}
