const projectsState = {
    projects: [],
    visibleProjects: [],
    selectedIds: new Set(),
    sort: { column: null, direction: 'asc' },
    filter: 'all',
    search: '',
    currentView: 'table',
    activeStatusProjectId: null,
    activeContextProjectId: null,
};

document.addEventListener('DOMContentLoaded', () => {
    collectProjects();
    bindToolbar();
    bindSelection();
    bindSorting();
    bindViewToggle();
    bindCardsAndRows();
    bindQuickActions();
    bindQuickView();
    bindContextMenu();
    bindStatusMenu();
    bindShortcuts();
    bindDeleteConfirms();
    initStickyToolbar();
    applyProjectsViewportView();
    window.matchMedia('(max-width: 767.98px)').addEventListener('change', applyProjectsViewportView);
    filterProjects();
});

function collectProjects() {
    document.querySelectorAll('#projectsTable tr[data-id]').forEach((row) => {
        projectsState.projects.push({
            id: row.dataset.id,
            name: row.dataset.name || '',
            culture: row.dataset.culture || '',
            products: row.dataset.products || '',
            status: row.dataset.status || '',
            superficie: parseFloat(row.dataset.superficie) || 0,
            date: row.dataset.date || '',
            detailUrl: row.dataset.detailUrl || '#',
            editUrl: row.dataset.editUrl || '#',
            predictUrl: row.dataset.predictUrl || '#',
            deleteUrl: row.dataset.deleteUrl || '#',
        });
    });
}

function bindToolbar() {
    const searchInput = document.getElementById('searchInput');
    const clearBtn = document.getElementById('clearSearch');
    const refreshBtn = document.getElementById('refreshBtn');
    const shortcutsBtn = document.getElementById('shortcutsBtn');
    let searchTimeout = null;

    searchInput?.addEventListener('input', () => {
        projectsState.search = searchInput.value.trim().toLowerCase();
        clearBtn?.classList.toggle('is-visible', Boolean(projectsState.search));
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(filterProjects, 180);
    });

    clearBtn?.addEventListener('click', () => {
        searchInput.value = '';
        projectsState.search = '';
        clearBtn.classList.remove('is-visible');
        filterProjects();
        searchInput.focus();
    });

    document.querySelectorAll('.filter-chip').forEach((chip) => {
        chip.addEventListener('click', () => {
            projectsState.filter = chip.dataset.filter || 'all';
            document.querySelectorAll('.filter-chip').forEach((item) => item.classList.remove('is-active'));
            chip.classList.add('is-active');
            filterProjects();
        });
    });

    refreshBtn?.addEventListener('click', refreshPage);
    shortcutsBtn?.addEventListener('click', toggleShortcutsPanel);
    document.getElementById('closeShortcutsBtn')?.addEventListener('click', toggleShortcutsPanel);
}

function bindSelection() {
    const selectAll = document.getElementById('selectAll');

    selectAll?.addEventListener('change', () => {
        document.querySelectorAll('#projectsTable tr[data-id]').forEach((row) => {
            const visible = row.style.display !== 'none';
            const checkbox = row.querySelector('.project-checkbox');
            if (!checkbox || !visible) return;
            checkbox.checked = selectAll.checked;
            setSelected(row.dataset.id, selectAll.checked);
        });
        syncCardSelections();
        updateSelectionUi();
    });

    document.querySelectorAll('.project-checkbox').forEach((checkbox) => {
        checkbox.addEventListener('change', () => {
            const row = checkbox.closest('tr[data-id]');
            if (!row) return;
            setSelected(row.dataset.id, checkbox.checked);
            syncCardSelections();
            updateSelectionUi();
        });
    });

    document.querySelectorAll('[data-card-checkbox]').forEach((button) => {
        button.addEventListener('click', (event) => {
            event.stopPropagation();
            const id = button.dataset.cardCheckbox;
            const nextValue = !projectsState.selectedIds.has(id);
            setSelected(id, nextValue);
            syncRowSelections();
            syncCardSelections();
            updateSelectionUi();
        });
    });

    document.getElementById('delete-form')?.addEventListener('submit', (event) => {
        if (projectsState.selectedIds.size === 0) {
            event.preventDefault();
            showToast('Selectionnez au moins un projet.', 'error');
            return;
        }

        const confirmed = window.confirm(`Supprimer ${projectsState.selectedIds.size} projet(s) ?`);
        if (!confirmed) event.preventDefault();
    });
}

