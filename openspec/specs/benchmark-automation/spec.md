# benchmark-automation Specification

## Purpose
Automatiser l'exécution du benchmark sprite+physique sur Godot, Defold et Phaser via Playwright, détecter automatiquement la condition d'arrêt (FPS < 20) et produire des artefacts reproductibles (screenshots + tableau de résultats) sans intervention manuelle. Source de vérité : `run-benchmarks.js` et `plan-benchmark.md`.

## Requirements

### Requirement: Les trois moteurs SHALL être servis sur localhost aux ports 8081, 8082, 8083
Le workflow MUST servir le build HTML5 de Godot sur le port 8081, le build HTML5 de Defold (defold-build-web4) sur le port 8082 et le répertoire phaser-benchmark sur le port 8083, chacun via `python -m http.server`.

#### Scenario: Démarrage des serveurs locaux
- **GIVEN** un terminal à la racine du dépôt
- **WHEN** l'opérateur lance les trois commandes `python -m http.server <port> --directory <build>` en tâche de fond
- **THEN** `http://localhost:8081/index.html`, `http://localhost:8082/index.html` et `http://localhost:8083/index.html` SHALL répondre 200 avec la page d'entrée du moteur correspondant

### Requirement: Le runner Playwright SHALL exécuter les benchmarks séquentiellement dans Chromium
Le script `run-benchmarks.js` MUST utiliser `chromium.launch({ headless: false })` avec les flags `--no-sandbox`, `--disable-web-security`, `--disable-background-timer-throttling`, `--disable-renderer-backgrounding`, `--disable-backgrounding-occluded-windows` et `--autoplay-policy=no-user-gesture-required`, puis exécuter les benchmarks l'un après l'autre dans l'ordre Phaser → Defold → Godot.

#### Scenario: Lancement du navigateur
- **GIVEN** l'exécution de `node run-benchmarks.js`
- **WHEN** Playwright instancie Chromium
- **THEN** le viewport SHALL être 980 × 580 px et tous les flags précités SHALL être appliqués

#### Scenario: Ordre d'exécution
- **GIVEN** la liste `benchmarks` dans `run-benchmarks.js`
- **WHEN** la boucle principale s'exécute
- **THEN** l'ordre SHALL être exactement : Phaser 4.0.0 (8083), Defold 1.12.3 (8082), Godot 4.6.2 (8081)

### Requirement: La détection d'arrêt SHALL combiner inspection pixel et lecture JavaScript
Le runner MUST détecter l'arrêt de deux manières selon le type de moteur : pour Phaser, en lisant `window.benchmarkResult` via `page.evaluate`; pour Godot et Defold (type "webgl"), en cherchant au moins 3 pixels rouges (R>180, G<60, B<60, alpha>100) dans la zone HUD du canvas (400 × 80 px coin supérieur gauche).

#### Scenario: Arrêt Phaser détecté via window.benchmarkResult
- **GIVEN** Phaser exécute le benchmark et atteint la condition d'arrêt
- **WHEN** le runner évalue `PHASER_STATE_JS` toutes les 3 secondes
- **THEN** dès que `window.benchmarkResult` est défini, `state.stopped` SHALL être `true` et `{sprites, fps}` SHALL être consignés

#### Scenario: Arrêt Godot détecté via analyse pixel
- **GIVEN** Godot affiche le HUD rouge au stop
- **WHEN** le runner exécute `CHECK_RED_HUD_JS` qui copie le canvas dans un canvas 2D temporaire
- **THEN** si plus de 5 pixels rouges sont trouvés dans la zone 400 × 80 px, `found` SHALL être `true`

#### Scenario: Fallback WebGL readPixels
- **GIVEN** le canvas Godot refuse `drawImage` (contexte WebGL pur)
- **WHEN** le bloc `try/catch` de `CHECK_RED_HUD_JS` échoue
- **THEN** le runner SHALL basculer sur `gl.readPixels` en parcourant `x ∈ [5, 300] step 3` et `y ∈ [5, 70] step 3`, et un seuil de 3 pixels rouges SHALL suffire à déclarer `found: true`

### Requirement: Chaque benchmark SHALL respecter un timeout et produire une capture d'écran
Le runner MUST appliquer un `maxWaitMs` de 300 000 ms pour Phaser et Defold et de 600 000 ms pour Godot (chargement .wasm plus long), puis capturer une screenshot PNG dans `benchmark-results/<nom>_STOP.png` au stop, ou `<nom>_timeout.png` sinon.

#### Scenario: Stop détecté avant timeout
- **GIVEN** Phaser stoppe à 120 s
- **WHEN** la condition d'arrêt est vérifiée
- **THEN** le runner SHALL prendre une screenshot plein écran dans `benchmark-results/Phaser_4_0_0_STOP.png` et logger "✓ STOP détecté à 120.0s"

#### Scenario: Timeout atteint sans stop
- **GIVEN** Godot n'a pas stoppé après 600 s
- **WHEN** la boucle de polling sort de la fenêtre de temps
- **THEN** le runner SHALL prendre une screenshot dans `benchmark-results/Godot_4_6_2_timeout.png` et consigner `sprites: "N/A", fps: "N/A"`

### Requirement: Les résultats SHALL être affichés sous forme de tableau ASCII dans la console
À la fin de l'exécution, le script MUST afficher un tableau aligné listant pour chaque moteur : nom, nombre de sprites et FPS final.

#### Scenario: Rendu du tableau final
- **GIVEN** les trois benchmarks terminés (stop ou timeout)
- **WHEN** la fonction principale atteint sa phase d'affichage
- **THEN** la console SHALL imprimer une ligne d'en-tête `Moteur | Sprites | FPS final`, un séparateur, puis une ligne par moteur, et indiquer le dossier `benchmark-results/` en pied de tableau

### Requirement: La détection SHALL poller toutes les 3 secondes et journaliser les transitions
Le runner MUST attendre 3 000 ms entre deux polls, journaliser chaque changement de statut ou tous les cinq itérations, et afficher l'élapsed en secondes.

#### Scenario: Log périodique
- **GIVEN** un benchmark Phaser en cours depuis 45 s sans stop
- **WHEN** l'itération atteint le 15ᵉ poll (45 s)
- **THEN** la console SHALL afficher une ligne du type `[45s] sprites=4200 fps=45 stopped=false`
