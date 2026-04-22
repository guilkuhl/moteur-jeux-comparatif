## 1. Backend — générateurs de format

- [ ] 1.1 Helper `build_frames(image, slicing, template, options) -> list[Frame]` qui itère les cellules non-ignorées et retourne des `{name, x, y, w, h, pivot?}`
- [ ] 1.2 `emit_json_phaser(frames, atlas_size) -> str`
- [ ] 1.3 `emit_xml_starling(frames, atlas_size) -> str`
- [ ] 1.4 `emit_css_sprites(frames, atlas_basename) -> str`
- [ ] 1.5 `build_individual_pngs(image, frames) -> list[(filename, bytes)]`

## 2. Route POST /api/export

- [ ] 2.1 Lire payload `{image, format, template, options}`
- [ ] 2.2 Charger l'image + config slicing depuis history.json
- [ ] 2.3 Résoudre les noms via `build_frames`, résoudre les collisions
- [ ] 2.4 Construire le ZIP en mémoire (`io.BytesIO` + `zipfile`)
- [ ] 2.5 Sauver dans `outputs/<stem>/export/export_<ts>.zip`
- [ ] 2.6 Retourner `Response(zip_bytes, mimetype='application/zip', headers={...})`

## 3. Frontend — panneau export

- [ ] 3.1 Ajouter `.export-panel` avec les 4 contrôles + bouton
- [ ] 3.2 Au clic `Exporter`, disabled button + loading toast
- [ ] 3.3 `fetch` avec `response.blob()`, créer blob URL, déclencher `<a download>` anchor
- [ ] 3.4 Toast vert de succès

## 4. Pivot override

- [ ] 4.1 Ajouter option `Pivot` au popover override (coords x,y sliders 0-1)
- [ ] 4.2 Dessiner le pivot (croix rouge) sur la cellule si défini

## 5. Tests

- [ ] 5.1 Export json_phaser d'une grille 4×4 → ZIP avec atlas.png + atlas.json contenant 16 frames
- [ ] 5.2 Export individual d'une grille 3×2 avec 1 ignore → ZIP avec 5 PNG
- [ ] 5.3 Template `{name}` avec 2 collisions → suffixes `_2` et `_3` appliqués
- [ ] 5.4 XML validé par un parser XML tiers
- [ ] 5.5 Pivot inclus dans JSON si option cochée
