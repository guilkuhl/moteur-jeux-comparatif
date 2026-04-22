## Why

L'overlay grille pixel actuelle (capability `pixel-grid-overlay`) utilise une couleur blanche fixe avec opacité 0.15/0.30 et `mix-blend-mode: difference`. Sur certains spritesheets (fonds blancs ou très clairs), la grille devient illisible. L'utilisateur a besoin de personnaliser la couleur, l'opacité et éventuellement le blend mode pour adapter la grille au contraste de son image.

## What Changes

- Ajout de **3 contrôles** dans la toolbar du comparateur (visibles quand grille active) :
  - `<input type="color">` couleur principale (défaut `#ffffff`).
  - `<input type="range" min="0.05" max="1" step="0.05">` opacité (défaut `0.15`).
  - `<select>` blend mode : `difference` (défaut), `normal`, `multiply`.
- Persistance dans `localStorage` :
  - `dashGridColor` (string `#RRGGBB`).
  - `dashGridOpacity` (string `0.15`).
  - `dashGridBlend` (string mode CSS).
- La grille MUST se redessiner immédiatement à chaque changement.
- Le bouton `🔳` actuel reste inchangé ; les 3 contrôles apparaissent à côté de `#grid-step-label` et se masquent quand la grille est désactivée.

## Capabilities

### New Capabilities
<!-- aucune -->

### Modified Capabilities
- `pixel-grid-overlay`: ADDED requirement « La grille doit exposer 3 contrôles de personnalisation visuelle (couleur, opacité, blend mode) ». MODIFIED le requirement de dessin existant pour utiliser les valeurs configurables.

## Impact

- **Frontend (pixel-lab/dashboard/index.html)** : 3 nouveaux inputs dans `.cmp-toolbar`, fonction `setGridStyle({color, opacity, blend})`, refactor de `drawPixelGrid()` pour utiliser ces valeurs.
- **Backend** : aucun changement.
- **Specs** : delta MODIFIED + ADDED dans `pixel-grid-overlay`.
