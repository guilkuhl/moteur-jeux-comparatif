## ADDED Requirements

### Requirement: Le comparateur SHALL afficher un HUD des coordonnées pixel sous le curseur

Quand la souris survole `#cmp-left` ou `#cmp-overlay`, un HUD flottant `#pixel-hud` MUST afficher les coordonnées pixel natives `x,y` (entiers, basés sur `naturalWidth/Height` et la scale courante) et la couleur `#RRGGBB` du pixel sous la souris. Le HUD SHALL se mettre à jour de manière fluide (throttlé à ~60 fps via `requestAnimationFrame`). Maintenir la touche `Shift` enfoncée SHALL figer le HUD (pas de mise à jour) pour permettre de le lire ou en copier le contenu.

#### Scenario: Coordonnées affichées

- **GIVEN** une image 512×512 affichée à zoom ×2 dans le comparateur
- **WHEN** l'utilisateur place la souris sur l'équivalent du pixel natif (100, 50)
- **THEN** le HUD SHALL afficher `100, 50` et la couleur `#RRGGBB` correspondante

#### Scenario: Freeze avec Shift

- **GIVEN** le HUD visible et la souris en mouvement
- **WHEN** l'utilisateur maintient la touche `Shift` et bouge la souris
- **THEN** le HUD SHALL conserver sa dernière valeur affichée jusqu'au relâchement de `Shift`

#### Scenario: HUD masqué hors du comparateur

- **GIVEN** la souris qui quitte la zone comparateur (sort vers la sidebar, la toolbar, ou hors page)
- **WHEN** l'événement `mouseleave` se produit
- **THEN** le HUD SHALL disparaître (display none ou opacity 0)

### Requirement: La toolbar du comparateur SHALL exposer un bouton `Δ Diff` qui surligne les pixels divergents entre source et iter

