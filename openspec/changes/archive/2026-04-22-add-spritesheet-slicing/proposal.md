## Why

Un spritesheet n'est utile que découpé en cellules. Les spritesheets du commerce ont très souvent des cellules de tailles mixtes : une base régulière (ex. 16×16) avec quelques sprites plus grands (boss, animation spéciale) qui occupent plusieurs cellules ou ont des dimensions custom. Un simple découpage régulier est insuffisant. Ce change ajoute un éditeur de découpe permettant d'avoir une grille de base PLUS des overrides manuels (cellule redimensionnée, ignorée, fusionnée).

## What Changes

- **Panneau `Slicing`** dans le dashboard avec :
  - Input `cols × rows` (grille régulière).
  - Input `cellW × cellH` (dimensions d'une cellule en px natifs).
  - Input `gap-x × gap-y` (espacement entre cellules).
  - Input `margin-left/top` (offset depuis l'angle supérieur gauche).
  - Bouton `Éditer cellules…` qui active le mode override.
- **Mode override** : clic sur une cellule ouvre un popover avec options :
  - `Redimensionner` (préciser une largeur/hauteur custom en px).
  - `Fusionner avec voisins` (sélection rectangulaire).
  - `Ignorer cette cellule` (ne sera pas exportée).
  - `Nommer` (assigner un nom custom pour l'export).
- **Visualisation** : grille dessinée en overlay (réutilise l'infrastructure de `pixel-grid-overlay`), chaque cellule est numérotée (col,row) en badge, cellule survolée est surlignée (bbox jaune).
- Persistance : grille + overrides sauvegardés par image dans `history.json` (clé `slicing`).
- Nouvelle route `GET/PUT /api/slicing/<basename>` pour lire/écrire la config.

## Capabilities

### New Capabilities
- `spritesheet-slicing`: définition d'une grille régulière + overrides manuels (redimensionner, fusionner, ignorer, nommer), persistance par image.

### Modified Capabilities
- `pixel-art-dashboard`: ajout du panneau Slicing + mode override + numerotation cellules + surbrillance bbox.

## Impact

- **Frontend** : panneau Slicing complet, mode édition, overlay cellules (canvas distinct de pixel-grid-overlay), popover override, gestion de l'état slicing par image.
- **Backend** : route `GET/PUT /api/slicing/<basename>` qui lit/écrit la section `slicing` de `history.json`.
- **Specs** : nouvelle capability + delta dashboard.
- **Dépendance** : cette capability est un prérequis pour `spritesheet-pixel-constraints` (qui a besoin de connaître les cellules pour les valider) et `spritesheet-export` (qui a besoin de savoir comment découper pour exporter).
