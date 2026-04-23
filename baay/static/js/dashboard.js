// ===== GLOBAL DATA STORE =====
const allProjects = [];
let filteredProjects = [];
let rendementChart = null;
let statusChart = null;
let selectedProjects = new Set();
let contextMenuProjectId = null;
let isRefreshing = false;

document.addEventListener('DOMContentLoaded', function () {
    // Collect all project data from DOM
    document.querySelectorAll('.project-item').forEach(card => {
        allProjects.push({
            id: card.dataset.id,
            nom: card.dataset.nom,
            status: card.dataset.status,
            culture: card.dataset.culture,
            date: card.dataset.date,
            superficie: parseFloat(card.dataset.superficie) || 0,
            rendement: parseFloat(card.dataset.rendement) || 0,
            progress: parseInt(card.dataset.progress) || 0
        });
    });
    
    filteredProjects = [...allProjects];
    
    // Initialize features
    initCharts();
    initDragAndDrop();
    initKeyboardShortcuts();
    initVoiceSearch();
    initContextMenu();
    initCollapsibleSections();
    initThemeToggle();
    animateCounters();
    
    // Auto-refresh simulation (every 5 minutes)
    setInterval(autoRefresh, 5 * 60 * 1000);
    
    // ===== Search Filter with Debounce & Fuzzy =====
    const searchInput = document.getElementById('projectSearch');
    let searchTimeout;
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                const query = this.value.toLowerCase().trim();
                filterProjectsBySearch(query);
            }, 300); // 300ms debounce
        });
    }

    // ===== Filter Form =====
    const filterForm = document.getElementById('filterForm');
    const filterStatut = document.getElementById('filterStatut');
    const filterCulture = document.getElementById('filterCulture');
    const filterDateFrom = document.getElementById('filterDateFrom');
    const filterDateTo = document.getElementById('filterDateTo');
    
    if (filterForm) {
        filterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            applyFilters();
            showToast('Filtres appliqués', 'success');
        });
        
        [filterStatut, filterCulture].forEach(select => {
            if (select) select.addEventListener('change', applyFilters);
        });
        
        [filterDateFrom, filterDateTo].forEach(input => {
            if (input) input.addEventListener('change', applyFilters);
        });
    }
    
    const resetBtn = document.getElementById('resetFilters');
    if (resetBtn) {
        resetBtn.addEventListener('click', function() {
            filterStatut.value = '';
            filterCulture.value = '';
            filterDateFrom.value = '';
            filterDateTo.value = '';
            applyFilters();
            showToast('Filtres réinitialisés', 'info');
        });
    }
    
    // ===== Export Button =====
    const exportBtn = document.getElementById('exportData');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportToCSV);
    }
    
    // ===== Bulk Actions =====
    initBulkActions();
    
    // ===== Quick Add Form =====
    const quickAddForm = document.getElementById('quickAddForm');
    if (quickAddForm) {
        quickAddForm.addEventListener('submit', function(e) {
            e.preventDefault();
            handleQuickAddSubmit();
        });
    }
    
    // Close modals on overlay click
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.remove('active');
            }
        });
    });
    
    // Close context menu on click outside
    document.addEventListener('click', function(e) {
        const contextMenu = document.getElementById('contextMenu');
        if (!e.target.closest('.context-menu') && !e.target.closest('.project-item')) {
            contextMenu.classList.remove('active');
        }
    });
    
    // Close context menu on escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            document.getElementById('contextMenu').classList.remove('active');
            closeStatusModal();
            closeQuickAddModal();
            closeModal();
        }
    });
});

