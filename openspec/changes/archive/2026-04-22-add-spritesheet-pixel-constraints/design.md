## Context

Le pixel-lab actuel est tourné vers le cleanup d'images individuelles (denoise/sharpen/pixelsnap). Ce change amorce le pivot vers le traitement de spritesheets : un spritesheet est une image qui contient N cellules selon une grille, et le moteur de jeu attend des tailles précises pour éviter les artefacts.

Contraintes cibles classiques :
- Multiple de 16 (Phaser, Godot)
- POT : 64×64, 128×128, 256×256… (textures GL, hardware mobile)
- Padding interne 1-2 px (anti-bleed au filtrage linéaire)
- Marge extérieure 1-2 px (idem, côtés de l'atlas)

## Goals / Non-Goals

**Goals:**
- Valider toutes les contraintes sur chaque cellule/sprite identifié(e).
- **Avertir avant corriger**. Jamais de recadrage silencieux.
- Plan de correction visible en modal (liste des transformations proposées).
- Rapport exportable (liste anomalies, permet de les partager).

**Non-Goals:**
- Corriger automatiquement sans validation.
- Supporter des contraintes arbitraires (expressions mathématiques) — stick aux 4 règles définies.
- Gérer la quantification couleur / palette (hors scope).

## Decisions

**Décision 1 — Validation à la demande, pas en live.**
Click `Valider contraintes` → requête serveur avec l'image + grille + contraintes → violations retournées → rendu overlay rouge par cellule. Pas de live preview des contraintes (trop coûteux pour rien).

**Décision 2 — Correction en 3 étapes.**
1. L'utilisateur clique `Corriger auto`.
2. Modal liste les actions proposées (ex. « Cellule (3,2) : rogner 1 px à droite ; Cellule (5,0) : padder 15 px »).
3. Chaque action peut être individuellement désactivée via case à cocher.
4. Click `Appliquer` → `POST /api/constraints/apply` qui recrée un atlas corrigé et le sauvegarde comme nouvelle iter.

**Décision 3 — Ordre d'application des transformations.**
Pour chaque cellule, l'ordre est fixe :
1. Rognage whitespace (si actif) — trim alpha=0 aux bords.
2. Marge post-rognage (ajouter N px transparent).
3. Vérification multiple de N / POT.
4. Si dimensions non conformes : soit rogner à la plus proche valeur inférieure, soit padder à la plus proche valeur supérieure — l'utilisateur choisit dans le plan de correction.

**Décision 4 — Affichage des violations.**
- Cellule valide : aucune overlay.
- Cellule invalide : overlay `rgba(239,96,96,0.35)` sur toute la cellule + badge rouge avec texte court « 17px ≠ mul16 ».
- Le rapport complet est affiché dans un panneau repliable `#constraint-report`, trié par sévérité.

## Risks / Trade-offs

- **Risque** : l'utilisateur applique une correction qui rogne un pixel significatif (anti-aliasing volontaire par exemple).
  **Mitigation** : preview avant/après pour chaque cellule corrigée, bouton `Reset` facile.

- **Risque** : si la grille est mal définie, les violations sont fausses.
  **Mitigation** : contraintes désactivées par défaut si grille absente, toast « Définis d'abord une grille dans le panneau Slicing ».

- **Risque** : POT conflit avec multiple de 16 (ex. 128 est POT et mul16 ; 192 est mul16 mais pas POT).
  **Mitigation** : si les deux contraintes sont actives, prendre l'intersection (128, 256, 512…) et avertir l'utilisateur.

## Open Questions

- Faut-il exposer un "profil moteur" (Phaser / Godot / Unity) qui pré-régle les contraintes ? → Bonus pour une itération future.
- Le padding interne est-il inclus dans la taille totale ou ajouté ? → Ajouté (taille finale = max(contenu)+2×padding).
