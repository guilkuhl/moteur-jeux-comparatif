# Pixel Lab

Atelier Python pour transformer des sprites pixel-art via 4 familles d'algorithmes : **sharpen**, **scale2x**, **denoise**, **pixelsnap**.

## Usage CLI

```bash
python scripts/process.py inputs/sprite.png sharpen method=unsharp_mask radius=1.2 percent=200
python scripts/process.py inputs/sprite.png scale2x method=scale2x
python scripts/process.py inputs/sprite.png denoise method=bilateral sigma_color=50
python scripts/process.py inputs/sprite.png pixelsnap method=median block=4
```

Les résultats sont sauvegardés dans `outputs/{nom_image}/` et indexés dans `history.json`.

## Dashboard interactif

Le dashboard permet de déclencher des conversions directement depuis le navigateur, sans toucher au terminal.

### Prérequis

```bash
pip install -r pixel-lab/requirements.txt   # installe Flask
```

### Lancement

Un seul process Flask sert à la fois le dashboard statique et l'API :

```bash
# Mode dev (équivalent à `python pixel-lab/server/app.py`)
python pixel-lab/serve.py
# → http://localhost:5500/dashboard/index.html

# Mode prod (nécessite gunicorn)
pip install -r pixel-lab/requirements-prod.txt
PIXEL_LAB_PROD=1 python pixel-lab/serve.py
```

### Ports utilisés

| Processus | Port | Configurable |
|-----------|------|-------------|
| `serve.py` (Flask + dashboard + API) | **5500** | `PIXEL_LAB_BIND=127.0.0.1:8080 python serve.py` |

⚠️ En mode prod, gunicorn est lancé avec `-w 1` car le verrou `_active_job`
et le cache preview sont des globaux mémoire. Ne pas monter le nombre de
workers sans porter le lock vers un mécanisme inter-process.

### Mode dégradé

Si le serveur n'est **pas** lancé, le dashboard ouvert en `file://` reste
utilisable en lecture seule : la sidebar affiche les itérations existantes,
et le panneau "Convertir" affiche **"API hors-ligne"** sans erreur bloquante.
