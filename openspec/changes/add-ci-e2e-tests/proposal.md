## Why

Aujourd'hui, le Pixel Lab n'a **aucun test automatisé** :
- `pixel-lab/scripts/algorithms/test_params.py` existe mais n'est pas lancé par un CI.
- Les refactors back (`pixel-lab-backend-perf`) et les futurs (`migrate-back-fastapi`, `migrate-front-vue-spa`) reposent sur des tests manuels `curl` + clic-clic dans le dashboard.
- Zéro test front.
- Zéro workflow GitHub Actions.

Deux risques concrets :
1. **Régression silencieuse lors des migrations** : un refactor qui casse `/api/convert` ou le parsing d'un blob ne sera détecté qu'à l'usage utilisateur.
2. **Pas de gate de qualité sur les PRs** : une PR peut introduire une erreur de syntaxe Python, un type TS invalide, un lint break, sans rien signaler avant merge.

Les changes `migrate-back-fastapi` et `migrate-front-vue-spa` introduisent déjà des tests unitaires minimaux (pytest pour les routers, vitest pour les stores). Ce change **complète la pyramide** avec :
- **CI GitHub Actions** : workflow unique qui lance tests back + tests front + smoke e2e à chaque PR.
- **Tests e2e Playwright** : scenarios utilisateur bout-en-bout sur la vraie SPA Vue + vraie API FastAPI (boot → upload → preview → convert → compare → assert `iter_NNN_*.png` écrits).
- **Gates de qualité** : type-check TS, lint, coverage minimum, build size check, `npm audit`.

Ces trois briques transforment le projet en outil "shippable" — toute PR passe par la même checklist avant merge.

## What Changes

- **NEW** `.github/workflows/ci.yml` : pipeline GitHub Actions déclenché sur push et pull_request (branches `master`, `claude/**`). Jobs :
  - `back-lint-test` : Python 3.11, `pip install -r pixel-lab/requirements.txt -r pixel-lab/requirements-prod.txt -r pixel-lab/requirements-dev.txt`, `ruff check`, `ruff format --check`, `pytest pixel-lab/server_fastapi/tests/ --cov=server_fastapi --cov-report=xml --cov-fail-under=60`
  - `front-lint-test-build` : Node 20, `cd pixel-lab/frontend && npm ci && npm run lint && npm run type-check && npm run test -- --coverage && npm run build`. Check bundle size (fail si > 300 KB gzipped).
  - `e2e-playwright` : dépend de `back-lint-test` + `front-lint-test-build`. Boot FastAPI en background + serveur statique `frontend-dist`, lance `npx playwright test`. Upload d'un artefact `playwright-report/` en cas d'échec.
- **NEW** `pixel-lab/requirements-dev.txt` : `pytest>=8`, `pytest-cov>=5`, `pytest-asyncio>=0.23`, `ruff>=0.4`, `httpx>=0.27` (déjà dans prod pour TestClient).
- **NEW** `pixel-lab/pyproject.toml` (ou section dans `setup.cfg`) : config `ruff`, `pytest`, `coverage`. Pyproject préféré.
- **NEW** `pixel-lab/server_fastapi/tests/` (scope élargi par ce change) :
  - `test_convert_e2e.py` : batch complet image × pipeline 3 étapes, `cmp` bit-à-bit contre fixture `tests/fixtures/golden/`.
  - `test_preview_cache.py` : scénarios cache hit depth 0/1/2/3.
  - `test_bgmask_cache.py`, `test_inputs_upload.py`, `test_outputs_delete.py`, `test_jobs_sse.py` (stream consommé via `httpx.AsyncClient.stream`).
  - `tests/fixtures/` : ≥ 2 images PNG de test (`sprite_small.png` 64×64, `sprite_large.png` 512×512), et leurs `iter_NNN_*.png` de référence (golden files).
- **NEW** `pixel-lab/frontend/tests/` (scope élargi) :
  - Tests composants Vitest + Vue Test Utils pour chaque panneau principal (`ConvertPanel.test.ts`, `ComparePane.test.ts`, `LivePreviewToggle.test.ts`, …).
  - Mocks API centralisés dans `tests/mocks/api.ts`.
