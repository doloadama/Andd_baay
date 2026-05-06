/**
 * roi_calculator — Composant Alpine.js
 *
 * Usage :
 *   <div x-data="roiCalculator({ totalRecettes: N, totalCouts: N })">
 *     ...
 *   </div>
 *
 * Propriétés réactives exposées :
 *   montantSaisi  — valeur en cours de saisie dans le champ (nombre)
 *   typeOperation — 'recette' | 'depense'
 *   totalRecettes — cumul actuel des recettes (FCFA)
 *   totalCouts    — cumul actuel des coûts (FCFA)
 *   beneficeNet   — totalRecettes - totalCouts (calculé)
 *   roiPct        — ROI en % (calculé, null si totalCouts = 0)
 *   roiLabel      — chaîne formatée prête à l'affichage
 */
document.addEventListener('alpine:init', function () {
    Alpine.data('roiCalculator', function (initialData) {
        return {
            montantSaisi: 0,
            typeOperation: initialData.typeOperation || 'depense',
            totalRecettes: Number(initialData.totalRecettes) || 0,
            totalCouts: Number(initialData.totalCouts) || 0,

            get beneficeNet() {
                return this._previewRecettes() - this._previewCouts();
            },

            get roiPct() {
                const cout = this._previewCouts();
                if (!cout) return null;
                return ((this._previewRecettes() - cout) / cout * 100);
            },

            get roiLabel() {
                if (this.roiPct === null) return '—';
                const sign = this.roiPct >= 0 ? '+' : '';
                return `${sign}${this.roiPct.toFixed(1)} %`;
            },

            get beneficeLabel() {
                return this._fmt(this.beneficeNet) + ' FCFA';
            },

            get roiColorClass() {
                if (this.roiPct === null) return 'roi-neutral';
                return this.roiPct >= 0 ? 'roi-positive' : 'roi-negative';
            },

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
