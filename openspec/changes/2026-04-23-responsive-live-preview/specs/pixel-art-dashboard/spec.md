## ADDED Requirements

### Requirement: Le PipelineEditor SHALL déclencher une mise à jour de paramètre uniquement à la validation (blur / Enter / fin de drag)
Les inputs numériques (`<input type="number">`) du composant `PipelineEditor.vue` MUST utiliser l'événement `@change` (et non `@input`) pour appeler `pipeline.updateParam(...)`. Cela garantit qu'un drag répété sur les spinners natifs ou une saisie clavier multi-caractères ne génère **qu'une** mutation Pinia à la validation, donc **qu'un** preview à la clé. Les inputs booléens (`type="checkbox"`) conservent `@change` (comportement natif correct).

#### Scenario: Drag souris sur spinner → une seule requête preview
- **GIVEN** le live preview activé, une image active, un pipeline non vide
- **WHEN** l'utilisateur drag le spinner d'un paramètre numérique de la valeur 1 à la valeur 10 via la souris
- **THEN** exactement une requête `POST /api/preview` SHALL partir au relâchement de la souris, ET zéro requête SHALL partir pendant le drag

#### Scenario: Saisie clavier multi-caractères → une seule requête preview
- **GIVEN** les mêmes conditions
- **WHEN** l'utilisateur tape "12" dans un input numérique vide puis blur (Tab ou clic ailleurs)
- **THEN** exactement une requête `POST /api/preview` SHALL partir au blur, portant la valeur 12 (et non 1 puis 12)

### Requirement: Le store `usePreviewStore` SHALL publier uniquement la réponse de la dernière requête émise (latest-wins)
`usePreviewStore.fire` MUST maintenir un compteur monotone `requestSeq` incrémenté à chaque invocation. Avant de publier `lastUrl`/`lastMeta`/`status` à la résolution ou au rejet d'un `await api.postPreview(...)`, le handler MUST comparer le `seq` capturé en début d'appel au `requestSeq` courant : si une requête plus récente a été émise, la résolution (succès ou erreur) SHALL être ignorée silencieusement. Le `AbortController` existant est conservé pour couper le réseau, mais le latest-wins garantit la cohérence même si une réponse résout avant que l'abort ne soit honoré.

#### Scenario: Deux fires en succession rapide
- **GIVEN** `fire(A)` émis avec une réponse qui arrive à t=300 ms
- **WHEN** `fire(B)` est émis à t=50 ms avec une réponse qui arrive à t=200 ms
- **THEN** `lastUrl`/`lastMeta` SHALL refléter la réponse B, ET la résolution tardive de A à t=300 ms SHALL être ignorée (pas de régression vers A)

#### Scenario: Erreur tardive d'un fire obsolète
- **GIVEN** `fire(A)` échoue à t=500 ms (erreur réseau, non-AbortError)
- **WHEN** `fire(B)` a réussi à t=200 ms (pré-existant) et `status.value === 'ready'` à t=300 ms
- **THEN** l'erreur de A à t=500 ms SHALL être ignorée, `status.value` SHALL rester `'ready'`, ET `errorMsg.value` SHALL rester `null`

#### Scenario: Debounce coalesce un drag rapide
- **GIVEN** une constante `DEBOUNCE_MS = 250`
- **WHEN** `scheduleFire` est appelé 5 fois dans une fenêtre de 100 ms
- **THEN** une seule invocation de `fire` SHALL partir 250 ms après le dernier appel `scheduleFire`

### Requirement: Le ComparePane SHALL calculer la différence source/preview dans un Web Worker
Le composant `ComparePane.vue` MUST déléguer la boucle de calcul pixel-par-pixel du mode "Diff" à un Web Worker dédié (`src/workers/diff.worker.ts`), afin que le main thread reste disponible pour le rendu, la sidebar et les inputs pendant tout le calcul. Les buffers `ImageData` MUST être transférés au worker via le mécanisme `Transferable` pour éviter la copie au retour. Un indicateur UI discret SHALL être affiché tant que le calcul diff est en vol (état `diffInflight: true`).

