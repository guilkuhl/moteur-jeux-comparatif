## ADDED Requirements

### Requirement: Chaque module algorithme SHALL exposer un dict `PARAMS` décrivant les paramètres de ses méthodes
En complément du dict `METHODS`, chaque module `pixel-lab/scripts/algorithms/<algo>.py` MUST exposer un attribut `PARAMS` de type `dict[str, list[dict]]` mappant chaque nom de méthode à la liste ordonnée de ses paramètres exposables. Chaque entrée de paramètre MUST contenir au minimum les clés `name` (str), `type` (`"int"` | `"float"` | `"str"`) et `default` (valeur cohérente avec `type`). Les bornes `min` et `max` (numériques) sont obligatoires pour les types `int` et `float`.

#### Scenario: PARAMS aligné sur METHODS
- **GIVEN** un module `algorithms/sharpen.py`
- **WHEN** on lit ses attributs publics
- **THEN** chaque clé de `METHODS` SHALL avoir une entrée correspondante dans `PARAMS`, et chaque entrée SHALL être une liste (éventuellement vide si la méthode n'a aucun paramètre exposé)

#### Scenario: Métadonnée d'un paramètre
- **GIVEN** la clé `PARAMS["unsharp_mask"]` du module `sharpen`
- **WHEN** on lit la première entrée
- **THEN** elle SHALL contenir au minimum `{"name": "radius", "type": "float", "default": 1.2, "min": 0.1, "max": 10}` avec ces clés et types exacts

#### Scenario: Méthode sans paramètre
- **GIVEN** une méthode dont la signature ne prend que `img`
- **WHEN** on lit son entrée dans `PARAMS`
- **THEN** la valeur SHALL être une liste vide `[]`, ce qui signale au consommateur qu'aucun champ d'entrée n'est à proposer

### Requirement: Les `default` de `PARAMS` SHALL correspondre aux defaults Python des fonctions
Pour chaque paramètre déclaré dans `PARAMS`, le `default` MUST être strictement égal au default de la signature Python correspondante. Cette égalité garantit qu'invoquer la fonction sans paramètre via le builder du dashboard donne le même résultat qu'invoquer la fonction sans paramètre via le CLI.

#### Scenario: Cohérence default Python ↔ default PARAMS
- **GIVEN** la fonction `def unsharp_mask(img, radius=1.2, percent=200)`
- **WHEN** on lit `PARAMS["unsharp_mask"]`
- **THEN** les défauts déclarés SHALL être exactement `radius=1.2` et `percent=200`, sans dérive

### Requirement: Les valeurs `min`/`max` SHALL être respectées par toute UI ou validation amont
`PARAMS` MUST documenter les bornes pratiques utilisables pour chaque paramètre numérique : valeurs en dessous de `min` ou au-dessus de `max` SHALL être considérées comme invalides par tout consommateur (UI, backend HTTP, scripts de validation).

#### Scenario: Bornes lisibles côté serveur
- **GIVEN** un paramètre `block` du module `pixelsnap` avec `min:2`, `max:32`
- **WHEN** un consommateur (Flask, frontend) reçoit une valeur `block:99999`
- **THEN** il SHALL la considérer comme invalide en se basant sur `PARAMS`, sans avoir à inspecter le code de la fonction
