---
name: vendor-fit
description: Verify that a design fits a bought part (actuator, motor, bearing block, gearbox) by placing the manufacturer's STEP model on it and measuring - overlaps, seating, and screw/dowel hole alignment with a control that must fail. Use whenever a design mounts to a part that has a vendor CAD model, and before anyone prints an adapter, hub or mount.
---

# Fit a design against the vendor's STEP

A drawing is a claim; the vendor's STEP is evidence. In the project this skill comes from, a mount was
designed from a drawing that belonged to a different model. Only placing the real STEP showed it.

## 1. Get the model and keep it out of git

- Ask the user for the STEP (or find it on the vendor's site or GitHub). Save it as
  `vendor/<maker>/<part>.stp`. `vendor/` is git-ignored: vendor CAD is rarely redistributable. Record the URL
  and file date in the design's README so others can download it.
- Inspect it first: overall size, solids, coaxial diameters, small cylindrical faces (holes) with their bolt
  circles and angles. Compare with the drawing and the datasheet. **If they disagree, stop and tell the user
  which numbers differ.** Don't pick one silently.

## 2. Place it on the design

```python
from agentcad import vendor
raw = vendor.load_step(step)
placed = vendor.place(raw, [("Z", turn_deg), ("X", -90)], (x, face_y - step_face_z, z))
output, housing = vendor.split_solids(placed, predicate)   # rotating parts vs stationary, if relevant
```

- Find the vendor frame from the model itself: axis, mounting-face plane, the angle of the first hole.
- Rotating the part to dodge your bolts rotates **every** pattern on it (output flange too). Recompute them.
- Bounding boxes from STEP solids sit about 1e-4 off round numbers. Give predicates a margin.

## 3. Measure, as design checks (`Design.checks()`)

1. **Clearance:** `vendor.clearance(vendor_solid, {name: part})` for every part it touches or comes near.
   Overlap must be ≤ 1e-3 mm³. Distance 0 with zero overlap is a correct seat. Report anything under about
   1.5 mm.
2. **Hole alignment:** probe cylinders where your screws and dowels go, `vendor.probes(...)`, then
   `vendor.hole_alignment(target, probe, control, vendor.expected_overlap(n, probe_r, hole_r, depth))`:
   - screws: probe radius = nominal, hole radius = tap drill. Aligned overlap is the thread ring only.
   - dowels: probe slightly under the hole. Aligned overlap is 0.
   - control: the same probes at a wrong angle that lands on **solid material**. A control that lands on other
     holes (neighbouring pattern) cannot tell right from wrong; the check rejects it.
3. **Seating:** the faces you designed to touch are at the expected positions (e.g. output face at
   mounting face + stand-out).

Each check must pass in `agentcad check`, and the numbers go into the README (measured / aligned /
misaligned / control).

## 4. When it does not fit

Fix the design: chamfer a pocket mouth for a base fillet, move bolts, change the pattern phase. Then re-run
everything. If the vendor data itself is inconsistent, report both versions to the user and ask which unit they
have.
