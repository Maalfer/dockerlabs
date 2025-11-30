function ranking() {
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

    // Crear el botón de cierre
    var closeButton = document.createElement('button');
    closeButton.innerHTML = '&times;';
    closeButton.classList.add('modal-close-button');
    closeButton.addEventListener('click', function () {
        closePopup();
    });

    // Crear el contenido base del popup (cabecera)
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
                Puntos por máquinas
            </p>
        </div>
        <hr style="border: 0; border-top: 1px solid rgba(51,65,85,0.9); margin: 10px 0 14px;">
    `;

    // Cargar el ranking desde la API
    fetch('/api/bunker-ranking')
        .then(response => {
            if (!response.ok) {
                throw new Error('No se pudo cargar el archivo JSON');
            }
            return response.json();
        })
        .then(data => {
            // Ordenar los datos de mayor a menor puntuación
            data.sort((a, b) => b.puntos - a.puntos);

            // Crear la lista de clasificación
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
                // Determinar el color del puesto
                let color = 'var(--text-secondary)'; // Color por defecto
                if (index === 0) color = 'gold';        // 🥇 1º lugar
                else if (index === 1) color = 'silver'; // 🥈 2º lugar
                else if (index === 2) color = '#cd7f32'; // 🥉 3º lugar

                // Medallas top 3
                let medal = '';
                if (index === 0) medal = '🥇';
                else if (index === 1) medal = '🥈';
                else if (index === 2) medal = '🥉';

                // Posición (1º, 2º, 3º, etc.)
                let positionSuffix = (index + 1) + 'º';

                rankingList += `
                    <li style="
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
                    ">
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

            // Añadir la lista al contenido del popup
            contenidoPopup += rankingList;
            popupDiv.innerHTML = contenidoPopup;
            popupDiv.appendChild(closeButton);
        })
        .catch(error => {
            console.error('Error al cargar el archivo JSON:', error);
            contenidoPopup += '<p style="margin: 0; font-size: 0.85rem; color: var(--accent-red); text-align: center;">Error al cargar el ranking.</p>';
            popupDiv.innerHTML = contenidoPopup;
            popupDiv.appendChild(closeButton);
        });

    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

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


function rankingautores() {
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

    // Crear el botón de cierre
    var closeButton = document.createElement('button');
    closeButton.innerHTML = '&times;';
    closeButton.classList.add('modal-close-button');
    closeButton.addEventListener('click', function () {
        closePopup();
    });

    // Crear el contenido base del popup (cabecera)
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
        <hr style="border: 0; border-top: 1px solid rgba(51,65,85,0.9); margin: 10px 0 14px;">
    `;

    // Cargar el archivo JSON desde Flask (dentro de la carpeta static)
    fetch('/static/ranking_creadores.json')
        .then(response => {
            if (!response.ok) {
                throw new Error('No se pudo cargar el archivo JSON');
            }
            return response.json();
        })
        .then(data => {
            // Ordenar los datos de mayor a menor número de máquinas creadas
            data.sort((a, b) => b.maquinas - a.maquinas);

            // Crear la lista de clasificación
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
                // Determinar el color del puesto
                let color = 'var(--text-secondary)'; // Color por defecto
                if (index === 0) color = 'gold';        // 🥇 1º lugar
                else if (index === 1) color = 'silver'; // 🥈 2º lugar
                else if (index === 2) color = '#cd7f32'; // 🥉 3º lugar

                // Medallas top 3
                let medal = '';
                if (index === 0) medal = '🥇';
                else if (index === 1) medal = '🥈';
                else if (index === 2) medal = '🥉';

                // Posición (1º, 2º, 3º, etc.)
                let positionSuffix = (index + 1) + 'º';

                rankingList += `
                    <li style="
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
                    ">
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

            // Añadir la lista al contenido del popup
            contenidoPopup += rankingList;
            popupDiv.innerHTML = contenidoPopup;
            popupDiv.appendChild(closeButton);
        })
        .catch(error => {
            console.error('Error al cargar el archivo JSON:', error);
            contenidoPopup += '<p style="margin: 0; font-size: 0.85rem; color: var(--accent-red); text-align: center;">Error al cargar el ranking.</p>';
            popupDiv.innerHTML = contenidoPopup;
            popupDiv.appendChild(closeButton);
        });

    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

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