function bindSorting() {
    document.querySelectorAll('th.sortable').forEach((header) => {
        header.addEventListener('click', () => {
            const column = header.dataset.sort;
            if (!column) return;

            if (projectsState.sort.column === column) {
                projectsState.sort.direction = projectsState.sort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                projectsState.sort.column = column;
                projectsState.sort.direction = 'asc';
            }

            document.querySelectorAll('th.sortable').forEach((item) => item.classList.remove('sort-asc', 'sort-desc'));
            header.classList.add(projectsState.sort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
            sortRows();
            filterProjects();
        });
    });
}

function sortRows() {
    if (!projectsState.sort.column) return;

    const tbody = document.getElementById('projectsTable');
    if (!tbody) return;

    const rows = Array.from(tbody.querySelectorAll('tr[data-id]'));
    const direction = projectsState.sort.direction === 'asc' ? 1 : -1;
    const column = projectsState.sort.column;

    rows.sort((a, b) => {
        let valueA = a.dataset[column] || '';
        let valueB = b.dataset[column] || '';

        if (column === 'superficie') {
            valueA = parseFloat(valueA) || 0;
            valueB = parseFloat(valueB) || 0;
        }

        if (column === 'date') {
            valueA = new Date(valueA);
            valueB = new Date(valueB);
        }

        if (valueA < valueB) return -1 * direction;
        if (valueA > valueB) return 1 * direction;
        return 0;
    });

    rows.forEach((row) => tbody.appendChild(row));
}

function bindViewToggle() {
    document.querySelectorAll('.view-toggle button').forEach((button) => {
        button.addEventListener('click', () => setView(button.dataset.view || 'table'));
    });
}

function applyProjectsViewportView() {
    const saved = localStorage.getItem('projectsView');
    const isMobile = window.matchMedia('(max-width: 767.98px)').matches;
    if (isMobile) {
        setView(saved === 'table' ? 'table' : 'grid');
    } else {
        setView(saved || 'table');
    }
}

function setView(view) {
    projectsState.currentView = view === 'grid' ? 'grid' : 'table';

    document.querySelectorAll('.view-toggle button').forEach((button) => {
        button.classList.toggle('is-active', button.dataset.view === projectsState.currentView);
    });

    document.getElementById('tableView')?.classList.toggle('is-active', projectsState.currentView === 'table');
    document.getElementById('gridView')?.classList.toggle('is-active', projectsState.currentView === 'grid');
    localStorage.setItem('projectsView', projectsState.currentView);
}

function bindCardsAndRows() {
    document.querySelectorAll('#projectsTable tr[data-id]').forEach((row) => {
        row.addEventListener('dblclick', (event) => {
            if (event.target.closest('a, button, input, .quick-actions-menu')) return;
            window.location.href = row.dataset.detailUrl;
        });
    });

    document.querySelectorAll('[data-quick-view]').forEach((button) => {
        button.addEventListener('click', () => openQuickView(button.dataset.quickView));
    });

    document.querySelectorAll('.project-name-cell.editable').forEach((cell) => {
        cell.addEventListener('dblclick', (event) => {
            event.stopPropagation();
            startInlineEdit(cell);
        });
    });
}

function bindQuickActions() {
    document.querySelectorAll('[data-menu-trigger]').forEach((button) => {
        button.addEventListener('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            const menu = document.getElementById(`quickActions-${button.dataset.menuTrigger}`);
            document.querySelectorAll('.quick-actions-menu').forEach((item) => {
                if (item !== menu) item.classList.remove('is-open');
            });
            menu?.classList.toggle('is-open');
        });
    });

    document.addEventListener('click', (event) => {
        if (!event.target.closest('.action-menu-trigger') && !event.target.closest('.quick-actions-menu')) {
            document.querySelectorAll('.quick-actions-menu').forEach((menu) => menu.classList.remove('is-open'));
        }
    });
}

