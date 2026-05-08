# Stratégie responsive — Andd Baay

## Contexte
- Web : dashboard analytique sur desktop/tablette
- Mobile : saisie terrain (dépenses, photos plants, météo)
- Les agriculteurs utilisent principalement mobile en plein soleil
  → fort contraste obligatoire, textes grands, boutons larges

## Composants par breakpoint

### Navigation
- Mobile  : bottom nav bar (5 icônes) + drawer latéral
- Tablet  : sidebar rétractable 64px (icônes seules)
- Desktop : sidebar 220px (icônes + labels)

### KPI Cards
- Mobile  : scroll horizontal (snap) ou 1 colonne
- Tablet  : 2 colonnes
- Desktop : 4 colonnes

### Tableaux de données
- Mobile  : remplacés par liste de cards empilées
- Tablet  : tableau simplifié (3 colonnes max)
- Desktop : tableau complet avec toutes les colonnes

### Formulaires
- Mobile  : 1 colonne, labels au-dessus des champs
- Desktop : 2 colonnes, labels inline possibles

### Hero / Header page
- Mobile  : titre + 1 stat clé visible, reste en accordion
- Desktop : hero complet avec stat strip

## Tailles critiques
- Bouton CTA principal : h-11 (44px) minimum
- Input fields : h-11, font-16px (bloque zoom auto iOS)
- Bottom nav height : 64px + safe-area-inset-bottom
- Tap target spacing : gap-2 minimum entre éléments cliquables