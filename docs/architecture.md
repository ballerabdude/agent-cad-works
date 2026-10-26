# Architecture

```
src/agentcad/
  design.py        Design, ShowPart, Shot, BomItem, CheckResult; load_design()
  geom.py          box, cyl, cone, ring, teardrop, slot, bolt_circle
  kernel.py        OCCT: measure, tessellate, overlap_volume (None -> 0, error -> inf), rotate_xyz
  meshcheck.py     trimesh + manifold3d checks on the tessellation
  layers.py        layer-by-layer island / overhang analysis
  slicer.py        OrcaSlicer CLI with a flattened machine profile
  check.py         the three gates -> out/check.json
  vendor.py        vendor STEP placement, clearance, hole alignment with control
  bom.py           out/BOM.md
  render.py        matplotlib renders + out/site viewer (data/viewer.html)
  presentation.py  presentation export (STEP/STL + manifest), callout layout, gallery page
  freecad.py       FreeCAD runner (Xvfb, snap staging) + finishing (ID-pass anchors, fitted mapping)
  blender.py       Blender runner + finishing (shadow feathering, ray-cast anchors)
  config.py        tool discovery and printer profile
  doctor.py        toolchain report
  cli.py           `agentcad`
  library/         fasteners, extrusions, linear, belts, actuators (sourced specs)
  data/            viewer.html, freecad_explode.FCMacro, blender_scene.py, template/design.py
plugin/            Claude Code plugin (skills + reviewer agent)
examples/zlift/    worked example (Z lift v6)
tests/             pytest
```

Scripts in `data/` run inside FreeCAD's and Blender's own Python. They use only the standard library and the
host API, and talk to the package through JSON files (`job.json`, `manifest.json`, `views.json`,
`*_anchors.json`).

## Outputs of a design (`<design>/out/`, git-ignored)

```
check.json  BOM.md
print/<part>.stl|.step         print-oriented, what you send to the printer
slice/<part>/plate_1.gcode     OrcaSlicer output
site/                          viewer (+ explode/, photoreal/, BOM.md) -> `agentcad serve`
explode/                       FCStd documents, raw renders, final/*.png
photoreal/                     presentation/ (STL + manifest), raw/, final/*.jpg|png
```
