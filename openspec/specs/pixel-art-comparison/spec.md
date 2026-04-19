# pixel-art-comparison Specification

## Purpose
Générer, en une seule commande, toutes les variantes `algo × méthode` (et combos prédéfinis) sur une image donnée afin de pouvoir les comparer visuellement dans le dashboard et sélectionner le meilleur traitement. Source de vérité : `pixel-lab/scripts/compare_snap.py`.

## Requirements

### Requirement: Le script SHALL produire en mode exhaustif une itération par combinaison algo × méthode
Le script `compare_snap.py` MUST, par défaut, appliquer chaque méthode disponible de chaque algorithme (`sharpen`, `denoise`, `pixelsnap`) à l'image source, et créer une itération dans `outputs/<image>/` pour chaque combinaison.

#### Scenario: Parcours exhaustif
- **GIVEN** une image `inputs/fireball.png`
- **WHEN** on exécute `python scripts/compare_snap.py inputs/fireball.png`
- **THEN** pour chaque `(algo, method)` disponible dans `sharpen × {unsharp_mask, laplacian, kernel}`, `denoise × {median, bilateral, nlm}` et `pixelsnap × {median, mode, mean}`, une itération SHALL être produite dans `outputs/fireball/`

### Requirement: Le script SHALL également produire des combos prédéfinis
Le script MUST appliquer au moins deux chaînes de traitement prédéfinies : `pixelsnap/median → sharpen/unsharp_mask` et `denoise/median → pixelsnap/median → sharpen`.

#### Scenario: Combo pixelsnap → sharpen
- **GIVEN** l'exécution par défaut
- **WHEN** le script termine
- **THEN** une itération labellisée `pipeline_pixelsnap+unsharp_mask` (ou équivalente documentée) SHALL exister dans `outputs/<image>/`

### Requirement: L'option `--scale` SHALL inclure les variantes d'upscale
Le script MUST accepter `--scale 2` pour ajouter les variantes `scale2x × {nearest, scale2x, eagle2x}` au parcours exhaustif.

#### Scenario: Scale 2
- **GIVEN** la commande `python scripts/compare_snap.py inputs/fireball.png --scale 2`
- **WHEN** le script termine
- **THEN** au moins trois itérations supplémentaires `iter_XXX_scale2x_{nearest|scale2x|eagle2x}.png` SHALL être produites avec des dimensions doublées

### Requirement: L'option `--only` SHALL restreindre l'exploration à un algorithme
Le script MUST accepter `--only <algo>` (ex. `pixelsnap`) pour ne générer que les variantes de cet algorithme.

#### Scenario: Filtre pixelsnap
- **GIVEN** la commande `python scripts/compare_snap.py inputs/fireball.png --only pixelsnap`
- **WHEN** le script s'exécute
- **THEN** exactement trois itérations SHALL être produites, une par méthode de `pixelsnap` (`median`, `mode`, `mean`), et aucune itération `sharpen` / `denoise` SHALL être créée

### Requirement: L'option `--block` SHALL contrôler la taille de bloc du pixelsnap
Le script MUST accepter `--block <N>` (défaut documenté dans le script) et le transmettre aux méthodes `pixelsnap` lors du parcours.

#### Scenario: Block 4
- **GIVEN** la commande `python scripts/compare_snap.py inputs/fireball.png --block 4`
- **WHEN** les variantes `pixelsnap` sont générées
- **THEN** chaque méthode `pixelsnap` SHALL être appelée avec `block=4` et la taille de bloc SHALL apparaître dans le nom ou les paramètres loggués dans `history.json`

### Requirement: Chaque itération produite SHALL être traçable dans history.json
Chaque variante générée par `compare_snap.py` MUST être consignée dans `history["<image>"].runs` avec les mêmes champs que pour `process.py` (algo, méthode, paramètres, chemin d'itération, date ISO).

#### Scenario: Traçabilité de toutes les variantes
- **GIVEN** un parcours complet qui produit 12 itérations
- **WHEN** le script termine
- **THEN** `history["<image>"].runs` SHALL contenir 12 entrées supplémentaires, chacune pointant vers un fichier existant dans `outputs/<image>/`
