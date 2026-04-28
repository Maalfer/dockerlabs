// Sistema de Equipos - JavaScript Frontend

let currentTeam = null;
let teamInvitations = [];
let teamJoinRequests = [];

// Inject equipos styles
function injectEquiposStyles() {
    // First inject ranking styles if not present (for base modal styles)
    if (!document.getElementById('minimal-ranking-styles-v2')) {
        const style = document.createElement('style');
        style.id = 'minimal-ranking-styles-v2';
        style.textContent = `
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
                pointer-events: none;
                transition: opacity 0.2s ease;
            }

            .overlay.visible {
                opacity: 1;
                pointer-events: auto;
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
                pointer-events: none;
                font-family: 'Fira Code', monospace;
                transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            }

            .popup.visible {
                opacity: 1;
                transform: translate(-50%, -50%) scale(1);
                pointer-events: auto;
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
        `;
        document.head.appendChild(style);
    }

    // Now inject team-specific styles
    const styleId = 'equipos-styles';
    if (!document.getElementById(styleId)) {
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            /* Team-specific styles */
            .team-avatar {
                width: 48px;
                height: 48px;
                border-radius: 12px;
                object-fit: cover;
                border: 2px solid #3b82f6;
            }

            .team-avatar-small {
                width: 32px;
                height: 32px;
                border-radius: 8px;
                object-fit: cover;
                border: 1px solid #334155;
            }

            .team-member-avatar {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                object-fit: cover;
                border: 2px solid #3b82f6;
            }

            .team-actions {
                display: flex;
                gap: 0.5rem;
                margin-top: 1rem;
            }

            .team-btn {
                padding: 0.5rem 1rem;
                border: none;
                border-radius: 8px;
                font-family: 'Fira Code', monospace;
                font-size: 0.85rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }

            .team-btn-primary {
                background: #3b82f6;
                color: white;
            }

            .team-btn-primary:hover {
                background: #2563eb;
                transform: translateY(-1px);
            }

            .team-btn-secondary {
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
            }

            .team-btn-secondary:hover {
                background: #334155;
                color: #f1f5f9;
            }

            .team-btn-danger {
                background: #ef4444;
                color: white;
            }

            .team-btn-danger:hover {
                background: #dc2626;
            }

            .team-input {
                width: 100%;
                padding: 0.75rem 1rem;
                background: rgba(15, 23, 42, 0.5);
                border: 1px solid #334155;
                border-radius: 8px;
                color: #f1f5f9;
                font-family: 'Fira Code', monospace;
                font-size: 0.9rem;
                margin-bottom: 1rem;
            }

            .team-input:focus {
                outline: none;
                border-color: #3b82f6;
            }

            .team-file-input {
                display: none;
            }

            .team-file-label {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
                padding: 0.75rem 1rem;
                background: rgba(15, 23, 42, 0.5);
                border: 2px dashed #334155;
                border-radius: 8px;
                color: #94a3b8;
                cursor: pointer;
                transition: all 0.2s;
                margin-bottom: 1rem;
            }

            .team-file-label:hover {
                border-color: #3b82f6;
                color: #3b82f6;
            }

            .team-file-label.has-file {
                border-color: #22d3ee;
                color: #22d3ee;
                border-style: solid;
            }

            .team-preview-container {
                display: flex;
                justify-content: center;
                margin-bottom: 1rem;
            }

            .team-preview-image {
                max-width: 200px;
                max-height: 200px;
                border-radius: 12px;
                object-fit: cover;
            }

            .invitation-item {
                display: flex;
                align-items: center;
                gap: 1rem;
                padding: 1rem;
                background: rgba(30, 41, 59, 0.4);
                border: 1px solid rgba(148, 163, 184, 0.1);
                border-radius: 12px;
                margin-bottom: 0.75rem;
            }

            .invitation-info {
                flex: 1;
            }

            .invitation-team-name {
                font-weight: 600;
                color: #f1f5f9;
                margin-bottom: 0.25rem;
            }

            .invitation-meta {
                font-size: 0.8rem;
                color: #64748b;
            }

            .invitation-actions {
                display: flex;
                gap: 0.5rem;
            }

            .team-list-item {
                display: flex;
                align-items: center;
                gap: 1rem;
                padding: 0.875rem 1rem;
                background: rgba(30, 41, 59, 0.4);
                border: 1px solid rgba(148, 163, 184, 0.1);
                border-radius: 12px;
                margin-bottom: 0.5rem;
                cursor: pointer;
                transition: all 0.2s;
            }

            .team-list-item:hover {
                background: rgba(30, 41, 59, 0.8);
                border-color: #334155;
                transform: translateY(-1px);
            }

            .team-list-item.full {
                opacity: 0.5;
                cursor: not-allowed;
            }

            .team-members-count {
                font-size: 0.75rem;
                color: #64748b;
                background: rgba(15, 23, 42, 0.5);
                padding: 0.25rem 0.5rem;
                border-radius: 4px;
            }

            .member-item {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                padding: 0.75rem;
                background: rgba(30, 41, 59, 0.4);
                border: 1px solid rgba(148, 163, 184, 0.1);
                border-radius: 10px;
                margin-bottom: 0.5rem;
            }

            .member-info {
                flex: 1;
            }

            .member-name {
                font-weight: 600;
                color: #f1f5f9;
                font-size: 0.9rem;
            }

            .member-puntos {
                font-size: 0.75rem;
                color: #60a5fa;
            }

            .member-remove-btn {
                background: transparent;
                border: none;
                color: #ef4444;
                cursor: pointer;
                padding: 0.25rem;
                font-size: 1rem;
                opacity: 0.7;
                transition: opacity 0.2s;
            }

            .member-remove-btn:hover {
                opacity: 1;
            }

            .empty-state {
                text-align: center;
                padding: 3rem 2rem;
                color: #64748b;
            }

            .empty-state-icon {
                font-size: 4rem;
                margin-bottom: 1rem;
                color: #334155;
            }

            .empty-state-title {
                font-size: 1.25rem;
                color: #94a3b8;
                margin-bottom: 0.5rem;
            }

            .tabs-container {
                display: flex;
                gap: 0.5rem;
                margin-bottom: 1.5rem;
                border-bottom: 1px solid #334155;
                padding-bottom: 0.75rem;
            }

            .tab-btn {
                padding: 0.5rem 1rem;
                background: transparent;
                border: none;
                color: #64748b;
                font-family: 'Fira Code', monospace;
                font-size: 0.85rem;
                font-weight: 600;
                cursor: pointer;
                border-radius: 6px;
                transition: all 0.2s;
            }

            .tab-btn:hover {
                color: #94a3b8;
                background: rgba(30, 41, 59, 0.5);
            }

            .tab-btn.active {
                color: #3b82f6;
                background: rgba(59, 130, 246, 0.15);
            }

            .plus-btn {
                position: absolute;
                top: 1.25rem;
                right: 3.5rem;
                background: rgba(59, 130, 246, 0.15);
                border: 1px solid rgba(59, 130, 246, 0.3);
                color: #3b82f6;
                width: 36px;
                height: 36px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                font-size: 1.25rem;
                transition: all 0.2s;
                z-index: 10;
            }

            .plus-btn:hover {
                background: rgba(59, 130, 246, 0.25);
                border-color: #3b82f6;
                transform: scale(1.05);
            }

            .plus-dropdown {
                position: absolute;
                top: 3.5rem;
                right: 3.5rem;
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 0.5rem;
                min-width: 180px;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
                z-index: 10000;
                display: none;
            }

            .plus-dropdown.show {
                display: block;
            }

            .plus-dropdown-item {
                padding: 0.75rem 1rem;
                cursor: pointer;
                border-radius: 6px;
                display: flex;
                align-items: center;
                gap: 0.75rem;
                color: #f1f5f9;
                font-size: 0.9rem;
                font-family: 'Fira Code', monospace;
                transition: background 0.2s;
            }

            .plus-dropdown-item:hover {
                background: rgba(59, 130, 246, 0.15);
            }

            .plus-dropdown-item i {
                color: #3b82f6;
            }

            .search-results {
                max-height: 200px;
                overflow-y: auto;
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 0.5rem;
                background: rgba(15, 23, 42, 0.8);
            }

            .search-result-item {
                padding: 0.75rem 1rem;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 0.75rem;
                transition: background 0.2s;
            }

            .search-result-item:hover {
                background: rgba(30, 41, 59, 0.8);
            }

            .plus-menu {
                position: absolute;
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
                padding: 0.5rem;
                min-width: 180px;
                z-index: 10000;
            }

            .plus-menu-item {
                padding: 0.75rem 1rem;
                cursor: pointer;
                border-radius: 6px;
                display: flex;
                align-items: center;
                gap: 0.75rem;
                color: #f1f5f9;
                font-size: 0.9rem;
                transition: background 0.2s;
            }

            .plus-menu-item:hover {
                background: rgba(59, 130, 246, 0.15);
            }
        `;
        document.head.appendChild(style);
    }
}

// ==================== HELPER FUNCTIONS ====================

function createModalElements(width = 'min(480px, 95vw)') {
    const overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay';
    overlayDiv.style.position = 'fixed';
    overlayDiv.style.top = '0';
    overlayDiv.style.left = '0';
    overlayDiv.style.width = '100%';
    overlayDiv.style.height = '100%';
    overlayDiv.style.background = 'rgba(15, 23, 42, 0.6)';
    overlayDiv.style.backdropFilter = 'blur(12px)';
    overlayDiv.style.zIndex = '9998';
    overlayDiv.style.opacity = '0';
    overlayDiv.style.pointerEvents = 'none';
    overlayDiv.style.transition = 'opacity 0.2s ease';

    const popupDiv = document.createElement('div');
    popupDiv.className = 'popup';
    popupDiv.style.width = width;
    popupDiv.style.position = 'fixed';
    popupDiv.style.top = '50%';
    popupDiv.style.left = '50%';
    popupDiv.style.transform = 'translate(-50%, -48%) scale(0.96)';
    popupDiv.style.zIndex = '9999';
    popupDiv.style.background = '#1e293b';
    popupDiv.style.color = '#f1f5f9';
    popupDiv.style.border = '1px solid rgba(148, 163, 184, 0.1)';
    popupDiv.style.borderRadius = '16px';
    popupDiv.style.boxShadow = '0 25px 50px -12px rgba(0, 0, 0, 0.5)';
    popupDiv.style.padding = '2rem';
    popupDiv.style.maxHeight = '85vh';
    popupDiv.style.overflowY = 'auto';
    popupDiv.style.opacity = '0';
    popupDiv.style.pointerEvents = 'none';
    popupDiv.style.fontFamily = "'Fira Code', monospace";
    popupDiv.style.transition = 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)';

    return { overlayDiv, popupDiv };
}

function showModal(overlayDiv, popupDiv) {
    setTimeout(() => {
        overlayDiv.style.opacity = '1';
        overlayDiv.style.pointerEvents = 'auto';
        popupDiv.style.opacity = '1';
        popupDiv.style.transform = 'translate(-50%, -50%) scale(1)';
        popupDiv.style.pointerEvents = 'auto';
    }, 10);
}

function hideModal(overlayDiv, popupDiv, callback) {
    overlayDiv.style.opacity = '0';
    overlayDiv.style.pointerEvents = 'none';
    popupDiv.style.opacity = '0';
    popupDiv.style.transform = 'translate(-50%, -48%) scale(0.96)';
    popupDiv.style.pointerEvents = 'none';
    setTimeout(() => {
        if (popupDiv.parentNode) document.body.removeChild(popupDiv);
        if (overlayDiv.parentNode) document.body.removeChild(overlayDiv);
        if (callback) callback();
    }, 300);
}

// ==================== RANKING DE EQUIPOS ====================

function rankingEquipos() {
    injectEquiposStyles();

    const { overlayDiv, popupDiv } = createModalElements('min(600px, 95vw)');

    const closeButton = document.createElement('button');
    closeButton.className = 'modal-close-button';
    closeButton.innerHTML = '&times;';
    closeButton.onclick = () => hideModal(overlayDiv, popupDiv);

    popupDiv.innerHTML = `
        <div class="modal-header" style="position: relative; z-index: 1;">
            <h1 class="modal-title">Clasificación Equipos</h1>
            <div class="modal-subtitle">Ranking por puntos de writeups</div>
        </div>
        <div class="ranking-search-container" style="position: relative; z-index: 1;">
            <span style="font-size: 0.8rem; color: #64748b; font-weight: 500; display: inline-block;">Filtrar</span>
            <div class="search-wrapper">
                <input type="text" id="equiposSearchInput" class="search-input" placeholder="Buscar equipo...">
                <button class="search-icon-btn"><i class="bi bi-search"></i></button>
            </div>
        </div>
        <div id="equipos-list-container"></div>
    `;

    // Add plus button
    const plusBtn = document.createElement('button');
    plusBtn.className = 'plus-btn';
    plusBtn.innerHTML = '<i class="bi bi-plus-lg"></i>';
    plusBtn.onclick = (e) => {
        e.stopPropagation();
        const dropdown = document.getElementById('plus-dropdown-menu');
        if (dropdown) dropdown.classList.toggle('show');
    };
    plusBtn.id = 'plus-menu-btn';
    popupDiv.appendChild(plusBtn);

    // Add dropdown menu
    const dropdown = document.createElement('div');
    dropdown.className = 'plus-dropdown';
    dropdown.id = 'plus-dropdown-menu';

    const createItem = document.createElement('div');
    createItem.className = 'plus-dropdown-item';
    createItem.innerHTML = '<i class="bi bi-plus-circle"></i><span>Crear equipo</span>';
    createItem.addEventListener('click', () => { closePlusMenu(); showCrearEquipoForm(); });
    dropdown.appendChild(createItem);

    const joinItem = document.createElement('div');
    joinItem.className = 'plus-dropdown-item';
    joinItem.innerHTML = '<i class="bi bi-box-arrow-in-right"></i><span>Unirse a equipo</span>';
    joinItem.addEventListener('click', () => { closePlusMenu(); showUnirseEquipo(); });
    dropdown.appendChild(joinItem);

    const inviteItem = document.createElement('div');
    inviteItem.className = 'plus-dropdown-item';
    inviteItem.innerHTML = '<i class="bi bi-envelope"></i><span>Mis invitaciones</span>';
    inviteItem.addEventListener('click', () => { closePlusMenu(); showMisInvitaciones(); });
    dropdown.appendChild(inviteItem);

    popupDiv.appendChild(dropdown);

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        const dropdown = document.getElementById('plus-dropdown-menu');
        const plusBtn = document.getElementById('plus-menu-btn');
        if (dropdown && plusBtn && !dropdown.contains(e.target) && !plusBtn.contains(e.target)) {
            dropdown.classList.remove('show');
        }
    });

    popupDiv.appendChild(closeButton);

    // Load teams ranking
    fetch('/api/equipos/ranking')
        .then(res => {
            if (!res.ok) throw new Error('Error API');
            return res.json();
        })
        .then(data => {
            if (!data.success) throw new Error(data.message);

            const listContainer = popupDiv.querySelector('#equipos-list-container');
            const ul = document.createElement('ul');
            ul.className = 'ranking-list';

            data.equipos.forEach((team, index) => {
                const li = document.createElement('li');
                li.className = 'ranking-item';
                li.dataset.nombre = (team.nombre || '').toLowerCase();

                let badgeClass = 'rank-badge';
                let icon = '#' + (index + 1);

                if (index === 0) { badgeClass += ' rank-1'; icon = '🥇'; }
                else if (index === 1) { badgeClass += ' rank-2'; icon = '🥈'; }
                else if (index === 2) { badgeClass += ' rank-3'; icon = '🥉'; }

                li.innerHTML = `
                    <div class="${badgeClass}">${icon}</div>
                    ${team.imagen_url ? `<img src="${escapeHtml(team.imagen_url)}" class="team-avatar-small" style="margin-right: 12px;">` : ''}
                    <div class="user-info">
                        <span class="user-name">${escapeHtml(team.nombre)}</span>
                        <span style="font-size: 0.75rem; color: #64748b;">${team.member_count}/${team.max_members} miembros</span>
                    </div>
                    <div class="user-points">${team.puntos} pts</div>
                `;

                li.onclick = () => openTeamDetailModal(team.id);
                ul.appendChild(li);
            });

            listContainer.appendChild(ul);

            // Search functionality
            const searchInput = popupDiv.querySelector('#equiposSearchInput');
            searchInput.oninput = () => {
                const term = searchInput.value.toLowerCase();
                ul.querySelectorAll('li').forEach(li => {
                    const name = li.dataset.nombre;
                    li.style.display = name.includes(term) ? 'flex' : 'none';
                });
            };
        })
        .catch(err => {
            console.error(err);
            popupDiv.innerHTML += `<p style="text-align:center; color: #ef4444;">Error cargando ranking: ${err.message}</p>`;
        });

    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

    overlayDiv.onclick = (e) => { if (e.target === overlayDiv) hideModal(overlayDiv, popupDiv); };

    showModal(overlayDiv, popupDiv);
}

// ==================== MODAL PRINCIPAL DE EQUIPOS ====================

function openEquiposModal() {
    injectEquiposStyles();

    const { overlayDiv, popupDiv } = createModalElements('min(480px, 95vw)');

    const closeButton = document.createElement('button');
    closeButton.className = 'modal-close-button';
    closeButton.innerHTML = '&times;';
    closeButton.onclick = () => hideModal(overlayDiv, popupDiv);

    popupDiv.innerHTML = `
        <div class="modal-header">
            <h1 class="modal-title">Equipos</h1>
            <div class="modal-subtitle">Crea o únete a un equipo</div>
        </div>
        <div id="equipos-content">
            <div style="text-align: center; padding: 2rem;">
                <i class="bi bi-arrow-repeat" style="font-size: 2rem; color: #3b82f6; animation: spin 1s linear infinite;"></i>
                <p style="margin-top: 1rem; color: #64748b;">Cargando...</p>
            </div>
        </div>
    `;

    popupDiv.appendChild(closeButton);

    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

    overlayDiv.onclick = (e) => { if (e.target === overlayDiv) hideModal(overlayDiv, popupDiv); };

    // Check if user has a team
    try {
        loadMyTeam(popupDiv);
    } catch (err) {
        console.error('Error initializing team modal:', err);
        const contentDiv = popupDiv.querySelector('#equipos-content');
        if (contentDiv) {
            contentDiv.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-exclamation-triangle empty-state-icon"></i>
                    <div class="empty-state-title">Error</div>
                    <p>Error al inicializar: ${err.message}</p>
                </div>
            `;
        }
    }

    showModal(overlayDiv, popupDiv);
}

