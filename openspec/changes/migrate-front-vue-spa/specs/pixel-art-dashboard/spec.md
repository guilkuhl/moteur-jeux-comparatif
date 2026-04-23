## MODIFIED Requirements

### Requirement: Le dashboard SHALL être une SPA Vue 3 + TypeScript buildée avec Vite
Le dashboard MUST être implémenté comme une Single Page Application Vue 3 dans `pixel-lab/frontend/`, utilisant :
- Composition API exclusivement (`<script setup lang="ts">`)
- Pinia pour le state management (stores séparés par domaine)
- TypeScript en mode strict (`"strict": true`, `"noUncheckedIndexedAccess": true`)
- Vite 5+ comme bundler et dev server
- ESLint + Prettier comme outillage qualité

Le build prod MUST produire un dossier statique (`pixel-lab/frontend-dist/`) monté par le backend FastAPI via `StaticFiles` sur la racine `/`, avec fallback SPA vers `index.html` pour toute route non-API.

Le dashboard MUST NOT être utilisable via `file://` — l'usage requiert un serveur HTTP (uvicorn/gunicorn en prod, Vite dev server en dev).

#### Scenario: Structure du projet Vite
- **GIVEN** le dossier `pixel-lab/frontend/`
- **WHEN** on inspecte son contenu
- **THEN** il SHALL contenir au minimum : `package.json` avec scripts `dev`/`build`/`type-check`/`lint`/`test`, `vite.config.ts` avec proxy `/api → http://127.0.0.1:5500`, `tsconfig.json` en mode strict, `src/main.ts`, `src/App.vue`, les dossiers `src/api/`, `src/stores/`, `src/components/`, `src/composables/`, `src/types/`

#### Scenario: Serveur unique en prod
- **GIVEN** le build exécuté (`npm run build`) avec `frontend-dist/` peuplé
- **WHEN** on lance `PIXEL_LAB_PROD=1 python pixel-lab/serve.py`
- **THEN** le serveur SHALL répondre à `http://127.0.0.1:5500/` avec l'`index.html` du build, SHALL servir les assets `assets/*.js`/`assets/*.css` minifiés, ET SHALL continuer à traiter les routes `/api/*` via les routers FastAPI

#### Scenario: Dev avec HMR
- **GIVEN** deux terminaux ouverts (back sur `:5500` + `npm run dev` sur `:5173`)
- **WHEN** le développeur modifie un fichier `.vue` et sauvegarde
- **THEN** le navigateur ouvert sur `:5173` SHALL recharger le composant modifié sans rafraîchir la page complète (HMR Vite actif)

### Requirement: Le state SHALL être centralisé dans des stores Pinia typés
L'état de l'application MUST être géré par des stores Pinia, un store par domaine fonctionnel, avec les typages TS stricts. La liste minimale des stores MUST inclure :
- `useImagesStore` : liste des inputs, image active, cache history
- `usePipelineStore` : étapes du pipeline, validation locale, sérialisation payload
- `usePreviewStore` : mode live, mode pleine résolution, blob URL courant, statut
- `useJobStore` : job actif, événements SSE, progression
- `useBgDetectStore` : toggle preserve bg, tolerance, feather, overlay visible
- `useCompareStore` : compare left/right, divider, zoom

Aucune variable globale JS MUST être utilisée pour l'état partagé (pas de `let activeImage = ...` top-level comme dans l'implémentation historique).

#### Scenario: Store types accessibles
- **GIVEN** un fichier composant `ConvertPanel.vue`
- **WHEN** on import `useImagesStore` et lit `.activeImage`
- **THEN** TypeScript SHALL fournir l'autocomplétion sur les propriétés du store et rejeter les accès à des clés non déclarées

#### Scenario: Blob URL revoke automatique
- **GIVEN** un preview actif avec `lastBlobUrl` dans `usePreviewStore`
- **WHEN** l'utilisateur bascule le toggle live OFF ou lance un nouveau preview
- **THEN** `URL.revokeObjectURL(lastBlobUrl)` SHALL être appelé avant de remplacer par `null` ou par la nouvelle URL, garantissant l'absence de fuite mémoire

### Requirement: Les contrats API SHALL être typés en TypeScript
Toutes les requêtes et réponses API MUST avoir une interface TS correspondante dans `src/types/`. Les appels API MUST passer par les wrappers typés dans `src/api/*.ts`, et non par des `fetch` directs éparpillés dans les composants.

La gestion d'erreur MUST supporter les deux formats :
- Format Pydantic (backend FastAPI) : `{"errors": [{"loc": [...], "msg": "...", "type": "..."}]}`
- Format legacy : `{"error": "...", "message": "..."}`