- **NEW** `pixel-lab/e2e/` : projet Playwright dédié (séparé du dossier `frontend/` pour ne pas polluer le bundle).
  - `playwright.config.ts` : baseURL `http://127.0.0.1:5500`, browsers chromium uniquement V1.
  - `tests/smoke.spec.ts` : boot → page loaded → sidebar populated (fixtures pré-chargées).
  - `tests/convert.spec.ts` : upload image → build pipeline 2 étapes → click Lancer → attente `done` SSE → vérifie 2 `iter_NNN_*.png` apparaissent dans la sidebar.
  - `tests/preview.spec.ts` : toggle live → change un param → attendre re-render → vérifie image preview change (pixel hash) + `X-Cache-Hit-Depth` reflété dans le label.
  - `tests/bgdetect.spec.ts` : click détecter → overlay apparaît avec la bonne couleur.
  - `tests/helpers/` : wrappers Playwright pour interactions courantes (uploadFixture, waitForJobDone, assertBlobURL).
- **NEW** `pixel-lab/frontend/.github/dependabot.yml` (ou dépôt racine) : updates hebdomadaires npm et pip.
- **NEW** `pixel-lab/README.md` section "Tests" : comment lancer chaque suite en local (`pytest`, `npm run test`, `npx playwright test`).
- **NEW** badge CI dans `README.md` racine du dépôt.
- **PAS DE CHANGEMENT** : aucune modification du code applicatif (back ou front) au-delà de l'ajout de fixtures et de config de tests.

## Capabilities

### New Capabilities
- `dev-quality-gates` : nouvelle capability transverse qui décrit les gates de qualité appliqués à chaque PR (CI, coverage, lint, bundle size, e2e). Ce n'est pas une feature produit, mais c'est une surface observable : un mainteneur doit pouvoir s'appuyer sur ces garanties.

### Modified Capabilities
_Aucune._ Les tests ne modifient pas les capabilities existantes — ils les **vérifient**.

## Impact

- **Code touché**
  - Nouveau `.github/workflows/ci.yml` (~150 lignes YAML).
  - Nouveau `pixel-lab/requirements-dev.txt`, `pixel-lab/pyproject.toml` (~50 lignes).
  - Nouveaux tests pytest (~30 fichiers, ~1 500 lignes) sous `pixel-lab/server_fastapi/tests/`.
  - Nouveau `pixel-lab/e2e/` (~10 fichiers, ~800 lignes).
  - Nouveaux tests Vitest (~15 fichiers, ~1 000 lignes) sous `pixel-lab/frontend/tests/` ou colocalisés `*.test.ts`.
  - Fixtures PNG (~20 fichiers, ~500 KB) sous `pixel-lab/server_fastapi/tests/fixtures/`.
  - Mise à jour `pixel-lab/README.md` (section Tests).
- **APIs modifiées** : aucune.
- **Dépendances**
  - Python : `pytest`, `pytest-cov`, `pytest-asyncio`, `ruff`.
  - Node : `@playwright/test`, `@vitest/coverage-v8` (ajouté aux devDependencies front), `size-limit` ou script shell custom pour bundle size.
- **CI cost** : GitHub Actions = gratuit pour repo public. Temps estimé :
  - `back-lint-test` : ~2 min (install deps + pytest)
  - `front-lint-test-build` : ~3 min (npm ci + tsc + vitest + vite build)
  - `e2e-playwright` : ~5 min (install browsers + up services + run)
  - Total par PR : ~10 min (jobs parallèles quand possible).
- **Sécurité** : `npm audit --production` et `pip-audit` dans le CI (gate soft : warn, pas fail V1).
- **Performance** : aucun impact sur runtime. Les fixtures PNG ajoutent ~500 KB au repo.
- **Migration de données** : aucune.
- **Compatibilité descendante** : la CI est optionnelle en local (les contributeurs peuvent continuer `pytest`/`npm test` manuellement). En PR, elle devient obligatoire.
- **Rollback** : supprimer le workflow `.github/workflows/ci.yml` désactive la CI. Les tests restent utilisables en local.

## Prerequisites

- Ce change **dépend des changes `migrate-back-fastapi` et `migrate-front-vue-spa`** — pytest route tests et Vitest store tests présupposent la nouvelle structure. Il peut être :
  - **merged après les deux** : recommandé, permet de calibrer les tests sur la version finale.
  - **merged avant, avec des tests portés incrémentalement** : possible mais ajoute du churn (les tests seraient réécrits 2 fois).
- La décision d'ordre de merge est tranchée en revue.