// ===== DRAG & DROP TILES =====
function initDragAndDrop() {
    const grid = document.getElementById('dashboardGrid');
    if (grid && typeof Sortable !== 'undefined') {
        new Sortable(grid, {
            animation: 150,
            handle: '.tile-handle',
            draggable: '.bento-tile, .dash-section',
            ghostClass: 'dragging',
            onEnd: function(evt) {
                // Save layout preference
                const order = Array.from(grid.children).map(tile => tile.dataset.tileId);
                localStorage.setItem('dashboardLayout', JSON.stringify(order));
                showToast('Disposition sauvegardée', 'success');
            }
        });
        
        // Load saved layout
        const savedLayout = localStorage.getItem('dashboardLayout');
        if (savedLayout) {
            const order = JSON.parse(savedLayout);
            order.forEach(tileId => {
                const tile = document.querySelector(`[data-tile-id="${tileId}"]`);
                if (tile) grid.appendChild(tile);
            });
        }
    }
}

// ===== KEYBOARD SHORTCUTS =====
function initKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ignore if typing in input/textarea
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
            return;
        }
        
        // Show shortcuts panel
        if (e.key === '?') {
            e.preventDefault();
            toggleShortcutsPanel();
            return;
        }
        
        // Close shortcuts with Escape
        if (e.key === 'Escape') {
            document.getElementById('shortcutsPanel').classList.remove('active');
            return;
        }
        
        // New project: N
        if (e.key.toLowerCase() === 'n') {
            e.preventDefault();
            openQuickAddModal();
            return;
        }
        
        // Search: /
        if (e.key === '/') {
            e.preventDefault();
            document.getElementById('projectSearch')?.focus();
            return;
        }
        
        // Reset filters: R
        if (e.key.toLowerCase() === 'r') {
            e.preventDefault();
            document.getElementById('resetFilters')?.click();
            return;
        }
        
        // Export: E
        if (e.key.toLowerCase() === 'e') {
            e.preventDefault();
            exportToCSV();
            return;
        }
        
        // Toggle theme: T
        if (e.key.toLowerCase() === 't') {
            e.preventDefault();
            toggleTheme();
            return;
        }
        
        // Refresh: Ctrl+R or F5
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'r') {
            e.preventDefault();
            refreshData();
            return;
        }
    });
}

function toggleShortcutsPanel() {
    const panel = document.getElementById('shortcutsPanel');
    panel.classList.toggle('active');
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
            document.getElementById('projectSearch').value = transcript;
            filterProjectsBySearch(transcript.toLowerCase());
            showToast(`🔍 Recherche: "${transcript}"`, 'success');
        };
        
        recognition.onerror = function(event) {
            showToast('❌ Erreur de reconnaissance vocale', 'error');
        };
        
        recognition.onend = function() {
            voiceBtn.classList.remove('listening');
        };
    });
}

// ===== CONTEXT MENU =====
function initContextMenu() {
    document.querySelectorAll('.project-item').forEach(item => {
        item.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            contextMenuProjectId = this.dataset.id;
            
            const menu = document.getElementById('contextMenu');
            menu.style.left = e.pageX + 'px';
            menu.style.top = e.pageY + 'px';
            menu.classList.add('active');
        });
    });
}

function contextMenuAction(action) {
    if (!contextMenuProjectId) return;
    
    document.getElementById('contextMenu').classList.remove('active');
    
    switch(action) {
        case 'view':
            window.location.href = `/projets/${contextMenuProjectId}/`;
            break;
        case 'edit':
            window.location.href = `/projets/${contextMenuProjectId}/modifier/`;
            break;
        case 'predict':
            window.location.href = `/projets/${contextMenuProjectId}/prediction/`;
            break;
        case 'status':
            showStatusModal(contextMenuProjectId);
            break;
        case 'delete':
            if (confirm('Êtes-vous sûr de vouloir supprimer ce projet ?')) {
                deleteProject(contextMenuProjectId);
            }
            break;
    }
    contextMenuProjectId = null;
}

