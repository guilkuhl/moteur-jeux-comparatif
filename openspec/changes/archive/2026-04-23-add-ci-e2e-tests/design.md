## Context

Le projet est passé d'un prototype (`serve.py` simple HTTP) à un outil structuré : backend in-process unifié, refactor en FastAPI prévu, SPA Vue prévue. À ce stade, l'absence de tests automatisés est le plus grand risque restant. Les deux migrations (back + front) sont des cutovers lourds et **doivent** être couvertes par une CI verte avant merge.

Trois niveaux de tests sont nécessaires :
1. **Unitaires** : pytest (services, schémas) + Vitest (stores, composables). Rapides, ciblés, exécutés en parallèle.
2. **Intégration / route** : pytest + `TestClient` FastAPI (happy path + erreurs par route). Pas de vrai navigateur, pas de vrai disque de prod — tmp_path + fixtures.
3. **E2E** : Playwright sur la vraie app (FastAPI + frontend-dist servi) — un seul Chromium, scenarios critiques uniquement.

La CI GitHub Actions orchestre ces trois niveaux.

## Goals / Non-Goals

**Goals:**
- Une CI verte obligatoire avant merge sur `master` (protection branche optionnelle à activer dans les settings GitHub).
- Coverage minimum : 60 % back, 50 % front. Gates soft (fail), pas de sur-engineering.
- ≤ 10 scenarios e2e Playwright, couvrant les flux critiques (convert, preview live, bg-detect, upload, delete).
- Fixtures déterministes : images PNG de test + golden `iter_NNN_*.png` pour comparer bit-à-bit après `/api/convert`.
- Rapports de coverage et Playwright uploadés comme artefacts GitHub pour debug.
- Build size check : fail si bundle prod > 300 KB gzipped.
- `ruff` + ESLint + Prettier en gate dur.

**Non-Goals:**
- Pas de test de charge (k6, locust) — outil localhost mono-utilisateur.
- Pas de tests de compatibilité multi-browser Playwright — Chromium only V1.
- Pas de test de compatibilité multi-OS — `ubuntu-latest` only.
- Pas de mutation testing, fuzzing, property-based testing en V1.
- Pas de Docker/docker-compose — GitHub Actions service containers si besoin d'une DB plus tard.
- Pas de snapshot visuel (Percy, Chromatic) — trop fragile sur du rendu pixel-art (le test bit-à-bit suffit pour les artefacts).

## Decisions

### D1. Runner CI : GitHub Actions (vs GitLab CI, CircleCI)

**Choix :** GitHub Actions.

**Pourquoi :**
- Le repo est sur GitHub, zéro config externe.
- Gratuit pour repo public, 2000 min/mois gratuits en privé (largement suffisant).
- Matrix builds, artefacts, caching : tout natif.
- Integration PR : statuts, commentaires, badges.

### D2. Un workflow unique avec plusieurs jobs (vs workflows séparés)

**Choix :** `.github/workflows/ci.yml` avec 3 jobs : `back`, `front`, `e2e`.

**Pourquoi :**
- Vue d'ensemble unique dans l'UI GitHub.
- `e2e` dépend explicitement de `back` et `front` via `needs:`, ce qui rend l'ordre et les échecs lisibles.
- Un seul point d'entrée pour triggers (`on: push, pull_request`).

### D3. Caching : pip et npm

**Choix :**
- `actions/setup-python@v5` avec `cache: pip` et `cache-dependency-path: pixel-lab/requirements*.txt`.
- `actions/setup-node@v4` avec `cache: npm` et `cache-dependency-path: pixel-lab/frontend/package-lock.json`.

**Pourquoi :** réduit chaque job de ~30-60 s en CI.

### D4. Tests e2e : Playwright (vs Cypress, Selenium)

**Choix :** Playwright.

**Pourquoi :**
- Support natif TypeScript.
- `@playwright/test` bundle intégré.
- Auto-wait + locators robustes (`page.getByRole`, `page.getByText`).
- Trace viewer + video recording pour debug CI.
- Install browsers reproductible (`npx playwright install --with-deps chromium`).

**Alternatives :**
- **Cypress** : bon mais écosystème plus "walled garden" (runner propriétaire, moins de flexibilité).
- **Selenium** : legacy, debug douloureux.

