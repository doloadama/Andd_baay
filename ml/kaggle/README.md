# Entraînement Kaggle — modèle de nowcast de rendement

Modèle ML « pilier rendement » d'Andd Baay, entraîné sur **vraies données**
(satellite + climat → rendement crop-cut), pas sur le seed synthétique.

## Dataset retenu
**CGIAR Crop Yield Prediction Challenge** (Zindi) — crop-cut yields + séries
Sentinel-2 (NDVI/EVI) + TerraClimate. C'est un modèle de **nowcast en cours de
saison** (≠ prédiction pré-campagne au semis).

> Accès : compte Zindi + accepter les règles du challenge, puis télécharger les CSV.

## Étapes (Kaggle, GPU non requis)

1. **Créer un notebook Kaggle** et y attacher le dataset (Add Input).
2. **Coller** le contenu de `train_yield_nowcast.py` dans une cellule
   (ou l'ajouter en *Utility Script*).
3. **Régler le bloc CONFIG** en haut selon l'entête réel :
   - `TARGET_COL` : colonne du rendement (ex. `yield`, `yield_kg_ha`).
   - `GROUP_COL`  : colonne géographique pour le split (ex. `field_id`, `village`, `commune`).
   - `ID_COLS` / `CATEGORICAL` : identifiants à exclure / colonnes texte.
4. **Run All**. Le script affiche des **métriques honnêtes** :
   - R², RMSE, MAE **+ baseline « prédire la moyenne »**.
   - Verdict : *bat la baseline ?* et *R² ≥ 0.30 ?* → sinon **non déployable**.
5. Récupérer `yield_nowcast.pkl` (onglet *Output*).

## Anti-fuite (critique)
Le split est **GroupKFold par zone géographique** : une même zone ne peut pas être
à la fois en train et en test. Sans ça, le R² est gonflé et le modèle échoue sur
une nouvelle exploitation. **Renseigne toujours `GROUP_COL`.**

## Intégration dans l'app (étape suivante, à faire ensemble)
Le `.pkl` produit est au format de `baay/services/ml_service.py`
(`model` / `features` / `encoders` / `meta`), mais c'est un modèle **nowcast**
(features satellite/climat), distinct du modèle pré-campagne par culture.

À faire côté app (non encore branché) :
- Construire le **même vecteur de features** à l'inférence depuis
  `ndvi_service` (NDVI) + `meteo_service` (pluies/SPI) — l'app les calcule déjà.
- Charger `yield_nowcast.pkl` et l'utiliser en **nowcast** quand le cycle est
  avancé (>30 %), en complément du moteur à règles.

→ Donne-moi l'entête du CSV Zindi : je fige le CONFIG + j'écris le branchement d'inférence.