// ===== COLLAPSIBLE SECTIONS =====
function initCollapsibleSections() {
    document.querySelectorAll('[data-toggle="collapse"]').forEach(header => {
        header.addEventListener('click', function(e) {
            // Don't collapse if clicking on buttons/inputs
            if (e.target.closest('button, input, select, .filter-actions')) return;
            
            const section = this.closest('.dash-section');
            section.classList.toggle('collapsed');
            
            // Save preference
            const sectionId = section.dataset.tileId;
            if (sectionId) {
                const collapsed = JSON.parse(localStorage.getItem('collapsedSections') || '{}');
                collapsed[sectionId] = section.classList.contains('collapsed');
                localStorage.setItem('collapsedSections', JSON.stringify(collapsed));
            }
        });
    });
    
    // Load saved collapsed state
    const collapsed = JSON.parse(localStorage.getItem('collapsedSections') || '{}');
    Object.entries(collapsed).forEach(([id, isCollapsed]) => {
        const section = document.querySelector(`[data-tile-id="${id}"]`);
        if (section && isCollapsed) {
            section.classList.add('collapsed');
        }
    });
}

// ===== THEME TOGGLE =====
function initThemeToggle() {
    const toggle = document.getElementById('themeToggle');
    const savedTheme = localStorage.getItem('theme') || 'light';
    
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        toggle.innerHTML = '<i class="fas fa-sun"></i>';
    }
    
    toggle.addEventListener('click', toggleTheme);
}

function toggleTheme() {
    const body = document.body;
    const toggle = document.getElementById('themeToggle');
    const isDark = body.classList.toggle('dark-mode');
    
    toggle.innerHTML = isDark ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    
    // Update charts if they exist
    if (rendementChart || statusChart) {
        initCharts();
    }
    
    showToast(`Thème ${isDark ? 'sombre' : 'clair'} activé`, 'info');
}

// ===== BULK ACTIONS =====
function initBulkActions() {
    // Select all checkbox (could be added to header)
    document.getElementById('bulkCancel')?.addEventListener('click', function() {
        selectedProjects.clear();
        updateBulkActionsBar();
        document.querySelectorAll('.project-checkbox').forEach(cb => cb.classList.remove('checked'));
    });
    
    document.getElementById('bulkStatus')?.addEventListener('click', function() {
        if (selectedProjects.size === 0) return;
        showToast(`${selectedProjects.size} projet(s) - Ouvrir modal de statut...`, 'info');
        // Could open a modal for bulk status change
    });
    
    document.getElementById('bulkDelete')?.addEventListener('click', function() {
        if (selectedProjects.size === 0) return;
        if (confirm(`Supprimer ${selectedProjects.size} projet(s) ? Cette action est irréversible.`)) {
            deleteProjectsBulk(Array.from(selectedProjects));
        }
    });
}

function toggleProjectSelection(event, projectId) {
    event.stopPropagation();
    
    const checkbox = event.currentTarget;
    checkbox.classList.toggle('checked');
    
    if (checkbox.classList.contains('checked')) {
        selectedProjects.add(projectId);
    } else {
        selectedProjects.delete(projectId);
    }
    
    updateBulkActionsBar();
}

function updateBulkActionsBar() {
    const bar = document.getElementById('bulkActionsBar');
    const count = document.getElementById('selectedCount');
    
    if (selectedProjects.size > 0) {
        bar.classList.add('active');
        count.textContent = selectedProjects.size;
    } else {
        bar.classList.remove('active');
    }
}

