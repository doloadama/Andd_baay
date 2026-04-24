// ===== GLOBAL STATE =====
const projectsData = [];
let selectedProjects = new Set();
let currentSort = { column: null, direction: 'asc' };
let currentFilter = 'all';
let searchQuery = '';
let contextMenuProjectId = null;

document.addEventListener('DOMContentLoaded', function() {
    // Collect project data
    document.querySelectorAll('#projectsTable tr[data-id]').forEach(row => {
        projectsData.push({
            id: row.dataset.id,
            name: row.dataset.name,
            culture: row.dataset.culture,
            status: row.dataset.status,
            superficie: parseFloat(row.dataset.superficie) || 0,
            date: row.dataset.date
        });
    });
    
    // Initialize features
    initSearch();
    initVoiceSearch();
    initFilters();
    initSorting();
    initBulkActions();
    initKeyboardShortcuts();
    initViewToggle();
    initContextMenu();
    initInlineEditing();
    
    // Sticky actions bar on scroll
    initStickyActions();
    
    // Close dropdowns on outside click
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.quick-actions')) {
            document.querySelectorAll('.quick-actions-menu').forEach(menu => {
                menu.classList.remove('active');
            });
        }
        document.getElementById('contextMenu').classList.remove('active');
    });
    
    // Escape key closes modals/menus
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeQuickView();
            document.getElementById('contextMenu').classList.remove('active');
            document.querySelectorAll('.quick-actions-menu').forEach(menu => {
                menu.classList.remove('active');
            });
        }
    });
});

// ===== SEARCH =====
function initSearch() {
    const searchInput = document.getElementById('searchInput');
    const clearBtn = document.getElementById('clearSearch');
    let searchTimeout;
    
    searchInput?.addEventListener('input', function() {
        searchQuery = this.value.toLowerCase().trim();
        
        // Show/hide clear button
        if (clearBtn) {
            clearBtn.style.display = searchQuery ? 'block' : 'none';
        }
        
        // Debounce search
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            filterProjects();
        }, 300);
    });
    
    clearBtn?.addEventListener('click', function() {
        searchInput.value = '';
        searchQuery = '';
        this.style.display = 'none';
        searchInput.focus();
        filterProjects();
    });
}

