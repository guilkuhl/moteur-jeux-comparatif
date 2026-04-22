## Why

Pour livrer un atlas exploitable par un moteur de jeu (Phaser, Godot, Unity, GameMaker…), les contraintes pixel sont critiques : une tuile de 17 px au lieu de 16 px produit des artefacts de texture au runtime (rounding GPU, filtrage imprécis, bleed de pixels). L'utilisateur doit **être averti visuellement** quand une cellule ne respecte pas les contraintes, **pas silencieusement recadrer**. Ce change ajoute un panneau de contraintes pixel au dashboard, couvrant : forçage multiple de N, POT (puissance de 2), padding interne, marge extérieure, rognage whitespace, et rapport des violations.

## What Changes

- **Panneau `Contraintes`** ajouté à `.convert-panel` avec checkbox "Activer contraintes" et sous-options :
  - `Forcer taille multiple de N` (input 1-1024, défaut 16).
  - `Forcer POT` (puissance de 2 : 8, 16, 32, 64, 128, 256, 512, 1024, 2048).
  - `Padding interne par sprite` (0-32 px, défaut 0).
  - `Marge extérieure globale` (0-64 px, défaut 0).
  - `Rognage auto whitespace` (checkbox — pré-rogne les pixels transparents aux bords avant application des contraintes).
  - `Marge post-rognage` (0-16 px, défaut 0).
- **Validation et avertissement non-destructif** : quand les contraintes sont actives et qu'une cellule/sprite ne respecte pas une règle (ex. 17 px avec « multiple de 16 »), le dashboard MUST :
  - afficher une overlay rouge sur la cellule concernée dans le comparateur,
  - ajouter une entrée au `#constraint-report` listant la nature du problème (« Cellule (3,2) : largeur 17 px, attendu multiple de 16 »),
  - ne PAS recadrer automatiquement sans confirmation.
- **Bouton `Corriger auto`** qui propose un plan de correction (recadrer, padder, rogner) via une modal avant d'appliquer.
- Route serveur `POST /api/constraints/validate` qui reçoit `{image, constraints, grid}` et renvoie `{violations: [{cellX, cellY, issue, suggestion}]}`.

## Capabilities

### New Capabilities
- `spritesheet-pixel-constraints`: validation des contraintes pixel (multiple de N, POT, padding, marge), avertissement non-destructif, report des violations, correction opt-in.

### Modified Capabilities
- `pixel-art-dashboard`: ajout d'un panneau `.constraints-panel` dans la sidebar ou adjacent à `.convert-panel`, avec UI complète et bouton `Corriger auto`.

## Impact

- **Frontend** : nouvelle section dans le DOM, logique de validation client + rendu overlays rouges sur cellules.
- **Backend** : nouvelle route `/api/constraints/validate`, nouvelle logique de calcul (lit les dimensions de chaque cellule selon la grille définie, croise avec les contraintes, retourne les violations).
- **Dépendance** : nécessite que la capability `spritesheet-slicing` (proposée séparément) soit au moins partiellement implémentée pour disposer d'une notion de "cellule". En absence de slicing, les contraintes s'appliquent uniquement à l'image entière.
- **Specs** : nouvelle capability + delta `pixel-art-dashboard`.
