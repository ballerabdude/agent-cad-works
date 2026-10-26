# Verification

`agentcad check` is the definition of done. It writes `out/check.json` and exits 1 on any failure.

## Gate 1: interference

For every state: printed vs hardware, printed vs printed, hardware vs hardware, and keep-out zones vs
everything, using exact OCCT booleans. An overlap above 1e-3 mm³ that is not declared is a failure.
Booleans that **raise** count as `inf` (a failure), so a kernel error can never pass as "no overlap". An empty
intersection (`None` from build123d) is 0.

## Gate 2: printability

Every printed part and tool, in its print orientation:

| check | tool | why it is there |
|---|---|---|
| one valid, closed solid | OCCT `BRepCheck_Analyzer`, solid count | a part cut in two looked valid to the kernel |
| watertight, consistent winding, manifold | trimesh + manifold3d on the tessellation | an edge-only joint passed the kernel check |
| no floating islands | layer analysis (`agentcad.layers`), 0.2 mm slices | slivers printing in mid-air; independent of the slicer |
| slices, no warnings | OrcaSlicer CLI with the configured printer | the real printability and the print time / filament |

## Gate 3: design checks

Whatever the design adds. Two kinds are expected in every serious design.

**Non-vacuity.** Prove the sweep can fail: move a part past its limit and assert an overlap appears. The Z lift
moves its carriage 6 mm below the lower limit and asserts it hits the drive pulley (124.5 mm³).

**Vendor fit** (`agentcad.vendor`, `vendor-fit` skill). Place the manufacturer's STEP and measure:

- clearance to every part it touches;
- hole alignment with probe cylinders, compared against the analytic aligned and misaligned overlaps;
- a **control**: the same probes at a wrong angle that must give a clearly different overlap. A control that
  lands on other holes cannot discriminate, and `hole_alignment` fails it.

Z lift results:

| check | measured | aligned | misaligned | control |
|---|---|---|---|---|
| 8 housing screws | 182.4 | 192.6 | 603.2 | 43.7 |
| 3 hub dowels | 0.0 | 0.0 | 179.2 | 179.0 |
| 6 hub screws | 81.8 | 88.4 | 377.0 | 376.4 |

All values are overlap in mm³.

## Reading a failure

- `a x b@state: V`: parts `a` and `b` overlap by V mm³ at that state. Fix the design. If the contact is
  intended, declare the pair and say why in a comment.
- `islands=N`: N cross-sections start in mid-air; `island_detail` gives the height and the bounds. Usually
  a wall that must start on the bed, or a sliver next to a pocket.
- `slicer_warning`: read it, then confirm with the layer analysis. A "floating regions" warning with 0 islands
  and 0 cm³ of tree support is a false positive. Document it rather than ignoring it.