// ===== CHART INITIALIZATION WITH ZOOM =====
function initCharts() {
    if (typeof Chart === 'undefined' || allProjects.length === 0) return;
    
    const isDark = document.body.classList.contains('dark-mode');
    const gridColor = isDark ? 'rgba(57, 255, 20, 0.05)' : 'rgba(0, 0, 0, 0.05)';
    const textColor = isDark ? '#cbd5e1' : '#64748b';

    // Destroy existing charts
    if (rendementChart) rendementChart.destroy();
    if (statusChart) statusChart.destroy();

    // Yield Chart with zoom plugin
    const rendementCtx = document.getElementById('rendementChart');
    if (rendementCtx) {
        const ctx = rendementCtx.getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(57, 255, 20, 0.4)');
        gradient.addColorStop(1, 'rgba(57, 255, 20, 0.01)');

        rendementChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: filteredProjects.map(p => p.nom),
                datasets: [{
                    label: 'Rendement Estimé (kg)',
                    data: filteredProjects.map(p => p.rendement),
                    backgroundColor: gradient,
                    borderColor: '#39FF14',
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false,
                    barPercentage: 0.6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 1000, easing: 'easeOutQuart' },
                interaction: { intersect: false, mode: 'index' },
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const project = filteredProjects[index];
                        if (project) {
                            window.location.href = `/projets/${project.id}/`;
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: gridColor, drawBorder: false },
                        ticks: { color: textColor, font: { family: "'Space Grotesk', sans-serif" } },
                        title: { display: true, text: 'Rendement (kg)', color: '#39FF14', font: { family: "'Space Grotesk', sans-serif", weight: '700' } }
                    },
                    x: {
                        grid: { display: false, drawBorder: false },
                        ticks: { color: textColor, font: { family: "'Inter', sans-serif" }, maxRotation: 45 }
                    }
                },
                plugins: {
                    legend: { display: false },
                    zoom: {
                        pan: { enabled: true, mode: 'xy' },
                        zoom: {
                            wheel: { enabled: true },
                            pinch: { enabled: true },
                            mode: 'xy',
                            onZoomComplete: ({ chart }) => chart.update('none')
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(22, 27, 19, 0.95)',
                        titleColor: '#39FF14',
                        titleFont: { family: "'Space Grotesk', sans-serif", weight: '700' },
                        bodyColor: '#e0e0e0',
                        bodyFont: { family: "'Inter', sans-serif" },
                        borderColor: 'rgba(57, 255, 20, 0.3)',
                        borderWidth: 1,
                        padding: 16,
                        cornerRadius: 15,
                        displayColors: false,
                        callbacks: {
                            label: (context) => `Rendement: ${context.raw.toLocaleString('fr-FR')} kg`,
                            afterLabel: (context) => {
                                const project = filteredProjects[context.dataIndex];
                                return `Superficie: ${project.superficie} ha`;
                            }
                        }
                    }
                }
            }
        });
        
        // Chart toolbar buttons
        document.getElementById('chartZoomIn')?.addEventListener('click', () => {
            rendementChart.zoom(1.1);
        });
        document.getElementById('chartZoomOut')?.addEventListener('click', () => {
            rendementChart.zoom(0.9);
        });
        document.getElementById('chartReset')?.addEventListener('click', () => {
            rendementChart.resetZoom();
        });
    }

    // Status Pie Chart
    const statusCtx = document.getElementById('statusChart');
    if (statusCtx) {
        const statusCounts = getStatusCounts(filteredProjects);
        
        statusChart = new Chart(statusCtx, {
            type: 'doughnut',
            data: {
                labels: ['En cours', 'En pause', 'Terminé'],
                datasets: [{
                    data: [statusCounts.en_cours, statusCounts.en_pause, statusCounts.fini],
                    backgroundColor: [
                        'rgba(57, 255, 20, 0.6)',
                        'rgba(226, 114, 91, 0.6)',
                        'rgba(255, 215, 0, 0.6)'
                    ],
                    borderColor: ['#39FF14', '#E2725B', '#FFD700'],
                    borderWidth: 2,
                    hoverOffset: 15,
                    spacing: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '75%',
                animation: { animateRotate: true, animateScale: true, duration: 1500, easing: 'easeOutElastic' },
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const statusMap = ['en_cours', 'en_pause', 'fini'];
                        const statusLabels = ['En cours', 'En pause', 'Terminé'];
                        const status = statusMap[index];
                        const projectsWithStatus = filteredProjects.filter(p => p.status === status);
                        showProjectsModal('status', `Projets ${statusLabels[index]}`, projectsWithStatus);
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 25,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            color: textColor,
                            font: { family: "'Space Grotesk', sans-serif", weight: 600, size: 12 }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(22, 27, 19, 0.95)',
                        titleColor: '#e0e0e0',
                        bodyColor: '#39FF14',
                        borderColor: 'rgba(57, 255, 20, 0.3)',
                        borderWidth: 1,
                        padding: 16,
                        cornerRadius: 15,
                        callbacks: {
                            label: (context) => `${context.label}: ${context.raw} projet(s)`,
                            afterLabel: () => 'Cliquez pour plus de détails'
                        }
                    }
                }
            }
        });
    }
}

