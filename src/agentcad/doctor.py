"""``agentcad doctor``: which tools were found, their versions, and whether each pipeline can run."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .config import load_config


def _ver(cmd, timeout=60):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (p.stdout + p.stderr).strip().splitlines()
    except Exception as e:  # noqa: BLE001
        return [f"error: {e}"]


def run(start: Path, log=print) -> bool:
    import build123d
    import OCP  # noqa: F401
    cfg = load_config(start)
    ok = True
    log(f"config files: {cfg.sources or 'none (defaults)'}")
    log(f"build123d {build123d.__version__} (OCCT via OCP)                    [check, render: always available]")
    log(f"printer: {cfg.printer['machine']} / {cfg.printer['process']} / {cfg.printer['filament']}")
    if cfg.orca and cfg.orca_profiles:
        prof = cfg.orca_profiles / cfg.printer["vendor"]
        missing = [k for k in ("machine", "process", "filament")
                   if not (prof / k / f"{cfg.printer[k]}.json").exists()]
        log(f"OrcaSlicer: {cfg.orca}  profiles: {prof}" + (f"  MISSING profiles: {missing}" if missing else ""))
        ok &= not missing
    else:
        log("OrcaSlicer: NOT FOUND  -> `agentcad check` skips slicing (set [tools] orca)")
    log(f"Xvfb: {'found' if shutil.which('xvfb-run') else 'NOT FOUND (needed for FreeCAD renders)'}")
    if cfg.freecad:
        v = [l for l in _ver([str(cfg.freecad.with_name('freecad.cmd')) if cfg.freecad_is_snap else str(cfg.freecad),
                              "--version"]) if "FreeCAD" in l]
        log(f"FreeCAD: {cfg.freecad} {v[0] if v else ''}{'  (snap: staging in ' + str(cfg.stage_dir) + ')' if cfg.freecad_is_snap else ''}")
    else:
        log("FreeCAD: NOT FOUND  -> `agentcad explode` unavailable (set [tools] freecad)")
    if cfg.blender:
        v = _ver([str(cfg.blender), "--version"])
        log(f"Blender: {cfg.blender} {v[0] if v else ''}")
    else:
        log("Blender: NOT FOUND  -> `agentcad photoreal` unavailable (set [tools] blender)")
    log(f"vendor dir: {cfg.vendor_dir or 'none (vendor STEP checks will skip)'}")
    return ok
