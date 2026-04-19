import json
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, Response, jsonify, redirect, request, send_from_directory

ROOT = Path(__file__).parent.parent        # pixel-lab/
SCRIPTS_DIR = ROOT / "scripts"
INPUTS_DIR  = ROOT / "inputs"
OUTPUTS_DIR = ROOT / "outputs"
HISTORY_FILE = ROOT / "history.json"

sys.path.insert(0, str(SCRIPTS_DIR))
from algorithms import denoise, pixelsnap, scale2x, sharpen

ALGO_MODULES = {
    "sharpen":   sharpen,
    "scale2x":   scale2x,
    "denoise":   denoise,
    "pixelsnap": pixelsnap,
}

app = Flask(__name__)

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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5500, debug=False, threaded=True)
