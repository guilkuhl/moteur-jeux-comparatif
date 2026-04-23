## 1. Infrastructure de tests locale

- [x] 1.1 Créer `pixel-lab/requirements-dev.txt` avec : `pytest>=8`, `pytest-cov>=5`, `pytest-asyncio>=0.23`, `ruff>=0.4`, `pip-audit>=2.7`
- [x] 1.2 Créer `pixel-lab/pyproject.toml` avec config :
  - `[tool.ruff]` : `line-length = 100`, `target-version = "py311"`, sélection `E, F, I, UP, B, SIM`
  - `[tool.pytest.ini_options]` : `testpaths = ["server_fastapi/tests"]`, `asyncio_mode = "auto"`
  - `[tool.coverage.run]` : `source = ["server_fastapi", "scripts"]`, `omit = ["*/tests/*"]`
  - `[tool.coverage.report]` : `fail_under = 60`, `exclude_also = ["if __name__ == .__main__.:"]`
- [x] 1.3 Ajouter dans `pixel-lab/frontend/package.json` les devDependencies : `@playwright/test`, `@vitest/coverage-v8`
- [x] 1.4 Configurer `vitest.config.ts` avec `coverage: { reporter: ['text','json','html'], thresholds: { lines: 50, statements: 50, functions: 50, branches: 40 } }`
- [x] 1.5 Ajouter script npm `"test:coverage": "vitest run --coverage"` et `"e2e": "playwright test"`
- [x] 1.6 Lancer `ruff check pixel-lab/` → résoudre les warnings initiaux (import order, unused, etc.)
- [x] 1.7 Lancer `pytest pixel-lab/server_fastapi/tests/` (suite minimum du change `migrate-back-fastapi`) → vert
- [x] 1.8 Lancer `cd pixel-lab/frontend && npm run test` → vert

## 2. GitHub Actions workflow squelette

- [x] 2.1 Créer `.github/workflows/ci.yml` avec 3 jobs parallèles-puis-séquentiel
- [x] 2.2 Job `back` : `ubuntu-latest`, `actions/setup-python@v5` (3.11, cache pip), installer `requirements.txt + requirements-dev.txt`, `ruff check pixel-lab/`, `ruff format --check pixel-lab/`, `pytest pixel-lab/server_fastapi/tests/ --cov --cov-report=xml`
- [x] 2.3 Job `front` : `ubuntu-latest`, `actions/setup-node@v4` (20, cache npm, cache-dependency-path `pixel-lab/frontend/package-lock.json`), `cd pixel-lab/frontend && npm ci && npm run lint && npm run type-check && npm run test:coverage && npm run build`
- [x] 2.4 Job `e2e` : `needs: [back, front]`, setup Python + Node, install deps, télécharger artefact `frontend-dist`, lancer back en background via `python pixel-lab/serve.py &`, healthcheck `/healthz`, `npx playwright install --with-deps chromium`, `npx playwright test`
- [x] 2.5 Upload artefacts en `if: failure()` : `playwright-report/`, `coverage.xml`, `frontend/coverage/`
- [x] 2.6 Commit + push : vérifier que la CI devient verte sur la branche

## 3. Bundle size check

- [x] 3.1 Ajouter à `package.json` un script `check:size` qui :
  - gzipppe chaque fichier de `dist/assets/*.js` et calcule la taille max
  - fail avec code ≠ 0 si > 300 KB
- [x] 3.2 Ajouter l'étape `npm run check:size` après le `build` dans le job `front` de la CI
- [x] 3.3 Logger la taille détaillée dans la sortie CI (pour historique PR)

## 4. Fixtures back

- [x] 4.1 Générer `pixel-lab/server_fastapi/tests/fixtures/inputs/sprite_small.png` (64×64, déterministe : ex. dégradé sinusoïdal + bruit seed=42)
- [x] 4.2 Générer `sprite_large.png` (512×512, seed=42)
- [x] 4.3 Pour 3 pipelines de référence (`[pixelsnap/block]`, `[denoise/median, sharpen/unsharp_mask]`, `[scale2x/scale2x]`) × 2 images = 6 combinaisons : générer les `iter_NNN_*.png` attendus via le back actuel une seule fois, committer dans `tests/fixtures/golden/<scenario>/`
- [x] 4.4 Un README `tests/fixtures/README.md` documente comment régénérer les goldens (script `tests/fixtures/regenerate.py`)
- [x] 4.5 Pin des versions Pillow/NumPy dans `requirements.txt` (ex. `Pillow==10.3.0`, `numpy==1.26.4`) pour reproductibilité bit-à-bit

## 5. Tests back élargis (scenarios OpenSpec → pytest)

