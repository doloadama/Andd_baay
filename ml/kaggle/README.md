# Entraînement Kaggle — nowcast de rendement (Zindi CGIAR)

Modèle ML « pilier rendement » d'Andd Baay, entraîné sur **vraies données**
satellite (Sentinel-2) → rendement crop-cut. Modèle de **nowcast** (en cours de
saison), distinct de la prédiction pré-campagne au semis.

## Format réel du dataset
- `Train.csv` : `Field_ID, Year, Quality, Yield` (la cible).
- `Image_arrays_train/` : un `.npy` par parcelle, shape **(360, 41, 41)**
  = 360 canaux (temps × bandes) × patch spatial 41×41.
- `Bandnames.txt` : noms des 360 canaux.
- `test_field_ids_with_year.csv` : années du test (pour ajouter la météo).

## Approche (CPU, pas de GPU)
Cube `(360,41,41)` → **features tabulaires** (moyenne + écart-type spatial par
canal, + **NDVI temporel** si bandes Rouge/PIR connues) → **XGBoost**.
C'est l'approche gagnante classique sur ces challenges et elle tourne sur CPU.
(Un CNN sur le cube = piste GPU ultérieure, pas nécessaire pour un premier modèle.)

## Étapes Kaggle
1. Notebook Kaggle → **Add Input** : attacher le dataset CGIAR.
2. **Décompresser** `Image_arrays_train.zip` (Kaggle le fait souvent ; sinon
   `!unzip` dans une cellule) et ajuster `IMG_DIR` dans le CONFIG.
3. Coller `train_yield_nowcast.py`, **régler le CONFIG** :
   - chemins `TRAIN_CSV`, `IMG_DIR`, `BANDNAMES` (selon le sous-dossier exact).
   - **NDVI** (recommandé) : depuis `Bandnames.txt`, renseigner
     `N_BANDS_PER_STEP` (ex. 12), `RED_IDX_IN_STEP`, `NIR_IDX_IN_STEP`.
4. **Run All** → métriques honnêtes (R², RMSE, MAE **+ baseline moyenne**) et
   verdict *« Déployable ? »*. Récupérer `yield_nowcast.pkl` (onglet Output).

## Anti-fuite
Pas de colonne géographique dans le train (Field_ID = unique par échantillon).
→ Split **GroupKFold par ANNÉE** (`Year`) = anti-fuite **temporelle** (on n'évalue
pas sur une année vue à l'entraînement). Le filtre `Quality` écarte les labels GPS douteux.

## Bandes (résolu) — CONFIG figé
`Bandnames.txt` = **12 pas de temps × 30 bandes** : 16 Sentinel-2 (B1–B12, B8A,
QA10/20/60) + 14 TerraClimate (`pr`, `aet`, `pet`, `soil`, `pdsi`, `tmmn/tmmx`,
`vpd`…). Le **climat est déjà dans le cube** → pas de météo externe à ajouter.
NDVI = B8/B4 → CONFIG : `N_BANDS_PER_STEP=30, RED_IDX_IN_STEP=3, NIR_IDX_IN_STEP=7`.

Features produites par parcelle (**739**) : moyenne + écart-type spatial des 360
canaux, + **NDVI mensuel (12)** + stats NDVI (moyenne, max, min, σ, AUC, mois du
pic, amplitude). Vérifié sur cube synthétique (NDVI correct, sans NaN).

Seuls les **chemins** restent à ajuster selon le sous-dossier exact du dataset
attaché (`TRAIN_CSV`, `IMG_DIR`, `BANDNAMES`).

## Verdict final (campagne d'optimisation complète)

Structure confirmée : `0_S2_B1 … 0_CLIM_vs, 1_S2_B1 …` = **12 pas × 30 bandes**,
temps-major. NDVI = B8/B4 (offsets 7/3). Décodage **correct dès le départ**.

| Version | features | KFold aléatoire | GroupKFold/année (réf.) |
|---|---|---|---|
| NDVI seul | 19 | 0.097 | −0.085 |
| + climat TerraClimate | 51 | 0.182 | −0.023 |
| + QA60 + red-edge + interpolation + régul. | 72 | **0.212** | **+0.046** |
| baseline « moyenne » (mêmes splits CV) | — | — | −0.047 |

Filtre qualité : `Quality<=2` → GroupKFold 0.060 ; `Quality==3` (44 %) = bruit.

**Conclusion : signal réel mais trop faible.** R²≈0.05 inter-année = un rendement
chiffré aurait ±53 % d'erreur (RMSE 1.7 t/ha pour moy 3.2). **Non déployable comme
chiffre.** Prédire le rendement absolu d'une parcelle paysanne (<2 ha, sous la
résolution Sentinel-2) sur 4 ans est intrinsèquement trop dur ici.

**Tous les leviers honnêtes épuisés** : décodage ✓, centre 9×9 ✓, climat ✓,
nuages QA60 ✓, red-edge NDRE ✓, interpolation ✓, régularisation ✓, filtre qualité ✓,
baseline CV honnête ✓.

## Ce qu'on en fait
- **Pas de prédiction chiffrée** depuis le satellite.
- Piste retenue : NDVI/NDRE comme **indicateur RELATIF** (« cette parcelle verdit
  X % sous la médiane locale ») — label-free, robuste, déployable via `ndvi_service`.
- Le rendement chiffré viendra du **modèle pré-campagne par culture** une fois de
  **vraies** observations terrain accumulées (cf. `docs/project-state.md`).
- Si un jour un dataset plus dense apparaît (plus d'années, parcelles plus grandes),
  ce script reste prêt — réattacher les données suffit.
