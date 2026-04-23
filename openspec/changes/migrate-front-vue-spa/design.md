## Context

Le dashboard actuel est un prototype sophistiqué mais ingérable à long terme : 3 983 lignes dans un seul fichier, 68 fonctions globales, gestion d'état par variables top-level (`activeImage`, `compareRight`, `liveMode`, `lastPreviewUrl`, `bgOverlayVisible`, `preserveBg`, `fullResMode`, …), aucun typage, aucun test.

À chaque ajout de fonctionnalité (live preview, bg-detect, spritesheet, autotile, grid overlay), la surface croît et la probabilité de régression aussi. Le change `pixel-lab-backend-perf` a déjà nécessité de toucher ~30 lignes JS éparpillées en 5 endroits juste pour remplacer un parse JSON base64 par un blob URL.

Vue 3 + Pinia + TS est un choix standard pour ce type de SPA outillée : réactivité déclarative, state store testable, typage des contrats API, tooling mature (Vite, Vitest, ESLint, Volar).

## Goals / Non-Goals

**Goals:**
- Remplacer `dashboard/index.html` par une SPA Vue 3 avec state Pinia et types TS.
- Découper par composants cohérents (1 panneau UI = 1 composant).
- Typer strictement les réponses API (interfaces TS alignées sur les schémas Pydantic du back).
- Build Vite reproductible, dev server avec HMR, bundle minifié pour prod.
- Préserver 100 % des features existantes : sidebar, live preview, compare pane, bg-detect, spritesheet tools, autotile, pixel grid overlay, pixel axes overlay, grid visual customization.
- Centraliser la logique SSE (subscription, déconnexion, reconnexion) dans un composable réutilisable.
- Ouvrir la porte à Vitest (tests unitaires composants) et Playwright (tests e2e) sans rework — mais leur setup est dans `add-ci-e2e-tests`.

**Non-Goals:**
- Pas de SSR ni Nuxt : inutile en localhost.
- Pas de PWA / offline : le back est toujours accessible en localhost.
- Pas de thème multiple (dark/light) ou i18n : hors scope V1.
- Pas de refactor du back — ce change consomme les routes existantes telles quelles.
- Pas de monorepo npm : `pixel-lab/frontend/` est un projet npm indépendant, pas de workspace yarn/pnpm.

## Decisions

### D1. Vue 3 Composition API + `<script setup>` + TS

**Choix :** 100 % Composition API, 100 % `<script setup lang="ts">`. Aucun composant Options API.

**Pourquoi :**
- API moderne Vue 3, meilleur typage TS.
- Logique extractable en composables (ex. `usePreviewLive()` réutilisable).
- Moins de verbosité qu'Options API, `<script setup>` élimine le boilerplate de `defineComponent`.

