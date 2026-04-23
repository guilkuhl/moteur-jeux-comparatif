## Why

Le live preview et la comparaison dans la SPA Vue présentent trois symptômes visibles par l'utilisateur :

1. **Slider figé pendant le calcul.** `PipelineEditor.vue:96` déclenche `pipeline.updateParam(...)` sur **chaque** `@input` du `<input type="number">`. Ça fait ~5–10 mutations Pinia par seconde pendant un drag, chacune coalescée par le debounce 200 ms de `preview.scheduleFire()` (`stores/preview.ts:8`). Avec un pipeline lourd (5 étapes, GPU off), un preview peut prendre 400–800 ms ; pendant ce temps, un nouveau drag déclenche un nouveau debounce, puis une nouvelle requête annulée via `AbortController`. Problème : l'affichage reflète parfois un **preview obsolète** si la réponse arrive après l'abort du nouveau (race sur l'ordre de résolution des `fetch`).
2. **Gel visible sur le diff.** `ComparePane.vue:66-98` calcule la différence pixel-par-pixel sur le main thread dans une boucle JS non découpée. Sur une image 1024×1024, c'est 4 M itérations et ~150–300 ms de freeze total de l'UI : la sidebar ne répond plus, le slider ne bouge plus. Sur 2048×2048, le gel dépasse la seconde.
3. **Canvas source écrasé par un résultat périmé.** `ComparePane.vue:41-56` charge une `Image` via `.src = url` sans tracker quelle image est "la dernière demandée". Si l'utilisateur switche d'image rapidement dans la sidebar, la `onload` d'une image précédente peut arriver après le chargement de la nouvelle et écraser `srcCanvas`, rendant le comparateur incohérent.

Les trois causes sont du pur main-thread-blocking / race condition. Le fix est front-only, sans toucher au backend.

## What Changes

- **MODIFIED** `pixel-lab/frontend/src/stores/preview.ts` : ajouter un compteur `requestSeq` incrémenté à chaque `fire()`. La résolution `await api.postPreview(...)` SHALL vérifier `if (seq !== requestSeq) return;` **avant** de `revokeCurrent()` et publier `lastUrl`. Le debounce passe de 200 ms à 250 ms pour mieux coalescer les drags rapides, configurable via constante.
- **MODIFIED** `pixel-lab/frontend/src/components/PipelineEditor.vue` : pour les inputs `type="number"`, basculer de `@input` à `@change` pour les mises à jour "fermes" (fin de drag / Enter / blur), et conserver un affichage local `v-model` intermédiaire qui ne pousse pas dans le store pendant le drag. Les inputs `type="checkbox"` continuent sur `@change` (déjà correct). Résultat : un drag de slider numérique ne pousse qu'**une** mise à jour dans Pinia à la fin, au lieu de N intermédiaires.
- **NEW** `pixel-lab/frontend/src/workers/diff.worker.ts` : Web Worker module qui reçoit `{ srcImageData, prevImageData, width, height }` via `postMessage` et renvoie `ImageData` résultat. La boucle pixel-par-pixel y est identique à l'actuelle, mais hors main thread. Transfert via `Transferable` (`ArrayBuffer.transfer`) pour éviter la copie.
- **MODIFIED** `pixel-lab/frontend/src/components/ComparePane.vue` :
  - Remplacer la boucle sync dans `buildDiff()` par un appel au worker avec un compteur de génération (`diffSeq`) : la réponse du worker SHALL être ignorée si `seq !== currentDiffSeq`.
  - Ajouter un `loadSeq` pour `loadIntoCanvas` : chaque appel incrémente et capture un id ; la résolution SHALL refuser d'assigner `srcCanvas`/`prevCanvas` si un nouvel appel a été lancé entre-temps.
  - Pendant que le diff calcule (>50 ms), afficher un léger indicateur `calcul diff…` pour feedback utilisateur.
- **NEW** `pixel-lab/frontend/src/composables/useLatestWins.ts` (optionnel, petit utilitaire générique) : factorise le pattern "seq id" utilisé par diff et loadIntoCanvas. À ne créer que si utilisé ≥ 2 fois.
- **MODIFIED** `pixel-lab/frontend/src/components/ConvertPanel.vue` : la `watch` sur `pipeline.steps` (ligne 55, `deep: true`) reste, mais avec le changement de `@input` → `@change` dans l'éditeur, elle ne se déclenche plus pendant le drag — seulement à la validation. Aucun changement de code requis ici, c'est une conséquence du point précédent.
- **PAS DE CHANGEMENT BACKEND.** Toutes les modifs sont dans `pixel-lab/frontend/src/`. Vite 5 supporte nativement les Web Workers via `new Worker(new URL('./diff.worker.ts', import.meta.url), { type: 'module' })`.

## Capabilities

### New Capabilities
_Aucune nouvelle capability._

### Modified Capabilities
- `pixel-art-dashboard` : ajout d'exigences sur la réactivité du PipelineEditor (pas de flood de mutations Pinia pendant un drag), la non-régression de l'affichage de preview (latest-wins via `requestSeq`), et le chargement d'images dans ComparePane (latest-wins via `loadSeq`).
- `pixel-art-comparison` _(n'existe pas pour l'UI diff — la spec porte sur le CLI. On ajoute donc la partie diff-UI sous `pixel-art-dashboard`)_.

## Impact

- **Code touché**
  - `pixel-lab/frontend/src/stores/preview.ts` : ~10 lignes (requestSeq + check).
  - `pixel-lab/frontend/src/components/PipelineEditor.vue` : ~15 lignes (buffer local + `@change`).
  - `pixel-lab/frontend/src/workers/diff.worker.ts` : nouveau, ~30 lignes.
  - `pixel-lab/frontend/src/components/ComparePane.vue` : ~40 lignes (appel worker + loadSeq + indicateur).
  - Tests vitest à ajouter : `stores/preview.test.ts` (couvre déjà partiellement — ajouter le cas "réponse tardive après abort"), `components/ComparePane.test.ts` ou test d'intégration minimal du worker.
- **APIs modifiées** : aucune.
- **Dépendances** : aucune nouvelle (Vite gère les workers nativement, TypeScript aussi).
- **Sécurité** : surface inchangée (le worker tourne dans la même origin).
- **Performance** :
  - Slider drag : 0 requête preview au lieu de N pendant le drag, 1 requête au release.
  - Diff : 0 ms de main-thread bloqué au lieu de 150–300 ms (freeze perçu éliminé).
  - Preview affiché : jamais d'image obsolète (ordre strict via `requestSeq`).
- **Migration de données** : aucune.
- **Compatibilité descendante** : 100 %. Aucun contrat externe.
- **Rollback** : `git revert` simple. Le worker est chargé dynamiquement ; s'il échoue à charger (cas improbable), fallback possible sur l'ancien code — à ajouter optionnellement.
