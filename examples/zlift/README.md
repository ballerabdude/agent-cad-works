# Example: Z lift (RobStride 03 belt drive on a 4080 extrusion)

A vertical axis that carries a 3–5 kg robot arm. A RobStride 03 actuator, mounted low on the back of a 4080
extrusion, drives a GT2 belt through a shaft in one drilled hole. The belt runs between two MGN12 rails on the
front face. This is the sixth version of a real design. It is here because it exercises every part of
agent-cad-works: a moving mechanism, a keep-out zone, a vendor STEP, printed parts with real print
constraints, and presentation output.

```bash
uv run agentcad check examples/zlift        # ~30 s with slicing
uv run agentcad all examples/zlift          # + BOM, renders, FreeCAD exploded view, Blender renders
uv run agentcad serve examples/zlift
```

**Vendor model:** the RS03 checks need RobStride's STEP, which is not redistributed here. Download
`RS03.stp` from github.com/RobStride/Product_Information (Product Literature/CAN2.0/RS03) into
`vendor/robstride/RS03.stp` at the repo root. Without it, those four checks are skipped and the renders use a
simplified actuator.

## Requirements (from the user, 2026-10-25)

- 4080 aluminium extrusion, 40-series with 8 mm slots, M8 slot hardware.
- Two MGN12H rails on the 80 mm front face, with the belt between them.
- RobStride 03, stationary, low on the back face, driving through one hole drilled through the extrusion.
- The bottom ~40 mm of the extrusion sits in the robot's chassis: nothing below z = 45.
- Mount only on the 80 mm faces.

## Layout

- **Drive:** RS03 behind the back face with its axis at **z = 108**. Its Ø70 pilot sits in a pocket in a
  printed plate, which locates it on the shaft axis. A printed hub (3 dowels + 6 countersunk M4) holds an 8 mm
  shaft. The shaft passes through **hole C (Ø10 at x = 41, z = 108)** to a 20T pulley on the front.
- **Belt:** GT2 10 mm, teeth in, wraps the drive pulley 180° (10 teeth) and a 20T idler in a top cap with
  tension slots.
- **Guide:** MGN12 rails on the x = 20/60 slots, lifted on 10 mm spacer bars so the blocks clear the belt. The
  blocks sit at the carriage's top end, so they never pass over the pulley.
- **Carriage:** a single comb wall clamps the belt. 16 M4 heat-set inserts on a 20 mm grid take the arm.

## Results (`out/check.json`)

- **Travel:** 328 mm with L = 500 (carriage z0 from 58 to 386). No interference at either end or in the middle.

| printed part | print (X1C, PETG, 0.2 mm) |
|---|---|
| rs03_mount | 2 h 38 m, 85.6 g |
| carriage | 2 h 19 m, 70.4 g |
| top_cap | 1 h 48 m, 50.6 g |
| drill_jig | 35 m, 15.7 g |
| drive_hub | 24 m, 5.3 g |

All five are single valid solids, watertight and manifold, with 0 floating islands, and slice without warnings.

| design check | result |
|---|---|
| sweep is not vacuous (carriage 6 mm too low hits the pulley) | 124.5 mm³ overlap: detected |
| RS03 STEP vs plate, hub, bolts, extrusion, chassis | 0 overlap; plate and hub seat at distance 0 |
| 8 housing M4 screws | 182.4 mm³ (aligned 192.6, misaligned 603.2, control 43.7) |
| 3 hub dowels | 0.0 mm³ (aligned 0, misaligned 179.2, control 179.0) |
| 6 hub M4 screws | 81.8 mm³ (aligned 88.4, misaligned 377.0, control 376.4) |

## History: what each version taught

| version | change | why |
|---|---|---|
| v1 | NEMA 17 at the bottom, 3:1 belt reduction | first layout |
| v2 | motor at mid-height, belt loop beside the extrusion | the bottom 40 mm sits in the chassis |
| v3 | RobStride 03 at mid-height, omega drive | user switched actuator |
| v4 | RS03 at the bottom, one hole, 180° wrap | user wanted it low |
| v5 | rails on x = 20/60 with spacer bars | the real profile is slot-8 with one slot per 40 mm, not 6 mm V-slot |
| v6 | RS03 interface from RobStride's STEP; M8 hardware | v3–v5 used the RS04 drawing by mistake; the STEP check found it |

## Not covered

Power-loss protection (the RS03 has no brake: the arm drops when unpowered), a cable chain, a homing switch,
and the arm's own mount.
