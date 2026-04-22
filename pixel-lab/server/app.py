import base64
import datetime
import io
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import zipfile
from collections import OrderedDict
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from flask import Flask, Response, jsonify, redirect, request, send_from_directory
from PIL import Image
from werkzeug.exceptions import RequestEntityTooLarge

ROOT = Path(__file__).parent.parent        # pixel-lab/
SCRIPTS_DIR = ROOT / "scripts"
INPUTS_DIR  = ROOT / "inputs"
OUTPUTS_DIR = ROOT / "outputs"
HISTORY_FILE = ROOT / "history.json"

sys.path.insert(0, str(SCRIPTS_DIR))
from algorithms import bgdetect, denoise, pixelsnap, scale2x, sharpen

ALGO_MODULES = {
    "sharpen":   sharpen,
    "scale2x":   scale2x,
    "denoise":   denoise,
    "pixelsnap": pixelsnap,
}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB max upload

INPUTS_TRASH  = INPUTS_DIR / "_trash"
OUTPUTS_TRASH = OUTPUTS_DIR / "_trash"
ALLOWED_UPLOAD_EXTS = {".png", ".webp", ".jpg", ".jpeg"}
_SAFE_BASENAME_RE = re.compile(r"[^A-Za-z0-9._\- ]+")


def _sanitize_basename(name: str) -> str:
    name = (name or "").strip().strip(".")
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    else:
        ext = ext.lower()
    stem = _SAFE_BASENAME_RE.sub("_", stem).strip("_ ")
    if not stem:
        stem = "image"
    return f"{stem}.{ext}" if ext else stem


def _suggest_unused_name(basename: str) -> str:
    stem, dot, ext = basename.rpartition(".")
    if not dot:
        stem, ext = basename, ""
    else:
        ext = "." + ext
    i = 2
    while (INPUTS_DIR / f"{stem}-{i}{ext}").exists():
        i += 1
        if i > 999:
            break
    return f"{stem}-{i}{ext}"


def _move_to_trash(src: Path, trash_root: Path) -> Path:
    """Déplace `src` dans `trash_root` avec un timestamp unique. Retourne le chemin destination."""
    trash_root.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    if src.is_file():
        stem, ext = src.stem, src.suffix
        dest = trash_root / f"{stem}_{ts}{ext}"
        n = 1
        while dest.exists():
            n += 1
            dest = trash_root / f"{stem}_{ts}_{n}{ext}"
    else:
        dest = trash_root / f"{src.name}_{ts}"
        n = 1
        while dest.exists():
            n += 1
            dest = trash_root / f"{src.name}_{ts}_{n}"
    shutil.move(str(src), str(dest))
    return dest


@app.errorhandler(RequestEntityTooLarge)
def _too_large(_e):
    return jsonify({"error": "too_large", "message": "Fichier trop gros (> 20 MB)."}), 413


@app.route("/")
def index():
    return redirect("/dashboard/index.html")

@app.route("/<path:filename>", methods=["GET", "HEAD"])
def serve_static(filename):
    return send_from_directory(str(ROOT), filename)

# ── Job store ─────────────────────────────────────────────────────────────────

_lock       = threading.Lock()
_active_job: str | None = None
_jobs: dict = {}     # job_id → {state, events: list}


# ── GET /api/inputs ───────────────────────────────────────────────────────────

@app.route("/api/inputs")
def api_inputs():
    exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tga"}
    history: dict = {}
    if HISTORY_FILE.exists():
        history = json.loads(HISTORY_FILE.read_text("utf-8"))

    files = []
    if INPUTS_DIR.exists():
        for f in sorted(INPUTS_DIR.iterdir()):
            if not f.is_file():
                continue
            if f.suffix.lower() in exts:
                files.append({"name": f.name, "processed": f.stem in history})
    return jsonify(files)


# ── GET /api/algos ────────────────────────────────────────────────────────────

@app.route("/api/algos")
def api_algos():
    result = {}
    for algo_name, mod in ALGO_MODULES.items():
        methods = {}
        params = getattr(mod, "PARAMS", {})
        for method_name in mod.METHODS:
            methods[method_name] = {"params": params.get(method_name, [])}
        result[algo_name] = {"methods": methods}
    return jsonify(result)


# ── Validation ────────────────────────────────────────────────────────────────

_INPUT_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tga"}

def _resolve_input(name: str) -> Path | None:
    """Résout un nom (avec ou sans extension) vers le fichier réel dans inputs/."""
    exact = INPUTS_DIR / name
    if exact.exists():
        return exact
    for ext in _INPUT_EXTS:
        candidate = INPUTS_DIR / (name + ext)
        if candidate.exists():
            return candidate
    return None

