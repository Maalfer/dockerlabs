function subir_flag(machineName) {
    const styleId = 'bunker-flag-styles';
    if (!document.getElementById(styleId)) {
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            .bunker-flag-overlay {
                position: fixed;
                top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(13, 12, 28, 0.85);
                backdrop-filter: blur(8px);
                z-index: 10000;
                opacity: 0;
                transition: opacity 0.2s ease;
            }
            .bunker-flag-overlay.visible { opacity: 1; }

            .bunker-flag-popup {
                position: fixed;
                top: 50%; left: 50%;
                transform: translate(-50%, -48%) scale(0.98);
                width: min(400px, 90vw);
                padding: 2.2rem;
                background: linear-gradient(145deg, rgba(20, 18, 41, 0.98), rgba(13, 12, 28, 0.99));
                border: 1px solid rgba(139, 92, 246, 0.3);
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8), 0 0 30px rgba(139, 92, 246, 0.15);
                border-radius: 16px;
                z-index: 10001;
                color: #e2e8f0;
                font-family: 'Inter', sans-serif;
                opacity: 0;
                transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            }
            .bunker-flag-popup.visible { opacity: 1; transform: translate(-50%, -50%) scale(1); }

            .bunker-flag-title {
                margin: 0 0 1.2rem;
                font-size: 1.4rem;
                font-weight: 800;
                text-align: center;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                background: linear-gradient(135deg, #fff 0%, #a78bfa 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }

            .bunker-flag-input {
                width: 100%;
                padding: 0.9rem 1.1rem;
                background: rgba(15, 23, 42, 0.6);
                border: 1px solid rgba(139, 92, 246, 0.2);
                border-radius: 10px;
                color: #fff;
                font-size: 1rem;
                margin-bottom: 1.5rem;
                outline: none;
                transition: all 0.2s;
                text-align: center;
                letter-spacing: 0.05em;
            }
            .bunker-flag-input:focus { 
                border-color: rgba(167, 139, 250, 0.6); 
                box-shadow: 0 0 15px rgba(167, 139, 250, 0.15);
                background: rgba(15, 23, 42, 0.8);
            }

            .bunker-flag-btn {
                width: 100%;
                padding: 0.9rem;
                background: linear-gradient(135deg, #7c3aed, #4f46e5);
                border: none;
                border-radius: 10px;
                color: #fff;
                font-weight: 700;
                cursor: pointer;
                transition: all 0.2s;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }
            .bunker-flag-btn:hover { 
                transform: translateY(-2px); 
                box-shadow: 0 8px 20px rgba(124, 58, 237, 0.4); 
                filter: brightness(1.1);
            }
            .bunker-flag-btn:active { transform: translateY(0); }

            .bunker-flag-close {
                position: absolute;
                top: 1rem; right: 1rem;
                background: transparent; border: none;
                color: rgba(255,255,255,0.3);
                font-size: 1.8rem; cursor: pointer;
                line-height: 1;
                transition: color 0.2s;
            }
            .bunker-flag-close:hover { color: #fff; }
        `;
        document.head.appendChild(style);
    }

    const overlay = document.createElement('div');
    overlay.className = 'bunker-flag-overlay';
    const popup = document.createElement('div');
    popup.className = 'bunker-flag-popup';

    popup.innerHTML = `
        <button class="bunker-flag-close">&times;</button>
        <h2 class="bunker-flag-title">Subir Flag</h2>
        <p style="font-size: 0.95rem; color: #94a3b8; margin-bottom: 1.5rem; text-align: center; line-height: 1.5;">
            Introduce el PIN obtenido en la máquina:<br><strong style="color: #e2e8f0;">${machineName}</strong>
        </p>
        <input type="text" class="bunker-flag-input" placeholder="PIN de Acceso" id="flagInput" autofocus>
        <button class="bunker-flag-btn" id="submitFlag">Validar Flag</button>
    `;

    document.body.appendChild(overlay);
    document.body.appendChild(popup);

    setTimeout(() => {
        overlay.classList.add('visible');
        popup.classList.add('visible');
    }, 10);

    const close = () => {
        overlay.classList.remove('visible');
        popup.classList.remove('visible');
        setTimeout(() => {
            if (overlay.parentNode) document.body.removeChild(overlay);
            if (popup.parentNode) document.body.removeChild(popup);
        }, 200);
    };

    popup.querySelector('.bunker-flag-close').onclick = close;
    overlay.onclick = (e) => { if (e.target === overlay) close(); };

    const handleSubir = () => {
        const pin = document.getElementById('flagInput').value.trim();
        if (!pin) return;

        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

        fetch('/bunkerlabs/subir-flag', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ maquina: machineName, pin: pin })
        })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                } else {
                    alert(data.message);
                    if (data.message.includes("correcta")) {
                        close();
                        location.reload();
                    }
                }
            })
            .catch(err => {
                console.error(err);
                alert("Error al enviar la flag.");
            });
    };

    popup.querySelector('#submitFlag').onclick = handleSubir;
    popup.querySelector('#flagInput').onkeypress = (e) => {
        if (e.key === 'Enter') handleSubir();
    };
}
