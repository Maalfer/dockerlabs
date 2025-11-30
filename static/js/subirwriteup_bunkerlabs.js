function subir_flag(nombre) {
    var overlayDiv = document.createElement('div');
    overlayDiv.className = 'overlay';
    overlayDiv.style.position = 'fixed';
    overlayDiv.style.top = '0';
    overlayDiv.style.left = '0';
    overlayDiv.style.width = '100%';
    overlayDiv.style.height = '100%';
    overlayDiv.style.background = 'rgba(26, 27, 38, 0.92)';
    overlayDiv.style.backdropFilter = 'blur(8px)';
    overlayDiv.style.zIndex = '9998';
    overlayDiv.style.opacity = '0';
    overlayDiv.style.transition = 'opacity 0.3s ease';

    var popupDiv = document.createElement('div');
    popupDiv.className = 'popup';
    popupDiv.style.width = 'min(420px, 90vw)';
    popupDiv.style.background = 'linear-gradient(135deg, #24283B 0%, #1A1B26 100%)';
    popupDiv.style.color = '#C0CAF5';
    popupDiv.style.border = '1px solid #7E57C2';
    popupDiv.style.borderRadius = '16px';
    popupDiv.style.boxShadow = '0 20px 60px rgba(0, 0, 0, 0.6), 0 0 30px rgba(126, 87, 194, 0.4)';
    popupDiv.style.position = 'fixed';
    popupDiv.style.top = '50%';
    popupDiv.style.left = '50%';
    popupDiv.style.transform = 'translate(-50%, -50%)';
    popupDiv.style.zIndex = '9999';
    popupDiv.style.padding = '2rem';
    popupDiv.style.textAlign = 'center';
    popupDiv.style.overflowY = 'auto';
    popupDiv.style.transition = 'opacity 0.3s ease, transform 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55)';
    popupDiv.style.opacity = '0';
    popupDiv.style.transform = 'translate(-50%, -60%)';
    popupDiv.style.fontFamily = "'Inter', sans-serif";

    var closeButton = document.createElement('button');
    closeButton.classList.add('modal-close-button');
    closeButton.innerHTML = '&times;';
    closeButton.style.position = 'absolute';
    closeButton.style.top = '1rem';
    closeButton.style.right = '1.2rem';
    closeButton.style.fontSize = '1.8rem';
    closeButton.style.color = '#A9B1D6';
    closeButton.style.cursor = 'pointer';
    closeButton.style.background = 'none';
    closeButton.style.border = 'none';
    closeButton.style.transition = 'all 0.2s ease';
    closeButton.style.width = '36px';
    closeButton.style.height = '36px';
    closeButton.style.borderRadius = '8px';
    closeButton.style.display = 'flex';
    closeButton.style.alignItems = 'center';
    closeButton.style.justifyContent = 'center';
    closeButton.addEventListener('mouseover', function () {
        this.style.color = '#B39DDB';
        this.style.background = 'rgba(126, 87, 194, 0.15)';
        this.style.transform = 'scale(1.1)';
    });
    closeButton.addEventListener('mouseout', function () {
        this.style.color = '#A9B1D6';
        this.style.background = 'none';
        this.style.transform = 'scale(1)';
    });
    closeButton.addEventListener('click', function () {
        closePopup();
    });

    // Icon
    var iconDiv = document.createElement('div');
    iconDiv.style.width = '64px';
    iconDiv.style.height = '64px';
    iconDiv.style.margin = '0 auto 1.5rem';
    iconDiv.style.background = 'linear-gradient(135deg, #7E57C2, #5E35B1)';
    iconDiv.style.borderRadius = '16px';
    iconDiv.style.display = 'flex';
    iconDiv.style.alignItems = 'center';
    iconDiv.style.justifyContent = 'center';
    iconDiv.style.fontSize = '2rem';
    iconDiv.style.boxShadow = '0 0 30px rgba(126, 87, 194, 0.5)';
    iconDiv.innerHTML = '<i class="bi bi-flag-fill" style="color: white;"></i>';

    // Title
    var titulo = document.createElement('h2');
    titulo.textContent = `Introduce la Flag`;
    titulo.style.marginBottom = '0.5rem';
    titulo.style.fontSize = '1.5rem';
    titulo.style.fontWeight = '700';
    titulo.style.background = 'linear-gradient(135deg, #9575CD, #B39DDB)';
    titulo.style.webkitBackgroundClip = 'text';
    titulo.style.backgroundClip = 'text';
    titulo.style.webkitTextFillColor = 'transparent';
    titulo.style.letterSpacing = '0.02em';

    // Subtitle
    var subtitulo = document.createElement('p');
    subtitulo.textContent = nombre;
    subtitulo.style.marginBottom = '2rem';
    subtitulo.style.fontSize = '0.95rem';
    subtitulo.style.color = '#787C99';
    subtitulo.style.fontWeight = '500';

    // Input wrapper
    var inputWrapper = document.createElement('div');
    inputWrapper.style.position = 'relative';
    inputWrapper.style.marginBottom = '1.5rem';

    // Input
    var inputPin = document.createElement('input');
    inputPin.id = 'pin';
    inputPin.type = 'text';
    inputPin.placeholder = 'Introduce el PIN/Flag';
    inputPin.style.width = '100%';
    inputPin.style.padding = '1rem 1.2rem';
    inputPin.style.border = '1px solid #414868';
    inputPin.style.background = '#2A2E3F';
    inputPin.style.color = '#C0CAF5';
    inputPin.style.borderRadius = '12px';
    inputPin.style.fontSize = '1rem';
    inputPin.style.outline = 'none';
    inputPin.style.transition = 'all 0.3s ease';
    inputPin.style.fontFamily = "'Fira Code', monospace";
    inputPin.addEventListener('focus', function () {
        this.style.borderColor = '#7E57C2';
        this.style.boxShadow = '0 0 0 3px rgba(126, 87, 194, 0.2)';
        this.style.background = '#24283B';
    });
    inputPin.addEventListener('blur', function () {
        this.style.borderColor = '#414868';
        this.style.boxShadow = 'none';
        this.style.background = '#2A2E3F';
    });

    inputWrapper.appendChild(inputPin);

    // Button
    var enviarButton = document.createElement('button');
    enviarButton.id = 'enviarButton';
    enviarButton.textContent = 'Enviar Flag';
    enviarButton.style.width = '100%';
    enviarButton.style.padding = '1rem';
    enviarButton.style.border = 'none';
    enviarButton.style.background = 'linear-gradient(135deg, #7E57C2, #5E35B1)';
    enviarButton.style.color = 'white';
    enviarButton.style.fontSize = '1rem';
    enviarButton.style.fontWeight = '600';
    enviarButton.style.cursor = 'pointer';
    enviarButton.style.borderRadius = '12px';
    enviarButton.style.transition = 'all 0.3s ease';
    enviarButton.style.boxShadow = '0 4px 15px rgba(126, 87, 194, 0.3)';
    enviarButton.style.letterSpacing = '0.03em';
    enviarButton.addEventListener('mouseover', function () {
        this.style.background = 'linear-gradient(135deg, #9575CD, #7E57C2)';
        this.style.transform = 'translateY(-2px)';
        this.style.boxShadow = '0 6px 25px rgba(126, 87, 194, 0.5)';
    });
    enviarButton.addEventListener('mouseout', function () {
        this.style.background = 'linear-gradient(135deg, #7E57C2, #5E35B1)';
        this.style.transform = 'translateY(0)';
        this.style.boxShadow = '0 4px 15px rgba(126, 87, 194, 0.3)';
    });

    popupDiv.appendChild(closeButton);
    popupDiv.appendChild(iconDiv);
    popupDiv.appendChild(titulo);
    popupDiv.appendChild(subtitulo);
    popupDiv.appendChild(inputWrapper);
    popupDiv.appendChild(enviarButton);
    document.body.appendChild(overlayDiv);
    document.body.appendChild(popupDiv);

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

    function closePopup() {
        popupDiv.style.opacity = '0';
        popupDiv.style.transform = 'translate(-50%, -60%)';
        overlayDiv.style.opacity = '0';
        setTimeout(function () {
            document.body.removeChild(popupDiv);
            document.body.removeChild(overlayDiv);
        }, 300);
    }

    document.getElementById('enviarButton').addEventListener('click', function () {
        let pin = document.getElementById('pin').value;

        let csrfToken = document.querySelector('meta[name="csrf-token"]').content;

        fetch('/subir-flag', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ maquina: nombre, pin: pin })
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(`Error: ${data.error}`);
                } else {
                    alert(data.message);
                    closePopup();
                }
            })
            .catch(error => {
                alert('Error al enviar la flag.');
                console.error(error);
            });
    });
}
