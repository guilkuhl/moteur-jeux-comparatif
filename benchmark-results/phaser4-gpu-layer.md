# Résultats Benchmark — Phaser 4.0.0 — SpriteGPULayer (rendu massif)

## Configuration

- **Moteur** : Phaser 4.0.0 (SpriteGPULayer)
- **Renderer** : Phaser.WEBGL
- **Sprite** : cercle 4×4 px (rayon 2)
- **Résolution** : 960 × 1080 px
- **Physique** : AUCUNE
- **Collision** : AUCUNE
- **Spawn rate** : ~25 000/s (5 000 × 200ms)
- **Stop** : FPS < 20 (jamais atteint — arrêt manuel à 2 790 000 sprites)
- **Date** : 2026-04-18

## Résultat final

- **Sprites à l'arrêt manuel** : 2 790 000
- **FPS à l'arrêt** : 39
- **Durée du test** : 111.6s
- **Note** : le FPS n'est jamais descendu sous 38, arrêt manuel

## Courbe FPS / Sprites

| Sprites | FPS | Temps (s) |
|---------|-----|-----------|
| 10 000 | 60 | 0.4 |
| 110 000 | 60 | 4.4 |
| 210 000 | 60 | 8.4 |
| 310 000 | 60 | 12.4 |
| 410 000 | 55 | 16.4 |
| 510 000 | 46 | 20.4 |
| 610 000 | 41 | 24.4 |
| 710 000 | 39 | 28.4 |
| 810 000 | 39 | 32.4 |
| 910 000 | 39 | 36.4 |
| 1 010 000 | 38 | 40.4 |
| 1 110 000 | 38 | 44.4 |
| 1 210 000 | 38 | 48.4 |
| 1 310 000 | 38 | 52.4 |
| 1 410 000 | 38 | 56.4 |
| 1 510 000 | 38 | 60.4 |
| 1 610 000 | 39 | 64.4 |
| 1 710 000 | 39 | 68.4 |
| 1 810 000 | 39 | 72.4 |
| 1 910 000 | 39 | 76.4 |
| 2 010 000 | 39 | 80.4 |
| 2 110 000 | 39 | 84.4 |
| 2 210 000 | 39 | 88.4 |
| 2 310 000 | 39 | 92.4 |
| 2 410 000 | 39 | 96.4 |
| 2 510 000 | 38 | 100.4 |
| 2 610 000 | 38 | 104.4 |
| 2 710 000 | 39 | 108.4 |
| **2 790 000** | **39** | **111.6** |

## Analyse

- **60 FPS stables** jusqu'à ~310 000 sprites
- **Dégradation douce** de 310 000 à 710 000 (60 → 39 FPS)
- **Plateau stable à 38-39 FPS** de 710 000 à 2 790 000 sprites — le FPS ne baisse plus !
- Le GPU est le goulot (fillrate), pas le CPU ni les draw calls (1 seul draw call)
- **310× plus de sprites** que le rendu standard avec physique (8 950)
- **212× plus de sprites** que le rendu standard sans collision (13 250)

## Conclusion

SpriteGPULayer est extraordinairement efficace pour le rendu de masse. Avec 2,8 millions de sprites statiques à 39 FPS, c'est la solution idéale pour les décors, particules, fonds animés. Le plafond n'est pas le nombre de sprites mais le fillrate GPU (combien de pixels le GPU peut rasteriser par frame).
