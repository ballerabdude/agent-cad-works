"""OrcaSlicer from the command line: flattened profiles, slicing, print time and filament.

Why profiles are flattened: the OrcaSlicer CLI resolves only one level of ``inherits`` when profiles are passed
with ``--load-settings``. Values further up the chain silently fall back to built-in defaults. On the Bambu X1C
that made the printable height 100 mm instead of 250, and taller parts were rejected with "no object fully
inside it". The machine profile is therefore merged into one file. Process and filament profiles are passed as
shipped, because flattening them broke the CLI's compatibility checks.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from .config import Config


def flatten(profiles: Path, vendor: str, kind: str, name: str, out_dir: Path) -> Path:
    """Merge a profile and its ``inherits`` chain into one standalone JSON."""
    chain, cur = [], name
    while cur:
        d = json.loads((profiles / vendor / kind / f"{cur}.json").read_text())
        chain.append(d)
        cur = d.get("inherits")
    merged: dict = {}
    for d in reversed(chain):
        merged.update(d)
    merged.pop("inherits", None)
    merged["name"] = name
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{kind}_{re.sub(r'[^A-Za-z0-9_.-]+', '_', name)}.json"
    p.write_text(json.dumps(merged, indent=1))
    return p


def slice_stl(stl: Path, out_dir: Path, cfg: Config, timeout: int = 900) -> dict:
    """Slice one STL as it lies (no auto-orient). Returns status, print time, filament (g) and any warning."""
    if not cfg.orca or not cfg.orca_profiles:
        return {"slice": "skipped (OrcaSlicer not configured; see `agentcad doctor`)"}
    pr = cfg.printer
    prof = cfg.orca_profiles
    machine = flatten(prof, pr["vendor"], "machine", pr["machine"], out_dir.parent / "_profiles")
    process = prof / pr["vendor"] / "process" / f"{pr['process']}.json"
    filament = prof / pr["vendor"] / "filament" / f"{pr['filament']}.json"
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("*"):
        if f.is_file():
            f.unlink()
    q = subprocess.run([str(cfg.orca), "--datadir", str(out_dir.parent / "_datadir"),
                        "--load-settings", f"{machine};{process}", "--load-filaments", str(filament),
                        "--arrange", "1", "--orient", "0", "--slice", "0", "--outputdir", str(out_dir), str(stl)],
                       capture_output=True, text=True, timeout=timeout)
    res = json.loads((out_dir / "result.json").read_text()) if (out_dir / "result.json").exists() else {}
    g = out_dir / "plate_1.gcode"
    if not g.exists():
        return {"slice": f"failed rc={q.returncode}", "slicer_log": (q.stdout + q.stderr)[-400:]}
    t = g.read_text(errors="replace")
    mt = re.search(r"total estimated time: (.+)", t)
    mf = re.search(r"; filament used \[cm3\] = ([\d.]+)", t)
    return {"slice": res.get("error_string", "Success."),
            "print_time": mt.group(1).strip() if mt else None,
            "filament_g": round(float(mf.group(1)) * float(pr.get("filament_density", 1.27)), 1) if mf else None,
            "slicer_warning": "; ".join(p.get("warning_message", "") for p in res.get("sliced_plates", [])).strip("; ")}
