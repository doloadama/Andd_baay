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

## Ce qu'il me faut pour affiner
👉 **Colle le contenu de `Bandnames.txt`** (les 360 noms, ou au moins la structure :
nb de bandes par date + position du Rouge et du PIR). Avec ça je fige les indices
NDVI et j'ajoute les features agronomiques (AUC de verdure, date du pic).

## Intégration app (étape suivante)
Le `.pkl` n'est **pas** branché à l'app pour l'instant : c'est un modèle
satellite (features cube), pas le modèle pré-campagne par culture. Le brancher
suppose de reconstruire le même vecteur de features à l'inférence (NDVI/bandes
depuis `ndvi_service`) — à faire ensemble une fois le modèle validé sur Kaggle.
