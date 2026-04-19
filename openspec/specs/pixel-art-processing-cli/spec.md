# pixel-art-processing-cli Specification

## Purpose
Exposer une CLI Python (`pixel-lab/scripts/process.py`) qui applique un algorithme (ou un pipeline) sur une image source, sauvegarde chaque itération dans `outputs/<image_name>/` avec un index séquentiel et tient à jour l'historique des exécutions dans `pixel-lab/history.json`.

## Requirements

### Requirement: La CLI SHALL accepter `source`, `algo` et des paramètres `key=value`
Le script `process.py` MUST accepter trois arguments positionnels : `source` (chemin d'image, relatif à `inputs/` si non absolu), `algo` (nom d'algorithme : `sharpen`, `scale2x`, `denoise`, `pixelsnap` ou `pipeline`) et une liste variadique de paramètres au format `key=value`.

#### Scenario: Chemin relatif à inputs/
- **GIVEN** un fichier `pixel-lab/inputs/sprite.png`
- **WHEN** on exécute `python scripts/process.py inputs/sprite.png sharpen method=unsharp_mask`
- **THEN** la source SHALL être résolue en `pixel-lab/inputs/sprite.png` et ouverte avec PIL

#### Scenario: Parsing automatique des types
- **GIVEN** l'argument `radius=1.2`
- **WHEN** `parse_params` traite la liste d'arguments
- **THEN** la valeur SHALL être castée en `float` (1.2), tandis que `percent=200` SHALL être casté en `int` (200) et les chaînes restantes SHALL rester en `str`

#### Scenario: Image source introuvable
- **GIVEN** un chemin de source qui n'existe pas
- **WHEN** la CLI vérifie `src_path.exists()`
- **THEN** elle SHALL afficher `[erreur] Image introuvable : <path>` et sortir avec le code 1

### Requirement: Chaque exécution SHALL produire une itération numérotée dans `outputs/<image_name>/`
La CLI MUST créer le dossier `pixel-lab/outputs/<image_name>/` si nécessaire et écrire le résultat sous `iter_NNN_<algo>_<method>.png`, où `NNN` est un entier zéro-paddé sur 3 chiffres, incrémenté à chaque appel pour cette image.

#### Scenario: Numérotation incrémentale
- **GIVEN** une image `sprite.png` avec deux runs déjà consignés dans `history.json`
- **WHEN** une troisième exécution est lancée
- **THEN** le fichier produit SHALL être `outputs/sprite/iter_003_<algo>_<method>.png` et la longueur de `history["sprite"].runs` SHALL passer à 3

#### Scenario: Label pipeline
- **GIVEN** une exécution via `pipeline` enchaînant `denoise:median` puis `sharpen:unsharp_mask`
- **WHEN** `save_result` écrit l'image résultat
- **THEN** le nom de fichier SHALL contenir l'algo_label `pipeline` et le method_label `median+unsharp_mask`

### Requirement: Le mode `pipeline` SHALL enchaîner plusieurs étapes ordonnées
La CLI MUST accepter `algo=pipeline` avec un paramètre `steps="algo:method,algo:method"` et appliquer chaque étape dans l'ordre, en loggant la trace `{algo, method}` par étape dans `history.json`.

#### Scenario: Pipeline à deux étapes
- **GIVEN** la commande `python scripts/process.py inputs/sprite.png pipeline steps="denoise:median,sharpen:unsharp_mask"`
- **WHEN** `run_pipeline` itère
- **THEN** `denoise/median` SHALL être appliqué en premier, puis `sharpen/unsharp_mask`, et la clé `runs[-1].steps` de l'historique SHALL être `[{"algo":"denoise","method":"median"}, {"algo":"sharpen","method":"unsharp_mask"}]`

#### Scenario: Pipeline sans steps
- **GIVEN** la commande `python scripts/process.py inputs/sprite.png pipeline` (sans `steps=...`)
- **WHEN** la CLI démarre
- **THEN** elle SHALL afficher `[erreur] Pipeline : fournis steps='algo:method,algo:method'` et sortir avec le code 1

### Requirement: L'historique SHALL être persistant dans `pixel-lab/history.json`
La CLI MUST lire `history.json` s'il existe, ajouter une entrée par exécution (algo, méthode, paramètres, chemin de sortie, date ISO) et ré-écrire le fichier avec indentation et `ensure_ascii=False`.

#### Scenario: Fichier history.json absent
- **GIVEN** un dépôt sans `pixel-lab/history.json`
- **WHEN** `load_history` est appelé
- **THEN** la fonction SHALL retourner un dict vide et `save_history` SHALL créer le fichier à la première écriture

#### Scenario: Structure d'une entrée
- **GIVEN** une exécution qui vient de terminer
- **WHEN** `save_history` persiste les données
- **THEN** `history["<image>"].runs[i]` SHALL contenir au minimum les clés `algo`, `method` (ou `steps` pour un pipeline), `params`, `output` et une date ISO-8601

### Requirement: Une méthode par défaut SHALL être utilisée si `method=` est absent
Lorsqu'un utilisateur appelle un algo sans préciser `method=`, la CLI MUST sélectionner la première méthode listée dans le dict `METHODS` de l'algo et logger un message `[info] Pas de method= fourni, utilisation de '<method>' par défaut.`

#### Scenario: Sharpen sans méthode
- **GIVEN** la commande `python scripts/process.py inputs/sprite.png sharpen`
- **WHEN** `apply_algo` résout la méthode
- **THEN** la méthode par défaut (`unsharp_mask`) SHALL être utilisée et le message `[info] Pas de method= fourni...` SHALL apparaître dans la sortie
