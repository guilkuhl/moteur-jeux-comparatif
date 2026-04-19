## ADDED Requirements

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