### D5. Fixtures PNG versionnées dans le repo

**Choix :** ≥ 2 PNG de test (`sprite_small.png` 64×64, `sprite_large.png` 512×512) committés dans `pixel-lab/server_fastapi/tests/fixtures/inputs/`. Et les PNG attendus `iter_NNN_*.png` pour chaque pipeline testé dans `tests/fixtures/golden/<scenario>/`.

**Pourquoi :**
- Tests bit-à-bit déterministes (Pillow/NumPy donnent le même output sur la même version de libs).
- Pas de dépendance réseau (télécharger depuis un CDN serait fragile).
- ≤ 1 MB total en repo (acceptable).

**Risque :** si Pillow/NumPy update casse le déterminisme → fail CI → pin strict des versions dans `requirements.txt` (déjà en place indirectement via `Pillow` transitivement).

### D6. Coverage gates soft (vs hard fail)

**Choix :**
- Back : `--cov-fail-under=60` (gate dur à 60 %).
- Front : `--coverage --coverage.reporter=text --coverage.thresholds.lines=50` (gate dur à 50 %).

**Pourquoi :**
- 60 % / 50 % est réaliste V1 avec les tests proposés (routers + stores principaux).
- Un gate à 80 % pousserait à des tests de façade peu utiles.
- La barre pourra monter au fil du temps (commit: "bump coverage to 70%").

### D7. Bundle size check : script dédié

**Choix :** après `npm run build`, script shell qui compare `dist/assets/index-*.js.gz` (compression préalable via `gzip`) à un seuil codé en dur (300 KB). Fail si dépassé.

**Pourquoi :**
- `size-limit` serait trop lourd.
- Un check explicite force la vigilance sur les dépendances lourdes ajoutées par inadvertance.

### D8. Playwright : chromium only, headless

**Choix :** V1 chromium uniquement, mode headless en CI. Matrix future possible mais pas d'ajout gratuit de Firefox/WebKit en V1.

**Pourquoi :**
- 95 % de la surface bug UI se révèle en chromium.
- Chaque browser supplémentaire = ~2 min CI de plus + flakiness.

### D9. Démarrage des services en CI pour e2e

**Choix :** dans le job `e2e`, deux étapes :
1. `python pixel-lab/serve.py &` (background) sur `:5500` avec `frontend-dist` servi en statique.
2. `curl --retry 10 --retry-delay 1 http://127.0.0.1:5500/healthz` pour attendre l'API ready.
3. `cd pixel-lab/e2e && npx playwright test`.

**Pourquoi :**
- Pas besoin de service container Docker — le back est un script Python.
- Healthcheck explicite > `sleep 10`.

### D10. Artefacts en cas d'échec

**Choix :** en `if: failure()`, upload :
- `pixel-lab/e2e/playwright-report/` (traces, vidéos, screenshots).
- `pixel-lab/frontend/coverage/` (HTML coverage front).
- `pixel-lab/coverage.xml` (back).

**Pourquoi :** le debug post-échec en CI est critique. Sans artefacts, les échecs deviennent frustrants.

## Best Practices (checklist à appliquer pendant l'implémentation)

