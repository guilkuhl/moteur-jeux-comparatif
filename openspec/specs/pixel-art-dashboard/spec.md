# pixel-art-dashboard Specification

## Purpose
Fournir une IHM web locale (`pixel-lab/dashboard/index.html`) pour parcourir les images sources, visualiser les itérations produites dans `outputs/<image>/` et comparer visuellement les variantes, ainsi qu'un script `pixel-lab/serve.py` pour servir ce dashboard sur localhost et ouvrir le navigateur.
## Requirements
### Requirement: Le dashboard SHALL afficher une topbar, une sidebar et une zone principale
La page `dashboard/index.html` MUST présenter au minimum trois régions : une topbar avec titre et badge, une sidebar listant les images sources, et une zone principale dédiée à la comparaison des itérations.

#### Scenario: Structure visuelle
- **GIVEN** le dashboard ouvert dans un navigateur
- **WHEN** on inspecte le DOM
- **THEN** on SHALL trouver un élément `.topbar` avec un badge et un titre, un élément `.sidebar` scrollable avec une liste `.sidebar-list`, et une zone principale `.main-layout`

### Requirement: La sidebar SHALL lister les images sources et le nombre d'itérations
La sidebar MUST afficher, pour chaque image de `pixel-lab/inputs/` présente dans `history.json`, une entrée `.img-item` avec vignette, nom tronqué et le nombre d'itérations consignées.

#### Scenario: Sélection d'une image
- **GIVEN** la sidebar peuplée avec plusieurs entrées
- **WHEN** l'utilisateur clique sur un élément `.img-item`
- **THEN** l'entrée SHALL prendre la classe `.active` et la vue principale SHALL charger les itérations de `outputs/<image_name>/`

### Requirement: Le dashboard SHALL afficher les vignettes en rendu pixel-art non lissé
Les vignettes et visualisations MUST appliquer `image-rendering: pixelated` afin de préserver l'apparence pixel-art sans lissage du navigateur.

#### Scenario: Rendu pixelisé
- **GIVEN** une vignette `.img-item img`
- **WHEN** on inspecte son style calculé
- **THEN** la propriété CSS `image-rendering` SHALL valoir `pixelated`

### Requirement: Le dashboard SHALL permettre de comparer plusieurs itérations
Pour une image sélectionnée, la zone principale MUST permettre d'afficher au moins deux itérations côte à côte pour comparer leurs résultats.

#### Scenario: Comparaison deux variantes
- **GIVEN** une image avec au moins deux itérations
- **WHEN** l'utilisateur active la comparaison
- **THEN** deux visualisations SHALL être affichées côte à côte avec leur label d'itération (`iter_XXX_<algo>_<method>`)

### Requirement: Le serveur local SHALL exposer le dashboard sur un port configurable
Le script `pixel-lab/serve.py` MUST démarrer un `http.server` local avec racine sur `pixel-lab/`, port par défaut 5500, et ouvrir automatiquement `http://localhost:<port>/dashboard/index.html` dans le navigateur par défaut.

#### Scenario: Port personnalisé
- **GIVEN** la commande `py serve.py --port 8080`
- **WHEN** le serveur démarre
- **THEN** le dashboard SHALL être accessible à `http://localhost:8080/dashboard/index.html`

#### Scenario: Option --no-browser
- **GIVEN** la commande `py serve.py --no-browser`
- **WHEN** le serveur démarre
- **THEN** aucun onglet de navigateur SHALL être ouvert automatiquement et le serveur SHALL rester en écoute sur le port configuré

### Requirement: Le dashboard SHALL se recharger avec l'état courant de history.json
Le dashboard MUST refléter l'état actuel de `pixel-lab/history.json` à chaque chargement (ou rafraîchissement) : ajout d'une image dans `inputs/` + nouveau `runs[]` = nouvelles entrées visibles dans la sidebar et la zone principale.

#### Scenario: Actualisation après une nouvelle itération
- **GIVEN** le dashboard ouvert et une image sélectionnée
- **WHEN** l'utilisateur lance une exécution `process.py` puis rafraîchit la page
- **THEN** la nouvelle itération SHALL apparaître dans la liste et être consultable dans la zone principale

### Requirement: Bouton toggle axes pixel dans le footer comparateur
Le dashboard SHALL inclure un bouton "Axes pixel" dans le footer du comparateur, à côté des contrôles de zoom existants.

#### Scenario: Bouton visible dans le footer
- **WHEN** le comparateur est affiché avec deux images sélectionnées
- **THEN** un bouton "Axes pixel" est visible dans le footer du comparateur

#### Scenario: État actif du bouton
- **WHEN** le toggle est activé
- **THEN** le bouton apparaît avec le style `.active` (fond accent violet)

### Requirement: La sidebar SHALL distinguer l'image active (preview) de la multi-sélection (batch)

