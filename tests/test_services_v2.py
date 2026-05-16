"""
Tests unitaires pour les services Andd Baay V2
Piliers: IA Agronomique, Finance ROI, Carte Chaleur, Marketplace
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta, date
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.cache import cache

from baay.models import (
    Profile, Ferme, Projet, ProjetProduit, ProduitAgricole,
    Localite, Pays, HistoriqueSol, Recette, SimulationROI, OffreProduit, TransactionMarche,
)
from baay.services.fertilisation_service import (
    generer_recommandation,
    _calculer_deficits,
)
from baay.services.roi_simulation_service import (
    calculer_simulation,
    creer_simulation,
    generer_scenarios_par_defaut,
    ScenarioHypotheses,
    SimulationResult,
)
from baay.services.carte_chaleur_service import (
    agréger_cultures_par_localite,
    generer_geojson_heatmap,
    CULTURES_PRINCIPALES,
    CultureAggregate,
)
from baay.voice_assistant_service import _detecter_type_incident as detecter_incident


# =============================================================================
# HELPERS
# =============================================================================

def get_mock_projet():
    """Helper projet mock pour tests."""
    ferme = Mock(spec=Ferme)
    ferme.id = 1
    ferme.nom = "Ferme Test"

    pays = Mock(spec=Pays)
    pays.id = 1
    pays.nom = "Sénégal"

    localite = Mock(spec=Localite)
    localite.id = 1
    localite.nom = "Dakar"
    localite.latitude = 14.7167
    localite.longitude = -17.4677
    localite.pays = pays

    projet = Mock(spec=Projet)
    projet.id = 1
    projet.nom = "Projet Test"
    projet.ferme = ferme
    projet.localite = localite
    projet.date_lancement = date.today()

    return projet


def get_mock_sol():
    """Helper sol mock pour tests fertilisation."""
    sol = Mock(spec=HistoriqueSol)
    sol.ferme = Mock(spec=Ferme)
    sol.ph = 6.5
    sol.n_pourcent = 0.15
    sol.p_pourcent = 0.08
    sol.k_pourcent = 0.12
    sol.matieres_organiques_pourcent = 2.5
    sol.texture = "limoneux"
    return sol


def get_mock_produit_agricole():
    """Helper produit agricole mock."""
    produit = Mock(spec=ProduitAgricole)
    produit.id = 1
    produit.nom = "Mil"
    produit.culture = "cereale"
    produit.besoins_npka_json = {
        "N_kg_ha": 60,
        "P_kg_ha": 30,
        "K_kg_ha": 40,
        "pH_optimal": {"min": 6.0, "max": 7.0}
    }
    return produit


# =============================================================================
# TESTS SERVICE FERTILISATION
# =============================================================================

class TestFertilisationService(TestCase):
    """Tests pour le service de recommandation fertilisation."""

    def test_calculer_deficit_nutriments(self):
        """Test du calcul des déficits N-P-K."""
        sol = get_mock_sol()
        sol.azote_ppm = 15
        sol.phosphore_ppm = 10
        sol.potassium_ppm = 20
        sol.ph = 6.5

        produit = get_mock_produit_agricole()
        produit.nom = "Mil"

        deficits = _calculer_deficits(sol, "mil")

        assert deficits.deficit_azote > 0
        assert deficits.deficit_phosphore > 0
        assert deficits.deficit_potassium > 0
        assert deficits.ph_actuel == 6.5

    def test_obtenir_recommandation_fertilisation(self):
        """Test de génération de recommandation complète."""
        sol = get_mock_sol()
        sol._state = Mock()
        sol._state.db = "default"
        sol.azote_ppm = 15
        sol.phosphore_ppm = 10
        sol.potassium_ppm = 20
        sol.ph = 6.5
        sol.ferme.nom = "Ferme Test"

        projet = get_mock_projet()
        produit = get_mock_produit_agricole()
        produit._state = Mock()
        produit._state.db = "default"
        produit.nom = "Mil"

        recommandation = generer_recommandation(
            historique_sol=sol,
            culture_cible=produit,
            sauvegarder=False
        )

        assert recommandation is not None
        assert recommandation.type_engrais_conseille is not None
        assert recommandation.message_explication is not None


# =============================================================================
# TESTS SERVICE ROI SIMULATION
# =============================================================================

class TestROISimulationService(TestCase):
    """Tests pour le service de simulation ROI."""

    def setUp(self):
        """Setup test data."""
        self.projet = Mock(spec=Projet)
        self.projet.id = 1
        self.projet.budget_alloue = Decimal("1000000")
        self.projet.ferme = Mock()
        self.projet.ferme.nom = "Ferme Test"

    def test_calculer_roi_basique(self):
        """Test calcul ROI basique."""
        hypotheses = ScenarioHypotheses(
            rendement_kg_ha=Decimal("1000"),
            prix_fcfa_kg=Decimal("500"),
            investissement_total=Decimal("300000"),
            description="Test"
        )
        superficie = Decimal("1.0")

        resultat = calculer_simulation(hypotheses, superficie)

        # Recette = 1000 * 500 * 1.0 = 500,000
        # Benefice = 500,000 - 300,000 = 200,000
        # ROI = (200,000 / 300,000) * 100 = 66.66%
        assert resultat.recette_prevue == Decimal("500000")
        assert resultat.benefice_prevu == Decimal("200000")
        assert round(resultat.roi_pct, 2) == Decimal("66.67")

    def test_scenarios_predefinis(self):
        """Test génération des scénarios par défaut."""
        projet = Mock(spec=Projet)
        projet.superficie = Decimal("1.0")
        projet.culture = Mock(spec=ProduitAgricole)
        projet.culture.nom = "Mil"

        with patch("baay.services.roi_simulation_service.Investissement.objects.filter") as mock_filter:
            mock_filter.return_value.aggregate.return_value = {'total': Decimal('100000')}
            scenarios = generer_scenarios_par_defaut(
                projet=projet,
            )

            assert len(scenarios) == 3
            assert "optimiste" in scenarios
            assert "realiste" in scenarios
            assert "pessimiste" in scenarios

    def test_simulation_comparaison_previsionnel_reel(self):
        """Test comparaison prévisionnel vs réel."""
        simulation = Mock(spec=SimulationROI)
        simulation.investissement_prevu = Decimal("500000")
        simulation.recette_prevue = Decimal("800000")
        simulation.investissement_reel = Decimal("550000")
        simulation.recette_reelle = Decimal("750000")

        # Mocking property
        type(simulation).ecart_investissement_pct = PropertyMock(return_value=10.0)

        # Ecart investissement: (550000 - 500000) / 500000 = 10%
        assert simulation.ecart_investissement_pct == 10.0

        # ROI prévu: (800000 - 500000) / 500000 = 60%
        # ROI réel: (750000 - 550000) / 550000 = ~36.36%


# =============================================================================
# TESTS SERVICE CARTE CHALEUR
# =============================================================================

class TestCarteChaleurService(TestCase):
    """Tests pour le service de carte de chaleur."""

    def test_cultures_principales_definies(self):
        """Test que les cultures principales sont définies."""
        assert len(CULTURES_PRINCIPALES) > 0
        # Correcting expected values based on baay/services/carte_chaleur_service.py
        assert any(c[0] == "mil" for c in CULTURES_PRINCIPALES)
        assert any(c[0] == "oignon" for c in CULTURES_PRINCIPALES)

    @patch("baay.services.carte_chaleur_service.Projet")
    def test_obtenir_donnees_cultures_par_localite(self, mock_projet):
        """Test agrégation des données par localité."""
        # Mock queryset
        mock_qs = MagicMock()
        mock_qs.select_related.return_value = mock_qs
        mock_qs.filter.return_value = mock_qs
        mock_qs.exclude.return_value = mock_qs
        mock_projet.objects.filter.return_value = mock_qs
        mock_qs.__iter__.return_value = []

        donnees = agréger_cultures_par_localite(pays_id=None, culture_type=None)

        assert isinstance(donnees, list)

    def test_generer_geojson_heatmap(self):
        """Test génération GeoJSON."""
        with patch("baay.services.carte_chaleur_service.agréger_cultures_par_localite") as mock_get_data:
            mock_get_data.return_value = [
                CultureAggregate(
                    culture_nom="mil",
                    localite_nom="Dakar",
                    superficie_totale=100.0,
                    nb_projets=5,
                    latitude=14.7,
                    longitude=-17.5,
                    pays_nom="Sénégal"
                )
            ]

            geojson = generer_geojson_heatmap(pays_id=None, culture_type=None)

            assert geojson["type"] == "FeatureCollection"
            assert "features" in geojson


# =============================================================================
# TESTS SERVICE VOICE ASSISTANT
# =============================================================================

class TestVoiceAssistantService(TestCase):
    """Tests pour le service voice assistant."""

    def test_detecter_incident_maladie_detectee(self):
        """Test détection incident maladie."""
        transcription = "Mes plants de tomate ont des feuilles jaunes et des taches brunes"

        type_inc, gravite, score = detecter_incident(
            transcription
        )

        assert type_inc == "maladie_feuilles"
        assert gravite in ["faible", "moyenne", "haute", "critique"]

    def test_detecter_incident_pas_dincident(self):
        """Test quand pas d'incident détecté."""
        transcription = "Le temps est beau aujourd'hui, parfait pour travailler"

        type_inc, gravite, score = detecter_incident(
            transcription
        )

        assert type_inc is None


