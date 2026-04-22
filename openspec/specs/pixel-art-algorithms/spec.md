# pixel-art-algorithms Specification

## Purpose
Fournir la bibliothèque d'algorithmes d'image utilisés par le Pixel Lab pour traiter les sprites pixel-art : netteté, upscale sans flou, débruitage et pixel-snap. Chaque algorithme expose plusieurs méthodes sélectionnables. Source de vérité : `pixel-lab/scripts/algorithms/`.
## Requirements
### Requirement: Quatre familles d'algorithmes SHALL être exposées
La bibliothèque MUST exposer quatre modules : `sharpen`, `scale2x`, `denoise`, `pixelsnap`, chacun avec un dictionnaire `METHODS` mappant un nom de méthode vers sa fonction d'implémentation.

#### Scenario: Modules disponibles
- **GIVEN** le répertoire `pixel-lab/scripts/algorithms/`
- **WHEN** on importe le paquet
- **THEN** les modules `sharpen`, `scale2x`, `denoise` et `pixelsnap` SHALL être importables et chacun SHALL exposer un attribut `METHODS` de type dict

### Requirement: Le module `sharpen` SHALL proposer au moins unsharp_mask, laplacian et kernel
Le module `sharpen` MUST exposer trois méthodes de netteté : `unsharp_mask`, `laplacian`, `kernel` (ou `custom_kernel`).

#### Scenario: unsharp_mask avec paramètres
- **GIVEN** une image PIL d'entrée
- **WHEN** on appelle `sharpen.METHODS["unsharp_mask"](img, radius=1.2, percent=200)`
- **THEN** la fonction SHALL retourner une image PIL de même taille avec un gain de netteté proportionnel aux paramètres

### Requirement: Le module `scale2x` SHALL proposer nearest, scale2x et eagle2x
Le module `scale2x` MUST exposer au minimum trois méthodes d'upscale sans interpolation floue : `nearest` (plus proche voisin), `scale2x` (AdvMAME2x), `eagle2x`.

#### Scenario: Upscale x2 par scale2x
- **GIVEN** une image 16 × 16
- **WHEN** on appelle `scale2x.METHODS["scale2x"](img)`
- **THEN** la fonction SHALL retourner une image 32 × 32 sans interpolation floue sur les bords

### Requirement: Le module `denoise` SHALL proposer median, bilateral et nlm
Le module `denoise` MUST exposer trois méthodes de débruitage : `median` (filtre médian), `bilateral` (filtre bilatéral préservant les bords), `nlm` (non-local means).

#### Scenario: Bilateral avec sigma_color
- **GIVEN** une image bruitée
- **WHEN** on appelle `denoise.METHODS["bilateral"](img, sigma_color=50)`
- **THEN** la fonction SHALL retourner une image débruitée où les bords nets SHALL être conservés

### Requirement: Le module `pixelsnap` SHALL proposer median, mode et mean
Le module `pixelsnap` MUST exposer trois méthodes de nettoyage post-upscale par bloc : `median`, `mode`, `mean`. Chaque méthode regroupe les pixels flous par blocs N × N et recalcule une couleur unie.

#### Scenario: Snap par bloc 4×4
- **GIVEN** une image upscalée au bicubique avec bord flou
- **WHEN** on appelle `pixelsnap.METHODS["median"](img, block=4)`
- **THEN** chaque bloc 4 × 4 SHALL être ramené à une couleur unique correspondant à la médiane du bloc

### Requirement: Une méthode inconnue SHALL être refusée par le dispatcher
Toute fonction haut niveau (`apply_algo`, `run_pipeline`) MUST lever un `ValueError` si l'algo ou la méthode demandée n'existe pas dans les dicts `METHODS`.

#### Scenario: Méthode introuvable
- **GIVEN** un appel à `apply_algo(img, "sharpen", {"method": "unknown_filter"})`
- **WHEN** la validation des arguments s'exécute
- **THEN** un `ValueError` SHALL être levé avec le message listant les méthodes disponibles pour `sharpen`

### Requirement: Le module `bgdetect` SHALL fournir une détection automatique du fond des sprites pixel-art

Le module `pixel-lab/scripts/algorithms/bgdetect.py` MUST exposer :

