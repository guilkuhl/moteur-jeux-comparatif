# Résultats Benchmark — Phaser 4.0.0 — Config WebGL optimisée

## Configuration

- **Moteur** : Phaser 4.0.0 (Arcade Physics)
- **Renderer** : Phaser.WEBGL forcé
- **Sprite** : cercle 4×4 px (rayon 2)
- **Résolution** : 960 × 1080 px
- **Physique** : collision balle↔balle + murs (identique au baseline)
- **Config rendu** : batchSize=16384, powerPreference=high-performance, maxTextures=-1, mipmapFilter=NEAREST, roundPixels=false
- **Spawn rate** : ~500/s
- **Stop** : FPS < 20 avec > 100 sprites
- **Date** : 2026-04-18

## Résultat final

- **Sprites au stop** : 7 350
- **FPS au stop** : 19
- **Durée du test** : 17.7s

## Courbe FPS / Sprites

| Sprites | FPS | Temps (s) |
|---------|-----|-----------|
| 200 | 60 | 0.4 |
| 400 | 60 | 0.8 |
| 600 | 60 | 1.2 |
| 800 | 60 | 1.6 |
| 1000 | 60 | 2.0 |
| 1200 | 60 | 2.4 |
| 1400 | 60 | 2.8 |
| 1600 | 60 | 3.2 |
| 1800 | 60 | 3.6 |
| 2000 | 60 | 4.0 |
| 2200 | 60 | 4.4 |
| 2400 | 60 | 4.8 |
| 2600 | 60 | 5.2 |
| 2800 | 60 | 5.6 |
| 3000 | 60 | 6.0 |
| 3200 | 60 | 6.4 |
| 3400 | 60 | 6.8 |
| 3600 | 60 | 7.2 |
| 3800 | 60 | 7.6 |
| 4000 | 60 | 8.0 |
| 4200 | 60 | 8.4 |
| 4400 | 60 | 8.8 |
| 4600 | 60 | 9.2 |
| 4800 | 60 | 9.6 |
| 5000 | 60 | 10.0 |
| 5200 | 60 | 10.4 |
| 5400 | 60 | 10.8 |
| 5600 | 59 | 11.2 |
| 5800 | 59 | 11.7 |
| 6000 | 59 | 12.0 |
| 6200 | 53 | 12.4 |
| 6400 | 53 | 13.0 |
| 6600 | 45 | 13.7 |
| 6800 | 36 | 14.4 |
| 7000 | 36 | 15.3 |
| 7200 | 23 | 16.6 |
| **7350** | **19** | **17.7** |

## Analyse

- **60 FPS stables** jusqu'à ~5 400 sprites — similaire au baseline (5 000)
- **Chute plus brutale** que le baseline : 59→53→45→36→23→19 entre 5 600 et 7 350
- **Résultat inférieur au baseline** : 7 350 vs 8 950 (-18%)
- Le forçage de `Phaser.WEBGL` et `batchSize: 16384` n'apporte pas de gain mesurable
- La légère baisse peut être due à la variabilité système ou au batchSize trop élevé qui augmente l'empreinte mémoire GPU

## Conclusion

Les paramètres de config WebGL avancés n'améliorent pas les performances quand le goulot est la physique Arcade (collision O(n²)). Phaser 4 est déjà bien optimisé par défaut pour ce scénario.
