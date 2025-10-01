// Main JavaScript file for AIZEVA

// CSRF Token helper
function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

// Add CSRF token to HTMX requests
document.body.addEventListener('htmx:configRequest', function(evt) {
    evt.detail.headers['X-CSRF-Token'] = getCSRFToken();
});

// Quill.js initialization
function initializeQuillEditor(selector, placeholder = '내용을 입력하세요...') {
    if (document.querySelector(selector)) {
        return new Quill(selector, {
            theme: 'snow',
            placeholder: placeholder,
            modules: {
                toolbar: [
                    [{ 'header': [1, 2, 3, false] }],
                    ['bold', 'italic', 'underline', 'strike'],
                    [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                    ['blockquote', 'code-block'],
                    ['link'],
                    ['clean']
                ]
            }
        });
    }
    return null;
}

// Mobile menu toggle
function toggleMobileMenu() {
    const menu = document.getElementById('mobile-menu');
    if (menu) {
        menu.classList.toggle('hidden');
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Quill editor if present
    initializeQuillEditor('#editor');
    
    // HTMX success/error handlers
    document.body.addEventListener('htmx:afterRequest', function(evt) {
        if (evt.detail.successful) {
            // Success handling
            const alerts = document.querySelectorAll('.alert-success');
            alerts.forEach(alert => {
                setTimeout(() => alert.remove(), 5000);
            });
        } else {
            // Error handling
            console.error('HTMX request failed:', evt.detail);
        }
    });
});