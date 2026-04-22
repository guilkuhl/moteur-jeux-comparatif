## Why

Un spritesheet "trouvé" (récupéré d'un asset store, de GenAI, d'une capture) contient souvent des irrégularités : frames dans un ordre non optimal pour l'animation, doublons d'images, décalages sous-pixel résiduels d'un upscale imparfait, tailles non-uniformes mélangées. Avant export, un outil de **nettoyage/réorganisation** évite des heures de correction manuelle.

## What Changes

- **Panneau `Nettoyage`** avec 5 outils :
  1. **Réordonnancement frames** : drag-and-drop dans une vue grille-miniatures pour réorganiser l'ordre d'export.
  2. **Suppression doublons** : détecte les cellules pixel-identiques (ou à un seuil de similarité), propose de les marquer comme `ignore` ou de réutiliser une seule occurrence.
  3. **Détection décalage sous-pixel** : repère les cellules dont le contenu est décalé de 1-2 px par rapport à un alignement idéal (via corrélation croisée). Propose un recalage auto.
  4. **Rapport d'anomalies** : produit un JSON + affichage UI listant tous les problèmes (doublons, décalages, cellules vides, violations de contraintes).
  5. **Normalisation taille uniforme** : force toutes les cellules à la même taille (max dimensions rencontrées + padding pour centrer).

## Capabilities

### New Capabilities
- `spritesheet-cleanup`: outils de réordonnancement, dé-duplication, détection décalage sous-pixel, rapport anomalies, normalisation.

### Modified Capabilities
- `pixel-art-dashboard`: ajout du panneau Nettoyage et des 5 actions.

## Impact

- **Frontend** : vue grille-miniatures interactive, drag-drop, actions par clic avec modal.
- **Backend** : nouvelle famille de routes `/api/cleanup/*` :
  - `POST /api/cleanup/detect-duplicates`
  - `POST /api/cleanup/detect-subpixel`
  - `POST /api/cleanup/normalize`
  - `GET /api/cleanup/report`
- Algorithmes : hash perceptuel pour doublons, corrélation 2D FFT pour sous-pixel.
