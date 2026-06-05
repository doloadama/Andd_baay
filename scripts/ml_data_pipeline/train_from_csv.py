import os
import sys
import pandas as pd
import numpy as np
import pickle
import logging
from datetime import datetime, timezone
import django

# Setup Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Andd_Baayi.settings')
django.setup()

from sklearn.model_selection import KFold, cross_val_score
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBRegressor

from baay.models import MLModeleInfo
from baay.services.ml_service import PRECAMPAGNE_FEATURES, MIN_R2, _CATEGORICAL_FEATURES, _slug, _MODELS_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def train_from_csv(culture_nom, csv_path):
    logger.info(f"Training robust model for {culture_nom} from {csv_path}")
    
    culture_slug = _slug(culture_nom)
    df = pd.read_csv(csv_path)
    
    n = len(df)
    if n < 30:
        logger.warning(f"Not enough data in {csv_path} (n={n})")
        return None
        
    feature_cols = [f for f in PRECAMPAGNE_FEATURES if f in df.columns]
    X_df = df[feature_cols].copy()
    y = df["_rendement_reel"].astype(float).values
    
    encoders = {}
    for col in _CATEGORICAL_FEATURES:
        if col in X_df.columns:
            le = LabelEncoder()
            X_df[col] = X_df[col].fillna("Inconnu").astype(str)
            X_df[col] = le.fit_transform(X_df[col])
            encoders[col] = le
            
    for col in ("sol_inadapte", "deficit_hydrique"):
        if col in X_df.columns:
            X_df[col] = X_df[col].fillna(0).astype(int)
            
    X_df = X_df.fillna(0)
    X = X_df.values.astype(float)
    
    model = XGBRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=0,
    )
    
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    scores_r2 = cross_val_score(model, X, y, cv=cv, scoring="r2")
    scores_rmse = cross_val_score(model, X, y, cv=cv, scoring="neg_root_mean_squared_error")
    
    r2_cv = float(scores_r2.mean())
    rmse_cv = float(-scores_rmse.mean())
    
    logger.info(f"CV R2: {r2_cv:.4f}, CV RMSE: {rmse_cv:.2f}")
    
    model.fit(X, y)
    
    if r2_cv >= MIN_R2:
        output_dir_path = _MODELS_DIR
        output_dir_path.mkdir(parents=True, exist_ok=True)
        pkl_path = output_dir_path / f"{culture_slug}.pkl"
        
        modele_dict = {
            "model": model,
            "features": feature_cols,
            "encoders": encoders,
            "meta": {
                "culture": culture_nom,
                "n_train": n,
                "rmse_cv": round(rmse_cv, 2),
                "r2_cv": round(r2_cv, 4),
                "date_entrainement": datetime.now(timezone.utc).isoformat(),
                "declencheur": "bootstrap_csv",
                "warm_start": False,
            },
        }
        
        with pkl_path.open("wb") as f:
            pickle.dump(modele_dict, f, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info(f"Model saved to {pkl_path}")
        
        # Deactivate old models
        MLModeleInfo.objects.filter(culture_slug=culture_slug, actif=True).update(actif=False)
        
        # Register new model
        MLModeleInfo.objects.create(
            culture_slug=culture_slug,
            culture_nom=culture_nom,
            n_observations=n,
            r2_score=round(r2_cv, 4),
            rmse=round(rmse_cv, 2),
            actif=True,
            declencheur="bootstrap_csv",
            warm_start=False,
            fichier_pkl=str(pkl_path),
        )
        logger.info(f"Model registered in DB for {culture_nom}")
        return True
    else:
        logger.warning(f"Model R2 ({r2_cv:.4f}) is below MIN_R2 ({MIN_R2}). Model discarded.")
        return False

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'ml_bootstrap')
    crops = [('Mil', 'mil_bootstrap.csv'), ('Arachide', 'arachide_bootstrap.csv'), 
             ('Mais', 'mais_bootstrap.csv'), ('Riz', 'riz_bootstrap.csv')]
             
    for crop_nom, csv_file in crops:
        csv_path = os.path.join(data_dir, csv_file)
        if os.path.exists(csv_path):
            train_from_csv(crop_nom, csv_path)
        else:
            logger.error(f"CSV not found: {csv_path}")

if __name__ == "__main__":
    main()