**Alternatives :** Options API rejetée (verbose, moins typée, incompatible avec l'extraction en composables).

### D2. State management : Pinia, store par domaine

**Choix :** stores Pinia séparés :
- `useImagesStore` : liste `inputs/`, `activeImage`, cache de `history.json`, actions CRUD.
- `usePipelineStore` : étapes du pipeline courant, validation locale, sérialisation JSON pour `POST /api/convert` et `POST /api/preview`.
- `usePreviewStore` : `liveMode`, `fullResMode`, `lastPreviewUrl` (avec revoke auto), `previewStatus`, throttling/debounce.
- `useJobStore` : job actif, événements SSE, état compare, erreurs.
- `useBgDetectStore` : `preserveBg`, overlay visible, `tolerance`, `feather`.
- `useCompareStore` : `compareLeft`, `compareRight`, divider position, zoom.

**Pourquoi :**
- Un seul endroit par domaine → facile à tracer.
- Pinia < 2 KB gzipped, réactivité Vue native.
- Testable sans composant (fonctions pures sur le store).

**Trade-off :** la communication inter-store (ex. `usePreviewStore` a besoin de `activeImage` depuis `useImagesStore`) passe par composition dans les composables, pas par références directes entre stores — évite les cycles.

### D3. Typage des contrats API

**Choix V1 :** **interfaces TS manuelles** alignées à la main sur les schémas Pydantic du back.
```ts
export interface PipelineStep { algo: "sharpen" | "scale2x" | "denoise" | "pixelsnap"; method: string; params: Record<string, number | boolean>; }
export interface ConvertRequest { images: string[]; pipeline: PipelineStep[]; }
export interface PreviewResponseHeaders { xWidth: number; xHeight: number; xElapsedMs: number; xCacheHitDepth: number; }
```

**Pourquoi :**
- L'utilisateur n'a pas retenu l'option « OpenAPI contract partagé ». On évite la complexité de `openapi-typescript` V1.
- Facile à mettre à jour à la main vu la petite surface (~10 types).
- Possible d'ajouter `openapi-typescript` plus tard sans rupture (les interfaces générées remplaceront celles écrites à la main).

**Alternatives :**
- `openapi-typescript` : génère les types depuis `openapi.json`. Hors scope V1, à revisiter.
- `zod` pour validation runtime côté front : overkill vu que Pydantic valide déjà côté serveur.

### D4. Client HTTP : `fetch` natif + wrappers typés

**Choix :** wrappers fins dans `src/api/*.ts` qui appellent `fetch` et renvoient des promises typées. Pas d'axios, pas de vue-query en V1.

```ts
// api/previewApi.ts
export async function postPreview(req: PreviewRequest, signal: AbortSignal): Promise<PreviewResult> {
  const res = await fetch("/api/preview", { method: "POST", signal, headers: {"Content-Type":"application/json"}, body: JSON.stringify(req) });
  if (!res.ok) throw await parseApiError(res);
  const blob = await res.blob();
  return { blob, width: parseInt(res.headers.get("X-Width")!), height: parseInt(res.headers.get("X-Height")!), elapsedMs: parseInt(res.headers.get("X-Elapsed-Ms")!), cacheHitDepth: parseInt(res.headers.get("X-Cache-Hit-Depth")!) };
}
```

**Pourquoi :**
- `fetch` natif + AbortController → pas besoin de lib externe.
- `parseApiError` centralisé dans `api/errors.ts` gère les deux formats (Pydantic `{errors:[{loc,msg}]}` + legacy `{error,message}`).
- Taille minimale du bundle.

**Alternatives :**
- `axios` : lourd, interceptors inutiles pour 10 routes.
- `@tanstack/vue-query` : surkill pour un cache local trivial.

### D5. SSE : composable `useSSESubscription`

**Choix :** un composable qui encapsule `EventSource`, gère la vie cyclique (`onUnmounted` → `es.close()`), dispatch les événements typés dans `useJobStore`.

```ts
export function useSSESubscription(jobId: Ref<string | null>) {
  let es: EventSource | null = null;
  watch(jobId, (id) => {
    es?.close();
    if (!id) return;
    es = new EventSource(`/api/jobs/${id}/stream`);
    es.onmessage = (ev) => jobStore.dispatch(JSON.parse(ev.data));
    es.onerror = () => jobStore.markStreamError();
  }, { immediate: true });
  onUnmounted(() => es?.close());
}
```

**Pourquoi :**
- Vie cyclique propre (auto-close au démontage du composant).
- Testable en isolation (mock `EventSource` global).
- Réutilisable si une future feature a besoin d'un 2ᵉ flux SSE.

### D6. Build : Vite + PostCSS + ESLint + Prettier + Volar

**Choix :**
- **Vite 5** : bundler + dev server + HMR.
- **@vitejs/plugin-vue** : support Vue 3 SFC.
- **TypeScript 5** strict : `"strict": true`, `"noUncheckedIndexedAccess": true`, `"exactOptionalPropertyTypes": true`.
- **ESLint + eslint-plugin-vue + @typescript-eslint** : lint standard.
- **Prettier** : formatage consistent.
- **Volar** : extension VS Code recommandée (`.vscode/extensions.json`).

**Scripts npm :**
- `npm run dev` : vite dev server sur `:5173`, proxy `/api → http://127.0.0.1:5500`, HMR actif
- `npm run build` : bundle prod dans `dist/`, rapport de taille
- `npm run preview` : preview local du build prod
- `npm run type-check` : `vue-tsc --noEmit`
- `npm run lint` : `eslint --ext .vue,.ts src/`
- `npm run lint:fix` : fix auto
- `npm run format` : `prettier --write src/`
- `npm run test` : `vitest run` (détail dans `add-ci-e2e-tests`)

### D7. Mode dev vs prod

**Dev (recommandé pour développement) :**
- Terminal 1 : `python pixel-lab/serve.py` (back sur `:5500`)
- Terminal 2 : `cd pixel-lab/frontend && npm run dev` (front sur `:5173`, proxy `/api`)
- Le navigateur s'ouvre sur `:5173`, HMR actif

**Prod (usage quotidien) :**
- Build : `cd pixel-lab/frontend && npm run build` → génère `pixel-lab/frontend/dist/`
- Copie (script ou `vite.config.ts::build.outDir`) : `pixel-lab/frontend-dist/`
- Un seul process : `python pixel-lab/serve.py` (ou `PIXEL_LAB_PROD=1 python pixel-lab/serve.py`)
- FastAPI mount `StaticFiles(directory="frontend-dist", html=True)` à la racine `/`, fallback SPA sur `index.html` pour les routes non-API

**Pourquoi :**
- Dev : HMR impossible si le back sert les fichiers buildés → deux serveurs.
- Prod : un seul process = déploiement simple, pas de CORS.

### D8. Préservation des préférences utilisateur

**Choix :** les préférences stockées dans `localStorage` (`dashLeftOpen`, éventuellement `lastPipeline`, `liveMode`) MUST être lues au boot par les stores Pinia via un plugin `pinia-plugin-persistedstate` ou un hook manuel dans chaque store.

**Pourquoi :**
- L'utilisateur actuel a des préférences sauvegardées (`localStorage.getItem('dashLeftOpen')`).
- Ne pas les casser à la migration.

## Best Practices (checklist à appliquer pendant l'implémentation)

**Vue 3 / Composition API**
- **`<script setup lang="ts">` partout** : jamais d'Options API, jamais de `defineComponent({...})` explicite.
- **`defineProps<T>()` typé par interface TS** (pas de runtime declarations `defineProps({ foo: String })`) pour bénéficier du typage strict.
- **`defineEmits<{(e: 'update', v: string): void}>()` typé** — idem, pas de string array.
- **Props readonly** : jamais muter `props.xxx`, passer par `emit('update:xxx', newValue)` + `v-model` parent.
- **`ref` vs `reactive` vs `shallowRef`** : `ref` par défaut pour primitives + objets simples ; `shallowRef` pour les gros objets qui ne changent qu'en bloc (ex. un blob) ; `reactive` seulement pour des forms complexes, jamais en paramètre d'API.
- **`computed` pour les dérivations**, pas `watch` + `ref` mutation — `watch` uniquement pour les effets de bord (API call, DOM imperatif).
- **`v-for` avec `:key` stable** (id, pas index) — règle non négociable.
- **Jamais `v-html` sur du contenu utilisateur** (XSS).
- **`onUnmounted` pour tout cleanup** : `EventSource.close()`, `URL.revokeObjectURL`, `AbortController.abort()`, `clearTimeout`, `removeEventListener`. Si un composable crée une ressource, il doit la libérer.
- **Pas d'accès DOM impératif** (`document.getElementById`, `querySelector`) sauf cas extrême documenté. Utiliser `ref()` + `templateRef` Vue.
- **Pas d'`any`, pas de `as unknown as T`**. Si un cast est nécessaire, ajouter un commentaire expliquant pourquoi TS ne peut pas inférer.

**Pinia**
- Style **setup store** (`defineStore('x', () => { ... })`), pas le style Options — meilleur typage TS, plus idiomatique Composition API.
- **Actions asynchrones renvoient des Promises** (pas de fire-and-forget sans `await`).
- **Pas de mutation directe du state depuis un composant** : passer par une action.
- **Pas de dépendance circulaire entre stores** : si `storeA` a besoin de `storeB`, l'injection se fait au niveau du composable ou de l'action, pas en top-level `import`.
- **`persistedstate` ou équivalent** pour `localStorage` : clés explicites, sérialisation safe (pas de `Blob`, pas de fonctions).
- **Getters pour les dérivations coûteuses**, pas de computed inline dans chaque composant.

**TypeScript**
- `tsconfig.json` : `"strict": true`, `"noUncheckedIndexedAccess": true`, `"exactOptionalPropertyTypes": true`, `"noImplicitOverride": true`, `"useUnknownInCatchVariables": true`.
- **Types discriminés** pour les unions (`type SSEEvent = StepStart | StepDone | ...` avec champ `type` discriminant) + type guards exportés.
- **Pas de `!` non-null assertion** sauf dans les tests ou avec un commentaire justifiant.
- **`readonly` et `Readonly<T>`** pour les props/state immuables.
- **`satisfies`** pour annoter un littéral sans casser son inférence (`const routes = { ... } satisfies Record<string, Route>`).

**Composants**
- **1 composant = 1 responsabilité**. Si un composant dépasse 200 lignes, découper.
- **Logique extractible → composable**. Un composable `useXxx` est pur, testable, sans `this`.
- **CSS scoped** (`<style scoped>`) par défaut, variables CSS globales dans `assets/styles.css`.
- **Accessibilité** : `<button>` (pas `<div @click>`), labels associés (`<label :for="id">`), `role="dialog"`/`aria-*` sur les modales, navigation clavier (Esc ferme, Tab cycle).
- **Pas de logique dans les templates** au-delà de ternaire trivial — extraire en `computed`.
- **`defineAsyncComponent`** pour les panneaux lourds (spritesheet, autotile) — code-splitting Vite automatique.

**Client HTTP**
- **`AbortController` systématique** : toute requête annulable (preview, bgmask), cleanup au démontage.
- **Parsing d'erreur centralisé** (`api/errors.ts`) : une fonction `parseApiError(response): Promise<UserFacingError>` qui gère les deux formats (Pydantic + legacy).
- **Pas de catch silencieux** : `catch (e) {}` est interdit. Soit remonter à l'utilisateur (banner), soit logger + ignorer avec commentaire.
- **Types de réponse imposés** côté wrapper : un appel API retourne `Promise<T>` typé, jamais `Promise<any>`.

**Outillage / qualité**
- **ESLint strict** : `plugin:vue/vue3-recommended`, `@typescript-eslint/recommended-strict`, `plugin:vue/vue3-strongly-recommended`.
- **Prettier** aligné sur ESLint via `eslint-config-prettier`.
- **Volar** en `takeover mode` (pas d'extension TypeScript VSCode parallèle).
- **Pre-commit hook** (optionnel, géré dans `add-ci-e2e-tests`) : `lint-staged` lance eslint+prettier sur les fichiers modifiés.
- **`console.log` interdits en prod** : règle ESLint `no-console` en error (sauf `console.warn`/`console.error` autorisés).

**Performance**
- **Lazy-loading** des panneaux lourds (`defineAsyncComponent(() => import('./SpritesheetPanel.vue'))`).
- **`v-show` vs `v-if`** : `v-show` pour toggle fréquent, `v-if` pour contenu conditionnel coûteux.
- **Virtualisation** si `files[]` dépasse 100 entrées (reporter V2).
- **Watchers `{ deep: false }`** par défaut, `deep: true` seulement si justifié.

**Sécurité front**
- **Pas d'`innerHTML`** ni `v-html` avec contenu non contrôlé.
- **CSP stricte** configurée dans `index.html` : `default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'` (Vite produit du code sans eval).
- **Pas de secret dans le bundle** (pas de token en dur — il n'y en a pas, mais règle générale).



- **[Perte du support `file://`]** → l'ancien dashboard s'ouvrait sans serveur en lecture seule. Vue/Vite nécessitent un serveur HTTP (dev ou prod). Mitigation : le README documente clairement. Utilisateur localhost → accès serveur toujours dispo.
- **[Bundle size vs perf]** → Vue 3 + Pinia runtime ~40 KB gzipped, + app ~150-200 KB. Comparable à l'HTML actuel (167 KB) mais plus de JS à parser. Mitigation : lazy-load des panneaux lourds (spritesheet, autotile) via `defineAsyncComponent`.
- **[Désync types TS ↔ schémas Pydantic]** → si le back change un schéma et pas le front, TS ne signale rien. Mitigation V1 : review discipline + tests e2e. Mitigation V2 : `openapi-typescript` (change séparé).
- **[Complexité de migration UX en un seul coup]** → 3 983 lignes à porter. Mitigation : découpage en commits par panneau (`feat(sidebar): port sidebar to Vue`, `feat(convert): port convert panel`, …). Chaque commit est testable isolément.
- **[npm audit / supply chain]** → tout nouveau projet Node amène ses vulnérabilités. Mitigation : pin strict (`package-lock.json` commité), `npm audit` dans le CI (change `add-ci-e2e-tests`).
- **[localStorage non migré]** → clés changeraient sans procédure. Mitigation : conserver les mêmes noms de clés au boot des stores.

## Migration Plan

1. **Phase 1 — Scaffolding** : `npm create vite@latest frontend -- --template vue-ts`. Nettoyage du template. Installation `pinia`, `vue-router` (si besoin). Tsconfig strict. ESLint + Prettier.
2. **Phase 2 — Client API** : écrire `src/api/*.ts` (client HTTP typé) + `src/types/*.ts` (interfaces). Tests unitaires des parsers (happy + erreur).
3. **Phase 3 — Stores Pinia** : implémenter les 6 stores listés en D2. Tests unitaires des actions critiques (ajout de step, revoke blob URL, reset).
4. **Phase 4 — Composants atomiques** : `ImageThumbnail.vue`, `PipelineStepRow.vue`, `StatusDot.vue`, `ErrorBanner.vue`. Storybook/Vitest snapshots.
5. **Phase 5 — Panneaux** : `Sidebar.vue`, `ConvertPanel.vue`, `ComparePane.vue`, `LivePreviewToggle.vue`, `BgDetectPanel.vue` — un par commit.
6. **Phase 6 — Fonctionnalités transverses** : `PixelGridOverlay.vue`, `PixelAxesOverlay.vue`, `GridCustomizer.vue`.
7. **Phase 7 — Spritesheet / Autotile** : portage panneaux avancés (potentiellement lazy-loaded).
8. **Phase 8 — Layout & routing** : `DashboardView.vue`, `App.vue`, intégration layout final.
9. **Phase 9 — Cutover** : suppression `pixel-lab/dashboard/index.html`, adaptation `serve.py` (mount statique prod), mise à jour `README.md`.
10. **Phase 10 — Vérification** : smoke test manuel complet côté prod (serveur unique) et dev (2 serveurs). Toutes les features existantes fonctionnent.

Rollback : `git revert` du merge restaure `dashboard/index.html` et l'ancien `serve.py`. Le back ignore `frontend-dist/`, pas de désync.

## Open Questions

- **Vue Router ou pas ?** : si un jour on veut des vues séparées (ex. `/spritesheet`, `/autotile`), oui. V1 : probablement pas nécessaire, tout tient dans un `DashboardView`. À trancher en phase 8.
- **i18n ?** : UI actuelle en français. Pas de traduction prévue. À ouvrir plus tard si besoin.
- **Dark mode ?** : l'HTML actuel utilise des variables CSS (`--muted`, `--green`, etc.) — un toggle serait trivial mais hors scope V1.
- **`openapi-typescript` pour le typage automatique ?** : user n'a pas retenu l'option. À revisiter après Vue migré.
- **Tests composants Vitest dans ce change ou dans `add-ci-e2e-tests` ?** : les tests écrits en phase 2-4 restent dans ce change (unitaires petits). Les tests composants plus lourds et les e2e sont dans `add-ci-e2e-tests`.
- **Monorepo npm / workspace pnpm ?** : pas V1. `pixel-lab/frontend/` reste un projet npm indépendant.
