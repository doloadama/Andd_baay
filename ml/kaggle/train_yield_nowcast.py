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

# Structure Bandnames.txt (Zindi CGIAR) : 360 = 12 pas de temps × 30 bandes.
# Par pas : 16 Sentinel-2 (B1,B2,B3,B4,B5,B6,B7,B8,B8A,B9,B10,B11,B12,QA10,QA20,QA60)
#           + 14 TerraClimate (aet,def,pdsi,pet,pr,ro,soil,srad,swe,tmmn,tmmx,vap,vpd,vs).
# NDVI = (B8 - B4)/(B8 + B4)  → B4=position 3, B8=position 7 dans le pas.
N_BANDS_PER_STEP = 30
RED_IDX_IN_STEP  = 3        # B4 (repli si Bandnames illisible)
NIR_IDX_IN_STEP  = 7        # B8 (repli)

MIN_R2       = 0.30
OUTPUT_PKL   = "/kaggle/working/yield_nowcast.pkl"
RANDOM_STATE = 42
ARR_SHAPE    = (360, 41, 41)

# Fenetre centrale (anti pixel-mixte) : sous-carre au centre du patch 41x41.
# 4 -> 9x9 (~0.8 ha) : parcelles paysannes sahéliennes < 2 ha.
CENTER_HALF  = 4
# Valeurs aberrantes / nodata a masquer (reflectance plausible apres correction).
NODATA_VALUES = (-9999.0, 0.0)

# Mode compact : ~30 features agronomiques (NDVI + climat) au lieu de 739.
# Combat le fleau de la dimensionnalite (739 features / 2977 obs => sur-apprentissage
# sous GroupKFold par annee). Passez a False pour comparer avec le set complet.
COMPACT_FEATURES = True

# Indices resolus depuis Bandnames.txt (remplis par decode_bands()).
RED_IDX: list[int] = []
NIR_IDX: list[int] = []
# Bandes climat TerraClimate appariees par NOM : {nom: [indices par pas de temps]}.
CLIM_IDX: dict[str, list[int]] = {}
# Variables climat ciblees (precip, temp max/min, humidite sol).
CLIM_TARGETS = ("pr", "tmmx", "tmmn", "soil")


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


def decode_bands():
    """
    Lit Bandnames.txt et resout RED_IDX / NIR_IDX par NOM (robuste a l'ordre
    bande-major OU temps-major). On apparie les indices red(B4) et NIR(B8) pas
    a pas : pour chaque pas de temps t, on a un index red et un index NIR.
    Repli positionnel (30/pas) si les noms sont illisibles.
    """
    global RED_IDX, NIR_IDX, CLIM_IDX
    import re
    try:
        names = [l.strip() for l in open(BANDNAMES) if l.strip()]
    except Exception:
        names = []

    red_pos, nir_pos = [], []
    clim: dict[str, list[int]] = {k: [] for k in CLIM_TARGETS}
    if len(names) == ARR_SHAPE[0]:
        for i, n in enumerate(names):
            u = n.upper()
            toks = [t for t in re.split(r"[^A-Za-z0-9]+", n.lower()) if t]
            # NIR = B8 (pas B8A) ; RED = B4.
            if "B08" in u or (("B8" in u) and ("B8A" not in u)):
                nir_pos.append(i)
            elif "B04" in u or "B4" in u:
                red_pos.append(i)
            # Climat TerraClimate : appariement par token exact.
            for tgt in CLIM_TARGETS:
                aliases = {"pr": ("pr", "ppt", "prcp", "precip")}.get(tgt, (tgt,))
                if any(a in toks for a in aliases):
                    clim[tgt].append(i)

    if red_pos and nir_pos and len(red_pos) == len(nir_pos):
        RED_IDX, NIR_IDX = red_pos, nir_pos
        print(f"Bandes NDVI resolues par NOM : {len(RED_IDX)} pas "
              f"(red ex={RED_IDX[:3]} nir ex={NIR_IDX[:3]})")
    else:
        nb, steps = N_BANDS_PER_STEP, ARR_SHAPE[0] // N_BANDS_PER_STEP
        RED_IDX = [t * nb + RED_IDX_IN_STEP for t in range(steps)]
        NIR_IDX = [t * nb + NIR_IDX_IN_STEP for t in range(steps)]
        print(f"Bandes NDVI : repli POSITIONNEL ({steps} pas, 30/pas) "
              f"— noms non exploitables ({len(names)} lignes).")

    CLIM_IDX = {k: v for k, v in clim.items() if v}
    if CLIM_IDX:
        print("Bandes climat resolues par NOM : "
              + ", ".join(f"{k}({len(v)})" for k, v in CLIM_IDX.items()))
    else:
        print("Bandes climat : aucune resolue (noms non exploitables) "
              "-> features climat ignorees.")


def _center(flat_cube: np.ndarray) -> np.ndarray:
    """Retourne le sous-cube central 15x15 aplati en (360, k) pour anti pixel-mixte."""
    h = ARR_SHAPE[1] // 2
    s = slice(h - CENTER_HALF, h + CENTER_HALF + 1)
    return flat_cube[:, s, s].reshape(flat_cube.shape[0], -1)


