# Plan de benchmarks Phaser 4 — Multi-configuration

## Objectif

Mesurer les performances de Phaser 4.0.0 sous différentes configurations de rendu et d'architecture pour déterminer les limites et les meilleures pratiques selon le cas d'usage (sprites interactifs avec physique vs décor massif).

## Vue d'ensemble des benchmarks

| # | Nom | Ce qu'on mesure | Physique | Collision |
|---|-----|-----------------|----------|-----------|
| 1 | **Standard (baseline)** | Rendu standard + Arcade Physics | Oui | balle↔balle + murs |
| 2 | **Config optimisée** | Standard avec batchSize, powerPreference, maxTextures | Oui | balle↔balle + murs |
| 3 | **Standard sans collision inter-sprites** | Standard mais collision murs seulement (pas balle↔balle) | Oui | murs uniquement |
| 4 | **SpriteGPULayer** | Rendu GPU massif, sans physique | Non | Non |
| 5 | **bitECS direct** | Utiliser les Systems bitECS internes pour la boucle de mise à jour | Oui | murs uniquement |

## Paramètres communs

- **Sprite** : cercle 4×4 px (rayon 2), couleur `0x4db3ff`
- **Canvas** : 960 × 1080 px
- **Gravité** : 0
- **Vitesse initiale** : aléatoire [-200, +200] px/s sur X et Y
- **Spawn rate** : 500/s (50 balles × 100ms via setInterval)
- **Stop** : FPS < 20 avec > 100 sprites actifs
- **Données collectées** : {sprites, fps, elapsed} tous les 200 sprites
- **Exécution** : injection JS via Chrome (CDN Phaser)
- **Nettoyage** : `game.destroy(true)` automatique au stop

## Détail par benchmark

### Bench 1 — Standard (baseline) ✅ FAIT

Déjà exécuté. Résultat : **8 950 sprites @ 17 FPS**. 60 FPS stables jusqu'à ~5 000 sprites. Sert de référence pour tous les autres tests.

Config Phaser :
```javascript
{ type: Phaser.AUTO, physics: { default: 'arcade' } }
// Collision : balls↔balls + balls↔worldBounds
```

### Bench 2 — Config optimisée

Même test que le baseline mais avec les paramètres de rendu WebGL poussés.

Config Phaser :
```javascript
{
  type: Phaser.WEBGL,
  render: {
    batchSize: 16384,        // max quads par batch (défaut: 4096 → on pousse à 16384)
    powerPreference: 'high-performance',  // demander le GPU discret
    maxTextures: -1,          // utiliser toutes les unités de texture
    mipmapFilter: 'NEAREST',  // pas de mipmap pour des sprites 4px
  },
  physics: { default: 'arcade' }
}
```

**Hypothèse** : gain modeste (5-15%) car le goulot est la collision O(n²), pas le rendu.

### Bench 3 — Standard sans collision inter-sprites

Même chose que le baseline mais SANS `physics.add.collider(balls, balls)`. Les balles traversent les autres balles, ne rebondissent que sur les murs.

```javascript
// PAS de : this.physics.add.collider(this.balls, this.balls);
// Seulement : ball.setCollideWorldBounds(true);
```

**Hypothèse** : gain majeur (2-5×) car on supprime le broadphase O(n²). Permet d'isoler le coût du rendu vs le coût de la physique.

### Bench 4 — SpriteGPULayer (rendu pur)

Pas de physique, pas de collision. On ajoute des sprites dans un SpriteGPULayer et on mesure le FPS.

```javascript
const layer = this.add.spriteGPULayer('ball', maxCapacity);
// Ajout de membres au layer
for (let i = 0; i < batchToAdd; i++) {
  layer.add({ x, y, scaleX: 1, scaleY: 1 });
}
```

**Particularité** : le spawn rate est beaucoup plus élevé (5 000-10 000/s) car on attend des centaines de milliers de sprites. Le stop est relevé à FPS < 30 au lieu de 20 pour être plus exigeant.

**Hypothèse** : 100 000+ sprites avant le drop, potentiellement 500 000+ selon le GPU.

