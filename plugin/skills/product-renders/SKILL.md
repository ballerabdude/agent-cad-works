---
name: product-renders
description: Produce presentation material for a checked agentcad design - FreeCAD exploded-view documents and renders with numbered callouts, Blender Cycles photoreal renders (white background with soft shadows, transparent PNGs, close-ups), and a phone-friendly gallery. Use when the user wants marketing images, an exploded view, product shots or a shareable visual of a design.
---

# Exploded views and photoreal renders

Only render a design whose `agentcad check` passes. Images of a part that does not fit are worse than none.

## 1. Presentation model (`Design.presentation()`)

Return one `ShowPart` per visible component:

- `shape`: the **detailed** model (T-slot profile, grooved rails, toothed pulleys, a belt that wraps, screws),
  not the interference envelope. Use the vendor STEP for bought parts when available.
- `material`: `printed` (+ `print_axis` = the world axis that is vertical when printed, for 0.2 mm layer
  lines), `aluminium`, `steel`, `chrome`, `black_oxide`, `rubber`, `black`, `bright`, `seal`.
- `explode`: offset in mm along the assembly direction. Stack parts that go on in sequence at increasing
  distances (spacers 30, rails 65, blocks 100, carriage 150, screws 205). Move a chain behind the frame with
  negative offsets. Parts that stay put (frame, belt, shaft through a hole) keep 0.
- `label`: callout text for the main components; `None` for screws and other small hardware.

## 2. Run

```bash
agentcad explode <design>                       # FreeCAD: FCStd documents + orthographic views with callouts
agentcad photoreal <design> --samples 64 --pct 40 --shots exploded_front   # quick look first
agentcad photoreal <design>                     # full: 512 samples, all shots
agentcad serve <design>                         # out/site/explode/ and out/site/photoreal/
```

Look at the quick render before the full one. Check exposure (black parts must look black), framing,
whether every labelled part is visible, and leader lines.

## 3. Shots (`Design.shots()`)

The defaults are exploded front and back (with callouts) and assembled front and back. Add close-ups with
`Shot(name, title, exploded, direction, lens_mm, resolution, hidden, frame_box)`:

- `direction` is where the camera looks; world Z stays up on screen.
- `frame_box` is the world box (mm) to fill the frame.
- `hidden` removes parts that block the view (e.g. the carriage over a pulley).

## 4. Check the results before showing them

- Read each callout image. Parts hidden in a view are left unlabelled and reported: label them in the other
  view, or add a shot.
- Leader lines must not cross labels; the layout swaps crossing neighbours, but a line may still pass over a
  part. Mention it if it does.
- Vendor STEPs and files that embed them (FCStd) stay out of git; rendered images are fine to share.

## Output

- `out/explode/`: `<name>_exploded.FCStd`, `<name>_assembled.FCStd` and `final/*.png` (white, transparent,
  callouts).
- `out/photoreal/final/`: `*.jpg` (white with soft shadow), `*_transparent.png`, `*_callouts.jpg`.
- Galleries in `out/site/`.