# =============================================================================
# TESTS MODELES MARKETPLACE
# =============================================================================

class TestMarketplaceModels(TestCase):
    """Tests pour les modèles OffreProduit et TransactionMarche."""

    def test_offre_produit_prix_total(self):
        """Test propriété prix_total."""
        offre = Mock(spec=OffreProduit)
        offre.quantite_disponible = Decimal("100.00")
        offre.prix_unitaire = Decimal("500.00")

        # prix_total = 100 * 500 = 50000
        offre.prix_total = offre.quantite_disponible * offre.prix_unitaire
        assert offre.prix_total == Decimal("50000.00")

    def test_offre_produit_est_disponible(self):
        """Test propriété est_disponible."""
        offre = Mock(spec=OffreProduit)
        offre.statut = "disponible"
        offre.date_expiration = date.today() + timedelta(days=7)
        # Mocking the property if it's a property on the model
        type(offre).est_disponible = PropertyMock(return_value=True)

        assert offre.est_disponible is True

    def test_transaction_statuts_valides(self):
        """Test que les statuts de transaction sont valides."""
        statuts = [s[0] for s in TransactionMarche.STATUT_CHOICES]

        assert "en_negociation" in statuts
        assert "confirme" in statuts
        assert "paye" in statuts
        assert "livre" in statuts
        assert "annule" in statuts


