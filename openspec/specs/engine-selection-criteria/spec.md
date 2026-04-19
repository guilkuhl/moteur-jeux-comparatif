# engine-selection-criteria Specification

## Purpose
Formaliser les critères pondérés et les contraintes techniques qui permettent de comparer Godot, Phaser, Defold et Unity pour un jeu 2D ciblant mobile (Android/iOS) et web, afin de produire une recommandation justifiée. Source de vérité : `cahier-besoins-techniques.md`.

## Requirements

### Requirement: Les critères d'évaluation SHALL être pondérés selon six axes
Le projet MUST évaluer chaque moteur 2D candidat avec les six critères pondérés suivants, dont la somme des poids est de 100 % : Physique & collisions (25 %), Sprites avec collision (20 %), Poids léger APK/build (15 %), Particules (15 %), Facilité de développement (15 %), Multi-plateforme mobile+web (10 %).

#### Scenario: Somme des pondérations
- **GIVEN** le tableau des critères défini dans `cahier-besoins-techniques.md`
- **WHEN** on additionne les pondérations des six critères
- **THEN** le total SHALL être exactement égal à 100 %

#### Scenario: Calcul du score d'un moteur
- **GIVEN** un moteur noté sur chacun des six critères entre 0 et 10
- **WHEN** on calcule la note pondérée `somme(note_i × poids_i)`
- **THEN** le moteur retenu SHALL être celui qui maximise cette somme sous les contraintes techniques

### Requirement: Les contraintes mobile SHALL être explicites et vérifiables
Le projet MUST documenter les contraintes mobiles qui conditionnent l'acceptabilité d'un moteur : taille d'APK idéale inférieure à 10 Mo, performance native ARM (éviter WebView lorsque possible), export iOS et Android sans outil tiers, compatibilité des appareils disposant de 2 Go de RAM.

#### Scenario: APK dépassant le seuil
- **GIVEN** un moteur candidat dont l'APK standard dépasse 10 Mo
- **WHEN** on applique le critère "Poids léger"
- **THEN** le moteur SHALL être pénalisé, et une justification explicite (ex. recompilation C++ Godot) SHALL être documentée dans le rapport

#### Scenario: Moteur à base de WebView
- **GIVEN** un moteur mobile reposant sur Capacitor/WebView (Phaser 4)
- **WHEN** on évalue la performance native ARM
- **THEN** le document SHALL signaler la latence d'input additionnelle de +20 à +30 ms par rapport au natif

### Requirement: Les contraintes web SHALL couvrir la compatibilité Safari/iOS et le poids
Le projet MUST exiger un build web idéalement inférieur à 5 Mo, un fonctionnement sans header COOP/COEP lorsque possible, un chargement rapide et une compatibilité avec Safari/iOS.

#### Scenario: Build web incompatible Safari
- **GIVEN** un moteur dont l'export web ne fonctionne pas sur Safari/iOS (cas documenté de Godot 4)
- **WHEN** on applique le critère "Multi-plateforme"
- **THEN** ce moteur SHALL être disqualifié pour un déploiement web grand public ou explicitement limité à Chrome/Firefox

#### Scenario: Build web gzippé léger
- **GIVEN** un moteur dont le build HTML5/WASM gzippé fait moins de 5 Mo (ex. Defold 1,14 Mo)
- **WHEN** on applique le critère "Poids léger"
- **THEN** le moteur SHALL recevoir la meilleure note sur cet axe

### Requirement: Les contraintes gameplay SHALL imposer la physique 2D et les particules GPU
Le projet MUST exiger un moteur physique 2D avec collisions (Box2D ou équivalent), un système de particules GPU, un maximum de sprites simultanés avec collision active, et le support d'animations sprite sheets / flipbook.

#### Scenario: Moteur sans physique intégrée
- **GIVEN** un moteur pur rendu (PixiJS v8)
- **WHEN** on évalue les exigences gameplay
- **THEN** le moteur SHALL être rejeté car il ne fournit ni physique, ni collision, ni audio intégrés

### Requirement: La recommandation finale SHALL justifier chaque rejet
Le document `cahier-besoins-techniques.md` MUST désigner un moteur recommandé et lister au moins Godot 4.6.2, Phaser 4.0.0 et Unity 6.4 comme alternatives évaluées avec la raison de leur rejet.

#### Scenario: Justification du rejet de Godot
- **GIVEN** la section "Alternatives évaluées" du cahier
- **WHEN** on consulte la ligne Godot 4.6.2
- **THEN** la raison du rejet SHALL mentionner à la fois l'APK trop lourd (~30 Mo standard), l'incompatibilité web Safari/iOS et la recompilation C++ nécessaire pour optimiser la taille

#### Scenario: Justification du rejet de Phaser 4
- **GIVEN** la section "Alternatives évaluées" du cahier
- **WHEN** on consulte la ligne Phaser 4.0.0
- **THEN** la raison du rejet SHALL mentionner l'absence de mobile natif (WebView via Capacitor) et la limite d'environ 4 500 sprites avec collision
