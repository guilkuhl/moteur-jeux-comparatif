## ADDED Requirements

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
