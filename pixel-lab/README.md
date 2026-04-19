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

Ouvrir **deux terminaux** depuis la racine du projet :

```bash
# Terminal 1 — serveur statique (dashboard)
python pixel-lab/serve.py
# → http://localhost:5500/dashboard/index.html

# Terminal 2 — API Flask (conversions)
python pixel-lab/server/app.py
# → http://localhost:5501
```

Puis ouvrir **http://localhost:5500/dashboard/index.html** dans le navigateur.

### Ports utilisés

| Processus | Port | Configurable |
|-----------|------|-------------|
| `serve.py` (dashboard statique) | **5500** | `python serve.py --port 8080` |
| `server/app.py` (API Flask) | **5501** | modifier `port=5501` dans `app.py` |

### Mode dégradé

Si Flask n'est **pas** lancé, le dashboard reste utilisable en lecture seule :
- La sidebar affiche les images et itérations existantes.
- Le panneau "Convertir" affiche le message **"API hors-ligne"** et désactive le bouton `▶ Lancer`.
- Aucune erreur bloquante — il suffit de lancer `server/app.py` pour réactiver les conversions.
