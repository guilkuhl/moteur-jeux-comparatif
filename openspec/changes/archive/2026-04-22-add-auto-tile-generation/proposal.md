## Why

Pour les jeux à tilemap (RPG, plateformer, roguelike), un tile « base » seul est insuffisant : il faut TOUTES les variantes de transitions selon les voisins (coin haut-gauche, bord supérieur, etc.). Les conventions standard sont **Wang 16 tiles** (4 bits, 2×2 voisins) et **Wang 47 / blob 47 tiles** (8 voisins, masques de Marching Squares étendus). Générer ces variantes manuellement est tedious. Ce change ajoute un générateur auto-tile : à partir d'1 ou 2 tiles « base » + « masque/bord », il produit la variante complète prête pour Tiled / Godot / Phaser.

## What Changes

- **Panneau `Auto-tile`** :
  - Sélecteur de mode : `Wang 16 (corners)`, `Wang 47 (blob)`, `Wang 256 (full 8-neighbor)`.
  - Inputs `Tile base` (cellule du spritesheet ou fichier) et `Tile bord` (idem).
  - Optionnel : `Tile coin extérieur`, `Tile coin intérieur` selon mode.
  - Slider `Taille de tile` (8/16/32/64 px).
  - Bouton `Générer` qui produit un nouveau spritesheet complet contenant les 16/47/256 variantes.
  - Le résultat apparaît comme nouvelle iter dans `outputs/<stem>/`.

## Capabilities

### New Capabilities
- `auto-tile-generation`: génération automatique de tiles connectables Wang 16/47/256 à partir de tiles atomiques.

### Modified Capabilities
- `pixel-art-dashboard`: ajout du panneau Auto-tile.

## Impact

- **Frontend** : panneau dédié, sélection des tiles d'entrée (preview).
- **Backend** : nouvelle route `POST /api/autotile/generate` avec algorithmes de blending pour chaque variante.
- **Algorithmes** : composition de masques (alpha blending par bit-pattern), pour chaque combinaison de bits voisins, prendre les portions appropriées des tiles d'entrée.
- **Specs** : nouvelle capability + delta dashboard.
- **Notes** : feature significative et indépendante. Peut être considérée comme un module à part dans le pixel-lab.
