# Plan de benchmark — Sprites avec physique et collision

## Objectif

Mesurer pour chaque moteur/framework le nombre maximum de sprites affichables à l'écran avec physique et collision active, et observer la dégradation du FPS au fur et à mesure.

## Moteurs testés

- Defold 1.12.3 (Box2D intégré, Lua)
- Godot 4.6.2 (Godot Physics 2D, GDScript)
- Phaser 4.0.0 (Arcade Physics, JavaScript)

## Protocole de test

### Conditions identiques pour les 3 moteurs

- Résolution : 960 × 540 px
- Sprite : cercle 16 × 16 px (généré procéduralement, identique partout)
- Physique : chaque sprite a un body circulaire (rayon 8 px) avec collision active
- Gravité : aucune (0, 0) — les sprites rebondissent librement
- Rebond : coefficient 1.0 (élastique), friction 0
- Murs : 4 murs statiques autour de l'écran pour contenir les sprites
- Collision : sprite ↔ sprite + sprite ↔ murs
- Vitesse initiale : aléatoire entre -200 et +200 px/s sur X et Y

### Spawn progressif

- 10 sprites par seconde (1 toutes les 100 ms)
- Le test continue tant que le FPS reste ≥ 20
- Quand le FPS descend sous 20 avec plus de 50 sprites, le test s'arrête automatiquement

### Données collectées

- Nombre de sprites actifs au moment du stop
- FPS au moment du stop
- Courbe FPS / nombre de sprites (captures régulières)

## Comment récupérer les résultats

### Option 1 — Automatisé via Playwright (déjà en place)

Le script `run-benchmarks.js` lance un navigateur headless pour chaque moteur, attend le stop et prend des screenshots. Pour Phaser, il lit aussi `window.benchmarkResult` via JavaScript. Pour Defold, le script Lua expose `window.defoldResult` via `html5.run_javascript()`. Pour Godot, la détection se fait par analyse de pixels rouges dans le HUD.

Lancer :
```bash
# Servir les 3 builds web
python -m http.server 8081 --directory godot-benchmark/build &
python -m http.server 8082 --directory defold-build-web4 &
python -m http.server 8083 --directory phaser-benchmark &

# Lancer le benchmark automatisé
node run-benchmarks.js
```

Résultats : screenshots + données dans `benchmark-results/`.

### Option 2 — Manuel via Chrome (si automatisé bloque)

1. Servir chaque build web sur un port local
2. Ouvrir dans Chrome, laisser tourner jusqu'au stop
3. Lire le HUD (FPS + nombre de sprites affichés en rouge)
4. Pour des captures intermédiaires : ouvrir la console et lire les variables exposées

Variables JS accessibles dans la console :
- Phaser : `window.phaserGame.scene.scenes[0].activeCount` et `.game.loop.actualFps`
- Defold : `window.defoldResult` (objet {fps, sprites, stopped})
- Godot : lecture visuelle du HUD uniquement (pas d'API JS exposée)

### Option 3 — Via Claude in Chrome (Cowork)

Utiliser le plugin Chrome de Cowork pour naviguer vers chaque build, prendre des screenshots à intervalles réguliers, et lire les résultats via JavaScript.

## Améliorations possibles

- Augmenter le spawn rate (50/s ou 100/s) pour accélérer le test
- Logger le FPS toutes les secondes dans un tableau JS pour générer une courbe
- Tester aussi en mode GPU-only (sans physique) pour comparer le plafond de rendu pur
- Tester sur mobile réel via build natif (pas web) pour des données plus proches de la prod

## Problèmes connus de la session précédente

- Defold web : timeout fréquents, le build HTML5 peut nécessiter des headers COOP/COEP ou un serveur spécifique
- Godot web : le .wasm est lourd (25-40 Mo), le chargement est long
- Playwright headless : peut donner des résultats différents du Chrome normal (pas de GPU hardware)

## État actuel des builds

- `phaser-benchmark/` : build web prêt (index.html + phaser.min.js)
- `defold-benchmark/` : projet Defold avec sources, builds web dans defold-build-web*
- `godot-benchmark/` : projet Godot avec sources, build web dans godot-benchmark/build
- `benchmark-results/` : screenshots des tests précédents (timeouts + quelques captures)
