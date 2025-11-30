function createPopup(contenidoPopup) {
    const style = document.createElement('style');
    style.textContent = `
        @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600;700&display=swap');

        .overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle at top, rgba(2, 6, 23, 0.95), rgba(2, 6, 23, 0.98));
            backdrop-filter: blur(8px);
            z-index: 9998;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .overlay.visible {
            opacity: 1;
        }

        .popup {
            background: linear-gradient(135deg, #0a1120 0%, #020617 100%);
            color: #f9fafb;
            border: 1px solid #3b82f6;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.7), 0 0 40px rgba(59, 130, 246, 0.3);
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -60%);
            z-index: 9999;
            padding: 2rem;
            text-align: center;
            max-width: 480px;
            width: min(480px, 90vw);
            max-height: 85vh;
            overflow-y: auto;
            opacity: 0;
            font-family: 'Fira Code', monospace;
            transition: opacity 0.3s ease, transform 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        }

        .popup.visible {
            opacity: 1;
            transform: translate(-50%, -50%);
        }

        .popup-header {
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-bottom: 2rem;
        }

        .popup-icon {
            width: 64px;
            height: 64px;
            margin-bottom: 1.5rem;
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            box-shadow: 0 0 30px rgba(59, 130, 246, 0.5);
        }

        .popup-title {
            margin: 0 0 0.5rem;
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #60a5fa, #22d3ee);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 0.02em;
        }

        .popup-subtitle {
            margin: 0;
            font-size: 0.85rem;
            color: #94a3b8;
            font-weight: 400;
        }

        .popup ul {
            list-style-type: none;
            padding: 0;
            margin: 0;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            text-align: left;
        }

        .popup li {
            margin: 0;
            display: flex;
            align-items: stretch;
            font-size: 0.9rem;
        }

        .writeup-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            background: rgba(59, 130, 246, 0.15);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 10px 0 0 10px;
            font-size: 1.3rem;
            flex-shrink: 0;
            line-height: 1;
        }

        .popup a {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0.75rem 1rem;
            border-radius: 0 10px 10px 0;
            background: #0f172a;
            border: 1px solid #334155;
            border-left: none;
            color: #cbd5e1;
            text-decoration: none;
            font-weight: 500;
            font-size: 0.9rem;
            transition: all 0.3s ease;
            text-align: center;
            position: relative;
        }

        .popup a::after {
            content: "↗";
            font-size: 0.85rem;
            opacity: 0.6;
            position: absolute;
            right: 1rem;
            transition: all 0.2s ease;
        }

        .popup li:hover .writeup-icon {
            background: rgba(59, 130, 246, 0.25);
            border-color: #3b82f6;
        }

        .popup a:hover {
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            color: #ffffff;
            border-color: #3b82f6;
            transform: translateX(3px);
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
        }

        .popup a:hover::after {
            opacity: 1;
            transform: translateX(2px);
        }

        .popup a:focus-visible {
            outline: 2px solid #22d3ee;
            outline-offset: 2px;
        }

        .no-writeups {
            padding: 2rem 1rem;
            text-align: center;
            color: #64748b;
            font-size: 0.9rem;
        }

        .modal-close-button {
            position: absolute;
            top: 1rem;
            right: 1.2rem;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            border: none;
            background: none;
            color: #94a3b8;
            font-size: 1.8rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .modal-close-button:hover {
            background: rgba(239, 68, 68, 0.1);
            color: #ef4444;
            transform: scale(1.1);
        }

        .modal-close-button:focus-visible {
            outline: 2px solid #22d3ee;
            outline-offset: 2px;
        }

        .autor-registrado {
            color: #fbbf24 !important;
            font-weight: 700 !important;
            text-shadow: 0 0 8px rgba(251, 191, 36, 0.4);
        }

        .autor-registrado::before {
            content: "⭐ ";
            font-size: 0.75rem;
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
        }

        .popup::-webkit-scrollbar-thumb:hover {
            background: rgba(59, 130, 246, 0.5);
        }

        @media (max-width: 640px) {
            .popup {
                padding: 1.5rem;
                max-width: 94%;
            }

            .popup-icon {
                width: 56px;
                height: 56px;
                font-size: 1.75rem;
            }

            .popup-title {
                font-size: 1.3rem;
            }

            .popup a {
                font-size: 0.85rem;
                padding: 0.65rem 0.85rem;
            }

            .writeup-icon {
                width: 36px;
                height: 36px;
                font-size: 1rem;
            }
        }
    `;
    document.head.appendChild(style);

    const overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay';

    const popupDiv = document.createElement('div');
    popupDiv.className = 'popup';

    const closeButton = document.createElement('button');
    closeButton.innerHTML = '&times;';
    closeButton.className = 'modal-close-button';
    closeButton.addEventListener('click', closePopup);

    popupDiv.innerHTML = contenidoPopup;
    popupDiv.appendChild(closeButton);

    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

    setTimeout(() => {
        popupDiv.classList.add('visible');
        overlayDiv.classList.add('visible');
    }, 10);

    overlayDiv.addEventListener('click', (event) => {
        if (event.target === overlayDiv) {
            closePopup();
        }
    });

    function closePopup() {
        popupDiv.classList.remove('visible');
        overlayDiv.classList.remove('visible');
        setTimeout(() => {
            document.body.removeChild(popupDiv);
            document.body.removeChild(overlayDiv);
        }, 300);
    }
}

function showEnlaces(machine) {
    fetch(`/api/writeups/${encodeURIComponent(machine)}`)
        .then(response => {
            if (!response.ok) {
                throw new Error("Error HTTP " + response.status);
            }
            return response.json();
        })
        .then(enlaces => {
            let content = `
                <div class="popup-header">
                    <div class="popup-icon">
                        <i class="bi bi-journal-code" style="color: white;"></i>
                    </div>
                    <h2 class="popup-title">Writeups</h2>
                    <p class="popup-subtitle">${machine}</p>
                </div>
            `;

            if (!enlaces || enlaces.length === 0) {
                content += '<div class="no-writeups">No hay writeups disponibles aún</div>';
            } else {
                content += "<ul>";
                for (let i = 0; i < enlaces.length; i++) {
                    const enlace = enlaces[i];
                    // Check if it's a video type (handle both 'video' string and emoji)
                    const isVideo = enlace.type === 'video' || enlace.type === '🎥';
                    const icono = isVideo ? '🎥' : '📝';
                    const nombre = enlace.name || "Autor desconocido";
                    const url = enlace.url || "#";
                    const clase = enlace.es_usuario_registrado ? "autor-registrado" : "";
                    content += `
                        <li>
                            <div class="writeup-icon">${icono}</div>
                            <a class="${clase}" href="${url}" target="_blank" rel="noopener noreferrer">${nombre}</a>
                        </li>
                    `;
                }
                content += "</ul>";
            }

            createPopup(content);
        })
        .catch(error => {
            console.error('Error loading the links:', error);
            createPopup(`
                <div class="popup-header">
                    <div class="popup-icon">
                        <i class="bi bi-exclamation-triangle" style="color: white;"></i>
                    </div>
                    <h2 class="popup-title">Error</h2>
                </div>
                <div class="no-writeups">Error al cargar los writeups de esta máquina</div>
            `);
        });
}
