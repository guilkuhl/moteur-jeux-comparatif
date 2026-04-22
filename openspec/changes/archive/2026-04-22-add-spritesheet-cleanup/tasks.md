## 1. Backend — perceptual hash + détection doublons

- [ ] 1.1 Implémenter `compute_phash(img: Image) -> int` (DCT 8×8 → bitmask 64 bits)
- [ ] 1.2 Route `POST /api/cleanup/detect-duplicates` : itère cellules, calcule phash, retourne paires Hamming ≤ 5
- [ ] 1.3 Permettre paramètre `similarity_threshold` (défaut 5)

## 2. Backend — détection sous-pixel

- [ ] 2.1 Helper `phase_correlate(a: np.ndarray, b: np.ndarray) -> (dx, dy)` via FFT 2D
- [ ] 2.2 Route `POST /api/cleanup/detect-subpixel` : pour chaque paire successive, calculer delta, filtrer |Δ| entre 0.2 et 2.5
- [ ] 2.3 Retourner `{cell, delta}` pour chaque cellule suspecte

## 3. Backend — normalisation

- [ ] 3.1 Route `POST /api/cleanup/normalize` : détecter maxW/maxH, créer nouvelle image, coller chaque cellule centrée/aligné dans sa case cible
- [ ] 3.2 Sauvegarder comme nouvelle iter `iter_NNN_normalize.png`

## 4. Backend — rapport

- [ ] 4.1 Route `GET /api/cleanup/report` : exécute les 4 détections + lit les violations de contraintes existantes
- [ ] 4.2 Retourne JSON structuré avec download header

## 5. Frontend — vue grille-miniatures + drag-drop

- [ ] 5.1 Panneau `.cleanup-frames-view` avec miniatures 128×128 (canvas par cellule)
- [ ] 5.2 HTML5 Drag and Drop API : dragstart/dragover/drop pour réordonner
- [ ] 5.3 À chaque drop, recalculer l'ordre global et persister via PUT slicing

## 6. Frontend — modals de validation

- [ ] 6.1 Modal doublons : liste paires avec preview + 3 boutons par paire
- [ ] 6.2 Modal sous-pixel : liste cellules avec delta + 3 boutons par ligne
- [ ] 6.3 Modal normaliser : preview avant/après + choix alignement
- [ ] 6.4 Toasts de confirmation après chaque action

## 7. Tests

- [ ] 7.1 Image avec 2 cellules pixel-identiques → détection doublons retourne exactement 1 paire
- [ ] 7.2 Image avec cellule clairement décalée de 1px → détection sous-pixel retourne un delta (1.0, 0.0) ± 0.1
- [ ] 7.3 Image avec 3 tailles différentes → normalize produit une iter uniforme
- [ ] 7.4 Rapport JSON téléchargé contient les 5 sections