// ===== UPDATE CHARTS =====
function updateCharts() {
    if (rendementChart) {
        rendementChart.data.labels = filteredProjects.map(p => p.nom);
        rendementChart.data.datasets[0].data = filteredProjects.map(p => p.rendement);
        rendementChart.update('active');
    }
    
    if (statusChart) {
        const statusCounts = getStatusCounts(filteredProjects);
        statusChart.data.datasets[0].data = [statusCounts.en_cours, statusCounts.en_pause, statusCounts.fini];
        statusChart.update('active');
    }
}

// ===== GET STATUS COUNTS =====
function getStatusCounts(projects) {
    return {
        en_cours: projects.filter(p => p.status === 'en_cours').length,
        en_pause: projects.filter(p => p.status === 'en_pause').length,
        fini: projects.filter(p => p.status === 'fini').length
    };
}

// ===== FILTER PROJECTS BY SEARCH (FUZZY) =====
function filterProjectsBySearch(query) {
    if (!query) {
        // Reset to filtered by form filters
        applyFilters();
        return;
    }
    
    const results = allProjects.filter(project => {
        // Fuzzy match on name
        const nameMatch = project.nom.toLowerCase().includes(query);
        // Also search in culture name (would need to fetch culture names)
        return nameMatch;
    });
    
    // Update display
    document.querySelectorAll('.project-item').forEach(card => {
        const isVisible = results.some(p => p.id === card.dataset.id);
        card.style.display = isVisible ? 'flex' : 'none';
    });
    
    // Update count
    document.getElementById('filterCount').textContent = `${results.length} projet(s)`;
}

// ===== APPLY FILTERS =====
function applyFilters() {
    const statut = document.getElementById('filterStatut').value;
    const culture = document.getElementById('filterCulture');
    const cultureId = culture.value;
    const cultureName = culture.options[culture.selectedIndex]?.text || '';
    const dateFrom = document.getElementById('filterDateFrom').value;
    const dateTo = document.getElementById('filterDateTo').value;
    
    // Filter projects
    filteredProjects = allProjects.filter(project => {
        let matches = true;
        if (statut && project.status !== statut) matches = false;
        if (cultureId && project.culture !== cultureId) matches = false;
        if (dateFrom && project.date && project.date < dateFrom) matches = false;
        if (dateTo && project.date && project.date > dateTo) matches = false;
        return matches;
    });
    
    // Update project cards visibility
    document.querySelectorAll('.project-item').forEach(card => {
        const isVisible = filteredProjects.some(p => p.id === card.dataset.id);
        card.style.display = isVisible ? 'flex' : 'none';
    });
    
    // Update KPIs
    updateKPIs();
    
    // Update charts
    updateCharts();
    
    // Update active filters display
    updateActiveFilters(statut, cultureName, dateFrom, dateTo);
    
    // Update count badge with animation
    const filterCountEl = document.getElementById('filterCount');
    filterCountEl.textContent = `${filteredProjects.length} projet(s)`;
    filterCountEl.style.transform = 'scale(1.2)';
    setTimeout(() => filterCountEl.style.transform = 'scale(1)', 200);
}

