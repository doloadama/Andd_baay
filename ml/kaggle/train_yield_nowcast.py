"""
Andd Baay — Entraînement Kaggle : NOWCAST de rendement depuis cubes satellite.
==============================================================================
Dataset : « CGIAR Crop Yield Prediction Challenge » (Zindi).

Format réel des données :
  - Train.csv               : Field_ID, Year, Quality, Yield
  - Image_arrays_train/      : un .npy par Field_ID, shape (360, 41, 41)
                               = 360 canaux (temps × bandes) × patch 41×41 px
  - Bandnames.txt           : noms des 360 canaux
  - test_field_ids_with_year.csv : Field_ID + Year du test

Stratégie (CPU, pas de GPU requis) :
  Cube (360,41,41) → FEATURES tabulaires (stats spatiales par canal + NDVI
  temporel si bandes Rouge/PIR identifiées) → XGBoost.

Garde-fous (audit ML) :
  - Split par ANNÉE (GroupKFold sur Year) = anti-fuite temporelle (on n'a pas de
    colonne géographique ici ; Field_ID est unique par échantillon).
  - Métriques honnêtes : R², RMSE, MAE + BASELINE « prédire la moyenne ».
  - Filtre qualité du label de localisation (Quality).

USAGE : régler le bloc CONFIG, puis Run All dans un notebook Kaggle.
"""
from __future__ import annotations

import os
import pickle
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold, KFold, cross_val_predict
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from xgboost import XGBRegressor

# ════════════════════════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════════════════════════
BASE         = "/kaggle/input"                         # racine du dataset attaché
TRAIN_CSV    = f"{BASE}/Train.csv"                      # ← ajuste le sous-dossier si besoin
IMG_DIR      = f"{BASE}/Image_arrays_train"            # dossier des .npy (décompressé)
BANDNAMES    = f"{BASE}/Bandnames.txt"
TARGET_COL   = "Yield"
ID_COL       = "Field_ID"
YEAR_COL     = "Year"
QUALITY_COL  = "Quality"
MIN_QUALITY  = None        # ex: 1 → ne garder que les labels de bonne qualité (None = tout)

# Indices (0-based) des canaux Rouge et PIR DANS UN PAS DE TEMPS, + nb de bandes/pas.
# À renseigner depuis Bandnames.txt (cf. README). Si None → pas de NDVI, on garde
# uniquement les stats par canal (le modèle marche quand même).
N_BANDS_PER_STEP = None    # ex: 12 (Sentinel-2) → 360/12 = 30 pas de temps
RED_IDX_IN_STEP  = None    # ex: 3
NIR_IDX_IN_STEP  = None    # ex: 7

MIN_R2       = 0.30
OUTPUT_PKL   = "/kaggle/working/yield_nowcast.pkl"
RANDOM_STATE = 42
ARR_SHAPE    = (360, 41, 41)


def _load_array(field_id) -> np.ndarray | None:
    """Charge le cube .npy d'une parcelle (tolère quelques variantes de nom)."""
    for name in (f"{field_id}.npy", f"{field_id}",):
        p = os.path.join(IMG_DIR, name)
        if os.path.exists(p):
            try:
                a = np.load(p, allow_pickle=True)
                return a.reshape(ARR_SHAPE) if a.size == np.prod(ARR_SHAPE) else a
            except Exception:
                return None
    return None


def _features_from_cube(cube: np.ndarray) -> np.ndarray:
    """
    (360,41,41) → vecteur de features.
      - par canal : moyenne + écart-type spatial (sur le patch 41×41)
      - + NDVI temporel (moyenne/max/somme) si bandes Rouge/PIR fournies
    NaN (nuages/masques) ignorés via nanmean/nanstd.
    """
    c = cube.astype(np.float32)
    flat = c.reshape(c.shape[0], -1)                 # (360, 1681)
    with np.errstate(all="ignore"):
        mean = np.nanmean(flat, axis=1)              # (360,)
        std = np.nanstd(flat, axis=1)                # (360,)
    feats = [mean, std]

    if N_BANDS_PER_STEP and RED_IDX_IN_STEP is not None and NIR_IDX_IN_STEP is not None:
        nb = N_BANDS_PER_STEP
        steps = c.shape[0] // nb
        ndvi_series = []
        for t in range(steps):
            red = mean[t * nb + RED_IDX_IN_STEP]
            nir = mean[t * nb + NIR_IDX_IN_STEP]
            denom = (nir + red)
            ndvi_series.append((nir - red) / denom if denom not in (0, np.nan) and denom != 0 else 0.0)
        ndvi = np.nan_to_num(np.array(ndvi_series, dtype=np.float32))
        # Stats temporelles du NDVI = signal agronomique fort (vigueur, AUC)
        feats.append(np.array([
            np.nanmean(ndvi), np.nanmax(ndvi), np.nanmin(ndvi),
            np.nanstd(ndvi), float(np.nansum(ndvi)),  # AUC ≈ biomasse cumulée
            float(np.argmax(ndvi)),                   # date du pic de verdure
        ], dtype=np.float32))

    return np.nan_to_num(np.concatenate(feats))


