// ===== GLOBAL DATA STORE =====
const allProjects = [];
let filteredProjects = [];
let rendementChart = null;
let statusChart = null;
let monthlyTrendsChart = null;
let cultureChart = null;
let selectedProjects = new Set();
let dashboardStatsData = null;
let contextMenuProjectId = null;
let isRefreshing = false;
let searchQuery = '';
let chartControlsBound = false;

document.addEventListener('DOMContentLoaded', function () {
    // Collect all project data from DOM
    document.querySelectorAll('.project-item').forEach(card => {
        allProjects.push({
            id: card.dataset.id,
            nom: card.dataset.nom,
            status: card.dataset.status,
            culture: card.dataset.culture,
            cultureName: card.dataset.cultureName || '',
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
    initContextMenu();
    initCollapsibleSections();
    initThemeToggle();
    bindQuickAddTriggers();
    animateCounters();
    applyFilters();

    window.addEventListener('themeChanged', () => {
        updateThemeShortcutIcon();
        initCharts();
    });
    
    // Auto-refresh simulation (every 5 minutes)
    setInterval(autoRefresh, 5 * 60 * 1000);
    
    // ===== Search Filter with Debounce & Fuzzy =====
    const searchInput = document.getElementById('projectSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            searchQuery = this.value.toLowerCase().trim();
            applyFilters();
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
            const fermeSelect = document.getElementById('filterFerme');
            const hadFerme = fermeSelect && fermeSelect.value;
            if (fermeSelect) fermeSelect.value = '';
            filterStatut.value = '';
            filterCulture.value = '';
            filterDateFrom.value = '';
            filterDateTo.value = '';
            if (hadFerme) {
                applyFarmFilter('');
            } else {
                applyFilters();
            }
            showToast('Filtres réinitialisés', 'info');
        });
    }
    
    // ===== Farm Filter (AJAX) =====
    const filterFerme = document.getElementById('filterFerme');
    if (filterFerme) {
        filterFerme.addEventListener('change', function () {
            applyFarmFilter(this.value);
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

    // Handle browser Back/Forward for farm filter
    window.addEventListener('popstate', function() {
        const params = new URLSearchParams(window.location.search);
        const fermeId = params.get('ferme') || '';
        const fermeSelect = document.getElementById('filterFerme');
        if (fermeSelect && fermeSelect.value !== fermeId) {
            fermeSelect.value = fermeId;
            applyFarmFilter(fermeId);
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
                localStorage.setItem('dashboardLayout_v2', JSON.stringify(order));
                showToast('Disposition sauvegardée', 'success');
            }
        });

        // Drop legacy v1 layout so the redesigned default order takes effect
        localStorage.removeItem('dashboardLayout');

        // Load saved layout
        const savedLayout = localStorage.getItem('dashboardLayout_v2');
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

        // Reset filters: R
        if (e.key.toLowerCase() === 'r') {
            e.preventDefault();
            document.getElementById('resetFilters')?.click();
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

function bindQuickAddTriggers() {
    document.querySelectorAll('[data-open-quick-add]').forEach((trigger) => {
        trigger.addEventListener('click', openQuickAddModal);
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
            window.location.href = `/projet/${contextMenuProjectId}/`;
            break;
        case 'edit':
            window.location.href = `/projet/${contextMenuProjectId}/modifier/`;
            break;
        case 'predict':
            window.location.href = `/projet/${contextMenuProjectId}/generer_prediction/`;
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
    const toggle = document.getElementById('dashboardThemeShortcut');
    if (!toggle) return;

    updateThemeShortcutIcon();
    toggle.addEventListener('click', toggleTheme);
}

function toggleTheme() {
    const globalToggle = document.getElementById('themeToggle') || document.getElementById('themeToggleMobile');
    if (globalToggle) {
        globalToggle.click();
        return;
    }

    const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    const nextTheme = isDark ? 'light' : 'dark';

    document.documentElement.setAttribute('data-bs-theme', nextTheme);
    document.documentElement.classList.toggle('dark-mode', nextTheme === 'dark');
    document.documentElement.classList.toggle('light-mode', nextTheme === 'light');
    document.body.classList.toggle('dark-mode', nextTheme === 'dark');
    document.body.classList.toggle('light-mode', nextTheme === 'light');
    localStorage.setItem('theme', nextTheme);

    updateThemeShortcutIcon();
    initCharts();
}

function updateThemeShortcutIcon() {
    const toggle = document.getElementById('dashboardThemeShortcut');
    if (!toggle) return;

    const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    toggle.innerHTML = isDark ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
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

// ===== API HELPERS =====
function fetchDashboardStats(url) {
    const targetUrl = url || '/api/dashboard/stats/';
    return fetch(targetUrl)
        .then(res => {
            if (!res.ok) throw new Error('Network response was not ok');
            return res.json();
        })
        .then(data => {
            dashboardStatsData = data;
            return data;
        });
}

function buildStatsApiUrl() {
    const params = new URLSearchParams();
    const ferme = document.getElementById('filterFerme')?.value;
    const statut = document.getElementById('filterStatut')?.value;
    const culture = document.getElementById('filterCulture')?.value;
    const dateFrom = document.getElementById('filterDateFrom')?.value;
    const dateTo = document.getElementById('filterDateTo')?.value;
    if (ferme) params.append('ferme', ferme);
    if (statut) params.append('statut', statut);
    if (culture) params.append('culture', culture);
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    return `/api/dashboard/stats/?${params.toString()}`;
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
                            window.location.href = `/projet/${project.id}/`;
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
        
        bindChartControls();
    }

    // Status Pie Chart
    const statusCtx = document.getElementById('statusChart');
    if (statusCtx) {
        const statusCounts = getStatusCounts(filteredProjects);
        
        statusChart = new Chart(statusCtx.getContext('2d'), {
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

    if (!dashboardStatsData) {
        fetchDashboardStats().then(() => initCharts());
        return;
    }

    // Monthly Trends Line Chart
    const trendsCtx = document.getElementById('monthlyTrendsChart');
    if (trendsCtx && dashboardStatsData.monthly_trends) {
        const trends = dashboardStatsData.monthly_trends;
        const tCtx = trendsCtx.getContext('2d');
        const trendsGradient = tCtx.createLinearGradient(0, 0, 0, 300);
        trendsGradient.addColorStop(0, 'rgba(57, 255, 20, 0.3)');
        trendsGradient.addColorStop(1, 'rgba(57, 255, 20, 0.01)');

        monthlyTrendsChart = new Chart(tCtx, {
            type: 'line',
            data: {
                labels: trends.map(t => t.month),
                datasets: [
                    {
                        label: 'Projets',
                        data: trends.map(t => t.count),
                        borderColor: '#39FF14',
                        backgroundColor: trendsGradient,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: '#39FF14',
                        yAxisID: 'y'
                    },
                    {
                        label: 'Superficie (ha)',
                        data: trends.map(t => t.superficie),
                        borderColor: '#E2725B',
                        backgroundColor: 'transparent',
                        borderDash: [5, 5],
                        tension: 0.4,
                        pointRadius: 3,
                        pointBackgroundColor: '#E2725B',
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { intersect: false, mode: 'index' },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: gridColor, drawBorder: false },
                        ticks: { color: textColor, font: { family: "'Space Grotesk', sans-serif" } },
                        title: { display: true, text: 'Projets', color: '#39FF14', font: { family: "'Space Grotesk', sans-serif", weight: '700' } }
                    },
                    y1: {
                        position: 'right',
                        beginAtZero: true,
                        grid: { drawOnChartArea: false },
                        ticks: { color: textColor, font: { family: "'Space Grotesk', sans-serif" } },
                        title: { display: true, text: 'Superficie (ha)', color: '#E2725B', font: { family: "'Space Grotesk', sans-serif", weight: '700' } }
                    },
                    x: {
                        grid: { display: false, drawBorder: false },
                        ticks: { color: textColor, font: { family: "'Inter', sans-serif" } }
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: textColor, font: { family: "'Space Grotesk', sans-serif", weight: 600, size: 12 }, usePointStyle: true, padding: 20 }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(22, 27, 19, 0.95)',
                        titleColor: '#e0e0e0',
                        bodyColor: '#39FF14',
                        borderColor: 'rgba(57, 255, 20, 0.3)',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 12,
                        callbacks: {
                            label: (context) => `${context.dataset.label}: ${context.raw.toLocaleString('fr-FR')}`
                        }
                    }
                }
            }
        });
    }

    // Culture Distribution Horizontal Bar
    const cultureCtx = document.getElementById('cultureChart');
    if (cultureCtx && dashboardStatsData.projets_par_culture) {
        const cultures = dashboardStatsData.projets_par_culture;
        const cCtx = cultureCtx.getContext('2d');
        const cultureColors = [
            'rgba(57, 255, 20, 0.7)',
            'rgba(226, 114, 91, 0.7)',
            'rgba(255, 215, 0, 0.7)',
            'rgba(59, 130, 246, 0.7)',
            'rgba(168, 85, 247, 0.7)',
            'rgba(236, 72, 153, 0.7)'
        ];

        cultureChart = new Chart(cCtx, {
            type: 'bar',
            data: {
                labels: cultures.map(c => c.culture || 'Inconnu'),
                datasets: [{
                    label: 'Superficie (ha)',
                    data: cultures.map(c => c.superficie),
                    backgroundColor: cultures.map((_, i) => cultureColors[i % cultureColors.length]),
                    borderColor: cultures.map((_, i) => cultureColors[i % cultureColors.length].replace('0.7', '1')),
                    borderWidth: 1,
                    borderRadius: 6,
                    barPercentage: 0.6
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: { color: gridColor, drawBorder: false },
                        ticks: { color: textColor, font: { family: "'Space Grotesk', sans-serif" } },
                        title: { display: true, text: 'Superficie (ha)', color: '#39FF14', font: { family: "'Space Grotesk', sans-serif", weight: '700' } }
                    },
                    y: {
                        grid: { display: false, drawBorder: false },
                        ticks: { color: textColor, font: { family: "'Inter', sans-serif" } }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(22, 27, 19, 0.95)',
                        titleColor: '#e0e0e0',
                        bodyColor: '#39FF14',
                        borderColor: 'rgba(57, 255, 20, 0.3)',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 12,
                        callbacks: {
                            label: (context) => `Superficie: ${context.raw.toLocaleString('fr-FR')} ha`
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

    fetch(buildStatsApiUrl())
        .then(r => r.json())
        .then(data => {
            dashboardStatsData = data;
            if (monthlyTrendsChart && data.monthly_trends) {
                monthlyTrendsChart.data.labels = data.monthly_trends.map(t => t.month);
                monthlyTrendsChart.data.datasets[0].data = data.monthly_trends.map(t => t.count);
                monthlyTrendsChart.data.datasets[1].data = data.monthly_trends.map(t => t.superficie);
                monthlyTrendsChart.update('active');
            }
            if (cultureChart && data.projets_par_culture) {
                cultureChart.data.labels = data.projets_par_culture.map(c => c.culture || 'Inconnu');
                cultureChart.data.datasets[0].data = data.projets_par_culture.map(c => c.superficie);
                cultureChart.update('active');
            }
        })
        .catch(err => console.error('Failed to update API charts:', err));
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
    searchQuery = (query || '').toLowerCase().trim();
    applyFilters();
}

function bindChartControls() {
    if (chartControlsBound) return;

    document.getElementById('chartZoomIn')?.addEventListener('click', () => {
        if (rendementChart) rendementChart.zoom(1.1);
    });
    document.getElementById('chartZoomOut')?.addEventListener('click', () => {
        if (rendementChart) rendementChart.zoom(0.9);
    });
    document.getElementById('chartReset')?.addEventListener('click', () => {
        if (rendementChart) rendementChart.resetZoom();
    });

    chartControlsBound = true;
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
        if (searchQuery) {
            const haystack = `${project.nom} ${project.cultureName}`.toLowerCase();
            if (!haystack.includes(searchQuery)) matches = false;
        }
        return matches;
    });
    
    updateProjectVisibility();
    
    // Update KPIs
    updateKPIs();
    updateOverviewMetrics();
    
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

function updateProjectVisibility() {
    document.querySelectorAll('.project-item').forEach(card => {
        const isVisible = filteredProjects.some(p => p.id === card.dataset.id);
        card.style.display = isVisible ? 'flex' : 'none';
    });
}

// ===== UPDATE KPIs =====
function updateKPIs() {
    const totalProjects = filteredProjects.length;
    const totalSuperficie = filteredProjects.reduce((sum, p) => sum + p.superficie, 0);
    const totalRendement = filteredProjects.reduce((sum, p) => sum + p.rendement, 0);
    const totalInvestissement = filteredProjects.reduce((sum, p) => sum + (p.investissement || 0), 0);

    animateValue('kpiTotalProjects', totalProjects);
    animateValue('kpiSuperficie', totalSuperficie);
    animateValue('kpiRendement', totalRendement);
    if (document.getElementById('kpiInvestissement')) {
        animateValue('kpiInvestissement', totalInvestissement);
    }
    if (document.getElementById('kpiUtilisation')) {
        // Client-side filtering doesn't change farm utilization; keep existing value
    }
}

function updateOverviewMetrics() {
    const active = filteredProjects.filter((project) => project.status === 'en_cours').length;
    const paused = filteredProjects.filter((project) => project.status === 'en_pause').length;
    const finished = filteredProjects.filter((project) => project.status === 'fini').length;
    const total = filteredProjects.length;
    const completionRate = total ? Math.round((finished / total) * 100) : 0;

    // Farm view spotlight stats
    const farmProjectsEl = document.getElementById('spotlightFarmProjects');
    const farmUtilEl = document.getElementById('spotlightFarmUtilisation');
    if (farmProjectsEl) farmProjectsEl.textContent = active.toLocaleString('fr-FR');

    // Global view spotlight stats
    const projectsEl = document.getElementById('spotlightProjects');
    const farmsEl = document.getElementById('spotlightFarms');
    const membersEl = document.getElementById('spotlightMembers');
    if (projectsEl) projectsEl.textContent = total.toLocaleString('fr-FR');
    if (farmsEl) {
        // Farm count doesn't change with client-side filters
    }
    if (membersEl) {
        // Member count doesn't change with client-side filters
    }

    // Legacy IDs (fallback if still present in other pages)
    const activeEl = document.getElementById('spotlightActiveProjects');
    const pausedEl = document.getElementById('spotlightPausedProjects');
    const completionEl = document.getElementById('spotlightCompletionRate');
    if (activeEl) activeEl.textContent = active.toLocaleString('fr-FR');
    if (pausedEl) pausedEl.textContent = paused.toLocaleString('fr-FR');
    if (completionEl) completionEl.textContent = `${completionRate}%`;
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

    const fermeSelect = document.getElementById('filterFerme');
    if (fermeSelect && fermeSelect.value) {
        const fermeLabel = fermeSelect.options[fermeSelect.selectedIndex].text;
        activeFilters.push({type: 'ferme', label: fermeLabel});
    }
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
        case 'ferme':
            const fermeSelect = document.getElementById('filterFerme');
            if (fermeSelect) {
                fermeSelect.value = '';
                applyFarmFilter('');
            }
            return;
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
            <div class="modal-project-item" onclick="window.location.href='/projet/${project.id}/'">
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
                window.location.href = `/projet/${data.project_id}/generer_prediction/`;
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
    deleteProjectsBulk([projectId]);
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

// ===== DYNAMIC FARM FILTER (AJAX) =====
let currentFermeId = document.getElementById('filterFerme')?.value || '';

function applyFarmFilter(fermeId) {
    currentFermeId = fermeId;

    // Update URL without reload
    const url = new URL(window.location);
    if (fermeId) {
        url.searchParams.set('ferme', fermeId);
    } else {
        url.searchParams.delete('ferme');
    }
    history.pushState({}, '', url);

    // Build API URL with all current filters
    const params = new URLSearchParams();
    if (fermeId) params.set('ferme', fermeId);
    const statut = document.getElementById('filterStatut')?.value;
    const culture = document.getElementById('filterCulture')?.value;
    const dateFrom = document.getElementById('filterDateFrom')?.value;
    const dateTo = document.getElementById('filterDateTo')?.value;
    if (statut) params.set('statut', statut);
    if (culture) params.set('culture', culture);
    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);

    const apiUrl = `/api/dashboard/stats/?${params.toString()}`;

    // Show loading indicator
    const indicator = document.getElementById('refreshIndicator');
    indicator?.classList.add('refreshing');

    fetch(apiUrl)
        .then(res => {
            if (!res.ok) throw new Error('Network error');
            return res.json();
        })
        .then(data => {
            updateSpotlight(data);
            updateKPIsFromAPI(data);
            updateFarmCards(data);
            updateProjectList(data);
            updateChartsFromAPI(data);

            // Update allProjects data store
            allProjects.length = 0;
            (data.projets_list || []).forEach(p => {
                allProjects.push({
                    id: p.id,
                    nom: p.nom,
                    status: p.statut,
                    culture: p.culture_id,
                    cultureName: p.culture_nom,
                    date: p.date_lancement,
                    superficie: p.superficie,
                    rendement: p.rendement_estime,
                    progress: p.statut === 'fini' ? 100 : p.statut === 'en_pause' ? 50 : 75,
                    fermeNom: p.ferme_nom
                });
            });
            filteredProjects = [...allProjects];

            // Update filter count
            const filterCountEl = document.getElementById('filterCount');
            if (filterCountEl) {
                filterCountEl.textContent = `${data.nb_projets} projet(s)`;
                filterCountEl.style.transform = 'scale(1.2)';
                setTimeout(() => filterCountEl.style.transform = 'scale(1)', 200);
            }

            showToast(fermeId ? 'Ferme filtrée' : 'Vue globale', 'success');
        })
        .catch(err => {
            console.error('Farm filter error:', err);
            showToast('Erreur lors du filtrage', 'error');
        })
        .finally(() => {
            indicator?.classList.remove('refreshing');
        });
}

function updateSpotlight(data) {
    const section = document.getElementById('spotlightSection');
    if (!section) return;

    const mainDiv = section.querySelector('.dashboard-spotlight-main');
    const sideDiv = section.querySelector('.dashboard-spotlight-side');

    if (data.selected_ferme) {
        const f = data.selected_ferme;
        mainDiv.innerHTML = `
            <span class="spotlight-kicker"><i class="fas fa-warehouse"></i> Ferme sélectionnée</span>
            <h2 class="spotlight-title">${f.nom}</h2>
            <p class="spotlight-copy">
                ${f.description || 'Gérer les projets liés à cette ferme.'}
                <br><small class="text-muted">${f.localite}${f.localite && f.pays ? ', ' : ''}${f.pays} — ${f.superficie || '?'} ha</small>
            </p>
            <div class="spotlight-actions">
                <a href="/creer-projet/?ferme=${f.id}" class="btn-baay btn-baay-primary">
                    <i class="fas fa-plus"></i> Nouveau projet
                </a>
                <a href="/fermes/${f.id}/" class="btn-baay btn-baay-outline">
                    <i class="fas fa-warehouse"></i> Fiche ferme
                </a>
                <a href="#" class="btn-baay btn-baay-ghost" onclick="event.preventDefault(); document.getElementById('filterFerme').value=''; applyFarmFilter('');">
                    <i class="fas fa-globe"></i> Vue globale
                </a>
            </div>`;
        sideDiv.innerHTML = `
            <div class="spotlight-stat-card">
                <span class="spotlight-stat-label">Utilisation</span>
                <strong class="spotlight-stat-value" id="spotlightFarmUtilisation">${f.utilisation}%</strong>
                <span class="spotlight-stat-meta">${Math.round(f.superficie_utilisee)}/${Math.round(f.superficie)} ha</span>
            </div>
            <div class="spotlight-stat-card">
                <span class="spotlight-stat-label">Membres</span>
                <strong class="spotlight-stat-value" id="spotlightFarmMembers">${f.membres}</strong>
                <span class="spotlight-stat-meta">dans cette ferme</span>
            </div>
            <div class="spotlight-stat-card">
                <span class="spotlight-stat-label">Projets actifs</span>
                <strong class="spotlight-stat-value" id="spotlightFarmProjects">${data.projets_en_cours}</strong>
                <span class="spotlight-stat-meta">dans cette ferme</span>
            </div>`;
    } else {
        mainDiv.innerHTML = `
            <span class="spotlight-kicker">Vue d'ensemble</span>
            <h2 class="spotlight-title">Pilotez vos projets agricoles depuis un tableau de bord plus clair.</h2>
            <p class="spotlight-copy">
                ${data.nombre_fermes} ferme(s), ${data.nb_projets} projet(s) — Gardez les indicateurs importants visibles et filtrez rapidement.
            </p>
            <div class="spotlight-actions">
                <button class="btn-baay btn-baay-primary" type="button" data-open-quick-add>
                    <i class="fas fa-plus"></i> Nouveau projet
                </button>
                <a href="/fermes/" class="btn-baay btn-baay-outline">
                    <i class="fas fa-warehouse"></i> Mes fermes
                </a>
                <a href="/liste-projets/" class="btn-baay btn-baay-ghost">
                    <i class="fas fa-layer-group"></i> Tous les projets
                </a>
            </div>`;
        const inactiveTxt = data.fermes_inactives
            ? `<span class="text-warning">${data.fermes_inactives} inactive(s)</span>`
            : 'actives';
        sideDiv.innerHTML = `
            <div class="spotlight-stat-card">
                <span class="spotlight-stat-label">Fermes</span>
                <strong class="spotlight-stat-value" id="spotlightFarms">${data.nombre_fermes}</strong>
                <span class="spotlight-stat-meta">${inactiveTxt}</span>
            </div>
            <div class="spotlight-stat-card">
                <span class="spotlight-stat-label">Projets</span>
                <strong class="spotlight-stat-value" id="spotlightProjects">${data.nb_projets}</strong>
                <span class="spotlight-stat-meta">${data.projets_en_cours} en cours</span>
            </div>
            <div class="spotlight-stat-card">
                <span class="spotlight-stat-label">Membres</span>
                <strong class="spotlight-stat-value" id="spotlightMembers">${data.total_membres}</strong>
                <span class="spotlight-stat-meta">dans toutes les fermes</span>
            </div>`;
    }

    // Rebind quick add triggers
    bindQuickAddTriggers();
}

function updateKPIsFromAPI(data) {
    const grid = document.getElementById('dashboardGrid');
    if (!grid) return;

    // Remove old KPI cards
    grid.querySelectorAll('.tile-kpi').forEach(el => el.remove());

    // Reference node to insert before
    const filtersSection = grid.querySelector('[data-tile-id="filters"]');

    let kpiHtml = '';
    if (data.selected_ferme) {
        const f = data.selected_ferme;
        kpiHtml = `
        <div class="dash-stat-card bento-tile tile-kpi" data-tile-id="kpi-projects">
            <div class="tile-handle"><i class="fas fa-grip-vertical"></i></div>
            <div class="dash-stat-icon orange"><i class="fas fa-folder"></i></div>
            <div class="dash-stat-value" id="kpiTotalProjects">${data.nb_projets}</div>
            <div class="dash-stat-label">Projets ferme</div>
        </div>
        <div class="dash-stat-card bento-tile tile-kpi" data-tile-id="kpi-superficie">
            <div class="tile-handle"><i class="fas fa-grip-vertical"></i></div>
            <div class="dash-stat-icon accent"><i class="fas fa-map"></i></div>
            <div class="dash-stat-value" id="kpiSuperficie">${Math.round(f.superficie_utilisee)}/${Math.round(f.superficie)}</div>
            <div class="dash-stat-label">Ha utilisés</div>
        </div>
        <div class="dash-stat-card bento-tile tile-kpi" data-tile-id="kpi-utilisation">
            <div class="tile-handle"><i class="fas fa-grip-vertical"></i></div>
            <div class="dash-stat-icon purple"><i class="fas fa-chart-pie"></i></div>
            <div class="dash-stat-value" id="kpiUtilisation">${f.utilisation}%</div>
            <div class="dash-stat-label">Taux utilisation</div>
        </div>
        <div class="dash-stat-card bento-tile tile-kpi" data-tile-id="kpi-rendement">
            <div class="tile-handle"><i class="fas fa-grip-vertical"></i></div>
            <div class="dash-stat-icon blue"><i class="fas fa-boxes"></i></div>
            <div class="dash-stat-value" id="kpiRendement">${Math.round(f.rendement)}</div>
            <div class="dash-stat-label">Kg estimés ferme</div>
        </div>
        <div class="dash-stat-card bento-tile tile-kpi" data-tile-id="kpi-en-cours">
            <div class="tile-handle"><i class="fas fa-grip-vertical"></i></div>
            <div class="dash-stat-icon teal"><i class="fas fa-play-circle"></i></div>
            <div class="dash-stat-value" id="kpiEnCours">${data.projets_en_cours || 0}</div>
            <div class="dash-stat-label">Projets actifs</div>
        </div>
        <div class="dash-stat-card bento-tile tile-kpi" data-tile-id="kpi-completion">
            <div class="tile-handle"><i class="fas fa-grip-vertical"></i></div>
            <div class="dash-stat-icon green"><i class="fas fa-check-circle"></i></div>
            <div class="dash-stat-value" id="kpiCompletion">${data.completion_rate || 0}%</div>
            <div class="dash-stat-label">Taux de complétion</div>
        </div>
        <div class="dash-stat-card bento-tile tile-kpi" data-tile-id="kpi-membres">
            <div class="tile-handle"><i class="fas fa-grip-vertical"></i></div>
            <div class="dash-stat-icon teal"><i class="fas fa-users"></i></div>
            <div class="dash-stat-value" id="kpiMembres">${f.membres || 0}</div>
            <div class="dash-stat-label">Membres ferme</div>
        </div>
        <div class="dash-stat-card bento-tile tile-kpi" data-tile-id="kpi-investissement-ferme">
            <div class="tile-handle"><i class="fas fa-grip-vertical"></i></div>
            <div class="dash-stat-icon green"><i class="fas fa-coins"></i></div>
            <div class="dash-stat-value" id="kpiInvestissementFerme">${Math.round(data.investissement_total || 0)}</div>
            <div class="dash-stat-label">CFA investis</div>
        </div>`;
    } else {
        kpiHtml = `
        <div class="dash-stat-card bento-tile tile-kpi" data-tile-id="kpi-fermes">
            <div class="tile-handle"><i class="fas fa-grip-vertical"></i></div>
            <div class="dash-stat-icon teal"><i class="fas fa-warehouse"></i></div>
            <div class="dash-stat-value" id="kpiFermes">${data.nombre_fermes}</div>
            <div class="dash-stat-label">Fermes</div>
        </div>
        <div class="dash-stat-card bento-tile tile-kpi" data-tile-id="kpi-projects">
            <div class="tile-handle"><i class="fas fa-grip-vertical"></i></div>
            <div class="dash-stat-icon orange"><i class="fas fa-folder"></i></div>
            <div class="dash-stat-value" id="kpiTotalProjects">${data.nb_projets}</div>
            <div class="dash-stat-label">Projets</div>
        </div>
        <div class="dash-stat-card bento-tile tile-kpi" data-tile-id="kpi-superficie">
            <div class="tile-handle"><i class="fas fa-grip-vertical"></i></div>
            <div class="dash-stat-icon accent"><i class="fas fa-map"></i></div>
            <div class="dash-stat-value" id="kpiSuperficie">${Math.round(data.superficie_totale)}</div>
            <div class="dash-stat-label">Hectares</div>
        </div>
        <div class="dash-stat-card bento-tile tile-kpi" data-tile-id="kpi-investissement">
            <div class="tile-handle"><i class="fas fa-grip-vertical"></i></div>
            <div class="dash-stat-icon green"><i class="fas fa-coins"></i></div>
            <div class="dash-stat-value" id="kpiInvestissement">${Math.round(data.investissement_total)}</div>
            <div class="dash-stat-label">CFA investis</div>
        </div>
        <div class="dash-stat-card bento-tile tile-kpi" data-tile-id="kpi-en-cours">
            <div class="tile-handle"><i class="fas fa-grip-vertical"></i></div>
            <div class="dash-stat-icon blue"><i class="fas fa-play-circle"></i></div>
            <div class="dash-stat-value" id="kpiEnCours">${data.projets_en_cours || 0}</div>
            <div class="dash-stat-label">Projets actifs</div>
        </div>
        <div class="dash-stat-card bento-tile tile-kpi" data-tile-id="kpi-completion">
            <div class="tile-handle"><i class="fas fa-grip-vertical"></i></div>
            <div class="dash-stat-icon purple"><i class="fas fa-check-circle"></i></div>
            <div class="dash-stat-value" id="kpiCompletion">${data.completion_rate || 0}%</div>
            <div class="dash-stat-label">Taux de complétion</div>
        </div>
        <div class="dash-stat-card bento-tile tile-kpi" data-tile-id="kpi-rendement-global">
            <div class="tile-handle"><i class="fas fa-grip-vertical"></i></div>
            <div class="dash-stat-icon blue"><i class="fas fa-boxes"></i></div>
            <div class="dash-stat-value" id="kpiRendementGlobal">${Math.round(data.rendement_total || 0)}</div>
            <div class="dash-stat-label">Kg estimés</div>
        </div>
        <div class="dash-stat-card bento-tile tile-kpi" data-tile-id="kpi-membres">
            <div class="tile-handle"><i class="fas fa-grip-vertical"></i></div>
            <div class="dash-stat-icon teal"><i class="fas fa-users"></i></div>
            <div class="dash-stat-value" id="kpiMembres">${data.total_membres || 0}</div>
            <div class="dash-stat-label">Membres équipe</div>
        </div>`;
    }

    // Insert KPI cards before filters
    const temp = document.createElement('div');
    temp.innerHTML = kpiHtml;
    while (temp.firstElementChild) {
        grid.insertBefore(temp.firstElementChild, filtersSection);
    }

    animateCounters();
}

function updateFarmCards(data) {
    const section = document.getElementById('farmCardsSection');
    if (!section) return;

    if (data.selected_ferme || !data.fermes_data || data.fermes_data.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = '';

    const row = section.querySelector('.farm-cards-row');
    if (!row) return;

    row.innerHTML = data.fermes_data.map(fd => `
        <a href="javascript:void(0)" class="farm-card" onclick="document.getElementById('filterFerme').value='${fd.id}'; applyFarmFilter('${fd.id}');"
           style="min-width: 260px; flex: 0 0 auto; background: var(--card-bg); border-radius: 12px; padding: 16px; text-decoration: none; color: inherit; border: 1px solid var(--border-color); transition: transform .2s;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <strong style="font-size: 1.05rem; color: var(--text-main);">${fd.nom}</strong>
                <span class="badge" style="background: rgba(20,184,166,0.15); color: #14b8a6; font-size: .75rem; padding: 2px 8px; border-radius: 6px;">${fd.projets_actifs} actif${fd.projets_actifs !== 1 ? 's' : ''}</span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: .85rem; color: var(--text-muted);">
                <div><i class="fas fa-folder" style="margin-right: 4px;"></i> ${fd.projets_count} projet${fd.projets_count !== 1 ? 's' : ''}</div>
                <div><i class="fas fa-users" style="margin-right: 4px;"></i> ${fd.membres_count} membre${fd.membres_count !== 1 ? 's' : ''}</div>
                <div><i class="fas fa-map" style="margin-right: 4px;"></i> ${Math.round(fd.superficie_ferme)} ha</div>
                <div><i class="fas fa-chart-pie" style="margin-right: 4px;"></i> ${fd.utilisation_pct}% utilisé</div>
            </div>
            <div style="margin-top: 10px; height: 4px; background: var(--bg-tertiary); border-radius: 2px; overflow: hidden;">
                <div style="width: ${fd.utilisation_pct}%; height: 100%; background: linear-gradient(90deg, #14b8a6, #0ea5e9); border-radius: 2px;"></div>
            </div>
        </a>
    `).join('');
}

function updateProjectList(data) {
    const container = document.getElementById('projectsList');
    const projectsSection = document.querySelector('[data-tile-id="projects-list"] .dash-section-body');
    if (!projectsSection) return;

    const showFerme = !data.selected_ferme;
    const projets = data.projets_list || [];

    if (projets.length === 0) {
        projectsSection.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-folder-open"></i>
                <h4>Aucun projet</h4>
                <p>${data.selected_ferme ? "Cette ferme n'a pas encore de projet." : 'Commencez par créer votre premier projet agricole.'}</p>
                <a href="/creer-projet/${data.selected_ferme ? '?ferme=' + data.selected_ferme.id : ''}" class="btn-baay btn-baay-primary mt-3">
                    <i class="fas fa-plus"></i> Créer un projet
                </a>
            </div>`;
        return;
    }

    const statusLabel = s => s === 'en_cours' ? 'En cours' : s === 'en_pause' ? 'En pause' : 'Terminé';
    const progressVal = s => s === 'fini' ? 100 : s === 'en_pause' ? 50 : 75;

    const bulkBar = `<div class="bulk-actions-bar" id="bulkActionsBar">
        <span class="selected-count"><span id="selectedCount">0</span> sélectionné(s)</span>
        <button class="btn btn-primary" id="bulkStatus" title="Changer le statut"><i class="fas fa-tag"></i> Statut</button>
        <button class="btn btn-danger" id="bulkDelete" title="Supprimer"><i class="fas fa-trash"></i> Supprimer</button>
        <button class="btn" id="bulkCancel">Annuler</button>
    </div>`;

    const listHtml = projets.map(p => {
        const prog = progressVal(p.statut);
        const farmBadge = (showFerme && p.ferme_nom) ? `<span class="farm-badge"><i class="fas fa-warehouse"></i> ${p.ferme_nom}</span>` : '';
        return `
        <div class="project-item" data-id="${p.id}" data-status="${p.statut}"
            data-culture="${p.culture_id}" data-date="${p.date_lancement}"
            data-culture-name="${p.culture_nom}"
            data-nom="${p.nom}" data-rendement="${p.rendement_estime}"
            data-superficie="${p.superficie}"
            data-progress="${prog}">
            <div class="project-checkbox" onclick="toggleProjectSelection(event, '${p.id}')"></div>
            <div class="project-info" onclick="window.location.href='/projet/${p.id}/'">
                <div class="project-name editable" data-id="${p.id}"
                    ondblclick="editProjectName(event, '${p.id}', '${p.nom.replace(/'/g, "\\'")}')">
                    ${p.nom}
                </div>
                <div class="project-meta">
                    ${farmBadge}
                    <span><i class="fas fa-seedling"></i> ${p.culture_nom}</span>
                    <span><i class="fas fa-map"></i> ${p.superficie} ha</span>
                </div>
                <div class="project-progress">
                    <div class="project-progress-bar" style="width: ${prog}%"></div>
                </div>
                <div class="project-progress-meta">
                    <span>Progression</span>
                    <strong>${prog}%</strong>
                </div>
            </div>
            <span class="status-badge status-${p.statut}"
                onclick="event.stopPropagation(); showStatusModal('${p.id}', '${p.statut}')">
                ${statusLabel(p.statut)}
            </span>
            <div class="mini-p-stats">
                <span><i class="fas fa-crop-alt"></i> ${p.superficie} ha</span>
                <span><i class="fas fa-weight"></i> ${p.rendement_estime || '-'} kg</span>
            </div>
            <div class="mini-p-actions">
                <a href="/projet/${p.id}/" class="btn-baay btn-baay-outline py-1 px-2 text-xs" onclick="event.stopPropagation();" title="Voir">
                    <i class="fas fa-eye"></i>
                </a>
                <a href="/projet/${p.id}/modifier/" class="btn-baay btn-baay-ghost py-1 px-2 text-xs" onclick="event.stopPropagation();" title="Modifier">
                    <i class="fas fa-edit"></i>
                </a>
                <a href="/projet/${p.id}/generer_prediction/" class="btn-baay btn-baay-primary py-1 px-3 text-xs" onclick="event.stopPropagation();" title="IA Prediction">
                    <i class="fas fa-robot"></i>
                </a>
            </div>
        </div>`;
    }).join('');

    projectsSection.innerHTML = bulkBar + `<div class="project-list" id="projectsList">${listHtml}</div>`;

    // Re-init context menu and bulk actions on new DOM
    initContextMenu();
    initBulkActions();
    selectedProjects.clear();
}

function updateChartsFromAPI(data) {
    // Store API data for chart rebuilding
    dashboardStatsData = data;

    // Rebuild rendement & status charts from the new allProjects
    if (typeof Chart !== 'undefined') {
        // Small delay to let DOM settle
        requestAnimationFrame(() => {
            initCharts();
        });
    }
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

    fetch('/api/dashboard/stats/')
        .then(res => {
            if (!res.ok) throw new Error('Network response was not ok');
            return res.json();
        })
        .then(data => {
            // Update KPI cards from server data (only if element exists)
            const kpiIds = ['kpiTotalProjects', 'kpiSuperficie', 'kpiRendement', 'kpiInvestissement', 'kpiUtilisation', 'kpiFermes'];
            const kpiMap = {
                'kpiTotalProjects': data.nb_projets || 0,
                'kpiSuperficie': data.superficie_totale || 0,
                'kpiRendement': data.rendement_total || 0,
                'kpiInvestissement': data.investissement_total || 0,
                'kpiUtilisation': data.selected_ferme ? (data.selected_ferme.utilisation || 0) : 0,
                'kpiFermes': data.nombre_fermes || 0
            };
            kpiIds.forEach(id => {
                const el = document.getElementById(id);
                if (el) animateValue(id, kpiMap[id]);
            });

            // Update spotlight stats
            const enCours = data.projets_par_statut.find(p => p.statut === 'en_cours');
            const enPause = data.projets_par_statut.find(p => p.statut === 'en_pause');
            const finis = data.projets_par_statut.find(p => p.statut === 'fini');
            const total = data.nb_projets || 0;

            // Farm view IDs
            const farmProjectsEl = document.getElementById('spotlightFarmProjects');
            const farmUtilEl = document.getElementById('spotlightFarmUtilisation');
            const farmMembersEl = document.getElementById('spotlightFarmMembers');
            if (farmProjectsEl) farmProjectsEl.textContent = (enCours ? enCours.count : 0).toLocaleString('fr-FR');
            if (farmUtilEl && data.selected_ferme) farmUtilEl.textContent = `${data.selected_ferme.utilisation || 0}%`;
            if (farmMembersEl && data.selected_ferme) farmMembersEl.textContent = (data.selected_ferme.membres || 0).toLocaleString('fr-FR');

            // Global view IDs
            const projectsEl = document.getElementById('spotlightProjects');
            const farmsEl = document.getElementById('spotlightFarms');
            const membersEl = document.getElementById('spotlightMembers');
            if (projectsEl) projectsEl.textContent = total.toLocaleString('fr-FR');
            if (farmsEl) farmsEl.textContent = (data.nombre_fermes || 0).toLocaleString('fr-FR');
            if (membersEl) membersEl.textContent = (data.total_membres || 0).toLocaleString('fr-FR');

            // Legacy IDs (fallback)
            const activeEl = document.getElementById('spotlightActiveProjects');
            const pausedEl = document.getElementById('spotlightPausedProjects');
            const completionEl = document.getElementById('spotlightCompletionRate');
            const completionRate = total ? Math.round(((finis ? finis.count : 0) / total) * 100) : 0;
            if (activeEl) activeEl.textContent = (enCours ? enCours.count : 0).toLocaleString('fr-FR');
            if (pausedEl) pausedEl.textContent = (enPause ? enPause.count : 0).toLocaleString('fr-FR');
            if (completionEl) completionEl.textContent = `${completionRate}%`;

            // Update timestamp
            const now = new Date();
            const lastUpdated = document.getElementById('lastUpdated');
            if (lastUpdated) {
                lastUpdated.textContent =
                    `Mis à jour: ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
            }

            // Update API-based charts
            if (monthlyTrendsChart && data.monthly_trends) {
                monthlyTrendsChart.data.labels = data.monthly_trends.map(t => t.month);
                monthlyTrendsChart.data.datasets[0].data = data.monthly_trends.map(t => t.count);
                monthlyTrendsChart.data.datasets[1].data = data.monthly_trends.map(t => t.superficie);
                monthlyTrendsChart.update('active');
            }
            if (cultureChart && data.projets_par_culture) {
                cultureChart.data.labels = data.projets_par_culture.map(c => c.culture || 'Inconnu');
                cultureChart.data.datasets[0].data = data.projets_par_culture.map(c => c.superficie);
                cultureChart.update('active');
            }

            showToast('Données actualisées', 'success');
            animateCounters();
        })
        .catch(err => {
            console.error(err);
            showToast('Erreur lors de l\'actualisation', 'error');
        })
        .finally(() => {
            indicator.classList.remove('refreshing');
            isRefreshing = false;
        });
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
