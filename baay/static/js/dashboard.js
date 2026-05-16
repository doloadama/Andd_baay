// ===== GLOBAL DATA STORE =====
const allProjects = [];
let filteredProjects = [];
let rendementChart = null;
let statusChart = null;
let financeFlowChart = null;
let investCategoryChart = null;
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
            progress: parseInt(card.dataset.progress, 10) || 0
        });
    });
    
    filteredProjects = [...allProjects];
    
    dashboardStatsBootstrap()
        .then(() => {
            updateQuickStripFromStats(dashboardStatsData);
            loadDashboardWeather();
            initCharts();
        })
        .catch(() => {
            initCharts();
        });

    initDragAndDrop();
    initKeyboardShortcuts();
    initContextMenu();
    initCollapsibleSections();
    initThemeToggle();
    bindQuickAddTriggers();
    initVoiceAssistantUi();
    animateCounters();
    applyFilters();

    window.addEventListener('themeChanged', () => {
        updateThemeShortcutIcon();
        initCharts();
    });
    
    // Auto-refresh simulation (every 5 minutes)
    setInterval(autoRefresh, 5 * 60 * 1000);
    
    // ===== Search Filter with Debounce & Fuzzy =====
    function debounce(fn, delay) {
        let timeoutId;
        return function(...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    const searchInput = document.getElementById('projectSearch');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function() {
            searchQuery = this.value.toLowerCase().trim();
            applyFilters();
        }, 250));
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

function dashboardStatsBootstrap() {
    return fetchDashboardStats(buildStatsApiUrl());
}

function fcfa(n) {
    if (n === null || n === undefined || Number.isNaN(Number(n))) return '—';
    try {
        return `${Math.round(Number(n)).toLocaleString('fr-FR')} FCFA`;
    } catch {
        return String(n);
    }
}

function updateQuickStripFromStats(data) {
    if (!data || !data.quick_stats) return;
    const qs = data.quick_stats;
    const b = document.getElementById('cqBenefice');
    const r = document.getElementById('cqRoi');
    const t = document.getElementById('cqTachesCrit');
    if (b) {
        if (qs.show_financial_kpis) b.textContent = fcfa(qs.benefice_net_total);
        else b.textContent = '—';
    }
    if (r) {
        if (qs.show_financial_kpis && qs.roi_moyen_pct != null)
            r.textContent = `${Number(qs.roi_moyen_pct).toLocaleString('fr-FR', {
                maximumFractionDigits: 1
            })}%`;
        else r.textContent = '—';
    }
    if (t) t.textContent = String(qs.taches_critiques_retard ?? 0);
}

function loadDashboardWeather() {
    const w = document.getElementById('weatherWidget');
    const inner = w && w.querySelector('.cw-inner');
    if (!w || !inner) return;
    let fermeId = w.dataset.weatherFerme || '';
    if (!fermeId) {
        fermeId = document.getElementById('filterFerme')?.value || '';
    }
    if (!fermeId) {
        w.className = 'cockpit-weather';
        inner.innerHTML =
            '<i class="fas fa-cloud-sun fa-lg cw-weather-icon" aria-hidden="true"></i><span id="weatherSummary">Coordonnées ferme ou filtre à définir</span>';
        return;
    }
    w.className = 'cockpit-weather';
    inner.innerHTML =
        '<i class="fas fa-cloud-sun fa-lg cw-weather-icon" aria-hidden="true"></i><span id="weatherSummary">Chargement météo…</span>';
    fetch(`/api/dashboard/weather/?ferme=${encodeURIComponent(fermeId)}`)
        .then((res) => res.json())
        .then((payload) => {
            const resolve = window.resolveOpenWeatherTheme || function () {
                return { cockpitSkin: '', cockpitIcon: 'fa-cloud-sun' };
            };
            if (!payload.ok || !payload.data) {
                w.className = 'cockpit-weather';
                const msg =
                    payload.error === 'coords_absentes'
                        ? 'GPS ferme à renseigner'
                        : payload.error === 'api_key_absente'
                          ? 'Météo : clé API absente'
                          : 'Météo indisponible';
                inner.innerHTML =
                    '<i class="fas fa-cloud-sun fa-lg cw-weather-icon" aria-hidden="true"></i><span id="weatherSummary">' +
                    msg +
                    '</span>';
                return;
            }
            const d = payload.data;
            const theme = resolve(d.icone);
            const skin = theme.cockpitSkin ? ` ${theme.cockpitSkin}` : '';
            w.className = `cockpit-weather${skin}`;
            const tmp =
                d.temperature != null ? `${Math.round(Number(d.temperature))}°C` : '';
            const desc =
                ((d.description || '') + '').charAt(0).toUpperCase() + (d.description || '').slice(1);
            const icon = theme.cockpitIcon || 'fa-cloud-sun';
            inner.innerHTML =
                `<i class="fas ${icon} fa-lg cw-weather-icon" aria-hidden="true"></i>` +
                `<span id="weatherSummary"><span class="cw-temp">${tmp}</span> <span class="cw-desc">${desc}</span></span>`;
        })
        .catch(() => {
            w.className = 'cockpit-weather';
            inner.innerHTML =
                '<i class="fas fa-cloud-sun fa-lg cw-weather-icon" aria-hidden="true"></i><span id="weatherSummary">Erreur réseau météo</span>';
        });
}

