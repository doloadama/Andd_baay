/**
 * roi_calculator — Composant Alpine.js pour le simulateur ROI du Hub Finance.
 *
 * Usage :
 *   <div x-data="roiCalculator({ totalRecettes: N, totalCouts: N })">
 *     ...
 *   </div>
 *
 * État réactif :
 *   montantSaisi  — nombre saisi dans le champ (FCFA, default 0)
 *   typeOperation — 'recette' | 'depense' (default 'depense')
 *   totalRecettes — cumul actuel des recettes (immutable, init via initialData)
 *   totalCouts    — cumul actuel des coûts (immutable, init via initialData)
 *
 * Getters dérivés (utilisés par le template) :
 *   beneficeNet, beneficeLabel, recettesLabel, coutsLabel
 *   roiPct, roiLabel, roiColorClass
 *   roiActuelPct  — ROI baseline avant simulation (référence)
 *   roiDeltaPct   — variation projetée vs baseline (pt de %)
 *   roiDeltaLabel — chaîne formatée "+12.3 pt vs actuel" ou "" si N/A
 *   roiDeltaClass — classe CSS pour la couleur du delta
 *
 * Actions :
 *   reset() — remet montantSaisi à 0
 */
document.addEventListener('alpine:init', function () {
    Alpine.data('roiCalculator', function (initialData) {
        const d =
            initialData != null && typeof initialData === 'object' ? initialData : {};
        return {
            montantSaisi: 0,
            typeOperation: d.typeOperation || 'depense',
            totalRecettes: Number(d.totalRecettes) || 0,
            totalCouts: Number(d.totalCouts) || 0,

            // ── Bénéfice net ──
            get beneficeNet() {
                return this._previewRecettes() - this._previewCouts();
            },
            get beneficeLabel() {
                return this._fmt(this.beneficeNet) + ' FCFA';
            },

            // ── Totaux projetés (utilisés par le template) ──
            get recettesLabel() {
                return this._fmt(this._previewRecettes()) + ' FCFA';
            },
            get coutsLabel() {
                return this._fmt(this._previewCouts()) + ' FCFA';
            },

            // ── ROI projeté (avec saisie) ──
            get roiPct() {
                const cout = this._previewCouts();
                if (!cout) return null;
                return ((this._previewRecettes() - cout) / cout) * 100;
            },
            get roiLabel() {
                if (this.roiPct === null) return '—';
                const sign = this.roiPct >= 0 ? '+' : '';
                return `${sign}${this.roiPct.toFixed(1)} %`;
            },
            get roiColorClass() {
                if (this.roiPct === null) return 'roi-neutral';
                return this.roiPct >= 0 ? 'roi-positive' : 'roi-negative';
            },

            // ── ROI actuel (baseline, sans saisie) ──
            get roiActuelPct() {
                if (!this.totalCouts) return null;
                return ((this.totalRecettes - this.totalCouts) / this.totalCouts) * 100;
            },

            // ── Δ projeté vs actuel — masqué si pas de saisie ou ROI indéfini ──
            get roiDeltaPct() {
                if (Number(this.montantSaisi) === 0) return null;
                if (this.roiPct === null || this.roiActuelPct === null) return null;
                return this.roiPct - this.roiActuelPct;
            },
            get roiDeltaLabel() {
                const d = this.roiDeltaPct;
                if (d === null) return '';
                const sign = d >= 0 ? '+' : '';
                return `${sign}${d.toFixed(1)} pt vs actuel`;
            },
            get roiDeltaClass() {
                const d = this.roiDeltaPct;
                if (d === null) return '';
                return d >= 0
                    ? 'roi-widget__kpi-delta--positive'
                    : 'roi-widget__kpi-delta--negative';
            },

            // ── Actions ──
            reset() {
                this.montantSaisi = 0;
            },

            // ── Helpers internes ──
            _previewRecettes() {
                const m = Number(this.montantSaisi) || 0;
                return this.typeOperation === 'recette'
                    ? this.totalRecettes + m
                    : this.totalRecettes;
            },
            _previewCouts() {
                const m = Number(this.montantSaisi) || 0;
                return this.typeOperation === 'depense'
                    ? this.totalCouts + m
                    : this.totalCouts;
            },
            _fmt(n) {
                return Math.round(n).toLocaleString('fr-FR');
            },
        };
    });
});
