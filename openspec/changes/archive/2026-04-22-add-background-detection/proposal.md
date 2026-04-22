## Why

Les algorithmes actuels (denoise, sharpen) traitent toute l'image indistinctement, ce qui dégrade le fond uni des sprites : les contours du sprite « bavent » sur le fond après un flou bilatéral, et les fonds parfaitement unis deviennent légèrement bruités. La plupart des sprites pixel-art ont un fond uniforme (parfois déjà transparent) qui devrait être préservé tel quel — seul le sprite lui-même a besoin des traitements.

On veut une détection automatique du fond, exposable dans le dashboard et utilisable comme masque optionnel par les algos existants pour leur faire ignorer les pixels de fond.

## What Changes

- Nouveau module `pixel-lab/scripts/algorithms/bgdetect.py` avec `detect_bg_color(img)`, `compute_bg_mask(img, bg_color=None, tolerance=8)` et un dict `METHODS` / `PARAMS` alignés sur les autres algos.
- Détection par **échantillonnage des 4 coins** (≥3 pixels identiques = couleur de fond) puis **flood-fill** depuis les bords. Si l'image est en mode RGBA et contient déjà des pixels alpha=0, ceux-ci servent directement de masque (bypass).
- Nouveau endpoint `GET /api/bgmask?image=<basename>&tolerance=<int>` qui retourne un PNG (alpha=0 pour le fond, 255 pour le foreground) pour visualisation.
- Nouveau paramètre optionnel `preserve_bg: bool` (défaut `False`) ajouté à **tous les PARAMS de `denoise/*` et `sharpen/*`** : quand `True`, l'algo applique son traitement puis recompose en réinjectant les pixels originaux du fond (masque calculé une fois, caché sur `(basename, mtime, tolerance)`).
- Dashboard : bouton `🎯 Détecter fond` dans le panneau Convertir, affichage d'une overlay semi-transparente du masque sur l'image active, toggle `Préserver le fond` qui bascule `preserve_bg=true` sur toutes les étapes compatibles du pipeline.
- **Rétrocompat** : `preserve_bg` est optionnel avec défaut `False`. Aucun pipeline existant, aucun appel CLI/API existant ne change de comportement.

## Capabilities

### New Capabilities

Aucune.

### Modified Capabilities

- `pixel-art-algorithms` : ajout du module/algo `bgdetect` (detect_bg_color, compute_bg_mask, METHODS/PARAMS). Ajout d'un paramètre `preserve_bg` à chaque méthode de `denoise` et `sharpen`.
- `pixel-art-conversion-api` : ajout de l'endpoint `GET /api/bgmask`, validation du paramètre `preserve_bg` dans les payloads `/api/convert` et `/api/preview`, mise en cache du masque réutilisable.
- `pixel-art-dashboard` : bouton de détection, overlay du masque, toggle global `Préserver le fond` appliqué aux étapes du builder.

## Impact

- Code impacté : `pixel-lab/scripts/algorithms/bgdetect.py` (nouveau), `pixel-lab/scripts/algorithms/denoise.py` + `sharpen.py` (ajout du wrapper `preserve_bg`), `pixel-lab/server/app.py` (endpoint + cache + validation), `pixel-lab/dashboard/index.html` (bouton + overlay + toggle).
- Dépendances : aucune nouvelle (PIL + numpy déjà utilisés ; `scipy.ndimage.label` ou flood-fill manuel en numpy — préférer numpy pur pour éviter la dépendance scipy).
- Performance : le calcul du masque est O(H×W) et caché sur `(basename, mtime, tolerance)`. Le surcoût de `preserve_bg=true` en pipeline est ~5-10 ms par étape (lookup cache + composition numpy).
- Aucun breaking change — tous les CLI, endpoints, presets et pipelines existants fonctionnent sans modification.