def validate_payload(payload: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []
    images   = payload.get("images", [])
    pipeline = payload.get("pipeline", [])

    if not images:
        errors.append("images: liste vide")
    for img in images:
        if not isinstance(img, str) or "/" in img or "\\" in img or ".." in img:
            errors.append(f"images: nom invalide '{img}'")
        elif _resolve_input(img) is None:
            errors.append(f"images: fichier introuvable '{img}'")

    if not pipeline:
        errors.append("pipeline: liste vide")

    for i, step in enumerate(pipeline):
        algo   = step.get("algo")
        method = step.get("method")
        params = step.get("params", {})

        if algo not in ALGO_MODULES:
            errors.append(f"pipeline[{i}].algo: algo inconnu '{algo}'")
            continue
        mod = ALGO_MODULES[algo]
        if method not in mod.METHODS:
            errors.append(f"pipeline[{i}].method: méthode inconnue '{method}'")
            continue
        allowed = {p["name"]: p for p in getattr(mod, "PARAMS", {}).get(method, [])}
        for pname, pval in params.items():
            if pname not in allowed:
                errors.append(f"pipeline[{i}].params.{pname}: paramètre non déclaré dans PARAMS")
                continue
            meta = allowed[pname]
            if meta.get("type") == "bool":
                if not isinstance(pval, bool):
                    errors.append(f"pipeline[{i}].params.{pname}: valeur booléenne attendue, '{pval}' reçu")
                continue
            try:
                v = float(pval)
                if v < meta["min"] or v > meta["max"]:
                    errors.append(
                        f"pipeline[{i}].params.{pname}: {pval} hors bornes "
                        f"[{meta['min']}, {meta['max']}]"
                    )
            except (TypeError, ValueError):
                errors.append(f"pipeline[{i}].params.{pname}: valeur non numérique '{pval}'")

    return len(errors) == 0, errors


# ── POST /api/convert ─────────────────────────────────────────────────────────

@app.route("/api/convert", methods=["POST"])
def api_convert():
    global _active_job
    payload = request.get_json(force=True) or {}
    ok, errors = validate_payload(payload)
    if not ok:
        return jsonify({"errors": errors}), 400

    with _lock:
        if _active_job is not None:
            return jsonify({"error": "Un job est déjà actif", "job_id": _active_job}), 409
        job_id = str(uuid.uuid4())
        _active_job = job_id
        _jobs[job_id] = {"state": "running", "events": []}

    threading.Thread(target=_run_job, args=(job_id, payload), daemon=True).start()
    return jsonify({"job_id": job_id}), 202


# ── Orchestrateur ─────────────────────────────────────────────────────────────

def _push(job_id: str, event: dict):
    _jobs[job_id]["events"].append(event)


def _run_job(job_id: str, payload: dict):
    global _active_job
    images   = payload["images"]
    pipeline = payload["pipeline"]

    try:
        for img_name in images:
            resolved = _resolve_input(img_name)
            last_input = str(resolved) if resolved else str(INPUTS_DIR / img_name)
            img_stem   = Path(img_name).stem

            for step_idx, step in enumerate(pipeline):
                algo   = step["algo"]
                method = step["method"]
                params = step.get("params", {})

                # Warning scale2x en milieu de pipeline (tâche 2.11)
                if algo == "scale2x" and step_idx < len(pipeline) - 1:
                    _push(job_id, {
                        "type":    "warning",
                        "message": (
                            f"scale2x à l'étape {step_idx + 1}/{len(pipeline)} — "
                            "l'upscale en milieu de pipeline peut produire des artefacts "
                            "sur les étapes suivantes."
                        ),
                    })

                _push(job_id, {
                    "type":   "step_start",
                    "image":  img_name,
                    "step":   step_idx,
                    "algo":   algo,
                    "method": method,
                })

                cmd = [
                    sys.executable,
                    str(SCRIPTS_DIR / "process.py"),
                    last_input, algo,
                    f"method={method}",
                ] + [f"{k}={v}" for k, v in params.items()]
                # Forcer l'output sous le dossier de l'image originale pour le chaînage
                if step_idx > 0:
                    cmd.append(f"name={img_stem}")

                proc = subprocess.Popen(
                    cmd, cwd=str(ROOT),
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                )
                stdout, stderr = proc.communicate()

                if proc.returncode != 0:
                    _push(job_id, {
                        "type":   "step_error",
                        "image":  img_name,
                        "step":   step_idx,
                        "stderr": stderr[:500],
                    })
                    continue

                # Chaînage : input suivant = dernière iter produite (tâche 2.10)
                iter_file = _find_latest_iter(img_stem)
                if iter_file:
                    last_input = str(iter_file)

                _push(job_id, {
                    "type":   "step_done",
                    "image":  img_name,
                    "step":   step_idx,
                    "output": iter_file.name if iter_file else None,
                })

            _push(job_id, {"type": "image_done", "image": img_name})

    finally:
        _push(job_id, {"type": "done"})
        _jobs[job_id]["state"] = "done"
        with _lock:
            _active_job = None


def _find_latest_iter(img_stem: str) -> Path | None:
    out_dir = OUTPUTS_DIR / img_stem
    if not out_dir.exists():
        return None
    iters = sorted(f for f in out_dir.iterdir() if f.name.startswith("iter_"))
    return iters[-1] if iters else None


# ── DELETE /api/outputs/<stem>/<filename> ────────────────────────────────────

def _safe_name(s: str) -> bool:
    return isinstance(s, str) and "/" not in s and "\\" not in s and ".." not in s

def _load_history() -> dict:
    return json.loads(HISTORY_FILE.read_text("utf-8")) if HISTORY_FILE.exists() else {}

def _save_history(h: dict):
    HISTORY_FILE.write_text(json.dumps(h, indent=2, ensure_ascii=False), "utf-8")

@app.route("/api/outputs/<stem>/<filename>", methods=["DELETE"])
def delete_one_output(stem: str, filename: str):
    if not _safe_name(stem) or not _safe_name(filename):
        return jsonify({"error": "nom invalide"}), 400
    filepath = OUTPUTS_DIR / stem / filename
    if not filepath.exists():
        return jsonify({"error": "fichier introuvable"}), 404
    filepath.unlink()
    h = _load_history()
    if stem in h:
        h[stem]["runs"] = [r for r in h[stem]["runs"] if not r.get("output", "").endswith(filename)]
        _save_history(h)
    return jsonify({"deleted": filename})

@app.route("/api/outputs/<stem>", methods=["DELETE"])
def delete_all_outputs(stem: str):
    if not _safe_name(stem):
        return jsonify({"error": "nom invalide"}), 400
    out_dir = OUTPUTS_DIR / stem
    deleted = []
    if out_dir.exists():
        for f in out_dir.iterdir():
            if f.name.startswith("iter_"):
                f.unlink()
                deleted.append(f.name)
    h = _load_history()
    if stem in h:
        h[stem]["runs"] = []
        _save_history(h)
    return jsonify({"deleted": deleted})


# ── POST /api/preview (live preview, volatile, pas de persistance) ──────────

_PREVIEW_CACHE: "OrderedDict[tuple, Image.Image]" = OrderedDict()
_PREVIEW_CACHE_MAX = 32
_preview_cache_lock = threading.Lock()

ALGO_NAMES_SET = set(ALGO_MODULES.keys())


def _validate_preview_payload(payload: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []
    image    = payload.get("image")
    pipeline = payload.get("pipeline", [])
    downscale = payload.get("downscale", 256)

    if not isinstance(image, str) or "/" in image or "\\" in image or ".." in image:
        errors.append(f"image: nom invalide '{image}'")
    elif _resolve_input(image) is None:
        errors.append(f"image: fichier introuvable '{image}'")

    if not isinstance(pipeline, list) or not pipeline:
        errors.append("pipeline: liste vide")
    else:
        for i, step in enumerate(pipeline):
            algo   = step.get("algo")
            method = step.get("method")
            params = step.get("params", {})
            if algo not in ALGO_MODULES:
                errors.append(f"pipeline[{i}].algo: algo inconnu '{algo}'")
                continue
            mod = ALGO_MODULES[algo]
            if method not in mod.METHODS:
                errors.append(f"pipeline[{i}].method: méthode inconnue '{method}'")
                continue
            allowed = {p["name"]: p for p in getattr(mod, "PARAMS", {}).get(method, [])}
            for pname, pval in params.items():
                if pname not in allowed:
                    errors.append(f"pipeline[{i}].params.{pname}: paramètre non déclaré dans PARAMS")
                    continue
                meta = allowed[pname]
                if meta.get("type") == "bool":
                    if not isinstance(pval, bool):
                        errors.append(f"pipeline[{i}].params.{pname}: valeur booléenne attendue, '{pval}' reçu")
                    continue
                try:
                    v = float(pval)
                    if v < meta["min"] or v > meta["max"]:
                        errors.append(
                            f"pipeline[{i}].params.{pname}: {pval} hors bornes "
                            f"[{meta['min']}, {meta['max']}]"
                        )
                except (TypeError, ValueError):
                    errors.append(f"pipeline[{i}].params.{pname}: valeur non numérique '{pval}'")

    if downscale is not None:
        if not isinstance(downscale, int) or isinstance(downscale, bool):
            errors.append(f"downscale: doit être null ou un entier, reçu {type(downscale).__name__}")
        elif downscale < 64 or downscale > 4096:
            errors.append(f"downscale: {downscale} hors bornes [64, 4096]")

    return len(errors) == 0, errors


def _load_source_image(basename: str) -> Image.Image:
    path = _resolve_input(basename)
    # copy() détache l'objet du fichier, sinon toute mutation PIL reste liée au handle
    return Image.open(path).copy()


def _apply_downscale(img: Image.Image, downscale: int | None) -> Image.Image:
    if downscale is None:
        return img
    # LANCZOS donne un meilleur résultat sur photos/illustrations ; pour du pixel-art natif
    # le downscale écrase déjà les détails, le choix du filtre a peu d'impact visuel
    img_copy = img.copy()
    img_copy.thumbnail((downscale, downscale), Image.Resampling.LANCZOS)
    return img_copy


def _apply_step(img: Image.Image, algo: str, method: str, params: dict) -> Image.Image:
    fn = ALGO_MODULES[algo].METHODS[method]
    # Les paramètres arrivent en float (JS), cast vers int pour les params déclarés int
    meta = {p["name"]: p for p in getattr(ALGO_MODULES[algo], "PARAMS", {}).get(method, [])}
    typed_params = {}
    for k, v in params.items():
        if k in meta and meta[k]["type"] == "int":
            typed_params[k] = int(v)
        else:
            typed_params[k] = float(v) if isinstance(v, (int, float)) else v
    return fn(img, **typed_params)


def _encode_png_base64(img: Image.Image) -> tuple[str, int, int]:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii"), img.width, img.height


def _step_key(step: dict) -> tuple:
    algo   = step["algo"]
    method = step["method"]
    params = step.get("params", {}) or {}
    return (algo, method, tuple(sorted(params.items())))


def _pipeline_cache_key(basename: str, mtime_ns: int, downscale: int | None,
                        steps_prefix: list[dict]) -> tuple:
    return (basename, mtime_ns, downscale, tuple(_step_key(s) for s in steps_prefix))


def _cache_get(key: tuple) -> Image.Image | None:
    with _preview_cache_lock:
        img = _PREVIEW_CACHE.get(key)
        if img is not None:
            _PREVIEW_CACHE.move_to_end(key)
            return img.copy()
        return None


def _cache_put(key: tuple, img: Image.Image):
    with _preview_cache_lock:
        _PREVIEW_CACHE[key] = img.copy()
        _PREVIEW_CACHE.move_to_end(key)
        while len(_PREVIEW_CACHE) > _PREVIEW_CACHE_MAX:
            _PREVIEW_CACHE.popitem(last=False)


@app.route("/api/preview", methods=["POST"])
def api_preview():
    payload = request.get_json(force=True) or {}
    ok, errors = _validate_preview_payload(payload)
    if not ok:
        return jsonify({"errors": errors}), 400

    image_name = payload["image"]
    pipeline   = payload["pipeline"]
    downscale  = payload.get("downscale", 256)

    t0 = time.perf_counter()
    source_path = _resolve_input(image_name)
    mtime_ns = source_path.stat().st_mtime_ns

    # Plus long préfixe caché : on part de l'image source downscalée (k=0) si rien
    cached_img: Image.Image | None = None
    start_idx = 0
    for k in range(len(pipeline), 0, -1):
        key = _pipeline_cache_key(image_name, mtime_ns, downscale, pipeline[:k])
        hit = _cache_get(key)
        if hit is not None:
            cached_img = hit
            start_idx = k
            break

    if cached_img is None:
        base_key = _pipeline_cache_key(image_name, mtime_ns, downscale, [])
        hit = _cache_get(base_key)
        if hit is not None:
            cached_img = hit
        else:
            cached_img = _apply_downscale(_load_source_image(image_name), downscale)
            _cache_put(base_key, cached_img)

    current = cached_img
    for i in range(start_idx, len(pipeline)):
        step = pipeline[i]
        current = _apply_step(current, step["algo"], step["method"], step.get("params", {}))
        prefix_key = _pipeline_cache_key(image_name, mtime_ns, downscale, pipeline[: i + 1])
        _cache_put(prefix_key, current)

    b64, w, h = _encode_png_base64(current)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return jsonify({
        "png_base64": b64,
        "width":      w,
        "height":     h,
        "elapsed_ms": elapsed_ms,
        "cache_hit_depth": start_idx,  # utile pour debug / tâche 3.5
    })


# ── GET /api/bgmask : détection automatique du fond, retour PNG RGBA ─────────

_BG_MASK_CACHE: OrderedDict = OrderedDict()
_BG_MASK_CACHE_MAX = 16


def _bg_cache_key(basename: str, mtime_ns: int, tolerance: int, feather: int, mode: str = "highlight") -> tuple:
    return (basename, mtime_ns, tolerance, feather, mode)


def _bg_cache_get(key):
    val = _BG_MASK_CACHE.get(key)
    if val is not None:
        _BG_MASK_CACHE.move_to_end(key)
    return val


def _bg_cache_put(key, val):
    _BG_MASK_CACHE[key] = val
    _BG_MASK_CACHE.move_to_end(key)
    while len(_BG_MASK_CACHE) > _BG_MASK_CACHE_MAX:
        _BG_MASK_CACHE.popitem(last=False)


@app.route("/api/bgmask", methods=["GET"])
def api_bgmask():
    image_name = request.args.get("image", "")
    try:
        tolerance = int(request.args.get("tolerance", "8"))
        feather   = int(request.args.get("feather",   "0"))
    except ValueError:
        return jsonify({"errors": ["tolerance/feather doivent être entiers"]}), 400

    # Validation
    errors = []
    if not image_name or "/" in image_name or "\\" in image_name or ".." in image_name:
        errors.append(f"image: nom invalide '{image_name}'")
    elif _resolve_input(image_name) is None:
        errors.append(f"image: fichier introuvable '{image_name}'")
    if not (0 <= tolerance <= 50):
        errors.append(f"tolerance: {tolerance} hors bornes [0, 50]")
    if not (0 <= feather <= 5):
        errors.append(f"feather: {feather} hors bornes [0, 5]")
    if errors:
        return jsonify({"errors": errors}), 400

    mode_req = request.args.get("mode", "highlight")
    path = _resolve_input(image_name)
    mtime_ns = path.stat().st_mtime_ns
    key = _bg_cache_key(image_name, mtime_ns, tolerance, feather, mode_req)
    cached = _bg_cache_get(key)

    if cached is not None:
        png_bytes, bg_color = cached
        headers = {"Content-Type": "image/png", "X-Cache": "HIT"}
        headers["X-Bgmask-Color"] = "#{:02x}{:02x}{:02x}".format(*bg_color) if bg_color else "none"
        return Response(png_bytes, headers=headers)

    img = Image.open(path)
    bg_color = bgdetect.detect_bg_color(img, tolerance=tolerance)
    mask = bgdetect.compute_bg_mask(img, bg_color=bg_color, tolerance=tolerance, feather=feather)

    # Mode de rendu : "highlight" (vert fluo sur le foreground, défaut, lisible)
    # ou "raw" (couleur de fond détectée, pour debug)
    import numpy as np
    h, w = mask.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    if mode_req == "raw":
        c = bg_color or (0, 0, 0)
        rgba[..., 0] = c[0]; rgba[..., 1] = c[1]; rgba[..., 2] = c[2]
        rgba[..., 3] = np.where(mask, 255, 0).astype(np.uint8)
    else:
        # Foreground : vert fluo semi-opaque ; background : transparent
        rgba[..., 0] = 0; rgba[..., 1] = 255; rgba[..., 2] = 100
        rgba[..., 3] = np.where(mask, 200, 0).astype(np.uint8)

    out_img = Image.fromarray(rgba, mode="RGBA")
    buf = io.BytesIO()
    out_img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    _bg_cache_put(key, (png_bytes, bg_color))

    headers = {"Content-Type": "image/png", "X-Cache": "MISS"}
    headers["X-Bgmask-Color"] = "#{:02x}{:02x}{:02x}".format(*bg_color) if bg_color else "none"
    return Response(png_bytes, headers=headers)


# ── GET /api/jobs/<id>/stream (SSE) ──────────────────────────────────────────

@app.route("/api/jobs/<job_id>/stream")
def api_stream(job_id: str):
    if job_id not in _jobs:
        return jsonify({"error": "job introuvable"}), 404

    def generate():
        job  = _jobs[job_id]
        idx  = 0
        last_keepalive = time.time()

        while True:
            events = job["events"]
            if idx < len(events):
                event = events[idx]
                yield f"data: {json.dumps(event)}\n\n"
                idx += 1
                if event.get("type") == "done":
                    return
            else:
                if job["state"] == "done":
                    return
                time.sleep(0.1)
                now = time.time()
                if now - last_keepalive >= 5:
                    yield ": keepalive\n\n"
                    last_keepalive = now

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── POST /api/inputs (upload image source) ──────────────────────────────────

@app.route("/api/inputs", methods=["POST"])
def api_inputs_upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "missing_file", "message": "Champ 'file' absent."}), 400

    basename = _sanitize_basename(f.filename)
    ext = Path(basename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTS:
        return jsonify({
            "error": "bad_extension",
            "message": f"Extension {ext or '?'} non supportée (autorisé: png, webp, jpg, jpeg).",
        }), 415

    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = INPUTS_DIR / basename
    if dest.exists():
        return jsonify({
            "error": "exists",
            "message": f"{basename} existe déjà.",
            "suggestion": _suggest_unused_name(basename),
        }), 409

    f.save(str(dest))
    size = dest.stat().st_size
    return jsonify({"basename": basename, "size": size})


# ── DELETE /api/inputs/<basename> (archive image + outputs) ─────────────────

@app.route("/api/inputs/<path:basename>", methods=["DELETE"])
def api_inputs_delete(basename: str):
    if not _safe_name(basename):
        return jsonify({"error": "bad_name"}), 400
    src = INPUTS_DIR / basename
    if not src.exists():
        return jsonify({"error": "not_found"}), 404

    archived_src = _move_to_trash(src, INPUTS_TRASH)

    stem = Path(basename).stem
    out_dir = OUTPUTS_DIR / stem
    archived_out = None
    if out_dir.exists():
        archived_out = _move_to_trash(out_dir, OUTPUTS_TRASH)

    h = _load_history()
    if stem in h:
        del h[stem]
        _save_history(h)

    return jsonify({
        "archivedSource": str(archived_src.relative_to(ROOT)),
        "archivedOutputs": str(archived_out.relative_to(ROOT)) if archived_out else None,
    })


# ── GET / PUT /api/slicing/<basename> (config découpe spritesheet) ───────────

def _validate_slicing_config(base: dict, overrides: list) -> list[str]:
    errors: list[str] = []
    if base is None:
        return errors  # config vide acceptée (suppression)
    cols = base.get("cols")
    rows = base.get("rows")
    if not isinstance(cols, int) or cols < 1 or cols > 256:
        errors.append("cols must be int in [1,256]")
    if not isinstance(rows, int) or rows < 1 or rows > 256:
        errors.append("rows must be int in [1,256]")
    for fld in ("cellW", "cellH", "gapX", "gapY", "marginX", "marginY"):
        v = base.get(fld, 0)
        if not isinstance(v, int) or v < 0 or v > 1024:
            errors.append(f"{fld} must be int in [0,1024]")
    if not isinstance(overrides, list):
        errors.append("overrides must be a list")
        return errors
    occupied: dict[tuple, str] = {}
    for ov in overrides:
        if not isinstance(ov, dict):
            errors.append("override must be dict")
            continue
        cx, cy = ov.get("cellX"), ov.get("cellY")
        otype = ov.get("type")
        if not isinstance(cx, int) or not isinstance(cy, int):
            errors.append("override.cellX/cellY must be int")
            continue
        if cols and rows and (cx < 0 or cx >= cols or cy < 0 or cy >= rows):
            errors.append(f"override at ({cx},{cy}) is out of grid {cols}x{rows}")
            continue
        if otype not in ("resize", "merge", "ignore", "name", "pivot", "order"):
            errors.append(f"unknown override type {otype!r}")
            continue
        if otype == "merge":
            mw = ov.get("w", 1)
            mh = ov.get("h", 1)
            if not isinstance(mw, int) or not isinstance(mh, int) or mw < 1 or mh < 1:
                errors.append(f"merge at ({cx},{cy}) needs positive w,h")
                continue
            for dx in range(mw):
                for dy in range(mh):
                    key = (cx + dx, cy + dy)
                    if key in occupied and occupied[key] != "merge_owner":
                        errors.append(f"merge at ({cx},{cy}) overlaps with cell {key}")
                    occupied[key] = "merge_member"
            occupied[(cx, cy)] = "merge_owner"
    return errors


@app.route("/api/slicing/<path:basename>", methods=["GET"])
def api_slicing_get(basename: str):
    if not _safe_name(basename):
        return jsonify({"error": "bad_name"}), 400
    stem = Path(basename).stem
    h = _load_history()
    entry = h.get(stem) or {}
    sl = entry.get("slicing")
    if not sl:
        return jsonify({"base": None, "overrides": []})
    return jsonify(sl)


@app.route("/api/slicing/<path:basename>", methods=["PUT"])
def api_slicing_put(basename: str):
    if not _safe_name(basename):
        return jsonify({"error": "bad_name"}), 400
    payload = request.get_json(silent=True) or {}
    base = payload.get("base")
    overrides = payload.get("overrides", [])
    errors = _validate_slicing_config(base, overrides if isinstance(overrides, list) else [])
    if errors:
        return jsonify({"error": "invalid_config", "details": errors}), 400
    stem = Path(basename).stem
    h = _load_history()
    if stem not in h:
        # crée une entrée minimale si pas encore présente
        h[stem] = {"source": f"inputs/{basename}", "runs": []}
    if base is None:
        h[stem].pop("slicing", None)
    else:
        h[stem]["slicing"] = {"base": base, "overrides": overrides}
    _save_history(h)
    return jsonify(h[stem].get("slicing") or {"base": None, "overrides": []})


# ── POST /api/constraints/validate (valider contraintes pixel sur cellules) ─

def _is_pot(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def _next_pot(n: int) -> int:
    p = 1
    while p < n:
        p <<= 1
    return p


@app.route("/api/constraints/validate", methods=["POST"])
def api_constraints_validate():
    payload = request.get_json(silent=True) or {}
    image_name = payload.get("image")
    constraints = payload.get("constraints") or {}
    grid = payload.get("grid") or {}
    if not image_name or not _safe_name(image_name):
        return jsonify({"error": "bad_image"}), 400
    base = grid.get("base") if isinstance(grid, dict) else None
    if not base:
        return jsonify({"violations": [], "warning": "no_grid"})
    overrides = grid.get("overrides", []) if isinstance(grid, dict) else []
    cols, rows = base.get("cols", 0), base.get("rows", 0)
    cellW, cellH = base.get("cellW", 0), base.get("cellH", 0)
    mul_n = constraints.get("mulN")
    use_pot = constraints.get("pot")
    violations: list[dict] = []
    ignore_set = {(o.get("cellX"), o.get("cellY")) for o in overrides if o.get("type") == "ignore"}

    def cell_dims(cx: int, cy: int) -> tuple[int, int]:
        w, h = cellW, cellH
        for o in overrides:
            if o.get("cellX") == cx and o.get("cellY") == cy:
                if o.get("type") == "resize":
                    w = o.get("w", w); h = o.get("h", h)
                elif o.get("type") == "merge":
                    w = cellW * (o.get("w", 1)); h = cellH * (o.get("h", 1))
        return w, h

    for cy in range(rows):
        for cx in range(cols):
            if (cx, cy) in ignore_set:
                continue
            w, h = cell_dims(cx, cy)
            if mul_n and isinstance(mul_n, int) and mul_n > 0:
                if w % mul_n != 0 or h % mul_n != 0:
                    sugg_w = ((w + mul_n - 1) // mul_n) * mul_n
                    sugg_h = ((h + mul_n - 1) // mul_n) * mul_n
                    violations.append({
                        "cellX": cx, "cellY": cy,
                        "issue": f"{w}x{h} non multiple de {mul_n}",
                        "suggestion": f"padder à {sugg_w}x{sugg_h} ou rogner à {w - w % mul_n}x{h - h % mul_n}",
                        "type": "mulN",
                    })
            if use_pot:
                if not _is_pot(w) or not _is_pot(h):
                    violations.append({
                        "cellX": cx, "cellY": cy,
                        "issue": f"{w}x{h} non POT",
                        "suggestion": f"padder à {_next_pot(w)}x{_next_pot(h)}",
                        "type": "pot",
                    })
    return jsonify({"violations": violations})


# ── POST /api/export (export spritesheet : PNG atlas + JSON/XML/CSS ou sprites individuels) ─

def _build_frames(grid: dict, template: str, options: dict) -> list[dict]:
    base = grid.get("base") or {}
    overrides = grid.get("overrides", [])
    cols, rows = base.get("cols", 0), base.get("rows", 0)
    cellW, cellH = base.get("cellW", 0), base.get("cellH", 0)
    gapX, gapY = base.get("gapX", 0), base.get("gapY", 0)
    marginX, marginY = base.get("marginX", 0), base.get("marginY", 0)

    ov_by_cell = {}
    for o in overrides:
        ov_by_cell.setdefault((o.get("cellX"), o.get("cellY")), []).append(o)

    def find(cx, cy, type_):
        return next((o for o in ov_by_cell.get((cx, cy), []) if o.get("type") == type_), None)

    def is_member(cx, cy):
        for o in overrides:
            if o.get("type") != "merge":
                continue
            ox, oy = o.get("cellX"), o.get("cellY")
            mw, mh = o.get("w", 1), o.get("h", 1)
            dx, dy = cx - ox, cy - oy
            if 0 <= dx < mw and 0 <= dy < mh and (dx > 0 or dy > 0):
                return True
        return False

    frames: list[dict] = []
    used_names: set[str] = set()
    idx = 0
    order_map = {(o["cellX"], o["cellY"]): o.get("value", 0) for o in overrides if o.get("type") == "order"}
    cells = []
    for cy in range(rows):
        for cx in range(cols):
            if find(cx, cy, "ignore") or is_member(cx, cy):
                continue
            cells.append((cx, cy))
    if order_map:
        cells.sort(key=lambda p: (order_map.get(p, 1e9), p[1], p[0]))

    for cx, cy in cells:
        merge = find(cx, cy, "merge")
        resize = find(cx, cy, "resize")
        w = cellW * (merge["w"] if merge else 1) + gapX * ((merge["w"] if merge else 1) - 1)
        h = cellH * (merge["h"] if merge else 1) + gapY * ((merge["h"] if merge else 1) - 1)
        if resize:
            w, h = resize.get("w", w), resize.get("h", h)
        x = marginX + cx * (cellW + gapX)
        y = marginY + cy * (cellH + gapY)
        nameOv = find(cx, cy, "name")
        custom_name = nameOv.get("name") if nameOv else f"{cx}_{cy}"
        name = template.format(basename=options.get("basename", "img"), col=cx, row=cy, index=idx, name=custom_name)
        # collision
        base_name = name
        suffix = 1
        while name in used_names:
            suffix += 1
            name = f"{base_name}_{suffix}"
        used_names.add(name)
        frame = {"name": name, "x": x, "y": y, "w": w, "h": h, "index": idx, "cellX": cx, "cellY": cy}
        pivot = find(cx, cy, "pivot")
        if pivot and options.get("pivot"):
            frame["pivot"] = {"x": pivot.get("x", 0.5), "y": pivot.get("y", 0.5)}
        frames.append(frame)
        idx += 1
    return frames


def _emit_json_phaser(frames: list[dict], image_name: str, atlas_size: tuple) -> str:
    out = {
        "frames": {f["name"]: {
            "frame": {"x": f["x"], "y": f["y"], "w": f["w"], "h": f["h"]},
            "rotated": False,
            "trimmed": False,
            "spriteSourceSize": {"x": 0, "y": 0, "w": f["w"], "h": f["h"]},
            "sourceSize": {"w": f["w"], "h": f["h"]},
            **({"pivot": f["pivot"]} if "pivot" in f else {}),
        } for f in frames},
        "meta": {
            "image": image_name,
            "size": {"w": atlas_size[0], "h": atlas_size[1]},
            "scale": "1",
        },
    }
    return json.dumps(out, indent=2, ensure_ascii=False)


def _emit_xml_starling(frames: list[dict], image_name: str) -> str:
    parts = ['<?xml version="1.0" encoding="UTF-8"?>', f'<TextureAtlas imagePath="{xml_escape(image_name)}">']
    for f in frames:
        parts.append(f'  <SubTexture name="{xml_escape(f["name"])}" x="{f["x"]}" y="{f["y"]}" width="{f["w"]}" height="{f["h"]}"/>')
    parts.append('</TextureAtlas>')
    return "\n".join(parts)


def _emit_css_sprites(frames: list[dict], image_name: str) -> str:
    parts = [f'.sprite {{ background: url("{image_name}") no-repeat; display: inline-block; }}']
    for f in frames:
        parts.append(f'.sprite-{f["name"]} {{ background-position: -{f["x"]}px -{f["y"]}px; width: {f["w"]}px; height: {f["h"]}px; }}')
    return "\n".join(parts)


@app.route("/api/export", methods=["POST"])
def api_export():
    payload = request.get_json(silent=True) or {}
    image_name = payload.get("image")
    fmt = payload.get("format", "json_phaser")
    template = payload.get("template", "{basename}_{col}_{row}")
    options = payload.get("options") or {}
    if not image_name or not _safe_name(image_name):
        return jsonify({"error": "bad_image"}), 400
    src_path = INPUTS_DIR / image_name
    if not src_path.exists():
        return jsonify({"error": "image_not_found"}), 404
    h = _load_history()
    stem = Path(image_name).stem
    grid = (h.get(stem) or {}).get("slicing")
    if not grid or not grid.get("base"):
        return jsonify({"error": "no_slicing"}), 400
    options["basename"] = stem
    frames = _build_frames(grid, template, options)
    if not frames:
        return jsonify({"error": "no_frames"}), 400

    img = Image.open(src_path).convert("RGBA")
    atlas_size = img.size

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if fmt == "individual":
            for f in frames:
                crop = img.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))
                pb = io.BytesIO()
                crop.save(pb, format="PNG")
                zf.writestr(f["name"] + ".png", pb.getvalue())
        else:
            atlas_buf = io.BytesIO()
            img.save(atlas_buf, format="PNG")
            zf.writestr("atlas.png", atlas_buf.getvalue())
            if fmt == "png_atlas":
                pass  # juste l'atlas
            elif fmt == "json_phaser":
                zf.writestr("atlas.json", _emit_json_phaser(frames, "atlas.png", atlas_size))
            elif fmt == "xml_starling":
                zf.writestr("atlas.xml", _emit_xml_starling(frames, "atlas.png"))
            elif fmt == "css_sprites":
                zf.writestr("atlas.css", _emit_css_sprites(frames, "atlas.png"))
            else:
                return jsonify({"error": "unknown_format"}), 400

    # sauvegarde côté serveur
    export_dir = OUTPUTS_DIR / stem / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    saved = export_dir / f"export_{fmt}_{ts}.zip"
    saved.write_bytes(buf.getvalue())

    return Response(
        buf.getvalue(),
        mimetype="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{stem}_{fmt}.zip"',
            "X-Frames-Count": str(len(frames)),
        },
    )


# ── Spritesheet cleanup : helpers communs ────────────────────────────────────

def _iter_cells(image_name: str):
    """Yield (frame_dict, crop_Image) pour chaque cellule non-ignorée.
    Utilise _build_frames pour cohérence avec export."""
    h = _load_history()
    stem = Path(image_name).stem
    grid = (h.get(stem) or {}).get("slicing")
    if not grid or not grid.get("base"):
        return None, None, None
    src = INPUTS_DIR / image_name
    if not src.exists():
        return None, None, None
    img = Image.open(src).convert("RGBA")
    frames = _build_frames(grid, "{col}_{row}", {"basename": stem})
    return img, frames, grid


def _phash(img: "Image.Image", size: int = 8) -> int:
    """Perceptual hash 8x8 DCT-less (moyenne-based, sans scipy)."""
    import numpy as np
    small = img.convert("L").resize((size, size), Image.Resampling.LANCZOS)
    arr = np.asarray(small, dtype=np.float32)
    mean = arr.mean()
    bits = (arr > mean).astype(np.uint8).flatten()
    h = 0
    for b in bits:
        h = (h << 1) | int(b)
    return h


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def _phase_correlate(a: "Image.Image", b: "Image.Image") -> tuple[float, float]:
    """Phase correlation FFT — retourne (dx, dy) en pixels (sub-pixel par parabole)."""
    import numpy as np
    A = np.asarray(a.convert("L"), dtype=np.float32)
    B = np.asarray(b.convert("L"), dtype=np.float32)
    if A.shape != B.shape:
        # resize B to A
        b2 = b.convert("L").resize(a.size, Image.Resampling.NEAREST)
        B = np.asarray(b2, dtype=np.float32)
    Fa = np.fft.fft2(A)
    Fb = np.fft.fft2(B)
    R = Fa * np.conj(Fb)
    R /= np.abs(R) + 1e-10
    r = np.fft.ifft2(R).real
    peak = np.unravel_index(np.argmax(r), r.shape)
    dy, dx = peak
    h, w = r.shape
    if dy > h // 2: dy -= h
    if dx > w // 2: dx -= w
    # raffinement parabolique autour du peak (sub-pixel)
    def parab(y0, y1, y2):
        denom = (y0 - 2 * y1 + y2)
        return 0.5 * (y0 - y2) / denom if abs(denom) > 1e-9 else 0.0
    py, px = peak
    sx = sy = 0.0
    if 1 <= py < h - 1:
        sy = parab(r[py - 1, px], r[py, px], r[py + 1, px])
    if 1 <= px < w - 1:
        sx = parab(r[py, px - 1], r[py, px], r[py, px + 1])
    return (float(dx) + sx, float(dy) + sy)


# ── POST /api/cleanup/detect-duplicates ──────────────────────────────────────

@app.route("/api/cleanup/detect-duplicates", methods=["POST"])
def api_cleanup_duplicates():
    payload = request.get_json(silent=True) or {}
    image_name = payload.get("image")
    threshold = int(payload.get("similarity_threshold", 5))
    if not image_name or not _safe_name(image_name):
        return jsonify({"error": "bad_image"}), 400
    img, frames, _ = _iter_cells(image_name)
    if img is None:
        return jsonify({"error": "no_slicing"}), 400
    hashes = []
    for f in frames:
        crop = img.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))
        hashes.append((f, _phash(crop)))
    pairs = []
    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            d = _hamming(hashes[i][1], hashes[j][1])
            if d <= threshold:
                pairs.append({
                    "a": {"cellX": hashes[i][0]["cellX"], "cellY": hashes[i][0]["cellY"], "name": hashes[i][0]["name"]},
                    "b": {"cellX": hashes[j][0]["cellX"], "cellY": hashes[j][0]["cellY"], "name": hashes[j][0]["name"]},
                    "hamming": d,
                })
    return jsonify({"pairs": pairs, "threshold": threshold})