function loadMyTeam(popupDiv) {
    fetch('/api/equipos/mi-equipo/info')
        .then(res => res.json())
        .then(data => {
            const contentDiv = popupDiv.querySelector('#equipos-content');

            if (data.success && data.tiene_equipo) {
                // User has a team - show team management
                renderMyTeam(contentDiv, data.team, popupDiv);
            } else {
                // No team - show create/join options
                renderCreateJoinOptions(contentDiv);
            }
        })
        .catch(err => {
            console.error('Error loading team:', err);
            const contentDiv = popupDiv.querySelector('#equipos-content');
            if (contentDiv) {
                contentDiv.innerHTML = `
                    <div class="empty-state">
                        <i class="bi bi-exclamation-triangle empty-state-icon"></i>
                        <div class="empty-state-title">Error</div>
                        <p>No se pudo cargar la información de equipos.</p>
                    </div>
                `;
            }
        });
}

function renderCreateJoinOptions(container) {
    container.innerHTML = `
        <div style="text-align: center; padding: 2rem 1rem;">
            <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(139, 92, 246, 0.15));
                        padding: 2.5rem; border-radius: 20px; margin-bottom: 2rem;
                        display: inline-block;">
                <i class="bi bi-people-fill" style="font-size: 4rem; color: #3b82f6;"></i>
            </div>
            <h3 style="color: #f1f5f9; margin-bottom: 1rem;">¿No tienes equipo?</h3>
            <p style="color: #94a3b8; margin-bottom: 2rem; max-width: 300px; margin-left: auto; margin-right: auto;">
                Crea tu propio equipo y compite con otros, o únete a un equipo existente.
            </p>
            <div style="display: flex; flex-direction: column; gap: 0.75rem; max-width: 280px; margin: 0 auto;">
                <button class="team-btn team-btn-primary" onclick="showCrearEquipoForm()">
                    <i class="bi bi-plus-lg"></i> Crear equipo
                </button>
                <button class="team-btn team-btn-secondary" onclick="showUnirseEquipo()">
                    <i class="bi bi-box-arrow-in-right"></i> Unirse a equipo
                </button>
                <button class="team-btn team-btn-secondary" onclick="showMisInvitaciones()">
                    <i class="bi bi-envelope"></i> Mis invitaciones
                </button>
            </div>
        </div>
    `;
}

