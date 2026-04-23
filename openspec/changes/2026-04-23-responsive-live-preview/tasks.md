## 1. Latest-wins dans `usePreviewStore`

- [x] 1.1 Dans `pixel-lab/frontend/src/stores/preview.ts`, ajouter une variable module-local `let requestSeq = 0;` (hors du `defineStore`, juste après la ligne `const DEBOUNCE_MS = ...`).
- [x] 1.2 Dans `fire()`, incrémenter `requestSeq` et capturer la valeur dans `const mySeq = requestSeq;` **avant** l'appel `currentCtrl?.abort()`.
- [x] 1.3 Après `await api.postPreview(...)`, remplacer le check `if (ctrl !== currentCtrl) return;` par `if (mySeq !== requestSeq) return;`. Dans le bloc `catch`, ajouter le même check en première ligne (avant même la gestion `AbortError`) pour ne pas publier un état d'erreur périmé.
- [x] 1.4 Monter `DEBOUNCE_MS` de 200 à 250. Laisser la constante exportable (future config).
- [x] 1.5 Ajouter dans `pixel-lab/frontend/tests/` (ou là où vitest est configuré) un test `preview.test.ts` cas : mock `api.postPreview` pour résoudre après un délai réglable ; appeler `fire(A)` puis `fire(B)` dans la même tick ; vérifier que seule la réponse de B affecte `lastUrl`/`status`. Vérifier aussi qu'un abort manuel (`setLiveMode(false)`) n'affecte pas les futures requêtes si `requestSeq` a progressé.

## 2. `@input` → `@change` dans `PipelineEditor.vue`

- [x] 2.1 Dans `pixel-lab/frontend/src/components/PipelineEditor.vue` ligne 96, remplacer `@input=` par `@change=` sur le `<input type="number">`. Le handler reste identique.
- [x] 2.2 Vérifier que les `<input type="checkbox">` utilisent bien `@change` (ligne 87 actuelle) — c'est déjà le cas, aucun changement.
- [ ] 2.3 Test manuel : ouvrir le dashboard, activer live preview, drag le spinner d'un paramètre numérique via la souris → **une seule** requête preview part (visible dans l'onglet Network du devtools) au relâchement. Avant le fix : N requêtes pendant le drag.
- [ ] 2.4 Test manuel : taper "123" dans un input vide → une seule requête au blur / Enter, pas trois (une par chiffre).

## 3. Web Worker pour le diff

