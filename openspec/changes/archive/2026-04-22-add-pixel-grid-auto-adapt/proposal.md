## Why

La capability `pixel-grid-overlay` existante masque la grille quand `pixelScreen < 2` (au step demandé) et affiche un warning ⚠. L'utilisateur doit alors zoomer ou changer manuellement le step pour voir une grille. Ce comportement est prédictible mais pénalise le cas courant : activer la grille sur une image non zoomée. La demande explicite de l'utilisateur est : « la granularité minimale doit être 1 pixel réel de l'image », ce qui implique qu'on ne descend jamais sous le step natif, mais qu'on monte automatiquement tant qu'il faut pour rester lisible.

## What Changes

- Quand `pixelScreen = scale × stepUser < 2`, la fonction `drawPixelGrid()` MUST chercher le plus petit multiple de 2 ≥ `stepUser` tel que `scale × stepEff ≥ 2` (séquence 1→2→4→8→16→32→64). Si même à step=64 on reste en dessous du seuil, on masque.
- Le step auto-adapté MUST être affiché en toolbar : `grille · step 1→8` (par exemple). Sans auto-adapt, afficher simplement `grille · step 1`.
- Le warning ⚠ existant SHALL apparaître uniquement quand aucun step dans `[stepUser, 64]` ne satisfait le seuil (zoom vraiment trop faible).
- L'input `#grid-step` conserve la valeur **utilisateur** (ne pas mutuer visuellement la valeur saisie). L'auto-adapt est purement interne au rendu.
- `localStorage.dashGridStep` conserve la valeur utilisateur, pas la valeur auto-adaptée.

## Capabilities

### New Capabilities
<!-- aucune -->

### Modified Capabilities
- `pixel-grid-overlay`: MODIFIED du requirement « Si la grille devient illisible… » pour introduire l'auto-adapt avant masquage. Ajout d'un requirement sur l'affichage du step effectif en toolbar.

## Impact

- **Frontend (pixel-lab/dashboard/index.html)** : modifier `drawPixelGrid()` pour calculer `stepEff`, dessiner à partir de cette valeur, et écrire le label `step X→Y` dans un nouvel élément `#grid-step-label` de la toolbar (ou `title` du bouton si on veut rester compact).
- **Backend** : aucun changement.
- **Specs** : mise à jour de `openspec/specs/pixel-grid-overlay/spec.md` via delta MODIFIED + ADDED.
- **Tests visuels** : 3 scénarios à ajouter.
