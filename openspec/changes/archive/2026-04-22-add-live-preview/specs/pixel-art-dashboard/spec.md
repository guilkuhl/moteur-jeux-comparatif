## ADDED Requirements

### Requirement: La sidebar SHALL distinguer l'image active (preview) de la multi-sélection (batch)
La sidebar MUST gérer deux états d'image orthogonaux : **selected** (cases à cocher, alimente `/api/convert`) et **active** (un seul item à la fois, alimente `/api/preview`). Le clic sur la miniature ou le corps de l'item MUST mettre à jour `active` sans modifier `selected`. Un indicateur visuel distinct (contour, badge, ou couleur d'accent) MUST signaler l'image active, différent de l'état `selected`. Cet indicateur visuel actif MUST être visible quand le toggle "Live preview" est activé ; quand le toggle est désactivé, l'indicateur peut rester discret ou être masqué, au choix de l'implémentation.

#### Scenario: Cliquer une miniature ne décoche pas les sélections batch
- **GIVEN** 3 images cochées pour un batch futur et une 4ᵉ image actuellement active
- **WHEN** l'utilisateur clique sur une 5ᵉ image (non cochée)
- **THEN** l'état `active` SHALL être déplacé sur la 5ᵉ image, les 3 premières images cochées SHALL rester cochées inchangées, et la 4ᵉ ex-active SHALL perdre sa marque visuelle active

#### Scenario: Image active indiquée visuellement en mode live
- **GIVEN** le toggle "Live preview" activé
- **WHEN** on inspecte la sidebar
- **THEN** exactement un item SHALL porter la marque visuelle "active" (ex. contour coloré ou badge), et cet item SHALL correspondre à la dernière miniature cliquée

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
Le dashboard MUST inclure une zone dédiée (dans la zone de comparaison principale ou adjacente au panneau Convertir) pour afficher le PNG base64 renvoyé par `/api/preview`. Cette zone MUST être visible uniquement quand `[ Live preview ]` est ON. Quand `[ Live preview ]` est OFF, la zone SHALL être masquée ou retirée du DOM pour ne pas encombrer l'affichage.

#### Scenario: Affichage du preview
- **GIVEN** une réponse `/api/preview` réussie avec `png_base64: "<data>"` et dimensions
- **WHEN** le client reçoit la réponse
- **THEN** la zone de preview SHALL afficher un `<img src="data:image/png;base64,<data>">` avec les dimensions renvoyées, et un petit label SHALL indiquer `elapsed_ms` (ex. "Calculé en 320 ms")

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
