# Swatch Marker

Mark points on photos and export their sampled colours as JSON.

## Run

```bash
cd swatch-marker
python3 -m http.server
```

Open <http://localhost:8000>.

## Use

1. **Drop in photos** (or use the file picker). Multiple at once; each becomes a tab.
   Convert HEIC to JPEG first — browsers can't display HEIC.
2. Pick a **kind** (`swatch` / `wall` / `neutral`) and type a **label** (e.g. paint name).
3. **Click** the photo to drop a point. It samples a patch (size adjustable, top bar) and
   stores the median RGB. The loupe shows exactly which pixels are sampled.
4. Repeat across all photos. The **±** column flags points on an edge/shadow (turns amber) —
   re-place those on flat colour.
5. **Copy JSON** or **Download .json**.

## Kinds

- `swatch` — a point on a paint swatch (label = colour name).
- `wall` — a bare-wall reference point.
- `neutral` — a fixed grey/white reference visible across frames.

Coordinates are natural-image pixels; RGB is gamma-encoded sRGB (linearized downstream).
