// Utility function to escape HTML and prevent XSS attacks
function escapeHtml(text) {
    if (!text) return text;
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function presentacion(nombre, dificultad, color, autor_nombre, autor_enlace, fecha, imagen, categoria = '', isMostRecent = false) {
    // Inject Styles for the new design
    const styleId = 'modern-modal-styles-v2';
    if (!document.getElementById(styleId)) {
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

            .overlay, .overlay-rating {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(15, 23, 42, 0.85);
                backdrop-filter: blur(8px);
                z-index: 9998;
                opacity: 0;
                opacity: 0;
                transition: opacity 0.3s ease;
            }

            .overlay.visible, .overlay-rating.visible {
                opacity: 1;
            }

            .popup {
                background: #1e293b; /* Dark Slate Blue Background */
                color: #f1f5f9;
                border-radius: 24px;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                position: fixed;
                top: 50%;
                left: 50%;
                width: 900px;
                max-width: 95vw;
                height: auto;
                max-height: 90vh;
                display: grid;
                grid-template-columns: 1fr 1.1fr; /* Image | Content */
                overflow: hidden;
                opacity: 0;
                transform: translate(-50%, -50%) scale(0.95);
                transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
                font-family: 'Inter', sans-serif;
                margin: 0;
            }


            @media (max-width: 768px) {
                .popup {
                    grid-template-columns: 1fr;
                    width: 95vw;
                    max-height: 90vh;
                    overflow-y: auto;
                    border-radius: 16px;
                }
                
                .popup-image-container {
                    padding: 1.5rem !important;
                    min-height: 250px;
                    max-height: 300px;
                }
                
                .popup-content {
                    padding: 1.5rem !important;
                }
                
                .machine-title {
                    font-size: 1.75rem !important;
                    line-height: 1.2 !important;
                }
                
                .header-row {
                    padding-right: 2.5rem !important;
                    flex-wrap: wrap;
                    gap: 0.5rem;
                }
                
                .rating-badge {
                    font-size: 0.85rem !important;
                }
                
                .difficulty-pill {
                    font-size: 0.7rem !important;
                    padding: 0.3rem 0.8rem !important;
                }
                
                .creator-card {
                    margin-top: 1.5rem !important;
                    padding: 0.875rem !important;
                    flex-wrap: wrap;
                }
                
                .creation-date {
                    width: 100%;
                    margin-left: 0 !important;
                    margin-top: 0.5rem;
                    justify-content: flex-start;
                }
                
                .action-area {
                    margin-top: 1.5rem !important;
                }
                
                .btn-mark-completed {
                    padding: 0.875rem !important;
                    font-size: 0.95rem !important;
                }
                
                .modal-footer {
                    padding-top: 1.5rem !important;
                    flex-direction: column;
                    gap: 1rem;
                    align-items: flex-start;
                }
                
                .user-rating-stars {
                    font-size: 1.2rem !important;
                }
            }

            @media (max-width: 480px) {
                .popup {
                    width: 100vw;
                    max-height: 100vh;
                    border-radius: 0;
                }
                
                .popup-image-container {
                    padding: 1rem !important;
                    min-height: 200px;
                    max-height: 250px;
                }
                
                .popup-content {
                    padding: 1rem !important;
                }
                
                .machine-title {
                    font-size: 1.5rem !important;
                }
                
                .modal-close-button {
                    top: 1rem !important;
                    right: 1rem !important;
                }
                
                .creator-card {
                    padding: 0.75rem !important;
                }
                
                .creator-avatar {
                    width: 40px !important;
                    height: 40px !important;
                }
                
                .creator-name {
                    font-size: 0.9rem !important;
                }
                
                .rating-modal-v2 {
                    padding: 1.5rem !important;
                    border-radius: 12px !important;
                }
            }

            .popup.visible {
                opacity: 1;
                transform: translate(-50%, -50%) scale(1);
            }

            /* Left Side: Image */
            .popup-image-container {
                position: relative;
                background: #0f172a;
                overflow: hidden;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 2rem;
            }

            .popup-machine-image {
                width: 100%;
                height: auto;
                max-height: 100%;
                aspect-ratio: 1/1;
                object-fit: cover;
                border-radius: 16px;
                /* box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3); */
            }
            
            /* Decorative sparkle or overlay on image if needed */
            .image-sparkle {
                position: absolute;
                bottom: 2rem;
                right: 2rem;
                color: rgba(255,255,255,0.6);
                font-size: 1.5rem;
            }

            /* Right Side: Content */
            .popup-content {
                padding: 2.5rem;
                display: flex;
                flex-direction: column;
                position: relative;
            }
            
            .modal-close-button {
                position: absolute;
                top: 1.5rem;
                right: 1.5rem;
                background: rgba(255,255,255,0.05); /* Subtle background */
                border: none;
                color: #94a3b8;
                width: 32px;
                height: 32px;
                border-radius: 50%;
                font-size: 1.25rem;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.2s;
                z-index: 10;
            }

            .modal-close-button:hover {
                background: rgba(255,255,255,0.1);
                color: white;
            }

            /* Header Section */
            .header-row {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 0.5rem;
                padding-right: 2rem; /* Space for close button */
            }

            .machine-title {
                font-size: 2.5rem;
                font-weight: 700;
                color: #ffffff;
                margin: 0;
                line-height: 1.1;
                letter-spacing: -0.02em;
            }

            .rating-badge {
                display: flex;
                align-items: center;
                gap: 0.35rem;
                background: rgba(255,255,255,0.05);
                padding: 0.35rem 0.75rem;
                border-radius: 8px;
                font-weight: 600;
                color: #fbbf24; /* Amber 400 */
                font-size: 0.9rem;
            }

            .difficulty-pill {
                display: inline-block;
                padding: 0.35rem 1rem;
                border-radius: 999px;
                font-size: 0.75rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-top: 0.75rem;
                background: rgba(255,255,255,0.05); /* Fallback */
                border: 1px solid rgba(255,255,255,0.1);
            }

            /* Creator Card */
            .creator-card {
                background: rgba(30, 41, 59, 0.5); /* Slightly lighter/darker */
                border: 1px solid rgba(148, 163, 184, 0.1);
                border-radius: 12px;
                padding: 1rem;
                margin-top: 2rem;
                display: flex;
                align-items: center;
                gap: 1rem;
            }

            .creator-avatar {
                width: 48px;
                height: 48px;
                border-radius: 50%;
                object-fit: cover;
                background: #334155;
            }

            .creator-info {
                flex: 1;
            }

            .creator-label {
                font-size: 0.75rem;
                color: #94a3b8;
                margin-bottom: 2px;
            }

            .creator-name {
                font-weight: 600;
                color: #e2e8f0;
                font-size: 1rem;
                text-decoration: none;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            
            .creator-socials {
                display: flex;
                gap: 0.5rem;
                margin-left: 0.5rem;
            }
            
            .social-icon {
                color: #94a3b8;
                transition: color 0.2s;
                font-size: 1rem;
            }
            
            .social-icon:hover { color: #fff; }

            .creation-date {
                font-size: 0.8rem;
                color: #64748b;
                display: flex;
                align-items: center;
                gap: 0.35rem;
                margin-left: auto; /* Push to right */
            }

            /* Main Action Button */
            .action-area {
                margin-top: 2rem;
            }

            .btn-mark-completed {
                width: 100%;
                background: transparent;
                border: 1px solid #334155;
                color: #cbd5e1;
                padding: 1rem;
                border-radius: 12px;
                font-weight: 600;
                font-size: 1rem;
                cursor: pointer;
                transition: all 0.2s;
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 0.75rem;
            }

            .btn-mark-completed:hover {
                background: rgba(255,255,255,0.03);
                border-color: #475569;
                color: #fff;
            }

            .btn-mark-completed.completed {
                background: rgba(16, 185, 129, 0.1); /* Emerald tint */
                border-color: rgba(16, 185, 129, 0.4);
                color: #34d399;
            }

            /* Footer / Rating */
            .modal-footer {
                margin-top: auto; /* Push to bottom */
                padding-top: 2rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .user-rating-label {
                color: #64748b;
                font-size: 0.9rem;
            }

            .user-rating-stars {
                color: #fbbf24;
                font-size: 1.1rem;
                cursor: pointer;
            }
            
            /* Difficulty Colors Override */
            .diff-muy-facil { color: #06b6d4 !important; border-color: rgba(6, 182, 212, 0.3) !important; }
            .diff-facil { color: #8bc34a !important; border-color: rgba(139, 195, 74, 0.3) !important; }
            .diff-medio { color: #e0a553 !important; border-color: rgba(224, 165, 83, 0.3) !important; }
            .diff-dificil { color: #d83c31 !important; border-color: rgba(216, 60, 49, 0.3) !important; }


            /* Rating Modal Styles (reused mostly) */
            .rating-modal-v2 {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                z-index: 10000;
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 16px;
                padding: 2rem;
                width: min(400px, 90%);
                text-align: center;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                font-family: 'Inter', sans-serif;
                color: #f8fafc;
            }
            .rating-row {
                display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;
            }
            .rating-actions { 
                 display: flex; gap: 1rem; margin-top: 1.5rem; 
            }
            .primary-btn { flex:1; background: #3b82f6; color: white; border:none; padding: 0.75rem; border-radius: 8px; cursor:pointer;}
            .secondary-btn { flex:1; background: transparent; border: 1px solid #475569; color: #94a3b8; padding: 0.75rem; border-radius: 8px; cursor:pointer;}
        `;
        document.head.appendChild(style);
    }

    // --- Modal Structure Construction ---

    var overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay';

    var popupDiv = document.createElement('div');
    popupDiv.className = 'popup';

    // Escaped Data
    const escNombre = escapeHtml(nombre);
    const escDificultad = escapeHtml(dificultad);
    const escAutor = escapeHtml(autor_nombre);
    const escFecha = escapeHtml(fecha);
    const escImagen = escapeHtml(imagen);

    // Determine Difficulty Class
    let diffClass = '';
    const dLower = dificultad.toLowerCase();
    if (dLower === 'muy fácil') diffClass = 'diff-muy-facil';
    else if (dLower === 'fácil') diffClass = 'diff-facil';
    else if (dLower === 'medio') diffClass = 'diff-medio';
    else if (dLower === 'difícil') diffClass = 'diff-dificil';

    // Apply colored border/glow based on difficulty color passed
    if (color) {
        popupDiv.style.border = `2px solid ${color}`;
        popupDiv.style.boxShadow = `0 0 20px -5px ${color}, 0 25px 50px -12px rgba(0, 0, 0, 0.5)`;
    }

    // Image Cleanup
    function sanitizeImagePath(path) {
        if (!path) return 'logos/default.png';
        path = path.replace(/\.\./g, '');
        path = path.replace(/^\/+/, '');
        path = path.replace(/[^a-zA-Z0-9\-_./]/g, '');
        return path;
    }
    const imageUrl = "/static/images/" + sanitizeImagePath(escImagen);

    // --- DOM Structure ---

    // 1. Left Container: Image
    const leftContainer = document.createElement('div');
    leftContainer.className = 'popup-image-container';

    const imgEl = document.createElement('img');
    imgEl.className = 'popup-machine-image';
    imgEl.src = imageUrl;

    // Optional sparkle icon from screenshot
    const sparkle = document.createElement('i');
    sparkle.className = 'bi bi-stars image-sparkle';

    leftContainer.appendChild(imgEl);
    leftContainer.appendChild(sparkle);

    // 2. Right Container: Content
    const rightContainer = document.createElement('div');
    rightContainer.className = 'popup-content';

    // Close Button
    const closeBtn = document.createElement('button');
    closeBtn.className = 'modal-close-button';
    closeBtn.innerHTML = '&times;';
    closeBtn.onclick = closePopup;

    // Header (Title + Rating Score)
    const headerRow = document.createElement('div');
    headerRow.className = 'header-row';

    const title = document.createElement('h1');
    title.className = 'machine-title';
    title.textContent = escNombre;

    const ratingBadge = document.createElement('div');
    ratingBadge.className = 'rating-badge';
    ratingBadge.id = 'modal-rating-score-display'; // Hook for fetching
    ratingBadge.innerHTML = '<i class="bi bi-star-fill"></i> <span>--</span>';

    headerRow.appendChild(title);
    headerRow.appendChild(ratingBadge);

    // Difficulty Pill
    const diffPill = document.createElement('div');
    diffPill.className = `difficulty-pill ${diffClass}`;
    diffPill.textContent = escDificultad;

    // Creator Card
    const creatorCard = document.createElement('div');
    creatorCard.className = 'creator-card';

    // We need to fetch author profile to get avatar and links
    // Placeholder structure first
    creatorCard.innerHTML = `
        <img src="/static/images/balu.webp" class="creator-avatar" id="creator-avatar-img">
        <div class="creator-info">
            <div class="creator-label">Creada por</div>
            <div class="creator-name">
                <span style="font-size:1.1em; font-weight:700;">${escAutor}</span>
                <span class="creator-socials" id="creator-socials-container"></span>
            </div>
        </div>
        <div class="creation-date">
            <i class="bi bi-calendar3"></i> ${escFecha}
        </div>
    `;

    // Action Area (Mark as Done / Download?)
    // Screenshot only shows "Marcar como hecha" and it's large.
    const actionArea = document.createElement('div');
    actionArea.className = 'action-area';

    const markDoneBtn = document.createElement('button');
    markDoneBtn.className = 'btn-mark-completed';
    markDoneBtn.innerHTML = '<i class="bi bi-circle"></i> Marcar como hecha'; // Default state

    actionArea.appendChild(markDoneBtn);

    // Footer (User Rating)
    const footer = document.createElement('div');
    footer.className = 'modal-footer';

    const footerLabel = document.createElement('span');
    footerLabel.className = 'user-rating-label';
    footerLabel.textContent = 'Tu valoración:';

    const footerStars = document.createElement('div');
    footerStars.className = 'user-rating-stars';
    footerStars.id = 'modal-user-rating-stars';
    // Initialize with 5 empty stars, each with an index for easier hover targeting
    footerStars.innerHTML = '';
    for (let i = 1; i <= 5; i++) {
        footerStars.innerHTML += `<i class="bi bi-star" data-index="${i}"></i>`;
    }

    footerStars.onclick = () => openRatingModal(nombre);

    footer.appendChild(footerLabel);
    footer.appendChild(footerStars);

    // Assemble Right Column
    rightContainer.appendChild(closeBtn);
    rightContainer.appendChild(headerRow);
    rightContainer.appendChild(diffPill);
    rightContainer.appendChild(creatorCard);
    rightContainer.appendChild(actionArea);
    rightContainer.appendChild(footer);

    // Assemble Popup
    popupDiv.appendChild(leftContainer);
    popupDiv.appendChild(rightContainer);
    overlayDiv.appendChild(popupDiv);

    document.body.appendChild(overlayDiv);

    // Animation
    setTimeout(() => {
        popupDiv.classList.add('visible');
        overlayDiv.classList.add('visible');
    }, 10);

    // --- Logic & Fetching ---

    // 1. Fetch Author Details (Avatar & Socials)
    fetch(`/api/author_profile?nombre=${encodeURIComponent(autor_nombre)}`)
        .then(res => res.json())
        .then(data => {
            if (data.profile_image_url) {
                const avatarEl = document.getElementById('creator-avatar-img');
                if (avatarEl) {
                    avatarEl.src = data.profile_image_url;
                }
            }

            const socialContainer = document.getElementById('creator-socials-container');
            if (socialContainer) {
                let html = '';
                if (data.linkedin_url) html += `<a href="${escapeHtml(data.linkedin_url)}" target="_blank" class="social-icon"><i class="bi bi-linkedin"></i></a>`;
                if (data.github_url) html += `<a href="${escapeHtml(data.github_url)}" target="_blank" class="social-icon"><i class="bi bi-github"></i></a>`;
                if (data.youtube_url) html += `<a href="${escapeHtml(data.youtube_url)}" target="_blank" class="social-icon"><i class="bi bi-youtube"></i></a>`;
                socialContainer.innerHTML = html;
            }
        })
        .catch(err => console.error(err));

    let hasUserRated = false; // State to track rating

    // 2. Fetch Machine Rating
    fetch(`/api/get_machine_rating/${nombre}`)
        .then(res => res.json())
        .then(data => {
            const scoreEl = document.getElementById('modal-rating-score-display');
            if (scoreEl && data.average) {
                scoreEl.innerHTML = `<i class="bi bi-star-fill"></i> <span>${parseFloat(data.average).toFixed(1)}</span>`;

                if (data.user_rating) {
                    hasUserRated = true;
                    const vals = Object.values(data.user_rating);
                    if (vals.length > 0) {
                        const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
                        updateUserStars(Math.round(avg));
                    }
                } else {
                    hasUserRated = false;
                    enableStarHover(footerStars);
                }
            } else {
                scoreEl.innerHTML = `<i class="bi bi-star-fill"></i> <span>--</span>`;
                hasUserRated = false;
                enableStarHover(footerStars);
            }
        });

    function updateUserStars(count) {
        // If updating definitively (e.g. from DB), remove hover listeners if we want to lock it?
        // Actually the user requirement is "if I haven't put a score".
        // So if we have a score, we just show it.
        const c = document.getElementById('modal-user-rating-stars');
        if (!c) return;
        let html = '';
        for (let i = 1; i <= 5; i++) {
            html += (i <= count) ? '<i class="bi bi-star-fill" data-index="' + i + '"></i>' : '<i class="bi bi-star" data-index="' + i + '"></i>';
        }
        c.innerHTML = html;
        c.style.color = '#fbbf24';
    }

    function enableStarHover(container) {
        if (!container) return;

        container.addEventListener('mousemove', function (e) {
            if (hasUserRated) return; // Don't hover effect if already rated

            // Find which star is hovered
            // e.target might be the i element
            const target = e.target.closest('i');
            if (!target) return;

            const index = parseInt(target.getAttribute('data-index') || "0");

            // Fill up to index
            const stars = container.querySelectorAll('i');
            stars.forEach((star, idx) => { // idx is 0-based
                if (idx < index) {
                    star.classList.remove('bi-star');
                    star.classList.add('bi-star-fill');
                    star.style.color = '#fbbf24';
                } else {
                    star.classList.remove('bi-star-fill');
                    star.classList.add('bi-star');
                    star.style.color = ''; // Reset color
                }
            });
        });

        container.addEventListener('mouseleave', function () {
            if (hasUserRated) return;

            // Reset to empty
            const stars = container.querySelectorAll('i');
            stars.forEach(star => {
                star.classList.remove('bi-star-fill');
                star.classList.add('bi-star');
                star.style.color = '';
            });
        });
    }

    // 3. Mark as Completed Logic
    function checkCompletion() {
        if (!currentUser) return; // Defined in global scope from template

        // Fetch status
        fetch(`/api/completed_machines/${encodeURIComponent(nombre)}`)
            .then(res => res.json())
            .then(data => {
                if (data.completed) {
                    setButtonCompleted(true);
                }
            });
    }

    function setButtonCompleted(isComplete) {
        if (isComplete) {
            markDoneBtn.innerHTML = '<i class="bi bi-check-circle-fill"></i> Completada';
            markDoneBtn.classList.add('completed');
        } else {
            markDoneBtn.innerHTML = '<i class="bi bi-circle"></i> Marcar como hecha';
            markDoneBtn.classList.remove('completed');
        }
    }

    markDoneBtn.onclick = function () {
        if (!currentUser) {
            alert("Debes iniciar sesión.");
            return;
        }
        // Optimistic UI update
        const isCurrentlyCompleted = markDoneBtn.classList.contains('completed');
        setButtonCompleted(!isCurrentlyCompleted);

        fetch('/api/toggle_completed_machine', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
            body: JSON.stringify({ machine_name: nombre })
        })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    setButtonCompleted(data.completed);
                } else {
                    setButtonCompleted(isCurrentlyCompleted); // Revert
                    alert("Error: " + data.error);
                }
            })
            .catch(err => {
                setButtonCompleted(isCurrentlyCompleted); // Revert
                alert("Error de conexión");
            });
    };

    if (typeof currentUser !== "undefined" && currentUser !== "") {
        checkCompletion();
    } else {
        markDoneBtn.style.display = 'none'; // Hide if not logged in
    }


    // Close logic
    overlayDiv.addEventListener('click', (e) => {
        if (e.target === overlayDiv) closePopup();
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

// Keep the existing Rating Modal Logic (it works fine and was not requested to change, 
// though we might want to update styles to match v2. I included v2 styles in CSS block)
function openRatingModal(machineName) {
    // ... (Keep implementation, just update class names if needed)
    // For brevity, I'll paste the existing logic but ensure it uses the new overlay class

    if (!currentUser) {
        alert("Debes iniciar sesión para puntuar.");
        return;
    }

    fetch(`/api/completed_machines/${encodeURIComponent(machineName)}`)
        .then(response => response.json())
        .then(data => {
            if (!data.completed) {
                alert("Debes marcar la máquina como completada antes de poder puntuarla.");
                return;
            }
            showRatingModal(machineName);
        })
        .catch(err => {
            console.error(err);
            alert("Error al verificar estado.");
        });
}

function showRatingModal(machineName) {
    var overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay-rating';

    var modalDiv = document.createElement('div');
    modalDiv.className = 'rating-modal-v2'; // Updated class

    var title = document.createElement('h3');
    title.textContent = `Puntuar ${machineName}`;
    title.style.margin = '0 0 1.5rem 0';
    title.style.fontSize = '1.25rem';
    title.style.color = '#f8fafc';
    modalDiv.appendChild(title);

    const criteria = [
        { id: 'dificultad_score', label: 'Dificultad Acorde' },
        { id: 'aprendizaje_score', label: 'Aprendizaje' },
        { id: 'recomendaria_score', label: 'Recomendaría' },
        { id: 'diversion_score', label: 'Diversión' }
    ];

    var scores = {};

    criteria.forEach(c => {
        var row = document.createElement('div');
        row.className = 'rating-row';

        var label = document.createElement('span');
        label.textContent = c.label;
        label.style.fontSize = '0.9rem';
        label.style.color = '#cbd5e1';

        var starsContainer = document.createElement('div');
        starsContainer.style.color = '#f59e0b';
        starsContainer.style.cursor = 'pointer';

        for (let i = 1; i <= 5; i++) {
            let star = document.createElement('i');
            star.className = 'bi bi-star';
            star.style.marginLeft = '4px';

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

    var actions = document.createElement('div');
    actions.className = 'rating-actions';

    var cancelBtn = document.createElement('button');
    cancelBtn.textContent = 'Cancelar';
    cancelBtn.className = 'secondary-btn';
    cancelBtn.onclick = function () {
        overlayDiv.classList.remove('visible');
        setTimeout(() => document.body.removeChild(overlayDiv), 200);
    };

    var saveBtn = document.createElement('button');
    saveBtn.textContent = 'Guardar';
    saveBtn.className = 'primary-btn';
    saveBtn.onclick = function () {
        if (Object.keys(scores).length < 4) {
            alert("Por favor valora todos los puntos.");
            return;
        }

        fetch('/api/rate_machine', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
            body: JSON.stringify({ maquina_nombre: machineName, ...scores })
        })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showSuccessToast("¡Puntuación registrada con éxito!");
                    overlayDiv.classList.remove('visible');
                    setTimeout(() => document.body.removeChild(overlayDiv), 200);

                    // Refresh parent ratings
                    fetch(`/api/get_machine_rating/${machineName}`)
                        .then(res => res.json())
                        .then(ratingData => {
                            // Update Average Score
                            const scoreEl = document.getElementById('modal-rating-score-display');
                            if (scoreEl && ratingData.average) {
                                scoreEl.innerHTML = `<i class="bi bi-star-fill"></i> <span>${parseFloat(ratingData.average).toFixed(1)}</span>`;
                            }

                            // Update User Stars
                            if (ratingData.user_rating) {
                                const vals = Object.values(ratingData.user_rating);
                                if (vals.length > 0) {
                                    const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
                                    // Re-implement updateUserStars logic here as we are out of scope
                                    const starContainer = document.getElementById('modal-user-rating-stars');
                                    if (starContainer) {
                                        let html = '';
                                        const count = Math.round(avg);
                                        for (let i = 1; i <= 5; i++) {
                                            html += (i <= count) ? '<i class="bi bi-star-fill"></i>' : '<i class="bi bi-star"></i>';
                                        }
                                        starContainer.innerHTML = html;
                                        starContainer.style.color = '#fbbf24';
                                    }
                                }
                            }
                        });

                } else {
                    alert("Error: " + data.message);
                }
            })
            .catch(err => alert("Error de red"));
    };

    actions.appendChild(cancelBtn);
    actions.appendChild(saveBtn);
    modalDiv.appendChild(actions);

    overlayDiv.appendChild(modalDiv);
    document.body.appendChild(overlayDiv);

    setTimeout(() => overlayDiv.classList.add('visible'), 10);

    overlayDiv.addEventListener('click', (e) => {
        if (e.target === overlayDiv) {
            overlayDiv.classList.remove('visible');
            setTimeout(() => document.body.removeChild(overlayDiv), 200);
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

function showSuccessToast(message) {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = 'custom-toast';
    toast.innerHTML = `<i class="bi bi-check-circle-fill" style="margin-right: 8px;"></i> ${message}`;

    // Styles
    Object.assign(toast.style, {
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        backgroundColor: '#10b981', // Emerald 500
        color: 'white',
        padding: '1rem 1.5rem',
        borderRadius: '12px',
        boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        display: 'flex',
        alignItems: 'center',
        fontSize: '1rem',
        fontWeight: '600',
        zIndex: '11000',
        opacity: '0',
        transform: 'translateY(20px)',
        transition: 'all 0.3s ease-out',
        fontFamily: "'Inter', sans-serif"
    });

    document.body.appendChild(toast);

    // Animate in
    requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    });

    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        setTimeout(() => {
            if (document.body.contains(toast)) {
                document.body.removeChild(toast);
            }
        }, 300);
    }, 3000);
}