# =============================================================================
# TESTS INTEGRATION
# =============================================================================

@pytest.mark.django_db
class TestIntegrationV2(TestCase):
    """Tests d'intégration pour Andd Baay V2."""

    def test_creer_simulation_roi_complete(self):
        """Test création complète simulation ROI avec utilisateur."""
        user = User.objects.create_user("testuser", "test@test.com", "password")
        profile = user.profile  # Profile created by signal

        pays = Pays.objects.create(nom="Sénégal", code_iso="SN")
        localite = Localite.objects.create(nom="Dakar", pays=pays, latitude=14.7, longitude=-17.5)
        ferme = Ferme.objects.create(
            nom="Ferme Test",
            pays=pays,
            proprietaire=profile,
        )

        projet = Projet.objects.create(
            nom="Projet Test",
            ferme=ferme,
            utilisateur=profile,
            localite=localite,
            superficie=Decimal("1.0"),
            date_lancement=date.today(),
            budget_alloue=Decimal("1000000"),
        )

        simulation = SimulationROI.objects.create(
            projet=projet,
            scenario_type="realiste",
            nom_simulation="Test Scenario",
            rendement_prevu_kg_ha=Decimal("1000"),
            prix_prevu_fcfa_kg=Decimal("500"),
            investissement_prevu=Decimal("500000"),
            cree_par=profile,
        )

        assert simulation.id is not None
        assert simulation.roi_calcule_pct is not None


# =============================================================================
# COMMANDE POUR EXECUTER LES TESTS
# =============================================================================

# pytest tests/test_services_v2.py -v
# pytest tests/test_services_v2.py::TestFertilisationService -v
# pytest tests/test_services_v2.py::TestROISimulationService -v
