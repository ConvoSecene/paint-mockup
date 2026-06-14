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

To resume later, **Import JSON** (button or drag the `.json` in). It restores every point,
global, region and polygon. The export doesn't contain the photos themselves, so re-drop them —
they're matched to the restored data by filename (order doesn't matter). Frames awaiting their
photo show as dashed ⚠ tabs.

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

## Masks (Draw mask mode)

Switch the top toggle to **Draw mask** to outline where each wall actually is — the downstream
tool only repaints inside the mask, and uses it to decide which region's transfer applies where.

1. Pick a **region** (same names as your points; blank = single wall).
2. Choose **fill (wall)** or **hole (occluder)**.
3. **Click** around the wall to drop polygon vertices. **Finish** (or Enter) closes it,
   **Backspace** undoes the last vertex, **Esc** cancels.
4. Add **hole** polygons for things in front of the wall (furniture, radiator, pictures, sockets)
   — they get cut out of that region.
5. **Adjust** any vertex by dragging it (the cursor turns into a move icon over a grabbable point);
   works on finished polygons and the one you're still placing.

Polygons are **global** — like wall/neutral points, the geometry is identical across tripod-locked
frames, so they're drawn once and shown on every photo. A wall is a plane, so its outline is usually
4–6 clicks. Per-region polygons double as the region map — no separate segmentation needed.

Coordinates are natural-image pixels; RGB is gamma-encoded sRGB (linearized downstream).
