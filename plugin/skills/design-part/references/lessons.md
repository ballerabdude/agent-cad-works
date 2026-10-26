# Lessons (each was a real failure)

From the project agent-cad-works grew out of: a robot Z lift that went through six versions. Each item says
what happened and the rule that prevents it.

## Requirements and bought parts

1. **The extrusion was not the profile everyone assumed.** "V-slot 4080, 6 mm slots" was designed for five
   versions. The supplier drawing showed a 40-series slot-8 profile with one slot per 40 mm. The rails had to
   move and the belt no longer fitted between the blocks. *Rule: get the supplier drawing (or measure) before
   placing anything on a profile.*
2. **The actuator drawing belonged to another model.** The mount was designed for an "RS03" drawing that was
   the RS04's (Ø120 vs Ø100.5, different hole patterns). Placing RobStride's own STEP on the design exposed it.
   *Rule: check every bought part against its vendor STEP (`vendor-fit` skill); never trust a drawing alone.*
3. **The STEP showed what the drawing did not.** The RS03's Ø70 pilot is about Ø71 at its base (a fillet). A
   Ø70.4 pocket would have stopped it seating; a 0.7 mm chamfer at the pocket mouth fixed it.
4. **Hardware changes geometry.** Switching T-nuts from M5 to M8 (the user's actual hardware) moved the drive
   axis 4.5 mm, because the bigger heads must clear the actuator body. *Rule: ask what hardware they have.*
5. **Rotating a part rotates all its patterns.** Turning the actuator 22.5 deg to clear bolt heads also turned
   its output-flange pattern. The hub had to follow.

## Checks

6. **Kernel validity is not printability.** OCCT called an edge-only joint between two bodies valid; the
   independent mesh check (trimesh + manifold3d) flagged it non-manifold.
7. **A split part can pass as valid.** An opening cut a bracket into two disconnected solids. Each was valid;
   only the solid count gave it away. The gate requires exactly one solid.
8. **Empty intersections are not errors, and errors are not empty.** `a & b` returns `None` when they do not
   touch. An early checker turned that into NaN, which also hid real boolean failures. Now `None` means 0 and an
   exception means `inf` (a failure).
9. **Prove each check can fail.** Over-travel by 6 mm must collide; a dowel pattern rotated by a wrong angle must
   overlap. A control rotated onto the neighbouring holes (30 deg) passed as well, so the control was moved to
   land on solid (15 deg).
10. **STEP bounding boxes sit 1e-4 off round numbers.** A `min.z >= 26.0` filter missed the output flange (its
    box started at 25.9999). Put a margin on every threshold.
11. **Slicer warnings need interpretation, layer analysis does not.** OrcaSlicer's "floating regions" warning
    fired on a part that needed 0.0 cm³ of support. The independent layer analysis (islands) is the gate.
    Remove the warning's cause or document why it is a false positive.
12. **Plain round holes high up in a part grow supports.** 6.3 cm³ of tree support came from three horizontal
    holes; teardrop roofs removed all of it.

## Mechanism details

13. **A rotating flange next to a clamp needs real clearance.** 0.27 mm between an 18 mm pulley flange and a
    clamp would rub with a 19 mm flange. Check against the largest flange you might buy.
14. **Blocks are wider than rails.** MGN12H blocks (27 mm) on a slot-8 4080 leave 13 mm between them. Rails on
    10 mm spacer bars put the block undersides above the belt.
15. **Screw lengths are geometry.** M3x12 into an MGN12H with the original counterbore engaged 2.1 mm; the
    counterbore was deepened so it engages 3.1 of the block's 3.5 mm threads.
16. **Unpowered axes drop.** Quasi-direct-drive actuators and stepper belt drives are backdrivable. Say so
    every time a vertical axis carries a load.