// ===== UPDATE KPIs =====
function updateKPIs() {
    const totalProjects = filteredProjects.length;
    const totalSuperficie = filteredProjects.reduce((sum, p) => sum + p.superficie, 0);
    const totalRendement = filteredProjects.reduce((sum, p) => sum + p.rendement, 0);
    
    animateValue('kpiTotalProjects', totalProjects);
    animateValue('kpiSuperficie', totalSuperficie);
    animateValue('kpiRendement', totalRendement);
}

// ===== ANIMATE VALUE =====
function animateValue(elementId, newValue) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const currentValue = parseInt(element.textContent.replace(/\s/g, '')) || 0;
    const duration = 500;
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const current = Math.floor(currentValue + (newValue - currentValue) * easeOut);
        
        element.textContent = current.toLocaleString('fr-FR');
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

// ===== ANIMATE COUNTERS =====
function animateCounters() {
    const counters = document.querySelectorAll('.dash-stat-value');
    counters.forEach(counter => {
        const target = parseFloat(counter.textContent.replace(/\s/g, '')) || 0;
        if (target === 0) return;
        
        const duration = 1500;
        const startTime = performance.now();
        
        function updateCounter(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeOut = 1 - Math.pow(1 - progress, 3);
            const current = Math.floor(target * easeOut);
            
            counter.textContent = current.toLocaleString('fr-FR');
            
            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            }
        }
        
        requestAnimationFrame(updateCounter);
    });
}

