# The Design interface (agentcad.design)

A design file defines one `Design` subclass, or a module-level `DESIGN = MyDesign(__file__)`. Units are mm.

| member | required | what it is |
|---|---|---|
| `name`, `title` | yes | identifier (output folder names) and human title |
| `printed(state) -> {name: Shape}` | yes | printed parts in assembly position |
| `hardware(state) -> {name: Shape}` | yes | bought parts and keep-out zones, at their real envelope |
| `states() -> list` | no (`[None]`) | poses to sweep; include both ends of every motion range |
| `print_rotation` | yes for printed parts | `{part: (rx, ry, rz)}`, degrees, X then Y then Z, into print orientation |
| `expected_contacts` | no | `{(printed, hardware)}` intended overlaps (belt in a comb, part bolted to a block) |
| `hardware_overlaps` | no | `{(hw, hw)}` intended overlaps of simplified models (block box over its rail) |
| `keepouts` | no | `{zone: {hardware allowed inside}}`; a zone is a hardware solid nothing else may enter |
| `tools() -> {name: Shape}` | no | printed fixtures not in the assembly (drill jigs); sliced, not swept |
| `checks() -> [(name, fn)]` | no | design-specific checks; `fn()` returns `CheckResult`, a dict with `passed`, or a bool |
| `info() -> dict` | no | key numbers for the report and the viewer |
| `bom() -> [BomItem]` | no | bought parts, quantities, notes; compute lengths from the geometry |
| `presentation() -> [ShowPart]` | no | detailed components, material, explode offset, callout label, print axis |
| `shots() -> [Shot]` | no | photoreal cameras (defaults: exploded front/back with callouts, assembled front/back) |
| `render_details() -> [dict]` | no | close-ups for the quick renders: `z` window, `view` (elev, azim), `title`, `hide` |

Materials for `ShowPart.material`: `printed` (with `print_axis` X/Y/Z for layer lines), `aluminium`, `steel`,
`chrome`, `black_oxide`, `rubber`, `black`, `bright`, `seal`.

## Geometry helpers (agentcad.geom)

`box(x0, x1, y0, y1, z0, z1)`, `cyl(center, r, h, axis)`, `cone(base, r0, r1, h, axis)`,
`ring(center, r_out, r_in, h, axis)`, `teardrop(center, r, length, axis, up)` (use for every hole that is
horizontal when printed; `up` is the print's +Z in model coordinates), `slot(c0, c1, r, length, axis)`,
`bolt_circle(center, radius, angles, plane)`. Booleans: `+`, `-`, `&`.

## Library (agentcad.library)

| module | contents |
|---|---|
| `fasteners` | `M3..M8` (clearance, tap drill, socket and countersunk heads), `socket_screw`, `countersink`, `engagement` |
| `extrusions` | `SLOT8_4080`, `VSLOT_4080` profiles; `simple(profile, length, holes)` envelope; `detailed_slot8` |
| `linear` | MGN12 `rail()`, `block()` (envelope or detailed with seals) |
| `belts` | GT2 `pitch_diameter`, `pulley_envelope`, `pulley_detailed`, `belt_segment`, `belt_arc` |
| `actuators` | `RS03_SPEC`, `rs03_envelope`, `rs03_vendor_rotations`, `rs03_output_angles`, `NEMA17` |

## Worked example

`examples/zlift/design.py` in the agent-cad-works repo: a belt-driven vertical axis with a RobStride 03,
including vendor-fit checks, a non-vacuity check, a BOM computed from the geometry, a presentation with
explode offsets, and custom photoreal shots.
