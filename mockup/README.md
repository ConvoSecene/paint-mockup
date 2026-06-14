# Mockup generator

Turns a [Swatch Marker](../swatch-marker) export (v5) + your photos into one
photorealistic mockup per target paint colour.

## How it works

A matte pixel is shading × reflectance, `I = S·R`. Painting changes only `R`, so

```
mockup(p) = reference(p) · (R_paint / R_wall) = reference(p) · gain
```

The gain is measured where shading cancels — a swatch over the reference at the
same pixel (`gain = swatch / reference`). Gains are sampled at the swatch points
and interpolated into a smooth field (absorbing illuminant drift across the wall),
then applied per region inside the polygon mask. Frames are first normalised to a
common exposure/white-balance using the `neutral` reference. All maths is done in
linear light.

**Convention:** the reference frame is the photo with no swatch points (override
with `--reference`).

## Setup

```bash
python3 -m venv ../.venv
../.venv/bin/pip install -r requirements.txt
```

## Run

```bash
../.venv/bin/python mockup.py swatch-points.json --photos /path/to/photos --out out
```

Writes `out/mockup_<ColourLabel>.png`, one per swatch label.

Options: `--reference NAME` (pick the base frame), `--smoothing S` (RBF smoothing,
0 = exact interpolation), `--debug` (also dump region mask PNGs).

## Test

`synth_test.py` builds a synthetic scene with known shading, exposure/WB drift and
an occluder, runs the pipeline, and checks the output against the analytic ground
truth:

```bash
../.venv/bin/python synth_test.py
```

## Limits (inherent to the method)

- Assumes a matte surface — sheen/gloss mismatch isn't captured by a flat swatch.
- No interreflection: a strong colour bouncing onto adjacent surfaces isn't modelled.
- Gain is extrapolated (and clamped to the observed range) outside the sampled
  area, so keep swatches spread across each wall.
- Assumes frames are pixel-aligned (locked-off tripod).
