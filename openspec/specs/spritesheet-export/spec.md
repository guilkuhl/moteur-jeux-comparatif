# spritesheet-export Specification

## Purpose
TBD - created by archiving change add-spritesheet-export. Update Purpose after archive.
## Requirements
### Requirement: Le dashboard doit exposer un panneau d'export avec 5 formats

Le dashboard MUST inclure un panneau `.export-panel` avec :
- `<select>` format : `png_atlas`, `json_phaser`, `xml_starling`, `css_sprites`, `individual`.
- Input `template` (texte, défaut `{basename}_{col}_{row}`).
- Checkbox `Inclure pivot`.
- Checkbox `Trim whitespace`.
- Bouton `Exporter` qui appelle `POST /api/export` et déclenche le téléchargement du ZIP retourné.

#### Scenario: Panneau opérationnel

- **WHEN** le dashboard est chargé et une image active a un slicing défini
- **THEN** le panneau `.export-panel` SHALL être visible et le bouton `Exporter` SHALL être cliquable

#### Scenario: Export désactivé sans slicing

- **GIVEN** une image active sans slicing défini
- **WHEN** on inspecte le panneau
- **THEN** le bouton `Exporter` SHALL être `disabled` avec un tooltip « Définis d'abord une grille dans le panneau Slicing »

### Requirement: Le serveur doit exposer une route POST /api/export qui retourne un ZIP

Le backend MUST exposer `POST /api/export` qui retourne un ZIP prêt à télécharger. La route accepte `{image, format, template, options: {pivot?, trim?}}` et retourne un ZIP (application/zip) avec `Content-Disposition: attachment`. Le ZIP contient :
- Pour formats atlas (png_atlas/json_phaser/xml_starling/css_sprites) : `atlas.png` + `atlas.{json,xml,css}`.
- Pour `individual` : un PNG par cellule non-ignorée, nommé selon le template.

Le serveur SHALL aussi sauvegarder le ZIP dans `outputs/<stem>/export/export_<timestamp>.zip`.

#### Scenario: Export PNG atlas + JSON Phaser

- **GIVEN** une image avec slicing 4×4 et format `json_phaser`
- **WHEN** `POST /api/export` est appelé
- **THEN** la réponse SHALL être un ZIP contenant `atlas.png` + `atlas.json` avec 16 entrées dans `frames`, la réponse SHALL avoir `Content-Disposition: attachment; filename="<basename>_phaser.zip"`, et une copie SHALL exister dans `outputs/<stem>/export/`

#### Scenario: Export sprites individuels

- **GIVEN** une image avec slicing 3×2 et 1 cellule ignorée, format `individual`
- **WHEN** `POST /api/export` est appelé
- **THEN** le ZIP SHALL contenir exactement 5 PNG (6 cellules - 1 ignorée), nommés selon le template

### Requirement: Le template de nommage doit supporter des variables paramétrables

Le template MUST supporter les variables `{basename}`, `{col}`, `{row}`, `{index}`, `{name}`.

Le template interprété doit :
- Remplacer `{basename}` par le nom de l'image source sans extension.
- Remplacer `{col}` et `{row}` par les coordonnées de la cellule dans la grille.
- Remplacer `{index}` par l'index 0-based dans l'ordre d'itération.
- Remplacer `{name}` par le nom custom de l'override si présent, sinon `{col}_{row}`.

En cas de collision de nom final entre deux cellules, un suffixe `_2`, `_3`… SHALL être ajouté automatiquement.

#### Scenario: Template basique

- **GIVEN** template `sprite_{col}_{row}` et cellule (3,2)
- **WHEN** le nom est résolu
- **THEN** il SHALL valoir `sprite_3_2`

#### Scenario: Template avec nom custom

- **GIVEN** template `{name}` et cellule (0,0) avec override name=`hero_idle`
- **WHEN** le nom est résolu
- **THEN** il SHALL valoir `hero_idle`

#### Scenario: Collision de noms

- **GIVEN** deux cellules avec le même nom custom `attack`
- **WHEN** l'export résout les noms
- **THEN** la première SHALL rester `attack`, la seconde SHALL devenir `attack_2`

### Requirement: Un override `pivot` doit être inclus dans l'export si l'option est cochée

Un nouvel override `{cellX, cellY, type:"pivot", x: 0..1, y: 0..1}` SHALL pouvoir être défini dans la config slicing. Si la checkbox `Inclure pivot` est cochée à l'export, le pivot SHALL apparaître dans le JSON/XML de sortie :

- JSON Phaser : `"pivot": {"x": 0.5, "y": 1.0}` dans chaque frame.
- XML Starling : attributs `frameX="..."` `frameY="..."` calculés depuis le pivot.
- CSS / individual : pas de pivot (ignoré).

#### Scenario: Pivot inclus

- **GIVEN** une cellule (0,0) avec override pivot={x:0.5, y:1.0} et checkbox `Inclure pivot` cochée, format json_phaser
- **WHEN** l'export génère le JSON
- **THEN** l'entrée de la frame SHALL contenir `"pivot": {"x": 0.5, "y": 1.0}`

