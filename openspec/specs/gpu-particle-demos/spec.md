# gpu-particle-demos Specification

## Purpose
Offrir un ensemble de six démos PixiJS interactives qui illustrent le rendu GPU batché via `ParticleContainer` (un seul draw call par frame) et couvrent des cas d'usage variés : débris, atmosphérique, IA flocking, effets additifs, ambiances saisonnières et rendu style SNES. Source de vérité : `index.html` et les fichiers `1-debris-explosion.html` → `6-saisons-snes.html`.

## Requirements

### Requirement: La page d'accueil SHALL lister exactement six démos
`index.html` MUST proposer une grille de six cartes cliquables, chacune pointant vers une démo : Débris & Explosions, Neige & Feuilles mortes, Boids, Particules Massives, 4 Saisons, 4 Saisons SNES.

#### Scenario: Cartes présentes
- **GIVEN** `index.html` ouvert dans un navigateur
- **WHEN** on inspecte le DOM
- **THEN** on SHALL trouver six éléments `<a class="card">` avec les liens relatifs `1-debris-explosion.html`, `2-neige-feuilles.html`, `3-boids.html`, `4-particules-feu.html`, `5-quatre-saisons.html`, `6-saisons-snes.html`

### Requirement: Toutes les démos SHALL utiliser PixiJS 7 avec ParticleContainer pour un unique draw call
Chaque démo MUST reposer sur PixiJS 7, WebGL et `ParticleContainer`, et réaliser un seul draw call GPU par frame pour l'ensemble des sprites.

#### Scenario: Draw call unique
- **GIVEN** une démo affichant des milliers de sprites
- **WHEN** on inspecte les statistiques WebGL (ex. via Spector.js)
- **THEN** le rendu du `ParticleContainer` SHALL compter exactement 1 draw call par frame, indépendamment du nombre de sprites

### Requirement: La démo Débris SHALL supporter jusqu'à 80 000 sprites avec gravité et pooling
La démo `1-debris-explosion.html` MUST permettre à l'utilisateur de cliquer pour créer des explosions de ~350 fragments chacune, avec gravité, rebond et friction, et SHALL tolérer environ 80 000 sprites simultanés grâce à un object pooling.

#### Scenario: Clic déclenche une explosion
- **GIVEN** la démo ouverte
- **WHEN** l'utilisateur clique sur le canvas
- **THEN** au moins 350 fragments SHALL être spawnés à la position du clic avec des vecteurs de vélocité aléatoires

#### Scenario: Rafale continue
- **GIVEN** l'utilisateur maintient le clic enfoncé
- **WHEN** la démo est active
- **THEN** des explosions SHALL être générées en continu jusqu'à atteindre approximativement le plafond documenté de 80 000 sprites

### Requirement: La démo Neige & Feuilles SHALL stabiliser 5 000 particules atmosphériques
La démo `2-neige-feuilles.html` MUST maintenir 5 000 particules en mouvement perpétuel, avec vent oscillant et variation de profondeur, et proposer un basculement entre neige et feuilles d'automne.

#### Scenario: Bascule neige ↔ feuilles
- **GIVEN** la démo active en mode neige
- **WHEN** l'utilisateur déclenche la bascule
- **THEN** le thème SHALL passer aux feuilles mortes sans recharger la page

### Requirement: La démo Boids SHALL simuler 2 000 agents avec grille spatiale O(n·k)
La démo `3-boids.html` MUST implémenter les trois règles de flocking de Craig Reynolds (séparation, alignement, cohésion) sur 2 000 agents et utiliser une grille spatiale pour ramener la complexité du voisinage à O(n·k).

#### Scenario: Interaction souris
- **GIVEN** la démo en cours
- **WHEN** l'utilisateur actionne l'interaction souris
- **THEN** trois modes au minimum SHALL être disponibles : attirer, repousser, disperser

### Requirement: La démo Particules Massives SHALL afficher 18 000 sprites en blending additif
La démo `4-particules-feu.html` MUST gérer 18 000 particules en blend-additif avec turbulence procédurale, rampe de couleur et object pooling, et proposer au moins les modes Feu, Plasma, Blizzard et Multi-sources.

#### Scenario: Sélection d'un mode
- **GIVEN** la démo active en mode Feu
- **WHEN** l'utilisateur sélectionne le mode Plasma
- **THEN** la rampe de couleur SHALL s'adapter sans recharger la page et le blending additif SHALL rester actif

### Requirement: La démo 4 Saisons SHALL faire transiter 6 000 particules entre quatre ambiances
La démo `5-quatre-saisons.html` MUST faire évoluer 6 000 particules selon la saison : pétales (printemps), lucioles (été), feuilles mortes (automne), flocons (hiver), avec une transition de fond automatique ou navigation libre.

#### Scenario: Transition automatique
- **GIVEN** la démo en mode automatique
- **WHEN** un temps défini s'écoule
- **THEN** la saison active SHALL changer et les particules SHALL être remplacées progressivement par celles de la saison suivante

### Requirement: La démo SNES SHALL rendre à 256×224 avec pixel art et effets CRT
La démo `6-saisons-snes.html` MUST rendre à la résolution native Super Nintendo 256 × 224, appliquer un scaling CSS `image-rendering: pixelated`, utiliser une palette 15-bit authentique, des sprites 8 × 8 pixel art, ajouter scanlines et vignette CRT, et réaliser un fondu au noir entre saisons.

#### Scenario: Résolution et palette
- **GIVEN** la démo SNES active
- **WHEN** on inspecte le canvas PixiJS
- **THEN** sa résolution interne SHALL être 256 × 224 et le CSS SHALL appliquer `image-rendering: pixelated`

#### Scenario: Fondu au noir entre saisons
- **GIVEN** une transition entre deux saisons
- **WHEN** le changement s'amorce
- **THEN** l'écran SHALL faire un fondu au noir, puis révéler la saison suivante avec ses nouveaux sprites
