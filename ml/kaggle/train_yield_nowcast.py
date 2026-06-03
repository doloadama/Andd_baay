"""
Andd Baay — Entraînement Kaggle : NOWCAST de rendement depuis cubes satellite.
==============================================================================
Dataset : « CGIAR Crop Yield Prediction Challenge » (Zindi).

Format réel des données :
  - Train.csv                : Field_ID, Year, Quality, Yield
  - Image_arrays_train/      : un .npy par Field_ID, shape (360, 41, 41)
                               = 360 canaux (temps × bandes) × patch 41×41 px
  - Bandnames.txt            : noms des 360 canaux
  - test_field_ids_with_year.csv : Field_ID + Year du test

Stratégie (CPU, pas de GPU requis) :
  Cube (360,41,41) → FEATURES tabulaires (stats spatiales par canal + NDVI
  temporel interpolé si bandes Rouge/PIR identifiées) → XGBoost.

Garde-fous (audit ML) :
  - Split par ANNÉE (GroupKFold sur Year) = anti-fuite temporelle.
  - Interpolation temporelle = correction des "trous noirs" causés par les nuages.
    IMPORTANT : on n'interpole QUE les vrais nodata (NaN). Un 0.0 climatique
    (ex : aucune pluie en saison sèche) est une valeur RÉELLE, jamais comblée.
  - Métriques honnêtes : R², RMSE, MAE + BASELINE « prédire la moyenne »
    évaluée sur les MÊMES splits CV (donc comparable, souvent négative en
    GroupKFold/année).
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
TRAIN_CSV    = f"{BASE}/Train.csv"                     # ← ajuste le sous-dossier si besoin
IMG_DIR      = f"{BASE}/Image_arrays_train"             # dossier des .npy (décompressé)
BANDNAMES    = f"{BASE}/Bandnames.txt"
TARGET_COL   = "Yield"
ID_COL       = "Field_ID"
YEAR_COL     = "Year"
QUALITY_COL  = "Quality"
MIN_QUALITY  = None        # ex: 1 → ne garder que les labels de bonne qualité (None = tout)

# Structure Bandnames.txt (Zindi CGIAR) — CONFIRMEE : 360 = 12 pas x 30 bandes,
# ordre TEMPS-MAJOR. Offsets dans chaque pas de 30 bandes :
N_BANDS_PER_STEP = 30
ARR_SHAPE        = (360, 41, 41)
N_STEPS          = ARR_SHAPE[0] // N_BANDS_PER_STEP   # 12

BAND_OFFSET = {
    # Sentinel-2 (reflectance, 0..15)
    "B1": 0, "B2": 1, "B3": 2, "B4": 3, "B5": 4, "B6": 5, "B7": 6, "B8": 7,
    "B8A": 8, "B9": 9, "B10": 10, "B11": 11, "B12": 12,
    "QA10": 13, "QA20": 14, "QA60": 15,
    # TerraClimate (16..29)
    "aet": 16, "def": 17, "pdsi": 18, "pet": 19, "pr": 20, "ro": 21, "soil": 22,
    "srad": 23, "swe": 24, "tmmn": 25, "tmmx": 26, "vap": 27, "vpd": 28, "vs": 29,
}
# 0 = nodata UNIQUEMENT pour les bandes optiques S2 (réflectance). QA60 (offset 15)
# est volontairement EXCLU : sa valeur 0 signifie « ciel clair », pas « nodata ».
S2_REFLECTANCE_OFFSETS = tuple(range(13))   # B1..B12 (0 = nodata réel)
S2_OFFSETS = tuple(range(16))               # optique + QA (masquage nuages)
QA60_OFFSET = 15                            # masque nuages Sentinel-2

# Variables climat retenues : pilotes inter-annuels du rendement sahelien.
CLIM_TARGETS = ("pr", "pet", "def", "pdsi", "soil", "aet", "tmmx", "tmmn")

MIN_R2       = 0.15  # Seuil abaissé à 0.15 pour le dataset CGIAR (très bruité)
OUTPUT_PKL   = "/kaggle/working/yield_nowcast.pkl"
RANDOM_STATE = 42

# Fenetre centrale (anti pixel-mixte) : 4 -> 9x9 (~0.8 ha), parcelles < 2 ha.
CENTER_HALF  = 4
# Mode compact : features agronomiques (indices vegetation + climat) vs set complet.
COMPACT_FEATURES = True
# Masquage des pixels nuageux via QA60 avant moyenne (anti-bruit optique).
USE_QA60_MASK = True

# Indices de vegetation = (A-B)/(A+B) sur bandes nommees. red-edge B5 = NDRE
# (azote/biomasse), B3 vert = GCVI/NDWI. Tous insensibles a l'echelle.
VEG_INDICES = {
    "NDVI": ("B8", "B4"),   # verdure / vigueur
    "NDRE": ("B8", "B5"),   # red-edge : azote, biomasse (souvent + predictif)
    "GNDVI": ("B8", "B3"),  # chlorophylle (vert)
    "NDWI": ("B3", "B8"),   # eau / stress hydrique
}


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


def _channels(band: str) -> list[int]:
    """Indices des 12 pas de temps pour une bande nommee (carte d'offsets figee)."""
    off = BAND_OFFSET[band]
    return [t * N_BANDS_PER_STEP + off for t in range(N_STEPS)]


def decode_bands():
    """
    Verifie que Bandnames.txt correspond a la structure figee (temps-major,
    30 bandes/pas). Si le fichier est lisible, on controle les 30 premiers noms ;
    sinon on fait confiance a la carte d'offsets (structure deja confirmee).
    """
    try:
        names = [l.strip() for l in open(BANDNAMES) if l.strip()]
    except Exception:
        names = []

    if len(names) == ARR_SHAPE[0]:
        # Controle : le nom du pas 0 doit finir par la bande attendue a l'offset.
        ok = all(names[off].upper().endswith(b.upper())
                 for b, off in BAND_OFFSET.items())
        if ok:
            print("Bandnames.txt verifie : structure temps-major confirmee (30/pas).")
        else:
            print("ATTENTION : Bandnames.txt ne colle pas a la carte d'offsets ! "
                  f"pas0[3]={names[3]!r} attendu *B4. Verifier l'ordre.")
    else:
        print(f"Bandnames.txt illisible ({len(names)} lignes) "
              "-> carte d'offsets figee utilisee (structure confirmee).")
    print("Indices vegetation actifs :", ", ".join(VEG_INDICES))
    print("Variables climat actives  :", ", ".join(CLIM_TARGETS))


def _center(flat_cube: np.ndarray) -> np.ndarray:
    """Sous-cube central 9x9 aplati en (360, k) — anti pixel-mixte."""
    h = ARR_SHAPE[1] // 2
    s = slice(h - CENTER_HALF, h + CENTER_HALF + 1)
    return flat_cube[:, s, s].reshape(flat_cube.shape[0], -1)


def _index_series(mean: np.ndarray, a_band: str, b_band: str) -> np.ndarray:
    """
    Indice normalise (A-B)/(A+B) par pas de temps, borne [-1,1].
    Les pas manquants (A ou B = NaN, ou denom == 0) restent NaN : c'est le
    signal « trou nuageux » que _interpolate_series comblera ensuite.
    """
    a = mean[_channels(a_band)]
    b = mean[_channels(b_band)]
    denom = a + b
    with np.errstate(divide="ignore", invalid="ignore"):
        s = np.where(denom != 0, (a - b) / denom, np.nan)
    return np.clip(s, -1.0, 1.0).astype(np.float32)


def _interpolate_series(s: np.ndarray) -> np.ndarray:
    """
    Comble les 'trous noirs' (vrais nodata = NaN) par interpolation linéaire
    temporelle. ATTENTION : seul NaN est considéré comme manquant — un 0.0
    réel (ex : précipitation nulle en saison sèche) est PRÉSERVÉ.
    """
    s_clean = s.astype(np.float32).copy()
    missing = np.isnan(s_clean)

    # Tout manquant (parcelle entièrement nuageuse) -> série neutre (zéros).
    if missing.all():
        return np.nan_to_num(s_clean)
    # Rien à combler.
    if not missing.any():
        return s_clean

    indices = np.arange(len(s_clean))
    s_clean[missing] = np.interp(
        indices[missing], indices[~missing], s_clean[~missing]
    )
    return s_clean


def _serie_stats(s: np.ndarray) -> np.ndarray:
    """Stats agronomiques d'une serie temporelle (phenologie)."""
    return np.array([
        s.mean(), s.max(), s.min(), s.std(),
        float(s.sum()),                 # AUC ~ cumul saisonnier
        float(np.argmax(s)),            # mois du pic
        float(s.max() - s.min()),       # amplitude
    ], dtype=np.float32)


def _features_from_cube(cube: np.ndarray) -> np.ndarray:
    """
    (360,41,41) -> features (anti-nuages QA60 + interpolation nodata + anti pixel-mixte).
    """
    c = cube.astype(np.float32)
    nb = N_BANDS_PER_STEP

    # 1) nodata : -9999 partout ; 0 seulement sur la réflectance S2 (B1..B12).
    #    QA60 exclu (0 = ciel clair, valeur réelle) ; climat exclu (0 réel).
    c[c == -9999.0] = np.nan
    refl_channels = [t * nb + o for t in range(N_STEPS) for o in S2_REFLECTANCE_OFFSETS]
    sub = c[refl_channels]
    sub[sub == 0.0] = np.nan
    c[refl_channels] = sub

    # 2) Masquage nuages via QA60 : par pas, on annule les pixels S2 nuageux.
    if USE_QA60_MASK:
        for t in range(N_STEPS):
            qa = c[t * nb + QA60_OFFSET]                 # (41,41)
            cloudy = np.nan_to_num(qa) > 0               # QA60 != 0 => nuage/cirrus
            if cloudy.any():
                for o in S2_OFFSETS:
                    ch = c[t * nb + o]
                    ch[cloudy] = np.nan
                    c[t * nb + o] = ch

    # 3) Fenetre centrale + moyenne robuste. On GARDE les NaN (pas full→0 ici) :
    #    un canal entièrement masqué doit rester NaN pour être interpolé après.
    win = _center(c)
    with np.errstate(all="ignore"):
        mean = np.nanmean(win, axis=1)                   # (360,) — NaN si pas vide
        std = np.nan_to_num(np.nanstd(win, axis=1))

    feats = []
    # 4) Multi-indices de vegetation : serie + interpolation (NaN) + stats phenologiques.
    for name, (a, b) in VEG_INDICES.items():
        s = _index_series(mean, a, b)
        s = _interpolate_series(s)                       # comble les trous nuageux
        if name == "NDVI":
            feats.append(s)                              # serie complete pour NDVI
        feats.append(_serie_stats(s))

    # 5) Climat (pilotes inter-annuels) : interpolation des vrais nodata seulement,
    #    les 0.0 réels (saison sèche) sont conservés.
    for name in CLIM_TARGETS:
        serie = _interpolate_series(mean[_channels(name)])
        feats.append(np.array([
            float(np.nansum(serie)), float(np.nanmean(serie)),
            float(np.nanmax(serie)), float(np.nanargmax(serie)),
        ], dtype=np.float32))

    if not COMPACT_FEATURES:
        feats = [np.nan_to_num(mean), std] + feats       # + tous les canaux bruts

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
        # Recherche INSENSIBLE A LA CASSE (le fichier reel est 'bandnames.txt').
        hits = [p for p in glob.glob("/kaggle/input/**/*.txt", recursive=True)
                if os.path.basename(p).lower() == "bandnames.txt"]
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

    X, y, years, quals, ok, skipped_label = [], [], [], [], 0, 0
    for _, row in df.iterrows():
        cube = _load_array(row[ID_COL])
        if cube is None:
            continue
        # Label invalide (NaN / non numérique) -> on n'entraîne pas dessus.
        try:
            label = float(row[TARGET_COL])
        except (TypeError, ValueError):
            skipped_label += 1
            continue
        if not np.isfinite(label):
            skipped_label += 1
            continue
        try:
            X.append(_features_from_cube(cube))
            y.append(label)
            years.append(row.get(YEAR_COL, 0))
            quals.append(row.get(QUALITY_COL, 0))
            ok += 1
        except Exception:
            continue
    print(f"Cubes chargés et vectorisés : {ok}/{len(df)}"
          + (f" (labels invalides ignorés : {skipped_label})" if skipped_label else ""))
    if ok == 0:
        raise RuntimeError("Aucun cube chargé — vérifie IMG_DIR / noms de fichiers.")
    return (np.vstack(X), np.array(y, dtype=float),
            np.array(years), np.array(quals))


def _cv_scores(model, X, y, splits):
    y_pred = cross_val_predict(model, X, y, cv=splits)
    return (r2_score(y, y_pred),
            float(np.sqrt(mean_squared_error(y, y_pred))),
            mean_absolute_error(y, y_pred))


def _baseline_cv_r2(y, splits):
    """
    R² du prédicteur « moyenne du TRAIN » évalué sur les MÊMES splits CV.
    C'est la baseline honnête : en GroupKFold/année elle est souvent négative
    (chaque campagne a sa propre moyenne), contrairement au R²=0 en in-sample.
    """
    y_pred = np.empty_like(y, dtype=float)
    for train_idx, test_idx in splits:
        y_pred[test_idx] = y[train_idx].mean()
    return r2_score(y, y_pred)


def evaluer(model, X, y, years):
    """
    Double validation :
      - GroupKFold par ANNEE  = generalisation a une campagne INEDITE (= usage reel nowcast).
      - KFold aleatoire        = le signal existe-t-il (intra-annee) ?
    La baseline « moyenne » est calculee sur les MEMES splits que la metrique de reference.
    """
    kf_splits = list(KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE).split(X))
    r2_rand, rmse_rand, mae_rand = _cv_scores(model, X, y, kf_splits)
    print(f"\n[KFold aleatoire]   R2={r2_rand:.3f}  RMSE={rmse_rand:.2f}  MAE={mae_rand:.2f}")

    n_annees = len(set(years.tolist()))
    if n_annees >= 2:
        ref_splits = list(GroupKFold(n_splits=min(5, n_annees)).split(X, y, years))
        r2, rmse, mae = _cv_scores(model, X, y, ref_splits)
        print(f"[GroupKFold/annee]  R2={r2:.3f}  RMSE={rmse:.2f}  MAE={mae:.2f}  "
              f"({n_annees} annees) <- metrique de reference")
    else:
        print("Une seule annee -> pas de GroupKFold ; on retient le KFold aleatoire.")
        ref_splits = kf_splits
        r2, rmse, mae = r2_rand, rmse_rand, mae_rand

    # Baseline honnete : meme CV, predit la moyenne du train de chaque fold.
    r2_base = _baseline_cv_r2(y, ref_splits)
    print(f"[Baseline moyenne]  R2={r2_base:.3f}  <- predire la moyenne du train (memes splits)")

    return r2, rmse, mae, r2_base


