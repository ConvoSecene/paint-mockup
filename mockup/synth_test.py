#!/usr/bin/env python3
"""
Synthetic end-to-end test for mockup.py (no real photos needed).

Builds a scene with known shading S, wall reflectance R_wall and a target paint
R_paint, simulates swatch + neutral samples under random per-frame exposure/WB
drift, writes a v5 export + reference photo, runs the pipeline, and checks the
result against the analytic ground truth M = S * R_paint inside the wall mask.
"""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

from scipy.ndimage import binary_erosion

from mockup import srgb_to_linear, linear_to_srgb, build_region_mask

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "_testdata")
OUT = os.path.join(DATA, "out")
W, H = 640, 480
RNG = np.random.default_rng(0)


def to_u8(lin):
    return int(round(linear_to_srgb(lin) * 255.0)) if np.isscalar(lin) else \
        np.round(linear_to_srgb(lin) * 255.0).astype(np.uint8)


def main():
    os.makedirs(DATA, exist_ok=True)

    # --- shading: smooth left->right + vertical falloff, grey, in [~0.35, 1.0] ---
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    S = (0.55 + 0.45 * xx / W) * (1.0 - 0.25 * yy / H)
    S = S[..., None]  # (H, W, 1)

    R_wall = np.array([0.55, 0.50, 0.45])     # existing warm beige
    R_paint = np.array([0.15, 0.25, 0.55])    # target blue
    R_furn = np.array([0.20, 0.30, 0.40])     # an occluder (sofa)

    # furniture rectangle (an occluder in front of the wall) -> a mask hole
    fx0, fy0, fx1, fy1 = 380, 300, 560, 440
    furn = np.zeros((H, W), bool)
    furn[fy0:fy1, fx0:fx1] = True

    # reference photo: wall everywhere except furniture
    ref_lin = S * R_wall
    ref_lin[furn] = (S * R_furn)[furn]
    Image.fromarray(to_u8(ref_lin), "RGB").save(os.path.join(DATA, "reference.png"))

    # ground truth: wall repainted, furniture untouched
    gt_lin = S * R_paint
    gt_lin[furn] = ref_lin[furn]

    # wall mask polygon (whole frame) with the furniture as a hole
    wall_poly = [[5, 5], [W - 5, 5], [W - 5, H - 5], [5, H - 5]]
    furn_hole = [[fx0, fy0], [fx1, fy0], [fx1, fy1], [fx0, fy1]]

    # neutral reference (grey card) at a fixed pixel
    nx, ny = 60, 60
    neutral_true = S[ny, nx, 0] * np.array([0.80, 0.80, 0.80])

    # swatch points on a grid across the wall, each its own frame w/ exposure+WB drift
    images = [{"filename": "reference.png", "width": W, "height": H, "points": []}]
    neutral_samples = {"reference.png": {"rgb": to_u8(neutral_true).tolist(), "std": [0, 0, 0], "patchPixels": 1}}

    grid = [(x, y) for x in range(80, W - 80, 110) for y in range(70, H - 90, 90)]
    for i, (x, y) in enumerate(grid):
        if furn[y, x]:
            continue
        fname = f"swatch_{i:02d}.png"
        e = RNG.uniform(0.88, 1.12) * (1 + RNG.uniform(-0.04, 0.04, 3))  # exposure + WB jitter
        swatch_obs = np.clip(S[y, x, 0] * R_paint * e, 0, 1)
        images.append({
            "filename": fname, "width": W, "height": H,
            "points": [{"kind": "swatch", "region": "", "label": "TestBlue",
                        "x": x, "y": y, "rgb": to_u8(swatch_obs).tolist(),
                        "std": [1, 1, 1], "patchPixels": 169}],
        })
        neutral_samples[fname] = {"rgb": to_u8(np.clip(neutral_true * e, 0, 1)).tolist(),
                                  "std": [0, 0, 0], "patchPixels": 1}

    export = {
        "tool": "swatch-marker", "version": 5,
        "sample": {"patchRadius": 6, "statistic": "median", "spread": "stddev",
                   "colorSpace": "srgb-8bit-gamma", "coordinates": "natural-image-pixels"},
        "globalPoints": [{"kind": "neutral", "region": "", "label": "grey card",
                          "x": nx, "y": ny, "samples": neutral_samples}],
        "mask": [{"region": None, "polygons": [wall_poly], "holes": [furn_hole]}],
        "images": images,
    }
    json_path = os.path.join(DATA, "points.json")
    with open(json_path, "w") as f:
        json.dump(export, f)

    # run the pipeline
    subprocess.run([sys.executable, os.path.join(HERE, "mockup.py"), json_path,
                    "--photos", DATA, "--out", OUT], check=True, cwd=HERE)

    # validate against the tool's own mask rasterisation (self-consistent: a
    # user-drawn polygon has no "true" sub-pixel edge -- whatever PIL fills IS the mask)
    tool_mask = build_region_mask(W, H, [wall_poly], [furn_hole])
    gt = ref_lin.copy()
    gt[tool_mask] = (S * R_paint)[tool_mask]
    gt_u8 = to_u8(gt).astype(np.int16)
    ref_u8 = to_u8(ref_lin).astype(np.int16)
    res_u8 = np.asarray(Image.open(os.path.join(OUT, "mockup_TestBlue.png")).convert("RGB")).astype(np.int16)

    err = np.abs(res_u8 - gt_u8).max(axis=2)
    core = binary_erosion(tool_mask, iterations=2)          # skip 1-2px boundary band
    e = err[core]
    outside = np.abs(res_u8 - ref_u8).max(axis=2)[~tool_mask]

    print("\n=== validation (max 8-bit sRGB channel error) ===")
    print(f"  inside mask : mean {e.mean():.2f}  p99 {np.percentile(e, 99):.1f}  max {e.max()}")
    print(f"  outside mask (must be 0): max {outside.max()}")
    ok = e.mean() < 1.0 and e.max() < 8 and outside.max() == 0
    print("  RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
