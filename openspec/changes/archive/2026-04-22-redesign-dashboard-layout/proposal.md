## Why

Le dashboard actuel empile plusieurs zones de comparaison, barres d'outils, détails, grille d'iters et panneau Convertir dans une mise en page dense qui oblige l'utilisateur à scroller pour voir le résultat complet d'un sprite. Pour du **tuning live**, on veut voir l'image de travail au plus grand possible, toujours à l'écran, sans perdre de pixel de focus.

Le style Upscayl (référence jointe par l'utilisateur) est une illustration typique : **sidebar gauche étroite** avec contrôles verticaux, **zone image à droite** qui prend 100% de la hauteur et toute la largeur restante, avec la poignée de slider toujours visible au centre — zéro scroll, aucune compétition visuelle.

## What Changes

- Réorganiser le layout principal du dashboard en **deux colonnes** plein écran :
  - **Colonne gauche fixe** (~280 px, rétractable) contenant : sidebar images + panneau Convertir (builder pipeline, toggles live/fullres/preserve_bg, bouton Lancer, indicateur status).
  - **Colonne droite fluide** qui occupe 100% de la hauteur restante et toute la largeur, dédiée uniquement au comparateur slider (image source ↔ dernier iter ou preview) avec poignée centrale.
- Retirer de la vue principale : barre de tri/filtre, grille d'iters, détails textuels d'un iter (ce contenu devient accessible via un panneau rétractable droit « Détails » ouvert sur demande).
- Ajouter deux chevrons `<` et `>` de rétractation pour fermer/ouvrir la sidebar gauche et le panneau droit (comme chez Upscayl) : permet de mettre le comparateur vraiment plein écran.
- Poignée du slider centrée dans le viewport (viewport-centric), pas au milieu du body image — elle reste toujours accessible quelle que soit la taille de l'image.
- Toolbar minimale en haut du comparateur : titre du sprite, zoom × (±, reset, axes pixel), toggle light/dark (existant). Le reste passe dans la sidebar ou les panneaux.
- Nouvel onglet/panneau **Historique** accessible via un bouton en bas de la sidebar gauche, qui affiche la grille d'iters dans un overlay ou panneau rétractable (remplace la vue grid principale actuelle).
- **BREAKING** (UI seulement) : la grille d'iters n'est plus affichée par défaut dans la zone principale. Les utilisateurs doivent ouvrir le panneau Historique pour y accéder. Aucune API ni CLI n'est touchée.

## Capabilities

### New Capabilities

Aucune.

### Modified Capabilities

- `pixel-art-dashboard` : nouvelle mise en page 2 colonnes full-height, panneaux rétractables, comparateur toujours plein écran, grille d'iters déplacée dans un panneau historique rétractable, poignée slider viewport-centric.

## Impact

- Code impacté : `pixel-lab/dashboard/index.html` principalement (CSS layout, structure HTML, logique de rétractation, repositionnement de la grille dans un panneau historique).
- Rétrocompat : tous les raccourcis, toggles, bouton Lancer, mode live, sélection d'image restent fonctionnels. Les URLs de contenu, l'API, le CLI `process.py` et `history.json` ne changent pas.
- Performance : neutre ou légèrement améliorée (moins de DOM rendu par défaut quand la grille d'iters est dans un panneau fermé).
- UX : beaucoup plus d'espace pour l'image, scroll supprimé pour le cas d'usage principal (tuning live).
