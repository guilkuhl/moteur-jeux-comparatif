# Corrections du rapport source — Vérification 18 avril 2026

## Rapport vérifié
"Rapport d'Analyse Comparative : Performance des Frameworks et Moteurs de Jeu 2D Mobiles en 2026"

---

## ✅ Données CONFIRMÉES

| Affirmation | Statut | Source |
|---|---|---|
| Godot 4.6 sorti en janvier 2026 | ✅ Exact | godotengine.org |
| Jolt physique 3D par défaut dans Godot 4.6 | ✅ Exact | Wikipedia, release notes |
| Phaser 4 avec SpriteGPULayer 1M+ sprites | ✅ Exact | GitHub phaser changelog |
| bitECS intégré dans Phaser 4 | ✅ Exact | phaser.io devlog 260 |
| Defold runtime 1,14 Mo HTML5 | ✅ Exact | Grokipedia |
| Rapier 7 800 objets collision | ✅ Exact | godot.rapier.rs |
| Godot Physics natif 2 900 objets | ✅ Exact | godot.rapier.rs |
| Rapier state_sync_callback optimisation | ✅ Exact | godot.rapier.rs |
| Phaser 4 architecture node-based renderer | ✅ Exact | GitHub changelog |

## ❌ Données INCORRECTES

| Affirmation | Valeur rapport | Valeur réelle | Source |
|---|---|---|---|
| Box2D v3.0 à 6 500 objets | 6 500 | **3 000** (v2.4) | godot.rapier.rs |
| Godot 4.6 build vide ~9 Mo | ~9 Mo | **25-40 Mo** web, **~30 Mo** APK arm64 | APKMirror, forums |
| Benchmark Rapier sur Godot 4.6 | Godot 4.6 | **Godot 4.3** | godot.rapier.rs |

## ⚠️ Données NON VÉRIFIÉES (aucune source primaire trouvée)

| Affirmation | Valeur | Commentaire |
|---|---|---|
| 85 000 sprites Godot @ 60fps mobile | 85 000+ | Aucun benchmark primaire. Defold natif = 27k @ 30fps (PlayCanvas forum) |
| 85 000 sprites Defold @ 60fps mobile | 85 000+ | Aucun benchmark primaire |
| 65 000 sprites Unity DOTS @ 60fps mobile | 65 000+ | Aucun benchmark primaire |
| 4 500 sprites Phaser Arcade mobile | ~4 500 | Plausible mais pas de benchmark primaire |
| Gain 760% CPU Phaser 4 | 760% | Pas dans les sources officielles Phaser |
| Defold GPU Skinning 30-50% gain | 30-50% | Non confirmé pour 2026 spécifiquement |

## 📋 Erreurs de contexte

1. **Phaser 4 : 1M sprites ≠ 1M sprites avec physique**
   Le rapport ne précise pas que le SpriteGPULayer ne supporte PAS la physique. Les sprites GPU ne peuvent avoir ni physique, ni collision, ni input. Source : phaser.io beta 5 release notes.

2. **Godot APK "~9 Mo"**
   Le rapport cite probablement Cinevva ("Build sizes start around 9 MB uncompressed") mais c'est incorrect. Un projet vide en Godot 4.5 génère un APK de 114 Mo (forum Godot). Même stripped, la template fait ~13-20 Mo.

3. **Godot web "facile"**
   Le rapport ne mentionne pas que l'export web de Godot 4 ne fonctionne pas sur Safari/iOS. Depuis 4.3, le mode single-thread supprime le besoin de COOP/COEP sur Chrome/Firefox uniquement.

4. **Taille builds non comparables**
   Le rapport compare "build vide" mais les définitions varient. Defold 1.14 Mo = HTML5 gzippé. Godot "~9 Mo" = probablement web gzippé avec custom build, pas standard. Phaser 1.2 Mo = framework seul, sans Capacitor.
