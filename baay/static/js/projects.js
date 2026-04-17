/**
 * projects.js — Andd Baay Projects List Page
 * Handles: checkbox selection, delete button activation, search filtering
 */

document.addEventListener('DOMContentLoaded', function () {

    // ===== CHECKBOX SELECTION =====
    const checkboxes = document.querySelectorAll('.project-checkbox');
    const deleteBtn = document.getElementById('deleteBtn');
    const deleteCount = document.getElementById('deleteCount');

    function updateDeleteButton() {
        const checked = document.querySelectorAll('.project-checkbox:checked').length;
        if (deleteCount) deleteCount.textContent = `Supprimer (${checked})`;
        if (deleteBtn) {
            if (checked > 0) {
                deleteBtn.classList.add('active');
            } else {
                deleteBtn.classList.remove('active');
            }
        }
    }

    checkboxes.forEach(function (cb) {
        cb.addEventListener('change', updateDeleteButton);
    });

    // Initialize
    updateDeleteButton();

    // ===== SEARCH FILTER =====
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', function () {
            const query = this.value.toLowerCase().trim();
            const rows = document.querySelectorAll('#projectsTable tr');
            rows.forEach(function (row) {
                const name = (row.dataset.name || '').toLowerCase();
                const culture = (row.dataset.culture || '').toLowerCase();
                const matches = !query || name.includes(query) || culture.includes(query);
                row.style.display = matches ? '' : 'none';
            });
        });
    }

});