- `detect_bg_color(img: PIL.Image, tolerance: int = 8) -> tuple[int,int,int] | None` qui lit les 4 pixels de coin en RGB et retourne cette couleur si ≥3 coins sont égaux (distance L∞ ≤ `tolerance`). Si aucun groupe de ≥3 coins n'est cohérent, retourne `None`.
- `compute_bg_mask(img: PIL.Image, bg_color: tuple | None = None, tolerance: int = 8, feather: int = 0) -> np.ndarray` qui :
  - Si `img.mode == "RGBA"` et contient au moins un pixel `alpha == 0`, retourne directement `alpha > 0` (masque booléen H×W, True = foreground).
  - Sinon, appelle `detect_bg_color(img, tolerance)` si `bg_color` est `None`.
  - Si aucune couleur de fond n'est trouvée, retourne un masque `True` partout (pas de fond détecté = tout est foreground).
  - Sinon, lance un flood-fill connectivity-4 depuis chaque pixel du bord de l'image ayant la couleur `bg_color` (dans la tolerance), marque tous les pixels atteints comme fond, puis retourne le complément (True = foreground).
  - Si `feather > 0`, dilate le masque foreground de `feather` pixels et applique un flou gaussien de rayon `feather/2` pour adoucir les bords (masque reste booléen ≥ 0.5 en sortie).
- Un dict `METHODS = {"auto": <wrapper>}` et `PARAMS = {"auto": [{"name": "tolerance", "type": "int", "default": 8, "min": 0, "max": 50}, {"name": "feather", "type": "int", "default": 0, "min": 0, "max": 5}]}` pour l'exposition dans l'allow-list existante.

#### Scenario: Détection d'une couleur de fond unie

- **GIVEN** une image 256×256 avec fond gris uniforme `#404040` et un sprite au centre
- **WHEN** on appelle `detect_bg_color(img)` avec tolerance par défaut
- **THEN** le retour SHALL être `(0x40, 0x40, 0x40)` ou équivalent à tolerance près

#### Scenario: Fond non détectable

- **GIVEN** une image dont les 4 coins sont de 4 couleurs différentes
- **WHEN** on appelle `detect_bg_color(img)`
- **THEN** le retour SHALL être `None`

#### Scenario: RGBA avec alpha=0 pré-existant

- **GIVEN** une image RGBA dont le fond est déjà transparent (`alpha == 0` pour tous les pixels hors sprite)
- **WHEN** on appelle `compute_bg_mask(img)`
- **THEN** le masque SHALL être exactement `alpha > 0` sans appeler `detect_bg_color` ni flood-fill

#### Scenario: Masque connecté par flood-fill

- **GIVEN** une image avec fond bleu uni `#0000ff` et un sprite contenant une zone bleue interne (non connectée au bord)
- **WHEN** on appelle `compute_bg_mask(img)`
- **THEN** le masque SHALL être `True` (foreground) sur toute la zone bleue interne du sprite, et `False` (fond) sur la zone bleue connectée aux bords

#### Scenario: Tolerance applicable au bruit PNG/JPEG

- **GIVEN** une image avec fond gris `#404040` qui a subi une compression JPEG introduisant un bruit ±3 sur chaque canal
- **WHEN** on appelle `compute_bg_mask(img, tolerance=8)`
- **THEN** tous les pixels du fond bruité SHALL être classés fond (masque `False`)

### Requirement: Les algos `denoise/*` et `sharpen/*` SHALL accepter un paramètre `preserve_bg` pour réinjecter les pixels de fond originaux

Chaque méthode de `pixel-lab/scripts/algorithms/denoise.py` (`median`, `bilateral`, `nlm`) et `pixel-lab/scripts/algorithms/sharpen.py` (`unsharp_mask`, `laplacian`, `kernel`) MUST accepter un paramètre optionnel `preserve_bg: bool = False` déclaré dans son `PARAMS` respectif.