# ── POST /api/cleanup/detect-subpixel ────────────────────────────────────────

@app.route("/api/cleanup/detect-subpixel", methods=["POST"])
def api_cleanup_subpixel():
    payload = request.get_json(silent=True) or {}
    image_name = payload.get("image")
    if not image_name or not _safe_name(image_name):
        return jsonify({"error": "bad_image"}), 400
    img, frames, _ = _iter_cells(image_name)
    if img is None:
        return jsonify({"error": "no_slicing"}), 400
    shifts = []
    for i in range(1, len(frames)):
        a = img.crop((frames[i-1]["x"], frames[i-1]["y"], frames[i-1]["x"] + frames[i-1]["w"], frames[i-1]["y"] + frames[i-1]["h"]))
        b = img.crop((frames[i]["x"], frames[i]["y"], frames[i]["x"] + frames[i]["w"], frames[i]["y"] + frames[i]["h"]))
        try:
            dx, dy = _phase_correlate(a, b)
        except Exception:
            continue
        mag = (dx * dx + dy * dy) ** 0.5
        if 0.2 < mag < 2.5:
            shifts.append({
                "cell": {"cellX": frames[i]["cellX"], "cellY": frames[i]["cellY"], "name": frames[i]["name"]},
                "delta": {"x": round(dx, 3), "y": round(dy, 3)},
                "magnitude": round(mag, 3),
            })
    return jsonify({"shifts": shifts})


