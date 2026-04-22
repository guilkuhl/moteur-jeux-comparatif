## Why

Une fois un spritesheet découpé et validé, il doit être exportable dans les formats consommés par les moteurs de jeu. Les formats JSON (TexturePacker, Phaser), XML (Starling, Phaser 2), CSS sprites et PNG atlas sont les plus courants. L'export inclut aussi un mode "sprites individuels" (un PNG par cellule dans un zip/dossier) et un nommage automatique cohérent.

## What Changes

- **Panneau `Export`** avec :
  - Select format : `PNG atlas`, `JSON (Phaser)`, `XML (Starling)`, `CSS sprites`, `Sprites individuels`.
  - Input `Template de nom` (défaut `{basename}_{col}_{row}` avec variables `{basename}, {col}, {row}, {index}, {name}`).
  - Checkbox `Inclure offset pivot` (point de pivot par cellule, stocké dans les overrides).
  - Checkbox `Trim whitespace à l'export`.
  - Bouton `Exporter`.
- Nouvelle route `POST /api/export` qui reçoit `{image, slicing, format, template, options}` et retourne :
  - Pour PNG atlas : le PNG packé + un JSON/XML/CSS compagnon.
  - Pour sprites individuels : un ZIP contenant tous les PNG.
- Le résultat est téléchargé via le navigateur (blob URL).

## Capabilities

### New Capabilities
- `spritesheet-export`: export d'un spritesheet en PNG atlas + JSON/XML/CSS, ou en sprites individuels, avec nommage paramétrable et pivot optionnel.

### Modified Capabilities
- `pixel-art-dashboard`: ajout du panneau Export.

## Impact

- **Frontend** : panneau Export, déclencheur de téléchargement.
- **Backend** : route `POST /api/export`, générateurs pour chaque format (JSON, XML, CSS), packer PNG atlas, ZIP writer pour sprites individuels (stdlib zipfile).
- **Dépendances** : nécessite `spritesheet-slicing` pour avoir la définition des cellules.