function getCsrfToken() {
    const fromInput = document.querySelector('[name=csrfmiddlewaretoken]');
    if (fromInput && fromInput.value) return fromInput.value;
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
}

function initVoiceAssistantUi() {
    const fab = document.getElementById('voiceFab');
    const modal = document.getElementById('voiceAssistantModal');
    const closeBtn = document.getElementById('voiceModalClose');
    const send = document.getElementById('voiceSendBtn');
    const mic = document.getElementById('voiceMicBtn');
    const ta = document.getElementById('voiceTranscript');
    const locale = document.getElementById('voiceLocale');
    const reply = document.getElementById('voiceAssistantReply');
    if (!fab || !modal) return;

    const open = () => {
        modal.classList.add('active');
        modal.setAttribute('aria-hidden', 'false');
        if (reply) reply.textContent = '';
    };
    const shut = () => {
        modal.classList.remove('active');
        modal.setAttribute('aria-hidden', 'true');
    };

    fab.addEventListener('click', () => open());
    closeBtn?.addEventListener('click', shut);

    async function submitVocal() {
        const text = (ta?.value || '').trim();
        if (!text) {
            showToast('Saisissez une phrase ou utilisez le micro.', 'info');
            return;
        }
        const hint = (locale?.value || 'fr').trim();
        if (reply) reply.textContent = '…';
        try {
            const res = await fetch('/api/vocal-query/', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ text: text, transcript: text, locale_hint: hint })
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                if (reply) reply.textContent = data.error || 'Erreur assistant';
                return;
            }
            if (reply) reply.textContent = data.answer_text || data.summary || data.message || '';
        } catch {
            if (reply) reply.textContent = 'Erreur réseau';
        }
    }

    send?.addEventListener('click', submitVocal);

    mic?.addEventListener('click', () => {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) {
            showToast('Micro : non supporté sur ce navigateur', 'warning');
            return;
        }
        const rec = new SR();
        rec.lang =
            locale?.value === 'wo' ? 'wo-SN' : locale?.value === 'ff' ? 'ff-SN' : 'fr-FR';
        rec.onresult = ev => {
            const t =
                ev.results && ev.results[0] && ev.results[0][0]
                    ? ev.results[0][0].transcript
                    : '';
            if (ta) ta.value = t;
        };
        rec.onerror = () => showToast('Échec reconnaissance vocale', 'error');
        rec.start();
        showToast('Écoute…', 'info');
    });
}

/** Mois affichés en français court (ex. 2025-03 → mars 25). */
function cockpitYmToFrShort(key) {
    if (key == null || typeof key !== 'string') return key;
    const m = /^(\d{4})-(\d{2})/.exec(key.trim());
    if (!m) return key;
    const monthIdx = parseInt(m[2], 10) - 1;
    const shorts = [
        'janv.',
        'févr.',
        'mars',
        'avr.',
        'mai',
        'juin',
        'juil.',
        'août',
        'sept.',
        'oct.',
        'nov.',
        'déc.'
    ];
    const y2 = m[1].slice(-2);
    if (monthIdx < 0 || monthIdx > 11) return `${m[2]}/${y2}`;
    return `${shorts[monthIdx]} ${y2}`;
}

/** Axe Y : montants lisibles (k / M). */
function cockpitFormatFcfaAxis(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return '';
    const a = Math.abs(n);
    if (a < 1000) return n.toLocaleString('fr-FR', { maximumFractionDigits: 0 });
    if (a < 999_500) return `${(n / 1000).toLocaleString('fr-FR', { maximumFractionDigits: 0 })} k`;
    return `${(n / 1_000_000).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} M`;
}

function cockpitFormatFcfaFull(value) {
    return `${Number(value).toLocaleString('fr-FR', { maximumFractionDigits: 0 })} FCFA`;
}