# ── POST /api/cleanup/normalize ──────────────────────────────────────────────

@app.route("/api/cleanup/normalize", methods=["POST"])
def api_cleanup_normalize():
    payload = request.get_json(silent=True) or {}
    image_name = payload.get("image")
    alignment = payload.get("alignment", "center")  # center | topleft | bottomleft
    if not image_name or not _safe_name(image_name):
        return jsonify({"error": "bad_image"}), 400
    img, frames, grid = _iter_cells(image_name)
    if img is None:
        return jsonify({"error": "no_slicing"}), 400
    maxW = max(f["w"] for f in frames)
    maxH = max(f["h"] for f in frames)
    # layout row-major, même cols/rows que la grille de base
    base = grid["base"]
    cols, rows = base["cols"], base["rows"]
    out_w = cols * maxW
    out_h = rows * maxH
    out = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 0))
    frame_map = {(f["cellX"], f["cellY"]): f for f in frames}
    for cy in range(rows):
        for cx in range(cols):
            f = frame_map.get((cx, cy))
            if not f:
                continue
            crop = img.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))
            dx = {"center": (maxW - f["w"]) // 2, "topleft": 0, "bottomleft": 0}.get(alignment, 0)
            dy = {"center": (maxH - f["h"]) // 2, "topleft": 0, "bottomleft": maxH - f["h"]}.get(alignment, 0)
            out.paste(crop, (cx * maxW + dx, cy * maxH + dy), crop)
    stem = Path(image_name).stem
    outputs_stem = OUTPUTS_DIR / stem
    outputs_stem.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    existing = [p for p in outputs_stem.iterdir() if p.name.startswith("iter_")]
    idx = len(existing) + 1
    fname = f"iter_{idx:03d}_normalize.png"
    out.save(outputs_stem / fname, format="PNG")
    # history entry
    h = _load_history()
    h.setdefault(stem, {"source": f"inputs/{image_name}", "runs": []})
    h[stem]["runs"].append({
        "algo": "cleanup",
        "method": "normalize",
        "params": {"alignment": alignment, "target": [maxW, maxH]},
        "output": f"outputs/{stem}/{fname}",
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
    })
    _save_history(h)
    return jsonify({
        "iter": f"outputs/{stem}/{fname}",
        "dimensions": [out_w, out_h],
        "cellSize": [maxW, maxH],
    })


# ── GET /api/cleanup/report ──────────────────────────────────────────────────

@app.route("/api/cleanup/report", methods=["GET"])
def api_cleanup_report():
    image_name = request.args.get("image", "")
    if not image_name or not _safe_name(image_name):
        return jsonify({"error": "bad_image"}), 400
    img, frames, grid = _iter_cells(image_name)
    if img is None:
        return jsonify({"error": "no_slicing"}), 400
    # calcule rapidement : duplicates (phash), subpixel, sizes, empty
    import numpy as np
    hashes = [(f, _phash(img.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"])))) for f in frames]
    duplicates = []
    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            d = _hamming(hashes[i][1], hashes[j][1])
            if d <= 5:
                duplicates.append({"pair": [(hashes[i][0]["cellX"], hashes[i][0]["cellY"]),
                                             (hashes[j][0]["cellX"], hashes[j][0]["cellY"])], "hamming": d})
    sizes = sorted({(f["w"], f["h"]) for f in frames})
    # dominant size
    from collections import Counter
    c = Counter((f["w"], f["h"]) for f in frames)
    dominant = c.most_common(1)[0][0] if c else None
    # empty cells : alpha entière < 1% non-transparents
    empty = []
    for f in frames:
        crop = img.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))
        arr = np.asarray(crop)
        if arr.shape[-1] == 4:
            nonzero = (arr[..., 3] > 0).sum()
            if nonzero < (f["w"] * f["h"] * 0.01):
                empty.append((f["cellX"], f["cellY"]))
    report = {
        "duplicates": duplicates,
        "size_variants": {"unique_sizes": [list(s) for s in sizes], "dominant": list(dominant) if dominant else None},
        "empty_cells": [list(e) for e in empty],
        "frame_count": len(frames),
    }
    return Response(
        json.dumps(report, indent=2, ensure_ascii=False),
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="{Path(image_name).stem}_report.json"'},
    )


# ── POST /api/autotile/generate (Wang 16/47/256) ─────────────────────────────

def _decode_tile_data_url(data_url: str) -> "Image.Image":
    """Décode une image depuis une data URL base64."""
    if not data_url or not data_url.startswith("data:"):
        raise ValueError("invalid_data_url")
    _, b64 = data_url.split(",", 1)
    raw = base64.b64decode(b64)
    return Image.open(io.BytesIO(raw)).convert("RGBA")


def _quadrant(tile: "Image.Image", quad: str) -> "Image.Image":
    """Extrait le quadrant TL/TR/BL/BR d'une tile."""
    w, h = tile.size
    hw, hh = w // 2, h // 2
    if quad == "TL": return tile.crop((0, 0, hw, hh))
    if quad == "TR": return tile.crop((hw, 0, w, hh))
    if quad == "BL": return tile.crop((0, hh, hw, h))
    if quad == "BR": return tile.crop((hw, hh, w, h))
    return tile


def _compose_wang16(bits: int, base_tile: "Image.Image", edge_tile: "Image.Image", tile_size: int) -> "Image.Image":
    """Wang 16 : 4 bits (TL, TR, BL, BR). 1 = continuation base, 0 = bord."""
    out = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))
    hs = tile_size // 2
    corners = [("TL", 0, 0, 3), ("TR", hs, 0, 2), ("BL", 0, hs, 1), ("BR", hs, hs, 0)]
    for quad, x, y, bit_idx in corners:
        use_base = (bits >> bit_idx) & 1
        src = base_tile if use_base else edge_tile
        q = _quadrant(src, quad)
        if q.size != (hs, hs):
            q = q.resize((hs, hs), Image.Resampling.NEAREST)
        out.paste(q, (x, y), q)
    return out


def _compose_wang256(bits: int, tiles: dict, tile_size: int) -> "Image.Image":
    """Wang 256 : 8 bits (N, NE, E, SE, S, SW, W, NW). Approximation via Wang16 en ignorant les diagonales."""
    # Pour v1 : on réduit à Wang 16 via les 4 cardinaux → 4 bits
    # N bit 7, E bit 5, S bit 3, W bit 1 (intercalés diagonales bits 6,4,2,0)
    wang16_bits = 0
    for wang_idx, big_idx in [(3, 7), (2, 5), (1, 3), (0, 1)]:  # TL~N, TR~E, BL~S, BR~W approximation grossière
        if (bits >> big_idx) & 1:
            wang16_bits |= (1 << wang_idx)
    return _compose_wang16(wang16_bits, tiles["base"], tiles["edge"], tile_size)


@app.route("/api/autotile/generate", methods=["POST"])
def api_autotile_generate():
    payload = request.get_json(silent=True) or {}
    mode = payload.get("mode", "wang16")
    tile_size = int(payload.get("tile_size", 16))
    tiles_payload = payload.get("tiles") or {}
    image_name = payload.get("image")  # pour associer l'iter à une image source (optionnel)
    if tile_size not in (8, 16, 32, 64, 128):
        return jsonify({"error": "bad_tile_size"}), 400
    required = {"wang16": ["base", "edge"], "wang47": ["base", "edge", "corner_in", "corner_out"], "wang256": ["base", "edge"]}.get(mode)
    if not required:
        return jsonify({"error": "unknown_mode"}), 400
    tiles: dict = {}
    for key in required:
        url = tiles_payload.get(key)
        if not url:
            return jsonify({"error": f"missing_tile_{key}"}), 400
        try:
            t = _decode_tile_data_url(url)
            if t.size != (tile_size, tile_size):
                t = t.resize((tile_size, tile_size), Image.Resampling.NEAREST)
            tiles[key] = t
        except Exception as e:
            return jsonify({"error": f"bad_tile_{key}", "detail": str(e)}), 400

    # Génération
    if mode == "wang16":
        cols, rows = 4, 4
        variants = [_compose_wang16(b, tiles["base"], tiles["edge"], tile_size) for b in range(16)]
    elif mode == "wang47":
        # Sous-set 47-blob : les 47 valeurs canoniques sur 8 bits. Approximation via wang16 en v1.
        cols, rows = 7, 7
        variants = []
        # Liste standard des 47 indices blob de Godot (ordre row-major dans la tilemap)
        blob47 = [0, 1, 4, 5, 16, 17, 20, 21, 64, 65, 68, 69, 80, 81, 84, 85,
                  68, 69, 84, 85, 80, 81, 84, 85, 4, 5, 20, 21, 80, 81, 84, 85,
                  16, 17, 20, 21, 64, 65, 68, 69, 64, 65, 68, 69, 4, 5, 20]
        for b in blob47:
            # extraction des 4 cardinaux du mask 8-bit
            c = 0
            if (b >> 6) & 1: c |= (1 << 3)
            if (b >> 4) & 1: c |= (1 << 2)
            if (b >> 2) & 1: c |= (1 << 1)
            if b & 1:        c |= 1
            variants.append(_compose_wang16(c, tiles["base"], tiles["edge"], tile_size))
        # pad avec 2 cellules vides pour combler 7×7=49
        while len(variants) < cols * rows:
            variants.append(Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0)))
    else:  # wang256
        cols, rows = 16, 16
        variants = [_compose_wang256(b, tiles, tile_size) for b in range(256)]

    atlas = Image.new("RGBA", (cols * tile_size, rows * tile_size), (0, 0, 0, 0))
    for i, v in enumerate(variants):
        x = (i % cols) * tile_size
        y = (i // cols) * tile_size
        atlas.paste(v, (x, y), v)

    # Sauvegarder comme iter si image_name fourni, sinon dans un dossier générique
    if image_name and _safe_name(image_name):
        stem = Path(image_name).stem
    else:
        stem = f"autotile_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir = OUTPUTS_DIR / stem
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = [p for p in out_dir.iterdir() if p.name.startswith("iter_")] if out_dir.exists() else []
    idx = len(existing) + 1
    fname = f"iter_{idx:03d}_autotile_{mode}.png"
    atlas.save(out_dir / fname, format="PNG")
    h = _load_history()
    h.setdefault(stem, {"source": f"inputs/{image_name}" if image_name else f"outputs/{stem}/{fname}", "runs": []})
    h[stem]["runs"].append({
        "algo": "autotile",
        "method": mode,
        "params": {"tile_size": tile_size},
        "output": f"outputs/{stem}/{fname}",
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
    })
    _save_history(h)
    return jsonify({
        "iter": f"outputs/{stem}/{fname}",
        "gridLayout": {"cols": cols, "rows": rows, "tile_size": tile_size, "mode": mode},
    })


# ── POST /api/history/prune (retirer entrées orphelines) ─────────────────────

@app.route("/api/history/prune", methods=["POST"])
def api_history_prune():
    payload = request.get_json(silent=True) or {}
    basenames = payload.get("basenames") or []
    if not isinstance(basenames, list):
        return jsonify({"error": "basenames_must_be_list"}), 400

    existing_sources = set()
    if INPUTS_DIR.exists():
        for f in INPUTS_DIR.iterdir():
            if f.is_file():
                existing_sources.add(f.stem)

    h = _load_history()
    pruned: list[str] = []
    skipped: list[dict] = []

    for name in basenames:
        if not isinstance(name, str) or not _safe_name(name):
            skipped.append({"name": str(name), "reason": "bad_name"})
            continue
        stem = Path(name).stem if "." in name else name
        if stem in existing_sources:
            skipped.append({"name": name, "reason": "source file still present"})
            continue
        if stem not in h:
            skipped.append({"name": name, "reason": "not_in_history"})
            continue
        out_dir = OUTPUTS_DIR / stem
        if out_dir.exists():
            _move_to_trash(out_dir, OUTPUTS_TRASH)
        del h[stem]
        pruned.append(stem)

    if pruned:
        _save_history(h)
    return jsonify({"pruned": pruned, "skipped": skipped})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5500, debug=False, threaded=True)
