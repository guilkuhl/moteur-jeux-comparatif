## 1. Scaffolding projet Vite/Vue 3/TS

- [ ] 1.1 `npm create vite@latest pixel-lab/frontend -- --template vue-ts` (accepter les defaults), committer `package.json`, `package-lock.json`, `tsconfig.json`, `vite.config.ts`, `index.html`, `src/`
- [ ] 1.2 Supprimer les scaffolding assets (`HelloWorld.vue`, logo, CSS template) — garder `App.vue` vide et `main.ts`
- [ ] 1.3 Configurer `tsconfig.json` strict : `"strict": true`, `"noUncheckedIndexedAccess": true`, `"exactOptionalPropertyTypes": true`, `"moduleResolution": "bundler"`
- [ ] 1.4 Ajouter ESLint + Prettier : `npm i -D eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin eslint-plugin-vue prettier eslint-config-prettier`. Créer `.eslintrc.cjs`, `.prettierrc`, `.editorconfig`
- [ ] 1.5 Ajouter `pinia`, `@vueuse/core` : `npm i pinia @vueuse/core`
- [ ] 1.6 Ajouter `vitest`, `@vue/test-utils`, `happy-dom` : `npm i -D vitest @vue/test-utils happy-dom`
- [ ] 1.7 Configurer `vite.config.ts` : proxy `/api → http://127.0.0.1:5500`, alias `@ → src/`, build output par défaut (`dist/`)
- [ ] 1.8 Scripts `package.json` : `dev`, `build`, `preview`, `type-check` (`vue-tsc --noEmit`), `lint`, `lint:fix`, `format`, `test`
- [ ] 1.9 Créer `.vscode/extensions.json` recommandant Volar, ESLint, Prettier
- [ ] 1.10 Smoke test : `npm run dev` → navigateur sur `:5173` → page vide OK, `npm run build` → `dist/` généré

## 2. Types TS des contrats API

- [ ] 2.1 `src/types/pipeline.ts` : `export type Algo = "sharpen" | "scale2x" | "denoise" | "pixelsnap"`, `PipelineStep { algo: Algo; method: string; params: Record<string, number | boolean>; }`
- [ ] 2.2 `src/types/api.ts` : `ConvertRequest`, `ConvertResponse`, `PreviewRequest`, `PreviewResult` (avec `blob`, `width`, `height`, `elapsedMs`, `cacheHitDepth`), `BgmaskQuery`, `AlgoParamMeta`, `AlgosCatalog`, `InputFile`, `HistoryEntry`
- [ ] 2.3 `src/types/sse.ts` : union discriminée des événements SSE (`StepStartEvent`, `StepDoneEvent`, `StepErrorEvent`, `WarningEvent`, `ImageDoneEvent`, `DoneEvent`) + type guard `isStepStart(evt): evt is StepStartEvent`
- [ ] 2.4 `src/types/api-errors.ts` : `PydanticErrorItem { loc: (string|number)[]; msg: string; type: string; }`, `ApiErrorResponse { errors?: PydanticErrorItem[]; error?: string; message?: string; }`

## 3. Client API

- [ ] 3.1 `src/api/http.ts` : helper `fetchJson<T>(url, init): Promise<T>` avec `parseApiError` qui convertit `PydanticErrorItem[]` en string humain
- [ ] 3.2 `src/api/convertApi.ts` : `postConvert(req): Promise<{job_id:string}>`
- [ ] 3.3 `src/api/previewApi.ts` : `postPreview(req, signal): Promise<PreviewResult>` avec lecture `blob()` + headers `X-*`
- [ ] 3.4 `src/api/bgmaskApi.ts` : `getBgmask(params): Promise<{blob: Blob, color: string | null}>`
- [ ] 3.5 `src/api/inputsApi.ts` : `listInputs()`, `uploadInput(file)`, `deleteInput(name)`
- [ ] 3.6 `src/api/outputsApi.ts` : `deleteOutput(stem, filename)`, `deleteAllOutputs(stem)`
- [ ] 3.7 `src/api/algosApi.ts` : `getAlgos(): Promise<AlgosCatalog>`
- [ ] 3.8 `src/api/jobsStream.ts` : `openJobStream(jobId, onEvent, onError): () => void` (retourne fonction de cleanup)
- [ ] 3.9 Tests `src/api/*.test.ts` : mocks de `fetch` via `vi.fn()`, ≥ 2 cas par endpoint (happy + erreur)