def construire_dataset():
    df = pd.read_csv(TRAIN_CSV)
    print(f"Train.csv : {df.shape[0]} lignes — colonnes {list(df.columns)}")
    if MIN_QUALITY is not None and QUALITY_COL in df.columns:
        avant = len(df)
        df = df[df[QUALITY_COL] >= MIN_QUALITY]
        print(f"Filtre qualité ≥ {MIN_QUALITY} : {avant} → {len(df)} lignes")

    X, y, years, ok = [], [], [], 0
    for _, row in df.iterrows():
        cube = _load_array(row[ID_COL])
        if cube is None:
            continue
        try:
            X.append(_features_from_cube(cube))
            y.append(float(row[TARGET_COL]))
            years.append(row.get(YEAR_COL, 0))
            ok += 1
        except Exception:
            continue
    print(f"Cubes chargés et vectorisés : {ok}/{len(df)}")
    if ok == 0:
        raise RuntimeError("Aucun cube chargé — vérifie IMG_DIR / noms de fichiers.")
    return np.vstack(X), np.array(y, dtype=float), np.array(years)


def evaluer(model, X, y, years):
    n_annees = len(set(years.tolist()))
    if n_annees >= 2:
        cv = GroupKFold(n_splits=min(5, n_annees))
        splits = list(cv.split(X, y, years))
        print(f"Validation : GroupKFold par ANNÉE ({n_annees} années) — anti-fuite temporelle.")
    else:
        cv = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
        splits = list(cv.split(X))
        print("⚠️  Une seule année → KFold aléatoire (pas d'axe anti-fuite disponible).")
    y_pred = cross_val_predict(model, X, y, cv=splits)
    r2 = r2_score(y, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y, y_pred)))
    mae = mean_absolute_error(y, y_pred)
    r2_base = r2_score(y, np.full_like(y, y.mean()))
    return r2, rmse, mae, r2_base


def main():
    X, y, years = construire_dataset()
    print(f"\nMatrice features : {X.shape}  | cible moy={y.mean():.1f} σ={y.std():.1f}")

    model = XGBRegressor(
        n_estimators=500, max_depth=5, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.7,
        random_state=RANDOM_STATE, verbosity=0, n_jobs=-1,
    )
    r2, rmse, mae, r2_base = evaluer(model, X, y, years)
    print("\n──────────── MÉTRIQUES HONNÊTES (CV) ────────────")
    print(f"  R²    : {r2:.3f}   (baseline 'moyenne' = {r2_base:.3f})")
    print(f"  RMSE  : {rmse:.1f}")
    print(f"  MAE   : {mae:.1f}")
    deployable = (r2 > max(r2_base, 0.0)) and (r2 >= MIN_R2)
    print(f"  Déployable ? {'OUI ✅' if deployable else 'NON ❌ (n explique pas mieux que la moyenne)'}")

    model.fit(X, y)
    modele_dict = {
        "model": model,
        "n_features": int(X.shape[1]),
        "config": {
            "N_BANDS_PER_STEP": N_BANDS_PER_STEP,
            "RED_IDX_IN_STEP": RED_IDX_IN_STEP,
            "NIR_IDX_IN_STEP": NIR_IDX_IN_STEP,
            "arr_shape": ARR_SHAPE,
        },
        "meta": {
            "type": "nowcast_satellite",
            "n_train": int(len(y)),
            "rmse_cv": round(rmse, 2),
            "r2_cv": round(float(r2), 4),
            "r2_baseline": round(float(r2_base), 4),
            "date_entrainement": datetime.now(timezone.utc).isoformat(),
            "source": "Zindi CGIAR Crop Yield (Sentinel-2 cubes 360×41×41)",
        },
    }
    with open(OUTPUT_PKL, "wb") as f:
        pickle.dump(modele_dict, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"\n✅ Modèle exporté : {OUTPUT_PKL}")


if __name__ == "__main__":
    main()
