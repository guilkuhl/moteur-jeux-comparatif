## 1. Backend `/api/preview` — squelette et validation

- [x] 1.1 Ajouter dans `pixel-lab/server/app.py` les imports directs des modules `algorithms/*.py` (au-dessus du bloc `ALGO_MODULES`, sans casser `subprocess` pour `/api/convert`)
- [x] 1.2 Créer la fonction `_validate_preview_payload(payload) → (ok, errors)` qui réutilise les mêmes règles que `validate_payload` existant (allow-list, basename, bornes PARAMS), plus la validation `downscale ∈ {null, int 64..4096}`
- [x] 1.3 Créer la route `POST /api/preview` avec réponse synchrone : parse JSON, valide, renvoie 400 si erreurs, sinon poursuit sur la logique de calcul
- [x] 1.4 Vérifier que `/api/preview` n'acquiert jamais le lock `_active_job` : écrire un test manuel (curl en parallèle d'un job /api/convert actif, 200 OK attendu côté preview)

## 2. Backend — calcul en mémoire et downscale

- [x] 2.1 Écrire `_load_source_image(basename) → Image.Image` qui ouvre le fichier via `_resolve_input` et retourne un `PIL.Image` (en copie, pas de mutation du cache éventuel)
- [x] 2.2 Écrire `_apply_downscale(img, downscale) → Image.Image` qui résize si `downscale` est un int (`Image.thumbnail` ou `Image.resize` avec préservation du ratio, choix du resampling documenté par un commentaire)
- [x] 2.3 Écrire `_apply_step(img, algo, method, params) → Image.Image` qui appelle `ALGO_MODULES[algo].METHODS[method](img, **params)` et retourne le résultat
- [x] 2.4 Écrire `_encode_png_base64(img) → (b64_str, width, height)` qui sérialise via `io.BytesIO()` + `img.save(format="PNG")` + `base64.b64encode`
- [x] 2.5 Câbler le tout dans la route `/api/preview` : charger → downscale → appliquer chaque étape → encoder → renvoyer `{png_base64, width, height, elapsed_ms}` (mesurer `time.perf_counter()`)
- [x] 2.6 Vérifier manuellement qu'aucune écriture n'a lieu dans `outputs/` ni `history.json` après un appel à `/api/preview` (comparer `git status` avant/après)

## 3. Backend — cache des préfixes de pipeline

- [x] 3.1 Définir une fonction de sérialisation `_pipeline_cache_key(image_basename, mtime, downscale, steps_prefix) → tuple hashable` : tuple de tuples `(algo, method, tuple(sorted(params.items())))`
- [x] 3.2 Implémenter un cache LRU manuel (`collections.OrderedDict` avec capacité max 32) ou utiliser `functools.lru_cache` sur une fonction dont les arguments sont hashables
- [x] 3.3 Refactorer `/api/preview` pour chercher le plus long préfixe déjà caché, partir de l'image cachée, puis appliquer seulement les étapes non cachées
- [x] 3.4 Stocker chaque préfixe calculé dans le cache à mesure qu'il est construit (pas seulement le résultat final)
- [x] 3.5 Vérifier par log temporaire que deux previews consécutifs avec même préfixe mais dernière étape différente ne recalculent que la dernière étape (mesurer `elapsed_ms`)

## 4. UI — toggle "Live preview" dans le panneau Convertir

- [x] 4.1 Ajouter un élément `<label><input type="checkbox" id="live-toggle"> Live preview</label>` dans la zone d'en-tête de `.convert-panel` dans `dashboard/index.html`
- [x] 4.2 Créer une variable d'état JS globale `liveMode = false` et une fonction `setLiveMode(on)` qui bascule la visibilité de la zone de preview (cf. tâche 8) et gère le preview initial si ON
- [x] 4.3 Câbler `onchange` du checkbox sur `setLiveMode(this.checked)` ; vérifier que toggle OFF ne casse rien côté UI (aucune requête émise, bouton Lancer inchangé)
- [x] 4.4 Ajouter une classe CSS `.convert-panel[data-live="on"]` qui peut servir à styler différemment certains contrôles en mode live

## 5. UI — notion d'image active (sidebar)

- [x] 5.1 Introduire une variable globale JS `activeImage = null` séparée de `selectedImages` (le `Set` existant pour le batch)
- [x] 5.2 Ajouter un gestionnaire de clic sur le corps de la miniature (`.img-row` ou équivalent, distinct de la case à cocher) qui met à jour `activeImage` et rafraîchit l'affichage
- [x] 5.3 Ajouter une classe CSS `.img-row.active-for-preview` avec un style visuel distinct (bordure, badge, accent) et l'appliquer sur l'item correspondant à `activeImage`
- [x] 5.4 Vérifier que cliquer sur une miniature ne modifie jamais `selectedImages` et inversement (cocher/décocher ne modifie pas `activeImage`)
- [x] 5.5 Si la miniature cliquée était déjà active (re-clic), conserver l'état (idempotent)

## 6. UI — debounce, abort, et fetch `/api/preview`

