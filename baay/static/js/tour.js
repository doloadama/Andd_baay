(function () {
    const tourOverlay = document.getElementById('tourOverlay');
    const tourNext = document.getElementById('tourNext');
    const tourSkip = document.getElementById('tourSkip');
    const tourProgress = document.getElementById('tourProgress');
    const openGuideBtn = document.getElementById('openGuideBtn');
    const tourStepLabel = document.getElementById('tourStepLabel');
    const tourIconEl = document.getElementById('tourIconEl');
    const tourTitle = document.getElementById('tourTitle');
    const tourDesc = document.getElementById('tourDesc');
    const tourTips = document.getElementById('tourTips');

    if (!tourOverlay || !tourNext || !tourSkip || !tourProgress || !openGuideBtn || !tourStepLabel || !tourIconEl || !tourTitle || !tourDesc || !tourTips) {
        return;
    }

    const TOUR_KEY = 'anddbaay_tour_done_v1';
    const tourSteps = [
        {
            icon: 'fa-seedling',
            title: 'Bienvenue sur Andd Baay 🌱',
            desc: 'La plateforme intelligente pour gérer vos cultures, prédire vos rendements et optimiser chaque récolte.',
            tips: [
                { icon: 'fa-map', title: 'Une plateforme tout-en-un', text: 'Gérez vos projets agricoles, suivez vos semis et obtenez des prédictions de rendement basées sur l\'IA.' },
                { icon: 'fa-moon', title: 'Mode jour / nuit', text: 'Utilisez le bouton 🌙 en haut à droite pour changer de thème selon vos préférences.' },
                { icon: 'fa-question-circle', title: 'Ce guide toujours accessible', text: 'Cliquez à tout moment sur le bouton <strong>?</strong> dans la barre de navigation pour relancer ce guide.' },
            ]
        },
        {
            icon: 'fa-folder-plus',
            title: 'Créer votre premier projet',
            desc: 'Un projet représente une parcelle agricole avec ses cultures, sa superficie et ses objectifs de rendement.',
            tips: [
                { icon: 'fa-plus', title: 'Bouton « Nouveau »', text: 'Cliquez sur <strong>Nouveau</strong> dans la navbar ou sur la page Projets pour créer votre premier projet.' },
                { icon: 'fa-map-marker-alt', title: 'Sélectionner une localité', text: 'Choisissez votre région pour que nos algorithmes utilisent les données météo et sol adaptées.' },
                { icon: 'fa-leaf', title: 'Choisir vos cultures', text: 'Sélectionnez une ou plusieurs cultures. Le système calcule automatiquement le rendement estimé.' },
            ]
        },
        {
            icon: 'fa-chart-pie',
            title: 'Le Dashboard analytique',
            desc: 'Votre centre de commande : statistiques, graphiques et suivi en temps réel de tous vos projets.',
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
            tips: [
                { icon: 'fa-calendar-alt', title: 'Dates de semis et récolte', text: 'Saisissez les dates de semis et récolte prévues pour chaque culture de vos projets.' },
                { icon: 'fa-camera', title: 'Photos de vos plants', text: 'Ajoutez des photos au fil des semaines pour documenter l\'évolution de vos cultures.' },
                { icon: 'fa-check-circle', title: 'Clôturer un projet', text: 'Quand la récolte est terminée, saisissez le rendement final pour entraîner le modèle IA.' },
            ]
        },
        {
            icon: 'fa-robot',
            title: 'L\'Assistant IA 🤖',
            desc: 'Posez vos questions agricoles en langage naturel — météo, maladies, conseils, prédictions.',
            tips: [
                { icon: 'fa-comment-dots', title: 'Disponible partout', text: 'Cliquez sur le bouton vert en bas à droite pour ouvrir l\'assistant à tout moment.' },
                { icon: 'fa-history', title: 'Historique conservé', text: 'Vos conversations sont sauvegardées localement et restaurées à chaque visite.' },
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

        tourTips.innerHTML = s.tips.map(t => `
            <div class="tour-tip">
                <div class="tour-tip-icon"><i class="fas ${t.icon}"></i></div>
                <div class="tour-tip-text">
                    <strong>${t.title}</strong>
                    <span>${t.text}</span>
                </div>
            </div>
        `).join('');

        tourProgress.innerHTML = tourSteps.map((_, i) => `
            <button type="button" class="tour-dot ${i === step ? 'active' : i < step ? 'done' : ''}" data-step="${i}" aria-label="Aller à l'étape ${i + 1}"></button>
        `).join('');

        if (step === total - 1) {
            tourNext.innerHTML = `C'est parti ! <i class="fas fa-check ms-1"></i>`;
            tourSkip.style.display = 'none';
        } else {
            tourNext.innerHTML = `Suivant <i class="fas fa-arrow-right"></i>`;
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
        document.body.style.overflow = 'hidden';
    }

    function closeTour() {
        tourOverlay.classList.remove('active');
        document.body.style.overflow = '';
        localStorage.setItem(TOUR_KEY, '1');
    }

    tourSkip.addEventListener('click', closeTour);
    tourNext.addEventListener('click', () => {
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

    tourOverlay.addEventListener('click', (event) => {
        if (event.target === tourOverlay) {
            closeTour();
        }
    });

    openGuideBtn.addEventListener('click', openTour);

    document.addEventListener('DOMContentLoaded', () => {
        if (!localStorage.getItem(TOUR_KEY)) {
            setTimeout(openTour, 800);
        }
    });
})();
