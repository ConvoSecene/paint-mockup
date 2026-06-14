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
2. Pick a **kind** (`swatch` / `wall` / `neutral`), type a **label** (e.g. paint name), and
   optionally a **region** (see below). Label and region stick between clicks.
3. **Click** the photo to drop a point. It samples a patch (size adjustable, top bar) and
   stores the median RGB. The loupe shows exactly which pixels are sampled.
4. Repeat across all photos. The **±** column flags points on an edge/shadow (turns amber) —
   re-place those on flat colour.
5. **Copy JSON** or **Download .json**.

## Kinds

- `swatch` — **per-frame**. A point on a paint swatch in the active photo (label = colour name).
- `wall` — **global**. Bare-wall reference. Place once; auto-sampled at the same pixel in every photo.
- `neutral` — **global**. Fixed grey/white reference. Place once; auto-sampled in every photo.

Global points (wall/neutral) are placed a single time and read from all frames automatically —
their per-frame values differ (that's the cross-frame correction signal), but the *location* is
identical, so don't re-pick them by hand. They show as lettered squares; swatches as numbered circles.
Load all your photos before placing globals, or they back-fill any added later.

## Regions

A **region** names a source surface — one stretch of existing wall colour. If a room has two
differently-coloured walls you plan to paint the same target, give each its own region (e.g.
`chimney`, `alcove`). Each region needs its **own** `wall` sample **and** at least one `swatch`
sample placed on it, because the paint-over transfer depends on the colour underneath.

Points are colour-coded by region on the canvas and in the tables (squares = global, circles =
swatch). Leave region blank for single-colour rooms. Region names autocomplete once used.

Coordinates are natural-image pixels; RGB is gamma-encoded sRGB (linearized downstream).
