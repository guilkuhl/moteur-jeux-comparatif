## Why

Le dashboard `pixel-lab/dashboard/index.html` est un **fichier monolithique de 3 983 lignes** contenant HTML + CSS + ~68 fonctions JavaScript inline. Cinq limites concrètes :

1. **Navigabilité zéro** : impossible de localiser rapidement une fonctionnalité sans `grep`. Les panneaux (sidebar, convert, compare, preview live, bg-detect, spritesheet, autotile) sont entrelacés dans un seul fichier.
2. **Pas de réactivité déclarative** : les mises à jour DOM sont impératives (`document.getElementById(...)...`), les caches d'état sont des globaux (`activeImage`, `compareRight`, `liveMode`, `lastPreviewUrl`, `preserveBg`, `bgOverlayVisible`, …). Chaque nouveau feature rend le state management plus fragile.
3. **Pas de typage ni d'autocomplétion** : le contrat avec le back est implicite, une faute de frappe sur `data.png_base64` ne saute qu'à l'exécution.
4. **Pas de build ni de tests** : aucun bundling, aucun linter, aucun test unitaire ou e2e. Le dashboard est testé manuellement.
5. **Duplication logique** : la gestion d'URL blob (preview), la gestion d'erreurs API, la construction des payloads de pipeline sont répétées à plusieurs endroits.

Décisions utilisateur retenues :
- **Vue 3 + Vite + Pinia + TypeScript**
- **SSE conservé** (EventSource côté Vue, pas de WebSocket)
- **Stack CI + e2e** portée par un change séparé (`add-ci-e2e-tests`)

Vue 3 + TS apporte : réactivité fine via Composition API, store centralisé (Pinia) pour `activeImage` / `compareRight` / `liveMode` / `lastPreviewUrl`, typage strict des réponses API (interfaces TS), build Vite avec HMR, et écosystème de tests (Vitest + Vue Test Utils) trivial à brancher.

## What Changes

- **NEW** `pixel-lab/frontend/` : nouveau sous-projet Vite + Vue 3 + TypeScript.
  - `package.json`, `vite.config.ts`, `tsconfig.json`, `.eslintrc`, `.prettierrc`
  - `src/main.ts`, `src/App.vue`
  - `src/api/` : client HTTP typé (`convertApi.ts`, `previewApi.ts`, `bgmaskApi.ts`, `inputsApi.ts`, `jobsStream.ts`). Une interface TS par payload/réponse.
  - `src/stores/` (Pinia) : `useImagesStore`, `usePipelineStore`, `usePreviewStore`, `useJobStore`, `useBgDetectStore`, `useCompareStore`.
  - `src/components/` : composants réutilisables — `Sidebar/`, `ConvertPanel/`, `ComparePane/`, `LivePreviewToggle/`, `PipelineEditor/`, `BgDetectPanel/`, `SpritesheetTools/`, `AutotilePanel/`.
  - `src/views/` : `DashboardView.vue` (layout principal).
  - `src/composables/` : `usePreviewLive()`, `useSSESubscription()`, `useBlobUrl()`, `useKeyboard()`.
  - `src/utils/` : `validatePipeline.ts`, `formatElapsed.ts`.
  - Index HTML minimal : `index.html` qui charge `main.ts` via Vite.
