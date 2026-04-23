# Pixel Lab

Atelier Python pour transformer des sprites pixel-art via 4 familles d'algorithmes : **sharpen**, **scale2x**, **denoise**, **pixelsnap**.

## Usage CLI

```bash
python pixel-lab/scripts/process.py inputs/sprite.png sharpen method=unsharp_mask radius=1.2 percent=200
python pixel-lab/scripts/process.py inputs/sprite.png scale2x method=scale2x
python pixel-lab/scripts/process.py inputs/sprite.png denoise method=bilateral sigma_color=50
python pixel-lab/scripts/process.py inputs/sprite.png pixelsnap method=median block=4
```

Les résultats sont sauvegardés dans `outputs/{nom_image}/` et indexés dans `history.json`.

## Architecture

- **Back** : FastAPI (`server_fastapi/`) — routers par domaine, schémas Pydantic v2, services isolés, SSE via `StreamingResponse`. OpenAPI auto-exposé sur `/openapi.json` + `/docs`.
- **Front** : SPA Vue 3 (`frontend/`) — Composition API, TypeScript strict, Pinia, Vite. Bundle gzipped ~30 KB.
- **CLI** : scripts Python indépendants (`scripts/process.py`, `workflow.py`, `batch.py`) — partagent `scripts/apply_step.py` avec le back.

## Lancement

### Prod (un seul process)

Build le front une fois, puis le back sert tout :

```bash
pip install -r pixel-lab/requirements.txt
cd pixel-lab/frontend && npm ci && npm run build && cd ..
cp -r frontend/dist frontend-dist            # artefact servi par FastAPI

python pixel-lab/serve.py
# → http://127.0.0.1:5500/
```

Pour une vraie prod (supervision gunicorn) :

```bash
pip install -r pixel-lab/requirements-prod.txt
PIXEL_LAB_PROD=1 python pixel-lab/serve.py
```

### Dev (deux terminaux, HMR)

```bash
# Terminal 1 — back avec reload auto
python pixel-lab/serve.py
# → http://127.0.0.1:5500/ (API + docs)

# Terminal 2 — front Vite
cd pixel-lab/frontend && npm run dev
# → http://127.0.0.1:5173/ (HMR, proxy /api → :5500)
```

### Ports utilisés

| Processus | Port | Configurable |
|-----------|------|-------------|
| `serve.py` (FastAPI / uvicorn) | **5500** | `PIXEL_LAB_BIND=127.0.0.1:8080 python serve.py` |
| `npm run dev` (Vite) | **5173** | `vite.config.ts` |

⚠️ En mode prod, gunicorn est lancé avec `-w 1` : le verrou `_active_job`, le cache
preview et le cache bgmask sont des globaux mémoire du process. Monter `-w` > 1
sans porter ces états vers un mécanisme inter-process (fichier lock, Redis)
casserait la garantie « un seul job actif à la fois ».

## Scripts front utiles

```bash
cd pixel-lab/frontend

npm run dev          # dev server HMR
npm run build        # build prod (dist/)
npm run type-check   # vue-tsc strict
npm run lint         # ESLint + Prettier
npm run test         # Vitest
npm run check:size   # fail si le plus gros chunk gz > 300 KB
```

## Explorer l'API

- `GET /healthz` → `{"status":"ok","version":"1.0.0"}`
- `GET /docs` → Swagger UI interactif
- `GET /openapi.json` → schéma OpenAPI 3.1
