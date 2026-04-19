# Résultats Benchmark — Phaser 4.0.0 — Sans collision inter-sprites

## Configuration

- **Moteur** : Phaser 4.0.0 (Arcade Physics)
- **Sprite** : cercle 4×4 px (rayon 2)
- **Résolution** : 960 × 1080 px
- **Physique** : rebond murs uniquement, PAS de collision balle↔balle
- **Spawn rate** : ~500/s
- **Stop** : FPS < 20 avec > 100 sprites
- **Date** : 2026-04-18

## Résultat final

- **Sprites au stop** : 13 250
- **FPS au stop** : 18
- **Durée du test** : 28.4s

## Courbe FPS / Sprites

| Sprites | FPS | Temps (s) |
|---------|-----|-----------|
| 500 | 60 | 1.0 |
| 1000 | 60 | 2.0 |
| 1500 | 60 | 3.0 |
| 2000 | 60 | 4.0 |
| 2500 | 60 | 5.0 |
| 3000 | 60 | 6.0 |
| 3500 | 60 | 7.0 |
| 4000 | 60 | 8.0 |
| 4500 | 60 | 9.0 |
| 5000 | 60 | 10.0 |
| 5500 | 60 | 11.0 |
| 6000 | 60 | 12.0 |
| 6500 | 60 | 13.0 |
| 7000 | 60 | 14.0 |
| 7500 | 60 | 15.0 |
| 8000 | 60 | 16.0 |
| 8500 | 60 | 17.0 |
| 9000 | 60 | 18.0 |
| 9500 | 60 | 19.0 |
| 10000 | 58 | 20.0 |
| 10500 | 54 | 21.0 |
| 11000 | 49 | 22.0 |
| 11500 | 45 | 23.0 |
| 12000 | 40 | 24.1 |
| 12500 | 30 | 25.6 |
| 13000 | 21 | 27.3 |
| **13250** | **18** | **28.4** |

## Analyse

- **60 FPS stables** jusqu'à ~9 500 sprites (19s) — presque 2× le baseline (5 000)
- **Début de dégradation** à 10 000 sprites (58 FPS)
- **Chute progressive** de 10 000 à 13 250 (58 → 18 FPS)
- **+48% de sprites** vs baseline (13 250 vs 8 950)

La collision balle↔balle (O(n²)) coûtait donc environ 4 500 sprites de marge. Le goulot restant est le rendu + la mise à jour physique par sprite (collideWorldBounds, vélocité).
