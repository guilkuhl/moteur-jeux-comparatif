## ADDED Requirements

### Requirement: Le projet SHALL exposer un workflow CI GitHub Actions qui bloque les PRs défaillantes
Le dépôt MUST contenir un workflow `.github/workflows/ci.yml` déclenché sur `push` et `pull_request` qui exécute au minimum trois jobs : `back`, `front`, `e2e`. Chaque job MUST échouer (exit ≠ 0) si une de ses gates n'est pas satisfaite. La protection de branche `master` SHALL être configurée (action manuelle côté GitHub settings, documentée) pour exiger que ces trois jobs soient verts avant tout merge.

#### Scenario: PR avec test cassé est bloquée
- **GIVEN** une PR qui introduit un test `pytest` échouant ou une erreur `tsc` ou un `npm run lint` fail
- **WHEN** la CI s'exécute
- **THEN** le job correspondant SHALL échouer, la PR SHALL afficher un check rouge, et le bouton Merge SHALL être désactivé (sous réserve que la branch protection est configurée)

#### Scenario: Workflow déclenché automatiquement
- **GIVEN** un push sur une branche `claude/*` ou une PR ouverte contre `master`
- **WHEN** GitHub reçoit l'événement
- **THEN** le workflow `ci.yml` SHALL démarrer automatiquement, visible dans l'onglet Actions de la PR

### Requirement: Le job `back` SHALL lint, type-checker, tester et mesurer la coverage Python
Le job `back` du workflow CI MUST exécuter les étapes suivantes dans l'ordre :
1. Checkout + `setup-python@v5` (Python 3.11, cache pip)
2. Installer `requirements.txt`, `requirements-prod.txt`, `requirements-dev.txt`
3. `ruff check pixel-lab/` (lint — fail si erreurs)
4. `ruff format --check pixel-lab/` (formatage — fail si non formaté)
5. `pytest pixel-lab/server_fastapi/tests/ --cov=server_fastapi --cov=scripts --cov-report=xml --cov-fail-under=60`

La coverage MUST atteindre au minimum 60 % sur les modules `server_fastapi/` et `scripts/apply_step.py`.

#### Scenario: Coverage insuffisante
- **GIVEN** une PR qui supprime des tests ou qui ajoute du code non testé, faisant tomber la coverage à 55 %
- **WHEN** le job `back` s'exécute
- **THEN** `pytest --cov-fail-under=60` SHALL échouer avec message explicite, le job `back` SHALL être rouge, le rapport `coverage.xml` SHALL être uploadé comme artefact

#### Scenario: Ruff lint bloque
- **GIVEN** une PR introduisant `import sys, os` non utilisés
- **WHEN** `ruff check` s'exécute
- **THEN** le job SHALL échouer avec les règles F401 (unused import), le développeur pouvant lancer `ruff check --fix` en local pour corriger

### Requirement: Le job `front` SHALL lint, type-checker, tester, builder et vérifier la taille du bundle
Le job `front` du workflow CI MUST exécuter dans l'ordre :
1. Checkout + `setup-node@v4` (Node 20, cache npm)
2. `cd pixel-lab/frontend && npm ci` (reproductible via `package-lock.json`)
3. `npm run lint` (ESLint — fail si erreurs)
4. `npm run type-check` (`vue-tsc --noEmit` — fail si erreurs TS)
5. `npm run test:coverage` (Vitest avec thresholds ≥ 50 % lines)
6. `npm run build` (Vite production build)
7. `npm run check:size` : script qui gzippe les chunks JS et fail si le plus gros dépasse 300 KB

L'artefact `frontend-dist/` (contenu du `dist/`) MUST être uploadé via `actions/upload-artifact` pour consommation par le job `e2e`.

#### Scenario: Bundle size regresse
- **GIVEN** une PR qui importe accidentellement `lodash` complet, faisant passer le chunk principal de 240 KB à 320 KB gzipped
- **WHEN** le job `front` exécute `npm run check:size`
- **THEN** le script SHALL exit 1 avec un message indiquant la taille observée et le seuil, la PR SHALL être bloquée

#### Scenario: Type-check TS strict
- **GIVEN** une PR avec `const x: number = someStore.activeImage` alors que `activeImage: string | null`
- **WHEN** `npm run type-check` s'exécute
- **THEN** `vue-tsc` SHALL signaler l'erreur TS2322, le job SHALL échouer

### Requirement: Le job `e2e` SHALL exécuter des scenarios Playwright sur la vraie app
Le job `e2e` MUST :
1. Dépendre de `back` ET `front` (via `needs:`) — pas d'e2e si l'un des deux est rouge
2. Télécharger l'artefact `frontend-dist` produit par `front`, le placer dans `pixel-lab/frontend-dist/`
3. Installer les deps Python minimales (pour le back) et Node (pour Playwright)
4. Installer les browsers Playwright : `npx playwright install --with-deps chromium`
5. Démarrer le back en background : `PIXEL_LAB_PROD=1 python pixel-lab/serve.py &`
6. Attendre `/healthz` 200 OK (timeout 30 s)
7. Lancer `cd pixel-lab/e2e && npx playwright test`
8. En cas d'échec : uploader `pixel-lab/e2e/playwright-report/` comme artefact (traces, vidéos, screenshots)

