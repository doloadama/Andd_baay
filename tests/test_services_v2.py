"""
Tests unitaires pour les services Andd Baay V2
Piliers: IA Agronomique, Finance ROI, Carte Chaleur, Marketplace
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta, date
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.cache import cache

from baay.models import (
    Profile, Ferme, Projet, ProjetProduit, ProduitAgricole,
    Localite, Pays, Sol, Recette, SimulationROI, OffreProduit, TransactionMarche,
)
from baay.services.fertilisation_service import (
    obtenir_recommandation_fertilisation,
    calculer_deficit_nutriments,
)
from baay.services.roi_simulation_service import (
    calculer_roi,
    creer_simulation,
    scenarios_predefinis,
)
from baay.services.carte_chaleur_service import (
    obtenir_donnees_cultures_par_localite,
    generer_geojson_heatmap,
    CULTURES_PRINCIPALES,
)
from baay.services.voice_assistant_service import detecter_incident


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_projet():
    """Fixture projet mock pour tests."""
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


@pytest.fixture
def mock_sol():
    """Fixture sol mock pour tests fertilisation."""
    sol = Mock(spec=Sol)
    sol.ph = 6.5
    sol.n_pourcent = 0.15
    sol.p_pourcent = 0.08
    sol.k_pourcent = 0.12
    sol.matieres_organiques_pourcent = 2.5
    sol.texture = "limoneux"
    return sol


@pytest.fixture
def mock_produit_agricole():
    """Fixture produit agricole mock."""
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
        sol = mock_sol()
        produit = mock_produit_agricole()

        deficits = calculer_deficit_nutriments(sol, produit)

        assert "N" in deficits
        assert "P" in deficits
        assert "K" in deficits
        assert "pH" in deficits

        # N: besoin 60, sol 0.15*100=15kg/ha équivalent → déficit positif
        assert deficits["N"] > 0

    def test_obtenir_recommandation_fertilisation(self):
        """Test de génération de recommandation complète."""
        sol = mock_sol()
        projet = mock_projet()
        projet_produit = Mock(spec=ProjetProduit)
        projet_produit.projet = projet
        projet_produit.produit = mock_produit_agricole()
        projet_produit.superficie_hectares = Decimal("2.5")

        recommandation = obtenir_recommandation_fertilisation(
            projet_produit=projet_produit,
            sol=sol,
        )

        assert recommandation is not None
        assert "fertilisation" in recommandation
        assert "engrais_suggere" in recommandation["fertilisation"]
        assert "quantite_kg_ha" in recommandation["fertilisation"]
        assert "ajustement_ph" in recommandation


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
        resultat = calculer_roi(
            investissement_initial=Decimal("500000"),
            cout_recurrent_annuel=Decimal("200000"),
            recette_prevue=Decimal("1000000"),
            duree_projet_annees=3,
        )

        assert "roi_pct" in resultat
        assert "profit_total" in resultat
        assert "periode_retour_mois" in resultat

        # ROI = (recette - investissement) / investissement
        # 1000000 - 500000 = 500000 → 100% ROI
        assert resultat["roi_pct"] == 100.0

    def test_scenarios_predefinis(self):
        """Test génération des 3 scénarios prédéfinis."""
        scenarios = scenarios_predefinis(
            projet=self.projet,
            base_investissement=Decimal("500000"),
            base_cout_annuel=Decimal("150000"),
            base_recette=Decimal("800000"),
            duree_annees=2,
        )

        assert len(scenarios) == 3
        assert "optimiste" in scenarios
        assert "realiste" in scenarios
        assert "pessimiste" in scenarios

        # Optimiste doit avoir ROI > Realiste > Pessimiste
        assert scenarios["optimiste"]["roi_pct"] > scenarios["realiste"]["roi_pct"]
        assert scenarios["realiste"]["roi_pct"] > scenarios["pessimiste"]["roi_pct"]

    def test_simulation_comparaison_previsionnel_reel(self):
        """Test comparaison prévisionnel vs réel."""
        simulation = Mock(spec=SimulationROI)
        simulation.investissement_prevu = Decimal("500000")
        simulation.recette_prevue = Decimal("800000")
        simulation.investissement_reel = Decimal("550000")
        simulation.recette_reelle = Decimal("750000")

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
        assert any(c[0] == "cereale" for c in CULTURES_PRINCIPALES)
        assert any(c[0] == "legumineuse" for c in CULTURES_PRINCIPALES)

    @patch("baay.services.carte_chaleur_service.ProjetProduit")
    def test_obtenir_donnees_cultures_par_localite(self, mock_projet_produit):
        """Test agrégation des données par localité."""
        # Mock queryset
        mock_qs = MagicMock()
        mock_qs.select_related.return_value = mock_qs
        mock_qs.filter.return_value = mock_qs
        mock_qs.exclude.return_value = mock_qs
        mock_projet_produit.objects.return_value = mock_qs

        donnees = obtenir_donnees_cultures_par_localite(pays_id=None, culture_type=None)

        assert isinstance(donnees, dict)

    def test_generer_geojson_heatmap(self):
        """Test génération GeoJSON."""
        with patch("baay.services.carte_chaleur_service.obtenir_donnees_cultures_par_localite") as mock_get_data:
            mock_get_data.return_value = {
                1: {
                    "localite": Mock(nom="Dakar", latitude=14.7, longitude=-17.5),
                    "cultures": {
                        "cereale": {"superficie": 100.0, "nb_projets": 5}
                    }
                }
            }

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

        incident = detecter_incident(
            transcription=transcription,
            projet_id=1,
            ferme_id=1,
        )

        assert incident is not None
        assert "type_incident" in incident
        assert incident["gravite_estimee"] in ["faible", "moyenne", "elevee", "critique"]

    def test_detecter_incident_pas_dincident(self):
        """Test quand pas d'incident détecté."""
        transcription = "Le temps est beau aujourd'hui, parfait pour travailler"

        incident = detecter_incident(
            transcription=transcription,
            projet_id=1,
            ferme_id=1,
        )

        assert incident is None


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
        assert offre.prix_total == Decimal("50000.00")

    def test_offre_produit_est_disponible(self):
        """Test propriété est_disponible."""
        offre = Mock(spec=OffreProduit)
        offre.statut = "disponible"
        offre.date_expiration = date.today() + timedelta(days=7)

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
        profile = Profile.objects.create(user=user, nom="Test User")

        ferme = Ferme.objects.create(
            nom="Ferme Test",
            pays=Pays.objects.create(nom="Sénégal", code="SN"),
            cree_par=profile,
        )

        projet = Projet.objects.create(
            nom="Projet Test",
            ferme=ferme,
            date_lancement=date.today(),
            budget_alloue=Decimal("1000000"),
        )

        simulation = SimulationROI.objects.create(
            projet=projet,
            nom_scenario="Test Scenario",
            investissement_prevu=Decimal("500000"),
            cout_recurrent_prevu=Decimal("200000"),
            recette_prevue=Decimal("1000000"),
            duree_mois=24,
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
