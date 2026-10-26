---
name: design-part
description: Design a 3D-printed mechanical part or mechanism (brackets, mounts, carriages, belt drives, actuator adapters) as a build123d design file and prove it with the agentcad verification gates - interference sweep over every pose, printability (valid solid, watertight, no floating islands, OrcaSlicer slice), vendor-STEP fit, then BOM and renders. Use when the user asks to design, modify or check a physical part, or to turn a mechanical idea into printable files.
---

# Design a part with agentcad

You write a **design file** (`design.py`, one `Design` subclass) and drive everything else with the `agentcad`
CLI. You are done when `agentcad check` passes, not when the geometry looks right. Never report a pass you have
not seen in `out/check.json`.

Read `references/design-interface.md` before writing the first design, and `references/lessons.md` before
dimensioning anything bought.

## 0. Toolchain

```bash
agentcad --version || echo "install: uv tool install git+https://github.com/ballerabdude/agent-cad-works"
agentcad doctor <design-dir>
```

Check and quick renders always work. Slicing needs OrcaSlicer, the exploded view needs FreeCAD and Xvfb,
photoreal needs Blender. Tool paths go in `agentcad.local.toml` (see `references/toolchain.md`). If a tool is
missing, say which outputs that removes. Don't install system packages without asking.

## 1. Requirements: write them down, then ask only what blocks you

Put requirements at the top of `design.py`, with the date and who said them. Ask the user only for facts you
cannot measure or look up, and ask them early:

- **The real profile or part they own.** "4080" alone is ambiguous: a 6 mm V-slot and an 8 mm 40-series slot
  look alike but have different slot positions. Get the supplier drawing or a measurement.
- **The vendor STEP for any bought actuator, motor or bearing block.** Drawings get mixed up between models.
- **Their hardware** (M5 vs M8 T-nuts, which screws they have), their printer and their material.
- **Keep-outs** (chassis, other mechanisms) and **where mounting is allowed**.

Decisions that are yours (layout, clearances, which screw) get a sensible default and a one-line reason in the
design file. Don't ask the user about those.

## 2. Write the design

```bash
agentcad new parts/<name>          # template design.py + README.md
```

- Use `agentcad.library` for bought parts. Every dimension cites a source (datasheet section, vendor STEP,
  user's drawing). If a part is missing, add it to the library with its source.
- Model hardware at its **real envelope**: belts, pulley flanges and hubs, screw heads, bolt shanks in slots,
  actuator bodies, keep-out zones. The sweep is only as good as these shapes.
- **States:** list both ends of every motion range, plus the middle.
- Holes that are horizontal in the print orientation are `teardrop`s. Walls start on the bed. Give every part a
  `print_rotation`.
- Screw lengths are computed: grip plus engagement, with engagement below the target's thread depth.

## 3. Prove it

```bash
agentcad check <design>            # exit 1 on any failure; details in out/check.json
```

Fix the **design**, not the check. Each overlap pair, island or slicer warning is a real defect until shown
otherwise. For example, an edge-only joint between two bodies passed OCCT's own validity check and failed the
mesh check. Only use `expected_contacts`, `hardware_overlaps` or `keepouts` for genuinely intended contact (a
belt in a clamp comb, a block over its rail), and comment why.

Add design checks (`Design.checks()`) for whatever the generic gates cannot see:

- **Non-vacuity:** move something past its limit and assert the sweep reports it. A check that cannot fail
  proves nothing.
- **Vendor fit:** use the `vendor-fit` skill whenever a bought part has a STEP model.
- Clearances you care about (rotating flange to clamp, for example) via `shape.distance_to(other)`.

Then report tight clearances (distance under about 1.5 mm) to the user as numbers, even when they pass.

## 4. Deliver

```bash
agentcad bom <design>              # out/BOM.md
agentcad render <design>           # out/site (phone-friendly viewer); `agentcad serve <design>`
agentcad all <design>              # adds the FreeCAD exploded view + Blender renders when available
```

Write `README.md` next to the design: requirements, layout, holes to drill (positions measured from a named
face), assembly order, check results (numbers, not adjectives), and open questions. When a later version
supersedes an earlier one that would not fit, put a **"do not print"** warning at the top of the old README.

## Report to the user

Lead with whether it passed and what they should do next. Give the key numbers: travel, hole positions, print
time and filament per part, tightest clearances. List what you assumed and what still needs their input. Plain
statements; no hedging, no enthusiasm.