La sidebar (colonne gauche du layout 2 colonnes) MUST gérer deux états d'image orthogonaux : **selected** (cases à cocher, alimente `/api/convert`) et **active** (un seul item à la fois, alimente `/api/preview`). Le clic sur la miniature ou le corps de l'item MUST mettre à jour `active` sans modifier `selected`. Un indicateur visuel distinct (contour, badge, ou couleur d'accent) MUST signaler l'image active, différent de l'état `selected`. Cet indicateur visuel actif MUST être visible quand le toggle "Live preview" est activé ; quand le toggle est désactivé, l'indicateur peut rester discret ou être masqué, au choix de l'implémentation.

La sidebar SHALL être positionnée dans la colonne gauche du nouveau layout 2 colonnes et SHALL scroller indépendamment du panneau Convertir via `overflow-y: auto` sur sa section images.

#### Scenario: Cliquer une miniature ne décoche pas les sélections batch

- **GIVEN** 3 images cochées pour un batch futur et une 4ᵉ image actuellement active
- **WHEN** l'utilisateur clique sur une 5ᵉ image (non cochée)
- **THEN** l'état `active` SHALL être déplacé sur la 5ᵉ image, les 3 premières images cochées SHALL rester cochées inchangées, et la 4ᵉ ex-active SHALL perdre sa marque visuelle active

#### Scenario: Image active indiquée visuellement en mode live

- **GIVEN** le toggle "Live preview" activé
- **WHEN** on inspecte la sidebar
- **THEN** exactement un item SHALL porter la marque visuelle "active" (ex. contour coloré ou badge), et cet item SHALL correspondre à la dernière miniature cliquée

#### Scenario: Scroll indépendant de la liste d'images

- **GIVEN** 50 images dans la sidebar et le panneau Convertir visible en dessous
- **WHEN** l'utilisateur scrolle la liste d'images
- **THEN** seule la liste SHALL défiler ; le panneau Convertir SHALL rester visible et ancré au bas de la sidebar

### Requirement: Le panneau Convertir SHALL exposer un toggle "Live preview" qui bascule le comportement des inputs de paramètres
Le panneau `.convert-panel` MUST inclure un toggle `[ Live preview ]` (checkbox, switch ou bouton à état). Quand le toggle est `OFF`, le builder fonctionne comme aujourd'hui (les changements de paramètres n'ont aucun effet tant que l'utilisateur ne clique pas sur `[▶ Lancer]`). Quand le toggle est `ON`, chaque modification d'un champ de paramètre (event `input` ou `change` sur un `<input>` ou `<select>` du builder) MUST déclencher un `POST /api/preview` debouncé à 200 ms, dont la réponse met à jour une zone d'affichage dédiée.

#### Scenario: Toggle OFF par défaut
- **GIVEN** le dashboard fraîchement chargé
- **WHEN** on inspecte l'état du toggle "Live preview"
- **THEN** il SHALL être `OFF`, les inputs de paramètres SHALL être éditables comme aujourd'hui, et aucun `POST /api/preview` SHALL être émis lors des modifications

#### Scenario: Activation du toggle déclenche un preview initial
- **GIVEN** le toggle `OFF`, un builder avec au moins une étape valide, et une image active
- **WHEN** l'utilisateur active le toggle "Live preview"
- **THEN** un `POST /api/preview` SHALL être émis immédiatement avec les valeurs courantes du builder et l'image active, et la zone d'affichage preview SHALL montrer le résultat

#### Scenario: Tweak sous toggle ON → preview debouncé
- **GIVEN** le toggle `ON` et une rafale de 5 modifications du même slider en moins de 200 ms
- **WHEN** l'utilisateur arrête de bouger le slider
- **THEN** au maximum 1 ou 2 requêtes `POST /api/preview` SHALL avoir été émises (debounce 200 ms), les requêtes obsolètes SHALL avoir été annulées côté client via `AbortController`, et la zone d'affichage preview SHALL refléter uniquement le résultat de la dernière requête aboutie

#### Scenario: Absence d'image active
- **GIVEN** le toggle `ON` mais aucune image active sélectionnée
- **WHEN** l'utilisateur modifie un paramètre
- **THEN** aucune requête SHALL être émise, et la zone d'affichage preview SHALL montrer un message invitant à cliquer sur une miniature dans la sidebar

### Requirement: Les requêtes de preview SHALL être annulées côté client dès qu'une nouvelle requête part
Le client MUST instancier un `AbortController` unique partagé entre les requêtes `/api/preview`. À chaque nouvelle requête (après debounce), le contrôleur précédent MUST être `abort()` puis remplacé par un nouveau. Les réponses des requêtes abandonnées MUST être ignorées silencieusement (pas de message d'erreur utilisateur).

#### Scenario: Abort pendant le vol
- **GIVEN** une requête `POST /api/preview` en cours (3 s de calcul côté serveur)
- **WHEN** l'utilisateur modifie un paramètre après 500 ms, déclenchant un nouveau fetch
- **THEN** la requête précédente SHALL être `abort()` côté client (le fetch se termine avec une `AbortError`), l'erreur SHALL être capturée silencieusement, et la nouvelle requête SHALL être émise

#### Scenario: Réponse tardive d'une requête abandonnée ignorée
- **GIVEN** une requête abandonnée qui aboutit côté serveur malgré l'abort (thread serveur allé au bout)
- **WHEN** la réponse arrive au client
- **THEN** elle SHALL être ignorée (AbortError capturée), la zone d'affichage preview SHALL conserver le résultat de la requête la plus récente légitime

### Requirement: Un indicateur d'état non bloquant SHALL refléter le statut du preview en cours
Le panneau Convertir MUST afficher un indicateur visuel discret (dot coloré, badge, ou texte court) reflétant l'état courant du preview : `idle` (gris), `in-flight` (jaune/orange avec animation pulse ou spinner minimaliste), `ready` (vert), `error` (rouge avec message). L'indicateur MUST NOT bloquer l'interaction avec les inputs du builder (pas de `pointer-events: none`, pas d'overlay plein écran).

#### Scenario: Pulsation pendant le calcul
- **GIVEN** une requête `POST /api/preview` en cours
- **WHEN** on inspecte l'indicateur d'état
- **THEN** il SHALL être en état `in-flight` (jaune + animation discrète), et l'utilisateur SHALL pouvoir continuer à modifier les inputs sans blocage (ce qui déclenchera une nouvelle requête après debounce)

#### Scenario: Retour à idle après réponse
- **GIVEN** une requête qui vient d'aboutir
- **WHEN** le PNG est affiché dans la zone de preview
- **THEN** l'indicateur SHALL passer à `ready` (vert) puis retomber à `idle` (gris) après 500 ms si aucune nouvelle requête n'est déclenchée

#### Scenario: Erreur serveur affichée sans blocage
- **GIVEN** le serveur qui renvoie `500 Internal Server Error` sur un preview
- **WHEN** le client reçoit la réponse
- **THEN** l'indicateur SHALL passer à `error` (rouge) avec un tooltip ou message court indiquant la nature de l'erreur, et l'utilisateur SHALL pouvoir continuer à utiliser le builder normalement (retry automatique sur prochain tweak)

### Requirement: Un toggle "Taille réelle" SHALL désactiver le downscale par défaut du preview
Le panneau Convertir MUST inclure un second toggle `[ Taille réelle ]`, accessible uniquement quand le toggle "Live preview" est actif. Quand `[ Taille réelle ]` est `OFF` (état par défaut), les requêtes `/api/preview` SHALL envoyer `downscale: 256`. Quand `[ Taille réelle ]` est `ON`, les requêtes SHALL envoyer `downscale: null`. Un pictogramme d'avertissement MUST suggérer d'activer ce toggle si le pipeline contient `scale2x` ou `pixelsnap/block` (algos sensibles à la taille).

#### Scenario: Toggle OFF envoie downscale 256
- **GIVEN** `[ Live preview ]` ON et `[ Taille réelle ]` OFF
- **WHEN** un preview est déclenché
- **THEN** le payload envoyé à `/api/preview` SHALL contenir `"downscale": 256`

#### Scenario: Toggle ON envoie downscale null
- **GIVEN** `[ Live preview ]` ON et `[ Taille réelle ]` ON
- **WHEN** un preview est déclenché
- **THEN** le payload SHALL contenir `"downscale": null`, et la zone d'affichage SHALL montrer le preview calculé à la résolution native de l'image

#### Scenario: Avertissement affiché pour pipelines taille-dépendants
- **GIVEN** un pipeline contenant au moins une étape `scale2x` ou `pixelsnap/block`, et `[ Taille réelle ]` OFF
- **WHEN** le panneau s'affiche
- **THEN** un pictogramme d'avertissement ou un tooltip SHALL être visible à côté du toggle `[ Taille réelle ]` avec un message du type "Le downscale fausse le rendu de scale2x/pixelsnap, active la taille réelle avant de valider"

### Requirement: Une zone d'affichage du preview SHALL montrer le PNG renvoyé par /api/preview
Le dashboard MUST inclure une zone dédiée (dans la zone de comparaison principale ou adjacente au panneau Convertir) pour afficher le PNG binaire renvoyé par `/api/preview` (corps `Content-Type: image/png`, métadonnées dans les headers `X-Width`/`X-Height`/`X-Elapsed-Ms`/`X-Cache-Hit-Depth`). Cette zone MUST être visible uniquement quand `[ Live preview ]` est ON. Quand `[ Live preview ]` est OFF, la zone SHALL être masquée ou retirée du DOM pour ne pas encombrer l'affichage, et l'URL blob du dernier preview SHALL être libérée via `URL.revokeObjectURL` pour éviter toute fuite mémoire.

#### Scenario: Affichage du preview
- **GIVEN** une réponse `/api/preview` `200 OK` au format PNG binaire
- **WHEN** le client reçoit la réponse
- **THEN** le client SHALL faire `const blob = await res.blob(); const url = URL.createObjectURL(blob);` et afficher `<img src=url>`, et un petit label SHALL indiquer la valeur de `res.headers.get('X-Elapsed-Ms')` (ex. "Calculé en 320 ms") ainsi que les dimensions `X-Width × X-Height`

#### Scenario: Libération du blob URL au toggle OFF
- **GIVEN** `[ Live preview ]` ON avec un preview affiché (blob URL active dans `lastPreviewUrl`)
- **WHEN** l'utilisateur bascule `[ Live preview ]` OFF
- **THEN** le client SHALL appeler `URL.revokeObjectURL(lastPreviewUrl)` et réinitialiser `lastPreviewUrl = null` avant de masquer la zone — aucune blob URL obsolète ne SHALL rester référencée

#### Scenario: Zone masquée hors mode live
- **GIVEN** `[ Live preview ]` OFF
- **WHEN** on inspecte la zone d'affichage du preview
- **THEN** elle SHALL être masquée (`display: none` ou équivalent) ou retirée du DOM, laissant la zone de comparaison existante intacte

### Requirement: Le bouton "▶ Lancer" existant SHALL rester strictement inchangé et indépendant du mode live
Le flux `[▶ Lancer]` → `POST /api/convert` → SSE → écriture de `iter_NNN_*.png` et mise à jour de `history.json` MUST rester inchangé, que le toggle `[ Live preview ]` soit ON ou OFF. Cliquer sur `[▶ Lancer]` avec le toggle ON MUST envoyer exactement le même payload et déclencher exactement les mêmes effets qu'aujourd'hui.

#### Scenario: Lancer pendant un preview actif
- **GIVEN** `[ Live preview ]` ON avec un preview en cours d'exécution
- **WHEN** l'utilisateur clique sur `[▶ Lancer]`
- **THEN** un `POST /api/convert` SHALL être envoyé normalement, le job officiel SHALL produire `iter_NNN_*.png` et mettre à jour `history.json` comme aujourd'hui, et l'événement `done` SSE SHALL déclencher le refresh existant de la sidebar et de la zone de comparaison

#### Scenario: Indépendance de l'iter produit vs preview
- **GIVEN** un preview downscalé 256 px affiché à l'écran
- **WHEN** l'utilisateur clique sur `[▶ Lancer]`
- **THEN** l'iter produit par `/api/convert` SHALL être à la résolution originale de l'image source (pas 256 px), confirmant que le preview et le résultat officiel sont deux chemins totalement indépendants

### Requirement: Le panneau Convertir SHALL exposer un bouton `🎯 Détecter fond` et un toggle `Préserver le fond`

Le panneau `.convert-panel` MUST inclure :

- Un bouton `🎯 Détecter fond` qui, au clic, déclenche `GET /api/bgmask?image=<activeImage>` avec la valeur courante de `tolerance` (défaut 8), et affiche une overlay semi-transparente (`opacity: 0.5`) du masque retourné, par-dessus l'image source dans la zone de comparaison.
- Un toggle checkbox `[ ] Préserver le fond` qui, quand activé, ajoute `preserve_bg: true` aux params de chaque étape compatible (`denoise/*`, `sharpen/*`) lors de l'appel à `/api/preview` et `/api/convert`.
- Un petit champ numérique `tolerance` (0-50, défaut 8) exposé à côté du bouton pour ajuster la sensibilité de la détection.

Le bouton et le toggle MUST être désactivés (grisés) si aucune image n'est active (`activeImage === null`).

#### Scenario: Clic sur Détecter fond avec image active

- **GIVEN** une image active sélectionnée dans la sidebar
- **WHEN** l'utilisateur clique sur `🎯 Détecter fond`
- **THEN** le dashboard SHALL émettre `GET /api/bgmask?image=<basename>&tolerance=<val>`, afficher le PNG retourné en overlay sur l'image source avec `opacity: 0.5`, et afficher un label "Fond détecté: #RRGGBB" (ou "Fond non détecté") sous le bouton

#### Scenario: Toggle Préserver le fond modifie le payload preview

- **GIVEN** le toggle `Préserver le fond` activé et un pipeline `[{denoise, median}, {sharpen, unsharp_mask}]`
- **WHEN** le dashboard émet un `POST /api/preview`
- **THEN** le payload SHALL contenir `preserve_bg: true` dans les `params` de chaque étape

#### Scenario: Toggle désactivé n'ajoute pas preserve_bg

- **GIVEN** le toggle `Préserver le fond` désactivé (défaut)
- **WHEN** le dashboard émet un `POST /api/preview` ou `/api/convert`
- **THEN** le payload SHALL NE PAS contenir `preserve_bg` dans les `params` (ou contenir `preserve_bg: false`)

#### Scenario: Bouton désactivé sans image active

- **GIVEN** aucune image active sélectionnée
- **WHEN** on inspecte l'UI
- **THEN** le bouton `🎯 Détecter fond` SHALL être `disabled` et le toggle `Préserver le fond` SHALL être `disabled` avec un tooltip « Sélectionne une image d'abord »

### Requirement: L'overlay du masque SHALL être toggleable et non intrusive

L'overlay affichée après clic sur `🎯 Détecter fond` MUST :

- Être superposée à l'image source (côté gauche du comparateur) avec `opacity: 0.5`.
- Se retirer quand on re-clique sur `🎯 Détecter fond` (toggle on/off) ou quand l'image active change.
- Ne pas bloquer les interactions du comparateur (pan, zoom, drag du divider restent fonctionnels).
- Ne pas s'afficher dans le résultat officiel `/api/convert` (uniquement visualisation).

#### Scenario: Re-clic retire l'overlay

- **GIVEN** une overlay de masque affichée
- **WHEN** l'utilisateur clique à nouveau sur `🎯 Détecter fond`
- **THEN** l'overlay SHALL disparaître et l'image source SHALL redevenir seule

#### Scenario: Changement d'image active retire l'overlay

- **GIVEN** une overlay affichée pour `sprite1.png`
- **WHEN** l'utilisateur clique sur `sprite2.png` dans la sidebar
- **THEN** l'overlay SHALL être retirée automatiquement (l'utilisateur doit re-cliquer sur Détecter fond pour la nouvelle image)

