## Context

L'export suit le slicing (la capability précédente). Formats cibles :

- **Phaser 3 / Starling XML** : XML avec `<SubTexture name="..." x=".." y=".." width=".." height=".." frameX=".." frameY=".." frameWidth=".." frameHeight=".."/>`.
- **Phaser 3 / TexturePacker JSON (Hash)** :
  ```json
  {
    "frames": { "hero_idle": { "frame": {"x": 0, "y": 0, "w": 16, "h": 16}, ... }, ... },
    "meta": { "image": "atlas.png", "size": {"w":256, "h":256} }
  }
  ```
- **CSS sprites** : `.hero_idle { background-position: -0px -0px; width: 16px; height: 16px; }` + `.sprite { background: url('atlas.png'); }`.
- **Sprites individuels** : ZIP `{basename}.zip` contenant un PNG par cellule non-ignorée.

## Goals / Non-Goals

**Goals:**
- Un seul clic → téléchargement dans le bon format.
- Nommage paramétrable (template).
- Support pivot (pour Phaser, stocké comme `pivot: {x, y}` dans les overrides).
- Fichier JSON/XML généré à côté du PNG dans un ZIP.

**Non-Goals:**
- Rotation de sprites (TexturePacker feature avancée).
- Packing rectangle non-uniforme (on re-packe pas, on exporte la grille telle quelle).
- Format Aseprite / Unity .meta — demandes user specific si besoin plus tard.

## Decisions

**Décision 1 — L'atlas reste = image d'entrée.**
On ne re-packe pas les cellules dans un atlas optimisé pour cette première itération. On exporte l'image telle quelle comme `atlas.png`, et le JSON/XML décrit les coordonnées dans CETTE image. Plus simple, plus prévisible, et compatible avec les cas où le spritesheet est déjà bien organisé.

**Décision 2 — Packing uniquement pour sprites individuels.**
En mode "sprites individuels", on copie chaque cellule dans un PNG séparé. Pas d'atlas à régénérer.

**Décision 3 — Template de nom.**
Variables disponibles : `{basename}` (source), `{col}` / `{row}`, `{index}` (0-based), `{name}` (nom custom override ou `col_row` par défaut). Template invalide (variable inconnue) → warning + usage du défaut.

**Décision 4 — Téléchargement via blob côté client.**
`POST /api/export` renvoie un ZIP en binaire avec header `Content-Disposition: attachment; filename=...`. Le dashboard reçoit le blob et déclenche un download anchor.

**Décision 5 — Pivot stocké dans les overrides.**
Un override additionnel de type `pivot` avec `{x: 0..1, y: 0..1}` (ratio relatif à la cellule). Exporté dans le JSON/XML pour les moteurs qui supportent un centre d'origine custom.

## Risks / Trade-offs

- **Risque** : un spritesheet très dense (1000+ cellules) → JSON énorme, XML encore plus.
  **Mitigation** : compression ZIP + warning si > 10k cellules.

- **Risque** : template avec variables de collision (`{name}` pas défini → fallback sur `{col}_{row}` qui peut déjà exister ailleurs).
  **Mitigation** : détecter collisions avant export, renommer avec suffixe `_2`, `_3`…

## Open Questions

- Sortie par défaut dans `outputs/<stem>/export/` ou téléchargement direct ? → Les deux : sauvegarde côté serveur ET téléchargement.
