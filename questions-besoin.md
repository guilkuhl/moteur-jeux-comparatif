# Questions source du besoin — Jeu 2D Mobile + Web

Toujours utiliser la dernière version stable de chaque framework/moteur de jeux pour les comparatifs.
Quel est le moteur ou framework le plus adapté pour un jeu 2D ciblant mobile (Android/iOS) et web ?
Quel est le poids minimal d'un APK Android pour chaque solution ?
Quel est le poids minimal d'un build web pour chaque solution ?
Est-il possible de faire un custom build pour diminuer le poids final du build ?
Le build web fonctionne-t-il sur tous les navigateurs y compris Safari/iOS ?
Quel moteur physique 2D est intégré et combien d'objets en collision simultanée supporte-t-il ?
Combien de sprites avec collision active peut-on afficher à 60 FPS sur mobile ?
Le moteur dispose-t-il d'un système de particules GPU ?
Est-il possible d'utiliser du HTML/CSS pour les menus et GUI du jeu ?
L'export mobile est-il natif ARM ou passe-t-il par une WebView ?
Le langage principal est-il accessible (pas de C++ obligatoire) ?
Le moteur dispose-t-il d'un éditeur visuel intégré ?
Le moteur est-il open source ou gratuit ?
La documentation est-elle riche et la communauté active ?
Le moteur supporte-t-il les animations sprite sheets / flipbook ?
Le moteur est-il compatible avec les appareils bas de gamme (2 Go RAM) ?
L'export web nécessite-t-il des headers serveur spéciaux (COOP/COEP) ?
Quelle est la latence d'input sur mobile (natif vs WebView) ?
Le moteur supporte-t-il une architecture ECS (Entity Component System) ?
Quels filtres visuels sont disponibles nativement (blur, glow, bloom) ou faut-il du GLSL custom ?
Le moteur supporte-t-il le hot reload en développement ?
Quels langages alternatifs sont supportés en plus du langage principal (TypeScript, C#, Haxe, etc.) ?
Le moteur dispose-t-il d'un debugger et d'un profiler intégrés ?
Le moteur supporte-t-il l'export console (PS5, Switch, Steam) ?
Le moteur dispose-t-il d'un tilemap editor intégré ou faut-il un outil externe (Tiled) ?
Le moteur dispose-t-il d'un éditeur de particules visuel ou faut-il coder les effets ?
Quelle est la taille du build multi-architecture (arm64 + armv7 + x86) vs mono-architecture ?
Faut-il recompiler le moteur en C++ pour optimiser la taille du build ?
Le strip des features inutilisées (3D, Vulkan, XR) est-il possible depuis l'UI sans recompilation ?
Quelle est la part de marché du moteur et l'impact sur la disponibilité des ressources/tutoriels ?
Les benchmarks de performance (sprites, physique) sont-ils vérifiables via des sources primaires ?
Quand on compare les tailles de build, compare-t-on les mêmes conditions (gzippé, standard, custom) ?
Quelle est la différence entre sprites GPU purs (rendu seul) et sprites avec physique/collision active ?
Le moteur est-il soutenu par une fondation ou entreprise pérenne ?
PixiJS est-il une alternative viable ou est-ce un renderer pur sans physique/collision/audio intégré ?
Si le moteur supporte C# (.NET/Mono), l'export web est-il possible ou bloqué ?
Le moteur ou framework supporte-t-il l'injection de dépendance nativement ou via un plugin ?
Est-il possible d'afficher des centaines de milliers de sprites en fond (décor) sans physique via le GPU ?
