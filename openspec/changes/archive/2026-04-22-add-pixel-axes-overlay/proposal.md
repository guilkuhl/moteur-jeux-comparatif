## Why

Quand on compare des itérations pixel-art dans le dashboard, il est impossible de savoir visuellement à quoi correspond un pixel natif : l'image est affichée zoomée ou réduite, et aucune référence d'échelle n'est présente. Ajouter un overlay avec deux axes fléchés représentant exactement 1×1 pixel natif (en vert) donne une référence visuelle immédiate pour juger la netteté et la taille réelle des pixels.

## What Changes

- **NEW** Bouton toggle "Axes pixel" dans le footer du comparateur (et éventuellement sur les cartes individuelles).
- **NEW** Overlay `<canvas>` superposé à l'image : dessine un axe X (→) et un axe Y (↓) en vert avec flèches, dont la longueur correspond à exactement 1 pixel natif à l'échelle d'affichage courante.
- **NEW** L'overlay se redessine à chaque changement de zoom pour rester à l'échelle correcte.
- **NEW** Position de l'origine des axes : coin supérieur gauche de l'image, avec un léger décalage pour la lisibilité.
- Les axes sont affichés uniquement quand le toggle est actif (désactivé par défaut).

## Capabilities

### New Capabilities
- `pixel-axes-overlay` : Overlay canvas sur le comparateur du dashboard affichant deux axes fléchés verts représentant 1 pixel natif à l'échelle de zoom courante.

### Modified Capabilities
- `pixel-art-dashboard` : Ajout du toggle "Axes pixel" dans l'UI du comparateur.

## Impact

- **Code touché** : `pixel-lab/dashboard/index.html` uniquement (JS + HTML + CSS).
- **Aucune dépendance nouvelle** : canvas API native, pas de lib externe.
- **Aucune API backend** : feature 100 % frontend.
- **Aucun breaking change** : le comparateur existant reste inchangé si le toggle est désactivé.
