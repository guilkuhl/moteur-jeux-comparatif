"""Regénère les fixtures PNG déterministes. Exécuter uniquement après revue visuelle."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).parent
INPUTS = HERE / "inputs"


def _build_sprite_small() -> Image.Image:
    """32×32 RGBA avec pattern déterministe (seed 42, 4 couleurs)."""
    rng = np.random.default_rng(42)
    palette = np.array(
        [
            [0, 0, 0, 255],
            [200, 50, 50, 255],
            [50, 200, 50, 255],
            [50, 100, 255, 255],
        ],
        dtype=np.uint8,
    )
    idx = rng.integers(0, 4, size=(32, 32))
    arr = palette[idx]
    return Image.fromarray(arr, mode="RGBA")


def main() -> None:
    INPUTS.mkdir(parents=True, exist_ok=True)
    _build_sprite_small().save(INPUTS / "test_small.png")
    print(f"wrote {INPUTS / 'test_small.png'}")


if __name__ == "__main__":
    main()
