"""
Commande de diagnostic : évalue la précision du modèle de prédictions de récolte.

Usage
-----
    python manage.py evaluer_previsions
    python manage.py evaluer_previsions --ferme <uuid>

Exemple de sortie
-----------------
    === Précision du modèle de prédictions ===
    Échantillon : 12 projets clôturés
    MAPE globale  : 18.3 %   bon         (idéal < 20 %)
    Couverture    : 75.0 %   bon         (idéal > 70 %)
    Biais global  :  +5.2 %              (+ = sur-estimation)

    Par culture :
      Culture          N    MAPE       Couv.      Biais
      ───────────────────────────────────────────────────
      Arachide         6    14.1 %     83.3 %     +3.2 %  [OK]
      Riz              3    24.7 %     66.7 %    +18.6 %  [!]
      Mil              3    11.2 %    100.0 %     +1.4 %  [OK]

    Avertissements :
      - Echantillon inferieur a 5 -- resultats indicatifs seulement.
"""

from django.core.management.base import BaseCommand

from baay.services.prediction_accuracy import (
    evaluer_precision_modele,
    qualifier_mape,
    qualifier_coverage,
)


class Command(BaseCommand):
    help = "Évalue la précision du modèle de prédictions de récolte."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ferme",
            type=str,
            default=None,
            metavar="UUID",
            help="Restreindre l'analyse à une ferme spécifique (UUID).",
        )

    def handle(self, *args, **options):
        ferme_id = options.get("ferme")
        ferme_ids = [ferme_id] if ferme_id else None

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n=== Précision du modèle de prédictions de récolte ==="
        ))

        stats = evaluer_precision_modele(ferme_ids=ferme_ids)
        n = stats["n"]

        if n == 0:
            self.stdout.write(self.style.WARNING(
                "\n  Aucune donnée disponible.\n"
                "  Clôturez des projets en renseignant `rendement_final` pour chaque culture."
            ))
            self._print_warnings(stats["avertissements"])
            return

        # ── Métriques globales ───────────────────────────────────────────────
        self.stdout.write(f"\n  Échantillon   : {n} culture(s) clôturée(s)")

        mape = stats["mape"]
        mape_label = qualifier_mape(mape)
        mape_str = f"{mape:6.1f} %   {mape_label:<12}  (idéal < 20 %)" if mape is not None else "  N/D"
        self.stdout.write(f"  MAPE globale  : {mape_str}")

        cov = stats["coverage_pct"]
        cov_label = qualifier_coverage(cov)
        cov_str = f"{cov:6.1f} %   {cov_label:<12}  (idéal > 70 %)" if cov is not None else "  N/D"
        self.stdout.write(f"  Couverture    : {cov_str}")

        biais = stats["biais"]
        if biais is not None:
            signe = "+" if biais >= 0 else ""
            note = "sur-estimation" if biais > 2 else ("sous-estimation" if biais < -2 else "équilibré")
            self.stdout.write(f"  Biais global  : {signe}{biais:5.1f} %              ({note})")

        # ── Breakdown par culture ────────────────────────────────────────────
        par_culture = stats.get("par_culture", {})
        if par_culture:
            self.stdout.write(
                "\n  Par culture :\n"
                f"    {'Culture':<20} {'N':>4}  {'MAPE':>8}  {'Couv.':>8}  {'Biais':>8}  Note"
            )
            self.stdout.write("    " + "─" * 60)

            for nom, d in sorted(par_culture.items(), key=lambda x: -(x[1]["mape"] or 999)):
                mape_c = d["mape"]
                cov_c = d["coverage_pct"]
                biais_c = d["biais"]
                ok = (mape_c or 999) < 20 and (cov_c or 0) >= 70
                note = "[OK]" if ok else "[!] "
                m = f"{mape_c:6.1f} %" if mape_c is not None else "   N/D "
                c = f"{cov_c:6.1f} %" if cov_c is not None else "   N/D "
                b_str = ""
                if biais_c is not None:
                    signe = "+" if biais_c >= 0 else ""
                    b_str = f"{signe}{biais_c:5.1f} %"
                self.stdout.write(
                    f"    {nom:<20} {d['n']:>4}  {m}  {c}  {b_str:>8}  {note}"
                )

        # ── Avertissements ───────────────────────────────────────────────────
        self._print_warnings(stats["avertissements"])
        self.stdout.write("")

    def _print_warnings(self, warnings):
        if not warnings:
            return
        self.stdout.write(self.style.WARNING("\n  Avertissements :"))
        for w in warnings:
            self.stdout.write(f"    - {w}")
