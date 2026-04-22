## Context

Le comparateur central expose déjà `#cmp-left` (img source), `#cmp-overlay` (div clippé pour iter droit), `.cmp-toolbar` (contrôles zoom), le panneau `.iter-grid` à droite (via `H`). Tout ce qu'on ajoute ici s'accroche sur ces éléments existants — pas de restructuration.

Les 4 polissages n'ont aucune dépendance mutuelle mais partagent le même fichier `pixel-lab/dashboard/index.html`. On peut les implémenter dans n'importe quel ordre.

## Goals / Non-Goals

**Goals:**
- Chaque polissage est désactivable indépendamment (toggle, raccourci, ou bouton).
- Performance : pas de listener mousemove coûteux sur toute la page, seulement sur le conteneur comparateur.
- Le diff se calcule à la demande (clic bouton), pas automatiquement à chaque changement d'iter.
- Le nettoyage des orphelins propose mais ne supprime pas de manière destructive sans confirmation.

**Non-Goals:**
- Diff en live preview mode (trop coûteux, hors scope).
- Annuler la suppression de fichier source (pas de corbeille).
- Multi-sélection d'iters pour comparaison à trois (hors scope).

## Decisions

**Décision 1 — HUD coords : tooltip suivant la souris + freeze sur shift.**
Un élément `<div id="pixel-hud">` position fixe avec offset `(12, 16)` du curseur. Mis à jour dans le listener `mousemove` throttlé à ~60 fps (`requestAnimationFrame`). Affiche `x y  #RRGGBB`. Maintenir `Shift` fige le HUD (utile pour copier la coordonnée).

Couleur lue via un `<canvas>` offscreen de 1×1 pixel qui draw `#cmp-left` à la bonne position et lit `getImageData`. Pour éviter de reconstruire le canvas à chaque move, on cache une copie du canvas complet (taille naturelle de l'image) dès qu'elle change d'`src`.

**Décision 2 — Diff : canvas comparatif unique.**
Quand l'utilisateur clique `Δ Diff`, on :
1. Draw `#cmp-left` sur un canvas A taille = naturalWidth/Height du source.
2. Draw `cmp-right` (iter ou preview) sur un canvas B de même taille (avec scale si tailles différentes — nearest-neighbor).
3. Comparer pixel par pixel via `ImageData` : si `Δlum > 4` alors peindre `rgba(255,0,0,0.6)` sur un canvas C overlay ; si le pixel n'existe qu'en B (différence d'alpha) peindre en `rgba(0,255,0,0.6)`.
4. Afficher le canvas C par-dessus le comparateur avec `z-index: 25` (au-dessus de `#cmp-overlay` mais sous la toolbar).
5. Afficher dans la toolbar un badge `N pxs différents (p %)`.

Le diff est recalculé à chaque clic du bouton (pas automatique) pour rester rapide même sur de grandes images.

**Décision 3 — Navigation clavier iters.**
- `←` : sélectionne l'iter précédent dans l'ordre actuel du panneau historique.
- `→` : sélectionne l'iter suivant.
- `Home` / `End` : premier / dernier iter.
- `Esc` : revenir à l'iter le plus récent (comportement par défaut au chargement).

Raccourcis ignorés quand le focus est dans un `input/textarea/select`, et quand l'image active n'a pas d'iter.

Un cheat-sheet overlay (`<div id="kbd-help">`) s'affiche au focus sur `?` ou `F1`. Contenu : `H` historique, `G` grille, `Esc` reset iter, `←→` navigation iters, `Shift` fige HUD, `? / F1` aide.

**Décision 4 — Orphelins : côté client d'abord, route serveur optionnelle.**
Au chargement, on récupère `/api/inputs` (déjà exposé) et on compare les clés de `history.json`. Toute clé absente de `/api/inputs` est marquée orphan et filtrée par défaut.

Un badge `(N orphelins)` apparaît en bas de la sidebar avec un bouton `Nettoyer`. Au clic :
- Option A (retenue) : modal de confirmation + `POST /api/history/prune` (nouvelle route backend qui retire les entrées côté serveur + archive les dossiers `outputs/<stem>/` dans un dossier `outputs/_trash/`).
- Option B (rejetée) : édition locale de history.json depuis le client → race conditions possibles, moins clean.

La route backend est minimaliste : elle liste les entrées à purger (basename), les retire de `history.json`, déplace chaque `outputs/<stem>/` vers `outputs/_trash/<stem>_<timestamp>/`.

## Risks / Trade-offs

- **Risque HUD** : `getImageData` sur un canvas CORS-tainted jette une exception si l'img est servie depuis un autre domaine. Ici tout est localhost:5500, mais bien vérifier que `<img crossorigin="anonymous">` est OK.
  **Mitigation** : ne pas mettre `crossorigin` (serveur même origine) et fallback gracieux si exception.

- **Risque Diff** : grosses images (4k×4k = 16M pixels × 4 bytes = 64 MB `ImageData`) → peut faire vaciller le navigateur.
  **Mitigation** : si `naturalWidth > 2048`, afficher un warning « diff downscaled à 2048 pour éviter le lag » et scale nearest-neighbor avant diff.

- **Risque raccourcis clavier** : conflit avec des raccourcis natifs (← → sont utilisés dans les `<input type=number>` pour incrémenter).
  **Mitigation** : le handler global skip si `document.activeElement` est un input/select/textarea.

- **Risque orphelins serveur** : la nouvelle route `POST /api/history/prune` peut supprimer des données utilisateur. Un bug mal testé serait destructif.
  **Mitigation** : move-to-trash plutôt que delete, pas de suppression silencieuse, confirmation obligatoire côté UI.

## Open Questions

- Le HUD doit-il suivre la souris ou rester ancré en haut à gauche de la toolbar ? → Décision mise à l'implémentation, la toolbar est probablement plus propre.
- Le diff doit-il colorier les zones proches (delta faible) ou seulement les pixels binairement différents ? → Δlum>4 comme seuil initial, ajustable.