## 4. Stores Pinia

- [ ] 4.1 `src/stores/images.ts` : `useImagesStore` — state `files`, `activeImage`, `history`; actions `refresh()`, `select(name)`, `upload(file)`, `delete(name)`
- [ ] 4.2 `src/stores/pipeline.ts` : `usePipelineStore` — state `steps[]`, getters `isValid`, `asPayload`; actions `addStep`, `removeStep(i)`, `updateParam(i, key, val)`, `reorder(from, to)`, `reset()`
- [ ] 4.3 `src/stores/preview.ts` : `usePreviewStore` — state `liveMode`, `fullResMode`, `lastBlobUrl`, `previewStatus`, `elapsedMs`, `cacheHitDepth`; actions `setLive(bool)` (revoke blob), `firePreview(debounce)`, `abort()`, `cleanup()`
- [ ] 4.4 `src/stores/job.ts` : `useJobStore` — state `activeJobId`, `events[]`, `currentStep`; actions `startJob(payload)`, `handleSSEEvent(evt)`, `reset()`
- [ ] 4.5 `src/stores/bgDetect.ts` : `useBgDetectStore` — state `preserveBg`, `overlayVisible`, `tolerance`, `feather`, `detectedColor`; actions `toggleOverlay()`, `detect()`
- [ ] 4.6 `src/stores/compare.ts` : `useCompareStore` — state `compareLeft`, `compareRight`, `zoom`, `dividerX`; actions `setRight(item)`, `setZoom(n)`, `swap()`
- [ ] 4.7 Persistence `localStorage` : clés réutilisées des versions HTML (`dashLeftOpen`, etc.). Tests de sérialisation/lecture
- [ ] 4.8 Tests `src/stores/*.test.ts` : ≥ 2 tests critiques par store (actions + invariants)

## 5. Composants atomiques et composables

- [ ] 5.1 `src/composables/useBlobUrl.ts` : hook qui crée + révoque automatiquement au démontage (`onUnmounted`) → utilisé par preview et bgmask
- [ ] 5.2 `src/composables/useSSESubscription.ts` : wrapper `EventSource` avec cleanup auto, dispatch vers `useJobStore`
- [ ] 5.3 `src/composables/usePreviewLive.ts` : orchestre debounce, AbortController, appel API, dispatch store
- [ ] 5.4 `src/composables/useKeyboardShortcuts.ts` : enregistre les raccourcis globaux
- [ ] 5.5 `src/components/atoms/StatusDot.vue` : pill idle/inflight/ready/error avec `props.status`
- [ ] 5.6 `src/components/atoms/ErrorBanner.vue` : bannière fermable
- [ ] 5.7 `src/components/atoms/IconButton.vue`, `Toggle.vue`, `NumberField.vue` avec validation
- [ ] 5.8 Tests composants atomiques : `mount(X)` + assertions props/events via Vue Test Utils

## 6. Panneaux principaux (1 commit par panneau)

- [ ] 6.1 `src/components/sidebar/Sidebar.vue` + `ImageList.vue` : liste `files` avec indicateur `processed`, click pour sélection
- [ ] 6.2 `src/components/convert/ConvertPanel.vue` : composition — `<PipelineEditor>` + boutons Lancer/Live preview/Taille réelle
- [ ] 6.3 `src/components/convert/PipelineEditor.vue` : ajout/suppression/reorder d'étapes, `<StepForm>` par étape avec champs dynamiques selon `AlgoParamMeta`
- [ ] 6.4 `src/components/preview/LivePreviewToggle.vue` : checkbox + warning size-sensitive + `usePreviewLive()`
- [ ] 6.5 `src/components/compare/ComparePane.vue` + `Divider.vue` : slider divider, zoom, labels, timings
- [ ] 6.6 `src/components/bgdetect/BgDetectPanel.vue` : bouton détecter + toggle preserve + tolerance field + overlay
- [ ] 6.7 `src/components/overlays/PixelGridOverlay.vue` + `PixelAxesOverlay.vue` + `GridCustomizer.vue`
- [ ] 6.8 `src/components/spritesheet/SpritesheetPanel.vue` : slicing, cleanup, export, contraintes (lazy-loaded via `defineAsyncComponent`)
- [ ] 6.9 `src/components/autotile/AutotilePanel.vue` (lazy-loaded)

