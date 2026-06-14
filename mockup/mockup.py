#!/usr/bin/env python3
"""
Paint mockup generator.

Takes a Swatch Marker export (version 5) plus the bare-wall reference photo and
produces one photorealistic mockup per target paint colour.

Theory (see swatch-marker/README and the project notes):
    A matte pixel is  I = S * R  (shading x reflectance). Shading is independent
    of the surface colour, so painting only changes R:
        M(p) = I_ref(p) * (R_paint / R_wall) = I_ref(p) * gain
    The gain is measured where shading cancels -- a swatch over the reference at
    the same pixel:  gain = swatch / reference. Gains are sampled at scattered
    points and interpolated into a smooth field (handles illuminant drift), then
    applied per region inside a polygon mask.

Convention: the reference frame is the image in the JSON with no swatch points.
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict

import numpy as np
from PIL import Image, ImageDraw
from scipy.interpolate import RBFInterpolator, RegularGridInterpolator

EPS = 1e-6


# ---------- colour transfer (sRGB <-> linear), operating on [0,1] floats ----------
def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    c = np.clip(np.asarray(c, dtype=np.float64), 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def load_linear(path):
    img = Image.open(path).convert("RGB")
    return srgb_to_linear(np.asarray(img, dtype=np.float64) / 255.0)


def save_linear(arr, path):
    out = np.round(linear_to_srgb(arr) * 255.0).astype(np.uint8)
    Image.fromarray(out, "RGB").save(path)


# ---------- sampling ----------
def sample_patch_linear(ref_lin, x, y, r):
    """Median linear RGB of a (2r+1) patch of the reference around (x, y)."""
    h, w = ref_lin.shape[:2]
    x, y = int(round(x)), int(round(y))
    x0, x1 = max(0, x - r), min(w, x + r + 1)
    y0, y1 = max(0, y - r), min(h, y + r + 1)
    patch = ref_lin[y0:y1, x0:x1].reshape(-1, 3)
    return np.median(patch, axis=0)


def reg_key(s):
    """Normalise a region value ('' / None both mean the single implicit wall)."""
    return s or ""


# ---------- masks ----------
def build_region_mask(w, h, fills, holes):
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    for poly in fills:
        d.polygon([tuple(p) for p in poly], fill=255)
    for poly in holes:
        d.polygon([tuple(p) for p in poly], fill=0)
    return np.asarray(m) > 0


# ---------- neutral cross-frame normalisation ----------
def neutral_corrections(globals_, ref_name, frame_names):
    """Per-frame linear gain that maps each frame onto the reference frame's
    exposure/white-balance, derived from the fixed neutral reference(s)."""
    neutrals = [g for g in globals_ if g["kind"] == "neutral"]
    corr = {name: np.ones(3) for name in frame_names}
    if not neutrals:
        print("  ! no neutral reference -- assuming identical processing across frames")
        return corr
    for name in frame_names:
        ratios = []
        for n in neutrals:
            s_ref, s_f = n["samples"].get(ref_name), n["samples"].get(name)
            if s_ref and s_f:
                rl = srgb_to_linear(np.array(s_ref["rgb"]) / 255.0)
                fl = srgb_to_linear(np.array(s_f["rgb"]) / 255.0)
                ratios.append(rl / np.maximum(fl, EPS))
        if ratios:
            corr[name] = np.mean(ratios, axis=0)
    return corr


# ---------- gain field ----------
def fit_gain_field(xy, gains, ys, xs, smoothing):
    """Interpolate per-channel gain over the masked pixels (ys, xs).

    Fits a thin-plate-spline RBF on a coarse grid spanning the mask bbox, then
    bilinearly samples it at every masked pixel -- keeps memory bounded since the
    gain is smooth by assumption."""
    n = len(xy)
    if n < 3:
        return np.tile(gains.mean(axis=0), (len(ys), 1))

    x0, x1 = xs.min(), xs.max()
    y0, y1 = ys.min(), ys.max()
    nx = max(2, min(80, x1 - x0 + 1))
    ny = max(2, min(80, y1 - y0 + 1))
    gx = np.linspace(x0, x1, nx)
    gy = np.linspace(y0, y1, ny)
    GX, GY = np.meshgrid(gx, gy)

    rbf = RBFInterpolator(xy, gains, kernel="thin_plate_spline", smoothing=smoothing)
    grid_gain = rbf(np.column_stack([GX.ravel(), GY.ravel()])).reshape(ny, nx, 3)

    rgi = RegularGridInterpolator((gy, gx), grid_gain, bounds_error=False, fill_value=None)
    field = rgi(np.column_stack([ys, xs]))
    # Clamp to the observed gain range: the spline can overshoot wildly when
    # extrapolating past the sampled region, and gain shouldn't exceed what we saw.
    return np.clip(field, gains.min(axis=0), gains.max(axis=0))


# ---------- main pipeline ----------
def run(json_path, photos_dir, out_dir, reference=None, smoothing=0.0, debug=False):
    with open(json_path) as f:
        data = json.load(f)
    if data.get("tool") != "swatch-marker":
        sys.exit("Not a Swatch Marker export.")

    images = data["images"]
    patch_r = data["sample"]["patchRadius"]
    frame_names = [im["filename"] for im in images]

    # reference frame: explicit override, else the convention (no swatch points)
    if reference:
        ref_name = reference
    else:
        empty = [im["filename"] for im in images if not im["points"]]
        if len(empty) != 1:
            sys.exit(f"Need exactly one swatch-free reference frame (found {len(empty)}: "
                     f"{empty}). Pass --reference NAME.")
        ref_name = empty[0]
    print(f"Reference frame: {ref_name}")

    ref_path = os.path.join(photos_dir, ref_name)
    if not os.path.exists(ref_path):
        sys.exit(f"Reference photo not found: {ref_path}")
    ref_lin = load_linear(ref_path)
    h, w = ref_lin.shape[:2]

    # region masks
    region_masks = {}
    for grp in data["mask"]:
        key = reg_key(grp.get("region"))
        m = build_region_mask(w, h, grp["polygons"], grp["holes"])
        region_masks[key] = region_masks.get(key, np.zeros((h, w), bool)) | m
    if not region_masks:
        sys.exit("No mask polygons in the export -- nothing to paint.")

    # cross-frame normalisation
    print("Neutral normalisation:")
    corr = neutral_corrections(data["globalPoints"], ref_name, frame_names)

    # collect gain samples: label -> region -> [(x, y, gain3)]
    samples = defaultdict(lambda: defaultdict(list))
    for im in images:
        if im["filename"] == ref_name:
            continue
        c = corr.get(im["filename"], np.ones(3))
        for p in im["points"]:
            lin = srgb_to_linear(np.array(p["rgb"]) / 255.0) * c
            refp = sample_patch_linear(ref_lin, p["x"], p["y"], patch_r)
            gain = lin / np.maximum(refp, EPS)
            samples[p["label"] or "unnamed"][reg_key(p["region"])].append((p["x"], p["y"], gain))

    if not samples:
        sys.exit("No swatch points found.")

    os.makedirs(out_dir, exist_ok=True)
    print("Rendering:")
    for label, by_region in samples.items():
        out = ref_lin.copy()
        for region, pts in by_region.items():
            mask = region_masks.get(region)
            if mask is None:
                print(f"  ! {label}: region '{region}' has no mask polygon -- skipped")
                continue
            xy = np.array([(x, y) for x, y, _ in pts], dtype=np.float64)
            gains = np.array([g for _, _, g in pts], dtype=np.float64)
            ys, xs = np.where(mask)
            field = fit_gain_field(xy, gains, ys, xs, smoothing)
            out[ys, xs] = ref_lin[ys, xs] * field
            print(f"  {label} / region '{region}': {len(pts)} samples, "
                  f"mean gain {gains.mean(axis=0).round(3)}")
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", label)
        path = os.path.join(out_dir, f"mockup_{safe}.png")
        save_linear(out, path)
        print(f"  -> {path}")

        if debug:
            for region, mask in region_masks.items():
                dpath = os.path.join(out_dir, f"mask_{region or 'main'}.png")
                Image.fromarray((mask * 255).astype(np.uint8)).save(dpath)


def main():
    ap = argparse.ArgumentParser(description="Generate paint mockups from a Swatch Marker export.")
    ap.add_argument("json", help="Swatch Marker export (.json)")
    ap.add_argument("--photos", default=".", help="directory containing the photos")
    ap.add_argument("--out", default="out", help="output directory")
    ap.add_argument("--reference", help="reference frame filename (default: the swatch-free frame)")
    ap.add_argument("--smoothing", type=float, default=0.0, help="RBF smoothing (0 = exact interpolation)")
    ap.add_argument("--debug", action="store_true", help="also write region mask PNGs")
    a = ap.parse_args()
    run(a.json, a.photos, a.out, a.reference, a.smoothing, a.debug)


if __name__ == "__main__":
    main()
