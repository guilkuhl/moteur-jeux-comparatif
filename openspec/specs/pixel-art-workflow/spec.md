# pixel-art-workflow Specification

## Purpose
Automatiser en une seule commande le pipeline complet du Pixel Lab : diagnostic → recommandations → application ordonnée des traitements → mise à jour de `history.json` → résumé final. Source de vérité : `pixel-lab/scripts/workflow.py`.

## Requirements

### Requirement: Le workflow SHALL enchaîner diagnostic, recommandations et application
Le script `workflow.py` MUST, dans cet ordre, ouvrir l'image source, appeler `diagnose()`, afficher le rapport via `print_report()`, construire le plan via `build_recommendations()`, appliquer chaque étape via les algorithmes du paquet `algorithms`, puis écrire le résumé final des fichiers produits.

#### Scenario: Flux nominal
- **GIVEN** `python scripts/workflow.py inputs/sprite.png`
- **WHEN** le workflow s'exécute sans erreur
- **THEN** les cinq étapes SHALL se dérouler dans l'ordre précité et le résumé final SHALL lister au moins un chemin dans `outputs/sprite/`

### Requirement: Le mode `--dry-run` SHALL afficher le plan sans écrire d'itération
Le script MUST supporter `--dry-run` pour afficher le diagnostic et la liste des traitements recommandés SANS créer de fichier dans `outputs/` ni modifier `history.json`.

#### Scenario: Aucune écriture en dry-run
- **GIVEN** la commande `python scripts/workflow.py inputs/sprite.png --dry-run`
- **WHEN** le workflow se termine
- **THEN** aucun nouveau fichier SHALL être créé dans `outputs/sprite/` et `history.json` SHALL rester inchangé

### Requirement: Le mode `--force` SHALL exécuter même si l'image est jugée correcte
Par défaut, lorsque `build_recommendations` retourne une liste vide ou non critique, le workflow MUST s'arrêter sans rien faire. L'option `--force` MUST permettre d'appliquer malgré tout le plan recommandé par défaut.

#### Scenario: Image propre
- **GIVEN** une image qui ne déclenche aucune recommandation
- **WHEN** `python scripts/workflow.py inputs/clean.png` est exécuté sans `--force`
- **THEN** le workflow SHALL afficher un message indiquant qu'aucun traitement n'est nécessaire et sortir sans itération

#### Scenario: Force sur image propre
- **GIVEN** la même image propre
- **WHEN** `python scripts/workflow.py inputs/clean.png --force` est exécuté
- **THEN** le workflow SHALL exécuter le plan par défaut (sharpen, etc.) et créer les itérations correspondantes

### Requirement: L'option `--scale` SHALL contrôler l'upscale final
Le script MUST accepter `--scale <N>` (défaut 1, pas d'upscale) pour appliquer une étape d'upscale finale `scale2x` avec un facteur `N` compatible avec les méthodes disponibles.

#### Scenario: Upscale ×2
- **GIVEN** la commande `python scripts/workflow.py inputs/sprite.png --scale 2`
- **WHEN** le plan est assemblé
- **THEN** une étape `scale2x` SHALL être ajoutée en fin de plan et la dernière itération produite SHALL être de dimensions doublées

### Requirement: L'option `--only` SHALL restreindre les algorithmes appliqués
Le script MUST accepter `--only <algo1> <algo2> ...` pour filtrer les étapes recommandées et ne conserver que celles dont l'algo figure dans la liste.

#### Scenario: Filtrer à sharpen et denoise
- **GIVEN** la commande `python scripts/workflow.py inputs/sprite.png --only sharpen denoise`
- **WHEN** le plan est filtré
- **THEN** seules les étapes `sharpen` et `denoise` SHALL être exécutées, et toute étape `pixelsnap` ou `scale2x` SHALL être ignorée même si recommandée

### Requirement: Chaque étape du workflow SHALL produire une itération tracée
Chaque traitement appliqué MUST produire un fichier `outputs/<image>/iter_NNN_<algo>_<method>.png` et ajouter une entrée à `history["<image>"].runs` avec la référence à cette itération.

#### Scenario: Plan à trois étapes
- **GIVEN** un plan recommandé de trois étapes
- **WHEN** le workflow s'exécute complet (hors dry-run)
- **THEN** trois fichiers `iter_XXX_*.png` SHALL être créés dans `outputs/<image>/` et la liste `runs` SHALL grossir de trois entrées
