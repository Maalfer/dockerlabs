/**
 * Escape HTML to prevent XSS attacks.
 * @param {string} text - Text to escape
 * @returns {string} Escaped HTML-safe string
 */
function escapeHtml(text) {
    if (text == null || text === '') return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Get CSRF token from meta tag or input field.
 * @returns {string} CSRF token or empty string
 */
function getCsrfToken() {
    // Try meta tag first (used in most pages)
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');
    
    // Fallback to input field (used in some forms)
    const input = document.querySelector('input[name="csrf_token"]');
    if (input) return input.value;
    
    return '';
}

/**
 * Open a modal by adding the 'visible' class.
 * @param {string} modalId - The ID of the modal element
 */
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('visible');
}

/**
 * Close a modal by removing the 'visible' class.
 * @param {string} modalId - The ID of the modal element
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('visible');
}

/**
 * Initialize click-outside-to-close behavior for a modal.
 * @param {string} modalId - The ID of the modal element
 */
function initModalCloseOnClickOutside(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.addEventListener('click', function (e) {
            if (e.target === modal) closeModal(modalId);
        });
    }
}