### Requirement: Le dashboard SHALL utiliser un layout 2 colonnes plein écran avec comparateur plein hauteur

La page principale `pixel-lab/dashboard/index.html` MUST s'afficher en CSS Grid avec 3 colonnes :

- Colonne gauche : largeur variable `--left-w` (défaut 280 px), 0 px si rétractée.
- Colonne centrale : `1fr` (occupe tout l'espace restant).
- Colonne droite (panneau Historique) : largeur variable `--right-w` (défaut 0 px fermée, 320 px ouverte).

La hauteur totale MUST être exactement `100vh` (pas de scroll vertical global). Chaque colonne MUST scroller individuellement si son contenu dépasse.

La colonne centrale MUST contenir uniquement le comparateur slider qui occupe 100% de sa largeur et 100% de sa hauteur.

#### Scenario: Layout 2 colonnes au chargement

- **GIVEN** le dashboard fraîchement chargé sur un écran 1920×1080
- **WHEN** on inspecte la page
- **THEN** la hauteur totale du `body` SHALL être exactement 1080 px, la sidebar gauche SHALL mesurer 280 px, la zone centrale SHALL occuper les ~1640 px restants en largeur et 1080 px en hauteur, et aucun scroll vertical global ne SHALL être présent

#### Scenario: Le comparateur remplit la colonne centrale

- **GIVEN** une image active sélectionnée
- **WHEN** on inspecte la zone comparateur
- **THEN** elle SHALL occuper 100% de la largeur et 100% de la hauteur de la colonne centrale (moins une toolbar overlay optionnelle de ~40 px en haut)

### Requirement: Le dashboard SHALL permettre la rétractation de la sidebar gauche et du panneau historique

Deux chevrons-toggle MUST être présents :

- Bouton `<` en bord droit de la sidebar gauche : toggle ouvre/ferme la sidebar (0 px ↔ 280 px).
- Bouton `>` en bord gauche du panneau droit ou un bouton dédié dans la sidebar : toggle ouvre/ferme le panneau Historique (0 px ↔ 320 px).

La transition de largeur MUST être animée (`transition: grid-template-columns 0.22s ease`).

L'état rétracté/ouvert MUST être persisté dans `localStorage` sous les clés `dashLeftOpen` et `dashRightOpen`, et restauré au prochain chargement.

#### Scenario: Rétractation de la sidebar

- **GIVEN** la sidebar gauche ouverte à 280 px
- **WHEN** l'utilisateur clique sur le chevron `<`
- **THEN** la sidebar SHALL se réduire à 0 px en 220 ms, le comparateur SHALL s'étendre pour occuper l'espace libéré, et `localStorage.dashLeftOpen` SHALL valoir `"false"`

#### Scenario: Persistance entre sessions

- **GIVEN** la sidebar gauche fermée et `localStorage.dashLeftOpen === "false"`
- **WHEN** l'utilisateur recharge la page
- **THEN** la sidebar SHALL rester fermée au chargement initial (pas de flash d'ouverture)

#### Scenario: Raccourci clavier pour le panneau Historique

- **GIVEN** le panneau Historique fermé
- **WHEN** l'utilisateur appuie sur la touche `H`
- **THEN** le panneau SHALL s'ouvrir avec la grille d'iters, et `localStorage.dashRightOpen` SHALL valoir `"true"`

### Requirement: Le panneau Convertir SHALL être intégré dans la sidebar gauche (pas dans une zone séparée)

Le panneau Convertir actuel (builder pipeline, toggles live/fullres/preserve_bg, bouton Lancer, indicateur status, live row) MUST être positionné dans la sidebar gauche, sous la liste d'images, avec :

- `flex: 0 0 auto` (ne prend que sa taille naturelle).
- `max-height: 60vh` avec `overflow-y: auto` (scroll interne si contenu trop long).
- Layout des `.step-row` en `flex-direction: column` ou grille compacte pour s'adapter à la largeur de 280 px.

La liste d'images au-dessus MUST avoir `flex: 1 1 auto` et `overflow-y: auto` (scroll interne).

#### Scenario: Builder pipeline compact dans la sidebar

- **GIVEN** la sidebar gauche de 280 px avec le panneau Convertir visible
- **WHEN** on ajoute une étape au pipeline
- **THEN** l'étape SHALL s'afficher sans déborder horizontalement, les selects algo/method SHALL s'empiler verticalement si nécessaire, et les boutons d'action (↑ ↓ ×) SHALL rester visibles

#### Scenario: Liste d'images scrollable sans affecter le panneau Convertir

- **GIVEN** 50 images dans la sidebar
- **WHEN** l'utilisateur scrolle dans la liste d'images
- **THEN** seule la liste SHALL défiler ; le panneau Convertir SHALL rester visible et fixe en bas de la sidebar

### Requirement: La grille d'iters SHALL être déplacée dans un panneau Historique rétractable à droite

La zone actuelle affichant la grille d'iters + la barre de tri/filtre MUST être retirée de la zone principale et placée dans un panneau rétractable à droite (colonne 3 du grid).

Le panneau Historique MUST :

- Être fermé par défaut au premier chargement (avant `localStorage` persisté).
- S'ouvrir via un bouton dédié dans la sidebar gauche (`📜 Historique`) ou la touche `H`.
- Contenir : la barre tri/filtre en haut + la grille d'iters en dessous, scrollable.
- Un clic sur un iter dans le panneau MUST continuer à fonctionner (sélection comme compareRight, refresh du comparateur).

#### Scenario: Grille d'iters accessible via le panneau Historique

- **GIVEN** le panneau Historique fermé et une image active avec 20 iters
- **WHEN** l'utilisateur clique sur `📜 Historique` dans la sidebar
- **THEN** le panneau droit SHALL s'ouvrir à 320 px, afficher les 20 iters sous forme de grille (comme actuellement), et la barre tri/filtre SHALL être présente en haut

#### Scenario: Sélection d'un iter depuis le panneau

- **GIVEN** le panneau Historique ouvert
- **WHEN** l'utilisateur clique sur la vignette d'un iter
- **THEN** l'iter SHALL devenir le `compareRight` du comparateur central, qui SHALL afficher le diff source ↔ iter comme aujourd'hui

### Requirement: La poignée du slider SHALL être centrée dans le viewport visible, pas dans le body de l'image

La poignée (`#cmp-handle`) MUST calculer sa position verticale en fonction de la portion visible du comparateur dans le viewport :

- Au chargement, sur scroll (`window.scroll`), sur resize, et après chaque `applyDivider`, le top de la poignée MUST être recalculé via `(visibleTop + visibleBottom) / 2 - handleRadius` où `visibleTop = max(0, -rect.top)` et `visibleBottom = min(rect.height, viewportHeight - rect.top)`.

Dans le nouveau layout (comparateur = 100vh), cette formule donne toujours `top ≈ 50vh`, donc la poignée est toujours au centre de l'écran.

#### Scenario: Poignée au centre du viewport

- **GIVEN** un comparateur de 100vh avec une image grande (même plus grande que le viewport avec zoom)
- **WHEN** on inspecte la poignée
- **THEN** son centre vertical SHALL être à ~50vh de l'écran (au milieu visible)

#### Scenario: Poignée reste visible lors du scroll

- **GIVEN** un layout où une partie du comparateur dépasse verticalement (cas rare en nouveau layout mais possible)
- **WHEN** l'utilisateur scrolle
- **THEN** la poignée SHALL se repositionner dynamiquement pour rester au centre de la portion visible du comparateur

### Requirement: Le header global SHALL être retiré et son contenu intégré dans la sidebar gauche

Le header actuel (badge « ⚡ Pixel Lab », info serveur en ligne/hors ligne) MUST être retiré du haut de la page. Son contenu essentiel (badge + statut serveur compact) MUST être positionné en haut de la sidebar gauche (~50 px max, `flex: 0 0 auto`).

#### Scenario: Pas de header global

- **GIVEN** le dashboard chargé
- **WHEN** on inspecte la page
- **THEN** aucun élément `<header>` ni `.header` ne SHALL occuper la largeur totale en haut ; le badge version SHALL apparaître dans le haut de la sidebar gauche

### Requirement: Le comparateur SHALL afficher une toolbar minimale overlay en haut

En haut de la zone comparateur (colonne centrale), une barre semi-transparente MUST afficher :

- Le nom du sprite actif (gauche).
- Les labels Gauche/Droite si un iter ou preview est chargé.
- Les boutons zoom (−, zoom level, +, reset, toggle axes pixel) à droite.
- Le label de timing preview (« Calculé en Xms · cache=N ») si en mode live.

Styling : `position: absolute; top: 0; left: 0; right: 0; height: 40px; background: rgba(10,10,20,0.5); backdrop-filter: blur(8px); color: #fff`. Cette toolbar MUST NE PAS bloquer les interactions sur l'image en dessous (sauf sur les contrôles eux-mêmes).

#### Scenario: Toolbar overlay visible sans couper l'image

- **GIVEN** le comparateur plein écran
- **WHEN** on survole la toolbar
- **THEN** les boutons SHALL être cliquables, et l'image SHALL rester visible en transparence à travers le fond semi-transparent

#### Scenario: Zoom control depuis la toolbar

- **GIVEN** la toolbar affichée
- **WHEN** l'utilisateur clique sur le bouton `+`
- **THEN** le zoom SHALL augmenter (comme avec l'ancien footer), et le label de niveau de zoom SHALL se mettre à jour

### Requirement: La sidebar SHALL exposer une multi-sélection des images d'entrée
La sidebar MUST permettre à l'utilisateur de sélectionner un sous-ensemble d'images via une case à cocher par item, en complément du clic existant qui active une image pour la comparaison. La sélection multiple alimente le panneau "Convertir".

#### Scenario: Sélection multiple
- **GIVEN** la sidebar peuplée de 6 entrées
- **WHEN** l'utilisateur coche les cases de 3 entrées
- **THEN** le panneau "Convertir" SHALL afficher ces 3 noms comme cibles du prochain job, et le compteur `Images : N sélectionnée(s)` SHALL être mis à jour en temps réel

#### Scenario: Sélection vs activation
- **GIVEN** une image cochée mais pas activée pour la comparaison
- **WHEN** l'utilisateur clique sur le corps de l'item (hors checkbox)
- **THEN** l'item SHALL prendre la classe `.active` pour la zone de comparaison sans modifier son état coché

### Requirement: Un panneau "Convertir" SHALL exposer un builder d'étapes éditable
Le dashboard MUST inclure une région `.convert-panel` contenant un builder ordonné d'étapes. Chaque étape comporte un sélecteur `algo`, un sélecteur `method` filtré par l'algo, des champs d'inputs dynamiques pour les paramètres, et des contrôles `[×]` (suppression), `[↑]` `[↓]` (réordonnancement). À l'état initial, exactement une étape vide est présente — équivalent fonctionnel d'un mode mono-algo.

#### Scenario: État initial mono-étape
- **GIVEN** le dashboard fraîchement chargé
- **WHEN** on inspecte le builder
- **THEN** il SHALL contenir exactement une ligne d'étape avec algo et méthode non sélectionnés, et un bouton `+ Ajouter une étape` en dessous

#### Scenario: Ajout d'étape
- **GIVEN** un builder à 1 étape
- **WHEN** l'utilisateur clique `+ Ajouter une étape`
- **THEN** une nouvelle ligne SHALL apparaître en fin de liste, le focus SHALL être placé sur le sélecteur `algo`, et le bouton `[×]` SHALL apparaître sur les deux étapes (toujours désactivé sur la dernière étape restante quand il n'en reste qu'une)

#### Scenario: Suppression d'étape
- **GIVEN** un builder à 3 étapes
- **WHEN** l'utilisateur clique `[×]` sur l'étape 2
- **THEN** elle SHALL être retirée et les étapes restantes SHALL conserver leurs valeurs et être renumérotées 1, 2

#### Scenario: Réordonnancement
- **GIVEN** un builder à 3 étapes ordonnées (denoise, pixelsnap, sharpen)
- **WHEN** l'utilisateur clique `[↑]` sur l'étape `sharpen`
- **THEN** l'ordre SHALL devenir (denoise, sharpen, pixelsnap) avec préservation des paramètres saisis

### Requirement: Le builder SHALL générer dynamiquement les champs de paramètres à partir de /api/algos
Quand l'utilisateur change l'algo ou la méthode d'une étape, les champs d'inputs en dessous MUST être reconstruits selon `PARAMS[<method>]` reçu via `GET /api/algos`. Chaque param numérique MUST être rendu en `<input type="number">` avec attributs `min`, `max`, `step` correspondant aux bornes de `PARAMS`. Chaque champ MUST être pré-rempli avec sa valeur par défaut.

#### Scenario: Génération des inputs
- **GIVEN** une étape avec algo `pixelsnap`
- **WHEN** l'utilisateur sélectionne la méthode `median` qui déclare `PARAMS:[{name:"block",type:"int",default:4,min:2,max:32}]`
- **THEN** un input `<input type="number" min="2" max="32" value="4">` étiqueté `block` SHALL apparaître sous la ligne d'étape

#### Scenario: Reset des params au changement de méthode
- **GIVEN** une étape `sharpen / unsharp_mask` avec `radius:5.0` saisi par l'utilisateur
- **WHEN** l'utilisateur change la méthode pour `laplacian`
- **THEN** les inputs précédents (`radius`, `percent`) SHALL disparaître et les nouveaux inputs de `laplacian` SHALL apparaître avec leurs valeurs par défaut

### Requirement: Un menu de presets SHALL pré-remplir le builder avec des pipelines prédéfinis
Le panneau "Convertir" MUST fournir un menu `Charger un preset` proposant au minimum trois pipelines : `Nettoyage GenAI` (denoise/median → pixelsnap/median → sharpen/unsharp_mask), `Upscale propre x2` (pixelsnap/median → scale2x/eagle2x), `Correction JPEG` (denoise/bilateral → sharpen/unsharp_mask). Sélectionner un preset remplit le builder avec ses étapes et leurs paramètres par défaut, en remplaçant tout contenu existant.

#### Scenario: Charger Nettoyage GenAI
- **GIVEN** un builder vide
- **WHEN** l'utilisateur sélectionne `Nettoyage GenAI` dans le menu
- **THEN** le builder SHALL être rempli avec exactement 3 étapes ordonnées (denoise/median, pixelsnap/median block=4, sharpen/unsharp_mask radius=1.2 percent=200) et toutes les valeurs SHALL être éditables ensuite

#### Scenario: Preset remplace le contenu existant
- **GIVEN** un builder à 2 étapes saisies par l'utilisateur
- **WHEN** l'utilisateur sélectionne un preset
- **THEN** le builder SHALL être réinitialisé (les étapes manuelles sont perdues sauf confirmation), puis rempli avec le preset

### Requirement: Le bouton "Lancer" SHALL appeler POST /api/convert et ouvrir le flux SSE
Le bouton `[▶ Lancer]` du panneau "Convertir" MUST envoyer un `POST /api/convert` avec le payload `{images, pipeline}`, recevoir un `job_id`, puis ouvrir une connexion `EventSource` sur `GET /api/jobs/<job_id>/stream` pour afficher la progression en temps réel.

#### Scenario: Lancement nominal
- **GIVEN** 2 images cochées et un pipeline à 3 étapes valides
- **WHEN** l'utilisateur clique `[▶ Lancer]`
- **THEN** un `POST /api/convert` SHALL être envoyé, le job_id reçu SHALL être affiché dans le panneau, et une barre de progression `N/M` SHALL se mettre à jour à chaque événement SSE `step_done` ou `image_done`

#### Scenario: Affichage des erreurs
- **GIVEN** un job en cours
- **WHEN** un événement `{type:"step_error", image:"...", stderr:"..."}` est reçu
- **THEN** la ligne correspondante dans le panneau SHALL passer à un style d'erreur (rouge), afficher le `stderr` tronqué, et le job SHALL continuer pour les autres images

### Requirement: Après job terminé, la sidebar et la zone de comparaison SHALL être rafraîchies automatiquement
À la réception de l'événement SSE `{type:"done", ...}`, le dashboard MUST recharger `history.json` (ou re-fetcher `/api/inputs`) et reconstruire la sidebar ainsi que la zone de comparaison de l'image active si elle fait partie du job, sans rafraîchissement complet de la page.

#### Scenario: Auto-refresh
- **GIVEN** un job qui vient de produire 3 nouvelles itérations sur l'image active
- **WHEN** l'événement `done` est reçu
- **THEN** la sidebar SHALL afficher le compteur d'itérations mis à jour pour les images concernées, et la zone de comparaison SHALL inclure les nouvelles itérations sans rechargement de la page

### Requirement: Le dashboard SHALL fonctionner en mode dégradé sans backend Flask
Si l'API n'est pas joignable (Flask non lancé, port différent, erreur réseau), le dashboard MUST rester pleinement fonctionnel en lecture seule (sidebar + comparaison) et désactiver visiblement le panneau "Convertir" avec un message d'avertissement clair indiquant que le backend est hors-ligne et comment le démarrer.

#### Scenario: API hors-ligne au chargement
- **GIVEN** `serve.py` lancé mais aucun serveur Flask sur le port attendu
- **WHEN** le dashboard tente `GET /api/algos` au chargement et reçoit une erreur réseau
- **THEN** le panneau "Convertir" SHALL afficher un message non bloquant `API hors-ligne — démarre 'python pixel-lab/server/app.py' pour activer les conversions`, et le bouton `[▶ Lancer]` SHALL être désactivé visuellement (greyed out)

#### Scenario: Lecture seule fonctionne
- **GIVEN** le dashboard en mode dégradé
- **WHEN** l'utilisateur clique sur une image dans la sidebar
- **THEN** la comparaison des itérations SHALL fonctionner normalement (lecture statique de `history.json` et `outputs/`)

### Requirement: Le panneau Convertir SHALL exposer un toggle `Inverser masque` qui inverse visuellement l'overlay de détection de fond

Le panneau `.convert-panel` MUST inclure, à côté du bouton `🎯 Détecter fond` et du champ `tolerance`, un toggle `[ ] Inverser masque` (checkbox ou switch). Cette bascule est **purement visuelle côté client** : elle ne modifie AUCUN payload envoyé à `/api/convert` ou `/api/preview`, et en particulier n'altère pas le paramètre `preserve_bg` des étapes du pipeline.

Quand le toggle est `ON`, l'overlay `.bg-mask-overlay` (image retournée par `GET /api/bgmask`) MUST afficher son complément — les pixels du premier-plan (ce qui serait préservé) apparaissent au lieu du fond. L'implémentation utilise `filter: invert(1)` (ou équivalent) appliqué à l'élément `img.bg-mask-overlay`, sans nouvel appel réseau.

Quand le toggle est `OFF`, l'overlay MUST s'afficher en mode normal (fond détecté).

#### Scenario: Toggle OFF par défaut sans état persisté

- **GIVEN** un dashboard fraîchement chargé sans entrée `dashBgInvert` dans `localStorage`
- **WHEN** l'utilisateur clique sur `🎯 Détecter fond` pour afficher l'overlay
- **THEN** le toggle `Inverser masque` SHALL être `OFF` et l'overlay SHALL s'afficher en mode normal (fond visible en opaque)

#### Scenario: Activation du toggle inverse l'overlay sans appel réseau

- **GIVEN** une overlay `.bg-mask-overlay` affichée et le toggle `OFF`
- **WHEN** l'utilisateur active le toggle `Inverser masque`
- **THEN** aucune requête `GET /api/bgmask` SHALL être émise, et `img.bg-mask-overlay` SHALL recevoir le style `filter: invert(1)` (ou équivalent), de sorte que les zones noires et blanches soient inversées instantanément

#### Scenario: L'inversion ne modifie pas les payloads de conversion

- **GIVEN** le toggle `Inverser masque` activé et un pipeline `[{denoise, median}]`
- **WHEN** l'utilisateur clique sur `[▶ Lancer]` ou déclenche un live preview
- **THEN** le payload envoyé à `/api/convert` / `/api/preview` SHALL être strictement identique à celui qui aurait été envoyé avec le toggle désactivé (aucun champ `invert`, `invert_mask` ou équivalent ajouté ; `preserve_bg` inchangé)

### Requirement: L'état du toggle `Inverser masque` SHALL être persisté dans localStorage

L'état du toggle MUST être enregistré dans `localStorage` sous la clé `dashBgInvert` avec les valeurs `"true"` ou `"false"`. Au chargement du dashboard, la valeur persistée SHALL être restaurée. Au prochain affichage de l'overlay, l'état d'inversion SHALL refléter cette valeur restaurée.

#### Scenario: Persistance de l'état après reload

- **GIVEN** le toggle `Inverser masque` activé et l'overlay affichée
- **WHEN** l'utilisateur recharge la page puis re-clique sur `🎯 Détecter fond`
- **THEN** `localStorage.dashBgInvert` SHALL valoir `"true"` après reload, le toggle SHALL apparaître en `ON` dès que l'overlay est affichée, et l'overlay SHALL être inversée immédiatement

#### Scenario: La valeur persistée survit même sans overlay

- **GIVEN** le toggle `Inverser masque` activé, puis l'utilisateur change d'image active (ce qui retire l'overlay)
- **WHEN** l'utilisateur clique sur `🎯 Détecter fond` pour la nouvelle image
- **THEN** la nouvelle overlay SHALL s'afficher directement en mode inversé, car la valeur `dashBgInvert === "true"` a été préservée

### Requirement: Le toggle `Inverser masque` SHALL être désactivé (grisé) sans image active ou sans overlay affichée

Le toggle MUST être `disabled` dans deux cas :
- aucune image n'est sélectionnée comme active (`activeImage === null`) ;
- l'overlay `.bg-mask-overlay` n'est pas présente dans le DOM (détection jamais lancée, ou déjà retirée via re-clic).

Dans l'état `disabled`, le toggle SHALL afficher un style visuel grisé et un tooltip explicatif (ex. « Affiche d'abord le masque via Détecter fond »).

#### Scenario: Toggle désactivé sans image active

- **GIVEN** aucune image active dans la sidebar
- **WHEN** on inspecte le panneau Convertir
- **THEN** le toggle `Inverser masque` SHALL être `disabled` avec un tooltip « Sélectionne une image d'abord » (ou équivalent)

#### Scenario: Toggle désactivé tant qu'aucune détection n'a été lancée

- **GIVEN** une image active et aucune overlay affichée
- **WHEN** on inspecte le panneau Convertir
- **THEN** le toggle `Inverser masque` SHALL être `disabled` avec un tooltip « Affiche d'abord le masque via Détecter fond » (ou équivalent)

#### Scenario: Toggle activé dès que l'overlay est affichée

- **GIVEN** le toggle actuellement `disabled` faute d'overlay
- **WHEN** l'utilisateur clique sur `🎯 Détecter fond` et l'overlay apparaît
- **THEN** le toggle SHALL passer à l'état `enabled` et être interactif immédiatement

### Requirement: La toolbar du comparateur SHALL exposer un bouton `🔳 Grille` et son raccourci clavier `G`

La `.cmp-toolbar` overlay existante MUST inclure un bouton `🔳 Grille` (classe `.zbtn`) à côté du bouton `⊹ Axes pixel`. Le bouton toggle l'affichage de l'overlay `#grid-overlay` (capability `pixel-grid-overlay`).

Quand activé, le bouton MUST prendre la classe `.active`. La touche `G` sur le clavier (hors focus dans un champ `input/textarea/select`) MUST basculer le même toggle.

Quand le toggle est actif, un petit champ `<input type="number" id="grid-step">` (pas de la grille, 1..64) MUST apparaître dans la toolbar à droite immédiate du bouton. Le champ SHALL disparaître quand le toggle repasse à OFF.

#### Scenario: Clic sur le bouton Grille

- **GIVEN** la toolbar du comparateur visible
- **WHEN** l'utilisateur clique sur `🔳 Grille`
- **THEN** l'overlay `#grid-overlay` SHALL apparaître, le bouton SHALL prendre la classe `.active`, et le champ `#grid-step` SHALL être visible dans la toolbar avec la valeur courante du pas

#### Scenario: Raccourci clavier G

- **GIVEN** le dashboard avec le focus sur le comparateur (pas dans un input)
- **WHEN** l'utilisateur appuie sur la touche `G`
- **THEN** le toggle grille SHALL basculer (ON ↔ OFF) comme si le bouton avait été cliqué

#### Scenario: Raccourci G ignoré dans un champ

- **GIVEN** le focus sur `#bg-tolerance` (ou tout autre `input`)
- **WHEN** l'utilisateur tape `g` pour saisir du texte
- **THEN** le toggle grille ne SHALL PAS basculer, et la saisie SHALL fonctionner normalement

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