// ===== UPDATE ACTIVE FILTERS =====
function updateActiveFilters(statut, cultureName, dateFrom, dateTo) {
    const container = document.getElementById('activeFilters');
    if (!container) return;
    
    const activeFilters = [];
    
    if (statut) {
        const statusLabels = {'en_cours': 'En cours', 'en_pause': 'En pause', 'fini': 'Terminé'};
        activeFilters.push({type: 'statut', label: statusLabels[statut]});
    }
    if (cultureName && cultureName !== 'Toutes') {
        activeFilters.push({type: 'culture', label: cultureName});
    }
    if (dateFrom) {
        activeFilters.push({type: 'date_from', label: `Depuis ${dateFrom}`});
    }
    if (dateTo) {
        activeFilters.push({type: 'date_to', label: `Jusqu'à ${dateTo}`});
    }
    
    if (activeFilters.length > 0) {
        container.style.display = 'flex';
        container.innerHTML = activeFilters.map(f => `
            <div class="filter-chip">
                <span>${f.label}</span>
                <button type="button" class="filter-chip-remove" onclick="removeFilter('${f.type}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');
    } else {
        container.style.display = 'none';
    }
}

// ===== REMOVE FILTER =====
function removeFilter(type) {
    switch(type) {
        case 'statut':
            document.getElementById('filterStatut').value = '';
            break;
        case 'culture':
            document.getElementById('filterCulture').value = '';
            break;
        case 'date_from':
            document.getElementById('filterDateFrom').value = '';
            break;
        case 'date_to':
            document.getElementById('filterDateTo').value = '';
            break;
    }
    applyFilters();
    showToast('Filtre supprimé', 'info');
}

// ===== EDIT PROJECT NAME INLINE =====
function editProjectName(event, projectId, currentName) {
    event.stopPropagation();
    
    const nameEl = event.currentTarget;
    if (nameEl.classList.contains('editing')) return;
    
    const originalName = nameEl.textContent;
    nameEl.classList.add('editing');
    nameEl.innerHTML = `<input type="text" class="project-name-input" value="${currentName}" data-id="${projectId}">`;
    
    const input = nameEl.querySelector('input');
    input.focus();
    input.select();
    
    // Save on blur or enter
    const saveEdit = () => {
        const newValue = input.value.trim();
        if (newValue && newValue !== currentName) {
            // Update in DOM
            nameEl.textContent = newValue;
            nameEl.classList.remove('editing');
            
            // Update in data store
            const project = allProjects.find(p => p.id === projectId);
            if (project) project.nom = newValue;
            
            // Here you would make an API call to save
            // saveProjectName(projectId, newValue);
            
            showToast('Nom mis à jour', 'success');
        } else {
            nameEl.textContent = originalName;
            nameEl.classList.remove('editing');
        }
    };
    
    input.addEventListener('blur', saveEdit);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            input.blur();
        }
        if (e.key === 'Escape') {
            nameEl.textContent = originalName;
            nameEl.classList.remove('editing');
        }
    });
}

// ===== SHOW PROJECTS MODAL =====
function showProjectsModal(type, title, projects = null) {
    const modal = document.getElementById('projectsModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalList = document.getElementById('modalProjectList');
    
    modalTitle.textContent = title;
    
    const projectsToShow = projects || filteredProjects;
    
    if (projectsToShow.length === 0) {
        modalList.innerHTML = `
            <div class="modal-empty">
                <i class="fas fa-folder-open"></i>
                <p>Aucun projet trouvé</p>
            </div>
        `;
    } else {
        modalList.innerHTML = projectsToShow.map(project => `
            <div class="modal-project-item" onclick="window.location.href='/projets/${project.id}/'">
                <div class="modal-project-info">
                    <h4>${project.nom}</h4>
                    <p>${project.cultureName || 'Culture'} - ${project.localite || 'Localité'}</p>
                </div>
                <div class="modal-project-stats">
                    <span><i class="fas fa-crop-alt"></i> ${project.superficie} ha</span>
                    <span><i class="fas fa-weight"></i> ${project.rendement} kg</span>
                </div>
                <i class="fas fa-chevron-right modal-project-arrow"></i>
            </div>
        `).join('');
    }
    
    modal.classList.add('active');
}

// ===== CLOSE MODAL =====
function closeModal() {
    document.getElementById('projectsModal').classList.remove('active');
}

// ===== STATUS MODAL =====
function showStatusModal(projectId, currentStatus) {
    document.getElementById('statusModalProjectId').value = projectId;
    document.getElementById('statusModal').classList.add('active');
}

function closeStatusModal() {
    document.getElementById('statusModal').classList.remove('active');
}

// ===== UPDATE PROJECT STATUS =====
function updateProjectStatus(newStatus) {
    const projectId = document.getElementById('statusModalProjectId').value;
    
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                      document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
    
    fetch(`/api/projet/${projectId}/statut/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ statut: newStatus })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update the card in DOM
            const card = document.querySelector(`.project-item[data-id="${projectId}"]`);
            if (card) {
                card.setAttribute('data-status', newStatus);
                const badge = card.querySelector('.status-badge');
                badge.className = `status-badge status-${newStatus}`;
                badge.textContent = newStatus === 'en_cours' ? 'En cours' : 
                                   newStatus === 'en_pause' ? 'En pause' : 'Terminé';
                
                // Update progress bar
                const progressBar = card.querySelector('.project-progress-bar');
                if (progressBar) {
                    const progress = newStatus === 'fini' ? 100 : newStatus === 'en_pause' ? 50 : 75;
                    progressBar.style.width = `${progress}%`;
                }
            }
            
            // Update the project in our data store
            const projectIndex = allProjects.findIndex(p => p.id === projectId);
            if (projectIndex !== -1) {
                allProjects[projectIndex].status = newStatus;
            }
            
            // Re-apply filters to update everything
            applyFilters();
            
            closeStatusModal();
            showToast('Statut mis à jour ✅', 'success');
        } else {
            showToast('Erreur lors de la mise à jour', 'error');
        }
    })
    .catch(err => {
        console.error(err);
        showToast('Erreur de connexion', 'error');
    });
}

// ===== QUICK ADD MODAL =====
function openQuickAddModal() {
    document.getElementById('quickAddModal').classList.add('active');
}

function closeQuickAddModal() {
    document.getElementById('quickAddModal').classList.remove('active');
    document.getElementById('quickAddForm')?.reset();
}