Quand `preserve_bg=True`, l'algo MUST :
1. Appliquer son traitement normalement sur toute l'image (aucune optimisation nécessaire en V1).
2. Calculer le masque via `bgdetect.compute_bg_mask(img_source)` (avec ses valeurs par défaut de `tolerance=8, feather=0`).
3. Si le masque est `None` ou tout à `True` (fond non détecté), retourner le résultat tel quel (no-op sur preserve_bg).
4. Sinon, composer pixel-à-pixel : `out[mask] = out[mask]` (foreground reste traité), `out[~mask] = img_source[~mask]` (fond restauré à l'original).
5. Retourner l'image composée.

Quand `preserve_bg=False` (défaut), l'algo MUST se comporter exactement comme avant cette spec, sans appeler `bgdetect` ni modifier la composition.

#### Scenario: `sharpen` ne touche pas le fond quand preserve_bg=True

- **GIVEN** une image avec fond uni `#404040` et un sprite net
- **WHEN** on applique `sharpen/unsharp_mask(radius=2, percent=300, preserve_bg=True)`
- **THEN** tous les pixels de fond SHALL rester exactement `#404040` byte-à-byte dans l'image de sortie, et le sprite SHALL être accentué comme d'habitude

#### Scenario: preserve_bg=False n'a aucun effet secondaire

- **GIVEN** une image quelconque et un pipeline avec `preserve_bg=False` (défaut)
- **WHEN** le pipeline est exécuté
- **THEN** la sortie SHALL être byte-à-byte identique à celle produite avant l'introduction du paramètre `preserve_bg`

#### Scenario: Fond non détecté, preserve_bg=True sans échec

- **GIVEN** une image dont le fond ne peut pas être détecté (4 coins différents)
- **WHEN** on applique un algo avec `preserve_bg=True`
- **THEN** l'algo SHALL produire son résultat normal (traitement sur toute l'image), sans erreur, et le logging SHALL mentionner « fond non détecté, preserve_bg ignoré »

### Requirement: Chaque module algorithme SHALL exposer un dict `PARAMS` décrivant les paramètres de ses méthodes
En complément du dict `METHODS`, chaque module `pixel-lab/scripts/algorithms/<algo>.py` MUST exposer un attribut `PARAMS` de type `dict[str, list[dict]]` mappant chaque nom de méthode à la liste ordonnée de ses paramètres exposables. Chaque entrée de paramètre MUST contenir au minimum les clés `name` (str), `type` (`"int"` | `"float"` | `"str"`) et `default` (valeur cohérente avec `type`). Les bornes `min` et `max` (numériques) sont obligatoires pour les types `int` et `float`.

#### Scenario: PARAMS aligné sur METHODS
- **GIVEN** un module `algorithms/sharpen.py`
- **WHEN** on lit ses attributs publics
- **THEN** chaque clé de `METHODS` SHALL avoir une entrée correspondante dans `PARAMS`, et chaque entrée SHALL être une liste (éventuellement vide si la méthode n'a aucun paramètre exposé)

#### Scenario: Métadonnée d'un paramètre
- **GIVEN** la clé `PARAMS["unsharp_mask"]` du module `sharpen`
- **WHEN** on lit la première entrée
- **THEN** elle SHALL contenir au minimum `{"name": "radius", "type": "float", "default": 1.2, "min": 0.1, "max": 10}` avec ces clés et types exacts

#### Scenario: Méthode sans paramètre
- **GIVEN** une méthode dont la signature ne prend que `img`
- **WHEN** on lit son entrée dans `PARAMS`
- **THEN** la valeur SHALL être une liste vide `[]`, ce qui signale au consommateur qu'aucun champ d'entrée n'est à proposer

### Requirement: Les `default` de `PARAMS` SHALL correspondre aux defaults Python des fonctions
Pour chaque paramètre déclaré dans `PARAMS`, le `default` MUST être strictement égal au default de la signature Python correspondante. Cette égalité garantit qu'invoquer la fonction sans paramètre via le builder du dashboard donne le même résultat qu'invoquer la fonction sans paramètre via le CLI.

#### Scenario: Cohérence default Python ↔ default PARAMS
- **GIVEN** la fonction `def unsharp_mask(img, radius=1.2, percent=200)`
- **WHEN** on lit `PARAMS["unsharp_mask"]`
- **THEN** les défauts déclarés SHALL être exactement `radius=1.2` et `percent=200`, sans dérive

### Requirement: Les valeurs `min`/`max` SHALL être respectées par toute UI ou validation amont
`PARAMS` MUST documenter les bornes pratiques utilisables pour chaque paramètre numérique : valeurs en dessous de `min` ou au-dessus de `max` SHALL être considérées comme invalides par tout consommateur (UI, backend HTTP, scripts de validation).

#### Scenario: Bornes lisibles côté serveur
- **GIVEN** un paramètre `block` du module `pixelsnap` avec `min:2`, `max:32`
- **WHEN** un consommateur (Flask, frontend) reçoit une valeur `block:99999`
- **THEN** il SHALL la considérer comme invalide en se basant sur `PARAMS`, sans avoir à inspecter le code de la fonction

