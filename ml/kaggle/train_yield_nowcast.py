"""
Andd Baay — Entraînement Kaggle : modèle de NOWCAST de rendement (NDVI + climat).
==================================================================================
À exécuter dans un notebook Kaggle (CPU suffit — XGBoost tabulaire).

Cible : prédire le rendement (crop-cut) à partir de signaux EN COURS DE SAISON
(indices satellite Sentinel-2 / NDVI-EVI, climat TerraClimate / SPI, etc.).
Dataset recommandé : « CGIAR Crop Yield Prediction Challenge » (Zindi).

Principes (audit ML) :
  - Split PAR ZONE GÉOGRAPHIQUE (GroupKFold) — JAMAIS la même zone en train+test,
    sinon R² gonflé et échec sur le terrain.
  - Métriques honnêtes : R², RMSE, MAE + comparaison à une BASELINE (moyenne).
    Un modèle qui ne bat pas « prédire la moyenne » ne vaut rien.
  - Export d'un .pkl au format attendu par baay/services/ml_service.py.

──────────────────────────────────────────────────────────────────────────────
USAGE : 1) régler le bloc CONFIG ci-dessous (3 colonnes) ; 2) Run All.
──────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import glob
import pickle
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold, KFold, cross_val_predict
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from xgboost import XGBRegressor

# ════════════════════════════════════════════════════════════════════════════
# CONFIG — à renseigner selon l'entête réel du dataset
# ════════════════════════════════════════════════════════════════════════════
DATA_GLOB    = "/kaggle/input/**/*.csv"   # chemin des CSV (récursif)
TARGET_COL   = "yield"                    # ← colonne du rendement réel (crop-cut)
GROUP_COL    = "field_id"                 # ← colonne géographique pour le split (zone/commune/parcelle)
ID_COLS      = ["ID", "id", "sample_id"]  # colonnes identifiants à exclure des features
CATEGORICAL  = []                         # colonnes catégorielles éventuelles (ex: ["crop", "region"])
MIN_R2       = 0.30                        # garde-fou : sous ce seuil, modèle non explicatif
OUTPUT_PKL   = "/kaggle/working/yield_nowcast.pkl"
RANDOM_STATE = 42

# ════════════════════════════════════════════════════════════════════════════


def charger_donnees() -> pd.DataFrame:
    fichiers = sorted(glob.glob(DATA_GLOB, recursive=True))
    if not fichiers:
        raise FileNotFoundError(f"Aucun CSV trouvé via {DATA_GLOB}")
    print("Fichiers détectés :")
    for f in fichiers:
        print("  -", f)
    # On charge le plus volumineux (souvent le train), sinon concat si même schéma.
    df = pd.read_csv(fichiers[0])
    print(f"\nChargé : {fichiers[0]}  → {df.shape[0]} lignes, {df.shape[1]} colonnes")
    print("Colonnes :", list(df.columns))
    return df


def preparer(df: pd.DataFrame):
    if TARGET_COL not in df.columns:
        raise KeyError(f"TARGET_COL '{TARGET_COL}' absente. Colonnes: {list(df.columns)}")
    if GROUP_COL not in df.columns:
        print(f"⚠️  GROUP_COL '{GROUP_COL}' absente → split NON géographique (risque de fuite).")
    df = df[df[TARGET_COL].notna()].copy()

    exclude = set(ID_COLS) | {TARGET_COL, GROUP_COL}
    feature_cols = [c for c in df.columns if c not in exclude]

    encoders = {}
    for col in feature_cols:
        if col in CATEGORICAL or df[col].dtype == object:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].fillna("Inconnu").astype(str))
            encoders[col] = le
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    X = df[feature_cols].values.astype(float)
    y = df[TARGET_COL].astype(float).values
    groups = df[GROUP_COL].values if GROUP_COL in df.columns else None
    return X, y, groups, feature_cols, encoders


def evaluer(model, X, y, groups):
    """CV par zone géographique. Retourne (r2, rmse, mae, r2_baseline)."""
    n_groupes = len(set(groups)) if groups is not None else 0
    if groups is not None and n_groupes >= 3:
        cv = GroupKFold(n_splits=min(5, n_groupes))
        splitter = cv.split(X, y, groups)
        print(f"Validation : GroupKFold par zone ({n_groupes} zones distinctes).")
    else:
        cv = KFold(n_splits=min(5, len(y)), shuffle=True, random_state=RANDOM_STATE)
        splitter = cv.split(X)
        print("⚠️  Validation : KFold simple (pas de colonne géo) — fuite spatiale possible.")

    y_pred = cross_val_predict(model, X, y, cv=list(splitter))
    r2 = r2_score(y, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y, y_pred)))
    mae = mean_absolute_error(y, y_pred)
    # Baseline : prédire la moyenne globale
    r2_base = r2_score(y, np.full_like(y, y.mean()))
    return r2, rmse, mae, r2_base


def main():
    df = charger_donnees()
    X, y, groups, feature_cols, encoders = preparer(df)
    print(f"\nFeatures ({len(feature_cols)}) : {feature_cols}")
    print(f"Cible : {TARGET_COL}  (moyenne={y.mean():.1f}, écart-type={y.std():.1f})")

    model = XGBRegressor(
        n_estimators=400, max_depth=5, learning_rate=0.04,
        subsample=0.8, colsample_bytree=0.8,
        random_state=RANDOM_STATE, verbosity=0,
    )

    r2, rmse, mae, r2_base = evaluer(model, X, y, groups)
    print("\n──────────── MÉTRIQUES HONNÊTES (CV) ────────────")
    print(f"  R²        : {r2:.3f}   (baseline 'moyenne' = {r2_base:.3f})")
    print(f"  RMSE      : {rmse:.1f}")
    print(f"  MAE       : {mae:.1f}")
    bat_baseline = r2 > max(r2_base, 0.0)
    print(f"  Bat la baseline ? {'OUI' if bat_baseline else 'NON ❌'}")
    print(f"  Explicatif (R² ≥ {MIN_R2}) ? {'OUI' if r2 >= MIN_R2 else 'NON ❌'}")

    if not (bat_baseline and r2 >= MIN_R2):
        print("\n⚠️  Modèle NON déployable en l'état (n'explique pas mieux que la moyenne).")
        print("    → plus de données, meilleures features, ou revoir la cible.")

    # Entraînement final sur tout le dataset
    model.fit(X, y)

    # Importance des features (diagnostic)
    try:
        imp = sorted(zip(feature_cols, model.feature_importances_), key=lambda t: -t[1])
        print("\nTop features :")
        for name, val in imp[:10]:
            print(f"  {val:6.3f}  {name}")
    except Exception:
        pass

    # ── Export .pkl (format compatible baay/services/ml_service.py) ───────────
    modele_dict = {
        "model": model,
        "features": feature_cols,
        "encoders": encoders,
        "meta": {
            "culture": "nowcast_multi",
            "type": "nowcast",          # ≠ pré-campagne
            "n_train": int(len(y)),
            "rmse_cv": round(rmse, 2),
            "r2_cv": round(float(r2), 4),
            "r2_baseline": round(float(r2_base), 4),
            "date_entrainement": datetime.now(timezone.utc).isoformat(),
            "source": "Zindi CGIAR Crop Yield (Sentinel-2 + TerraClimate)",
        },
    }
    with open(OUTPUT_PKL, "wb") as f:
        pickle.dump(modele_dict, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"\n✅ Modèle exporté : {OUTPUT_PKL}")
    print("   → télécharge-le et place-le dans MEDIA_ROOT/ml_models/ (cf. README).")


if __name__ == "__main__":
    main()
