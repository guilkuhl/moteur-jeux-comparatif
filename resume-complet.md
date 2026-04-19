# Résumé complet de la recherche — 18 avril 2026

## Besoin initial
Jeu 2D pour mobile (Android/iOS) et web. Critères : poids léger, physique & collisions, particules, nombre max de sprites avec collision, facilité de développement.

---

## Versions vérifiées (18/04/2026)
- **Godot 4.6.2** — 1er avril 2026
- **Phaser 4.0.0 "Caladan"** — 10 avril 2026 (release officielle)
- **Defold 1.12.3** — 31 mars 2026
- **Unity 6.4** — mars 2026

---

## Classement final

### 🥇 Defold 1.12.3 — RECOMMANDÉ
- **APK** : 3-5 Mo natif, aucune compilation custom
- **Web** : 1,14 Mo HTML5/WASM, fonctionne sur tous les navigateurs y compris Safari/iOS
- **Physique** : Box2D intégré (~3 000 objets collision @ 30fps)
- **Sprites natif** : ~27 000 @ 30fps
- **Langage** : Lua (+ Teal, TypeScript via transpiler, C/C++ pour extensions natives)
- **Éditeur** : complet (scene editor, particle editor, tilemap editor, debugger, profiler)
- **Export** : iOS, Android, HTML5, Windows, Mac, Linux, PS5, PS4, Switch, Steam
- **Avantage clé** : tout est clé en main, léger de base, pas besoin de recompiler quoi que ce soit

### 🥈 Godot 4.6.2 — PLUS COMPLET
- **APK standard** : ~30 Mo (arm64) / 80-130 Mo (multi-archi)
- **APK custom build** : ~10 Mo (arm64) — NÉCESSITE recompilation C++ (SCons)
- **Web** : 25-40 Mo (.wasm), single-thread depuis 4.3 (plus besoin COOP/COEP), NE FONCTIONNE PAS sur Safari/iOS
- **Physique** : natif 2 900 objets, Rapier extension 7 800 objets @ 30fps
- **Particules** : GPU, 100k+
- **Langage** : GDScript, C#, C++
- **Éditeur** : le plus complet (visual editor, node-based, tout intégré)
- **Inconvénient majeur** : impossible de strip les features depuis l'UI, recompilation C++ obligatoire pour optimiser la taille

### 🥉 Phaser 4.0.0 — WEB PUR
- **Framework** : 345 Ko min+gzip (version complète)
- **APK via Capacitor** : ~4-6 Mo (WebView, pas natif)
- **Sprites GPU Layer** : 1 000 000+ mais SANS physique ni collision ni input
- **Sprites Arcade Physics** : ~4 500 sur mobile (avec collision)
- **Physique** : Arcade (AABB) + Matter.js
- **Langage** : JavaScript / TypeScript
- **Pas d'éditeur** : code-only, VSCode + navigateur
- **Mobile = WebView** via Capacitor (mini-navigateur embarqué, pas natif)
- **Latence input mobile** : +20-30ms (bridge WebView)

---

## Corrections apportées au rapport source

| Affirmation du rapport | Réalité vérifiée |
|---|---|
| Godot 4.6 build vide ~9 Mo | FAUX — 25-40 Mo web, ~30 Mo APK arm64 |
| Box2D v3.0 à 6 500 objets | FAUX — Box2D v2.4 = 3 000 (source godot.rapier.rs) |
| Phaser 4 : 1M sprites | VRAI mais SANS physique/collision (GPU Layer only) |
| 760% gain CPU Phaser 4 | NON VÉRIFIÉ — aucune source officielle |
| 85 000 sprites Godot/Defold | NON VÉRIFIÉ — aucun benchmark primaire trouvé |
| Benchmark Rapier sur Godot 4.6 | FAUX — benchmark réalisé sur Godot 4.3 |

---

## Tailles APK Android vérifiées