function renderMyTeam(container, team, popup) {
    // Add plus button and dropdown to the popup
    if (popup) {
        popup.style.position = 'relative';

        // Check if button already exists
        if (!document.getElementById('plus-menu-btn')) {
            // Add plus button
            const plusBtn = document.createElement('button');
            plusBtn.className = 'plus-btn';
            plusBtn.innerHTML = '<i class="bi bi-plus-lg"></i>';
            plusBtn.onclick = togglePlusMenu;
            plusBtn.id = 'plus-menu-btn';
            popup.appendChild(plusBtn);

            // Add dropdown menu
            const dropdown = document.createElement('div');
            dropdown.className = 'plus-dropdown';
            dropdown.id = 'plus-dropdown-menu';

            const createItem = document.createElement('div');
            createItem.className = 'plus-dropdown-item';
            createItem.innerHTML = '<i class="bi bi-plus-circle"></i><span>Crear equipo</span>';
            createItem.addEventListener('click', () => { closePlusMenu(); showCrearEquipoForm(); });
            dropdown.appendChild(createItem);

            const joinItem = document.createElement('div');
            joinItem.className = 'plus-dropdown-item';
            joinItem.innerHTML = '<i class="bi bi-box-arrow-in-right"></i><span>Unirse a equipo</span>';
            joinItem.addEventListener('click', () => { closePlusMenu(); showUnirseEquipo(); });
            dropdown.appendChild(joinItem);

            const inviteItem = document.createElement('div');
            inviteItem.className = 'plus-dropdown-item';
            inviteItem.innerHTML = '<i class="bi bi-person-plus"></i><span>Invitar a equipo</span>';
            inviteItem.addEventListener('click', () => { closePlusMenu(); switchTab(null, 'invitar', team.id); });
            dropdown.appendChild(inviteItem);

            const myInvitationsItem = document.createElement('div');
            myInvitationsItem.className = 'plus-dropdown-item';
            myInvitationsItem.innerHTML = '<i class="bi bi-envelope"></i><span>Mis invitaciones</span>';
            myInvitationsItem.addEventListener('click', () => { closePlusMenu(); showMisInvitaciones(); });
            dropdown.appendChild(myInvitationsItem);

            popup.appendChild(dropdown);
        }
    }

    const membersHtml = team.members.map(member => `
        <div class="member-item" style="cursor: pointer;" onclick="openAuthorProfileModal('${escapeHtml(member.username)}')">
            <img src="${member.profile_image_url}" class="team-member-avatar" alt="${escapeHtml(member.username)}">
            <div class="member-info">
                <div class="member-name">
                    ${escapeHtml(member.username)}
                    ${member.is_me ? '<span style="color: #3b82f6; font-size: 0.7rem;"> (Tú)</span>' : ''}
                </div>
                <div class="member-puntos">${member.puntos} pts</div>
            </div>
            ${!member.is_me ? `
                <button class="member-remove-btn" onclick="event.stopPropagation(); eliminarMiembro(${team.id}, ${member.user_id})" title="Eliminar miembro">
                    <i class="bi bi-x-lg"></i>
                </button>
            ` : ''}
        </div>
    `).join('');

    container.innerHTML = `
        <div style="text-align: center; margin-bottom: 1.5rem;">
            ${team.imagen_url ? `
                <img src="${team.imagen_url}" class="team-avatar" style="width: 80px; height: 80px;">
            ` : `
                <div class="team-avatar" style="width: 80px; height: 80px; display: flex; align-items: center; justify-content: center;
                            background: linear-gradient(135deg, #3b82f6, #8b5cf6); margin: 0 auto;">
                    <i class="bi bi-people-fill" style="font-size: 2rem; color: white;"></i>
                </div>
            `}
            <h3 style="color: #f1f5f9; margin-top: 1rem; margin-bottom: 0.25rem;">${escapeHtml(team.nombre)}</h3>
            <p style="color: #64748b; font-size: 0.85rem;">
                ${team.member_count}/${team.max_members} miembros · ${team.puntos} pts totales
            </p>
        </div>

        <div class="tabs-container">
            <button class="tab-btn active" onclick="switchTab(this, 'miembros', ${team.id})">Miembros</button>
            <button class="tab-btn" onclick="switchTab(this, 'solicitudes', ${team.id})">Solicitudes</button>
            ${team.member_count < team.max_members ? `
                <button class="tab-btn" onclick="switchTab(this, 'invitar', ${team.id})">Invitar</button>
            ` : ''}
        </div>

        <div id="tab-miembros" class="tab-content">
            ${membersHtml}
        </div>

        <div id="tab-solicitudes" class="tab-content" style="display: none;">
            <div id="solicitudes-list">
                <p style="text-align: center; color: #64748b; padding: 1rem;">Cargando solicitudes...</p>
            </div>
        </div>

        ${team.member_count < team.max_members ? `
        <div id="tab-invitar" class="tab-content" style="display: none;">
            <input type="text" id="invitarUsername" class="team-input" placeholder="Nombre de usuario...">
            <button class="team-btn team-btn-primary" onclick="invitarUsuario(${team.id})" style="width: 100%;">
                <i class="bi bi-send"></i> Enviar invitación
            </button>
        </div>
        ` : ''}

        <div class="team-actions" style="justify-content: center; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #334155;">
            <button class="team-btn team-btn-danger" onclick="salirDelEquipo(${team.id})">
                <i class="bi bi-box-arrow-right"></i> Salir del equipo
            </button>
        </div>
    `;

    // Load join requests
    loadSolicitudesPendientes(team.id);
}

function switchTab(btn, tabId, teamId) {
    // Update active tab
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // Show/hide content
    document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
    const content = document.getElementById('tab-' + tabId);
    if (content) content.style.display = 'block';

    // Load solicitudes when switching to solicitudes tab
    if (tabId === 'solicitudes' && teamId) {
        loadSolicitudesPendientes(teamId);
    }
}

function loadSolicitudesPendientes(teamId) {
    fetch(`/api/equipos/${teamId}/solicitudes`)
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById('solicitudes-list');
            if (!container) return;

            if (!data.success || !data.solicitudes || data.solicitudes.length === 0) {
                container.innerHTML = `
                    <div class="empty-state" style="padding: 2rem 1rem;">
                        <i class="bi bi-inbox empty-state-icon" style="font-size: 3rem;"></i>
                        <p>No hay solicitudes pendientes</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = data.solicitudes.map(req => `
                <div class="invitation-item">
                    <img src="${req.user.profile_image_url}" class="team-member-avatar" alt="${escapeHtml(req.user.username)}">
                    <div class="invitation-info">
                        <div class="invitation-team-name">${escapeHtml(req.user.username)}</div>
                        <div class="invitation-meta">${req.user.puntos} pts</div>
                    </div>
                    <div class="invitation-actions">
                        <button class="team-btn team-btn-primary" style="padding: 0.4rem 0.75rem; font-size: 0.8rem;"
                                onclick="responderSolicitud(${req.id}, true)">
                            <i class="bi bi-check-lg"></i>
                        </button>
                        <button class="team-btn team-btn-danger" style="padding: 0.4rem 0.75rem; font-size: 0.8rem;"
                                onclick="responderSolicitud(${req.id}, false)">
                            <i class="bi bi-x-lg"></i>
                        </button>
                    </div>
                </div>
            `).join('');
        })
        .catch(err => {
            const container = document.getElementById('solicitudes-list');
            if (container) {
                container.innerHTML = `<p style="text-align: center; color: #ef4444;">Error cargando solicitudes</p>`;
            }
        });
}

// ==================== CREAR EQUIPO ====================

function showCrearEquipoForm() {
    closePlusMenu(); // Close plus menu if open

    const overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay';

    const popupDiv = document.createElement('div');
    popupDiv.className = 'popup';
    popupDiv.style.width = 'min(420px, 95vw)';

    const closeButton = document.createElement('button');
    closeButton.className = 'modal-close-button';
    closeButton.innerHTML = '&times;';
    closeButton.onclick = closePopup;

    popupDiv.innerHTML = `
        <div class="modal-header">
            <h1 class="modal-title">Crear Equipo</h1>
            <div class="modal-subtitle">Máximo ${5} miembros</div>
        </div>

        <div id="preview-container" class="team-preview-container" style="display: none;">
            <img id="preview-image" class="team-preview-image">
        </div>

        <input type="text" id="teamNombre" class="team-input" placeholder="Nombre del equipo..." maxlength="50">

        <input type="file" id="teamImagen" class="team-file-input" accept="image/*">
        <label for="teamImagen" class="team-file-label">
            <i class="bi bi-image"></i>
            <span id="file-label-text">Subir imagen del equipo</span>
        </label>

        <button class="team-btn team-btn-primary" onclick="crearEquipo()" style="width: 100%;">
            <i class="bi bi-plus-lg"></i> Crear equipo
        </button>
    `;

    popupDiv.appendChild(closeButton);

    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

    // Setup image preview
    const fileInput = popupDiv.querySelector('#teamImagen');
    const previewContainer = popupDiv.querySelector('#preview-container');
    const previewImage = popupDiv.querySelector('#preview-image');
    const fileLabel = popupDiv.querySelector('#file-label-text');

    fileInput.onchange = function() {
        if (this.files && this.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                previewImage.src = e.target.result;
                previewContainer.style.display = 'flex';
                fileLabel.textContent = 'Cambiar imagen';
                fileInput.parentElement.querySelector('.team-file-label').classList.add('has-file');
            };
            reader.readAsDataURL(this.files[0]);
        }
    };

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

async function crearEquipo() {
    const nombre = document.getElementById('teamNombre').value.trim();
    const imagenInput = document.getElementById('teamImagen');

    if (!nombre || nombre.length < 3) {
        alert('El nombre del equipo debe tener al menos 3 caracteres');
        return;
    }

    const formData = new FormData();
    formData.append('nombre', nombre);
    if (imagenInput.files && imagenInput.files[0]) {
        formData.append('imagen', imagenInput.files[0]);
    }

    try {
        const response = await fetch('/api/equipos/crear', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            alert('¡Equipo creado exitosamente!');
            // Close modal and refresh
            document.querySelectorAll('.overlay.visible, .popup.visible').forEach(el => {
                el.classList.remove('visible');
            });
            setTimeout(() => {
                document.querySelectorAll('.overlay, .popup').forEach(el => {
                    if (el.parentNode) el.parentNode.removeChild(el);
                });
            }, 300);
            // Reopen equipos modal to show the team
            setTimeout(() => openEquiposModal(), 400);
        } else {
            alert('Error: ' + data.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al crear el equipo');
    }
}

// ==================== UNIRSE A EQUIPO ====================

function showUnirseEquipo() {
    closePlusMenu(); // Close plus menu if open

    const overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay';

    const popupDiv = document.createElement('div');
    popupDiv.className = 'popup';
    popupDiv.style.width = 'min(480px, 95vw)';

    const closeButton = document.createElement('button');
    closeButton.className = 'modal-close-button';
    closeButton.innerHTML = '&times;';
    closeButton.onclick = closePopup;

    popupDiv.innerHTML = `
        <div class="modal-header">
            <h1 class="modal-title">Unirse a Equipo</h1>
            <div class="modal-subtitle">Elige un equipo para solicitar unirte</div>
        </div>
        <div class="ranking-search-container">
            <div class="search-wrapper" style="flex: 1;">
                <input type="text" id="buscarEquipoInput" class="search-input" placeholder="Buscar equipo...">
                <button class="search-icon-btn"><i class="bi bi-search"></i></button>
            </div>
        </div>
        <div id="equipos-disponibles-list" style="max-height: 400px; overflow-y: auto;">
            <p style="text-align: center; color: #64748b; padding: 2rem;">Cargando equipos...</p>
        </div>
    `;

    popupDiv.appendChild(closeButton);

    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

    setTimeout(() => {
        popupDiv.classList.add('visible');
        overlayDiv.classList.add('visible');
    }, 10);

    overlayDiv.onclick = (e) => { if (e.target === overlayDiv) closePopup(); };

    // Load teams
    loadEquiposDisponibles();

    function closePopup() {
        popupDiv.classList.remove('visible');
        overlayDiv.classList.remove('visible');
        setTimeout(() => {
            if (popupDiv.parentNode) document.body.removeChild(popupDiv);
            if (overlayDiv.parentNode) document.body.removeChild(overlayDiv);
        }, 300);
    }
}

function loadEquiposDisponibles() {
    fetch('/api/equipos')
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById('equipos-disponibles-list');
            if (!data.success) {
                container.innerHTML = `<p style="text-align: center; color: #ef4444;">Error cargando equipos</p>`;
                return;
            }

            if (data.equipos.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="bi bi-people empty-state-icon"></i>
                        <div class="empty-state-title">No hay equipos</div>
                        <p>Sé el primero en crear un equipo</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = data.equipos.map(team => `
                <div class="team-list-item ${team.is_full ? 'full' : ''}" ${!team.is_full ? `onclick="solicitarUnirse(${team.id})"` : ''}>
                    ${team.imagen_url ? `
                        <img src="${team.imagen_url}" class="team-avatar-small">
                    ` : `
                        <div class="team-avatar-small" style="background: linear-gradient(135deg, #3b82f6, #8b5cf6); display: flex; align-items: center; justify-content: center;">
                            <i class="bi bi-people-fill" style="font-size: 1rem; color: white;"></i>
                        </div>
                    `}
                    <div class="user-info" style="flex: 1;">
                        <span class="user-name">${escapeHtml(team.nombre)}</span>
                    </div>
                    <span class="team-members-count">
                        ${team.is_full ? '<i class="bi bi-lock-fill" style="color: #ef4444;"></i>' : ''}
                        ${team.member_count}/${team.max_members}
                    </span>
                </div>
            `).join('');

            // Add search functionality
            const searchInput = document.getElementById('buscarEquipoInput');
            if (searchInput) {
                searchInput.oninput = function() {
                    const term = this.value.toLowerCase();
                    document.querySelectorAll('.team-list-item').forEach(item => {
                        const name = item.querySelector('.user-name').textContent.toLowerCase();
                        item.style.display = name.includes(term) ? 'flex' : 'none';
                    });
                };
            }
        })
        .catch(err => {
            const container = document.getElementById('equipos-disponibles-list');
            container.innerHTML = `<p style="text-align: center; color: #ef4444;">Error cargando equipos</p>`;
        });
}

async function solicitarUnirse(teamId) {
    if (!confirm('¿Enviar solicitud para unirte a este equipo?')) return;

    try {
        const response = await fetch(`/api/equipos/${teamId}/solicitar-unirse`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.success) {
            alert(data.message);
            // Close modal
            document.querySelectorAll('.overlay.visible, .popup.visible').forEach(el => {
                el.classList.remove('visible');
            });
            setTimeout(() => {
                document.querySelectorAll('.overlay, .popup').forEach(el => {
                    if (el.parentNode) el.parentNode.removeChild(el);
                });
            }, 300);
        } else {
            alert('Error: ' + data.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al enviar la solicitud');
    }
}

// ==================== INVITACIONES ====================

function showMisInvitaciones() {
    closePlusMenu(); // Close plus menu if open

    const overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay';

    const popupDiv = document.createElement('div');
    popupDiv.className = 'popup';
    popupDiv.style.width = 'min(480px, 95vw)';

    const closeButton = document.createElement('button');
    closeButton.className = 'modal-close-button';
    closeButton.innerHTML = '&times;';
    closeButton.onclick = closePopup;

    popupDiv.innerHTML = `
        <div class="modal-header">
            <h1 class="modal-title">Mis Invitaciones</h1>
            <div class="modal-subtitle">Invitaciones pendientes para unirte a equipos</div>
        </div>
        <div id="mis-invitaciones-list">
            <p style="text-align: center; color: #64748b; padding: 2rem;">Cargando invitaciones...</p>
        </div>
    `;

    popupDiv.appendChild(closeButton);

    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

    setTimeout(() => {
        popupDiv.classList.add('visible');
        overlayDiv.classList.add('visible');
    }, 10);

    overlayDiv.onclick = (e) => { if (e.target === overlayDiv) closePopup(); };

    // Load invitations
    loadMisInvitaciones();

    function closePopup() {
        popupDiv.classList.remove('visible');
        overlayDiv.classList.remove('visible');
        setTimeout(() => {
            if (popupDiv.parentNode) document.body.removeChild(popupDiv);
            if (overlayDiv.parentNode) document.body.removeChild(overlayDiv);
        }, 300);
    }
}

function loadMisInvitaciones() {
    fetch('/api/equipos/invitaciones/mis-invitaciones')
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById('mis-invitaciones-list');

            if (!data.success) {
                container.innerHTML = `<p style="text-align: center; color: #ef4444;">Error cargando invitaciones</p>`;
                return;
            }

            if (data.invitaciones.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="bi bi-envelope-slash empty-state-icon"></i>
                        <div class="empty-state-title">No tienes invitaciones</div>
                        <p>Espera a que te inviten a un equipo o solicita unirte a uno</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = data.invitaciones.map(inv => `
                <div class="invitation-item">
                    ${inv.team.imagen_url ? `
                        <img src="${inv.team.imagen_url}" class="team-avatar-small">
                    ` : `
                        <div class="team-avatar-small" style="background: linear-gradient(135deg, #3b82f6, #8b5cf6); display: flex; align-items: center; justify-content: center;">
                            <i class="bi bi-people-fill" style="font-size: 1rem; color: white;"></i>
                        </div>
                    `}
                    <div class="invitation-info">
                        <div class="invitation-team-name">${escapeHtml(inv.team.nombre)}</div>
                        <div class="invitation-meta">
                            Invitado por ${escapeHtml(inv.invited_by)} ·
                            ${inv.team.member_count}/${inv.team.max_members} miembros
                        </div>
                    </div>
                    <div class="invitation-actions">
                        <button class="team-btn team-btn-primary" style="padding: 0.4rem 0.75rem;"
                                onclick="responderInvitacion(${inv.id}, true)">
                            <i class="bi bi-check-lg"></i>
                        </button>
                        <button class="team-btn team-btn-danger" style="padding: 0.4rem 0.75rem;"
                                onclick="responderInvitacion(${inv.id}, false)">
                            <i class="bi bi-x-lg"></i>
                        </button>
                    </div>
                </div>
            `).join('');
        })
        .catch(err => {
            const container = document.getElementById('mis-invitaciones-list');
            container.innerHTML = `<p style="text-align: center; color: #ef4444;">Error cargando invitaciones</p>`;
        });
}

async function responderInvitacion(invitationId, accept) {
    try {
        const response = await fetch('/api/equipos/invitaciones/responder', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                invitation_id: invitationId,
                accept: accept
            })
        });

        const data = await response.json();

        if (data.success) {
            alert(data.message);
            // Close modal and refresh
            document.querySelectorAll('.overlay.visible, .popup.visible').forEach(el => {
                el.classList.remove('visible');
            });
            setTimeout(() => {
                document.querySelectorAll('.overlay, .popup').forEach(el => {
                    if (el.parentNode) el.parentNode.removeChild(el);
                });
            }, 300);
        } else {
            alert('Error: ' + data.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al procesar la invitación');
    }
}

async function responderSolicitud(requestId, accept) {
    try {
        const response = await fetch('/api/equipos/solicitudes/responder', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                request_id: requestId,
                accept: accept
            })
        });

        const data = await response.json();

        if (data.success) {
            alert(data.message);
            // Reload the current view
            const activeTab = document.querySelector('.tab-btn.active');
            if (activeTab && activeTab.textContent === 'Solicitudes') {
                // Find team id from the current modal
                const teamIdMatch = document.querySelector('.member-remove-btn');
                if (teamIdMatch) {
                    const onclick = teamIdMatch.getAttribute('onclick');
                    const match = onclick.match(/eliminarMiembro\((\d+),/);
                    if (match) {
                        loadSolicitudesPendientes(parseInt(match[1]));
                    }
                }
            }
        } else {
            alert('Error: ' + data.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al procesar la solicitud');
    }
}

async function invitarUsuario(teamId) {
    const username = document.getElementById('invitarUsername').value.trim();

    if (!username) {
        alert('Ingresa un nombre de usuario');
        return;
    }

    try {
        const response = await fetch(`/api/equipos/${teamId}/invitar`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ team_id: teamId, username: username })
        });

        const data = await response.json();

        if (data.success) {
            alert(data.message);
            document.getElementById('invitarUsername').value = '';
        } else {
            alert('Error: ' + data.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al enviar la invitación');
    }
}

async function eliminarMiembro(teamId, userId) {
    if (!confirm('¿Eliminar este miembro del equipo?')) return;

    try {
        const response = await fetch(`/api/equipos/${teamId}/eliminar-miembro`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ team_id: teamId, user_id: userId })
        });

        const data = await response.json();

        if (data.success) {
            alert(data.message);
            // Refresh modal
            document.querySelectorAll('.overlay.visible, .popup.visible').forEach(el => {
                el.classList.remove('visible');
            });
            setTimeout(() => {
                document.querySelectorAll('.overlay, .popup').forEach(el => {
                    if (el.parentNode) el.parentNode.removeChild(el);
                });
            }, 300);
            setTimeout(() => openEquiposModal(), 400);
        } else {
            alert('Error: ' + data.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al eliminar el miembro');
    }
}

async function salirDelEquipo(teamId) {
    if (!confirm('¿Salir del equipo? Si eres el último miembro, el equipo se eliminará.')) return;

    try {
        const response = await fetch(`/api/equipos/${teamId}/salir`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            alert(data.message);
            // Close modal
            document.querySelectorAll('.overlay.visible, .popup.visible').forEach(el => {
                el.classList.remove('visible');
            });
            setTimeout(() => {
                document.querySelectorAll('.overlay, .popup').forEach(el => {
                    if (el.parentNode) el.parentNode.removeChild(el);
                });
            }, 300);
        } else {
            alert('Error: ' + data.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al salir del equipo');
    }
}

function openTeamDetailModal(teamId) {
    fetch(`/api/equipos/${teamId}`)
        .then(res => res.json())
        .then(data => {
            if (!data.success) {
                alert('Error: ' + data.message);
                return;
            }

            const team = data.team;
            const { overlayDiv, popupDiv } = createModalElements('min(450px, 95vw)');

            const closeButton = document.createElement('button');
            closeButton.className = 'modal-close-button';
            closeButton.innerHTML = '&times;';
            closeButton.onclick = () => hideModal(overlayDiv, popupDiv);

            const membersHtml = team.members.map(member => `
                <div class="member-item" style="cursor: pointer;" onclick="openAuthorProfileModal('${escapeHtml(member.username)}')">
                    <img src="${member.profile_image_url}" class="team-member-avatar" alt="${escapeHtml(member.username)}">
                    <div class="member-info">
                        <div class="member-name">${escapeHtml(member.username)}</div>
                        <div class="member-puntos">${member.puntos} pts</div>
                    </div>
                </div>
            `).join('');

            let joinButtonHtml = '';
            if (!team.is_member && team.member_count < team.max_members) {
                joinButtonHtml = `<button class="team-btn team-btn-primary" onclick="solicitarUnirse(${team.id})" style="width: 100%; margin-top: 1rem;"><i class="bi bi-box-arrow-in-right"></i> Solicitar unirse</button>`;
            } else if (team.is_member) {
                joinButtonHtml = `<div style="text-align: center; color: #64748b; font-size: 0.85rem; margin-top: 1rem;"><i class="bi bi-check-circle-fill" style="color: #22c55e;"></i> Ya eres miembro</div>`;
            } else {
                joinButtonHtml = `<div style="text-align: center; color: #64748b; font-size: 0.85rem; margin-top: 1rem;"><i class="bi bi-x-circle-fill" style="color: #ef4444;"></i> Equipo completo</div>`;
            }

            popupDiv.innerHTML = `
                <div class="modal-header">
                    ${team.imagen_url ? `<img src="${team.imagen_url}" class="team-avatar" style="margin-bottom: 1rem;">` : `<div class="team-avatar" style="background: linear-gradient(135deg, #3b82f6, #8b5cf6); margin-bottom: 1rem; display: flex; align-items: center; justify-content: center;"><i class="bi bi-people-fill" style="font-size: 2rem; color: white;"></i></div>`}
                    <h1 class="modal-title">${escapeHtml(team.nombre)}</h1>
                    <div class="modal-subtitle">${team.member_count}/${team.max_members} miembros · ${team.puntos} pts</div>
                </div>
                <div class="section-title">Miembros</div>
                ${membersHtml}
                ${joinButtonHtml}
            `;

            popupDiv.appendChild(closeButton);

            document.body.appendChild(overlayDiv);
            document.body.appendChild(popupDiv);

            overlayDiv.onclick = (e) => { if (e.target === overlayDiv) hideModal(overlayDiv, popupDiv); };

            showModal(overlayDiv, popupDiv);
        })
        .catch(err => {
            console.error('Error:', err);
            alert('Error al cargar detalles del equipo');
        });
}

function solicitarUnirse(teamId) {
    fetch(`/api/equipos/${teamId}/solicitar-unirse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            location.reload();
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(err => {
        console.error(err);
        alert('Error al enviar solicitud');
    });
}

// ==================== PLUS MENU FUNCTIONS ====================

function togglePlusMenu(event) {
    event.stopPropagation();
    const dropdown = document.getElementById('plus-dropdown-menu');
    if (dropdown) {
        dropdown.classList.toggle('show');
    }
}

function closePlusMenuOnClickOutside(event) {
    const dropdown = document.getElementById('plus-dropdown-menu');
    const plusBtn = document.getElementById('plus-menu-btn');

    if (dropdown && plusBtn && !dropdown.contains(event.target) && !plusBtn.contains(event.target)) {
        dropdown.classList.remove('show');
    }
}

function closePlusMenu() {
    const dropdown = document.getElementById('plus-dropdown-menu');
    if (dropdown) {
        dropdown.classList.remove('show');
    }
}

// Export functions for global access
window.rankingEquipos = rankingEquipos;
window.openEquiposModal = openEquiposModal;
window.showCrearEquipoForm = showCrearEquipoForm;
window.showUnirseEquipo = showUnirseEquipo;
window.showMisInvitaciones = showMisInvitaciones;
window.crearEquipo = crearEquipo;
window.solicitarUnirse = solicitarUnirse;
window.responderInvitacion = responderInvitacion;
window.responderSolicitud = responderSolicitud;
window.invitarUsuario = invitarUsuario;
window.eliminarMiembro = eliminarMiembro;
window.salirDelEquipo = salirDelEquipo;
window.switchTab = switchTab;
window.openTeamDetailModal = openTeamDetailModal;
window.togglePlusMenu = togglePlusMenu;
window.closePlusMenu = closePlusMenu;
