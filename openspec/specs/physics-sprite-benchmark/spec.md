# physics-sprite-benchmark Specification

## Purpose
Définir un protocole de benchmark reproductible qui mesure, pour chaque moteur 2D candidat (Godot, Defold, Phaser), le nombre maximum de sprites affichables simultanément avec physique et collision actives sous des conditions identiques, jusqu'à ce que le FPS descende sous 20. Source de vérité : `plan-benchmark.md` et les projets `godot-benchmark/`, `defold-benchmark/`, `phaser-benchmark/`.

## Requirements

### Requirement: Les conditions de test SHALL être identiques pour les trois moteurs
Chaque benchmark MUST utiliser une résolution de 960 × 540 px, un sprite circulaire de 16 × 16 px généré procéduralement, un corps physique circulaire de rayon 8 px, une gravité nulle, un coefficient de rebond de 1.0, une friction nulle et quatre murs statiques pour contenir la scène.

#### Scenario: Configuration de la scène Godot
- **GIVEN** le projet `godot-benchmark/` exécuté dans Godot 4.6.2
- **WHEN** la scène principale se lance
- **THEN** le canvas SHALL mesurer 960 × 540 px et chaque sprite SHALL être un RigidBody2D circulaire de 8 px de rayon

#### Scenario: Configuration de la scène Defold
- **GIVEN** le projet `defold-benchmark/` exécuté dans Defold 1.12.3
- **WHEN** la collection `main` s'initialise
- **THEN** le canvas SHALL mesurer 960 × 540 px et chaque `ball.go` SHALL être un body Box2D circulaire de 8 px de rayon

#### Scenario: Configuration de la scène Phaser
- **GIVEN** `phaser-benchmark/index.html` servi sur localhost
- **WHEN** la scène Phaser 4 démarre
- **THEN** le canvas SHALL mesurer 960 × 540 px (ou 960 × 1080 pour les variantes, cf. `phaser4-benchmark-scenarios`) et chaque sprite SHALL utiliser Arcade Physics avec un corps circulaire

### Requirement: Les sprites SHALL être spawnés progressivement à 10 sprites par seconde
Le spawn MUST ajouter exactement 1 sprite toutes les 100 ms (soit 10/s) tant que la condition d'arrêt n'est pas atteinte. Chaque sprite reçoit une vitesse initiale aléatoire uniforme sur `[-200, +200]` px/s en X et en Y.

#### Scenario: Vitesse initiale
- **GIVEN** un nouveau sprite ajouté par le benchmark
- **WHEN** le sprite est instancié
- **THEN** ses composantes de vitesse `vx` et `vy` SHALL être tirées uniformément sur `[-200, 200]` px/s

### Requirement: Les collisions SHALL inclure sprite↔sprite et sprite↔murs
Chaque sprite MUST collisionner avec les autres sprites et avec les quatre murs de la scène.

#### Scenario: Collision inter-sprites active
- **GIVEN** deux sprites en route de collision
- **WHEN** ils se rencontrent
- **THEN** ils SHALL rebondir élastiquement (coefficient de restitution 1.0) sans perte de vitesse

### Requirement: Le test SHALL s'arrêter automatiquement quand le FPS passe sous 20 avec au moins 50 sprites
La condition d'arrêt MUST combiner un FPS instantané strictement inférieur à 20 et un nombre de sprites actifs strictement supérieur à 50 pour éviter les arrêts prématurés pendant les premières secondes.

#### Scenario: Arrêt déclenché
- **GIVEN** 1 200 sprites actifs et un FPS instantané de 18
- **WHEN** la boucle de jeu évalue la condition d'arrêt
- **THEN** le benchmark SHALL stopper le spawn, figer la scène et exposer `{sprites, fps, stopped: true}`

#### Scenario: FPS bas au démarrage ignoré
- **GIVEN** 20 sprites actifs et un FPS de 15 (pic au chargement)
- **WHEN** la boucle évalue la condition d'arrêt
- **THEN** le benchmark SHALL continuer le spawn car la condition `sprites > 50` n'est pas satisfaite

### Requirement: Les résultats SHALL être exposés via un HUD rouge ou une variable JS
Chaque moteur MUST afficher le nombre de sprites actifs et le FPS courant dans un HUD en rouge lisible, et (pour Phaser et Defold) exposer un objet `window.benchmarkResult` contenant au minimum `{sprites, fps, stopped}`.

#### Scenario: HUD rouge pour Godot
- **GIVEN** Godot 4.6.2 exécutant le benchmark
- **WHEN** le test est en cours
- **THEN** le HUD SHALL afficher en rouge vif (R>180, G<60, B<60) le nombre de sprites et le FPS

#### Scenario: Objet window.benchmarkResult pour Phaser
- **GIVEN** Phaser 4.0.0 exécutant le benchmark
- **WHEN** la condition d'arrêt est atteinte
- **THEN** `window.benchmarkResult` SHALL contenir `{sprites, fps, stopped: true}`

#### Scenario: Objet window.defoldResult pour Defold
- **GIVEN** Defold 1.12.3 exécutant le benchmark (build HTML5)
- **WHEN** la condition d'arrêt est atteinte
- **THEN** le script Lua SHALL appeler `html5.run_javascript` pour assigner `window.defoldResult = {sprites, fps, stopped: true}`

### Requirement: La référence de performance Phaser 4 baseline SHALL être 8 950 sprites @ 17 FPS
Le document MUST consigner le résultat de référence déjà exécuté pour Phaser 4 en mode standard (Arcade Physics, collision sprite↔sprite + sprite↔murs).

#### Scenario: Référence documentée
- **GIVEN** le plan de benchmark validé
- **WHEN** on consulte la section Bench 1 de `plan-benchmarks-phaser4.md`
- **THEN** le résultat baseline SHALL être explicitement "8 950 sprites @ 17 FPS" avec 60 FPS stable jusqu'à environ 5 000 sprites
