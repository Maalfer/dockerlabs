function createPopup(contenidoPopup) {
    const style = document.createElement('style');
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
            z-index: 9999;
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

        .popup ul {
            list-style: none;
            padding: 0;
            margin: 0;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .popup li {
            display: flex;
            align-items: center;
            padding: 0.5rem;
            border-radius: 6px;
            transition: background 0.1s ease;
        }

        .popup li:hover {
            background: rgba(148, 163, 184, 0.05);
        }

        .writeup-icon {
            font-size: 1.25rem;
            margin-right: 0.75rem;
            color: #cbd5e1;
            display: flex;
            align-items: center;
        }

        .popup a {
            flex: 1;
            color: #e2e8f0;
            text-decoration: none;
            font-size: 0.95rem;
            font-weight: 500;
        }

        .popup a:hover {
            color: #3b82f6;
        }
        
        .autor-registrado {
            color: #fbbf24 !important;
        }
        
        .autor-registrado::before {
            content: "⭐ ";
            font-size: 0.75rem;
            margin-right: 4px;
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

        .report-button {
            background: transparent !important;
            color: #64748b !important;
            font-size: 1rem !important;
            width: 28px !important;
            height: 28px !important;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
            margin-left: 0.5rem;
            opacity: 0.6;
            transition: all 0.2s;
            padding: 0;
            border: none;
            position: static !important;
        }

        .report-button:hover {
            opacity: 1;
            background: rgba(239, 68, 68, 0.1) !important;
            color: #ef4444 !important;
        }

        .no-writeups {
            text-align: center;
            padding: 2rem;
            color: #64748b;
            font-size: 0.9rem;
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
                    <h2 class="popup-title">
                        <i class="bi bi-file-text" style="color: #3b82f6;"></i>
                        Writeups
                    </h2>
                    <p class="popup-subtitle">Recursos disponibles para ${machine}</p>
                </div>
            `;

            if (!enlaces || enlaces.length === 0) {
                content += '<div class="no-writeups">No hay writeups disponibles.</div>';
            } else {
                content += "<ul>";
                for (let i = 0; i < enlaces.length; i++) {
                    const enlace = enlaces[i];
                    const isVideo = enlace.type === 'video' || enlace.type === '🎥';
                    // Use Bootstrap icons instead of emojis for cleaner look
                    const icono = isVideo ? '<i class="bi bi-play-circle-fill"></i>' : '<i class="bi bi-file-earmark-text-fill"></i>';
                    const nombre = enlace.name || "Autor desconocido";
                    const url = enlace.url || "#";
                    const clase = enlace.es_usuario_registrado ? "autor-registrado" : "";
                    const id = enlace.id;

                    content += `
                        <li>
                            <div class="writeup-icon">${icono}</div>
                            <a class="${clase}" href="${url}" target="_blank" rel="noopener noreferrer">${nombre}</a>
                            <button class="report-button" onclick="reportWriteup(${id}); event.stopPropagation();" title="Reportar">
                                <i class="bi bi-flag-fill"></i>
                            </button>
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
                <div class="popup-header" style="border-bottom-color: rgba(239, 68, 68, 0.2);">
                    <h2 class="popup-title" style="color: #ef4444;">
                        <i class="bi bi-exclamation-circle-fill"></i>
                        Error
                    </h2>
                </div>
                <div class="no-writeups">No se pudieron cargar los writeups.</div>
            `);
        });
}

function reportWriteup(writeupId) {
    const reason = prompt("Por favor, indica el motivo del reporte:");
    if (reason === null) return; // Cancelled

    fetch(`/api/writeups/${writeupId}/report`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
        },
        body: JSON.stringify({ reason: reason })
    })
        .then(response => {
            if (response.status === 401) {
                alert("Debes iniciar sesión para reportar un writeup.");
                return;
            }
            return response.json();
        })
        .then(data => {
            if (data && data.message) {
                alert(data.message);
            } else if (data && data.error) {
                alert("Error: " + data.error);
            }
        })
        .catch(error => {
            console.error('Error reporting writeup:', error);
            alert("Hubo un error al enviar el reporte.");
        });
}