**GitHub Actions workflow**
- **Pin versions d'actions** : `actions/checkout@v4`, `actions/setup-python@v5`, `actions/setup-node@v4` (SHA de commit pour paranoïa max, tag mineur OK V1).
- **`permissions:` minimum** au niveau workflow : `contents: read` par défaut, élever uniquement où strictement nécessaire (ex. `packages: write` n'est pas requis).
- **`concurrency: { group: ci-${{ github.ref }}, cancel-in-progress: true }`** : un push en écrase un précédent en cours sur la même branche.
- **`timeout-minutes: 20`** par job pour éviter les workflows zombies.
- **Caching explicite** : `setup-python` et `setup-node` utilisent `cache:` natif avec `cache-dependency-path` précis ; ne pas utiliser `actions/cache` direct sauf besoin spécifique.
- **`fail-fast: false`** sur les matrices (même si V1 n'a qu'une dimension) — meilleure visibilité des échecs.
- **Steps nommées** : chaque `run:` a un `name:` clair (affiché dans l'UI, utile en debug).
- **Pas de secret en clair** : toujours via `${{ secrets.X }}`. Aucun secret n'est attendu V1, mais règle générale.
- **`working-directory:`** explicite quand on travaille hors racine (`pixel-lab/frontend`).

**Python / pytest**
- **`pytest` en mode strict** : `-Werror` pour transformer les warnings en erreurs (attraper les DeprecationWarning).
- **Fixtures dans `conftest.py`** proches des tests qui les consomment (pas tout en top-level).
- **Pas de dépendance entre tests** : chaque test reproductible isolément (`pytest -k test_xxx` doit passer seul).
- **`pytest-asyncio` en mode `auto`** : évite le décorateur `@pytest.mark.asyncio` répétitif.
- **Factory fixtures** pour les objets complexes (ex. `make_convert_payload(algo="sharpen")`).
- **Pas de `time.sleep`** en test — `wait_for` + timeout explicite. Si un délai est inévitable, documenter pourquoi.
- **Couverture HTML uploadée** comme artefact en cas d'échec pour drill-down.
- **Nommage** : `test_<module>_<behavior>`, et un docstring une ligne décrivant le scenario couvert.

**TypeScript / Vitest**
- **`happy-dom` ou `jsdom`** explicite dans `vitest.config.ts`, pas de choix implicite.
- **`@vue/test-utils` `mount()`** pour les composants, `shallowMount()` pour les tests d'intégration légers.
- **Pas de `wrapper.vm.xxx`** pour accéder au state interne — piloter via DOM/events (plus robuste au refactor).
- **`vi.fn()`** pour les mocks, `vi.spyOn()` pour observer ; `vi.clearAllMocks()` dans `afterEach` global.
- **Coverage thresholds par métrique** (lines, statements, functions, branches) — pas juste `lines`.
- **Pas de `any` dans les tests** — typer les mocks avec `MockedFunction<typeof fn>`.

**Playwright**
- **Locators sémantiques** : `page.getByRole('button', { name: 'Lancer' })`, `page.getByLabel('Live preview')` — **pas** `page.locator('.btn-primary')` fragile.
- **`await expect(locator).toHaveText(...)`** : auto-wait intégré, pas de `page.waitForTimeout`.
- **Un test = un scenario utilisateur complet**, pas une suite micro-interactions.
- **`test.describe.configure({ mode: 'parallel' })`** par fichier quand possible (tests indépendants).
- **Traces activées** : `trace: 'on-first-retry'` dans `playwright.config.ts` — léger en CI verte, précieux en debug.
- **Fixtures de scenario** : un `beforeEach` qui `seedInputs()` + `cleanup()` en `afterEach` pour l'isolation.
- **Pas de hardcoded ports** : baseURL en variable d'env (`process.env.PIXEL_LAB_URL ?? 'http://127.0.0.1:5500'`).
- **Retry discipliné** : `retries: 1` en CI (attraper la flakiness vraie), `retries: 0` en local (ne pas masquer les régressions).

**Ruff / ESLint / formatage**
- **`ruff` remplace `flake8` + `black` + `isort`** — une seule commande.
- **Règles additionnelles pertinentes** : `B` (bugbear), `SIM` (simplify), `UP` (pyupgrade), `ARG` (unused args), `PTH` (pathlib).
- **ESLint** : `eslint-plugin-vue` + `@typescript-eslint/eslint-plugin` + `eslint-plugin-import` (ordre imports, pas de cycles).
- **Prettier** : line-width 100, single quotes JS/TS, double quotes JSX.
- **Configs committées à la racine du sous-projet** (`pixel-lab/frontend/.eslintrc.cjs`, `pixel-lab/pyproject.toml`) — pas de config user-global.

**Dépendances / supply chain**
- **`package-lock.json` et `requirements.txt` pinnés** (versions exactes ou caret, pas de `latest`).
- **`npm ci` en CI** (pas `npm install` — reproductibilité stricte).
- **`pip install --require-hashes`** idéalement (V2), V1 : pin exact suffit.
- **Dependabot** hebdomadaire (npm + pip + github-actions).
- **`npm audit --audit-level=high`** en CI (gate soft V1, hard V2).
- **Pas de dépendance non nécessaire** : chaque ajout `npm i X` justifié dans le commit message.

**Fixtures et déterminisme**
- **Seeds fixes** partout (`numpy.random.seed(42)`, `Math.random` remplacé par un générateur seedé dans les tests).
- **Versions Pillow/NumPy pinnées** dans `requirements.txt` pour garantir la reproductibilité bit-à-bit.
- **Pas de `datetime.now()` direct** dans le code testé — injecter une horloge (`clock: Callable[[], datetime] = datetime.now`).
- **Goldens versionnés** avec README expliquant comment régénérer et quelles vérifications visuelles faire avant commit.

**Artefacts / debug**
- **Naming explicite** : `playwright-report-${{ github.run_id }}`, `coverage-${{ matrix.os }}`.
- **Retention policy courte** : `retention-days: 14` (default 90 — trop long pour du debug).
- **Upload conditionnel** : `if: failure() || cancelled()` — pas de bruit sur les runs verts.



- **[Tests flaky (e2e surtout)]** → Playwright avec auto-wait limite déjà beaucoup. Mitigation : un test flaky qui échoue 2× est muté en `test.fixme` + issue ouverte, pas de rerun silencieux.
- **[CI lent = frein à itération]** → 10 min par PR est acceptable sur un projet localhost. Si ça monte à 20+ min, revoir la matrice.
- **[Coverage gate trop strict bloque les PRs hotfix]** → la ligne 60/50 % est calibrée pour passer la PR de migration initiale ; si un hotfix urgent dépasse, le gate peut être bumpé temporairement.
- **[Déterminisme Pillow/NumPy]** → pin des versions dans `requirements.txt`. Un test de smoke vérifie la version au boot du CI.
- **[Playwright browsers dans l'image GitHub Actions]** → installés via `npx playwright install --with-deps chromium` (~100 MB téléchargement, caché par action `cache`).

## Migration Plan

1. **Phase 1 — Infra locale** : créer `requirements-dev.txt`, `pyproject.toml` (ruff/pytest/coverage config). Les contributeurs peuvent dès maintenant lancer `pytest`/`npm test` en local.
2. **Phase 2 — Workflow CI skeleton** : ajouter `.github/workflows/ci.yml` avec les 3 jobs, mais avec `pytest` + `vitest` sur la suite existante (possiblement ~vide au départ). La CI devient verte sur master.
3. **Phase 3 — Tests back élargis** : porter les scenarios OpenSpec des specs en tests pytest. ≥ 1 test par scenario des requirements principales.
4. **Phase 4 — Tests front élargis** : ≥ 1 test Vitest par store + par composant de panneau principal.
5. **Phase 5 — E2E Playwright** : scaffolder `pixel-lab/e2e/`, écrire les 5 scenarios listés, valider en CI.
6. **Phase 6 — Fixtures golden** : générer une fois avec la version "de référence" du back post-migration FastAPI, committer dans `tests/fixtures/golden/`.
7. **Phase 7 — Activer branch protection** : demander au mainteneur d'activer "Require status checks to pass" sur `master` dans les settings du repo (hors scope code mais à documenter).

Rollback : `git revert` du workflow = CI désactivée. Les tests restent utilisables en local.

## Open Questions

- **Ordre de merge vs `migrate-back-fastapi` / `migrate-front-vue-spa`** : deux options :
  - A) CI d'abord (squelette + tests existants), migration ensuite. Avantage : la migration est elle-même testée dès le premier commit.
  - B) Migrations d'abord (big bang + tests unitaires inclus), CI ensuite. Avantage : pas de churn sur les tests à réécrire.
  - **Recommandation** : A, avec tests ajoutés au fil des migrations.
- **Self-hosted runner pour accélérer ?** : overkill V1 (GitHub Actions hosted suffit).
- **SonarCloud / Codecov intégration ?** : hors scope V1. `--cov-report=xml` prépare le terrain si on veut un rapport externe plus tard.
- **Tests de régression visuelle ?** : pas V1. Playwright peut capturer des screenshots mais comparer du pixel-art est bruité.
- **Activer Dependabot dans la même PR ?** : oui, ajout mineur de `.github/dependabot.yml`.