function bindQuickView() {
    document.querySelectorAll('[data-close-quick-view]').forEach((button) => {
        button.addEventListener('click', closeQuickView);
    });

    document.getElementById('quickViewModal')?.addEventListener('click', (event) => {
        if (event.target.id === 'quickViewModal') closeQuickView();
    });
}

function bindContextMenu() {
    const contextMenu = document.getElementById('contextMenu');
    const ctxView = document.getElementById('ctxView');
    const ctxEdit = document.getElementById('ctxEdit');
    const ctxPredict = document.getElementById('ctxPredict');
    const ctxDelete = document.getElementById('ctxDelete');
    const ctxStatus = document.getElementById('ctxStatus');

    document.querySelectorAll('#projectsTable tr[data-id], .project-card').forEach((item) => {
        item.addEventListener('contextmenu', (event) => {
            event.preventDefault();
            const id = item.dataset.id;
            const project = findProject(id);
            if (!project || !contextMenu) return;

            projectsState.activeContextProjectId = id;
            ctxView.href = project.detailUrl;
            ctxEdit.href = project.editUrl;
            ctxPredict.href = project.predictUrl;
            ctxDelete.href = project.deleteUrl;
            ctxStatus.dataset.projectId = id;

            contextMenu.style.left = `${event.pageX}px`;
            contextMenu.style.top = `${event.pageY}px`;
            contextMenu.classList.add('is-open');
        });
    });

    ctxStatus?.addEventListener('click', () => {
        if (!projectsState.activeContextProjectId) return;
        openStatusMenu(projectsState.activeContextProjectId, ctxStatus);
        contextMenu?.classList.remove('is-open');
    });

    document.addEventListener('click', (event) => {
        if (!event.target.closest('#contextMenu')) contextMenu?.classList.remove('is-open');
    });
}

function bindStatusMenu() {
    document.querySelectorAll('[data-status-trigger]').forEach((button) => {
        button.addEventListener('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            openStatusMenu(button.dataset.id, button);
        });
    });

    document.querySelectorAll('.status-menu-item').forEach((item) => {
        item.addEventListener('click', () => {
            if (!projectsState.activeStatusProjectId) return;
            updateStatus(projectsState.activeStatusProjectId, item.dataset.statusValue);
        });
    });

    document.addEventListener('click', (event) => {
        if (!event.target.closest('#statusMenu') && !event.target.closest('[data-status-trigger]')) {
            closeStatusMenu();
        }
    });
}

function openStatusMenu(projectId, anchor) {
    const menu = document.getElementById('statusMenu');
    if (!menu || !anchor) return;

    const rect = anchor.getBoundingClientRect();
    projectsState.activeStatusProjectId = projectId;
    menu.style.left = `${window.scrollX + rect.left}px`;
    menu.style.top = `${window.scrollY + rect.bottom + 6}px`;
    menu.classList.add('is-open');
}

function closeStatusMenu() {
    document.getElementById('statusMenu')?.classList.remove('is-open');
    projectsState.activeStatusProjectId = null;
}