#### Scenario: Diff sur image 2048×2048 ne fige pas l'UI
- **GIVEN** une source 2048×2048 et un preview 2048×2048 différents
- **WHEN** l'utilisateur bascule le mode de comparaison sur "Diff"
- **THEN** pendant la durée du calcul (mesurable en plusieurs dizaines de ms), la sidebar SHALL rester scrollable via la molette, les boutons de mode SHALL rester cliquables, ET aucun "Long Task" > 50 ms SHALL être attribué à `ComparePane.vue` dans le Performance profiler

#### Scenario: Indicateur diff inflight visible
- **GIVEN** un calcul diff en cours
- **WHEN** on inspecte le DOM du ComparePane
- **THEN** un élément textuel visible (ex. `calcul diff…`) SHALL signaler le travail en cours, ET SHALL disparaître à la fin du calcul

#### Scenario: Worker terminé au démontage du composant
- **GIVEN** un ComparePane monté avec un worker actif
- **WHEN** le composant est démonté (navigation, reload)
- **THEN** `worker.terminate()` SHALL être appelé dans `onBeforeUnmount` pour libérer le thread

### Requirement: Le ComparePane SHALL appliquer un latest-wins au chargement d'image source et preview
`loadIntoCanvas` et le `watch([sourceUrl, preview.lastUrl], ...)` du ComparePane MUST utiliser un compteur monotone `loadSeq` partagé par les deux chargements (src + prev). Un `onload` ou `onerror` d'une `Image` dont le `seq` capturé ne correspond plus au `loadSeq` courant SHALL être ignoré, évitant qu'une image chargée tardivement n'écrase un canvas plus récent.

#### Scenario: Switch rapide d'images dans la sidebar
- **GIVEN** une sidebar avec 5 images et une image A active (son `sourceUrl` est en cours de chargement via `<img>` JS)
- **WHEN** l'utilisateur clique successivement sur les images B, C, D, E dans un délai de 100 ms
- **THEN** le canvas source SHALL se stabiliser sur E, ET un `onload` tardif d'une des images A-D SHALL être ignoré (aucune assignation à `srcCanvas.value`)

#### Scenario: Switch pendant un diff en cours
- **GIVEN** un diff en calcul dans le worker avec `diffSeq = 7`
- **WHEN** l'utilisateur change d'image, déclenchant un nouveau `watch` qui incrémente `diffSeq` à 8 et repart un chargement
- **THEN** la réponse du worker portant `seq = 7` SHALL être ignorée à l'arrivée, ET seul le `seq = 8` SHALL potentiellement produire un nouveau diff

### Requirement: Le diff worker SHALL être un module ESM Vite-compatible
Le fichier `pixel-lab/frontend/src/workers/diff.worker.ts` MUST être un Web Worker module ESM, chargé via la syntaxe Vite `import DiffWorker from '@/workers/diff.worker?worker'`. Il MUST accepter un message typé `{ seq: number, width: number, height: number, srcBuf: ArrayBuffer, prevBuf: ArrayBuffer }` et répondre par un message typé `{ seq: number, width: number, height: number, diffBuf: ArrayBuffer }` avec `diffBuf` listé dans le second argument de `postMessage` (transfert). L'algorithme MUST reproduire fidèlement celui de l'implémentation pré-refactor : rouge proportionnel à `max(|Δr|, |Δg|, |Δb|)`, fond noir, alpha 255.

#### Scenario: Équivalence visuelle avec l'ancien diff
- **GIVEN** une paire (source, preview) fixe
- **WHEN** le nouveau code exécute `buildDiff()` via le worker
- **THEN** le canvas diff produit SHALL être pixel-identique (ou différer d'au plus 0 ou 1 niveau sur le canal rouge dû à l'arrondi) au canvas diff produit par l'implémentation pré-refactor pour la même entrée

#### Scenario: Transfert sans copie mémoire au retour
- **GIVEN** un message de retour du worker
- **WHEN** `postMessage(resp, [resp.diffBuf])` est appelé
- **THEN** le `ArrayBuffer` du worker SHALL être transféré au main thread (détaché côté worker), évitant une copie supplémentaire
