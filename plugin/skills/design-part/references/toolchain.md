# Toolchain notes

`agentcad doctor <design>` shows what was found. Paths go in `agentcad.local.toml` next to the design (or
any parent directory), or in `~/.config/agentcad/config.toml`, or in `AGENTCAD_ORCA`, `AGENTCAD_FREECAD`,
`AGENTCAD_BLENDER` and `AGENTCAD_VENDOR_DIR`.

| tool | used by | install (pin the version) | notes |
|---|---|---|---|
| build123d 0.13.0 / OCP 8.0.1 | everything | `uv sync` in agent-cad-works | pinned in `pyproject.toml` / `uv.lock` |
| OrcaSlicer 2.4.2 | `check` (slicing) | AppImage, extract with `--appimage-extract`; point `orca` at `squashfs-root/AppRun` | CLI resolves one level of profile `inherits`: agentcad flattens the machine profile |
| FreeCAD 1.1 | `explode` | AppImage or snap; needs `xvfb-run` | snap: cannot read outside `$HOME` or hidden dirs; agentcad stages in `~/agentcad-stage` |
| Blender 4.5 LTS | `photoreal` | official portable tarball (check the sha256); use a mirror if download.blender.org shows a challenge | RTX 50-series needs 4.4 or newer; OptiX is used automatically, CPU otherwise |

Printer profile: `[printer]` in the config, with `vendor`, `machine`, `process`, `filament` (OrcaSlicer system
profile names) and `filament_density`. The default is a Bambu X1C, 0.4 mm nozzle, 0.20 mm Standard, PETG.

## FreeCAD headless specifics (handled by agentcad; know them when debugging)

- A macro must end in `os._exit(0)`. An uncaught exception leaves FreeCAD idle under Xvfb until the timeout.
- Turn off navigation animation before moving the camera, or measurements read a camera mid-move.
- `saveImage` does not keep the viewport framing (portrait images are scaled by width/height). Fit the mapping
  from an ID pass; don't assume it.

## Blender specifics

- Exposure is tuned for AgX with a white backdrop: world strength 0.15, key light 16 W per m² of camera
  distance. If renders look washed out, lower these before touching materials.
- The shadow catcher plus post-feathering gives a clean white background. Shadows that leave the camera frame
  are faded in post.
