"""Exécution synchrone d'un job multi-images × multi-étapes (appelée dans un thread)."""
from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

from apply_step import run_step  # type: ignore[import-not-found]
from PIL import Image

from ..deps import INPUTS_DIR, OUTPUTS_DIR, resolve_input
from . import history_store
from .job_store import job_store


def run_job(job_id: str, payload: dict[str, Any]) -> None:
    """Orchestrateur : boucle sur images × pipeline, écrit iter_NNN_*.png et history.json."""
    images: list[str] = payload["images"]
    pipeline: list[dict[str, Any]] = payload["pipeline"]
    use_gpu: bool = bool(payload.get("use_gpu", False))

    try:
        for img_name in images:
            resolved = resolve_input(img_name)
            last_input: Path = resolved if resolved else (INPUTS_DIR / img_name)
            img_stem = Path(img_name).stem
            out_dir = OUTPUTS_DIR / img_stem

            # Copie source.png au premier run (parité CLI)
            source_copy = out_dir / "source.png"
            if not source_copy.exists() and last_input.exists():
                out_dir.mkdir(parents=True, exist_ok=True)
                # non bloquant : un source.png manquant n'empêche pas le pipeline
                with contextlib.suppress(Exception):
                    Image.open(last_input).save(source_copy)

            img_entries: list[dict[str, Any]] = []

            for step_idx, step in enumerate(pipeline):
                algo = step["algo"]
                method = step["method"]
                params = step.get("params", {}) or {}

                if algo == "scale2x" and step_idx < len(pipeline) - 1:
                    job_store.push(job_id, {
                        "type": "warning",
                        "message": (
                            f"scale2x à l'étape {step_idx + 1}/{len(pipeline)} — "
                            "l'upscale en milieu de pipeline peut produire des artefacts "
                            "sur les étapes suivantes."
                        ),
                    })

                job_store.push(job_id, {
                    "type": "step_start",
                    "image": img_name,
                    "step": step_idx,
                    "algo": algo,
                    "method": method,
                })

                try:
                    produced_path, entry = run_step(
                        last_input, algo, method, params, out_dir,
                        name_override=img_stem if step_idx > 0 else None,
                        use_gpu=use_gpu,
                    )
                except Exception as e:  # noqa: BLE001
                    job_store.push(job_id, {
                        "type": "step_error",
                        "image": img_name,
                        "step": step_idx,
                        "stderr": str(e)[:500],
                    })
                    continue

                entry_full = dict(entry)
                entry_full["output"] = f"outputs/{img_stem}/{entry['output']}"
                try:
                    from ..deps import ROOT
                    entry_full["source"] = str(last_input.relative_to(ROOT))
                except ValueError:
                    entry_full["source"] = str(last_input)
                img_entries.append(entry_full)

                last_input = produced_path

                job_store.push(job_id, {
                    "type": "step_done",
                    "image": img_name,
                    "step": step_idx,
                    "output": produced_path.name,
                })

            if img_entries:
                def _mut(h: dict, stem: str = img_stem, entries: list = img_entries) -> None:
                    if stem not in h:
                        h[stem] = {"source": f"outputs/{stem}/source.png", "runs": []}
                    h[stem]["runs"].extend(entries)

                history_store.update(_mut)

            job_store.push(job_id, {"type": "image_done", "image": img_name})

    finally:
        job_store.push(job_id, {"type": "done"})
        job_store.finish(job_id)