function bindShortcuts() {
    const createProjectUrl = document.querySelector('.projects-hero-actions .btn-accent')?.getAttribute('href') || '/creer-projet/';

    document.addEventListener('keydown', (event) => {
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA' || event.target.isContentEditable) {
            return;
        }

        if (event.key === '?') {
            event.preventDefault();
            toggleShortcutsPanel();
            return;
        }

        if (event.key === '/') {
            event.preventDefault();
            document.getElementById('searchInput')?.focus();
            return;
        }

        if (event.key.toLowerCase() === 'n') {
            event.preventDefault();
            window.location.href = createProjectUrl;
            return;
        }

        if (event.key.toLowerCase() === 'g') {
            event.preventDefault();
            setView('grid');
            return;
        }

        if (event.key.toLowerCase() === 't') {
            event.preventDefault();
            setView('table');
            return;
        }

        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'a') {
            event.preventDefault();
            document.getElementById('selectAll')?.click();
            return;
        }

        if (event.key === 'Delete' && projectsState.selectedIds.size > 0) {
            event.preventDefault();
            document.getElementById('delete-form')?.requestSubmit();
            return;
        }

        if (event.key === 'Escape') {
            closeQuickView();
            closeStatusMenu();
            document.getElementById('contextMenu')?.classList.remove('is-open');
            document.querySelectorAll('.quick-actions-menu').forEach((menu) => menu.classList.remove('is-open'));
            document.getElementById('shortcutsPanel')?.classList.remove('is-open');
        }
    });
}

function bindDeleteConfirms() {
    document.querySelectorAll('[data-confirm-delete]').forEach((link) => {
        link.addEventListener('click', (event) => {
            const confirmed = window.confirm('Vraiment supprimer ce projet ?');
            if (!confirmed) event.preventDefault();
        });
    });
}

function filterProjects() {
    const query = projectsState.search;
    const filter = projectsState.filter;
    projectsState.visibleProjects = [];

    document.querySelectorAll('#projectsTable tr[data-id]').forEach((row) => {
        const matches = projectMatches(row.dataset, query, filter);
        row.style.display = matches ? '' : 'none';
        if (matches) {
            const project = findProject(row.dataset.id);
            if (project) projectsState.visibleProjects.push(project);
        }
    });

    document.querySelectorAll('.project-card[data-id]').forEach((card) => {
        const matches = projectMatches(card.dataset, query, filter);
        card.style.display = matches ? '' : 'none';
    });

    updateSummary();
    updateSelectionUi();
}

function projectMatches(dataset, query, filter) {
    const matchesSearch = !query || `${dataset.name} ${dataset.culture} ${dataset.products}`.includes(query);
    const matchesFilter = filter === 'all' || dataset.status === filter;
    return matchesSearch && matchesFilter;
}

function updateSummary() {
    const visible = projectsState.visibleProjects;
    const active = visible.filter((project) => project.status === 'en_cours').length;
    const area = visible.reduce((sum, project) => sum + project.superficie, 0);

    setText('projectsVisibleCount', visible.length.toLocaleString('fr-FR'));
    setText('projectsActiveCount', active.toLocaleString('fr-FR'));
    setText('projectsAreaCount', `${area.toLocaleString('fr-FR')} ha`);
}

function setSelected(id, selected) {
    if (selected) {
        projectsState.selectedIds.add(id);
    } else {
        projectsState.selectedIds.delete(id);
    }
}

function syncRowSelections() {
    document.querySelectorAll('#projectsTable tr[data-id]').forEach((row) => {
        const isSelected = projectsState.selectedIds.has(row.dataset.id);
        row.classList.toggle('is-selected', isSelected);
        const checkbox = row.querySelector('.project-checkbox');
        if (checkbox) checkbox.checked = isSelected;
    });
}

function syncCardSelections() {
    document.querySelectorAll('.project-card[data-id]').forEach((card) => {
        const isSelected = projectsState.selectedIds.has(card.dataset.id);
        card.classList.toggle('is-selected', isSelected);
        const checkbox = card.querySelector('.project-card-checkbox');
        checkbox?.classList.toggle('is-checked', isSelected);
    });
}

