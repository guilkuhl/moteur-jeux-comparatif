# engine-comparison-report Specification

## Purpose
Publier un rapport comparatif structuré des moteurs 2D évalués (Defold 1.12.3, Godot 4.6.2, Phaser 4.0.0, Unity 6.4) s'appuyant uniquement sur des sources primaires vérifiées, avec un classement explicite et une traçabilité des corrections apportées au rapport source. Sources de vérité : `resume-complet.md`, `corrections-rapport.md`, `sources.md`, `comparatif-moteurs-2d.html`.

## Requirements

### Requirement: Le rapport SHALL fixer les versions de référence au 18 avril 2026
Le rapport MUST consigner les versions exactes évaluées : Godot 4.6.2 (1ᵉʳ avril 2026), Phaser 4.0.0 "Caladan" (10 avril 2026), Defold 1.12.3 (31 mars 2026) et Unity 6.4 (mars 2026).

#### Scenario: Vérification des versions
- **GIVEN** `resume-complet.md`
- **WHEN** on consulte la section "Versions vérifiées"
- **THEN** les quatre moteurs SHALL être listés avec leur version ET leur date de sortie précitées

### Requirement: Le classement final SHALL suivre l'ordre Defold 🥇, Godot 🥈, Phaser 🥉
Le rapport MUST attribuer explicitement la 1ʳᵉ place à Defold 1.12.3 (RECOMMANDÉ), la 2ᵉ à Godot 4.6.2 (PLUS COMPLET) et la 3ᵉ à Phaser 4.0.0 (WEB PUR), chaque rang étant accompagné d'une synthèse APK / Web / Physique / Sprites / Langage / Éditeur / Export.

#### Scenario: Ligne Defold
- **GIVEN** la section "Classement final"
- **WHEN** on lit la fiche 🥇 Defold
- **THEN** elle SHALL mentionner APK 3-5 Mo, Web 1,14 Mo, Box2D ~3 000 objets collision @ 30 fps, ~27 000 sprites @ 30 fps natif, langage Lua, éditeur complet, export iOS/Android/HTML5/PS5/Switch

#### Scenario: Ligne Godot
- **GIVEN** la section "Classement final"
- **WHEN** on lit la fiche 🥈 Godot
- **THEN** elle SHALL mentionner APK standard ~30 Mo arm64, APK custom ~10 Mo (recompilation C++), Web 25-40 Mo (.wasm) non compatible Safari/iOS, Rapier 7 800 objets collision, particules GPU 100k+

#### Scenario: Ligne Phaser
- **GIVEN** la section "Classement final"
- **WHEN** on lit la fiche 🥉 Phaser
- **THEN** elle SHALL mentionner framework 345 Ko min+gzip, APK Capacitor 4-6 Mo (WebView, pas natif), SpriteGPULayer 1 000 000+ sprites SANS physique, Arcade ~4 500 sprites avec collision sur mobile, latence input +20-30 ms

### Requirement: Le rapport SHALL documenter les corrections apportées au rapport source
Le document `corrections-rapport.md` MUST lister les données confirmées (✅), les données incorrectes (❌) et les données non vérifiées (⚠️) par rapport au "Rapport d'Analyse Comparative" d'origine.

#### Scenario: Correction Box2D
- **GIVEN** le tableau des corrections
- **WHEN** on consulte la ligne "Box2D v3.0 à 6 500 objets"
- **THEN** la valeur corrigée SHALL être "3 000 (v2.4)" et la source citée SHALL être godot.rapier.rs

#### Scenario: Correction APK Godot
- **GIVEN** le tableau des corrections
- **WHEN** on consulte la ligne "Godot 4.6 build vide ~9 Mo"
- **THEN** la valeur corrigée SHALL être "25-40 Mo web, ~30 Mo APK arm64" avec sources APKMirror et forums

#### Scenario: Donnée non vérifiée marquée comme telle
- **GIVEN** l'affirmation "85 000 sprites Godot @ 60 fps mobile"
- **WHEN** on consulte la section ⚠️ "NON VÉRIFIÉES"
- **THEN** l'entrée SHALL indiquer explicitement "Aucun benchmark primaire" et rappeler que Defold natif atteint 27 000 @ 30 fps (PlayCanvas forum)

### Requirement: Les tailles APK Android SHALL être tabulées avec sources
Le rapport MUST fournir un tableau "Tailles APK Android vérifiées" recensant au minimum : Defold 1.12 natif 3-5 Mo, Phaser 4 + Capacitor ~4-6 Mo (WebView), Godot 4.6 standard arm64 ~30 Mo, Godot 4.6 multi-archi 80-130 Mo, Godot 4.6 custom 2D 40 Mo (~10/archi), Unity 6 ~25-50 Mo.

#### Scenario: Ligne Defold APK
- **GIVEN** le tableau APK
- **WHEN** on lit la ligne Defold 1.12
- **THEN** elle SHALL indiquer "Standard (natif) 3-5 Mo" avec source "Grokipedia, docs"

### Requirement: Les benchmarks de physique SHALL être tabulés avec source primaire
Le rapport MUST publier un tableau "Physique 2D — Objets en collision @ 30 FPS" avec : Rapier state_sync OFF 7 800, Rapier state_sync ON 5 000, Phaser Arcade ~4 500, Box2D v2.4 (Defold) 3 000, Godot Physics 2D natif 2 900, chaque ligne SHALL citer une source (godot.rapier.rs) ou être marquée comme non vérifiée.

#### Scenario: Ligne Rapier OFF
- **GIVEN** le tableau physique
- **WHEN** on lit la première ligne
- **THEN** elle SHALL indiquer "Rapier 2D (Godot ext., state_sync OFF) — 7 800" avec la source godot.rapier.rs ✅

### Requirement: Le rapport SHALL être consolidé dans un document HTML comparatif
Le fichier `comparatif-moteurs-2d.html` MUST offrir une vue navigable des tableaux comparatifs (critères, APK, physique, sprites, éditeurs) et renvoyer vers les démos GPU (`index.html`) ainsi que les benchmarks (`phaser-benchmark/`, `godot-benchmark/`, `defold-benchmark/`).

#### Scenario: Navigation vers les démos
- **GIVEN** `comparatif-moteurs-2d.html` ouvert dans un navigateur
- **WHEN** l'utilisateur actionne le lien vers les démos PixiJS
- **THEN** la navigation SHALL atteindre `index.html` et présenter la grille des six démos

### Requirement: Les sources SHALL être au moins 23 primaires et vérifiées
Le document `sources.md` MUST référencer au minimum 23 sources primaires (APKMirror, GitHub Phaser, godot.rapier.rs, phaser.io, PlayCanvas forum, Grokipedia, etc.). Le projet cible aujourd'hui 37 sources listées.

#### Scenario: Comptage des sources
- **GIVEN** `sources.md`
- **WHEN** on dénombre les entrées citées
- **THEN** le total SHALL être d'au moins 23 entrées et chaque affirmation numérique du rapport SHALL pouvoir être rattachée à l'une d'elles
