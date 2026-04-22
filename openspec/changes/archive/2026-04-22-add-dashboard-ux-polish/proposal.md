## Why

Le workflow quotidien du dashboard (sélectionner une image, lancer une conversion, inspecter les iters, comparer) gagne beaucoup à des raccourcis et indicateurs fins. Quatre polissages UX simples, indépendants entre eux, rendront l'inspection de sprites pixel-art nettement plus efficace : voir les coordonnées pixel sous la souris, surligner les pixels qui diffèrent entre source et iter, naviguer entre iters au clavier, et masquer les entrées orphelines de `history.json`.

## What Changes

1. **Coordonnées pixel sous le curseur** — un petit HUD flottant (badge coin haut-gauche de la toolbar ou tooltip suivant la souris) affiche `x,y` (pixels natifs) + `#RRGGBB` du pixel sous la souris pendant que celle-ci survole `#cmp-left` ou `#cmp-overlay`.
2. **Overlay diff source vs iter** — nouveau bouton `Δ Diff` dans la toolbar qui affiche un canvas surlignant en rouge/vert les pixels différents entre `#cmp-left` (source) et l'iter affiché à droite. Score colorimétrique global (nombre de pixels différents / total) dans le badge du bouton.
3. **Raccourcis clavier `←` `→`** — naviguent entre les iters dans le panneau Historique (équivalent d'un clic sur l'iter précédent/suivant), met à jour `compareRight`. Cheat-sheet visible via `?` ou `F1`.
4. **Nettoyage des entrées orphelines de history.json** — au chargement du dashboard, détecter les entrées dont le fichier source est absent de `pixel-lab/inputs/` (via `/api/inputs`) et les masquer par défaut. Un petit bouton `Nettoyer orphelins (N)` propose de les retirer de `history.json` (POST dédié ou édition client).

## Capabilities

### New Capabilities
<!-- aucune nouvelle : tout se rattache à pixel-art-dashboard -->

### Modified Capabilities
- `pixel-art-dashboard`: ajout de 4 requirements ciblés (HUD coordonnées, bouton Diff, raccourcis de navigation, gestion des orphelins).

## Impact

- **Frontend (pixel-lab/dashboard/index.html)** :
  - HUD coords : listener `mousemove` sur le conteneur comparateur, calcul `x = (e.clientX - rect.left) / scale`, lecture couleur via un canvas offscreen 1×1.
  - Bouton Diff : nouveau canvas comparatif (chargement des deux images sur un canvas partagé, boucle `ImageData`, peindre les pixels divergents).
  - Raccourcis clavier : ajout dans le handler global `keydown` (ignoré dans les inputs).
  - Orphelins : filtre à l'affichage de la sidebar + bouton visible quand `orphanCount > 0`.
- **Backend (pixel-lab/server/app.py)** : ajout (optionnel) d'une route `POST /api/history/prune` qui retire les entrées dont le fichier source n'existe pas. Alternative 100 % client : patcher `history.json` via `PUT /api/history` (plus intrusif). Choix du design à faire.
- **Specs (openspec/specs/pixel-art-dashboard/spec.md)** : ajout de 4 nouveaux requirements.
- **Tests visuels** : 4 scénarios clés à ajouter.
