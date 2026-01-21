document.addEventListener('DOMContentLoaded', function () {
    initializeDashboard();
});

function initializeDashboard() {
    const newPasswordInput = document.getElementById('newPassword');
    if (newPasswordInput) {
        newPasswordInput.addEventListener('input', updatePasswordStrength);
    }

    const btn = document.getElementById('btnChangePassword');
    if (btn) {
        btn.addEventListener('click', changePassword);
    }


    loadProfileData();

}

function cancelEdit() {
    resetForm();
}

function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

function handlePhotoUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
        showAlert('Por favor, selecciona una imagen válida.', 'error');
        return;
    }

    if (file.size > 5 * 1024 * 1024) {
        showAlert('La imagen no debe superar los 5MB.', 'error');
        return;
    }

    const reader = new FileReader();
    reader.onload = function (e) {
        const profilePicture = document.getElementById('profilePicture');
        if (profilePicture) profilePicture.src = e.target.result;
    };
    reader.readAsDataURL(file);

    const formData = new FormData();
    formData.append('photo', file);

    const csrfToken = getCsrfToken();

    showAlert('Subiendo foto de perfil...', 'info');

    fetch('/upload-profile-photo', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
        .then(response => response.json().then(data => ({ ok: response.ok, data })))
        .then(result => {
            if (!result.ok) {
                showAlert(result.data.error || 'Error al subir la foto.', 'error');
                return;
            }

            if (result.data.image_url) {
                const profilePicture = document.getElementById('profilePicture');
                if (profilePicture) profilePicture.src = result.data.image_url;
            }

            showAlert(result.data.message || 'Foto actualizada correctamente.', 'success');
        })
        .catch(() => {
            showAlert('Se produjo un error al subir la foto.', 'error');
        });
}

function enableEdit(fieldId) {
    const input = document.getElementById(fieldId);
    const editButton = input.nextElementSibling;
    if (input.disabled) {
        input.disabled = false;
        input.focus();
        editButton.innerHTML = '<i class="bi bi-check-lg"></i>';
        editButton.onclick = function () { saveField(fieldId); };
    }
}

function saveField(fieldId) {
    const input = document.getElementById(fieldId);
    const editButton = input.nextElementSibling;

    if (!input.value.trim()) {
        showAlert('Este campo no puede estar vacío.', 'error');
        input.focus();
        return;
    }

    if (fieldId === 'email') {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(input.value)) {
            showAlert('Por favor, ingresa un email válido.', 'error');
            input.focus();
            return;
        }
    }

    showAlert(`Campo ${fieldId} actualizado correctamente.`, 'success');

    input.disabled = true;
    editButton.innerHTML = '<i class="bi bi-pencil"></i>';
    editButton.onclick = function () { enableEdit(fieldId); };
}

function saveProfile() {
    // Only validate the profile fields (username and email), not the requested_username field
    const username = document.getElementById('username');
    const email = document.getElementById('email');
    let hasErrors = false;

    // Validate username if not disabled
    if (username && !username.disabled && !username.value.trim()) {
        showAlert('El campo de nombre de usuario no puede estar vacío.', 'error');
        hasErrors = true;
        username.focus();
        return;
    }

    // Validate email if not disabled
    if (email && !email.disabled) {
        if (!email.value.trim()) {
            showAlert('El campo de correo electrónico no puede estar vacío.', 'error');
            hasErrors = true;
            email.focus();
            return;
        }
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email.value)) {
            showAlert('Por favor, ingresa un email válido.', 'error');
            hasErrors = true;
            email.focus();
            return;
        }
    }

    if (hasErrors) return;

    const bio = document.getElementById('bio').value;
    const csrf = getCsrfToken();

    // Get social media links
    const linkedinUrl = document.getElementById('linkedin_url').value.trim();
    const githubUrl = document.getElementById('github_url').value.trim();
    const youtubeUrl = document.getElementById('youtube_url').value.trim();

    // Validate Social Media Links
    const linkedinRegex = /^https:\/\/(www\.)?linkedin\.com\/.*$/;
    const githubRegex = /^https:\/\/(www\.)?github\.com\/.*$/;
    const youtubeRegex = /^https:\/\/(www\.)?(youtube\.com|youtu\.be)\/.*$/;

    // SECURITY: Check for dangerous characters that could be used for XSS
    const dangerousChars = ['"', "'", '<', '>', '`'];

    function containsDangerousChars(url) {
        for (let char of dangerousChars) {
            if (url.includes(char)) {
                return char;
            }
        }
        return null;
    }

    if (linkedinUrl) {
        const dangerousChar = containsDangerousChars(linkedinUrl);
        if (dangerousChar) {
            showAlert(`La URL de LinkedIn contiene un carácter no permitido: ${dangerousChar}`, 'error');
            return;
        }
        if (!linkedinRegex.test(linkedinUrl)) {
            showAlert('La URL de LinkedIn debe ser válida (https://linkedin.com/...)', 'error');
            return;
        }
    }

    if (githubUrl) {
        const dangerousChar = containsDangerousChars(githubUrl);
        if (dangerousChar) {
            showAlert(`La URL de GitHub contiene un carácter no permitido: ${dangerousChar}`, 'error');
            return;
        }
        if (!githubRegex.test(githubUrl)) {
            showAlert('La URL de GitHub debe ser válida (https://github.com/...)', 'error');
            return;
        }
    }

    if (youtubeUrl) {
        const dangerousChar = containsDangerousChars(youtubeUrl);
        if (dangerousChar) {
            showAlert(`La URL de YouTube contiene un carácter no permitido: ${dangerousChar}`, 'error');
            return;
        }
        if (!youtubeRegex.test(youtubeUrl)) {
            showAlert('La URL de YouTube debe ser válida (https://youtube.com/... o https://youtu.be/...)', 'error');
            return;
        }
    }

    showAlert('Guardando perfil...', 'info');

    // Save biography
    fetch('/api/update_profile', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf
        },
        body: JSON.stringify({
            biography: bio
        })
    })
        .then(r => r.json().then(data => ({ ok: r.ok, data })))
        .then(result => {
            if (!result.ok) {
                showAlert(result.data.error || 'Error al actualizar el perfil.', 'error');
                return Promise.reject('Biography update failed');
            }

            // Now save social links
            return fetch('/api/update_social_links', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrf
                },
                body: JSON.stringify({
                    linkedin_url: linkedinUrl,
                    github_url: githubUrl,
                    youtube_url: youtubeUrl
                })
            });
        })
        .then(r => r.json().then(data => ({ ok: r.ok, data })))
        .then(result => {
            if (!result.ok) {
                showAlert(result.data.error || 'Error al actualizar enlaces sociales.', 'error');
                return;
            }

            showAlert('Perfil y enlaces actualizados correctamente.', 'success');
        })
        .catch((error) => {
            if (error !== 'Biography update failed') {
                showAlert('Error de conexión al actualizar el perfil.', 'error');
            }
        });
}