function cockpitSetChartOverlay(canvasEl, mode, message) {
    const wrap = canvasEl?.closest('.cockpit-chart-container');
    const overlay = wrap?.querySelector('.cockpit-chart-loading');
    if (!canvasEl || !overlay) return;
    canvasEl.classList.remove('cockpit-chart--concealed');
    overlay.classList.remove('cockpit-chart-overlay--empty');
    if (mode === 'loading') {
        overlay.textContent = message || '';
        if (overlay.textContent) {
            overlay.classList.remove('is-hidden');
            canvasEl.classList.add('cockpit-chart--concealed');
        }
        overlay.setAttribute('aria-hidden', overlay.textContent ? 'false' : 'true');
        return;
    }
    if (mode === 'empty') {
        overlay.textContent = message || 'Aucune donnée sur cette période.';
        overlay.classList.add('cockpit-chart-overlay--empty');
        overlay.classList.remove('is-hidden');
        overlay.setAttribute('aria-hidden', 'false');
        canvasEl.classList.add('cockpit-chart--concealed');
        return;
    }
    canvasEl.classList.remove('cockpit-chart--concealed');
    overlay.classList.add('is-hidden');
    overlay.setAttribute('aria-hidden', 'true');
}

function scheduleFinanceChartsInit(isDark, gridColor, textColor) {
    window.setTimeout(() => {
        buildFinanceCockpitCharts(isDark, gridColor, textColor);
    }, 0);
}

/**
 * Évolution recettes / dépenses (12 mois) + répartition investissements.
 * Libellés lisibles, axe Y compact, solde mensuel en infobulle.
 */
