# Résultats Benchmark — Phaser 4.0.0 — SpriteGPULayer animé (mouvement)

## Configuration

- **Moteur** : Phaser 4.0.0 (SpriteGPULayer)
- **Renderer** : Phaser.WEBGL
- **Sprite** : cercle 6×6 px, 8 couleurs différentes (8 layers GPU)
- **Résolution** : 960 × 1080 px
- **Physique** : AUCUNE
- **Animation GPU** : position x/y aller-retour (yoyo), alpha oscillant
- **Easing** : Sine, Quad, Cubic, Quart, Circ, Back, Bounce, Linear (1 par couleur)
- **Spawn rate** : ~20 000/s (500 × 8 layers × 200ms)
- **Stop** : FPS < 20 avec > 5000 sprites
- **Date** : 2026-04-18

## Résultat final

- **Sprites au stop** : 480 000
- **FPS au stop** : 19
- **Durée du test** : 25.2s

## Courbe FPS / Sprites

| Sprites | FPS | Temps (s) |
|---------|-----|-----------|
| 20 000 | 59 | 2.2 |
| 40 000 | 55 | 3.2 |
| 60 000 | 53 | 4.2 |
| 80 000 | 52 | 5.2 |
| 100 000 | 54 | 6.2 |
| 120 000 | 55 | 7.2 |
| 140 000 | 56 | 8.2 |
| 160 000 | 56 | 9.2 |
| 180 000 | 52 | 10.2 |
| 200 000 | 49 | 11.2 |
| 220 000 | 46 | 12.2 |
| 240 000 | 43 | 13.2 |
| 260 000 | 40 | 14.2 |
| 280 000 | 37 | 15.2 |
| 300 000 | 33 | 16.2 |
| 320 000 | 31 | 17.2 |
| 340 000 | 29 | 18.2 |
| 360 000 | 27 | 19.2 |
| 380 000 | 26 | 20.2 |
| 400 000 | 24 | 21.2 |
| 420 000 | 23 | 22.2 |
| 440 000 | 21 | 23.2 |
| 460 000 | 20 | 24.2 |
| **480 000** | **19** | **25.2** |

## Analyse

- **~55 FPS** jusqu'à 160 000 sprites (phase de montée puis plateau)
- **Dégradation linéaire** de 180 000 à 480 000 (52 → 19 FPS)
- Les animations GPU (yoyo position + alpha) consomment environ **6× plus** que les sprites statiques (480K animés vs 2,8M statiques)
- Malgré cela, **480 000 sprites animés** est massif — c'est **54× plus** que le rendu standard avec physique (8 950)

## Syntaxe d'animation GPU découverte

```javascript
layer.addMember({
  x: { base: 480, amplitude: 200, duration: 3000, ease: 'Sine', yoyo: true },
  y: { base: 540, amplitude: 150, duration: 4000, ease: 'Sine', yoyo: true },
  alpha: { base: 0.7, amplitude: 0.3, duration: 2400, ease: 'Sine', yoyo: true },
});
```

Chaque propriété (x, y, rotation, scaleX, scaleY, alpha) peut être un objet avec `base`, `amplitude`, `duration`, `ease` et `yoyo`. L'animation est entièrement calculée par le GPU dans le vertex shader.

## Comparaison GPU Layer : statique vs animé

| Mode | Sprites max | FPS stable jusqu'à |
|------|-------------|---------------------|
| Statique (pas d'anim) | 2 790 000+ (arrêt manuel) | ~310 000 |
| Animé (position + alpha yoyo) | 480 000 | ~160 000 |
