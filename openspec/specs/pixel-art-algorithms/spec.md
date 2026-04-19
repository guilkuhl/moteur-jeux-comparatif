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
