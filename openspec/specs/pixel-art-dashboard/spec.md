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