function updateSelectionUi() {
    syncRowSelections();
    syncCardSelections();

    const count = projectsState.selectedIds.size;
    const deleteBtn = document.getElementById('deleteBtn');
    const deleteCount = document.getElementById('deleteCount');
    const selectionMeta = document.getElementById('projectsSelectionMeta');
    const visibleRows = Array.from(document.querySelectorAll('#projectsTable tr[data-id]')).filter((row) => row.style.display !== 'none');
    const selectAll = document.getElementById('selectAll');

    deleteBtn?.classList.toggle('is-active', count > 0);
    setText('deleteCount', `Supprimer (${count})`);
    setText('projectsSelectionMeta', `${count} selectionne${count > 1 ? 's' : ''}`);

    if (selectionMeta) {
        selectionMeta.textContent = `${count} selectionne${count > 1 ? 's' : ''}`;
    }

    if (deleteCount) {
        deleteCount.textContent = `Supprimer (${count})`;
    }

    if (selectAll) {
        const checkedVisible = visibleRows.filter((row) => projectsState.selectedIds.has(row.dataset.id)).length;
        selectAll.checked = visibleRows.length > 0 && checkedVisible === visibleRows.length;
    }
}

function startInlineEdit(cell) {
    if (cell.classList.contains('editing')) return;

    const original = cell.dataset.original || cell.textContent.trim();
    const projectId = cell.dataset.id;
    cell.classList.add('editing');
    cell.innerHTML = `<input type="text" class="project-name-input" value="${original}" aria-label="Modifier le nom du projet">`;

    const input = cell.querySelector('input');
    input.focus();
    input.select();

    const finish = (save) => {
        const nextValue = input.value.trim();
        const value = save && nextValue ? nextValue : original;
        cell.textContent = value;
        cell.dataset.original = value;
        cell.classList.remove('editing');

        const project = findProject(projectId);
        if (project) project.name = value.toLowerCase();

        document.querySelectorAll(`[data-id="${projectId}"]`).forEach((element) => {
            element.dataset.name = value.toLowerCase();
        });
        document.querySelectorAll(`.project-card[data-id="${projectId}"] .project-card-title`).forEach((title) => {
            title.textContent = value;
        });

        if (save && nextValue && nextValue !== original) {
            showToast('Nom mis a jour.', 'success');
        }
    };

    input.addEventListener('blur', () => finish(true));
    input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            finish(true);
        }
        if (event.key === 'Escape') {
            event.preventDefault();
            finish(false);
        }
    });
}

function openQuickView(projectId) {
    const project = findProject(projectId);
    const modal = document.getElementById('quickViewModal');
    if (!project || !modal) return;

    const row = document.querySelector(`#projectsTable tr[data-id="${projectId}"]`);
    const culture = row?.querySelector('.project-culture')?.textContent?.trim() || project.culture || 'N/A';
    const statusLabel = project.status === 'en_cours' ? 'En cours' : project.status === 'en_pause' ? 'En pause' : 'Termine';
    const progress = project.status === 'fini' ? '100%' : project.status === 'en_pause' ? '50%' : '75%';

    setText('quickViewTitle', row?.querySelector('.project-name-cell')?.textContent?.trim() || project.name);
    document.getElementById('quickViewEdit').href = project.editUrl;
    document.getElementById('quickViewContent').innerHTML = `
        <div class="modal-detail-row">
            <span class="modal-detail-label">Culture</span>
            <span class="modal-detail-value">${culture}</span>
        </div>
        <div class="modal-detail-row">
            <span class="modal-detail-label">Statut</span>
            <span class="modal-detail-value">${statusLabel}</span>
        </div>
        <div class="modal-detail-row">
            <span class="modal-detail-label">Superficie</span>
            <span class="modal-detail-value">${project.superficie.toLocaleString('fr-FR')} ha</span>
        </div>
        <div class="modal-detail-row">
            <span class="modal-detail-label">Date de lancement</span>
            <span class="modal-detail-value">${formatDate(project.date)}</span>
        </div>
        <div class="modal-detail-row">
            <span class="modal-detail-label">Progression</span>
            <span class="modal-detail-value">${progress}</span>
        </div>
    `;
    modal.classList.add('is-open');
}