// ===== VOICE SEARCH =====
function initVoiceSearch() {
    const voiceBtn = document.getElementById('voiceSearch');
    if (!voiceBtn || !('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
        if (voiceBtn) voiceBtn.style.display = 'none';
        return;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = 'fr-FR';
    recognition.continuous = false;
    
    voiceBtn.addEventListener('click', function() {
        if (this.classList.contains('listening')) {
            recognition.stop();
            return;
        }
        
        this.classList.add('listening');
        showToast('🎤 Écoute en cours...', 'info');
        
        recognition.start();
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            document.getElementById('searchInput').value = transcript;
            searchQuery = transcript.toLowerCase();
            filterProjects();
            showToast(`🔍 "${transcript}"`, 'success');
        };
        
        recognition.onerror = function() {
            showToast('❌ Erreur de reconnaissance', 'error');
        };
        
        recognition.onend = function() {
            voiceBtn.classList.remove('listening');
        };
    });
}

// ===== FILTERS =====
function initFilters() {
    document.querySelectorAll('.filter-chip').forEach(chip => {
        chip.addEventListener('click', function() {
            // Update active state
            document.querySelectorAll('.filter-chip').forEach(c => c.dataset.active = 'false');
            this.dataset.active = 'true';
            
            currentFilter = this.dataset.filter;
            filterProjects();
            showToast(`Filtre: ${this.textContent}`, 'info');
        });
    });
}

// ===== SORTING =====
function initSorting() {
    document.querySelectorAll('th.sortable').forEach(th => {
        th.addEventListener('click', function() {
            const column = this.dataset.sort;
            
            // Toggle direction
            if (currentSort.column === column) {
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.column = column;
                currentSort.direction = 'asc';
            }
            
            // Update visual indicators
            document.querySelectorAll('th.sortable').forEach(t => {
                t.classList.remove('sort-asc', 'sort-desc');
            });
            this.classList.add(currentSort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
            
            sortProjects();
        });
    });
}

function sortProjects() {
    if (!currentSort.column) return;
    
    const sorted = [...projectsData].sort((a, b) => {
        let valA = a[currentSort.column];
        let valB = b[currentSort.column];
        
        if (currentSort.column === 'date') {
            valA = new Date(valA);
            valB = new Date(valB);
        }
        
        if (valA < valB) return currentSort.direction === 'asc' ? -1 : 1;
        if (valA > valB) return currentSort.direction === 'asc' ? 1 : -1;
        return 0;
    });
    
    // Reorder DOM rows
    const tbody = document.getElementById('projectsTable');
    sorted.forEach(project => {
        const row = tbody.querySelector(`tr[data-id="${project.id}"]`);
        if (row) tbody.appendChild(row);
    });
    
    showToast(`Trié par ${currentSort.column}`, 'info');
}

// ===== FILTER PROJECTS =====
function filterProjects() {
    const rows = document.querySelectorAll('#projectsTable tr[data-id]');
    const cards = document.querySelectorAll('.project-card');
    
    rows.forEach(row => {
        const name = row.dataset.name;
        const culture = row.dataset.culture;
        const status = row.dataset.status;
        
        const matchesSearch = !searchQuery || 
            name.includes(searchQuery) || 
            culture.includes(searchQuery);
        const matchesFilter = currentFilter === 'all' || status === currentFilter;
        
        row.style.display = (matchesSearch && matchesFilter) ? '' : 'none';
    });
    
    cards.forEach(card => {
        const name = card.dataset.name;
        const culture = card.dataset.culture;
        const status = card.dataset.status;
        
        const matchesSearch = !searchQuery || 
            name.includes(searchQuery) || 
            culture.includes(searchQuery);
        const matchesFilter = currentFilter === 'all' || status === currentFilter;
        
        card.style.display = (matchesSearch && matchesFilter) ? '' : 'none';
    });
}

// ===== BULK ACTIONS =====
function initBulkActions() {
    // Select all checkbox
    const selectAll = document.getElementById('selectAll');
    selectAll?.addEventListener('change', function() {
        const visibleCheckboxes = document.querySelectorAll('#projectsTable tr:not([style*="display: none"]) .project-checkbox');
        visibleCheckboxes.forEach(cb => {
            cb.checked = this.checked;
            toggleRowSelection(cb.closest('tr'), this.checked);
        });
        updateDeleteButton();
    });
    
    // Individual checkboxes
    document.querySelectorAll('.project-checkbox').forEach(cb => {
        cb.addEventListener('change', function() {
            toggleRowSelection(this.closest('tr'), this.checked);
            updateDeleteButton();
        });
    });
    
    // Delete button
    document.getElementById('deleteBtn')?.addEventListener('click', function(e) {
        if (selectedProjects.size === 0) {
            e.preventDefault();
            showToast('Sélectionnez des projets à supprimer', 'error');
            return false;
        }
        return confirm(`Supprimer ${selectedProjects.size} projet(s) ? Cette action est irréversible.`);
    });
}

function toggleRowSelection(row, selected) {
    if (!row) return;
    const id = row.dataset.id;
    
    if (selected) {
        selectedProjects.add(id);
        row.classList.add('selected');
    } else {
        selectedProjects.delete(id);
        row.classList.remove('selected');
    }
}

function toggleCardSelection(event, id) {
    event.stopPropagation();
    const card = event.currentTarget.closest('.project-card');
    const checkbox = card.querySelector('.project-card-checkbox');
    checkbox.classList.toggle('checked');
    
    if (checkbox.classList.contains('checked')) {
        selectedProjects.add(id);
        card.classList.add('selected');
    } else {
        selectedProjects.delete(id);
        card.classList.remove('selected');
    }
    updateDeleteButton();
}

function updateDeleteButton() {
    const btn = document.getElementById('deleteBtn');
    const count = document.getElementById('deleteCount');
    const num = selectedProjects.size;
    
    if (num > 0) {
        btn.classList.add('active');
        count.textContent = `Supprimer (${num})`;
    } else {
        btn.classList.remove('active');
        count.textContent = 'Supprimer (0)';
    }
}

// ===== INLINE EDITING =====
function initInlineEditing() {
    document.querySelectorAll('.project-name-cell.editable').forEach(cell => {
        cell.addEventListener('dblclick', function(e) {
            e.stopPropagation();
            startInlineEdit(this);
        });
    });
}

function startInlineEdit(cell) {
    if (cell.classList.contains('editing')) return;
    
    const id = cell.dataset.id;
    const original = cell.dataset.original;
    const currentText = cell.textContent.trim();
    
    cell.classList.add('editing');
    cell.innerHTML = `<input type="text" class="project-name-input" value="${currentText}" data-id="${id}">`;
    
    const input = cell.querySelector('input');
    input.focus();
    input.select();
    
    const saveEdit = () => {
        const newValue = input.value.trim();
        if (newValue && newValue !== original) {
            cell.textContent = newValue;
            cell.dataset.original = newValue;
            
            // Here you would make an API call to save
            // saveProjectName(id, newValue);
            
            showToast('Nom mis à jour ✓', 'success');
        } else {
            cell.textContent = original;
        }
        cell.classList.remove('editing');
    };
    
    input.addEventListener('blur', saveEdit);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            input.blur();
        }
        if (e.key === 'Escape') {
            cell.textContent = original;
            cell.classList.remove('editing');
        }
    });
}

