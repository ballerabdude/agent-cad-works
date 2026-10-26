# Parts library (`agentcad.library`)

Bought parts, each with the source of every number:

| module | parts | sources |
|---|---|---|
| `fasteners` | M3–M8: clearance (ISO 273), tap drill, socket head (ISO 4762), countersunk (ISO 10642), nut (ISO 4032); heat-set insert hole | ISO standards |
| `extrusions` | `SLOT8_4080` (40-series, 8 mm slot), `VSLOT_4080` (6 mm V-slot): envelope + detailed slot-8 model | supplier drawing (slot 8); OpenBuilds-style V-slot |
| `linear` | MGN12 rail, MGN12H block (envelope; detailed with seals and screw holes) | HIWIN MG series catalogue |
| `belts` | GT2 pitch diameter, pulley envelope and detailed model, belt segments and arcs | Gates GT2 (2MGT) |
| `actuators` | RobStride 03 (envelope, vendor-STEP placement, output pattern after rotation), NEMA 17 | RobStride RS03 STEP + user manual §1.1; NEMA ICS 16 |

## Adding a part

1. Put the spec in a frozen dataclass or module constants, **with a comment citing the source** (document,
   section or table, date).
2. Provide an **envelope** function for interference checks (simple, conservative, fast) and, if it will be
   rendered, a **detailed** function for presentation.
3. If the vendor publishes a STEP: add the placement constants (axis, mounting face, first-hole angle) and a
   vendor-fit check in a design that uses it. Do not commit the STEP; document where to download it.
4. Add a test for any non-trivial derived value (see `tests/test_library.py`).

Known trap: drawings get attributed to the wrong model. The RS04 drawing (Ø120, 10x M4 on Ø106) circulates
as the RS03's; `actuators.py` says so.
