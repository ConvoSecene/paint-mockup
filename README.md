# Paint mockup

Accurate mockups of a room repainted a new colour, extrapolated from photos of a
real paint swatch tacked at different spots on the wall.

## 1. Take the photos

- **Lock everything.** Tripod; manual exposure, ISO, white balance and focus held
  constant across the whole series. On iPhone: tap-and-hold for AE/AF lock, or use
  a RAW app. Don't bump the tripod — frames must stay pixel-aligned.
- **Constant lighting.** No sun drift through windows mid-shoot; do it quickly or
  under controlled light.
- **One bare-wall reference** photo with no swatch — this is the base that gets repainted.
- **Swatch frames:** tack the swatch flat against the wall (matte, no curl/shadow) and
  photograph it at many positions, spread right to the corners of each wall.
- **A fixed neutral** (grey/white card) visible in *every* frame, for cross-frame correction.
- **Two wall colours?** Treat each as a region and put a swatch on each surface.
- Convert HEIC to JPEG (browsers/tools can't read HEIC).

## 2. Mark points and masks — [swatch-marker/](swatch-marker)

Browser tool: drop in the photos, mark swatch / wall / neutral points, outline each
wall (mask), export JSON. See [swatch-marker/README.md](swatch-marker/README.md).

## 3. Render the mockups — [mockup/](mockup)

Python tool: feeds the JSON + photos through the shading-preserving transfer and
writes one image per colour. See [mockup/README.md](mockup/README.md).