function closeQuickView() {
    document.getElementById('quickViewModal')?.classList.remove('is-open');
}

function updateStatus(projectId, newStatus) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

    fetch(`/api/projet/${projectId}/statut/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ statut: newStatus }),
    })
        .then((response) => response.json())
        .then((data) => {
            if (!data.success) {
                showToast('Impossible de mettre a jour le statut.', 'error');
                return;
            }

            const project = findProject(projectId);
            if (project) project.status = newStatus;

            updateStatusInDom(projectId, newStatus);
            closeStatusMenu();
            filterProjects();
            showToast('Statut mis a jour.', 'success');
        })
        .catch(() => showToast('Erreur reseau.', 'error'));
}

function updateStatusInDom(projectId, status) {
    const label = status === 'en_cours' ? 'En cours' : status === 'en_pause' ? 'En pause' : 'Termine';
    const progress = status === 'fini' ? '100%' : status === 'en_pause' ? '50%' : '75%';

    document.querySelectorAll(`[data-id="${projectId}"] .status-badge`).forEach((badge) => {
        badge.className = `status-badge status-${status}`;
        badge.textContent = label;
        if (badge.matches('[data-status-trigger]')) {
            badge.dataset.status = status;
        }
    });

    document.querySelectorAll(`[data-id="${projectId}"] .progress-bar`).forEach((bar) => {
        bar.style.width = progress;
    });

    document.querySelectorAll(`[data-id="${projectId}"] .project-inline-meta strong`).forEach((strong) => {
        strong.textContent = progress;
    });

    document.querySelectorAll(`[data-id="${projectId}"]`).forEach((element) => {
        element.dataset.status = status;
    });
}

function refreshPage() {
    const button = document.getElementById('refreshBtn');
    const icon = button?.querySelector('i');
    if (icon) icon.classList.add('fa-spin');

    showToast('Actualisation...', 'info');

    setTimeout(() => {
        if (icon) icon.classList.remove('fa-spin');
        document.querySelectorAll('#projectsTable tr[data-id]').forEach((row, index) => {
            setTimeout(() => {
                row.classList.add('highlight');
                setTimeout(() => row.classList.remove('highlight'), 900);
            }, index * 40);
        });
        showToast('Vue actualisee.', 'success');
    }, 900);
}

function toggleShortcutsPanel() {
    document.getElementById('shortcutsPanel')?.classList.toggle('is-open');
}

function initStickyToolbar() {
    const toolbar = document.getElementById('actionsBar');
    const hero = document.querySelector('.projects-hero');
    if (!toolbar || !hero) return;

    const threshold = hero.getBoundingClientRect().bottom + window.scrollY;
    window.addEventListener('scroll', () => {
        toolbar.classList.toggle('sticky', window.scrollY > threshold - 40);
    });
}

function findProject(id) {
    return projectsState.projects.find((project) => project.id === id);
}

function formatDate(value) {
    if (!value) return 'N/A';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('fr-FR');
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = { success: 'check', error: 'exclamation', info: 'info' };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-icon"><i class="fas fa-${icons[type] || 'check'}"></i></div>
        <span class="toast-message">${message}</span>
        <button type="button" class="toast-close" aria-label="Fermer"><i class="fas fa-times"></i></button>
    `;

    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('is-visible'));

    toast.querySelector('.toast-close')?.addEventListener('click', () => removeToast(toast));
    setTimeout(() => removeToast(toast), 3500);
}

function removeToast(toast) {
    if (!toast || !toast.parentNode) return;
    toast.classList.remove('is-visible');
    setTimeout(() => toast.remove(), 200);
}