#### Scenario: Type-check sur payload convert
- **GIVEN** `usePipelineStore().asPayload` qui retourne un `ConvertRequest`
- **WHEN** on passe cet objet à `postConvert(req)`
- **THEN** TypeScript SHALL valider à la compilation que tous les champs requis sont présents et bien typés

#### Scenario: Affichage d'erreur unifié
- **GIVEN** une réponse `422 Unprocessable Entity` avec un corps Pydantic
- **WHEN** le wrapper API parse l'erreur
- **THEN** la fonction `parseApiError` SHALL retourner une string humaine `"pipeline[0].algo: méthode inconnue 'xxx'"`, utilisable directement dans `ErrorBanner.vue`

### Requirement: Les événements SSE SHALL être consommés via un composable réutilisable
La subscription au flux `GET /api/jobs/{job_id}/stream` MUST être encapsulée dans un composable `useSSESubscription(jobId)` qui :
- Crée un `EventSource` au changement de `jobId`
- Parse chaque message en événement typé (union discriminée sur `type`)
- Dispatch dans `useJobStore`
- Ferme proprement la connexion au démontage du composant (`onUnmounted(() => es.close())`)
- Gère les erreurs réseau en marquant le store `streamError`

#### Scenario: Cleanup au démontage
- **GIVEN** un composant utilisant `useSSESubscription(jobId)` avec un `EventSource` ouvert
- **WHEN** le composant est démonté (ex. navigation ou re-render complet)
- **THEN** `es.close()` SHALL être appelé dans le hook `onUnmounted`, et aucun événement ultérieur SHALL être traité

#### Scenario: Typage des événements
- **GIVEN** un message SSE `{"type":"step_done","image":"sprite.png","step":1,"output":"iter_002_sharpen_unsharp_mask.png"}`
- **WHEN** `useSSESubscription` parse l'événement
- **THEN** le type guard `isStepDone(evt)` SHALL permettre au reste du code de traiter `evt.output` avec typage strict, sans `any`

### Requirement: Le bundle prod SHALL être minifié, tree-shaken et sous une taille cible
Le build Vite (`npm run build`) MUST produire un `dist/` dont le chunk principal JS MUST être ≤ 250 KB gzipped. Les panneaux lourds (spritesheet, autotile) MUST être chargés en lazy via `defineAsyncComponent` ou `() => import('...')`.

#### Scenario: Bundle size check
- **GIVEN** un build prod fraîchement exécuté
- **WHEN** on inspecte le rapport Vite (`rollup-plugin-visualizer` ou sortie console)
- **THEN** la taille gzipped totale du chunk principal SHALL être documentée dans le PR de la migration, ET SHALL ne pas dépasser 250 KB

#### Scenario: Lazy loading du panneau spritesheet
- **GIVEN** un utilisateur qui ouvre le dashboard sans toucher au spritesheet
- **WHEN** on inspecte les requêtes Network du navigateur
- **THEN** le chunk associé à `SpritesheetPanel.vue` SHALL ne pas être téléchargé tant que le panneau n'est pas affiché ou monté

### Requirement: Le dashboard SHALL préserver les features existantes listées dans cette capability
La migration Vue NE DOIT PAS supprimer de fonctionnalité utilisateur existante. Toutes les requirements antérieures de la capability `pixel-art-dashboard` (sidebar + liste images, panneau convertir, live preview avec blob URL, compare pane avec divider, bg-detect, pixel grid overlay, pixel axes overlay, grid customization, spritesheet tools, auto-tile) MUST rester applicables — leur implémentation est portée en Vue mais leur comportement utilisateur MUST être préservé.

Les préférences utilisateur stockées dans `localStorage` (au minimum `dashLeftOpen`) MUST être lues au boot et écrites à chaque changement, avec les mêmes clés que la version historique.

#### Scenario: Parité fonctionnelle
- **GIVEN** un utilisateur qui utilisait l'ancien `dashboard/index.html`
- **WHEN** il ouvre la nouvelle SPA Vue
- **THEN** il SHALL retrouver toutes les actions familières : upload, select image, build pipeline, live preview toggle, click ▶ Lancer, comparer avant/après, détecter fond, grille de pixels, etc., avec un comportement fonctionnel identique (le look peut varier à la marge)

#### Scenario: Préférences localStorage préservées
- **GIVEN** un utilisateur avec `localStorage.dashLeftOpen === "false"` hérité de l'ancienne version
- **WHEN** il ouvre la nouvelle SPA Vue
- **THEN** le panneau latéral SHALL apparaître rétracté à l'ouverture (clé lue par `useImagesStore` au boot)