function buildFinanceCockpitCharts(isDark, gridColor, textColor) {
    if (typeof Chart === 'undefined') return;

    const data = dashboardStatsData || {};

    const fm = data.finance_monthly || { labels: [], recettes: [], depenses: [] };
    const rawLabs = fm.labels || [];
    const rec = fm.recettes || [];
    const dep = fm.depenses || [];

    const ttBorder = isDark ? 'rgba(248,250,252,0.12)' : 'rgba(15,23,42,0.12)';
    const ttBg = isDark ? 'rgba(15, 23, 42, 0.97)' : 'rgba(255, 255, 255, 0.98)';
    const axisLabel = isDark ? '#e2e8f0' : '#334155';

    /* ---- Recettes vs dépenses ---- */
    const finEl = document.getElementById('financeFlowChart');
    if (finEl) {
        if (financeFlowChart) financeFlowChart.destroy();

        const totalMouv =
            rec.reduce((s, v) => s + Number(v || 0), 0) + dep.reduce((s, v) => s + Number(v || 0), 0);

        if (!rawLabs.length || totalMouv === 0) {
            cockpitSetChartOverlay(
                finEl,
                'empty',
                'Pas de recettes ni de dépenses enregistrées sur les 12 derniers mois (périmètre et droits financiers actuels).'
            );
            financeFlowChart = null;
        } else {
            cockpitSetChartOverlay(finEl, 'ready');
            const labelFr = rawLabs.map(cockpitYmToFrShort);

            const borderRec = isDark ? '#4ade80' : '#15803d';
            const borderDep = isDark ? '#f87171' : '#dc2626';

            const finCtx = finEl.getContext('2d');
            const recGrad = finCtx.createLinearGradient(0, 0, 0, Math.max(260, finEl.height || 260));
            recGrad.addColorStop(0, isDark ? 'rgba(74,222,128,0.35)' : 'rgba(34,197,94,0.38)');
            recGrad.addColorStop(1, isDark ? 'rgba(74,222,128,0.02)' : 'rgba(34,197,94,0.02)');

            financeFlowChart = new Chart(finCtx, {
                type: 'line',
                data: {
                    labels: labelFr,
                    datasets: [
                        {
                            label: 'Recettes',
                            data: rec,
                            borderColor: borderRec,
                            backgroundColor: recGrad,
                            fill: true,
                            tension: 0.38,
                            pointRadius: 3,
                            pointHoverRadius: 7,
                            pointBackgroundColor: borderRec,
                            pointBorderWidth: 2,
                            pointBorderColor: isDark ? '#0f172a' : '#fff',
                            borderWidth: 2.5
                        },
                        {
                            label: 'Dépenses (invest. + fiches)',
                            data: dep,
                            borderColor: borderDep,
                            backgroundColor: 'transparent',
                            fill: false,
                            tension: 0.35,
                            pointRadius: 3,
                            pointHoverRadius: 7,
                            pointBackgroundColor: borderDep,
                            pointBorderWidth: 2,
                            pointBorderColor: isDark ? '#0f172a' : '#fff',
                            borderWidth: 2.5,
                            borderDash: [7, 4]
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    resizeDelay: 16,
                    animation: { duration: 520 },
                    interaction: { intersect: false, mode: 'index' },
                    scales: {
                        x: {
                            grid: { display: false, drawBorder: false },
                            ticks: {
                                color: textColor,
                                maxRotation: 45,
                                minRotation: 0,
                                autoSkip: true,
                                maxTicksLimit: 12,
                                font: { weight: '600', size: 11 }
                            },
                            border: { color: gridColor }
                        },
                        y: {
                            stacked: false,
                            beginAtZero: true,
                            grace: '8%',
                            grid: {
                                color: gridColor,
                                drawBorder: false,
                                tickLength: 0
                            },
                            ticks: {
                                color: textColor,
                                callback: v => cockpitFormatFcfaAxis(v),
                                font: { size: 11 }
                            },
                            title: {
                                display: true,
                                text: 'Montants (FCFA)',
                                color: axisLabel,
                                font: { size: 11, weight: '700' },
                                padding: { bottom: 6 }
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'top',
                            align: 'start',
                            labels: {
                                color: textColor,
                                usePointStyle: true,
                                pointStyle: 'rectRounded',
                                padding: 16,
                                font: { weight: '600', size: 12 }
                            }
                        },
                        tooltip: {
                            enabled: true,
                            backgroundColor: ttBg,
                            titleColor: axisLabel,
                            bodyColor: axisLabel,
                            borderColor: ttBorder,
                            borderWidth: 1,
                            padding: 14,
                            titleAlign: 'left',
                            bodyAlign: 'left',
                            displayColors: true,
                            footerAlign: 'left',
                            callbacks: {
                                title(items) {
                                    const i = items[0]?.dataIndex;
                                    if (i === undefined || i < 0) return '';
                                    return `Période : ${cockpitYmToFrShort(rawLabs[i])} (${rawLabs[i] ?? ''})`;
                                },
                                label(ctx) {
                                    return ` ${ctx.dataset.label}: ${cockpitFormatFcfaFull(Number(ctx.raw) || 0)}`;
                                },
                                footer(items) {
                                    const i = items[0]?.dataIndex;
                                    if (i === undefined || i < 0) return '';
                                    const rVal = Number(rec[i]) || 0;
                                    const dVal = Number(dep[i]) || 0;
                                    const solde = rVal - dVal;
                                    const sign = solde > 0 ? '+' : '';
                                    return `\nSolde du mois : ${sign}${cockpitFormatFcfaFull(solde)}`;
                                }
                            }
                        }
                    },
                    animation: {
                        onComplete: () => hideChartSkeleton('financeFlowChart')
                    }
                }
            });
        }
    }

    /* ---- Investissements par catégorie ---- */
    const invEl = document.getElementById('investCategoryChart');
    if (invEl) {
        if (investCategoryChart) investCategoryChart.destroy();

        const inv = data.invest_by_category || { labels: [], values: [] };
        const browns = ['#78350f', '#92400e', '#b45309', '#ca8a04', '#a16207', '#713f12', '#854d0e'];
        let pairs = (inv.labels || []).map((l, i) => ({
            label: l || '—',
            value: Number(inv.values?.[i]) || 0
        }));

        pairs = pairs.filter(p => p.value > 0);
        const totalInvest = pairs.reduce((s, p) => s + p.value, 0);

        if (!pairs.length || totalInvest <= 0) {
            cockpitSetChartOverlay(
                invEl,
                'empty',
                'Aucun investissement enregistré pour les projets de votre périmètre financier (ou filtres trop restrictifs).'
            );
            investCategoryChart = null;
        } else {
            cockpitSetChartOverlay(invEl, 'ready');
            const labs = pairs.map(p => p.label);
            const vals = pairs.map(p => p.value);

            investCategoryChart = new Chart(invEl.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: labs,
                    datasets: [
                        {
                            data: vals,
                            backgroundColor: labs.map((_, i) =>
                                isDark ? `${browns[i % browns.length]}d0` : `${browns[i % browns.length]}cc`
                            ),
                            borderColor: labs.map((_, i) => browns[i % browns.length]),
                            borderWidth: 2,
                            hoverOffset: 10,
                            spacing: 1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    resizeDelay: 16,
                    cutout: '56%',
                    animation: { animateRotate: true, duration: 600 },
                    plugins: {
                        legend: {
                            position: 'bottom',
                            align: 'center',
                            labels: {
                                color: textColor,
                                usePointStyle: true,
                                pointStyle: 'circle',
                                padding: 14,
                                font: { size: 11, weight: '600' },
                                boxWidth: 10,
                                boxHeight: 10,
                                generateLabels(chart) {
                                    const ds = chart.data.datasets[0];
                                    const d = ds.data.map(x => Number(x) || 0);
                                    const t = d.reduce((a, b) => a + b, 0);
                                    return chart.data.labels.map((label, i) => {
                                        const v = d[i];
                                        const pct = t > 0 ? Math.round((v / t) * 1000) / 10 : 0;
                                        return {
                                            text: `${label} — ${pct}%`,
                                            fillStyle: Array.isArray(ds.backgroundColor)
                                                ? ds.backgroundColor[i]
                                                : ds.backgroundColor,
                                            strokeStyle: Array.isArray(ds.borderColor)
                                                ? ds.borderColor[i]
                                                : ds.borderColor,
                                            fontColor: textColor,
                                            hidden: false,
                                            index: i,
                                            datasetIndex: 0
                                        };
                                    });
                                }
                            }
                        },
                        tooltip: {
                            backgroundColor: ttBg,
                            titleColor: axisLabel,
                            bodyColor: axisLabel,
                            borderColor: ttBorder,
                            borderWidth: 1,
                            padding: 14,
                            callbacks: {
                                title(ctxItems) {
                                    return ctxItems[0]?.label || '';
                                },
                                label(ctx) {
                                    const v = Number(ctx.raw) || 0;
                                    const sum = vals.reduce((a, b) => a + b, 0);
                                    const pct = sum > 0 ? Math.round((v / sum) * 1000) / 10 : 0;
                                    return [
                                        cockpitFormatFcfaFull(v),
                                        `Part du total : ${pct}%`
                                    ];
                                },
                                footer() {
                                    return `Total catégories : ${cockpitFormatFcfaFull(totalInvest)}`;
                                }
                            }
                        }
                    },
                    animation: {
                        onComplete: () => hideChartSkeleton('investCategoryChart')
                    }
                }
            });
        }
    }
}

// ===== CHART SKELETONS =====
function hideChartSkeleton(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (canvas) {
        canvas.style.display = 'block';
        const container = canvas.closest('[data-chart-container]');
        if (container) {
            const skeleton = container.querySelector('.chart-skeleton');
            if (skeleton) skeleton.style.display = 'none';
        }
    }
}

// ===== CHART INITIALIZATION WITH ZOOM =====
function initCharts() {
    if (typeof Chart === 'undefined') return;

    const isDark = document.body.classList.contains('dark-mode');
    const gridColor = isDark ? 'rgba(226, 232, 240, 0.04)' : 'rgba(15, 23, 42, 0.04)';
    const textColor = isDark ? '#cbd5e1' : '#64748b';
    const brandGreen = '#1D9E75';
    const brandGreenLight = '#5DCAA5';
    const brandMuted = '#94a3b8';

    // Destroy existing charts
    if (rendementChart) rendementChart.destroy();
    if (statusChart) statusChart.destroy();
    if (financeFlowChart) financeFlowChart.destroy();
    if (investCategoryChart) investCategoryChart.destroy();
    if (cultureChart) cultureChart.destroy();

    // Yield Chart with zoom plugin
    const rendementCtx = document.getElementById('rendementChart');
    if (rendementCtx && filteredProjects.length > 0) {
        const ctx = rendementCtx.getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(29, 158, 117, 0.36)');
        gradient.addColorStop(1, 'rgba(29, 158, 117, 0.04)');

        rendementChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: filteredProjects.map(p => p.nom),
                datasets: [{
                    label: 'Rendement Estimé (kg)',
                    data: filteredProjects.map(p => p.rendement),
                    backgroundColor: gradient,
                    borderColor: brandGreen,
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false,
                    barPercentage: 0.6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart',
                    onComplete: () => hideChartSkeleton('rendementChart')
                },
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
                        title: { display: true, text: 'Rendement (kg)', color: brandGreen, font: { family: "'Space Grotesk', sans-serif", weight: '700' } }
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
                        titleColor: brandGreenLight,
                        titleFont: { family: "'Space Grotesk', sans-serif", weight: '700' },
                        bodyColor: isDark ? '#e2e8f0' : '#334155',
                        bodyFont: { family: "'Inter', sans-serif" },
                        borderColor: 'rgba(29, 158, 117, 0.28)',
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
    if (statusCtx && filteredProjects.length > 0) {
        const statusCounts = getStatusCounts(filteredProjects);
        
        statusChart = new Chart(statusCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['En cours', 'En pause', 'Terminés'],
                datasets: [{
                    data: [statusCounts.en_cours, statusCounts.en_pause, statusCounts.fini],
                    backgroundColor: [
                        'rgba(29, 158, 117, 0.76)',
                        'rgba(148, 163, 184, 0.58)',
                        'rgba(93, 202, 165, 0.72)'
                    ],
                    borderColor: [brandGreen, brandMuted, brandGreenLight],
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
                        const statusMap = ['en_cours', 'en_pause', 'termines'];
                        const statusLabels = ['En cours', 'En pause', 'Terminés'];
                        const key = statusMap[index];
                        const projectsWithStatus =
                            key === 'termines'
                                ? filteredProjects.filter(
                                      (p) => p.status === 'fini' || p.status === 'cloture'
                                  )
                                : filteredProjects.filter((p) => p.status === key);
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
                        bodyColor: isDark ? '#e2e8f0' : '#334155',
                        borderColor: 'rgba(29, 158, 117, 0.24)',
                        borderWidth: 1,
                        padding: 16,
                        cornerRadius: 15,
                        callbacks: {
                            label: (context) => `${context.label}: ${context.raw} projet(s)`,
                            afterLabel: () => 'Cliquez pour plus de détails'
                        }
                    }
                },
                animation: {
                    onComplete: () => hideChartSkeleton('statusChart')
                }
            }
        });
    }

    scheduleFinanceChartsInit(isDark, gridColor, textColor);

    // Culture Distribution Horizontal Bar
    const cultureCtx = document.getElementById('cultureChart');
    if (cultureCtx && dashboardStatsData && dashboardStatsData.projets_par_culture) {
        const cultures = dashboardStatsData.projets_par_culture;
        const cCtx = cultureCtx.getContext('2d');
        const cultureColors = [
            'rgba(29, 158, 117, 0.78)',
            'rgba(93, 202, 165, 0.72)',
            'rgba(239, 159, 39, 0.72)',
            'rgba(8, 80, 65, 0.64)',
            'rgba(159, 225, 203, 0.72)',
            'rgba(217, 138, 28, 0.68)'
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
                        title: { display: true, text: 'Superficie (ha)', color: brandGreen, font: { family: "'Space Grotesk', sans-serif", weight: '700' } }
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
                        bodyColor: isDark ? '#e2e8f0' : '#334155',
                        borderColor: 'rgba(29, 158, 117, 0.24)',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 12,
                        callbacks: {
                            label: (context) => `Superficie: ${context.raw.toLocaleString('fr-FR')} ha`
                        }
                    }
                },
                animation: {
                    onComplete: () => hideChartSkeleton('cultureChart')
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
            updateQuickStripFromStats(data);
            const dark = document.body.classList.contains('dark-mode');
            const gc = dark ? 'rgba(226, 232, 240, 0.04)' : 'rgba(15, 23, 42, 0.04)';
            const tc = dark ? '#cbd5e1' : '#64748b';
            buildFinanceCockpitCharts(dark, gc, tc);
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
        fini: projects.filter(p => p.status === 'fini' || p.status === 'cloture').length
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
    const finished = filteredProjects.filter(
        (project) => project.status === 'fini' || project.status === 'cloture'
    ).length;
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
        const statusLabels = {
            en_cours: 'En cours',
            en_pause: 'En pause',
            fini: 'Fini',
            cloture: 'Clôturé',
        };
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
    
    modalList.innerHTML = '';
    if (projectsToShow.length === 0) {
        modalList.innerHTML = `
            <div class="modal-empty">
                <i class="fas fa-folder-open"></i>
                <p>Aucun projet trouvé</p>
            </div>
        `;
    } else {
        projectsToShow.forEach(project => {
            const item = document.createElement('div');
            item.className = 'modal-project-item';
            item.addEventListener('click', () => { window.location.href = '/projet/' + encodeURIComponent(project.id) + '/'; });

            const info = document.createElement('div');
            info.className = 'modal-project-info';

            const h4 = document.createElement('h4');
            h4.textContent = project.nom;
            info.appendChild(h4);

            const p = document.createElement('p');
            p.textContent = (project.cultureName || 'Culture') + ' - ' + (project.localite || 'Localité');
            info.appendChild(p);
            item.appendChild(info);

            const stats = document.createElement('div');
            stats.className = 'modal-project-stats';

            const span1 = document.createElement('span');
            span1.innerHTML = '<i class="fas fa-crop-alt"></i> ';
            const s1t = document.createElement('span');
            s1t.textContent = project.superficie + ' ha';
            span1.appendChild(s1t);
            stats.appendChild(span1);

            const span2 = document.createElement('span');
            span2.innerHTML = '<i class="fas fa-weight"></i> ';
            const s2t = document.createElement('span');
            s2t.textContent = project.rendement + ' kg';
            span2.appendChild(s2t);
            stats.appendChild(span2);
            item.appendChild(stats);

            const arrow = document.createElement('i');
            arrow.className = 'fas fa-chevron-right modal-project-arrow';
            item.appendChild(arrow);

            modalList.appendChild(item);
        });
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
                badge.textContent =
                    newStatus === 'en_cours'
                        ? 'En cours'
                        : newStatus === 'en_pause'
                          ? 'En pause'
                          : newStatus === 'cloture'
                            ? 'Clôturé'
                            : newStatus === 'fini'
                              ? 'Fini'
                              : '—';
                
                // Update progress bar
                const progressBar = card.querySelector('.project-progress-bar');
                if (progressBar) {
                    const progress = newStatus === 'fini' || newStatus === 'cloture' ? 100 : newStatus === 'en_pause' ? 50 : 75;
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
            showToast(data.error || 'Erreur lors de la mise à jour', 'error');
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
            updateQuickStripFromStats(data);
            const ww = document.getElementById('weatherWidget');
            if (ww && fermeId) ww.dataset.weatherFerme = fermeId;

            // Update allProjects data store
            allProjects.length = 0;
            (data.projets_list || []).forEach(p => {
                const pct =
                    typeof p.taux_avancement === 'number'
                        ? p.taux_avancement
                        : p.statut === 'fini' || p.statut === 'cloture'
                          ? 100
                          : p.statut === 'en_pause'
                            ? 50
                            : 75;
                allProjects.push({
                    id: p.id,
                    nom: p.nom,
                    status: p.statut,
                    culture: p.culture_id,
                    cultureName: p.culture_nom,
                    date: p.date_lancement,
                    superficie: p.superficie,
                    rendement: p.rendement_estime,
                    progress: pct,
                    fermeNom: p.ferme_nom
                });
            });
            filteredProjects = [...allProjects];

            loadDashboardWeather();

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
                <div class="cockpit-empty-illu" aria-hidden="true"></div>
                <div class="empty-state-icon"><i class="fas fa-folder-open"></i></div>
                <h4>Aucun projet actif</h4>
                <p>${data.selected_ferme ? "Cette ferme n'a pas encore de projet." : 'Commencez par créer votre premier projet agricole.'}</p>
                <a href="${data.selected_ferme ? '/creer-projet/?ferme=' + data.selected_ferme.id : '/creer-projet/'}" class="btn-baay btn-baay-primary mt-3">
                    <i class="fas fa-plus"></i> Créer un projet
                </a>
            </div>`;
        return;
    }

    const statusLabel = s =>
        s === 'en_cours' ? 'En cours' : s === 'en_pause' ? 'En pause' : s === 'cloture' ? 'Clôturé' : s === 'fini' ? 'Fini' : '—';
    const progressFallback = s =>
        s === 'fini' || s === 'cloture' ? 100 : s === 'en_pause' ? 50 : 75;

    const bulkBar = `<div class="bulk-actions-bar" id="bulkActionsBar">
        <span class="selected-count"><span id="selectedCount">0</span> sélectionné(s)</span>
        <button class="btn btn-primary" id="bulkStatus" title="Changer le statut"><i class="fas fa-tag"></i> Statut</button>
        <button class="btn btn-danger" id="bulkDelete" title="Supprimer"><i class="fas fa-trash"></i> Supprimer</button>
        <button class="btn" id="bulkCancel">Annuler</button>
    </div>`;

    const listContainer = document.createElement('div');
    listContainer.className = 'project-list';
    listContainer.id = 'projectsList';

    projets.forEach(p => {
        const prog = typeof p.taux_avancement === 'number' ? Math.round(p.taux_avancement) : progressFallback(p.statut);

        const item = document.createElement('div');
        item.className = 'project-item';
        item.dataset.id = p.id;
        item.dataset.status = p.statut;
        item.dataset.culture = p.culture_id;
        item.dataset.date = p.date_lancement;
        item.dataset.cultureName = p.culture_nom;
        item.dataset.nom = p.nom;
        item.dataset.rendement = p.rendement_estime;
        item.dataset.superficie = p.superficie;
        item.dataset.progress = String(prog);

        // Checkbox
        const checkbox = document.createElement('div');
        checkbox.className = 'project-checkbox';
        checkbox.addEventListener('click', (e) => toggleProjectSelection(e, p.id));
        item.appendChild(checkbox);

        // Project info
        const info = document.createElement('div');
        info.className = 'project-info';
        info.addEventListener('click', () => { window.location.href = '/projet/' + encodeURIComponent(p.id) + '/'; });

        const nameDiv = document.createElement('div');
        nameDiv.className = 'project-name editable';
        nameDiv.dataset.id = p.id;
        nameDiv.textContent = p.nom;
        if (typeof editProjectName === 'function') {
            nameDiv.addEventListener('dblclick', (e) => editProjectName(e, p.id, p.nom));
        }
        info.appendChild(nameDiv);

        const meta = document.createElement('div');
        meta.className = 'project-meta';
        if (showFerme && p.ferme_nom) {
            const farmBadgeEl = document.createElement('span');
            farmBadgeEl.className = 'farm-badge';
            farmBadgeEl.innerHTML = '<i class="fas fa-warehouse"></i> ';
            const farmText = document.createElement('span');
            farmText.textContent = p.ferme_nom;
            farmBadgeEl.appendChild(farmText);
            meta.appendChild(farmBadgeEl);
        }

        const cultureSpan = document.createElement('span');
        cultureSpan.innerHTML = '<i class="fas fa-seedling"></i> ';
        const cultureText = document.createElement('span');
        cultureText.textContent = p.culture_nom;
        cultureSpan.appendChild(cultureText);
        meta.appendChild(cultureSpan);

        const superficieSpan = document.createElement('span');
        superficieSpan.innerHTML = '<i class="fas fa-map"></i> ';
        const superficieText = document.createElement('span');
        superficieText.textContent = p.superficie + ' ha';
        superficieSpan.appendChild(superficieText);
        meta.appendChild(superficieSpan);
        info.appendChild(meta);

        const progressWrap = document.createElement('div');
        progressWrap.className = 'project-progress';
        const progressBar = document.createElement('div');
        progressBar.className = 'project-progress-bar';
        progressBar.style.width = prog + '%';
        progressWrap.appendChild(progressBar);
        info.appendChild(progressWrap);

        const progressMeta = document.createElement('div');
        progressMeta.className = 'project-progress-meta';
        const progLabel = document.createElement('span');
        progLabel.textContent = 'Progression';
        progressMeta.appendChild(progLabel);
        const progStrong = document.createElement('strong');
        progStrong.textContent = prog + '%';
        progressMeta.appendChild(progStrong);
        info.appendChild(progressMeta);
        item.appendChild(info);

        // Status badge
        const statusBadge = document.createElement('span');
        statusBadge.className = 'status-badge status-' + p.statut;
        statusBadge.textContent = statusLabel(p.statut);
        statusBadge.addEventListener('click', (e) => {
            e.stopPropagation();
            showStatusModal(p.id, p.statut);
        });
        item.appendChild(statusBadge);

        // Mini stats
        const miniStats = document.createElement('div');
        miniStats.className = 'mini-p-stats';
        const stat1 = document.createElement('span');
        stat1.innerHTML = '<i class="fas fa-crop-alt"></i> ';
        const stat1Text = document.createElement('span');
        stat1Text.textContent = p.superficie + ' ha';
        stat1.appendChild(stat1Text);
        miniStats.appendChild(stat1);
        const stat2 = document.createElement('span');
        stat2.innerHTML = '<i class="fas fa-weight"></i> ';
        const stat2Text = document.createElement('span');
        stat2Text.textContent = (p.rendement_estime || '-') + ' kg';
        stat2.appendChild(stat2Text);
        miniStats.appendChild(stat2);
        item.appendChild(miniStats);

        // Actions
        const actions = document.createElement('div');
        actions.className = 'mini-p-actions';

        const viewBtn = document.createElement('a');
        viewBtn.href = '/projet/' + encodeURIComponent(p.id) + '/';
        viewBtn.className = 'btn-baay btn-baay-outline py-1 px-2 text-xs';
        viewBtn.title = 'Voir';
        viewBtn.innerHTML = '<i class="fas fa-eye"></i>';
        viewBtn.addEventListener('click', (e) => e.stopPropagation());
        actions.appendChild(viewBtn);

        const editBtn = document.createElement('a');
        editBtn.href = '/projet/' + encodeURIComponent(p.id) + '/modifier/';
        editBtn.className = 'btn-baay btn-baay-ghost py-1 px-2 text-xs';
        editBtn.title = 'Modifier';
        editBtn.innerHTML = '<i class="fas fa-edit"></i>';
        editBtn.addEventListener('click', (e) => e.stopPropagation());
        actions.appendChild(editBtn);

        const predictBtn = document.createElement('a');
        predictBtn.href = '/projet/' + encodeURIComponent(p.id) + '/generer_prediction/';
        predictBtn.className = 'btn-baay btn-baay-primary py-1 px-3 text-xs';
        predictBtn.title = 'IA Prediction';
        predictBtn.innerHTML = '<i class="fas fa-robot"></i>';
        predictBtn.addEventListener('click', (e) => e.stopPropagation());
        actions.appendChild(predictBtn);

        item.appendChild(actions);
        listContainer.appendChild(item);
    });

    projectsSection.innerHTML = bulkBar;
    projectsSection.appendChild(listContainer);

    // Re-init context menu and bulk actions on new DOM
    initContextMenu();
    initBulkActions();
    selectedProjects.clear();
}

function updateChartsFromAPI(data) {
    // Store API data for chart rebuilding
    dashboardStatsData = data;
    updateQuickStripFromStats(data);

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

    fetch(buildStatsApiUrl())
        .then(res => {
            if (!res.ok) throw new Error('Network response was not ok');
            return res.json();
        })
        .then(data => {
            dashboardStatsData = data;
            updateQuickStripFromStats(data);
            const isDark = document.body.classList.contains('dark-mode');
            const gridColor = isDark ? 'rgba(226, 232, 240, 0.04)' : 'rgba(15, 23, 42, 0.04)';
            const textCol = isDark ? '#cbd5e1' : '#64748b';
            buildFinanceCockpitCharts(isDark, gridColor, textCol);
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

            const finis = data.projets_par_statut.find(p => p.statut === 'fini');
            const clotures = data.projets_par_statut.find(p => p.statut === 'cloture');
            const totalTermines = (finis ? finis.count : 0) + (clotures ? clotures.count : 0);
            const total = data.nb_projets || 0;

            // Update spotlight stats
            const enCours = data.projets_par_statut.find(p => p.statut === 'en_cours');
            const enPause = data.projets_par_statut.find(p => p.statut === 'en_pause');

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
            const completionRate = total ? Math.round((totalTermines / total) * 100) : 0;
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
