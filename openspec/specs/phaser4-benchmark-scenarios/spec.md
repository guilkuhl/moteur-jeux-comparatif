# phaser4-benchmark-scenarios Specification

## Purpose
Définir les cinq configurations de benchmark paramétrables pour Phaser 4.0.0 afin d'isoler successivement le coût du rendu, de la collision inter-sprites, de la configuration WebGL, du SpriteGPULayer et de l'architecture bitECS. Source de vérité : `plan-benchmarks-phaser4.md` et `phaser-benchmark/`.

## Requirements

### Requirement: Les paramètres communs SHALL être partagés par tous les scénarios
Tout scénario Phaser 4 MUST utiliser : sprite cercle 4 × 4 px (rayon 2, couleur `0x4db3ff`), canvas 960 × 1080 px, gravité nulle, vitesse initiale aléatoire sur `[-200, +200]` px/s, spawn rate 500/s (50 sprites par tick de 100 ms), condition d'arrêt `fps < 20 && sprites > 100`, logging toutes les 200 sprites et `game.destroy(true)` automatique au stop.

#### Scenario: Objet BENCH_CONFIG
- **GIVEN** le script paramétrable injecté via Chrome DevTools
- **WHEN** on instancie `BENCH_CONFIG`
- **THEN** les champs `spriteSize: 4`, `canvasW: 960`, `canvasH: 1080`, `spawnRate: 500`, `spawnBatch: 50`, `tickInterval: 100`, `stopFps: 20`, `stopMinSprites: 100`, `logEvery: 200`, `destroyOnStop: true` SHALL être présents avec exactement ces valeurs par défaut

#### Scenario: Nettoyage après stop
- **GIVEN** un scénario qui atteint la condition d'arrêt
- **WHEN** `destroyOnStop` vaut `true`
- **THEN** le runner SHALL appeler `game.destroy(true)` puis écrire `window.benchmarkResult` avant de rendre la main

### Requirement: Le Bench 1 (baseline) SHALL être la référence documentée à 8 950 sprites
Le scénario "Standard (baseline)" MUST utiliser `{ type: Phaser.AUTO, physics: { default: 'arcade' } }`, activer les collisions balle↔balle ET balle↔murs et servir de référence historique pour tous les autres scénarios.

#### Scenario: Résultat de référence
- **GIVEN** le baseline déjà exécuté
- **WHEN** on lit la section Bench 1 de `plan-benchmarks-phaser4.md`
- **THEN** le document SHALL indiquer "8 950 sprites @ 17 FPS", 60 FPS stable jusqu'à environ 5 000 sprites, et marquer ce bench comme ✅ FAIT

### Requirement: Le Bench 2 (config optimisée) SHALL pousser les paramètres WebGL
Le scénario "Config optimisée" MUST reprendre la baseline mais forcer `type: Phaser.WEBGL` et surcharger `render: { batchSize: 16384, powerPreference: 'high-performance', maxTextures: -1, mipmapFilter: 'NEAREST' }`.

#### Scenario: Rendu WebGL forcé
- **GIVEN** le scénario optimisé
- **WHEN** le jeu démarre
- **THEN** `game.config.renderType` SHALL valoir `Phaser.WEBGL` et `game.renderer.batchSize` SHALL valoir 16 384

### Requirement: Le Bench 3 (sans collision inter-sprites) SHALL supprimer le collider balles↔balles
Le scénario "Standard sans collision inter-sprites" MUST conserver `setCollideWorldBounds(true)` mais NE PAS appeler `this.physics.add.collider(this.balls, this.balls)`.

#### Scenario: Comportement attendu
- **GIVEN** deux balles en route de collision
- **WHEN** elles se rencontrent
- **THEN** elles SHALL se traverser sans rebondir, et seules les collisions avec les murs SHALL être actives

#### Scenario: Hypothèse de gain
- **GIVEN** la baseline à 8 950 sprites
- **WHEN** on exécute Bench 3
- **THEN** le document SHALL documenter une hypothèse de gain de 2× à 5× car on supprime le broadphase O(n²)

### Requirement: Le Bench 4 (SpriteGPULayer) SHALL mesurer le rendu pur sans physique
Le scénario "SpriteGPULayer" MUST ajouter les sprites via `this.add.spriteGPULayer('ball', maxCapacity)`, désactiver la physique et les collisions, relever le seuil d'arrêt à `fps < 30` et utiliser un spawn rate de 5 000 à 10 000 sprites/s.

#### Scenario: Ajout d'un membre de layer
- **GIVEN** un `SpriteGPULayer` initialisé avec une capacité max
- **WHEN** le spawn ajoute un batch
- **THEN** chaque ajout SHALL utiliser `layer.add({ x, y, scaleX: 1, scaleY: 1 })` et aucune collision SHALL être configurée

#### Scenario: Hypothèse de plafond
- **GIVEN** un GPU moderne
- **WHEN** le Bench 4 est exécuté
- **THEN** le document SHALL documenter une hypothèse de 100 000+ sprites, potentiellement 500 000+ selon le GPU

### Requirement: Le Bench 5 (bitECS direct) SHALL utiliser composants et systèmes bitECS
Le scénario "bitECS direct" MUST définir des composants `Position` et `Velocity` via `defineComponent` avec des types `f32`, utiliser `defineQuery` / `defineSystem` pour la boucle de mise à jour, et rebondir sur les murs en inversant la vélocité.

#### Scenario: Système de mouvement
- **GIVEN** un `movementSystem` défini via `defineSystem`
- **WHEN** le système s'exécute pour une entité
- **THEN** il SHALL mettre à jour `Position.x[eid] += Velocity.vx[eid] * dt` et `Position.y[eid] += Velocity.vy[eid] * dt`, puis inverser `vx` si `x < 2` ou `x > 958`, et `vy` si `y < 2` ou `y > 1078`

### Requirement: Les scénarios SHALL être exécutés dans l'ordre Bench 3 → 2 → 4 → 5
L'opérateur MUST exécuter d'abord Bench 3 (le plus rapide, isole le coût de la collision), puis Bench 2 (comparaison à la baseline), puis Bench 4 (rendu massif), puis Bench 5 (architecture ECS). Le Bench 1 est déjà exécuté et sert de référence.

#### Scenario: Ordre documenté
- **GIVEN** la section "Ordre d'exécution" de `plan-benchmarks-phaser4.md`
- **WHEN** on planifie une session de test
- **THEN** l'ordre SHALL être exactement : Bench 3, Bench 2, Bench 4, Bench 5

### Requirement: Chaque scénario SHALL produire un fichier .md et alimenter un dashboard HTML
Le livrable MUST inclure `benchmark-results/phaser4-<nom>.md` (données brutes) pour chaque scénario, plus `benchmark-results/dashboard-phaser4.html` avec les courbes FPS/sprites superposées, un tableau comparatif et des filtres par benchmark.

#### Scenario: Dashboard interactif
- **GIVEN** les cinq scénarios exécutés
- **WHEN** on ouvre `benchmark-results/dashboard-phaser4.html`
- **THEN** la page SHALL afficher les courbes superposées, un tableau des résultats finaux et une UI de filtrage par benchmark