def _features_from_cube(cube: np.ndarray) -> np.ndarray:
    """
    (360,41,41) -> vecteur de features (anti-nuages / anti pixel-mixte).
      - nodata (-9999, 0) -> NaN avant toute statistique
      - stats spatiales sur la FENETRE CENTRALE 15x15 (pas tout le patch)
      - NDVI temporel borne [-1,1], apparie par nom de bande
    """
    c = cube.astype(np.float32)
    # 1) Masquage nodata / valeurs aberrantes -> NaN (ignore par nanmean).
    for v in NODATA_VALUES:
        c[c == v] = np.nan
    # 2) Fenetre centrale (la culture, pas le decor).
    win = _center(c)                                  # (360, 81) en 9x9
    with np.errstate(all="ignore"):
        mean = np.nanmean(win, axis=1)                # (360,)
        std = np.nanstd(win, axis=1)
    mean = np.nan_to_num(mean)
    std = np.nan_to_num(std)

    # 3) NDVI mensuel apparie par nom, borne [-1,1].
    ndvi = np.zeros(0, dtype=np.float32)
    if RED_IDX and NIR_IDX:
        red, nir = mean[RED_IDX], mean[NIR_IDX]
        denom = nir + red
        ndvi = np.where(denom != 0, (nir - red) / denom, 0.0)
        ndvi = np.clip(np.nan_to_num(ndvi), -1.0, 1.0).astype(np.float32)

    if COMPACT_FEATURES:
        # ~30 features agronomiques : NDVI (serie + stats) + agregats climat.
        feats = []
        if ndvi.size:
            feats.append(ndvi)                          # courbe de verdure
            feats.append(np.array([
                ndvi.mean(), ndvi.max(), ndvi.min(), ndvi.std(),
                float(ndvi.sum()), float(ndvi.argmax()),
                float(ndvi.max() - ndvi.min()),
            ], dtype=np.float32))
        for name in CLIM_TARGETS:
            idx = CLIM_IDX.get(name)
            if not idx:
                continue
            serie = mean[idx]
            feats.append(np.array([
                float(np.nansum(serie)), float(np.nanmean(serie)),
                float(np.nanmax(serie)), float(np.nanargmax(serie)),
            ], dtype=np.float32))
        if not feats:                                   # garde-fou : jamais vide
            feats = [mean]
        return np.nan_to_num(np.concatenate(feats))

    # Mode complet (739) : moyennes + ecarts-types de tous les canaux + NDVI.
    feats = [mean, std]
    if ndvi.size:
        feats.append(ndvi)
        feats.append(np.array([
            ndvi.mean(), ndvi.max(), ndvi.min(), ndvi.std(),
            float(ndvi.sum()), float(ndvi.argmax()),
            float(ndvi.max() - ndvi.min()),
        ], dtype=np.float32))
    return np.nan_to_num(np.concatenate(feats))


def _autodetect_paths():
    """Trouve automatiquement Train.csv / dossier .npy / Bandnames.txt sous /kaggle/input."""
    import glob
    global TRAIN_CSV, IMG_DIR, BANDNAMES
    if not os.path.exists(TRAIN_CSV):
        hits = glob.glob("/kaggle/input/**/Train.csv", recursive=True)
        if hits:
            TRAIN_CSV = hits[0]
    if not os.path.isdir(IMG_DIR) or not glob.glob(os.path.join(IMG_DIR, "*.npy")):
        npys = glob.glob("/kaggle/input/**/*.npy", recursive=True)
        if npys:
            IMG_DIR = os.path.dirname(npys[0])
    if not os.path.exists(BANDNAMES):
        hits = glob.glob("/kaggle/input/**/Bandnames.txt", recursive=True)
        if hits:
            BANDNAMES = hits[0]
    print(f"Chemins → TRAIN_CSV={TRAIN_CSV}\n          IMG_DIR={IMG_DIR}")


def construire_dataset():
    _autodetect_paths()
    decode_bands()
    df = pd.read_csv(TRAIN_CSV)
    print(f"Train.csv : {df.shape[0]} lignes — colonnes {list(df.columns)}")
    if QUALITY_COL in df.columns:
        vc = df[QUALITY_COL].value_counts().sort_index()
        print(f"Distribution {QUALITY_COL} : {dict(vc)}  "
              f"(MIN_QUALITY={MIN_QUALITY} — regler selon la doc du dataset)")
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


def _cv_scores(model, X, y, splits):
    y_pred = cross_val_predict(model, X, y, cv=splits)
    return (r2_score(y, y_pred),
            float(np.sqrt(mean_squared_error(y, y_pred))),
            mean_absolute_error(y, y_pred))


def evaluer(model, X, y, years):
    """
    Double validation :
      - GroupKFold par ANNEE  = generalisation a une campagne INEDITE (= usage reel nowcast).
      - KFold aleatoire        = le signal existe-t-il (intra-annee) ?
    Si random >> groupe : features OK mais extrapolation inter-annee difficile.
    Si les deux ~0       : pas de signal exploitable (decodage / donnees).
    """
    r2_base = r2_score(y, np.full_like(y, y.mean()))

    kf = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    r2_rand, rmse_rand, mae_rand = _cv_scores(model, X, y, list(kf.split(X)))
    print(f"\n[KFold aleatoire]   R2={r2_rand:.3f}  RMSE={rmse_rand:.2f}  MAE={mae_rand:.2f}")

    n_annees = len(set(years.tolist()))
    if n_annees >= 2:
        gkf = GroupKFold(n_splits=min(5, n_annees))
        r2, rmse, mae = _cv_scores(model, X, y, list(gkf.split(X, y, years)))
        print(f"[GroupKFold/annee]  R2={r2:.3f}  RMSE={rmse:.2f}  MAE={mae:.2f}  "
              f"({n_annees} annees) <- metrique de reference")
    else:
        print("Une seule annee -> pas de GroupKFold ; on retient le KFold aleatoire.")
        r2, rmse, mae = r2_rand, rmse_rand, mae_rand

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
