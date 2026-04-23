# dev-quality-gates Specification

## Purpose
Gates de qualité appliqués à chaque PR du dépôt Pixel Lab, appliqués par un workflow GitHub Actions (`.github/workflows/ci.yml`). Couvre lint (ruff + ESLint), typage (vue-tsc strict), tests (pytest + Vitest), build front (Vite), taille du bundle (gzipped ≤ 300 KB) et smoke test bout-en-bout (boot uvicorn + frontend-dist monté).

## Requirements

### Requirement: Le projet SHALL exposer un workflow CI GitHub Actions qui bloque les PRs défaillantes
Le dépôt MUST contenir un workflow `.github/workflows/ci.yml` déclenché sur `push` et `pull_request` qui exécute au minimum trois jobs : `back`, `front`, `smoke`. Chaque job MUST échouer (exit ≠ 0) si une de ses gates n'est pas satisfaite. Les versions d'actions MUST être pinnées, les permissions définies au minimum (`contents: read`), et `concurrency` MUST annuler les runs obsolètes sur la même référence.

#### Scenario: PR avec test cassé est bloquée
- **GIVEN** une PR qui introduit un test `pytest` échouant ou une erreur `tsc` ou un `ruff check` fail
- **WHEN** la CI s'exécute
- **THEN** le job correspondant SHALL échouer et la PR SHALL afficher un check rouge

#### Scenario: Permissions et concurrency minimales
- **GIVEN** le fichier `ci.yml`
- **WHEN** on inspecte l'en-tête
- **THEN** il SHALL contenir `permissions: contents: read` et `concurrency: { group: ci-${{ github.ref }}, cancel-in-progress: true }`

### Requirement: Le job `back` SHALL lint, tester et mesurer la coverage Python
Le job `back` MUST installer les deps depuis `pixel-lab/requirements-dev.txt` (avec cache pip), lancer `ruff check`, puis `pytest --cov=server_fastapi --cov=scripts/apply_step.py --cov-report=xml` avec un `fail_under` configuré dans `pyproject.toml`. Le rapport `coverage.xml` MUST être uploadé comme artefact en cas d'échec (retention 14 jours).

#### Scenario: Lint strict bloque
- **GIVEN** une PR introduisant des imports non utilisés
- **WHEN** `ruff check` s'exécute
- **THEN** le job SHALL échouer avec la règle `F401` visible

### Requirement: Le job `front` SHALL lint, type-checker, tester, builder et vérifier la taille du bundle
Le job `front` MUST exécuter dans l'ordre : `npm ci`, `npm run type-check` (`vue-tsc --noEmit`), `npm run test` (Vitest), `npm run build` (Vite), `npm run check:size` (gzipped ≤ 300 KB). L'artefact `frontend-dist/` MUST être uploadé via `actions/upload-artifact` pour consommation par le job `smoke`.

#### Scenario: Bundle size regresse
- **GIVEN** une PR qui fait passer le chunk principal de 240 KB à 320 KB gzipped
- **WHEN** le job `front` exécute `npm run check:size`
- **THEN** le script SHALL exit ≠ 0 avec un message indiquant la taille observée et le seuil 300 KB

#### Scenario: TypeScript strict bloque
- **GIVEN** une PR avec `const x: number = store.activeImage` alors que `activeImage: string | null`
- **WHEN** `npm run type-check` s'exécute
- **THEN** `vue-tsc` SHALL signaler l'erreur TS2322, le job SHALL échouer

### Requirement: Le job `smoke` SHALL booter le serveur avec le front monté et vérifier les endpoints clés
Le job `smoke` MUST dépendre de `back` ET `front`, télécharger l'artefact `frontend-dist`, booter `python serve.py` en background avec healthcheck `/healthz` (timeout 30 s), puis `curl` les endpoints `/healthz`, `/openapi.json`, `/api/algos`, `/`. Le job MUST échouer si l'un de ces endpoints ne répond pas `200`.

#### Scenario: Smoke check booté et joignable
- **GIVEN** les jobs `back` et `front` verts
- **WHEN** le job `smoke` boote uvicorn et attend `/healthz`
- **THEN** la chaîne `curl /healthz → /openapi.json → /api/algos → /` SHALL toutes renvoyer `200` en moins de 30 secondes cumulées

### Requirement: Les dépendances SHALL être mises à jour automatiquement par Dependabot
Le dépôt MUST configurer `.github/dependabot.yml` avec des updates hebdomadaires pour `npm` sur `pixel-lab/frontend`, `pip` sur `pixel-lab`, et `github-actions` sur `/`. Les PRs Dependabot MUST passer la même CI que les PRs humaines avant merge.

#### Scenario: Dependabot ouvre une PR
- **GIVEN** une nouvelle version patch d'une dépendance npm
- **WHEN** Dependabot exécute son scan hebdomadaire
- **THEN** une PR SHALL être ouverte automatiquement avec le diff du `package.json` + `package-lock.json`, et la CI SHALL l'exécuter normalement
