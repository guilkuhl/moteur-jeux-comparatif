# pixel-art-lab Specification

## Purpose
Fournir un atelier de traitement d'images pixel-art qui diagnostique une image source, applique des algorithmes (netteté, upscale, débruitage, pixel-snap), trace chaque itération dans un historique et permet de comparer visuellement les résultats via un dashboard HTML local. Source de vérité : dossier `pixel-lab/` (`scripts/process.py`, `scripts/workflow.py`, `scripts/diagnose.py`, `scripts/compare_snap.py`, `dashboard/index.html`, `serve.py`).

## Requirements

### Requirement: Le Pixel Lab SHALL organiser ses données en dossiers fixes à la racine
Le dépôt `pixel-lab/` MUST contenir les sous-dossiers `inputs/` (images sources), `outputs/<image_name>/` (itérations produites), `scripts/` (code Python), `dashboard/` (IHM HTML) et le fichier `history.json` à la racine.

#### Scenario: Création de dossier de sortie
- **GIVEN** une image `inputs/sprite.png`
- **WHEN** `scripts/process.py inputs/sprite.png sharpen method=unsharp_mask` est lancé pour la première fois
- **THEN** le dossier `outputs/sprite/` SHALL être créé et l'itération SHALL y être enregistrée sous `iter_001_sharpen_unsharp_mask.png`

### Requirement: Les algorithmes supportés SHALL couvrir netteté, upscale, débruitage et pixel-snap
Le lab MUST exposer au minimum quatre familles d'algorithmes et leurs méthodes : `sharpen` (unsharp_mask, laplacian, kernel), `scale2x` (nearest, scale2x, eagle2x), `denoise` (median, bilateral, nlm), `pixelsnap` (median, mode, mean).

#### Scenario: Algo inconnu rejeté
- **GIVEN** un appel à `apply_algo` avec un nom inconnu
- **WHEN** la fonction s'exécute
- **THEN** elle SHALL lever un `ValueError` listant les algorithmes disponibles

#### Scenario: Méthode inconnue rejetée
- **GIVEN** un appel `python scripts/process.py inputs/sprite.png sharpen method=unknown_filter`
- **WHEN** `apply_algo` valide la méthode
- **THEN** il SHALL lever un `ValueError` mentionnant les méthodes disponibles pour l'algo `sharpen`

### Requirement: Chaque exécution SHALL produire une itération numérotée et tracée dans history.json
Le script `process.py` MUST incrémenter un index d'itération par image (format `iter_NNN_<algo>_<method>.png`), écrire l'image résultante dans `outputs/<image_name>/` et mettre à jour `history.json` avec la configuration et la date.

#### Scenario: Numérotation incrémentale
- **GIVEN** une image ayant déjà deux itérations
- **WHEN** une nouvelle commande `process.py` est lancée sur cette image
- **THEN** le fichier produit SHALL être `iter_003_<algo>_<method>.png` et la taille de `history["<image>"].runs` SHALL passer à 3

#### Scenario: Format du label de sortie
- **GIVEN** un algo `scale2x` avec méthode `eagle2x`
- **WHEN** `save_result` écrit l'image
- **THEN** le nom de fichier SHALL commencer par `iter_` suivi d'un numéro zéro-paddé sur 3 chiffres puis `_scale2x_eagle2x.png`

### Requirement: Le pipeline SHALL enchaîner plusieurs algorithmes via la commande `pipeline`
Le script `process.py` MUST accepter un argument `steps="algo:method,algo:method"` pour exécuter plusieurs étapes successives sur la même image, en conservant la trace ordonnée des étapes dans `history.json`.

#### Scenario: Chaîne de traitements
- **GIVEN** la commande `python scripts/process.py inputs/sprite.png pipeline steps="denoise:median,sharpen:unsharp_mask"`
- **WHEN** `run_pipeline` itère sur les étapes
- **THEN** chaque étape SHALL être appliquée dans l'ordre et la méta-itération SHALL être labellisée `pipeline` avec la concaténation des méthodes (ex. `median+unsharp_mask`)

### Requirement: Le workflow automatique SHALL diagnostiquer puis recommander un plan de traitement
Le script `workflow.py` MUST appeler `diagnose()` pour mesurer flou, artefacts JPEG, interpolation, bruit, taille de palette et résolution effective, puis appeler `build_recommendations()` pour générer l'ordre optimal des algorithmes à appliquer.

#### Scenario: Mode dry-run
- **GIVEN** la commande `python scripts/workflow.py inputs/sprite.png --dry-run`
- **WHEN** le workflow s'exécute
- **THEN** il SHALL afficher le diagnostic et le plan recommandé SANS créer d'itération dans `outputs/`

#### Scenario: Filtrage des algos appliqués
- **GIVEN** la commande `python scripts/workflow.py inputs/sprite.png --only sharpen denoise`
- **WHEN** le plan est construit
- **THEN** seuls les traitements `sharpen` et `denoise` SHALL être exécutés, et les autres SHALL être ignorés même s'ils apparaissent dans le plan recommandé

### Requirement: Le script `compare_snap.py` SHALL produire une variante par combinaison algo × méthode
Le script `compare_snap.py` MUST, en mode exhaustif (défaut), générer une itération pour chaque combinaison `algo × method` disponible, plus des combos prédéfinis (`pixelsnap/median → sharpen/unsharp_mask`, etc.), et respecter l'option `--scale 2` pour inclure les variantes d'upscale.

#### Scenario: Filtrage --only
- **GIVEN** la commande `python scripts/compare_snap.py inputs/fireball.png --only pixelsnap`
- **WHEN** le script s'exécute
- **THEN** seules les méthodes de `pixelsnap` (median, mode, mean) SHALL produire des itérations

### Requirement: Le dashboard SHALL permettre de comparer visuellement les itérations
Le dashboard `pixel-lab/dashboard/index.html` MUST afficher une topbar, une sidebar listant les images sources et le nombre d'itérations, et une zone principale pour visualiser/comparer les rendus, en lisant `history.json` et `outputs/<image_name>/`.

#### Scenario: Sélection d'une image
- **GIVEN** le dashboard ouvert avec plusieurs entrées dans la sidebar
- **WHEN** l'utilisateur clique sur une vignette
- **THEN** la vue principale SHALL charger les itérations correspondantes depuis `outputs/<image_name>/`

### Requirement: Le serveur local SHALL servir le dashboard et ouvrir le navigateur
Le script `serve.py` MUST lancer un `http.server` local (port par défaut 5500), et ouvrir automatiquement `http://localhost:<port>/dashboard/index.html` sauf si l'option `--no-browser` est fournie.

#### Scenario: Port personnalisé
- **GIVEN** la commande `py serve.py --port 8080`
- **WHEN** le serveur démarre
- **THEN** le dashboard SHALL être accessible à `http://localhost:8080/dashboard/index.html`