// ===== STATUS DROPDOWN =====
function showStatusDropdown(event, projectId, currentStatus) {
    event.stopPropagation();
    
    // Close any open dropdowns
    document.querySelectorAll('.quick-actions-menu').forEach(m => m.classList.remove('active'));
    
    const badge = event.currentTarget;
    const rect = badge.getBoundingClientRect();
    
    // Create or show status menu
    let menu = document.getElementById(`statusMenu-${projectId}`);
    
    if (!menu) {
        menu = document.createElement('div');
        menu.id = `statusMenu-${projectId}`;
        menu.className = 'quick-actions-menu';
        menu.style.position = 'fixed';
        menu.style.top = (rect.bottom + 4) + 'px';
        menu.style.left = rect.left + 'px';
        menu.style.zIndex = '1001';
        
        menu.innerHTML = `
            <div class="quick-actions-item" onclick="updateStatus('${projectId}', 'en_cours')">
                <span class="status-badge en_cours" style="margin-right: 8px;">En cours</span>
            </div>
            <div class="quick-actions-item" onclick="updateStatus('${projectId}', 'en_pause')">
                <span class="status-badge en_pause" style="margin-right: 8px;">En pause</span>
            </div>
            <div class="quick-actions-item" onclick="updateStatus('${projectId}', 'fini')">
                <span class="status-badge fini" style="margin-right: 8px;">Terminé</span>
            </div>
        `;
        
        document.body.appendChild(menu);
    }
    
    menu.classList.toggle('active');
    
    // Close on outside click
    setTimeout(() => {
        document.addEventListener('click', closeStatusMenu, { once: true });
    }, 0);
}

function closeStatusMenu(e) {
    if (!e.target.closest('.quick-actions-menu')) {
        document.querySelectorAll('[id^="statusMenu-"]').forEach(m => m.classList.remove('active'));
    }
}

