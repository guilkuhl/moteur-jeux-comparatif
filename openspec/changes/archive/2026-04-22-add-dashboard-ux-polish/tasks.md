## 1. HUD coordonnées pixel

- [ ] 1.1 Créer un `<div id="pixel-hud">` en position fixed, caché par défaut (opacity 0)
- [ ] 1.2 Attacher un listener `mousemove` sur le conteneur comparateur (via `requestAnimationFrame` throttle)
- [ ] 1.3 Calculer `x, y` natifs via `(e.clientX - rect.left) / scale`, arrondir en entiers
- [ ] 1.4 Maintenir un canvas offscreen clone de `#cmp-left` (taille naturelle) pour lire la couleur via `getImageData(x,y,1,1)`
- [ ] 1.5 Rafraîchir le canvas offscreen quand `cmp-left.src` change
- [ ] 1.6 Gérer la touche `Shift` (keydown/keyup) pour figer le HUD
- [ ] 1.7 Cacher le HUD sur `mouseleave`

## 2. Overlay diff source vs iter

- [ ] 2.1 Ajouter un bouton `<button class="zbtn" id="btn-diff" title="Afficher les pixels divergents (D)">Δ</button>` dans `.cmp-toolbar`
- [ ] 2.2 Ajouter un badge `<span id="diff-count">` à côté pour le décompte
- [ ] 2.3 Implémenter `computeDiff()` : charger `#cmp-left` et la source de `cmp-right` sur deux canvas, scaler si différents, comparer `ImageData` pixel à pixel
- [ ] 2.4 Peindre les pixels divergents (`Δlum > 4`) en `rgba(255,0,0,0.6)` sur un canvas `#diff-overlay`, les pixels "iter only" en `rgba(0,255,0,0.6)`
- [ ] 2.5 Downscaler à 2048 max si `naturalWidth > 2048` et afficher un warning
- [ ] 2.6 Toggle on/off : second clic retire le canvas et le badge

## 3. Raccourcis clavier iters + cheat-sheet

- [ ] 3.1 Étendre le handler global `keydown` avec `ArrowLeft / ArrowRight / Home / End / Escape`
- [ ] 3.2 Implémenter `selectPrevIter()`, `selectNextIter()`, `selectFirstIter()`, `selectLastIter()`, `resetToLatestIter()`
- [ ] 3.3 Ignorer les raccourcis quand `document.activeElement` ∈ {INPUT, TEXTAREA, SELECT}
- [ ] 3.4 Créer un overlay `<div id="kbd-help">` masqué par défaut, listant : H, G, Esc, ←→, Shift, ?/F1
- [ ] 3.5 Afficher/masquer l'overlay sur `?` ou `F1`

## 4. Orphelins history.json — client

- [ ] 4.1 Au `loadHistory()`, après la récupération de `/api/inputs`, calculer `orphans = historyKeys - inputsKeys`
- [ ] 4.2 Filtrer les orphelins dans `renderSidebar()` par défaut
- [ ] 4.3 Ajouter un badge `<span id="orphan-count">N orphelins</span>` en bas de la sidebar, masqué si N=0
- [ ] 4.4 Ajouter un bouton `🗑 Nettoyer` à côté du badge qui ouvre la modal
- [ ] 4.5 Implémenter la modal : liste des N basenames, bouton `Confirmer`, bouton `Annuler`
- [ ] 4.6 Au confirm, appeler `POST /api/history/prune` avec `{basenames}` et rafraîchir la sidebar

## 5. Orphelins history.json — serveur

- [ ] 5.1 Créer la route `POST /api/history/prune` dans `pixel-lab/server/app.py`
- [ ] 5.2 Valider que chaque basename demandé est bien orphelin (source absent de `inputs/`), sinon `skipped`
- [ ] 5.3 Retirer les entrées de `history.json` (atomic write via fichier temporaire)
- [ ] 5.4 Pour chaque basename pruned, déplacer `outputs/<stem>/` vers `outputs/_trash/<stem>_<timestamp>/`
- [ ] 5.5 Renvoyer `{pruned: [...], skipped: [{name, reason}]}`

## 6. Tests visuels

- [ ] 6.1 Déplacer la souris sur un pixel connu, vérifier `x,y` + couleur correcte dans le HUD
- [ ] 6.2 Cliquer `Δ Diff` avec 2 images différentes, vérifier l'overlay rouge/vert et le décompte
- [ ] 6.3 Charger une image 4096×4096, cliquer Diff → warning de downscale affiché
- [ ] 6.4 Naviguer avec `←→` dans les iters, vérifier que `compareRight` suit
- [ ] 6.5 Appuyer `?`, vérifier cheat-sheet visible
- [ ] 6.6 Avec 4 orphelins dans history.json, vérifier badge + modal + appel purge + dossier `_trash` créé

## 7. Validation finale

- [ ] 7.1 `openspec validate add-dashboard-ux-polish` OK
- [ ] 7.2 Re-test régression des features existantes (live preview, builder, axes pixel, grille)