### Bench 5 — bitECS direct (Systems natifs)

Phaser 4 utilise bitECS en interne. Au lieu de passer par les Game Objects standard (Sprite, Group), on utilise directement les composants et systèmes bitECS pour gérer position/vélocité, et un simple rendu via Graphics ou SpriteGPULayer.

```javascript
import { defineComponent, defineQuery, defineSystem, addEntity, addComponent } from 'bitecs';

const Position = defineComponent({ x: Types.f32, y: Types.f32 });
const Velocity = defineComponent({ vx: Types.f32, vy: Types.f32 });

const movementSystem = defineSystem((world) => {
  const ents = defineQuery([Position, Velocity])(world);
  for (const eid of ents) {
    Position.x[eid] += Velocity.vx[eid] * dt;
    Position.y[eid] += Velocity.vy[eid] * dt;
    // Rebond sur les murs
    if (Position.x[eid] < 2 || Position.x[eid] > 958) Velocity.vx[eid] *= -1;
    if (Position.y[eid] < 2 || Position.y[eid] > 1078) Velocity.vy[eid] *= -1;
  }
});
```

**Hypothèse** : gain significatif vs Standard sans collision car les Typed Arrays de bitECS sont cache-friendly (SoA vs AoS). Le rendu reste le même.

## Architecture du script paramétrable

Un seul script JS injecté dans Chrome, piloté par un objet de config :

```javascript
const BENCH_CONFIG = {
  name: 'standard-baseline',     // identifiant unique
  spriteSize: 4,                  // taille du sprite en px
  canvasW: 960,
  canvasH: 1080,
  spawnRate: 500,                 // sprites/seconde
  spawnBatch: 50,                 // sprites par tick
  tickInterval: 100,              // ms entre chaque tick
  stopFps: 20,                    // FPS seuil pour arrêter
  stopMinSprites: 100,            // minimum de sprites avant de checker le FPS
  logEvery: 200,                  // log tous les N sprites
  renderer: 'auto',              // 'auto' | 'webgl'
  renderConfig: {},               // options render: batchSize, powerPreference...
  physicsEnabled: true,           // activer Arcade Physics
  ballCollision: true,            // collision balle↔balle
  useSpriteGPULayer: false,       // utiliser SpriteGPULayer au lieu de Sprite standard
  useBitECS: false,               // mode bitECS direct
  destroyOnStop: true,            // game.destroy(true) automatique
};
```

Chaque benchmark = un preset de `BENCH_CONFIG`. Le script :
1. Charge Phaser depuis CDN (si pas déjà chargé)
2. Crée le Game avec la config appropriée
3. Lance le spawn via setInterval
4. Collecte les données dans `window.benchmarkLog`
5. Au stop, écrit `window.benchmarkResult` et détruit le jeu
6. On lit les résultats via `javascript_tool`

## Ordre d'exécution

1. **Bench 3** (sans collision) — rapide, isole le coût de la collision
2. **Bench 2** (config optimisée) — compare au baseline
3. **Bench 4** (SpriteGPULayer) — le test de rendu massif
4. **Bench 5** (bitECS) — le test d'architecture ECS

Le Bench 1 est déjà fait et sert de référence.

## Livrables

- `benchmark-results/phaser4-*.md` : un fichier .md par benchmark avec données brutes
- `benchmark-results/dashboard-phaser4.html` : dashboard HTML interactif avec :
  - Courbes FPS/sprites superposées pour tous les benchmarks
  - Tableau comparatif des résultats finaux
  - Filtres pour afficher/masquer chaque benchmark
  - Généré à partir des données collectées

## Risques et limites

- **SpriteGPULayer** : pas de physique intégrée, le test mesure le rendu pur uniquement
- **bitECS direct** : l'API interne de Phaser 4 pour bitECS n'est peut-être pas exposée publiquement, il faudra peut-être charger bitECS séparément depuis CDN
- **Chrome Cowork** : le GPU disponible dépend de la machine de l'utilisateur, les résultats ne sont pas reproductibles cross-machine
- **setInterval throttling** : Chrome peut throttle les timers si l'onglet passe en arrière-plan
