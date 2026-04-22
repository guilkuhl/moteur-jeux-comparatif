## ADDED Requirements

### Requirement: La sidebar SHALL accepter le drag-drop d'un fichier image pour l'uploader dans `inputs/`

La `.sidebar` MUST écouter les events `dragenter / dragover / dragleave / drop`. Pendant un drag actif (fichier survolant la sidebar), la sidebar SHALL afficher un indicateur visuel (classe CSS `.dragging-over` : halo violet + bordure pointillée) ainsi qu'un overlay « Dépose l'image ici » (`#drop-hint`).

Au drop :
1. Le dashboard valide côté client que le fichier a une extension dans `{.png, .webp, .jpg, .jpeg}` et une taille ≤ 20 MB. Toute violation SHALL produire un toast rouge explicite (« Format non supporté » / « Fichier trop gros (> 20 MB) ») sans appel serveur.
2. Si validation OK, le client envoie `POST /api/inputs` multipart avec le fichier.
3. Sur 200 OK, la sidebar se rafraîchit (`loadHistory()`), l'image nouvellement uploadée devient `activeImage`, et un toast vert confirme « X ajouté aux inputs ».
4. Sur 409 Conflict (nom existe déjà), le client propose le `suggestion` renvoyé par le serveur et re-tente sur confirmation de l'utilisateur.
5. Sur 4xx / 5xx autre, un toast rouge affiche l'erreur.

Si plusieurs fichiers sont droppés simultanément (`files.length > 1`), le dashboard SHALL afficher un toast « Dépose un fichier à la fois » et rejeter le drop.

#### Scenario: Drop d'un PNG valide

- **GIVEN** la sidebar visible et un fichier `sprite.png` de 2 MB
- **WHEN** l'utilisateur drag-drop `sprite.png` sur la sidebar
- **THEN** `POST /api/inputs` SHALL être émis, la sidebar SHALL se rafraîchir avec `sprite.png` présent, `activeImage === "sprite.png"`, et un toast vert « sprite.png ajouté aux inputs » SHALL apparaître

#### Scenario: Rejet d'un fichier non-image

- **GIVEN** un fichier `document.pdf`
- **WHEN** l'utilisateur le drop sur la sidebar
- **THEN** aucun appel réseau SHALL être émis, un toast rouge « Format non supporté » SHALL apparaître

#### Scenario: Rejet d'un fichier trop gros

- **GIVEN** un PNG de 25 MB
- **WHEN** l'utilisateur le drop sur la sidebar
- **THEN** aucun appel réseau SHALL être émis, un toast rouge « Fichier trop gros (> 20 MB) » SHALL apparaître

#### Scenario: Conflit de nom

- **GIVEN** `sprite.png` déjà présent dans `inputs/`
- **WHEN** l'utilisateur drop un nouveau `sprite.png`
- **THEN** le serveur SHALL renvoyer `409 Conflict` avec `{suggestion: "sprite-2.png"}`, et le client SHALL proposer à l'utilisateur d'uploader sous ce nouveau nom

### Requirement: Chaque `.img-item` de la sidebar SHALL exposer un menu contextuel avec une action `🗑 Supprimer`

Un bouton discret `⋯` (3 points verticaux) MUST apparaître à droite de chaque `.img-item` au hover, et le clic-droit sur un `.img-item` MUST ouvrir le même menu. Le menu propose a minima :

- `🗑 Supprimer` — ouvre une modal de confirmation.

Au clic sur `🗑 Supprimer` puis confirmation :
1. Le client émet `DELETE /api/inputs/<basename>`.
2. Sur 200 OK, l'entrée disparaît de la sidebar, `history.json` est mis à jour côté serveur, le fichier source est archivé dans `inputs/_trash/`, et le dossier `outputs/<stem>/` associé est archivé dans `outputs/_trash/`.
3. Un toast vert confirme « X supprimé (archivé dans _trash/) ».
4. Si l'image supprimée était active, une autre image (la suivante ou la plus récente) devient active.

#### Scenario: Suppression confirmée

- **GIVEN** `sprite.png` présent avec 12 iters dans `outputs/sprite/`
- **WHEN** l'utilisateur ouvre le menu `⋯` de `sprite.png`, clique `🗑 Supprimer`, et confirme la modal
- **THEN** `DELETE /api/inputs/sprite.png` SHALL être émis, `sprite.png` SHALL disparaître de la sidebar, `inputs/_trash/sprite_<timestamp>.png` et `outputs/_trash/sprite_<timestamp>/` SHALL exister

#### Scenario: Annulation de la modal

- **GIVEN** la modal de confirmation ouverte
- **WHEN** l'utilisateur clique `Annuler`
- **THEN** aucun appel SHALL être émis, la modal se ferme, l'image reste présente

#### Scenario: Clic-droit ouvre le menu

- **GIVEN** un `.img-item` dans la sidebar
- **WHEN** l'utilisateur fait un clic-droit dessus
- **THEN** le menu contextuel SHALL s'ouvrir exactement comme sur clic du bouton `⋯`

### Requirement: Le serveur doit exposer des routes d'upload et de suppression d'images source

Le backend Flask MUST exposer deux nouvelles routes : `POST /api/inputs` pour uploader une image source et `DELETE /api/inputs/<basename>` pour la supprimer (via archive).

**`POST /api/inputs`** (multipart form-data, champ `file`) :
- Valide que l'extension du filename est dans `{.png, .webp, .jpg, .jpeg}`.
- Valide que la taille ≤ 20 MB (`MAX_CONTENT_LENGTH`).
- Sanitize le basename (trim, remplacer caractères non `[A-Za-z0-9._\- ]` par `_`).
- Si le fichier existe déjà → `409 Conflict` avec `{error: "exists", suggestion: "<name>-2.<ext>"}`.
- Sinon écrit dans `pixel-lab/inputs/` et répond `200 {basename, size}`.

**`DELETE /api/inputs/<basename>`** :
- Si le fichier n'existe pas → `404`.
- Sinon : déplace `inputs/<basename>` vers `inputs/_trash/<stem>_<YYYYmmdd-HHMMSS><ext>`, déplace `outputs/<stem>/` vers `outputs/_trash/<stem>_<YYYYmmdd-HHMMSS>/` s'il existe, retire l'entrée de `history.json` (atomic write), répond `200 {archivedSource, archivedOutputs}`.

#### Scenario: Upload nominal

- **WHEN** un `POST /api/inputs` avec un PNG valide de 2 MB est émis
- **THEN** le serveur SHALL répondre `200 {basename, size: 2000000}` et le fichier SHALL exister dans `pixel-lab/inputs/`

#### Scenario: Upload refusé pour taille

- **WHEN** un `POST /api/inputs` avec un fichier > 20 MB est émis
- **THEN** le serveur SHALL répondre `413 Request Entity Too Large` avec un message clair

#### Scenario: Suppression nominale

- **GIVEN** `sprite.png` présent dans `inputs/` avec `outputs/sprite/` contenant 5 iters
- **WHEN** `DELETE /api/inputs/sprite.png` est appelé
- **THEN** `inputs/_trash/sprite_<ts>.png` et `outputs/_trash/sprite_<ts>/` SHALL exister, `inputs/sprite.png` et `outputs/sprite/` n'SHALL PLUS exister, et l'entrée `sprite.png` SHALL avoir disparu de `history.json`

#### Scenario: Suppression d'une image inexistante

- **WHEN** `DELETE /api/inputs/ghost.png` est appelé alors qu'aucun fichier de ce nom n'existe
- **THEN** le serveur SHALL répondre `404`
