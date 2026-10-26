# Getting started

## 1. Install the package

Requirements: Linux or macOS, Python 3.12, [uv](https://docs.astral.sh/uv/).

```bash
git clone <this repo> agent-cad-works && cd agent-cad-works
uv sync                      # pinned environment in .venv (build123d 0.13.0, OCCT 8.0.1)
uv run agentcad --version
uv run pytest -q             # 16 tests, about 10 s
```

To use `agentcad` from anywhere: `uv tool install .` (or `uv tool install git+<repo url>`).

## 2. Tell agentcad where the external tools are

Checks and quick renders need nothing else. Slicing, exploded views and photoreal renders need OrcaSlicer,
FreeCAD (+ Xvfb) and Blender. See [toolchain.md](toolchain.md) for pinned versions and how to install each.
Then create `agentcad.local.toml` (git-ignored) in your project:

```toml
[tools]
orca = "/opt/orcaslicer/squashfs-root/AppRun"
freecad = "/snap/bin/freecad"
blender = "/opt/blender-4.5.15-linux-x64/blender"

[printer]                  # OrcaSlicer system profile names; default: Bambu X1C, 0.20 mm, PETG
machine = "Bambu Lab X1 Carbon 0.4 nozzle"
process = "0.20mm Standard @BBL X1C"
filament = "Bambu PETG Basic @BBL X1C"
```

```bash
uv run agentcad doctor .     # what was found, and which commands that enables
```

## 3. Your first design

```bash
uv run agentcad new parts/bracket
uv run agentcad check parts/bracket      # interference, printability (with a real slice), design checks
uv run agentcad all parts/bracket        # + BOM, renders, exploded view, photoreal (as tools allow)
uv run agentcad serve parts/bracket      # http://<this machine>:8765/ on your phone
```

Edit `parts/bracket/design.py` and re-run `check` until it passes. Read [design-interface.md](design-interface.md)
and the worked example in [`examples/zlift`](../examples/zlift/).

## 4. Let an agent do it (Claude Code)

Install the plugin (see [plugin.md](plugin.md)), then ask in plain words, e.g. *"design a bracket that holds a
NEMA 17 on a 2020 extrusion, motor shaft parallel to the extrusion"*. The `design-part` skill takes it from
requirements to a checked design, a BOM and renders, and the `cad-reviewer` agent audits the result.