## 7. Layout et intégration

- [ ] 7.1 `src/views/DashboardView.vue` : layout 3 colonnes (sidebar / compare / convert) avec rétractation
- [ ] 7.2 `src/App.vue` : header minimal + `<DashboardView>`, handling d'erreurs globales
- [ ] 7.3 `src/main.ts` : `createApp(App).use(createPinia()).mount('#app')`, boot `useImagesStore.refresh()`
- [ ] 7.4 CSS global minimal (`src/assets/styles.css`) : variables `--muted`, `--green`, etc. reprises du dashboard actuel
- [ ] 7.5 Smoke test manuel : tout le flux (upload → preview → convert → compare) en `npm run dev`

## 8. Entrée serveur prod (mount statique)

- [ ] 8.1 Modifier `pixel-lab/serve.py` (ou `server_fastapi/main.py`) : en prod, `app.mount("/", StaticFiles(directory=ROOT / "frontend-dist", html=True), name="static")` avec fallback SPA vers `index.html` pour tout chemin non `/api/*`
- [ ] 8.2 Pour que `frontend-dist/` soit peuplé : `cd pixel-lab/frontend && npm run build && rm -rf ../frontend-dist && mv dist ../frontend-dist` — documenté dans `README.md` et dans un script `pixel-lab/frontend/build-and-install.sh`
- [ ] 8.3 Ajouter `pixel-lab/frontend-dist/` au `.gitignore` (artefact de build, pas versionné)
- [ ] 8.4 Vérifier que `PIXEL_LAB_PROD=1 python pixel-lab/serve.py` sert le dashboard Vue à `http://127.0.0.1:5500/` et les routes API à `/api/*`

## 9. Cutover

- [ ] 9.1 Supprimer `pixel-lab/dashboard/index.html`
- [ ] 9.2 Supprimer le dossier `pixel-lab/dashboard/` s'il est vide
- [ ] 9.3 Mettre à jour `pixel-lab/README.md` :
  - Section Dev : « 2 terminaux — `python pixel-lab/serve.py` + `cd pixel-lab/frontend && npm run dev` »
  - Section Prod : « Build `npm run build` puis serveur unique `python pixel-lab/serve.py` »
  - Section Breaking changes : plus de support `file://`, build Node requis
- [ ] 9.4 Vérifier `git grep -l "dashboard/index.html"` → 0 match (sauf archives)

## 10. Validation de non-régression fonctionnelle

- [ ] 10.1 Lister les features de l'HTML d'origine : sidebar, upload, convert, preview live, compare, bg-detect, pixel grid, pixel axes, grid customization, spritesheet (slicing/export/cleanup/constraints), autotile, history deletion, zip export. Pour chaque feature : test manuel écran par écran
- [ ] 10.2 Comparer côte-à-côte avec l'ancien dashboard (ouvert depuis `git stash` temporaire ou checkout du parent du merge) : même UX visuelle (tolérance : styles légèrement modernisés OK, comportements identiques requis)
- [ ] 10.3 Tester avec une base de 20+ images pour s'assurer que la sidebar performe (scroll virtuel non nécessaire mais pas de freeze)
- [ ] 10.4 Vérifier préférences `localStorage` préservées : `dashLeftOpen` est lue au boot, toggle fonctionne
- [ ] 10.5 `npm run type-check && npm run lint && npm run test` → 0 erreur
- [ ] 10.6 Bundle size check : `dist/` main bundle ≤ 250 KB gzipped (rapport Vite à consigner dans le PR)
