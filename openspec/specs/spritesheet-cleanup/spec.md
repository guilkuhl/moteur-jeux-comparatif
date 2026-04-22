# spritesheet-cleanup Specification

## Purpose
TBD - created by archiving change add-spritesheet-cleanup. Update Purpose after archive.
## Requirements
### Requirement: Le dashboard doit offrir une vue grille-miniatures pour réordonner les frames par drag-drop

Un panneau `.cleanup-frames-view` MUST afficher toutes les cellules non-ignorées sous forme de miniatures (128×128 max) dans un ordre initial row-major. L'utilisateur MUST pouvoir glisser-déposer chaque miniature pour redéfinir l'ordre. L'ordre résultant est stocké comme override `{type:"order", value: N}` par cellule.

#### Scenario: Drag-drop réordonne

- **GIVEN** 16 cellules en ordre row-major
- **WHEN** l'utilisateur drag-drop la cellule (0,0) en 10e position
- **THEN** toutes les cellules SHALL recevoir un override `order` avec la nouvelle valeur, et le PUT slicing SHALL persister l'ordre

### Requirement: La détection de doublons doit proposer un recensement avant action

Bouton `Détecter doublons` → `POST /api/cleanup/detect-duplicates` avec `{image, similarity_threshold?}`. Le serveur calcule un phash 8×8 par cellule et renvoie les paires dont la distance de Hamming ≤ 5 bits. Le dashboard MUST afficher les paires dans une modal avec preview côte à côte et 3 actions par paire :

- `Marquer le second comme ignoré` (ajoute override `ignore`).
- `Aliaser les deux` (attribue le même nom aux deux).
- `Garder les deux` (pas d'action).

#### Scenario: Paire identifiée et ignorée

- **GIVEN** 2 cellules pixel-identiques en (1,0) et (5,2)
- **WHEN** l'utilisateur clique `Marquer le second comme ignoré` sur la paire
- **THEN** l'override `ignore` SHALL être ajouté pour (5,2), et la modal SHALL afficher le statut « traité »

### Requirement: La détection de décalage sous-pixel doit proposer un recalage validé

Bouton `Détecter décalages` → `POST /api/cleanup/detect-subpixel` qui applique une phase correlation entre chaque cellule et son successeur dans l'ordre logique. Les cellules avec `0.2 < |Δ| < 2.5 px` SHALL être listées avec le décalage détecté et une action :

- `Recaler (arrondi entier)` : recadre la cellule de ±1/2 px vers l'alignement idéal.
- `Resample sous-pixel` : interpolation bilinéaire pour corriger le décalage.
- `Ignorer`.

L'action SHALL produire une nouvelle iter corrigée (pas de modification in-place de l'image source).

#### Scenario: Décalage détecté et recalé

- **GIVEN** une cellule décalée de (0.7, 1.2) px par rapport à son voisin
- **WHEN** l'utilisateur clique `Recaler (arrondi entier)`
- **THEN** une nouvelle iter SHALL être produite avec cette cellule décalée de (1, 1) px, et l'iter SHALL apparaître dans la liste de `history.json`

### Requirement: La normalisation taille uniforme doit proposer un plan et produire une iter

Le dashboard MUST proposer un bouton `Normaliser`. Bouton `Normaliser` → détecte les tailles uniques parmi les cellules non-ignorées. Si plus d'une taille existe, affiche une modal avec :
- Liste des tailles détectées.
- Taille cible proposée = dimensions maximales rencontrées (ex. 17×16 → cible 17×17).
- Options d'alignement : `centré`, `haut-gauche`, `bas-gauche`.
- Preview avant/après.

Au `Appliquer`, `POST /api/cleanup/normalize` produit un nouvel atlas où toutes les cellules sont paddées à la taille cible, et une nouvelle iter est sauvegardée.

#### Scenario: Cellules mixtes uniformisées

- **GIVEN** 10 cellules dont 8 en 16×16 et 2 en 17×16
- **WHEN** l'utilisateur clique `Normaliser`, accepte la taille cible 17×17, alignement centré
- **THEN** une nouvelle iter SHALL contenir 10 cellules toutes en 17×17, chaque cellule originale centrée avec padding transparent

### Requirement: Un rapport d'anomalies consolidé doit être exportable

Le dashboard MUST proposer un bouton `Exporter rapport` qui SHALL appeler `GET /api/cleanup/report?image=<basename>` renvoie un JSON structuré avec :
- `duplicates`: paires détectées.
- `subpixel_shifts`: décalages > 0.2 px.
- `size_variants`: dimensions uniques + dominante.
- `empty_cells`: cellules entièrement transparentes.
- `constraint_violations`: liste des violations de contraintes (si capability activée).

Le rapport SHALL être téléchargé comme fichier `<basename>_report.json`.

#### Scenario: Rapport exporté

- **GIVEN** une image avec 2 doublons, 1 décalage, 3 tailles différentes
- **WHEN** l'utilisateur clique `Exporter rapport`
- **THEN** un fichier `<basename>_report.json` SHALL être téléchargé avec les 3 sections renseignées