def _new_model():
    return XGBRegressor(
        n_estimators=300,        # Réduit pour éviter l'overfitting
        max_depth=3,             # Très peu profond pour forcer la généralisation
        learning_rate=0.04,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=1.0,           # Régularisation L1 (Lasso)
        reg_lambda=2.0,          # Régularisation L2 (Ridge)
        random_state=RANDOM_STATE,
        verbosity=0,
        n_jobs=-1,
    )


def ablation_qualite(X, y, years, quals):
    """Le bruit des labels plafonne-t-il le R² ? Compare des sous-ensembles Quality."""
    niveaux = sorted(set(int(q) for q in quals if q))
    if not niveaux:
        return
    print("\n──────────── ABLATION QUALITÉ (le bruit des labels plafonne-t-il ?) ────────────")
    sous_ensembles = []
    for q in niveaux:                       # qualite exacte
        sous_ensembles.append((f"Quality=={q}", quals == q))
    for q in niveaux[:-1]:                   # cumulatif <= q
        sous_ensembles.append((f"Quality<={q}", quals <= q))
    sous_ensembles.append(("TOUT", np.ones(len(y), dtype=bool)))

    kf = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    for label, mask in sous_ensembles:
        n = int(mask.sum())
        if n < 100:
            print(f"  {label:<14} n={n:<5} (trop peu — ignore)")
            continue
        Xs, ys, ys_years = X[mask], y[mask], years[mask]
        r2_rand, _, _ = _cv_scores(_new_model(), Xs, ys, list(kf.split(Xs)))
        line = f"  {label:<14} n={n:<5} KFold R²={r2_rand:+.3f}"
        n_an = len(set(ys_years.tolist()))
        if n_an >= 2:
            gkf = GroupKFold(n_splits=min(5, n_an))
            r2_grp, _, _ = _cv_scores(_new_model(), Xs, ys, list(gkf.split(Xs, ys, ys_years)))
            line += f"  |  GroupKFold/annee R²={r2_grp:+.3f}"
        print(line)