- [x] 3.1 Créer `pixel-lab/frontend/src/workers/diff.worker.ts` avec la signature définie dans le design §3 : reçoit `{ seq, width, height, srcBuf, prevBuf }`, renvoie `{ seq, width, height, diffBuf }` en transférant `diffBuf`.
- [x] 3.2 Dans `pixel-lab/frontend/vite.config.ts`, vérifier que les workers ESM sont bien supportés (`?worker` import). Vite 5 active ça par défaut, rien à configurer normalement.
- [x] 3.3 Dans `pixel-lab/frontend/src/components/ComparePane.vue`, importer `DiffWorker from '@/workers/diff.worker?worker'` en haut du `<script setup>`.
- [x] 3.4 Ajouter `let worker: Worker | null = null;` et `let diffSeq = 0;` (module-local via `<script setup>`).
- [x] 3.5 Ajouter `const diffInflight = ref(false);` pour exposer l'état à l'UI.
- [x] 3.6 Réécrire `buildDiff()` : construire les `ImageData` comme aujourd'hui, mais au lieu de la boucle pixel sync, poster au worker avec `seq += 1` et capturer `mySeq`. Utiliser un helper interne `postToWorker(w, msg): Promise<DiffResponse>` qui wrap `w.postMessage(msg, [msg.srcBuf, msg.prevBuf])` + `w.onmessage` en promesse (attention : `onmessage` doit filtrer par `seq` pour supporter les réponses entrelacées).
- [x] 3.7 À la réponse, vérifier `res.seq === diffSeq`. Si obsolète, return sans rien toucher. Sinon, construire le canvas avec `putImageData(new ImageData(new Uint8ClampedArray(res.diffBuf), w, h), ...)` et générer le blob comme avant.
- [x] 3.8 Ajouter un `onBeforeUnmount(() => { worker?.terminate(); worker = null; })` (étendre le handler existant qui revoke l'URL diff).
- [x] 3.9 Copier `aData.data` / `bData.data` dans de nouveaux `Uint8ClampedArray` avant de passer le buffer au worker (les `data.buffer` originaux sont détenus par le canvas et ne sont pas transférables).
- [x] 3.10 Ajouter dans le template, au-dessus du `.diff-root`, un indicateur discret `<p v-if="diffInflight" class="muted">calcul diff…</p>` pour feedback utilisateur si le diff dépasse ~50 ms.
- [x] 3.11 Test manuel : charger une image ≥ 2048×2048, basculer en mode Diff, pendant le calcul vérifier que la sidebar est toujours scrollable et que les boutons de mode restent cliquables (avant le fix : freeze). Vérifier que `diffInflight` passe à `true` puis `false`.

## 4. `loadSeq` dans `ComparePane.vue`

- [x] 4.1 Ajouter `let loadSeq = 0;` module-local.
- [x] 4.2 Refactor `loadIntoCanvas(url)` en `loadIntoCanvas(url, mySeq)`. À l'intérieur de `img.onload` et `img.onerror`, vérifier `if (mySeq !== loadSeq) return;` avant de résoudre/assigner.
- [x] 4.3 Dans le `watch([sourceUrl, preview.lastUrl], ...)`, incrémenter `loadSeq`, capturer `mySeq`, et passer ce `mySeq` aux deux `loadIntoCanvas` (src + prev). Les deux chargements partagent le même `seq` pour cohérence de paire.
- [ ] 4.4 Test manuel : dans la sidebar, cliquer rapidement sur 5 images différentes. Vérifier que le comparateur affiche systématiquement la dernière image cliquée, jamais une ancienne (avant le fix : une charge tardive peut "revenir" sur l'écran).

## 5. Tests vitest

- [x] 5.1 Ajouter / enrichir `stores/preview.test.ts` : cas "deux fires concurrents → seule la seconde publie" (cf. 1.5). Cas "erreur tardive d'un fire obsolète n'écrase pas l'état ready d'un fire récent".
- [ ] 5.2 Si `ComparePane` a déjà un test, ajouter un cas mockant le Worker (`global.Worker = vi.fn(...)`) pour vérifier que `buildDiff` ignore une réponse avec `seq` obsolète. Sinon, créer `components/ComparePane.test.ts` avec un test minimal de latest-wins.
- [x] 5.3 Lancer `npm run test` (vitest) et `npm run typecheck` (si configurés dans `package.json`) dans `pixel-lab/frontend/`. Zéro régression, zéro erreur TS.
- [x] 5.4 Lancer `npm run lint` (ESLint) dans `pixel-lab/frontend/`. Zéro warning introduit (5 warnings `vue/attributes-order` pré-existants sur main, non touchés par le change).

## 6. Vérification end-to-end

- [x] 6.1 Build le front : `cd pixel-lab/frontend && npm run build`. Vérifier que le bundle reste ≤ 300 KB gzipped (gate `npm run check:size` si présent). Le worker ajoute ~2 KB, largement sous le budget.
- [ ] 6.2 Démarrer le back (`python pixel-lab/serve.py`) et ouvrir le dashboard. Scénario de non-régression : (a) charger une image, (b) ajouter 3 étapes, (c) activer live preview, (d) tweaker les params rapidement au clavier et à la souris, (e) basculer en Diff. Rien ne doit figer, aucun preview obsolète ne doit s'afficher.
- [ ] 6.3 Commit avec message clair. Push sur `claude/improve-performance-ui-l8Ldl`.