Un bouton `Δ Diff` MUST apparaître dans `.cmp-toolbar`. Au clic, un canvas overlay `#diff-overlay` SHALL être rendu par-dessus le comparateur (z-index entre `#cmp-overlay` et la toolbar). Ce canvas peint en rouge semi-transparent (`rgba(255,0,0,0.6)`) les pixels où `|lum(source) − lum(iter)| > 4`, et en vert (`rgba(0,255,0,0.6)`) les pixels n'existant qu'en iter (cas d'upscale par exemple). Un badge dans la toolbar indique `N pxs différents (p %)`.

Un second clic sur le bouton SHALL retirer l'overlay.

#### Scenario: Clic déclenche le calcul

- **GIVEN** une image source et un iter sélectionné à droite, différents
- **WHEN** l'utilisateur clique sur `Δ Diff`
- **THEN** un canvas `#diff-overlay` SHALL apparaître avec des zones rouges sur les pixels qui diffèrent, et le badge SHALL afficher le décompte

#### Scenario: Clic ferme l'overlay

- **GIVEN** l'overlay diff affichée
- **WHEN** l'utilisateur re-clique sur `Δ Diff`
- **THEN** le canvas `#diff-overlay` SHALL être retiré et le badge SHALL disparaître

#### Scenario: Image trop grande downscalée

- **GIVEN** une image source 4096×4096
- **WHEN** l'utilisateur clique sur `Δ Diff`
- **THEN** un warning visible SHALL indiquer « Diff downscalé à 2048 » et le calcul SHALL se faire sur une version downscalée avant affichage (perf)

### Requirement: Le dashboard doit exposer des raccourcis clavier pour naviguer entre les iters

Quand le focus n'est pas sur un `input/textarea/select` et qu'une image active a au moins un iter, le dashboard MUST implémenter les raccourcis suivants :

- `←` SHALL sélectionner l'iter précédent dans l'ordre actuel du panneau historique.
- `→` SHALL sélectionner l'iter suivant.
- `Home` SHALL sélectionner le premier iter (plus ancien ou plus récent selon l'ordre de tri courant).
- `End` SHALL sélectionner le dernier.
- `Esc` SHALL revenir à l'iter le plus récent (comportement par défaut).

Chaque raccourci SHALL mettre à jour `compareRight` et rafraîchir le comparateur exactement comme le ferait un clic souris sur l'iter correspondant.

#### Scenario: Navigation avec flèches

- **GIVEN** une image active avec 5 iters et l'iter #2 sélectionné
- **WHEN** l'utilisateur appuie sur `→`
- **THEN** l'iter #3 SHALL devenir `compareRight` et le comparateur SHALL se mettre à jour

#### Scenario: Raccourci ignoré dans un input

- **GIVEN** le focus sur `#bg-tolerance` et plusieurs iters dispos
- **WHEN** l'utilisateur appuie sur `←`
- **THEN** le curseur dans le champ SHALL bouger normalement et `compareRight` SHALL rester inchangé

#### Scenario: Cheat-sheet via `?`

- **GIVEN** le focus sur le document (pas dans un input)
- **WHEN** l'utilisateur appuie sur `?` ou `F1`
- **THEN** un overlay `#kbd-help` SHALL s'afficher listant : `H` historique, `G` grille, `Esc` reset iter, `←→` navigation iters, `Shift` fige HUD, `? / F1` aide

### Requirement: Les entrées orphelines de history.json SHALL être détectées, filtrées par défaut, et proposées au nettoyage

Au chargement du dashboard, après la récupération de `/api/inputs`, le dashboard MUST comparer les basenames de `history.json` à ceux de `/api/inputs`. Toute entrée dans `history.json` sans fichier source correspondant dans `inputs/` est marquée **orpheline**.

Les entrées orphelines SHALL être masquées par défaut dans la sidebar. Un badge `N orphelins` SHALL apparaître en bas de la sidebar avec un bouton `🗑 Nettoyer`. Au clic :

1. Une modal de confirmation liste les N entrées avec leur nom et le nombre d'iters perdus.
2. Si confirmé, le dashboard envoie `POST /api/history/prune` avec la liste des basenames à retirer.
3. Le serveur retire les entrées de `history.json` et déplace chaque dossier `outputs/<stem>/` vers `outputs/_trash/<stem>_<timestamp>/`.
4. La sidebar se rafraîchit ; le badge `N orphelins` disparaît.

#### Scenario: Orphelins masqués par défaut

- **GIVEN** `history.json` référence 7 entrées et `inputs/` ne contient que 3 PNG/webp existants
- **WHEN** le dashboard charge
- **THEN** la sidebar SHALL afficher uniquement les 3 entrées valides ; un badge `4 orphelins` SHALL être visible en bas

#### Scenario: Nettoyage avec confirmation

- **GIVEN** le badge `4 orphelins` visible
- **WHEN** l'utilisateur clique `🗑 Nettoyer` et confirme la modal
- **THEN** `POST /api/history/prune` SHALL être appelé avec la liste des 4 basenames, le serveur SHALL les retirer de `history.json` et archiver leurs dossiers `outputs/`, et le badge SHALL disparaître

#### Scenario: Annulation

- **GIVEN** la modal de confirmation ouverte
- **WHEN** l'utilisateur clique `Annuler`
- **THEN** aucun appel serveur n'SHALL être émis, la modal se ferme, et l'état orphelin reste inchangé

### Requirement: Le serveur SHALL exposer `POST /api/history/prune` pour purger les entrées orphelines

Le backend Flask (`pixel-lab/server/app.py`) MUST exposer une nouvelle route `POST /api/history/prune` qui accepte un JSON `{basenames: string[]}` et, pour chaque nom :

1. Retire l'entrée correspondante de `pixel-lab/history.json`.
2. Déplace `pixel-lab/outputs/<basename_without_ext>/` vers `pixel-lab/outputs/_trash/<basename_without_ext>_<YYYYmmdd-HHMMSS>/`.
3. Renvoie `{pruned: [...basenames réellement traités], skipped: [...basenames invalides]}`.

La route MUST refuser tout basename qui n'est pas déjà orphelin (fichier source présent dans `inputs/`) pour éviter toute purge accidentelle d'une image active.

#### Scenario: Purge réussie

- **GIVEN** 2 basenames orphelins dans `history.json`
- **WHEN** le client envoie `POST /api/history/prune` avec les 2 basenames
- **THEN** les 2 entrées SHALL être retirées de `history.json`, leurs dossiers `outputs/` déplacés dans `outputs/_trash/`, et la réponse SHALL contenir les 2 basenames dans `pruned` et `[]` dans `skipped`

#### Scenario: Refus d'une entrée non-orpheline

- **GIVEN** un basename présent à la fois dans `history.json` ET dans `inputs/` (image active)
- **WHEN** le client tente de le purger via `POST /api/history/prune`
- **THEN** la route SHALL refuser et inclure le basename dans `skipped` avec une raison `"source file still present"`, aucune modification ne SHALL avoir lieu pour ce basename