function resetForm() {
    // Simply reload the page to reset the biography to its original value
    location.reload();
}

function updatePasswordStrength() {
    const password = document.getElementById('newPassword').value;
    const strengthBar = document.querySelector('.strength-bar');
    const strengthText = document.querySelector('.strength-text');

    let strength = 0;
    let color = '#ef4444';
    let text = 'Débil';

    if (password.length >= 8) strength += 25;
    if (/[A-Z]/.test(password)) strength += 25;
    if (/[0-9]/.test(password)) strength += 25;
    if (/[^A-Za-z0-9]/.test(password)) strength += 25;

    strengthBar.style.width = strength + '%';

    if (strength >= 75) {
        color = '#10b981';
        text = 'Fuerte';
    } else if (strength >= 50) {
        color = '#f59e0b';
        text = 'Media';
    }

    strengthBar.style.background = color;
    strengthText.textContent = `Seguridad: ${text}`;
    strengthText.style.color = color;

    updatePasswordRequirements(password);
}

function updatePasswordRequirements(password) {
    const requirements = document.querySelectorAll('.requirement');

    requirements[0].innerHTML = password.length >= 8 ?
        '<i class="bi bi-check-circle" style="color: #10b981;"></i> Mínimo 8 caracteres' :
        '<i class="bi bi-dash-circle"></i> Mínimo 8 caracteres';

    requirements[1].innerHTML = /[A-Z]/.test(password) ?
        '<i class="bi bi-check-circle" style="color: #10b981;"></i> Al menos una mayúscula' :
        '<i class="bi bi-dash-circle"></i> Al menos una mayúscula';

    requirements[2].innerHTML = /[0-9]/.test(password) ?
        '<i class="bi bi-check-circle" style="color: #10b981;"></i> Al menos un número' :
        '<i class="bi bi-dash-circle"></i> Al menos un número';

    requirements[3].innerHTML = /[^A-Za-z0-9]/.test(password) ?
        '<i class="bi bi-check-circle" style="color: #10b981;"></i> Al menos un carácter especial' :
        '<i class="bi bi-dash-circle"></i> Al menos un carácter especial';
}

function changePassword() {
    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;

    if (!currentPassword || !newPassword || !confirmPassword) {
        showAlert('Todos los campos son obligatorios.', 'error');
        return;
    }

    if (newPassword !== confirmPassword) {
        showAlert('Las contraseñas nuevas no coinciden.', 'error');
        return;
    }

    let strength = 0;
    if (newPassword.length >= 8) strength += 25;
    if (/[A-Z]/.test(newPassword)) strength += 25;
    if (/[0-9]/.test(newPassword)) strength += 25;
    if (/[^A-Za-z0-9]/.test(newPassword)) strength += 25;

    if (strength < 75) {
        showAlert('La contraseña no cumple con los requisitos de seguridad.', 'error');
        return;
    }

    const csrf = getCsrfToken();

    showAlert('Cambiando contraseña...', 'info');

    fetch('/api/change_password', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf
        },
        body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword
        })
    })
        .then(r => r.json().then(data => ({ ok: r.ok, data })))
        .then(result => {
            if (!result.ok) {
                showAlert(result.data.error || 'Error al cambiar la contraseña.', 'error');
                return;
            }

            document.getElementById('currentPassword').value = '';
            document.getElementById('newPassword').value = '';
            document.getElementById('confirmPassword').value = '';
            updatePasswordStrength();

            showAlert(result.data.message || 'Contraseña actualizada correctamente.', 'success');
        })
        .catch(() => {
            showAlert('Error de conexión al cambiar la contraseña.', 'error');
        });
}

function showAlert(message, type = 'info') {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alert.style.cssText = `
        top: 100px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        backdrop-filter: blur(10px);
    `;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alert);
    setTimeout(() => {
        if (alert.parentNode) alert.remove();
    }, 5000);
}

function loadProfileData() {
    console.log('Cargando datos del perfil...');
}

function openClaimMachineModal() {
    const modal = document.getElementById('claimMachineModal');
    if (modal) modal.classList.add('visible');
}

function closeClaimMachineModal() {
    const modal = document.getElementById('claimMachineModal');
    if (modal) modal.classList.remove('visible');
}

document.addEventListener('DOMContentLoaded', function () {
    const claimModal = document.getElementById('claimMachineModal');
    if (claimModal) {
        claimModal.addEventListener('click', function (e) {
            if (e.target === claimModal) closeClaimMachineModal();
        });
    }
});
