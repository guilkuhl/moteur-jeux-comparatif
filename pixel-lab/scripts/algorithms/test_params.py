"""
Vérifie que les defaults déclarés dans PARAMS correspondent aux defaults Python
de chaque fonction exposée dans METHODS.
"""

import inspect
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from algorithms import sharpen, scale2x, denoise, pixelsnap

# Mapping explicite METHODS key → fonction réelle (nécessaire quand les noms diffèrent)
ALGO_FUNC_MAP = {
    "sharpen": {
        "unsharp_mask": sharpen.unsharp_mask,
        "laplacian":    sharpen.laplacian_sharpen,
        "kernel":       sharpen.kernel_sharpen,
    },
    "scale2x": {
        "nearest": scale2x.nearest,
        # scale2x et eagle2x : pas de params → skip
    },
    "denoise": {
        "median":    denoise.median_filter,
        "bilateral": denoise.bilateral_filter,
        "nlm":       denoise.nlm_denoise,
    },
    "pixelsnap": {
        # METHODS sont des lambdas ; on vérifie snap() pour le param block
        "_snap_block": (pixelsnap.snap, "block"),
    },
}

MODULES = {
    "sharpen":   sharpen,
    "scale2x":   scale2x,
    "denoise":   denoise,
    "pixelsnap": pixelsnap,
}


def test_params_match_signatures():
    errors = []

    for algo_name, module in MODULES.items():
        params = module.PARAMS
        func_map = ALGO_FUNC_MAP.get(algo_name, {})

        for method_key, param_list in params.items():
            if not param_list:
                continue

            fn = func_map.get(method_key)
            if fn is None:
                continue

            # Cas spécial pixelsnap : tuple (fn, param_name)
            if isinstance(fn, tuple):
                fn, single_param = fn
                sig = inspect.signature(fn)
                sig_params = sig.parameters
                entry = next((p for p in param_list if p["name"] == single_param), None)
                if entry is None:
                    continue
                if single_param not in sig_params:
                    errors.append(f"pixelsnap.snap: param '{single_param}' manquant dans la signature")
                    continue
                py_default = sig_params[single_param].default
                declared = entry["default"]
                if py_default != declared:
                    errors.append(
                        f"pixelsnap.snap[{single_param}]: default Python={py_default} vs PARAMS={declared}"
                    )
                continue

            sig = inspect.signature(fn)
            sig_params = sig.parameters

            for entry in param_list:
                pname = entry["name"]
                declared = entry["default"]
                if pname not in sig_params:
                    errors.append(f"{algo_name}.{method_key}: param '{pname}' absent de la signature Python")
                    continue
                py_default = sig_params[pname].default
                if py_default == inspect.Parameter.empty:
                    errors.append(f"{algo_name}.{method_key}.{pname}: pas de default Python")
                    continue
                if py_default != declared:
                    errors.append(
                        f"{algo_name}.{method_key}.{pname}: default Python={py_default} vs PARAMS={declared}"
                    )

    if errors:
        for e in errors:
            print("FAIL:", e)
        sys.exit(1)
    else:
        print("OK — tous les defaults PARAMS correspondent aux signatures Python")


if __name__ == "__main__":
    test_params_match_signatures()
