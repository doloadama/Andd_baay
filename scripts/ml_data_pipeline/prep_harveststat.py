import os
import sys
import pandas as pd
import numpy as np
import requests
from io import StringIO
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Features anti-fuite requises par le modele XGBoost (baay/services/ml_service.py)
TARGET_FEATURES = [
    "pluie_moyenne", "besoin_eau", "superficie", "mois_semis",
    "sol_type", "type_irrigation", "type_engrais", "saison", "categorie_culture",
    "sol_inadapte", "deficit_hydrique"
]

CROP_MAPPINGS = {
    'Mil': {'besoin_eau': 450, 'saison': 'Hivernage', 'categorie_culture': 'Céréale'},
    'Arachide': {'besoin_eau': 500, 'saison': 'Hivernage', 'categorie_culture': 'Légumineuse'},
    'Mais': {'besoin_eau': 600, 'saison': 'Hivernage', 'categorie_culture': 'Céréale'},
    'Riz': {'besoin_eau': 1000, 'saison': 'Hivernage', 'categorie_culture': 'Céréale'},
}

def generate_realistic_bootstrap(n_samples=500, crop_name='Mil'):
    """
    Generate a realistic bootstrap dataset based on West African agronomic parameters.
    This replaces the "flawed" synthetic data with data that correctly models the 
    interaction between rainfall, soil, and management practices.
    """
    logger.info(f"Generating realistic bootstrap data for {crop_name}...")
    np.random.seed(42)
    crop_info = CROP_MAPPINGS.get(crop_name, CROP_MAPPINGS['Mil'])
    
    # 1. Base climatic variables for Senegal/Mali region
    pluie_moyenne = np.random.normal(loc=550, scale=150, size=n_samples).clip(200, 1200)
    superficie = np.random.lognormal(mean=0.5, sigma=0.8, size=n_samples).clip(0.5, 50)
    mois_semis = np.random.choice([5, 6, 7], size=n_samples, p=[0.2, 0.6, 0.2])
    
    # 2. Categorical variables
    sol_types = ['Dior', 'Deck', 'Deck-Dior', 'Sablonneux', 'Latéritique']
    sol_type = np.random.choice(sol_types, size=n_samples)
    
    irrigations = ['Aucune', 'Goutte-à-goutte', 'Aspersion', 'Gravitaire']
    # Mostly rainfed in this region
    type_irrigation = np.random.choice(irrigations, size=n_samples, p=[0.8, 0.05, 0.05, 0.1])
    
    engrais = ['Aucun', 'Organique', 'Minéral NPK', 'Minéral Urée', 'Mixte']
    type_engrais = np.random.choice(engrais, size=n_samples, p=[0.3, 0.3, 0.2, 0.1, 0.1])
    
    # 3. Derived boolean variables
    besoin = crop_info['besoin_eau']
    deficit_hydrique = (pluie_moyenne < besoin) & (type_irrigation == 'Aucune')
    
    # Simple agronomic rule: if peanut on lateritic, bad. If rice on dior (sandy), bad.
    sol_inadapte = np.zeros(n_samples, dtype=bool)
    if crop_name == 'Arachide':
        sol_inadapte = sol_type == 'Latéritique'
    elif crop_name == 'Riz':
        sol_inadapte = sol_type == 'Dior'
    
    # 4. Generate Target (Rendement Réel in kg/ha) based on agronomic logic, NOT financials
    base_yield = 1000 if crop_name == 'Mil' else (1200 if crop_name == 'Arachide' else 2500)
    
    # Modifiers
    water_modifier = np.where(deficit_hydrique, 0.6, 1.0)
    soil_modifier = np.where(sol_inadapte, 0.7, 1.0)
    fert_modifier = np.ones(n_samples)
    fert_modifier[type_engrais == 'Minéral NPK'] = 1.3
    fert_modifier[type_engrais == 'Mixte'] = 1.4
    irrig_modifier = np.where(type_irrigation != 'Aucune', 1.2, 1.0)
    
    # Random noise (weather variability, pests, etc.)
    noise = np.random.normal(loc=1.0, scale=0.15, size=n_samples)
    
    rendement_reel = base_yield * water_modifier * soil_modifier * fert_modifier * irrig_modifier * noise
    rendement_reel = rendement_reel.clip(100, 8000) # Ensure physical limits
    
    df = pd.DataFrame({
        'pluie_moyenne': pluie_moyenne,
        'besoin_eau': besoin,
        'superficie': superficie,
        'mois_semis': mois_semis,
        'sol_type': sol_type,
        'type_irrigation': type_irrigation,
        'type_engrais': type_engrais,
        'saison': crop_info['saison'],
        'categorie_culture': crop_info['categorie_culture'],
        'sol_inadapte': sol_inadapte.astype(int),
        'deficit_hydrique': deficit_hydrique.astype(int),
        '_rendement_reel': rendement_reel
    })
    
    return df

def fetch_and_prep_data():
    """
    Main function to prepare data. 
    In a full production scenario, this connects to FAOSTAT/HarvestStat APIs.
    For this robust bootstrapping phase, we generate empirically sound data.
    """
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'ml_bootstrap')
    os.makedirs(output_dir, exist_ok=True)
    
    for crop in ['Mil', 'Arachide', 'Mais', 'Riz']:
        df = generate_realistic_bootstrap(n_samples=1000, crop_name=crop)
        output_file = os.path.join(output_dir, f"{crop.lower()}_bootstrap.csv")
        df.to_csv(output_file, index=False)
        logger.info(f"Saved {crop} bootstrap dataset with {len(df)} rows to {output_file}")

if __name__ == "__main__":
    fetch_and_prep_data()
