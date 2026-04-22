## ADDED Requirements

### Requirement: Le dashboard doit exposer un panneau de découpage spritesheet

Le dashboard MUST inclure un panneau `.slicing-panel` avec les contrôles suivants :
- Inputs `cols`, `rows` (1-256).
- Inputs `cellW`, `cellH` (1-1024 px).
- Inputs `gapX`, `gapY` (0-64 px).
- Inputs `marginX`, `marginY` (0-64 px).
- Bouton `Appliquer` qui persiste la config via `PUT /api/slicing/<basename>`.
- Bouton `Éditer cellules…` qui active le mode override.

#### Scenario: Panneau présent et opérationnel

- **WHEN** le dashboard est chargé et on inspecte `.slicing-panel`
- **THEN** tous les 8 contrôles SHALL être présents et le bouton `Appliquer` SHALL écrire la config dans `history.json` via l'API

### Requirement: Une grille de base plus des overrides doivent pouvoir être définis par image

La config SHALL être stockée sous `history[basename].slicing` avec la structure `{base: {...}, overrides: [...]}`. Chaque override identifie une cellule par `{cellX, cellY}` et a un `type` parmi `{resize, merge, ignore, name}` avec les params associés.

Le serveur MUST rejeter toute config où :
- Un override `merge` chevauche un autre override (sauf si le second est dans la zone fusionnée).
- Un override référence une cellule hors grille (`cellX >= cols` ou `cellY >= rows`).

#### Scenario: Config valide acceptée

- **GIVEN** une grille 8×4 avec 3 overrides non-conflictuels
- **WHEN** le client envoie `PUT /api/slicing/sprite.png`
- **THEN** la config SHALL être écrite dans `history.json` et la réponse SHALL être `200`

#### Scenario: Chevauchement rejeté

- **GIVEN** un override `merge` en (2,0) de 2×1 et un autre override `resize` en (3,0)
- **WHEN** le client tente de sauvegarder
- **THEN** la réponse SHALL être `400 {error: "overlap", details: "..."}`

### Requirement: Le mode édition doit permettre clic-to-override sur une cellule

Au clic sur `Éditer cellules…`, le dashboard MUST :
- Appliquer `cursor: crosshair` sur le comparateur.
- Capturer les clics sur le canvas slicing-overlay pour déterminer la cellule cliquée.
- Ouvrir un popover avec 4 boutons : `Redimensionner`, `Fusionner…`, `Ignorer`, `Nommer`.

`Esc` SHALL quitter le mode édition.

#### Scenario: Activation mode édition

- **WHEN** l'utilisateur clique `Éditer cellules…`
- **THEN** le bouton SHALL prendre la classe `.active`, le curseur SHALL devenir crosshair, et un clic sur une cellule SHALL ouvrir le popover d'override

#### Scenario: Sortie du mode édition

- **GIVEN** le mode édition actif
- **WHEN** l'utilisateur appuie sur `Esc`
- **THEN** le bouton SHALL perdre la classe `.active`, le curseur SHALL redevenir par défaut, et tout popover ouvert SHALL se fermer

### Requirement: Les cellules doivent être numérotées et surlignées au survol

Un canvas `#slicing-overlay` MUST dessiner :
- Une bordure de 1 px par cellule, couleur `rgba(124,111,239,0.5)`.
- Un badge texte `col,row` (ex. `3,2`) à l'angle supérieur gauche de chaque cellule, font 10 px, couleur `#7c6fef`.
- Si un override `name` est défini, le badge SHALL afficher le nom custom au lieu des coordonnées.
- Au survol souris, la cellule sous le curseur SHALL recevoir une overlay jaune `rgba(255,224,96,0.2)` et une bordure 2 px jaune.

Les cellules avec override `ignore` SHALL être dessinées avec une diagonale barrée et une teinte gris foncé.

#### Scenario: Numerotation standard

- **GIVEN** une grille 4×2 sans overrides
- **WHEN** on inspecte `#slicing-overlay`
- **THEN** 8 badges de coordonnées SHALL être dessinés (`0,0`, `1,0`, …, `3,1`)

#### Scenario: Nom custom remplace coords

- **GIVEN** un override `{cellX:0, cellY:0, type:"name", name:"hero_idle"}`
- **WHEN** on inspecte le badge de la cellule (0,0)
- **THEN** il SHALL afficher `hero_idle` au lieu de `0,0`

#### Scenario: Cellule ignorée barrée

- **GIVEN** un override `{cellX:7, cellY:3, type:"ignore"}`
- **WHEN** on inspecte la cellule (7,3)
- **THEN** elle SHALL être dessinée avec une diagonale barrée visible et une teinte gris foncé

### Requirement: Le serveur doit exposer GET et PUT pour persister la config de slicing

Le backend MUST exposer deux routes :
- `GET /api/slicing/<basename>` SHALL retourner la config `slicing` de l'image ou `{base: null, overrides: []}` si absente.
- `PUT /api/slicing/<basename>` SHALL accepter `{base, overrides}` dans le body, valider la cohérence, écrire dans `history.json`, retourner la config écrite.

#### Scenario: GET absent

- **GIVEN** une image sans slicing défini
- **WHEN** le client appelle `GET /api/slicing/sprite.png`
- **THEN** la réponse SHALL être `200 {base: null, overrides: []}`

#### Scenario: PUT nominal

- **GIVEN** une config valide
- **WHEN** le client appelle `PUT /api/slicing/sprite.png` avec le payload
- **THEN** la réponse SHALL être `200` avec la config écrite, et `history.json` SHALL avoir été mis à jour
