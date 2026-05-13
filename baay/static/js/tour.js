(function () {
    const tourOverlay = document.getElementById('tourOverlay');
    const tourNext = document.getElementById('tourNext');
    const tourSkip = document.getElementById('tourSkip');
    const tourProgress = document.getElementById('tourProgress');
    const openGuideBtn = document.getElementById('openGuideBtn');
    const tourCloseBtn = document.getElementById('tourCloseBtn');
    const tourStepLabel = document.getElementById('tourStepLabel');
    const tourIconEl = document.getElementById('tourIconEl');
    const tourTitle = document.getElementById('tourTitle');
    const tourDesc = document.getElementById('tourDesc');
    const tourTips = document.getElementById('tourTips');

    if (!tourOverlay || !tourNext || !tourSkip || !tourProgress || !openGuideBtn || !tourStepLabel || !tourIconEl || !tourTitle || !tourDesc || !tourTips) {
        return;
    }

    const TOUR_KEY = 'anddbaay_tour_done_v3';

    /* ── Action system ─────────────────────────────────────── */
    let actionCompleted = false;
    let actionCleanup = null;

    function resetAction() {
        actionCompleted = false;
        if (actionCleanup) { actionCleanup(); actionCleanup = null; }
    }

    function setupAction(step) {
        resetAction();
        if (!step.action) return;

        const { type, target } = step.action;

        if (type === 'click') {
            const el = document.querySelector(target);
            if (!el) return;
            const handler = () => {
                actionCompleted = true;
                updateNextButton();
                el.classList.remove('tour-highlight-pulse');
            };
            el.classList.add('tour-highlight-pulse');
            el.addEventListener('click', handler, { once: true });
            actionCleanup = () => {
                el.removeEventListener('click', handler);
                el.classList.remove('tour-highlight-pulse');
            };
        } else if (type === 'theme') {
            const toggle = document.getElementById('themeToggle') || document.getElementById('themeToggleMobile');
            if (!toggle) return;
            const handler = () => {
                actionCompleted = true;
                updateNextButton();
                if (toggle) toggle.classList.remove('tour-highlight-pulse');
            };
            if (toggle) {
                toggle.classList.add('tour-highlight-pulse');
                toggle.addEventListener('click', handler, { once: true });
            }
            actionCleanup = () => {
                if (toggle) {
                    toggle.removeEventListener('click', handler);
                    toggle.classList.remove('tour-highlight-pulse');
                }
            };
        }
    }

    function updateNextButton() {
        const s = tourSteps[currentStep];
        const total = tourSteps.length;
        const isLast = currentStep === total - 1;

        if (s.action && !actionCompleted) {
            tourNext.disabled = true;
            tourNext.classList.add('tour-next-locked');
            tourNext.innerHTML = `<i class="fas fa-hand-pointer"></i> ${s.action.prompt || 'Essayez ci-dessus'}`;
        } else {
            tourNext.disabled = false;
            tourNext.classList.remove('tour-next-locked');
            if (isLast) {
                tourNext.innerHTML = `C'est parti ! <i class="fas fa-check ms-1"></i>`;
            } else {
                tourNext.innerHTML = `Suivant <i class="fas fa-arrow-right"></i>`;
            }
        }
    }

    /* ── Animated demo helpers ──────────────────────────────── */
    function buildDemo(type) {
        if (type === 'cursor-click') {
            return `<div class="tour-demo-cursor"><div class="demo-cursor-dot"></div><div class="demo-cursor-ring"></div></div>`;
        }
        if (type === 'phone-install') {
            return `<div class="tour-demo-phone">
                <div class="demo-phone-notch"></div>
                <div class="demo-phone-screen">
                    <div class="demo-phone-bar"><i class="fas fa-ellipsis-v"></i></div>
                    <div class="demo-phone-icon"><i class="fas fa-seedling"></i></div>
                    <div class="demo-phone-label">Andd Baay</div>
                </div>
            </div>`;
        }
        if (type === 'typing-chat') {
            return `<div class="tour-demo-chat">
                <div class="demo-chat-bubble demo-chat-user">Quand irriguer le mil ?</div>
                <div class="demo-chat-bubble demo-chat-bot"><span class="demo-typing"><span></span><span></span><span></span></span></div>
            </div>`;
        }
        if (type === 'chart-pulse') {
            return `<div class="tour-demo-chart">
                <div class="demo-chart-bar" style="--bar-h:40%"></div>
                <div class="demo-chart-bar" style="--bar-h:65%"></div>
                <div class="demo-chart-bar" style="--bar-h:50%"></div>
                <div class="demo-chart-bar" style="--bar-h:80%"></div>
                <div class="demo-chart-bar" style="--bar-h:55%"></div>
                <div class="demo-chart-bar" style="--bar-h:90%"></div>
            </div>`;
        }
        return '';
    }

    /* ── Tour steps ─────────────────────────────────────────── */
    const tourSteps = [
        {
            icon: 'fa-seedling',
            title: 'Bienvenue sur Andd Baay 🌱',
            desc: 'La plateforme intelligente pour gérer vos cultures, prédire vos rendements et optimiser chaque récolte — même au champ.',
            demo: 'cursor-click',
            tips: [
                { icon: 'fa-map', title: 'Une plateforme tout-en-un', text: 'Gérez vos projets agricoles, suivez vos semis et obtenez des prédictions de rendement basées sur l\'IA.' },
                { icon: 'fa-moon', title: 'Mode jour / nuit', text: 'Utilisez le bouton 🌙 en haut à droite pour changer de thème selon vos préférences.' },
                { icon: 'fa-question-circle', title: 'Ce guide toujours accessible', text: 'Cliquez à tout moment sur le bouton <strong>?</strong> dans la barre de navigation pour relancer ce guide.' },
            ]
        },
        {
            icon: 'fa-moon',
            title: 'Essayez le mode sombre 🌙',
            desc: 'Changez de thème maintenant ! Cliquez sur le bouton lune/soleil dans la barre de navigation pour débloquer l\'étape suivante.',
            action: {
                type: 'theme',
                prompt: 'Cliquez sur 🌙 pour débloquer'
            },
            demo: null,
            tips: [
                { icon: 'fa-adjust', title: 'Thème adaptatif', text: 'Le mode sombre réduit la fatigue oculaire, surtout en plein soleil au champ.' },
                { icon: 'fa-palette', title: 'Couleurs optimisées', text: 'Les couleurs s\'adaptent automatiquement pour garantir la lisibilité dans les deux modes.' },
            ]
        },
        {
            icon: 'fa-mobile-alt',
            title: 'Application mobile & PWA 📱',
            desc: 'Andd Baay fonctionne comme une application native sur votre téléphone, même sans connexion internet.',
            demo: 'phone-install',
            tips: [
                { icon: 'fa-download', title: 'Installer l\'application', text: 'Sur Android / iOS : ouvrez Chrome → menu ⋮ → « Ajouter à l\'écran d\'accueil ». L\'app se lance en plein écran.' },
                { icon: 'fa-wifi', title: 'Mode hors-ligne', text: 'Pas de réseau au champ ? Les pages déjà visitées restent accessibles. Le cache se met à jour automatiquement.' },
                { icon: 'fa-location-arrow', title: 'GPS intégré', text: 'Lors de la création d\'une ferme, utilisez le bouton « Me localiser » pour remplir latitude et longitude automatiquement.' },
                { icon: 'fa-camera', title: 'Photos directes', text: 'Prenez des photos de vos plants avec l\'appareil photo du téléphone — pas besoin d\'ouvrir la galerie.' },
            ]
        },
        {
            icon: 'fa-folder-plus',
            title: 'Créer votre premier projet',
            desc: 'Un projet représente une parcelle agricole avec ses cultures, sa superficie et ses objectifs de rendement.',
            demo: 'cursor-click',
            tryIt: { label: 'Créer un projet', url: '/creer-projet/' },
            tips: [
                { icon: 'fa-plus', title: 'Bouton « Nouveau »', text: 'Cliquez sur <strong>Nouveau</strong> dans la navbar ou sur la page Projets pour créer votre premier projet.' },
                { icon: 'fa-map-marker-alt', title: 'Sélectionner une localité', text: 'Choisissez votre région pour que nos algorithmes utilisent les données météo et sol adaptées.' },
                { icon: 'fa-leaf', title: 'Choisir vos cultures', text: 'Sélectionnez une ou plusieurs cultures. Le système calcule automatiquement le rendement estimé.' },
                { icon: 'fa-map-marker-alt', title: 'Géolocalisez votre ferme', text: 'Lors de la création d\'une ferme, utilisez le bouton « Me localiser » pour enregistrer les coordonnées GPS automatiquement.' },
            ]
        },
        {
            icon: 'fa-chart-pie',
            title: 'Le Dashboard analytique',
            desc: 'Votre centre de commande : statistiques, graphiques et suivi en temps réel de tous vos projets.',
            demo: 'chart-pulse',
            tryIt: { label: 'Ouvrir le dashboard', url: '/dashboard/' },
            tips: [
                { icon: 'fa-chart-bar', title: 'Graphiques interactifs', text: 'Analysez l\'évolution de vos superficies et rendements mois par mois avec les graphiques du dashboard.' },
                { icon: 'fa-sliders-h', title: 'Filtres avancés', text: 'Filtrez par statut, culture ou période pour affiner votre analyse.' },
                { icon: 'fa-mouse-pointer', title: 'Cliquez sur les KPI', text: 'Cliquez sur les tuiles (superficie, rendement...) pour voir les projets correspondants.' },
            ]
        },
        {
            icon: 'fa-seedling',
            title: 'Suivi de vos Semis',
            desc: 'Enregistrez chaque semis avec sa date, sa superficie et suivez l\'évolution jusqu\'à la récolte.',
            demo: null,
            tips: [
                { icon: 'fa-calendar-alt', title: 'Dates de semis et récolte', text: 'Saisissez les dates de semis et récolte prévues pour chaque culture de vos projets.' },
                { icon: 'fa-camera', title: 'Photos directes depuis le téléphone', text: 'Prenez des photos de vos plants avec l\'appareil photo — les images sont compressées automatiquement pour économiser la bande passante.' },
                { icon: 'fa-check-circle', title: 'Clôturer un projet', text: 'Quand la récolte est terminée, saisissez le rendement final pour entraîner le modèle IA.' },
            ]
        },
        {
            icon: 'fa-robot',
            title: 'L\'Assistant IA 🤖',
            desc: 'Posez vos questions agricoles en langage naturel — météo, maladies, conseils, prédictions.',
            demo: 'typing-chat',
            action: {
                type: 'click',
                target: '#messagerieBubble',
                prompt: 'Ouvrez la messagerie pour débloquer'
            },
            tips: [
                { icon: 'fa-comment-dots', title: 'Disponible partout', text: 'Cliquez sur le bouton bleu en bas à droite (ou dans la nav mobile) pour ouvrir l\'assistant à tout moment.' },
                { icon: 'fa-history', title: 'Historique conservé', text: 'Vos conversations sont sauvegardées localement et restaurées à chaque visite — même hors-ligne.' },
                { icon: 'fa-lightbulb', title: 'Exemples de questions', text: '"Quand irriguer le mil ?" — "Quels semences pour la saison sèche ?" — "Analyse mon rendement."' },
            ]
        }
    ];

    let currentStep = 0;

    function renderStep(step) {
        const s = tourSteps[step];
        const total = tourSteps.length;

        tourStepLabel.textContent = `Étape ${step + 1} sur ${total}`;
        tourIconEl.className = `fas ${s.icon}`;
        tourTitle.textContent = s.title;
        tourDesc.textContent = s.desc;

        // Build tips with optional demo and try-it
        let html = '';

        if (s.demo) {
            html += `<div class="tour-demo">${buildDemo(s.demo)}</div>`;
        }

        html += s.tips.map(t => `
            <div class="tour-tip">
                <div class="tour-tip-icon"><i class="fas ${t.icon}"></i></div>
                <div class="tour-tip-text">
                    <strong>${t.title}</strong>
                    <span>${t.text}</span>
                </div>
            </div>
        `).join('');

        if (s.tryIt) {
            html += `<a href="${s.tryIt.url}" class="tour-try-it" onclick="document.getElementById('tourOverlay').classList.remove('active');">
                <i class="fas fa-external-link-alt"></i> ${s.tryIt.label}
            </a>`;
        }

        tourTips.innerHTML = html;

        // Re-trigger stagger animation by forcing reflow on each tip
        requestAnimationFrame(() => {
            const tips = tourTips.querySelectorAll('.tour-tip');
            tips.forEach((tip) => {
                tip.style.animation = 'none';
                void tip.offsetHeight;
                tip.style.animation = '';
            });
        });

        const progressFill = document.getElementById('tourProgressFill');
        if (progressFill) {
            progressFill.style.width = `${((step + 1) / total) * 100}%`;
        }

        tourProgress.innerHTML = tourSteps.map((_, i) => `
            <button type="button" class="tour-dot ${i === step ? 'active' : i < step ? 'done' : ''}" data-step="${i}" aria-label="Aller à l'étape ${i + 1}"></button>
        `).join('');

        // Setup action-driven step
        setupAction(s);
        updateNextButton();

        if (step === total - 1) {
            tourSkip.style.display = 'none';
        } else {
            tourSkip.style.display = '';
        }
    }

    function nextStep() {
        if (currentStep < tourSteps.length - 1) {
            currentStep++;
            renderStep(currentStep);
        }
    }

    function goToStep(index) {
        currentStep = index;
        renderStep(currentStep);
    }

    function openTour() {
        currentStep = 0;
        renderStep(0);
        tourOverlay.classList.add('active');
        updateGuideFab();
    }

    function closeTour() {
        resetAction();
        tourOverlay.classList.remove('active');
        localStorage.setItem(TOUR_KEY, '1');
        updateGuideFab();
    }

    tourSkip.addEventListener('click', closeTour);
    tourNext.addEventListener('click', () => {
        const s = tourSteps[currentStep];
        if (s.action && !actionCompleted) return;
        if (currentStep === tourSteps.length - 1) {
            closeTour();
        } else {
            nextStep();
        }
    });

    tourProgress.addEventListener('click', (event) => {
        const target = event.target.closest('[data-step]');
        if (target) {
            goToStep(Number(target.dataset.step));
        }
    });

    // Close button in header
    if (tourCloseBtn) {
        tourCloseBtn.addEventListener('click', closeTour);
    }

    openGuideBtn.addEventListener('click', openTour);

    // Guide FAB button
    const guideFab = document.getElementById('guideFab');
    if (guideFab) {
        guideFab.addEventListener('click', openTour);
    }

    function updateGuideFab() {
        if (guideFab) {
            if (tourOverlay.classList.contains('active')) {
                guideFab.style.opacity = '0';
                guideFab.style.pointerEvents = 'none';
                guideFab.style.transform = 'scale(0.8)';
            } else {
                guideFab.style.opacity = '';
                guideFab.style.pointerEvents = '';
                guideFab.style.transform = '';
            }
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        if (!localStorage.getItem(TOUR_KEY)) {
            setTimeout(openTour, 800);
        }
    });
})();