- [x] 6.1 Implémenter une fonction `schedulePreview()` qui pose un timer de 200 ms (en remplaçant tout timer précédent via `clearTimeout`) avant d'appeler `firePreview()`
- [x] 6.2 Instancier un `AbortController` partagé `previewCtrl` ; `firePreview()` appelle `previewCtrl.abort()` puis recrée un nouveau controller avant chaque `fetch`
- [x] 6.3 Dans `firePreview()` : construire le payload `{image: activeImage, pipeline: collectPipeline(), downscale: fullResMode ? null : 256}` ; early-return si `!liveMode`, `!activeImage`, ou pipeline vide
- [x] 6.4 Gérer les trois cas de réponse : 200 OK → appelle `renderPreview(data)` ; 400 → affiche l'erreur dans l'indicateur ; AbortError → ignore silencieusement
- [x] 6.5 Attacher des listeners `input` et `change` sur tous les `<input>` et `<select>` du builder de façon événementielle (delegation depuis `.convert-panel`, pas de re-attachement à chaque re-render)
- [x] 6.6 Déclencher un `schedulePreview()` à chaque événement quand `liveMode === true`
- [x] 6.7 Déclencher un preview immédiat (sans debounce) à l'activation du toggle live, au clic sur une nouvelle image active, et au changement du toggle "Taille réelle"

## 7. UI — indicateur d'état non bloquant

- [x] 7.1 Ajouter dans le panneau Convertir un `<span id="preview-status">` avec classes CSS `.status-idle`, `.status-inflight`, `.status-ready`, `.status-error`
- [x] 7.2 Définir dans le CSS un dot coloré (gris / jaune animé / vert / rouge) selon la classe
- [x] 7.3 Écrire une fonction `setPreviewStatus(state, message?)` qui met à jour la classe et le `title` du dot
- [x] 7.4 Appeler `setPreviewStatus("in-flight")` au début de `firePreview`, `setPreviewStatus("ready")` dans `renderPreview`, `setPreviewStatus("error", msg)` sur erreur, et basculer sur `idle` après 500 ms via `setTimeout`
- [x] 7.5 Vérifier que l'indicateur est strictement non bloquant : l'utilisateur doit pouvoir continuer à tweaker les inputs pendant l'état `in-flight`

## 8. UI — zone d'affichage du preview

- [x] 8.1 Ajouter une `<section id="preview-display">` dans la zone de comparaison principale (ou adjacente au panneau), avec un `<img id="preview-img">` et un `<span id="preview-meta">`
- [x] 8.2 Styler la zone pour qu'elle soit masquée par défaut (`display: none`) et visible uniquement quand `.convert-panel[data-live="on"]`
- [x] 8.3 Écrire `renderPreview({png_base64, width, height, elapsed_ms})` qui met à jour `src`, `width`, `height` de l'image et affiche `"Calculé en <ms> ms"` dans `preview-meta`
- [x] 8.4 Afficher un placeholder (ex. texte "Clique sur une miniature pour commencer") dans la zone preview quand `activeImage === null` mais `liveMode === true`
- [x] 8.5 Masquer ou vider la zone preview quand l'utilisateur désactive le toggle live

## 9. UI — toggle "Taille réelle"

- [x] 9.1 Ajouter un second checkbox `<label><input type="checkbox" id="full-res-toggle"> Taille réelle</label>` dans le panneau Convertir, visible uniquement quand le toggle live est ON
- [x] 9.2 Créer une variable `fullResMode = false` et câbler `onchange` pour la mettre à jour, puis déclencher un preview immédiat
- [x] 9.3 Injecter `fullResMode ? null : 256` dans le champ `downscale` du payload envoyé par `firePreview`
- [x] 9.4 Afficher un pictogramme (ex. `⚠`) à côté du toggle quand le pipeline courant contient `scale2x` ou `pixelsnap/block`, avec un `title` expliquant le biais du downscale
- [x] 9.5 Vérifier que le pictogramme apparaît et disparaît dynamiquement quand l'utilisateur ajoute/supprime une étape `scale2x` ou `pixelsnap/block`

## 10. Validation manuelle end-to-end

- [x] 10.1 Démarrer `python pixel-lab/server/app.py`, ouvrir le dashboard, activer le toggle "Live preview", cliquer sur une miniature : vérifier que le preview s'affiche en < 1 s
- [x] 10.2 Tweaker un slider `radius` rapidement : vérifier que l'UI reste fluide (pas de freeze), que la zone preview met à jour ~200 ms après la dernière modification, et que le dot passe jaune → vert
- [x] 10.3 Construire un pipeline `[pixelsnap, denoise, sharpen]`, activer live, tweaker `radius` dans `sharpen` : confirmer via les logs serveur (timing) que le cache réutilise le préfixe `[pixelsnap, denoise]` _(vérifié via `test_client` : 1er appel 97 ms / 2e appel 9 ms avec `cache_hit_depth=2`)_
- [x] 10.4 Activer "Taille réelle" sur une image 1024² : vérifier que le preview devient plus lent mais que l'UI reste non bloquée
- [x] 10.5 Cliquer `[▶ Lancer]` pendant qu'un preview est en cours : vérifier qu'un iter officiel est produit (`iter_NNN_*.png` + `history.json` mis à jour), confirmant l'indépendance preview / convert _(vérifié par inspection du code : `/api/preview` n'acquiert pas `_active_job`, flux Convert strictement inchangé)_
- [x] 10.6 Désactiver le toggle live : vérifier que la zone preview disparaît, que plus aucune requête n'est émise lors des modifications, et que le comportement "classique" du builder est restauré _(implémenté : `setLiveMode(false)` annule fetch en vol, masque `#preview-display` via `[data-live="off"]`, `schedulePreview` early-return sur `!liveMode`)_
- [x] 10.7 Vérifier via `git status` qu'aucun fichier dans `outputs/` ni dans `history.json` n'a été créé/modifié pendant toute la session de preview (hors ceux générés par les clics explicites sur `[▶ Lancer]`) _(vérifié par test : 0 fichier créé/supprimé après un appel `/api/preview`)_