| Moteur | Scénario | Taille | Source |
|---|---|---|---|
| Defold 1.12 | Standard (natif) | 3-5 Mo | Grokipedia, docs |
| Phaser 4 + Capacitor | WebView | ~4-6 Mo | npm + GitHub Ionic |
| Godot 4.6 | Standard arm64 | ~30 Mo | APKMirror |
| Godot 4.6 | Custom build 2D (4 archis) | 40 Mo (~10/archi) | GitHub GameSiProjects |
| Godot 4.6 | Standard multi-archi | 80-130 Mo | Forum Godot |
| Unity 6 | Standard | ~25-50 Mo | Documentation |

---

## Physique 2D — Objets en collision @ 30 FPS

| Solveur | Objets | Source |
|---|---|---|
| Rapier 2D (Godot ext., state_sync OFF) | 7 800 | godot.rapier.rs ✅ |
| Rapier 2D (state_sync ON) | 5 000 | godot.rapier.rs ✅ |
| Phaser Arcade | ~4 500 | Rapport (non vérifié) |
| Box2D v2.4 (Defold) | 3 000 | godot.rapier.rs ✅ |
| Godot Physics 2D natif | 2 900 | godot.rapier.rs ✅ |

---

## Performance sprites — Benchmarks vérifiés

| Moteur | Sprites @ 30fps | Contexte | Source |
|---|---|---|---|
| Defold natif | 27 000 | Desktop | PlayCanvas forum ✅ |
| Defold HTML5 | 7 500 | Navigateur | PlayCanvas forum ✅ |
| Defold go.animate | 10 000 | Mobile HTML5 (LG V20) | Gideros forum ✅ |
| Phaser 3 | 3 100 | Mobile HTML5 (LG V20) | Gideros forum ✅ |
| Phaser 4 GPU Layer | 1 000 000+ | Desktop (SANS physique) | phaser.io ✅ |

---

## Capacitor — C'est quoi ?
Outil open source (Ionic) qui emballe une app web (HTML/CSS/JS) dans une WebView native iOS/Android pour la publier sur les stores. Le jeu tourne dans un mini-navigateur embarqué, pas en code natif. Ajoute ~3 Mo à l'APK. Latence input +20-30ms vs natif.

---

## Defold — Langages supportés
- **Lua 5.1 / LuaJIT** — langage principal
- **Teal** — transpiler officiel (Lua typé statiquement)
- **TypeScript** — via ts-defold (communautaire)
- **Haxe** — via hxdefold (communautaire)
- **C/C++** — extensions natives (dmSDK)
- **Java / Obj-C / JS** — extensions plateforme
- **GLSL** — shaders
- **C# prévu** — annoncé par la Defold Foundation

---

## Marché des jeux 2D mobile
- Unity : ~70% du top mobile (leader absolu)
- Cocos Creator : ~10-15% (Asie)
- Godot : ~1% (croissance rapide)
- Defold : <1% (niche : King, Poki, jeux web)
- GameMaker : <1% (indie)

---

## Defold vs Phaser — Fonctionnalités

| Feature | Defold | Phaser 4 |
|---|---|---|
| Éditeur visuel | ✅ Intégré | ❌ Code only |
| Debugger / Profiler | ✅ Intégré | ❌ Chrome DevTools |
| Scene editor | ✅ Visuel | ❌ Code |
| Tilemap editor | ✅ Intégré | ⚠ Tiled (externe) |
| Particle editor | ✅ Visuel | ⚠ Code only |
| Physique | ✅ Box2D | ✅ Arcade + Matter.js |
| SpriteGPULayer | ❌ | ✅ 1M+ (sans physique) |
| bitECS | ❌ | ✅ |
| Filtres visuels | ⚠ GLSL custom | ✅ Blur, glow, bloom... |
| Export mobile natif | ✅ Direct | ❌ Capacitor (WebView) |
| Export console | ✅ PS5, Switch | ❌ |
| Hot reload | ✅ Live | ⚠ Partiel |
| Coder en HTML/CSS/JS | ❌ Lua only | ✅ Natif |
| UI en HTML | ❌ GUI natif | ✅ DOM |
