function ranking() {
    const styleId = 'bunker-ranking-styles';
    if (!document.getElementById(styleId)) {
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            .bunker-rank-overlay {
                position: fixed;
                top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(13, 12, 28, 0.85);
                backdrop-filter: blur(8px);
                z-index: 10000;
                opacity: 0;
                transition: opacity 0.2s ease;
            }
            .bunker-rank-overlay.active { opacity: 1; }

            .bunker-rank-popup {
                position: fixed;
                top: 50%; left: 50%;
                transform: translate(-50%, -48%) scale(0.98);
                width: min(440px, 92vw);
                max-height: 85vh;
                background: linear-gradient(145deg, rgba(20, 18, 41, 0.98), rgba(13, 12, 28, 0.99));
                border: 1px solid rgba(139, 92, 246, 0.3);
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8), 0 0 30px rgba(139, 92, 246, 0.15);
                border-radius: 16px;
                z-index: 10001;
                color: #e2e8f0;
                font-family: 'Inter', sans-serif;
                opacity: 0;
                transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
                display: flex;
                flex-direction: column;
            }
            .bunker-rank-popup.active { opacity: 1; transform: translate(-50%, -50%) scale(1); }

            .bunker-rank-header {
                padding: 1.5rem 1.8rem 1rem;
                border-bottom: 1px solid rgba(139, 92, 246, 0.1);
                text-align: center;
            }

            .bunker-rank-title {
                margin: 0;
                font-size: 1.2rem;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 0.1em;
                background: linear-gradient(135deg, #fff 0%, #a78bfa 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }

            .bunker-rank-content {
                padding: 1.2rem 1.5rem;
                overflow-y: auto;
                flex: 1;
            }

            .bunker-rank-list {
                list-style: none;
                padding: 0; margin: 0;
                display: flex;
                flex-direction: column;
                gap: 0.8rem;
            }

            .bunker-rank-item {
                background: rgba(30, 41, 59, 0.4);
                border: 1px solid rgba(139, 92, 246, 0.1);
                border-radius: 12px;
                padding: 0.8rem 1rem;
                display: flex;
                align-items: center;
                justify-content: space-between;
                transition: all 0.2s;
            }
            .bunker-rank-item:hover {
                background: rgba(139, 92, 246, 0.1);
                border-color: rgba(139, 92, 246, 0.3);
                transform: translateX(4px);
            }

            .bunker-rank-pos {
                width: 32px; height: 32px;
                display: flex; align-items: center; justify-content: center;
                font-weight: 800; border-radius: 8px; font-size: 0.9rem;
                background: rgba(0,0,0,0.3);
            }
            .rank-1 { color: #fbbf24; border: 1px solid rgba(251, 191, 36, 0.3); }
            .rank-2 { color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.3); }
            .rank-3 { color: #d97706; border: 1px solid rgba(217, 119, 6, 0.3); }

            .bunker-rank-close {
                position: absolute;
                top: 1rem; right: 1rem;
                background: transparent; border: none;
                color: rgba(255,255,255,0.3);
                font-size: 1.8rem; cursor: pointer;
                line-height: 1; transition: color 0.2s;
            }
            .bunker-rank-close:hover { color: #fff; }
        `;
        document.head.appendChild(style);
    }

    const overlay = document.createElement('div');
    overlay.className = 'bunker-rank-overlay';
    const popup = document.createElement('div');
    popup.className = 'bunker-rank-popup';

    popup.innerHTML = `
        <button class="bunker-rank-close">&times;</button>
        <div class="bunker-rank-header">
            <h2 class="bunker-rank-title">Salón de la Fama</h2>
            <p style="font-size: 0.8rem; color: #94a3b8; margin: 0.2rem 0 0;">Top agentes por máquinas hackeadas</p>
        </div>
        <div class="bunker-rank-content">
            <div id="ranking-container">Cargando datos del búnker...</div>
        </div>
    `;

    document.body.appendChild(overlay);
    document.body.appendChild(popup);

    setTimeout(() => {
        overlay.classList.add('active');
        popup.classList.add('active');
    }, 10);

    const close = () => {
        overlay.classList.remove('active');
        popup.classList.remove('active');
        setTimeout(() => {
            if (overlay.parentNode) document.body.removeChild(overlay);
            if (popup.parentNode) document.body.removeChild(popup);
        }, 200);
    };

    popup.querySelector('.bunker-rank-close').onclick = close;
    overlay.onclick = (e) => { if (e.target === overlay) close(); };

    fetch('/bunkerlabs/api/ranking')
        .then(r => r.json())
        .then(data => {
            data.sort((a, b) => b.puntos - a.puntos);
            const container = popup.querySelector('#ranking-container');
            let html = '<ul class="bunker-rank-list">';
            data.forEach((user, i) => {
                const posClass = i === 0 ? 'rank-1' : i === 1 ? 'rank-2' : i === 2 ? 'rank-3' : '';
                const icon = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : i + 1;
                html += `
                    <li class="bunker-rank-item">
                        <div style="display: flex; align-items: center; gap: 1rem;">
                            <div class="bunker-rank-pos ${posClass}">${icon}</div>
                            <span style="font-weight: 600; font-size: 0.95rem;">${user.nombre}</span>
                        </div>
                        <span style="font-weight: 800; color: #a78bfa; font-size: 0.9rem;">${user.puntos} <small style="font-weight: 400; opacity: 0.6;">PTS</small></span>
                    </li>
                `;
            });
            html += '</ul>';
            container.innerHTML = html;
        })
        .catch(err => {
            popup.querySelector('#ranking-container').innerHTML = '<p style="color: #f87171; text-align: center;">Fallo en los sistemas. No se pudo cargar el ranking.</p>';
        });
}


function rankingautores() {
    // Para simplificar y mantener consistencia, redirigimos o usamos el mismo estilo
    // pero BunkerLabs usa su propio ranking de APIs. El de autores es general.
    // Si el usuario lo pide en Bunker, lo mostramos con este estilo.
    const styleId = 'bunker-ranking-styles';
    // ... asumimos estilos ya inyectados por ranking() o los inyectamos igual ...
    // Para evitar duplicar código excesivo en el script, llamamos a una base o repetimos
    // pero el usuario solo ve BunkerLabs. 

    // Mostramos un alert o implementamos similar
    alert("Ranking de autores no disponible en zona Bunker.");
}
