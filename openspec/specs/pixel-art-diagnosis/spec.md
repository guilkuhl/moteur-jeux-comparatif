# pixel-art-diagnosis Specification

## Purpose
Analyser automatiquement une image pixel-art avant traitement pour mesurer six indicateurs de qualité (flou, artefacts JPEG, interpolation, bruit, palette, résolution effective) et recommander les traitements adaptés. Source de vérité : `pixel-lab/scripts/diagnose.py`.

## Requirements

### Requirement: Le diagnostic SHALL mesurer six indicateurs objectifs
La fonction `diagnose(img)` MUST produire un rapport contenant au minimum : variance du Laplacien (flou), énergie sur les bords 8 × 8 (artefacts JPEG), détection de gradients lissés (interpolation), variance locale (bruit), nombre de couleurs uniques (palette) et ratio de pixels identiques entre voisins (résolution effective).

#### Scenario: Structure du rapport
- **GIVEN** une image PIL passée à `diagnose`
- **WHEN** la fonction retourne son rapport
- **THEN** le rapport SHALL inclure les clés `blur`, `jpeg_artifacts`, `interpolation`, `noise`, `palette_size`, `effective_resolution` avec des valeurs numériques

### Requirement: La CLI `diagnose.py` SHALL offrir trois modes de sortie
Le script `diagnose.py` MUST supporter un rendu humain (par défaut), une sortie JSON brute via `--json` et un enregistrement dans `history.json` via `--save`.

#### Scenario: Sortie JSON
- **GIVEN** la commande `python scripts/diagnose.py inputs/sprite.png --json`
- **WHEN** le script s'exécute
- **THEN** la sortie standard SHALL être un document JSON valide contenant les six indicateurs

#### Scenario: Enregistrement dans l'historique
- **GIVEN** la commande `python scripts/diagnose.py inputs/sprite.png --save`
- **WHEN** le script s'exécute
- **THEN** une entrée `diagnosis` SHALL être ajoutée à `history["sprite"]` avec les six indicateurs et un timestamp ISO

### Requirement: Le diagnostic SHALL produire un rapport lisible humain
Par défaut, la fonction `print_report(report)` MUST afficher chaque indicateur avec son nom, sa valeur et une interprétation qualitative (ex. "flou : élevé", "palette : 16 couleurs = pixel-art pur").

#### Scenario: Rapport humain
- **GIVEN** un rapport produit par `diagnose`
- **WHEN** `print_report` est appelé
- **THEN** la sortie SHALL comporter une ligne par indicateur avec une étiquette en français et un libellé qualitatif

### Requirement: Le diagnostic SHALL produire des recommandations de traitement ordonnées
La fonction `build_recommendations(report)` MUST retourner une liste ordonnée d'étapes recommandées (ex. `[{"algo":"denoise","method":"median"}, {"algo":"pixelsnap","method":"median"}, {"algo":"sharpen","method":"unsharp_mask"}]`) basée sur les seuils franchis par les indicateurs.

#### Scenario: Image bruitée et floue
- **GIVEN** un rapport avec `noise` élevé et `blur` élevé
- **WHEN** `build_recommendations` s'exécute
- **THEN** la liste retournée SHALL commencer par une étape `denoise`, suivie d'une étape `sharpen`

#### Scenario: Image déjà propre
- **GIVEN** un rapport dont tous les indicateurs sont sous les seuils problématiques
- **WHEN** `build_recommendations` s'exécute
- **THEN** la liste retournée SHALL être vide ou réduite à une étape optionnelle marquée comme non critique
