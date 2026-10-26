# Toolchain

Canonical notes, including the headless FreeCAD and Blender specifics, are in
[`plugin/skills/design-part/references/toolchain.md`](../plugin/skills/design-part/references/toolchain.md).
This page covers installation.

| tool | version used | how to install | config key |
|---|---|---|---|
| Python | 3.12 | uv | — |
| build123d / OCP | 0.13.0 / 8.0.1.1 | `uv sync` (pinned in `pyproject.toml` and `uv.lock`) | — |
| OrcaSlicer | 2.4.2 | download the AppImage from the OrcaSlicer GitHub releases, `./OrcaSlicer*.AppImage --appimage-extract` | `tools.orca` = `.../squashfs-root/AppRun` |
| FreeCAD | 1.1.1 | AppImage from freecad.org, or `snap install freecad` | `tools.freecad` |
| Xvfb | any | `apt install xvfb` (provides `xvfb-run`) | — |
| Blender | 4.5.15 LTS | official `blender-4.5.15-linux-x64.tar.xz`; check it against the published `.sha256`; if download.blender.org shows a browser challenge, use a mirror listed on blender.org | `tools.blender` |

No system Python or GPU drivers are modified by any of this. Blender uses OptiX on NVIDIA GPUs when present
(RTX 50-series needs Blender 4.4 or newer), and the CPU otherwise.

Config precedence: built-in defaults < `~/.config/agentcad/config.toml` < `agentcad.toml` (commit with the
project) < `agentcad.local.toml` (machine paths, git-ignored) < `AGENTCAD_*` environment variables.