- **NEW** Build : `npm run dev` (Vite HMR sur port 5173 avec proxy vers le back `http://127.0.0.1:5500`), `npm run build` (sortie `dist/` statique), `npm run type-check`, `npm run lint`, `npm run test` (Vitest).
- **MODIFIED** back : en dev le front est servi par Vite (port 5173) et appelle le back via CORS déjà configuré. En prod, le build `dist/` est copié dans `pixel-lab/frontend-dist/` et servi comme statique par FastAPI (mount statique). L'ancien `dashboard/index.html` est supprimé en fin de migration.
- **MODIFIED** `pixel-lab/serve.py` : ajoute en prod un mount statique `StaticFiles(directory="frontend-dist")` à la racine `/` (fallback SPA renvoyant `index.html` pour les chemins non-API). En dev, pas de mount — on démarre `vite dev` à côté dans un second terminal (documenté).
- **MODIFIED** README : section « Lancement » réécrite — dev (2 terminaux : back + vite), prod (1 terminal, serveur unique).
- **REMOVED** `pixel-lab/dashboard/index.html` : supprimé au cutover. L'ancien flux « ouvrir le fichier directement en `file://` » n'est plus supporté (remplacé par `npm run dev` en dev ou serveur unique en prod).
- **PAS DE CHANGEMENT** : les routes API consommées (`/api/convert`, `/api/preview`, `/api/bgmask`, `/api/inputs`, SSE `/api/jobs/<id>/stream`) sont inchangées.

## Capabilities

### New Capabilities
_Aucune nouvelle capability._ Le dashboard Vue remplace le dashboard HTML monolithique sous la capability `pixel-art-dashboard`.

### Modified Capabilities
- `pixel-art-dashboard` : réécriture en SPA Vue 3 + TS, state centralisé via Pinia, build Vite, typage strict des appels API. Les fonctionnalités (panneaux, toggles, live preview, compare, bg-detect, spritesheet, autotile) sont préservées fonctionnellement.

## Impact

- **Code touché**
  - Nouveau `pixel-lab/frontend/` (~2 500 lignes TS/Vue réparties en ≥ 25 composants/modules, chaque fichier ≤ 250 lignes).
  - Suppression `pixel-lab/dashboard/index.html` (-3 983 lignes).
  - Adaptation `pixel-lab/serve.py` : mount statique prod (~15 lignes).
  - Nouveau `pixel-lab/frontend/package.json`, `vite.config.ts`, `tsconfig.json`.
  - Mise à jour `pixel-lab/README.md` : section lancement dev/prod.
- **APIs modifiées** : 0 rupture côté back (le front consomme les routes existantes). Les types TS reflètent les schémas actuels.
- **Dépendances** :
  - Ajouts npm (dev + runtime) : `vue@^3.4`, `pinia@^2.1`, `vue-router@^4.3` (si navigation multi-vues), `vite@^5`, `@vitejs/plugin-vue`, `typescript@^5.3`, `vitest@^1.4`, `@vue/test-utils@^2.4`, `eslint`, `prettier`.
  - Aucune dépendance Python ajoutée (le back sert juste le dossier statique).
- **Sécurité** :
  - CSP stricte possible (pas de `eval`, pas de `unsafe-inline` — Vite produit du code signé).
  - CORS déjà limité à `127.0.0.1` par le change `migrate-back-fastapi`. En dev, `vite.config.ts` proxy `/api` vers le back, pas de CORS à gérer.
  - Validation côté front (types TS + validateurs explicites) + validation Pydantic côté back = deux niveaux.
- **Performance** :
  - Bundle Vite minifié, tree-shaking actif. Estimation cible : < 250 KB gzipped pour le bundle principal (comparable aux 167 KB actuels de l'HTML).
  - HMR en dev : rechargement < 100 ms après un `save`.
  - Réactivité fine (vs rebuild DOM manuel) : moins de reflows sur les écrans lourds (compare-pane avec divider, sidebar avec scroll virtuel si > 100 images).
- **Migration de données** : aucune. Le localStorage existant (`dashLeftOpen`, préférences utilisateur) MUST être lu au boot par les stores Pinia pour préserver les préférences inter-sessions.
- **Compatibilité descendante** :
  - Le flux `file://` (ouvrir `dashboard/index.html` directement) n'est plus supporté — documenté en BREAKING CHANGE dans le README.
  - Les utilisateurs existants doivent désormais lancer `python pixel-lab/serve.py` (prod) ou `npm run dev` (dev).
- **Rollback** : `git revert` restaure l'ancien `dashboard/index.html`. Le back reste identique, donc pas de désync.
