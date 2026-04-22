## ADDED Requirements

### Requirement: Le dashboard doit exposer un panneau de contraintes pixel

Le dashboard MUST inclure un panneau `.constraints-panel` contenant les contrôles suivants :

- Checkbox `Activer contraintes` (master toggle).
- Input numérique `Taille multiple de N` (1-1024, défaut 16, désactivé si POT actif).
- Checkbox `Forcer POT` (puissance de 2).
- Input `Padding interne` (0-32 px, défaut 0).
- Input `Marge extérieure` (0-64 px, défaut 0).
- Checkbox `Rognage auto whitespace`.
- Input `Marge post-rognage` (0-16 px, défaut 0).
- Bouton `Valider contraintes`.
- Bouton `Corriger auto` (désactivé tant qu'aucune violation n'est détectée).
- Zone `#constraint-report` repliable listant les violations.

#### Scenario: Panneau visible et contrôles présents

- **GIVEN** le dashboard chargé
- **WHEN** on inspecte `.constraints-panel`
- **THEN** les 8 contrôles listés ci-dessus SHALL être présents et accessibles

### Requirement: La validation des contraintes doit être non-destructive et afficher un rapport visuel

Au clic sur `Valider contraintes`, le dashboard MUST appeler `POST /api/constraints/validate` avec le payload `{image, constraints, grid}`. La réponse contient un tableau `violations: [{cellX, cellY, issue, suggestion}]`.

Pour chaque violation :
- Une overlay rouge semi-transparente (`rgba(239,96,96,0.35)`) MUST être peinte sur la cellule concernée dans le comparateur.
- Un badge rouge court (ex. « 17px ≠ mul16 ») MUST apparaître sur la cellule.
- Une entrée descriptive MUST être ajoutée à `#constraint-report`, triée par sévérité.

Aucun recadrage ou modification de l'image source ne SHALL être appliqué lors de la validation — seule l'affichage est modifié.

#### Scenario: Cellule de 17 px avec contrainte multiple de 16

- **GIVEN** une cellule identifiée à (3, 2) de largeur 17 px, la contrainte `multiple de 16` active
- **WHEN** l'utilisateur clique `Valider contraintes`
- **THEN** la cellule (3, 2) SHALL recevoir une overlay rouge et un badge « 17px ≠ mul16 », une entrée « Cellule (3,2) : largeur 17 px, attendu multiple de 16 (suggestion : rogner à 16 ou padder à 32) » SHALL être ajoutée à `#constraint-report`, et l'image source SHALL rester inchangée

#### Scenario: Toutes contraintes respectées

- **GIVEN** toutes les cellules respectent les contraintes actives
- **WHEN** l'utilisateur clique `Valider contraintes`
- **THEN** `#constraint-report` SHALL afficher « Aucune violation détectée », aucune overlay rouge ne SHALL être peinte, et le bouton `Corriger auto` SHALL rester désactivé

### Requirement: La correction automatique doit être opt-in et granulaire

Le bouton `Corriger auto` MUST ouvrir une modal listant chaque violation avec une action proposée. Chaque action :

- est accompagnée d'une case à cocher initialement **cochée**.
- affiche un preview avant/après de la cellule (si possible).
- peut être de type : `ROGNER`, `PADDER`, `CENTRER`.

Au clic sur `Appliquer`, le dashboard MUST envoyer `POST /api/constraints/apply` avec `{image, corrections: [{cellX, cellY, action, params}]}`. Le serveur SHALL produire une nouvelle image corrigée et la sauvegarder comme nouvelle iter dans `outputs/<stem>/`.

#### Scenario: Corrections sélectives

- **GIVEN** 5 violations détectées, la modal ouverte
- **WHEN** l'utilisateur décoche 2 actions et clique `Appliquer`
- **THEN** `POST /api/constraints/apply` SHALL être appelé avec uniquement les 3 corrections cochées, et l'iter produite SHALL refléter ces 3 corrections uniquement

### Requirement: Le serveur doit exposer les routes de validation et de correction des contraintes

Le backend MUST exposer `POST /api/constraints/validate` et `POST /api/constraints/apply`.

**`POST /api/constraints/validate`** accepte `{image: string, grid: {cols, rows, cellW, cellH, overrides?}, constraints: {mulN?, pot?, paddingInner?, marginOuter?, trimWhitespace?, marginPostTrim?}}` et retourne `{violations: [{cellX, cellY, issue, suggestion}]}`.

**`POST /api/constraints/apply`** accepte `{image, corrections: [{cellX, cellY, action, params}]}` et retourne `{iterPath, dimensions}`, après avoir généré et sauvegardé l'image corrigée.

#### Scenario: Validate nominal

- **WHEN** un client envoie `POST /api/constraints/validate` avec une image et 1 violation évidente
- **THEN** le serveur SHALL retourner `200 {violations: [{...}]}` avec l'entrée détaillée

#### Scenario: Apply produit une nouvelle iter

- **WHEN** `POST /api/constraints/apply` est appelé avec 2 corrections
- **THEN** un nouveau fichier `iter_NNN_constraints.png` SHALL exister dans `outputs/<stem>/`, `history.json` SHALL contenir l'entrée correspondante, et la réponse SHALL inclure le path relatif
