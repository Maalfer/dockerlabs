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
