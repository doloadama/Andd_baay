# baay/tests/test_ml.py — Garde-fous du modèle ML (anti-fuite + qualité minimale).
from django.test import TestCase

from baay.services import ml_service
from baay.services.ml_service import PRECAMPAGNE_FEATURES, predire_avec_ml


class _FakeModel:
    """Modèle minimal : predict renvoie une valeur fixe."""
    def __init__(self, value=1000.0):
        self._v = value

    def predict(self, X):
        return [self._v] * len(X)


def _modele(n_train, r2):
    return {
        "model": _FakeModel(1234.0),
        "encoders": {},
        "features": PRECAMPAGNE_FEATURES,
        "meta": {"n_train": n_train, "r2_cv": r2, "culture": "Mil"},
    }


_FEATURES_OK = {f: (0.0 if f not in ("sol_type", "type_irrigation", "type_engrais",
                                     "saison", "categorie_culture") else "x")
                for f in PRECAMPAGNE_FEATURES}


class PrecampagneFeaturesTest(TestCase):
    """Le jeu d'entraînement ne doit contenir AUCUNE variable de fuite."""

    LEAKY = {
        "penalite", "bonus", "variance", "confiance", "correcteur_biais",
        "source_rendement", "n_historique_local", "n_historique_regional",
        "etat_vegetatif", "progression_cycle", "ndvi", "pluie_reelle_mm",
        "localite_id",
    }

    def test_aucune_variable_de_fuite(self):
        fuites = self.LEAKY & set(PRECAMPAGNE_FEATURES)
        self.assertEqual(fuites, set(), f"Variables de fuite présentes : {fuites}")

    def test_contient_les_variables_pre_campagne(self):
        for f in ("pluie_moyenne", "besoin_eau", "sol_type", "type_irrigation",
                  "mois_semis", "saison", "type_engrais", "superficie"):
            self.assertIn(f, PRECAMPAGNE_FEATURES)


class PredireGuardTest(TestCase):
    """predire_avec_ml refuse un modèle sous-entraîné ou non explicatif."""

    def test_rejette_n_train_insuffisant(self):
        self.assertIsNone(predire_avec_ml(_FEATURES_OK, _modele(n_train=10, r2=0.8)))

    def test_rejette_r2_trop_faible(self):
        self.assertIsNone(predire_avec_ml(_FEATURES_OK, _modele(n_train=100, r2=0.1)))

    def test_accepte_modele_fiable(self):
        res = predire_avec_ml(_FEATURES_OK, _modele(n_train=80, r2=0.6))
        self.assertIsNotNone(res)
        self.assertEqual(res["rendement_kg_ha"], 1234.0)
        self.assertGreater(res["confiance_bonus"], 0)

    def test_seuils_exposes(self):
        self.assertEqual(ml_service.MIN_TRAIN_OBS, 30)
        self.assertGreaterEqual(ml_service.MIN_R2, 0.30)
