# The design interface

Every design is one Python file with one `agentcad.design.Design` subclass. The canonical reference table
(members, materials, helpers, library) is
[`plugin/skills/design-part/references/design-interface.md`](../plugin/skills/design-part/references/design-interface.md):
the same file the agent reads, so humans and agents work from one source.

## Mental model

```
             states()  ──►  for each pose:  printed(state) + hardware(state)  ──►  interference sweep
design.py ──► printed parts ──► print_rotation ──► STL/STEP ──► mesh + layer checks ──► OrcaSlicer
             checks()  ──►  design-specific gates (vendor fit, clearances, non-vacuity)
             bom(), info()  ──►  BOM.md, viewer
             presentation(), shots()  ──►  FreeCAD exploded view, Blender renders
```

- **`printed` vs `hardware`**: printed parts are what you design and print. Hardware is everything else that
  takes up space: bought parts, the frame, belts, screw heads, *and keep-out zones* (a chassis box, a cable
  path). Hardware is modelled at its real envelope and kept simple (fast booleans). The detailed versions
  go in `presentation()`.
- **`state`**: anything that identifies a pose (a carriage height, joint angles, a dict). `states()` returns
  the poses to sweep. Include both ends of each motion range; compute the ends from the geometry
  (`car_limits()` in the example) instead of typing them.
- **Declared overlaps** are the only way to tell the sweep that contact is intended. Keep them narrow (pairs,
  not "anything with the belt") and comment each one.
- **`checks()`** returns `(name, fn)` pairs. `fn()` returns a `CheckResult`, a dict with `passed`, or a bool.
  A raising check is a failing check.

## Conventions that keep designs checkable

1. Module docstring: requirements (with date and source), coordinate frame, sources for bought parts.
2. Parameters at the top, in mm, each with a one-line reason when it is a decision.
3. One function per printed part, with a docstring saying what it does and how it prints.
4. Derived values are computed (`ZD = ...` from clearances), not typed, so changing one input updates the rest.
5. A `DESIGN = MyDesign(__file__)` at the end, so `load_design` finds it unambiguously.

See [`examples/zlift/design.py`](../examples/zlift/design.py) for all of these in one file.