function updateStatus(projectId, newStatus) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    fetch(`/api/projet/${projectId}/statut/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ statut: newStatus })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            // Update badge
            const badge = document.querySelector(`.status-badge[data-id="${projectId}"]`);
            if (badge) {
                badge.className = `status-badge status-${newStatus}`;
                badge.textContent = newStatus === 'en_cours' ? 'En cours' : 
                                   newStatus === 'en_pause' ? 'En pause' : 'Terminé';
            }
            
            // Update progress bar
            const row = document.querySelector(`tr[data-id="${projectId}"]`);
            if (row) {
                const bar = row.querySelector('.progress-mini-bar');
                if (bar) {
                    bar.style.width = newStatus === 'fini' ? '100%' : newStatus === 'en_pause' ? '50%' : '75%';
                }
            }
            
            // Update data
            const project = projectsData.find(p => p.id === projectId);
            if (project) project.status = newStatus;
            
            filterProjects();
            showToast('Statut mis à jour ✓', 'success');
        }
    })
    .catch(() => showToast('Erreur de connexion', 'error'));
    
    // Close menu
    document.querySelectorAll('[id^="statusMenu-"]').forEach(m => m.classList.remove('active'));
}

// ===== QUICK ACTIONS =====
function toggleQuickActions(event, projectId) {
    event.stopPropagation();
    
    // Close all other menus
    document.querySelectorAll('.quick-actions-menu').forEach(m => {
        if (m.id !== `quickActions-${projectId}`) {
            m.classList.remove('active');
        }
    });
    
    const menu = document.getElementById(`quickActions-${projectId}`);
    menu?.classList.toggle('active');
}

// ===== CONTEXT MENU =====
function initContextMenu() {
    document.querySelectorAll('#projectsTable tr[data-id], .project-card').forEach(item => {
        item.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            contextMenuProjectId = this.dataset.id;
            
            const menu = document.getElementById('contextMenu');
            menu.style.left = e.pageX + 'px';
            menu.style.top = e.pageY + 'px';
            menu.classList.add('active');
            
            // Set action URLs
            document.getElementById('ctxView').href = `/projets/${contextMenuProjectId}/`;
            document.getElementById('ctxEdit').href = `/projets/${contextMenuProjectId}/modifier/`;
            document.getElementById('ctxPredict').href = `/projets/${contextMenuProjectId}/prediction/`;
            document.getElementById('ctxDelete').href = `/projets/${contextMenuProjectId}/supprimer/`;
        });
    });
}

// ===== QUICK VIEW MODAL =====
function showQuickView(projectId) {
    const project = projectsData.find(p => p.id === projectId);
    if (!project) return;
    
    const modal = document.getElementById('quickViewModal');
    const content = document.getElementById('quickViewContent');
    const title = document.getElementById('quickViewTitle');
    const editBtn = document.getElementById('quickViewEdit');
    
    title.textContent = project.name;
    editBtn.href = `/projets/${projectId}/modifier/`;
    
    // Find row data for display
    const row = document.querySelector(`tr[data-id="${projectId}"]`);
    const culture = row?.querySelector('.project-culture')?.textContent || 'N/A';
    const superficie = row?.cells[3]?.textContent || '0 ha';
    const date = row?.cells[4]?.textContent || 'N/A';
    const status = project.status;
    
    content.innerHTML = `
        <div class="modal-detail-row">
            <span class="modal-detail-label">Culture</span>
            <span class="modal-detail-value">${culture}</span>
        </div>
        <div class="modal-detail-row">
            <span class="modal-detail-label">Statut</span>
            <span class="modal-detail-value"><span class="status-badge status-${status}">${status === 'en_cours' ? 'En cours' : status === 'en_pause' ? 'En pause' : 'Terminé'}</span></span>
        </div>
        <div class="modal-detail-row">
            <span class="modal-detail-label">Superficie</span>
            <span class="modal-detail-value">${superficie}</span>
        </div>
        <div class="modal-detail-row">
            <span class="modal-detail-label">Date de lancement</span>
            <span class="modal-detail-value">${date}</span>
        </div>
        <div class="modal-detail-row">
            <span class="modal-detail-label">Progression</span>
            <span class="modal-detail-value">${status === 'fini' ? '100%' : status === 'en_pause' ? '50%' : '75%'}</span>
        </div>
    `;
    
    modal.classList.add('active');
}

function closeQuickView() {
    document.getElementById('quickViewModal').classList.remove('active');
}

// ===== VIEW TOGGLE =====
function initViewToggle() {
    document.querySelectorAll('.view-toggle button').forEach(btn => {
        btn.addEventListener('click', function() {
            const view = this.dataset.view;
            
            // Update button states
            document.querySelectorAll('.view-toggle button').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // Toggle views
            if (view === 'grid') {
                document.getElementById('tableView').classList.remove('active');
                document.getElementById('gridView').classList.add('active');
            } else {
                document.getElementById('tableView').classList.add('active');
                document.getElementById('gridView').classList.remove('active');
            }
            
            localStorage.setItem('projectsView', view);
            showToast(`Vue ${view === 'grid' ? 'cartes' : 'tableau'}`, 'info');
        });
    });
    
    // Load saved view
    const savedView = localStorage.getItem('projectsView') || 'table';
    document.querySelector(`.view-toggle button[data-view="${savedView}"]`)?.click();
}

// ===== KEYBOARD SHORTCUTS =====
function initKeyboardShortcuts() {
    const createProjectUrl = document.querySelector('.btn-accent[href]')?.getAttribute('href') || '/projets/creer/';

    document.addEventListener('keydown', function(e) {
        // Ignore if typing
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
            return;
        }
        
        // Show shortcuts: ?
        if (e.key === '?') {
            e.preventDefault();
            toggleShortcutsPanel();
            return;
        }
        
        // Close shortcuts: Escape
        if (e.key === 'Escape') {
            document.getElementById('shortcutsPanel').classList.remove('active');
            return;
        }
        
        // New project: N
        if (e.key.toLowerCase() === 'n') {
            e.preventDefault();
            window.location.href = createProjectUrl;
            return;
        }
        
        // Search: /
        if (e.key === '/') {
            e.preventDefault();
            document.getElementById('searchInput')?.focus();
            return;
        }
        
        // Select all: Ctrl+A
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'a') {
            e.preventDefault();
            document.getElementById('selectAll')?.click();
            return;
        }
        
        // Delete: Delete key
        if (e.key === 'Delete' && selectedProjects.size > 0) {
            e.preventDefault();
            if (confirm(`Supprimer ${selectedProjects.size} projet(s) ?`)) {
                document.getElementById('delete-form')?.submit();
            }
            return;
        }
        
        // Toggle view: G/T
        if (e.key.toLowerCase() === 'g') {
            e.preventDefault();
            document.querySelector('.view-toggle button[data-view="grid"]')?.click();
            return;
        }
        if (e.key.toLowerCase() === 't') {
            e.preventDefault();
            document.querySelector('.view-toggle button[data-view="table"]')?.click();
            return;
        }
        
        // Refresh: Ctrl+R
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'r') {
            e.preventDefault();
            refreshPage();
            return;
        }
    });
}

function toggleShortcutsPanel() {
    document.getElementById('shortcutsPanel').classList.toggle('active');
}

// ===== STICKY ACTIONS =====
function initStickyActions() {
    const actionsBar = document.getElementById('actionsBar');
    const header = document.querySelector('.page-header');
    
    if (!actionsBar || !header) return;
    
    const headerBottom = header.getBoundingClientRect().bottom;
    
    window.addEventListener('scroll', function() {
        if (window.scrollY > headerBottom + 20) {
            actionsBar.classList.add('sticky');
        } else {
            actionsBar.classList.remove('sticky');
        }
    });
}

// ===== REFRESH =====
function refreshPage() {
    const btn = document.getElementById('refreshBtn');
    if (!btn) return;
    
    const icon = btn.querySelector('i');
    icon.classList.add('fa-spin');
    
    showToast('Actualisation...', 'info');
    
    // Simulate refresh (replace with actual data fetch)
    setTimeout(() => {
        icon.classList.remove('fa-spin');
        showToast('Page actualisée ✓', 'success');
        
        // Re-animate rows
        document.querySelectorAll('#projectsTable tr').forEach((row, i) => {
            setTimeout(() => row.classList.add('highlight'), i * 50);
            setTimeout(() => row.classList.remove('highlight'), i * 50 + 1000);
        });
    }, 1000);
}

document.getElementById('refreshBtn')?.addEventListener('click', refreshPage);

// ===== SHORTCUTS BUTTON =====
document.getElementById('shortcutsBtn')?.addEventListener('click', toggleShortcutsPanel);

// ===== TOAST NOTIFICATIONS =====
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = { success: 'check', error: 'exclamation', info: 'info' };
    
    toast.innerHTML = `
        <div class="toast-icon">
            <i class="fas fa-${icons[type] || 'check'}"></i>
        </div>
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.closest('.toast').remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    container.appendChild(toast);
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.style.transform = 'translateX(-120%)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