def main():
    X, y, years, quals = construire_dataset()
    print(f"\nMatrice features : {X.shape}  | cible moy={y.mean():.1f} σ={y.std():.1f}")

    model = _new_model()
    r2, rmse, mae, r2_base = evaluer(model, X, y, years)
    ablation_qualite(X, y, years, quals)

    print("\n──────────── MÉTRIQUES HONNÊTES (CV) ────────────")
    print(f"  R²    : {r2:.3f}   (baseline 'moyenne' CV = {r2_base:.3f})")
    print(f"  RMSE  : {rmse:.1f}")
    print(f"  MAE   : {mae:.1f}")

    deployable = (r2 > max(r2_base, 0.0)) and (r2 >= MIN_R2)
    print(f"  Déployable ? {'OUI ✅' if deployable else 'NON ❌ (signal inter-annuel trop faible)'}")

    model.fit(X, y)
    modele_dict = {
        "model": model,
        "n_features": int(X.shape[1]),
        "config": {
            "N_BANDS_PER_STEP": N_BANDS_PER_STEP,
            "band_offset": BAND_OFFSET,
            "veg_indices": VEG_INDICES,
            "clim_targets": CLIM_TARGETS,
            "center_half": CENTER_HALF,
            "use_qa60_mask": USE_QA60_MASK,
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
