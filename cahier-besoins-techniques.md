# Cahier des besoins techniques — Jeu 2D Mobile + Web

## Contexte
Recherche du meilleur moteur/framework pour développer un jeu 2D ciblant mobile (Android/iOS) et web (navigateur).

## Critères pondérés

| Critère | Poids | Description |
|---|---|---|
| Poids léger (APK/build) | 15% | Taille minimale de l'APK Android et du build web |
| Physique & collisions | 25% | Nombre d'objets en collision simultanée, qualité du moteur physique |
| Particules | 15% | Système de particules GPU, nombre max, effets visuels |
| Sprites avec collision | 20% | Nombre max de sprites affichables avec physique active @ 60fps |
| Facilité de développement | 15% | Courbe d'apprentissage, outillage, documentation, communauté |
| Multi-plateforme (mobile+web) | 10% | Qualité de l'export natif mobile et web, compatibilité navigateurs |

## Contraintes techniques identifiées

### Mobile
- APK le plus léger possible (idéal < 10 Mo)
- Performance native ARM (pas de WebView si possible)
- Export natif iOS et Android sans outils tiers
- Compatibilité appareils bas de gamme (2GB RAM)

### Web
- Build web le plus léger possible (idéal < 5 Mo)
- Compatibilité tous navigateurs y compris Safari/iOS
- Pas de contraintes serveur complexes (pas de headers COOP/COEP si possible)
- Chargement rapide

### Gameplay
- Physique 2D avec collisions (Box2D ou équivalent)
- Système de particules GPU
- Maximum de sprites actifs avec collision simultanée
- Animations sprite sheets / flipbook

### Développement
- Langage accessible (pas de C++ obligatoire)
- Éditeur visuel préféré
- Documentation riche
- Communauté active
- Open source ou gratuit

## Moteur recommandé : Defold 1.12.3

### Justification
- Seul moteur qui coche TOUS les critères sans compromis
- APK 3-5 Mo natif sans recompilation
- Web 1.14 Mo, compatible Safari/iOS
- Box2D intégré
- Éditeur complet intégré
- Lua : langage simple et performant (LuaJIT)
- Export natif iOS/Android/HTML5 direct
- Gratuit, open source (Defold Foundation)

### Risques identifiés
- Communauté plus petite que Unity/Godot
- Lua moins répandu que JS/C#/GDScript
- Part de marché < 1% (moins de ressources/tutos)
- Pas de ECS natif (contrairement à Phaser 4 bitECS)
- Filtres visuels limités (GLSL custom nécessaire)

### Alternatives évaluées

| Alternative | Raison du rejet |
|---|---|
| Godot 4.6.2 | APK trop lourd (~30 Mo std), web ne marche pas sur Safari/iOS, recompilation C++ pour optimiser |
| Phaser 4.0.0 | Pas de mobile natif (WebView via Capacitor), sprites avec collision limités à ~4 500 |
| Unity 6.4 | APK 25-50 Mo, licence payante, overkill pour du 2D simple |
| PixiJS v8 | Renderer pur, aucune physique/collision/audio intégré |

## Sources
Voir le fichier `sources.md` pour la liste complète des 23 sources primaires vérifiées.
