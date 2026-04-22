## Why

Le bouton `Axes pixel` actuel (capability `pixel-axes-overlay`) affiche uniquement deux flèches matérialisant l'échelle d'un pixel natif — utile pour jauger le zoom, mais insuffisant pour analyser l'agencement des pixels d'un sprite. Pour juger la qualité d'un upscaler (scale2x, pixelsnap), comparer des variantes de denoising, ou aligner à l'œil un sprite sur sa grille native, l'utilisateur veut une **grille complète** (lignes horizontales + verticales à chaque pixel natif, ou par multiples de N pixels) qu'il puisse activer/désactiver instantanément et régler en pas.

## What Changes

- Ajouter un nouveau bouton `🔳 Grille` dans la toolbar du comparateur (à côté du bouton `⊹ Axes pixel` existant), toggle on/off.
- Ajouter un raccourci clavier `G` qui bascule le toggle (cohérent avec `H` pour le panneau historique).
- Quand actif, dessiner sur un overlay `<canvas>` une grille complète : lignes verticales tous les `N` pixels natifs + lignes horizontales tous les `N` pixels natifs, couvrant toute la surface visible de `#cmp-left`.
- Exposer un champ `pas` (step) à côté du bouton (défaut 1, bornes 1-64) pour choisir la densité de la grille.
- Persister l'état du toggle et le pas dans `localStorage` (clés `dashGridOn`, `dashGridStep`).
- La grille SHALL se redessiner au zoom, resize et scroll comme l'overlay axes pixel existant.
- **Distinction claire** avec `pixel-axes-overlay` : les axes restent une jauge d'échelle (deux flèches), la grille couvre l'image entière.

## Capabilities

### New Capabilities
- `pixel-grid-overlay`: overlay grille complète sur le comparateur, toggleable, avec pas configurable et persistance d'état.

### Modified Capabilities
- `pixel-art-dashboard`: ajout d'une exigence sur le bouton `🔳 Grille` dans la toolbar du comparateur et son raccourci clavier `G`.

## Impact

- **Frontend (pixel-lab/dashboard/index.html)** : ajout d'un nouveau `<canvas id="grid-overlay">` dans le comparateur, nouveau bouton `.zbtn` dans `.cmp-toolbar`, input numérique step, logique de rendu (`drawPixelGrid()`), handlers zoom/resize/scroll réutilisés, raccourci `G`.
- **Backend** : aucun changement.
- **Specs** :
  - Nouvelle capability `openspec/specs/pixel-grid-overlay/spec.md`.
  - Mise à jour `openspec/specs/pixel-art-dashboard/spec.md` pour exiger le bouton dans la toolbar.
- **Conflits potentiels** : aucun, l'overlay axes pixel existant et la grille peuvent cohabiter (deux canvas indépendants, z-index séparés).
