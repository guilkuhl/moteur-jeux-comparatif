## 1. Backend — algorithme de composition

- [ ] 1.1 Helper `compose_quadrant(tile_atom, quadrant_id) -> Image` qui extrait Q_TL/TR/BL/BR
- [ ] 1.2 Pour `wang16` : `build_variant_wang16(bit_pattern, base, edge) -> Image` qui assemble 4 quadrants
- [ ] 1.3 Pour `wang47` : `build_variant_wang47(bit_pattern, base, edge, corner_in, corner_out) -> Image`
- [ ] 1.4 Pour `wang256` : full 8-neighbor masking
- [ ] 1.5 Optionnel : feathering 1-2 px sur les jonctions (`PIL.ImageFilter.GaussianBlur` localisé)

## 2. Backend — assembly spritesheet

- [ ] 2.1 Fonction `assemble_grid(variants: list[Image], cols, rows, tile_size) -> Image`
- [ ] 2.2 Layout : wang16 → 4×4 ; wang47 → 7×7 (avec 2 cellules vides) ; wang256 → 16×16

## 3. Route POST /api/autotile/generate

- [ ] 3.1 Lire payload `{mode, tiles, tile_size}` (tiles peuvent être base64 ou références à des cellules du spritesheet courant)
- [ ] 3.2 Valider que toutes les tiles requises sont présentes selon le mode
- [ ] 3.3 Générer toutes les variants, assembler la grille, sauvegarder iter
- [ ] 3.4 Retourner `{iterPath, gridLayout}`

## 4. Frontend — panneau auto-tile

- [ ] 4.1 Ajouter `.autotile-panel` avec contrôles
- [ ] 4.2 Sélecteurs de tile : 2 onglets (cellule du sheet / upload)
- [ ] 4.3 Mode `cellule du sheet` : permet clic sur le comparateur pour assigner
- [ ] 4.4 Mode `upload` : drag-drop d'un PNG → preview miniature
- [ ] 4.5 Bouton `Générer` enable seulement si toutes les tiles requises sont définies

## 5. Tests

- [ ] 5.1 Wang16 avec deux tiles 16×16 → spritesheet 64×64 produit, 16 variants visuellement cohérents
- [ ] 5.2 Wang47 avec 5 tiles → 47 variants + 2 cellules vides
- [ ] 5.3 Variant 0b1111 (tous voisins) = base pure
- [ ] 5.4 Variant 0b0000 (aucun voisin) = bord pur
