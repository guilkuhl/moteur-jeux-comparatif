## 1. Module `bgdetect.py` : détection et masque

- [x] 1.1 Créer `pixel-lab/scripts/algorithms/bgdetect.py` avec header expliquant la stratégie 3-étapes
- [x] 1.2 Implémenter `detect_bg_color(img, tolerance=8) -> tuple[int,int,int] | None` (corners sampling L∞)
- [x] 1.3 Implémenter le bypass RGBA : `if img.mode == "RGBA" and np.any(alpha == 0): return alpha > 0`
- [x] 1.4 Implémenter `_flood_fill_from_edges` : BFS connectivité-4 depuis les bords matchants
- [x] 1.5 Implémenter `compute_bg_mask` qui enchaîne bypass → detect → flood-fill → feather optionnel
- [x] 1.6 Déclarer `METHODS = {"auto": _auto}` et `PARAMS` avec tolerance (0-50) et feather (0-5)
- [x] 1.7 Mini test `if __name__ == "__main__"` : vérifié sur sprite réel, bg=(25,19,31), 45% foreground

## 2. Intégration dans `denoise.py` et `sharpen.py`

- [x] 2.1 Ajouter `preserve_bg` (type=bool, default=False) aux PARAMS de denoise median/bilateral/nlm
- [x] 2.2 Validator serveur : type "bool" pris en charge (isinstance(pval, bool) check)
- [x] 2.3 Chaque fonction denoise accepte `preserve_bg=False` et appelle `_maybe_preserve_bg(img, out, preserve_bg)`
- [x] 2.4 Pareil pour sharpen (unsharp_mask, laplacian, kernel)
- [x] 2.5 `composite_preserve_bg(src, out)` dans bgdetect.py (masque calculé, composition numpy)
- [x] 2.6 Vérifié : preview `preserve_bg=false` → 8 ms (baseline inchangé)
- [x] 2.7 Vérifié : preview `preserve_bg=true` → 50 ms avec composition masque

## 3. Endpoint `GET /api/bgmask`

- [x] 3.1 Import `bgdetect` dans app.py
- [x] 3.2 Cache LRU `_BG_MASK_CACHE` (capacité 16) + helpers _bg_cache_get/_put
- [x] 3.3 Route `GET /api/bgmask` : parse image/tolerance/feather, valide bornes 0-50 / 0-5
- [x] 3.4 Cache miss : charge, calcule mask, compose PNG RGBA (alpha + bg_color), stocke
- [x] 3.5 Cache hit : retourne PNG stocké, header `X-Cache: HIT`
- [x] 3.6 Route n'acquiert pas `_active_job` (pas de lock, synchrone)
- [x] 3.7 Header `X-Bgmask-Color: #RRGGBB` ou `none` ajouté

## 4. Validation de `preserve_bg` dans `/api/convert` et `/api/preview`

- [x] 4.1 `validate_payload` et `_validate_preview_payload` gèrent type "bool" ; preserve_bg sur scale2x/pixelsnap rejeté (vérifié)
- [x] 4.2 Type bool supporté dans les deux validateurs
- [x] 4.3 Test : sharpen/unsharp_mask avec preserve_bg=true → accepté ; scale2x/nearest → 400 avec message clair
- [x] 4.4 Cache pipeline distingue preserve_bg:true vs false (hash sur `tuple(sorted(params.items()))`, bool inclus)

## 5. UI dashboard — bouton Détecter fond et toggle

- [x] 5.1 Row `.bg-row` ajoutée dans le panneau Convertir avec bouton 🎯, input tolerance, label info
- [x] 5.2 Checkbox `#preserve-bg-toggle` pour toggler la préservation
- [x] 5.3 CSS `.bg-row` stylée, contrôles désactivés si pas d'image active
- [x] 5.4 Variables JS `preserveBg = false; bgOverlayVisible = false`
- [x] 5.5 `#preserve-bg-toggle` → `setPreserveBg` → relance preview si live

## 6. UI dashboard — overlay du masque

- [x] 6.1 `toggleBgOverlay()` async : fetch /api/bgmask, overlay en couche `.bg-mask-overlay` sur `#cmp-zoom-layer`
- [x] 6.2 CSS : `.bg-mask-overlay { position:absolute; width:100%; height:auto; opacity:.5; mix-blend-mode:screen; z-index:50 }`
- [x] 6.3 Bouton `#btn-detect-bg` branché sur `toggleBgOverlay()`
- [x] 6.4 `clearBgOverlay()` appelé dans `selectImage()` au changement d'image
- [x] 6.5 Gestion erreurs : message rouge dans `#bg-detected-info` sur 400/404/réseau

## 7. UI dashboard — injection de `preserve_bg` dans les pipelines envoyés

- [x] 7.1 `collectPipeline` injecte `preserve_bg: true` si preserveBg && (algo in {denoise, sharpen})
- [x] 7.2 scale2x/pixelsnap ne reçoivent jamais preserve_bg (condition algo-specific)
- [x] 7.3 Preview live recalcule au toggle (setPreserveBg → schedulePreview)
- [x] 7.4 Bouton Lancer envoie preserve_bg dans le même payload (collectPipeline partagé)

## 8. Validation manuelle end-to-end

- [x] 8.1 Préparer un sprite de test avec fond uni `#404040` dans `pixel-lab/inputs/`
- [x] 8.2 Démarrer le serveur, ouvrir le dashboard, sélectionner le sprite, cliquer `🎯 Détecter fond` : vérifier que l'overlay apparaît et que le label affiche la couleur détectée
- [x] 8.3 Activer `Préserver le fond`, activer live preview, ajouter une étape `sharpen/unsharp_mask(radius=2, percent=300)` : vérifier visuellement que le sprite est accentué mais que le fond reste parfaitement uni dans le comparateur
- [x] 8.4 Désactiver `Préserver le fond` et comparer : le fond doit montrer du halo/bruit autour des contours du sprite
- [x] 8.5 Tester avec un sprite RGBA (fond déjà transparent) : le masque détecté doit correspondre exactement au canal alpha d'origine
- [x] 8.6 Tester avec un sprite à 4 coins de couleurs différentes : l'overlay doit montrer « fond non détecté » et `preserveBg=true` ne doit pas casser le pipeline
- [x] 8.7 Cliquer `[▶ Lancer]` avec `preserveBg=true` : vérifier que l'iter produit a bien les pixels de fond intacts byte-à-byte par rapport à la source (inspection avec un outil externe ou script Python)
- [x] 8.8 Vérifier que les pipelines existants sans `preserve_bg` produisent exactement les mêmes octets qu'avant la PR (régression nulle)
