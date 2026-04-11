import random
import logging
from .models import HistoriqueRendement, ParametresCulture

logger = logging.getLogger(__name__)

def calculer_indice_confiance(projet_produit):
    """
    Calcule un indice de confiance (%) pour un produit dans un projet.
    Basé sur la comparaison entre les semences allouées et les historiques locaux.
    """
    if not projet_produit.superficie_allouee or not projet_produit.quantite_semences:
        return 0.0

    densite_actuelle = float(projet_produit.quantite_semences) / float(projet_produit.superficie_allouee)
    
    # 1. Vérification paramétrage de base
    score_densite = 50.0
    try:
        if hasattr(projet_produit.produit, 'parametres'):
            # Logique future : comparer densite avec densite_recommandee si ajoutée dans ParametresCulture
            pass
    except ParametresCulture.DoesNotExist:
        pass

    # 2. Historique local
    # On regarde si on a des données historiques dans la localité du projet
    historiques = HistoriqueRendement.objects.filter(
        localite=projet_produit.projet.localite,
        produit=projet_produit.produit
    )

    if historiques.exists():
        # L'historique pèse lourd dans l'indice de confiance
        rendement_moyen = sum(h.rendement_reel_kg_ha for h in historiques) / historiques.count()
        if rendement_moyen > 0:
            score_histo = 30.0
        else:
            score_histo = 10.0
    else:
        # Sans données historiques, l'IA est moins confiante
        score_histo = 15.0

    # 3. Météo et Sol (placeholder)
    score_env = 20.0
    if projet_produit.projet.localite.type_sol == 'Dior' and 'arachide' in projet_produit.produit.nom.lower():
        score_env += 5.0  # Perfect match

    indice_final = min(100.0, score_densite + score_histo + score_env)
    return round(indice_final, 2)


def predict_rendement_ml(features: dict) -> float:
    """
    Stub pour l'utilisation d'un modèle de Machine Learning pré-entraîné.
    Exemple de features : 
    {
        'type_sol_encoded': 1, 
        'superficie': 2.5, 
        'pluviometrie_moyenne': 450, 
        'semences_kg': 50
    }
    
    Dans le futur, on décommenterait ceci :
    # import joblib
    # model = joblib.load('modele_rendement.pkl')
    # prediction = model.predict([list(features.values())])
    # return prediction[0]
    """
    # Pour l'instant, retourne une prédiction factice mais basée sur les données
    superficie = features.get('superficie', 1)
    base = 1200  # 1.2t / ha
    
    # Ajout d'une variance aléatoire pour simuler le ML (± 15%)
    variance = random.uniform(0.85, 1.15)
    rendement_prevu = base * superficie * variance
    
    return round(rendement_prevu, 2)
