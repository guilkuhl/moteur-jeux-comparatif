# mobile-web-export-constraints Specification

## Purpose
Formaliser les contraintes d'export vérifiées pour le jeu 2D cible (mobile natif + web), les seuils de taille acceptables et les incompatibilités bloquantes, afin que toute décision de sélection ou de packaging reste alignée avec les données primaires collectées. Sources de vérité : `cahier-formalisation-besoin.md`, `resume-complet.md`, `corrections-rapport.md`.

## Requirements

### Requirement: L'APK mobile SHALL viser une taille inférieure à 10 Mo
Le projet MUST viser un APK Android idéalement inférieur à 10 Mo, construit en natif ARM, compatible iOS et Android sans outil tiers, et exécutable sur des appareils disposant de 2 Go de RAM.

#### Scenario: Seuil de décision
- **GIVEN** un moteur dont l'APK standard dépasse 10 Mo
- **WHEN** on applique la contrainte "APK léger"
- **THEN** le moteur SHALL être pénalisé ou nécessiter une option documentée (ex. custom build Godot à ~10 Mo via recompilation C++ SCons)

#### Scenario: Référence Defold 3-5 Mo
- **GIVEN** Defold 1.12.3 en export standard (natif)
- **WHEN** on mesure l'APK
- **THEN** la taille SHALL être comprise entre 3 et 5 Mo, conformément aux sources Grokipedia/docs

### Requirement: Le build web SHALL viser une taille inférieure à 5 Mo et une compatibilité Safari/iOS
Le projet MUST viser un build web gzippé idéalement inférieur à 5 Mo, fonctionner sans header COOP/COEP lorsque possible, être compatible avec Safari/iOS, Chrome et Firefox, et supporter un chargement rapide.

#### Scenario: Référence Defold web 1,14 Mo
- **GIVEN** Defold 1.12.3 en export HTML5/WASM gzippé
- **WHEN** on mesure le build web
- **THEN** la taille SHALL être de 1,14 Mo et la page SHALL se charger sur Safari/iOS, Chrome et Firefox

#### Scenario: Godot web non compatible Safari/iOS
- **GIVEN** Godot 4.6.2 en export web
- **WHEN** le build est ouvert sur Safari/iOS
- **THEN** il SHALL ÊTRE documenté comme non fonctionnel, ce qui disqualifie Godot pour un déploiement web grand public

#### Scenario: Godot single-thread depuis 4.3
- **GIVEN** Godot 4.3 ou supérieur
- **WHEN** on déploie l'export web sur Chrome ou Firefox
- **THEN** aucun header COOP/COEP ne SHALL être requis en mode single-thread (cette concession reste insuffisante pour Safari/iOS)

### Requirement: Les tailles APK vérifiées SHALL suivre la table officielle
Le projet MUST considérer comme valeurs de référence exactes : Defold 1.12.3 standard natif 3-5 Mo, Phaser 4 + Capacitor WebView ~4-6 Mo, Godot 4.6.2 custom build arm64 ~10 Mo, Godot 4.6.2 standard arm64 ~30 Mo, Godot 4.6.2 standard multi-archi 80-130 Mo, Unity 6.4 standard 25-50 Mo.

#### Scenario: Consultation de la table
- **GIVEN** `cahier-formalisation-besoin.md` §3.1
- **WHEN** on cherche la taille APK Godot standard arm64
- **THEN** la valeur documentée SHALL être ~30 Mo, avec source APKMirror

#### Scenario: Godot custom build
- **GIVEN** la ligne "Godot 4.6.2 custom build arm64"
- **WHEN** on lit la source associée
- **THEN** elle SHALL citer GitHub GameSiProjects et la valeur SHALL être ~10 Mo, obtenue via recompilation C++ (SCons)

### Requirement: Le déploiement mobile via WebView SHALL être marqué comme non natif
Tout déploiement mobile reposant sur Capacitor (Phaser) MUST être explicitement étiqueté "WebView, non natif", avec un coût documenté de +20 à +30 ms de latence d'input et un overhead d'environ 3 Mo sur l'APK.

#### Scenario: Latence Capacitor
- **GIVEN** un build Phaser 4 + Capacitor déployé sur Android
- **WHEN** on mesure la latence d'input vs natif
- **THEN** un retard de +20 à +30 ms SHALL être documenté dans le rapport

#### Scenario: Overhead APK
- **GIVEN** un projet Phaser 4 initialement à 1,2 Mo
- **WHEN** on l'empaquette via Capacitor
- **THEN** l'APK produit SHALL atteindre environ 4-6 Mo (overhead Capacitor ~3 Mo documenté par le forum Ionic)

### Requirement: La recompilation C++ SHALL être signalée comme barrière d'accessibilité
Tout export dont l'optimisation de taille exige une recompilation C++ (SCons Godot) MUST être explicitement signalé comme "non accessible sans expertise avancée" dans la documentation de sélection.

#### Scenario: Warning sur Godot custom build
- **GIVEN** la décision de viser un APK Godot à ~10 Mo
- **WHEN** on consulte la justification dans `cahier-formalisation-besoin.md`
- **THEN** la section SHALL mentionner que le custom build nécessite une recompilation C++ via SCons, non accessible sans expertise avancée

### Requirement: Le support console et le support ECS SHALL être documentés par moteur
Le rapport MUST distinguer pour chaque moteur les exports console disponibles (PS5, PS4, Switch, Steam pour Defold ; aucun pour Phaser 4) et la disponibilité d'une architecture ECS (bitECS pour Phaser 4 ; absent pour Defold).

#### Scenario: Tableau des fonctionnalités
- **GIVEN** la table "Comparaison fonctionnelle détaillée" du cahier de formalisation
- **WHEN** on consulte la ligne "Export console"
- **THEN** Defold SHALL être marqué ✅ (PS5, PS4, Switch, Steam) et Phaser 4 SHALL être marqué ❌

### Requirement: Les données non vérifiées SHALL être isolées et marquées
Le rapport MUST identifier explicitement les affirmations non confirmées par une source primaire : 85 000 sprites Godot/Defold @ 60 fps mobile, 65 000 sprites Unity DOTS @ 60 fps mobile, 4 500 sprites Phaser Arcade mobile, gain 760 % CPU Phaser 4. Toute décision de sélection MUST s'appuyer en priorité sur des données vérifiées.

#### Scenario: Contradiction Box2D v3.0
- **GIVEN** l'affirmation initiale "Box2D v3.0 à 6 500 objets"
- **WHEN** on la confronte aux sources primaires
- **THEN** le rapport SHALL la marquer FAUX et la remplacer par "3 000 objets (v2.4, source godot.rapier.rs)"
