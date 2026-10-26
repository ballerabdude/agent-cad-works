"""Where the external tools are, and which printer profile to slice with.

Settings are merged, later wins:
  1. built-in defaults (Bambu Lab X1 Carbon, 0.4 mm nozzle, 0.20 mm Standard, Bambu PETG Basic)
  2. ``~/.config/agentcad/config.toml``
  3. ``agentcad.toml`` in the design's directory or any parent (commit this one with the project)
  4. ``agentcad.local.toml`` next to it (machine-specific paths; git-ignored)
  5. environment: ``AGENTCAD_ORCA``, ``AGENTCAD_FREECAD``, ``AGENTCAD_BLENDER``, ``AGENTCAD_VENDOR_DIR``

Example ``agentcad.local.toml``::

    [tools]
    orca = "/opt/orcaslicer/squashfs-root/AppRun"
    freecad = "/snap/bin/freecad"
    blender = "/opt/blender-4.5.15-linux-x64/blender"

    [printer]
    machine = "Bambu Lab X1 Carbon 0.4 nozzle"
    process = "0.20mm Standard @BBL X1C"
    filament = "Bambu PETG Basic @BBL X1C"
    filament_density = 1.27

Run ``agentcad doctor`` to see what was found.
"""

from __future__ import annotations

import glob
import os
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PRINTER = {
    "vendor": "BBL",
    "machine": "Bambu Lab X1 Carbon 0.4 nozzle",
    "process": "0.20mm Standard @BBL X1C",
    "filament": "Bambu PETG Basic @BBL X1C",
    "filament_density": 1.27,
}


@dataclass
class Config:
    orca: Path | None = None
    freecad: Path | None = None
    blender: Path | None = None
    vendor_dir: Path | None = None
    stage_dir: Path = field(default_factory=lambda: Path.home() / "agentcad-stage")
    printer: dict = field(default_factory=lambda: dict(DEFAULT_PRINTER))
    serve_host: str = "0.0.0.0"
    serve_port: int = 8765
    sources: list[str] = field(default_factory=list)

    @property
    def orca_profiles(self) -> Path | None:
        """``resources/profiles`` of an extracted OrcaSlicer AppImage (or install) next to the binary."""
        if not self.orca:
            return None
        for base in (self.orca.parent, self.orca.parent.parent):
            p = base / "resources" / "profiles"
            if p.exists():
                return p
        return None

    @property
    def freecad_is_snap(self) -> bool:
        return bool(self.freecad and (str(self.freecad).startswith("/snap/")
                                      or os.path.realpath(self.freecad).endswith("/usr/bin/snap")))


def _find_project_files(start: Path, name: str) -> list[Path]:
    found, d = [], start.resolve()
    while True:
        if (d / name).exists():
            found.append(d / name)
        if d.parent == d:
            break
        d = d.parent
    return list(reversed(found))          # outermost first, so the nearest one wins


def _discover(cfg: Config, roots: list[Path]) -> None:
    def first(paths):
        for p in paths:
            if p and Path(p).exists():
                return Path(p)
        return None

    if cfg.orca is None:
        cands = [r / "third_party/orcaslicer/squashfs-root/AppRun" for r in roots]
        cands += [shutil.which(n) for n in ("orca-slicer", "OrcaSlicer", "orcaslicer")]
        cfg.orca = first(cands)
    if cfg.freecad is None:
        cands = [shutil.which(n) for n in ("freecad", "FreeCAD")]
        cands += sorted(glob.glob(str(Path.home() / "Applications/FreeCAD*.AppImage")))
        cfg.freecad = first(cands)
    if cfg.blender is None:
        cands = []
        for r in roots:
            cands += sorted(glob.glob(str(r / "third_party/blender/blender-*/blender")), reverse=True)
        cands.append(shutil.which("blender"))
        cfg.blender = first(cands)


def load_config(start: Path | str = ".") -> Config:
    start = Path(start)
    start = start if start.is_dir() else start.parent
    cfg = Config()
    files = [Path.home() / ".config/agentcad/config.toml"]
    files += _find_project_files(start, "agentcad.toml") + _find_project_files(start, "agentcad.local.toml")
    for f in files:
        if not f.exists():
            continue
        d = tomllib.loads(f.read_text())
        cfg.sources.append(str(f))
        t = d.get("tools", {})
        for k in ("orca", "freecad", "blender"):
            if t.get(k):
                # absolute but NOT resolved: /snap/bin/<app> is a symlink to /usr/bin/snap, and the link name
                # is what selects the app (and tells us it is a snap)
                setattr(cfg, k, Path(os.path.abspath(f.parent / Path(t[k]).expanduser())))
        if t.get("stage_dir"):
            cfg.stage_dir = Path(t["stage_dir"]).expanduser()
        if d.get("vendor", {}).get("dir"):
            cfg.vendor_dir = (f.parent / Path(d["vendor"]["dir"]).expanduser()).resolve()
        cfg.printer.update(d.get("printer", {}))
        s = d.get("serve", {})
        cfg.serve_host = s.get("host", cfg.serve_host)
        cfg.serve_port = int(s.get("port", cfg.serve_port))
    for env, attr in (("AGENTCAD_ORCA", "orca"), ("AGENTCAD_FREECAD", "freecad"), ("AGENTCAD_BLENDER", "blender"),
                      ("AGENTCAD_VENDOR_DIR", "vendor_dir")):
        if os.environ.get(env):
            setattr(cfg, attr, Path(os.environ[env]).expanduser())
            cfg.sources.append(f"${env}")
    roots = [start.resolve(), *start.resolve().parents][:6] + [Path(__file__).resolve().parents[2]]
    _discover(cfg, roots)
    if cfg.vendor_dir is None:
        for r in roots:
            if (r / "vendor").is_dir():
                cfg.vendor_dir = r / "vendor"
                break
    return cfg