function handleQuickAddSubmit() {
    const form = document.getElementById('quickAddForm');
    const formData = new FormData(form);
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Création...';
    
    fetch('/api/projet/creer/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            closeQuickAddModal();
            showToast('🎉 Projet créé avec succès!', 'success');
            // Redirect to prediction or detail page
            setTimeout(() => {
                window.location.href = `/projets/${data.project_id}/prediction/`;
            }, 1500);
        } else {
            showToast(data.error || 'Erreur lors de la création', 'error');
        }
    })
    .catch(err => {
        console.error(err);
        showToast('Erreur de connexion', 'error');
    })
    .finally(() => {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
    });
}

// ===== EXPORT TO CSV =====
function exportToCSV() {
    if (filteredProjects.length === 0) {
        showToast('Aucune donnée à exporter', 'error');
        return;
    }
    
    const headers = ['ID', 'Nom', 'Culture', 'Statut', 'Superficie (ha)', 'Rendement (kg)', 'Date'];
    const rows = filteredProjects.map(p => [
        p.id,
        `"${p.nom}"`,
        p.culture,
        p.status,
        p.superficie,
        p.rendement,
        p.date
    ]);
    
    const csvContent = [
        headers.join(','),
        ...rows.map(row => row.join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `projets_andd_baay_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showToast('📊 Données exportées!', 'success');
}

// ===== BULK DELETE =====
function deleteProjectsBulk(projectIds) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    fetch('/api/projet/bulk-delete/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ ids: projectIds })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Remove from DOM and data store
            projectIds.forEach(id => {
                const card = document.querySelector(`.project-item[data-id="${id}"]`);
                if (card) card.remove();
                const index = allProjects.findIndex(p => p.id === id);
                if (index !== -1) allProjects.splice(index, 1);
            });
            
            selectedProjects.clear();
            updateBulkActionsBar();
            applyFilters();
            showToast(`${projectIds.length} projet(s) supprimé(s) 🗑️`, 'success');
        } else {
            showToast('Erreur lors de la suppression', 'error');
        }
    })
    .catch(err => {
        console.error(err);
        showToast('Erreur de connexion', 'error');
    });
}

// ===== SINGLE DELETE =====
function deleteProject(projectId) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    fetch(`/api/projet/${projectId}/`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const card = document.querySelector(`.project-item[data-id="${projectId}"]`);
            if (card) {
                card.style.animation = 'fadeOut 0.3s ease';
                setTimeout(() => card.remove(), 300);
            }
            const index = allProjects.findIndex(p => p.id === projectId);
            if (index !== -1) allProjects.splice(index, 1);
            
            applyFilters();
            showToast('Projet supprimé 🗑️', 'success');
        } else {
            showToast('Erreur lors de la suppression', 'error');
        }
    })
    .catch(err => {
        console.error(err);
        showToast('Erreur de connexion', 'error');
    });
}

// ===== TOAST NOTIFICATION =====
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
    
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ===== AUTO REFRESH =====
function autoRefresh() {
    if (isRefreshing) return;
    refreshData();
}

function refreshData() {
    if (isRefreshing) return;
    
    isRefreshing = true;
    const indicator = document.getElementById('refreshIndicator');
    indicator.classList.add('refreshing');
    
    // Simulate API call (replace with actual fetch)
    setTimeout(() => {
        // Update timestamp
        const now = new Date();
        document.getElementById('lastUpdated').textContent = 
            `Mis à jour: ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
        
        indicator.classList.remove('refreshing');
        isRefreshing = false;
        
        // Here you would fetch new data and update the dashboard
        // For now, just show a toast
        showToast('Données actualisées 🔄', 'success');
        
        // Re-animate KPIs
        animateCounters();
    }, 1500);
}

// Add fade out animation for deleted items
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeOut {
        from { opacity: 1; transform: translateX(0); }
        to { opacity: 0; transform: translateX(-20px); }
    }
`;
document.head.appendChild(style);