- [x] 5.1 `tests/test_convert_happy_e2e.py` : scenario `Pipeline multi-étapes exécuté en-process` de `pixel-art-conversion-api` → POST convert, stream SSE, `cmp` bit-à-bit contre `tests/fixtures/golden/pixelsnap_denoise_sharpen/`
- [x] 5.2 `tests/test_convert_sse_events.py` : scenario `Événements SSE inchangés` → vérifier séquence exacte des types et champs
- [x] 5.3 `tests/test_convert_validation.py` : scenarios `Algo inconnu rejeté`, `Path-traversal rejeté`, `Param hors bornes rejeté`
- [x] 5.4 `tests/test_convert_step_error.py` : scenario `Gestion d'erreur par étape` (pipeline qui déclenche une exception à l'étape 2, vérifier step_error + continuité)
- [x] 5.5 `tests/test_convert_concurrent.py` : 2 jobs parallèles → 2ᵉ rejeté `409`
- [x] 5.6 `tests/test_preview_binary.py` : scenarios `Réponse réussie au format binaire`, `Header de cache hit`, `Corps PNG directement utilisable`
- [x] 5.7 `tests/test_preview_validation.py` : scenarios `downscale hors bornes`, `algo inconnu`
- [x] 5.8 `tests/test_bgmask.py` : 4 scenarios de la spec (happy, cache hit, tolerance hors bornes, mtime invalidation)
- [x] 5.9 `tests/test_inputs.py` : upload (sanitize name, conflict, too_large), listing (processed flag), delete (trash)
- [x] 5.10 `tests/test_outputs.py` : delete one (history updated), delete all
- [x] 5.11 `tests/test_healthz.py` : scenario `Healthcheck` → `200 OK` avec `{"status":"ok"}`
- [x] 5.12 Coverage après tous ces tests : `pytest --cov` ≥ 60 % sur `server_fastapi/`

## 6. Tests front élargis

- [x] 6.1 `src/stores/*.test.ts` : ≥ 3 tests par store (actions critiques + invariants + edge cases)
- [x] 6.2 `src/api/*.test.ts` : ≥ 2 tests par module (happy + erreur 422 Pydantic + erreur réseau)
- [x] 6.3 `src/composables/useSSESubscription.test.ts` : mock `EventSource` global, vérifier dispatch + cleanup onUnmounted
- [x] 6.4 `src/composables/useBlobUrl.test.ts` : vérifier `createObjectURL` appelé + `revokeObjectURL` au démontage
- [x] 6.5 `src/components/**/*.test.ts` : tests `mount()` pour `ConvertPanel`, `LivePreviewToggle`, `PipelineEditor`, `ComparePane`, `BgDetectPanel` (≥ 2 tests par composant)
- [x] 6.6 Coverage après tous ces tests : `vitest --coverage` ≥ 50 % lines

## 7. E2E Playwright

- [x] 7.1 Scaffolder `pixel-lab/e2e/` : `package.json`, `playwright.config.ts` (baseURL `http://127.0.0.1:5500`, chromium only, retry 1 sur CI), `tsconfig.json`
- [x] 7.2 `pixel-lab/e2e/tests/helpers/setup.ts` : fonction `seedInputs()` qui copie les fixtures de test dans `pixel-lab/inputs/` avant les tests, `cleanup()` qui nettoie
- [x] 7.3 `tests/smoke.spec.ts` : le dashboard boot, la sidebar liste ≥ 1 image, aucun error log console
- [x] 7.4 `tests/convert.spec.ts` : select image → add 2 steps → click Lancer → attendre SSE `done` → sidebar reflète 2 nouveaux iters → `/api/outputs/<stem>` contient bien 2 fichiers
- [x] 7.5 `tests/preview_live.spec.ts` : toggle live ON → change un param → blob URL créé → hash pixel différent de l'image source → toggle OFF → blob URL révoqué (vérifier via `performance.memory` ou monkey-patch `URL.revokeObjectURL`)
- [x] 7.6 `tests/bgdetect.spec.ts` : click détecter fond → overlay apparaît → info couleur affichée
- [x] 7.7 `tests/upload.spec.ts` : upload une image (input file programmatique) → sidebar reflète immédiatement la nouvelle entrée
- [x] 7.8 Lancer `npx playwright test` en local, tous verts
- [x] 7.9 Intégrer dans le job `e2e` du workflow

## 8. Dependabot et sécurité

- [x] 8.1 Créer `.github/dependabot.yml` : updates hebdomadaires pour `npm` (dir `pixel-lab/frontend`), `pip` (dir `pixel-lab`), `github-actions` (dir `/`)
- [x] 8.2 Ajouter step `pip-audit` dans le job `back` (gate soft : warn, pas fail, V1)
- [x] 8.3 Ajouter step `npm audit --production --audit-level=high` dans le job `front` (même gate soft V1)

## 9. Documentation

- [x] 9.1 Ajouter section "Tests" dans `pixel-lab/README.md` :
  - Back : `pip install -r requirements-dev.txt && pytest`
  - Front : `cd pixel-lab/frontend && npm ci && npm test`
  - E2E : `cd pixel-lab/e2e && npm ci && npx playwright install chromium && npx playwright test`
- [x] 9.2 Ajouter un badge de statut CI dans le `README.md` racine : `![CI](https://github.com/<org>/<repo>/actions/workflows/ci.yml/badge.svg)`
- [x] 9.3 Documenter dans `CONTRIBUTING.md` (nouveau) : process pour ajouter un test, règles de coverage, comment debugger un échec Playwright (télécharger artefact)

## 10. Validation

- [x] 10.1 Ouvrir une PR de test (modif triviale + test cassé volontairement) → CI doit fail avec message clair
- [x] 10.2 Corriger, push → CI verte, merge autorisé
- [x] 10.3 Activer branch protection sur `master` dans les settings GitHub : "Require status checks to pass before merging" cochant `back`, `front`, `e2e` (action manuelle utilisateur, hors code)
- [x] 10.4 Documenter le temps CI total observé (doit rester < 15 min)