Les scenarios e2e minimaux qui DOIVENT exister et passer :
- Smoke : page boot, sidebar populée, pas d'erreur console
- Convert : upload + pipeline 2 étapes + run → vérifie `iter_NNN_*.png` créés
- Preview live : toggle ON + change param → image update + blob URL géré
- Bg detect : click détecter → overlay affiché

#### Scenario: E2E convert passe bit-à-bit
- **GIVEN** une image fixture `sprite_small.png` et un pipeline connu `[denoise/median, sharpen/unsharp_mask]`
- **WHEN** Playwright pilote le dashboard, click Lancer, attend `done`
- **THEN** les fichiers `outputs/sprite_small/iter_001_denoise_median.png` et `iter_002_sharpen_unsharp_mask.png` SHALL exister et SHALL être identiques bit-à-bit aux goldens `tests/fixtures/golden/denoise_sharpen/`

#### Scenario: Artefacts en cas d'échec e2e
- **GIVEN** un test Playwright qui échoue en CI
- **WHEN** le job se termine en erreur
- **THEN** un artefact `playwright-report/` SHALL être uploadé avec traces + vidéos + screenshots, téléchargeable depuis l'UI GitHub Actions pour debug post-mortem

### Requirement: Les dépendances SHALL être mises à jour automatiquement par Dependabot
Le dépôt MUST configurer `.github/dependabot.yml` avec :
- `package-ecosystem: npm` sur `pixel-lab/frontend`, schedule weekly
- `package-ecosystem: pip` sur `pixel-lab`, schedule weekly
- `package-ecosystem: github-actions` sur `/`, schedule weekly

Les PRs Dependabot MUST passer la même CI que les PRs humaines avant merge.

#### Scenario: Dependabot ouvre une PR
- **GIVEN** une nouvelle version patch d'une dépendance npm
- **WHEN** Dependabot exécute son scan hebdomadaire
- **THEN** une PR SHALL être ouverte automatiquement avec le diff du `package.json` + `package-lock.json`, et la CI SHALL l'exécuter normalement ; un mainteneur SHALL pouvoir merger si verte

### Requirement: Les tests pytest SHALL couvrir les scenarios des spec deltas OpenSpec
Chaque scenario défini dans les specs canoniques `pixel-art-conversion-api` et `pixel-art-dashboard` MUST avoir au moins un test automatisé correspondant (pytest côté back pour les scenarios de routes, Vitest ou Playwright côté front pour les scenarios d'UI). La correspondance MUST être documentée par un commentaire de test référençant la requirement et le scenario (ex. `# Spec: pixel-art-conversion-api § "Pipeline multi-étapes exécuté en-process"`).

#### Scenario: Scenario sans test identifié
- **GIVEN** un scenario de spec sans test correspondant (chercher par titre exact du scenario dans `tests/`)
- **WHEN** on lance un script de contrôle `scripts/check_spec_coverage.py` (à créer, out of scope V1 si jugé trop)
- **THEN** le script SHALL lister les scenarios orphelins — utilisé comme checklist à la revue manuelle en V1

### Requirement: Les fixtures de test SHALL être déterministes et versionnées
Les tests back qui dépendent de l'output exact d'un algorithme (bit-à-bit) MUST utiliser des fixtures PNG committées dans `pixel-lab/server_fastapi/tests/fixtures/inputs/` (inputs générés par seed fixe) et des goldens dans `pixel-lab/server_fastapi/tests/fixtures/golden/<scenario>/`. Les versions de `Pillow` et `numpy` MUST être pinnées dans `requirements.txt` pour garantir la reproductibilité.

Un script `tests/fixtures/regenerate.py` MUST exister pour recalculer les goldens quand une dépendance ou un algorithme change légitimement, avec un commentaire clair `# ⚠️ Reviewer: vérifier manuellement que les nouveaux goldens sont visuellement corrects avant merge.`

#### Scenario: Reproductibilité bit-à-bit
- **GIVEN** les fixtures committées et les versions pinnées
- **WHEN** deux contributeurs lancent `pytest tests/test_convert_happy_e2e.py` sur deux machines différentes
- **THEN** les deux runs SHALL produire les mêmes `iter_NNN_*.png` et les mêmes diffs `cmp` contre les goldens (exit 0)

#### Scenario: Régénération manuelle tracée
- **GIVEN** une mise à jour de `Pillow 10.3 → 10.4` qui modifie légèrement la sortie de l'unsharp mask
- **WHEN** un mainteneur lance `python tests/fixtures/regenerate.py`
- **THEN** les goldens SHALL être réécrits, le diff git SHALL être visible en revue, et le commit SHALL inclure une ligne de justification ("bump Pillow 10.4, regenerated goldens")
