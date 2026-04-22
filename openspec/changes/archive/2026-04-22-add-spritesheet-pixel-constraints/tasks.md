## 1. Backend — validation

- [ ] 1.1 Route `POST /api/constraints/validate` : lire l'image, appliquer la grille (cols/rows/overrides), itérer sur chaque cellule
- [ ] 1.2 Pour chaque cellule, vérifier : dimensions multiples de N, POT, présence de whitespace, padding interne, marge extérieure
- [ ] 1.3 Retourner `{violations: [{cellX, cellY, issue: "mulN|pot|overflow|...", suggestion}]}`

## 2. Backend — correction

- [ ] 2.1 Route `POST /api/constraints/apply` : charger l'image, pour chaque correction appliquer `ROGNER`, `PADDER`, `CENTRER` selon les params
- [ ] 2.2 Sauvegarder comme `iter_NNN_constraints.png` dans `outputs/<stem>/`
- [ ] 2.3 Mettre à jour `history.json` via la même logique que les iters existants

## 3. Frontend — panneau contraintes

- [ ] 3.1 Ajouter `.constraints-panel` avec tous les contrôles listés dans le spec
- [ ] 3.2 Persister les valeurs dans `localStorage.dashConstraints` (JSON sérialisé)
- [ ] 3.3 Désactiver le panneau si pas de grille définie (toast explicatif)

## 4. Frontend — rendu violations

- [ ] 4.1 Créer un canvas overlay `#constraint-overlay` pour peindre les cellules violant les contraintes en rouge
- [ ] 4.2 Afficher les badges textuels (« 17px ≠ mul16 ») à l'angle supérieur gauche de chaque cellule
- [ ] 4.3 Remplir `#constraint-report` avec les entrées triées par sévérité

## 5. Frontend — modal de correction

- [ ] 5.1 Étendre le composant modal existant pour afficher une liste d'actions avec cases à cocher
- [ ] 5.2 Générer un preview miniature de chaque cellule avant/après (canvas 64×64)
- [ ] 5.3 Au `Appliquer`, envoyer le subset d'actions cochées

## 6. Tests

- [ ] 6.1 Image 256×256 avec grille 4×4, cellules 64 (mul16 ✓) → 0 violations
- [ ] 6.2 Image 257×257 grille 4×4 (une cellule 65px) → 1 violation « 65 ≠ mul16 »
- [ ] 6.3 Correction ROGNER sur cette cellule → iter produite avec cellule 64
- [ ] 6.4 Contraintes POT + mul16 → intersection {64, 128, 256, 512} visible dans le tooltip
- [ ] 6.5 Rapport exportable (télécharger JSON du rapport actuel)
