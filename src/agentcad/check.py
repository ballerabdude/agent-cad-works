"""Verification gates. ``agentcad check`` runs all of them; a design is done only when every gate passes.

Gate 1, interference (every state from ``Design.states()``):
  printed vs hardware, printed vs printed, hardware vs hardware, and every keep-out zone vs everything else.
  Intended overlaps are declared on the design (``expected_contacts``, ``hardware_overlaps``, ``keepouts``).
Gate 2, printability (every printed part and tool, in its print orientation):
  one valid closed solid (kernel), watertight + consistent + manifold mesh (trimesh and manifold3d, independent
  of the kernel), no floating islands (layer analysis), and a successful OrcaSlicer slice without warnings.
Gate 3, design checks: whatever ``Design.checks()`` returns (vendor-model fit, hole alignment, clearances).

Outputs go to ``<design>/out/``: ``check.json``, ``print/<part>.stl|.step`` (print-oriented) and
``slice/<part>/plate_1.gcode``.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path

import build123d as bd

from . import kernel, layers, meshcheck
from .config import Config, load_config
from .design import CheckResult, Design
from .slicer import slice_stl


def interference(design: Design, log=print) -> dict:
    """Sweep every state. Returns {"overlaps": {pair@state: mm3}, "states": n}."""
    found = {}
    states = design.states()
    exp = {tuple(p) for p in design.expected_contacts}
    hw_ok = {frozenset(p) for p in design.hardware_overlaps}
    for st in states:
        tag = f"@{st}" if st is not None else ""
        printed, hw = design.printed(st), design.hardware(st)
        keep = design.keepouts
        for pn, p in printed.items():
            for hn, h in hw.items():
                if (pn, hn) in exp:
                    continue
                if hn in keep and pn in keep[hn]:
                    continue
                v = kernel.overlap_volume(p, h)
                if v > 1e-3:
                    found[f"{pn} x {hn}{tag}"] = round(v, 3)
        names = list(printed)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                v = kernel.overlap_volume(printed[a], printed[b])
                if v > 1e-3:
                    found[f"{a} x {b}{tag}"] = round(v, 3)
        hn_ = list(hw)
        for i, a in enumerate(hn_):
            for b in hn_[i + 1:]:
                if frozenset((a, b)) in hw_ok:
                    continue
                if a in keep and b in keep[a] or b in keep and a in keep[b]:
                    continue
                v = kernel.overlap_volume(hw[a], hw[b])
                if v > 1e-3:
                    found[f"{a} x {b}{tag}"] = round(v, 3)
        log(f"  interference @ state {st}: {len([k for k in found if k.endswith(tag)])} overlaps")
    return {"states": [str(s) for s in states], "overlaps": found}


def printability(design: Design, cfg: Config, do_slice: bool = True, log=print) -> dict:
    """Export each printed part and tool in print orientation and run the printability gates on it."""
    st = design.states()[0]
    parts = {**design.printed(st), **design.tools()}
    pdir, sdir = design.out / "print", design.out / "slice"
    pdir.mkdir(parents=True, exist_ok=True)
    rep = {}
    for name, s in parts.items():
        p = kernel.rotate_xyz(s, design.print_rotation.get(name, (0, 0, 0)))
        bb = p.bounding_box()
        p = p.translate((-bb.min.X, -bb.min.Y, -bb.min.Z))
        m = kernel.measure(p)
        pts, tris, refs = kernel.tessellate(p, 0.01, 25.0)
        mc = meshcheck.check_mesh(pts, tris, refs, exact_volume=m["volume"], drop_degenerate=True)
        stl = pdir / f"{name}.stl"
        meshcheck.write_stl(pts, tris, str(stl))
        bd.export_step(p, str(pdir / f"{name}.step"))
        bb = p.bounding_box()
        isl = layers.analyse(stl)
        r = {"kernel_valid": m["kernel_valid"], "solids": m["solids"], "closed_solid": m["closed_solid"],
             "volume_cm3": round(m["volume"] / 1000, 2),
             "print_bbox_mm": [round(bb.size.X, 1), round(bb.size.Y, 1), round(bb.size.Z, 1)],
             "watertight": mc["watertight"], "winding_ok": mc["winding_consistent"], "manifold3d_ok": mc["manifold3d_ok"],
             "triangles": mc["triangles"], "islands": len(isl["islands"]), "island_detail": isl["islands"][:5]}
        if do_slice:
            r.update(slice_stl(stl, sdir / name, cfg))
        r["passed"] = bool(r["kernel_valid"] and r["solids"] == 1 and r["closed_solid"] and r["watertight"]
                           and r["winding_ok"] and r["manifold3d_ok"] and r["islands"] == 0
                           and (not do_slice or r.get("slice", "").startswith(("Success", "skipped")))
                           and not r.get("slicer_warning"))
        log(f"  {name:22s} {'PASS' if r['passed'] else 'FAIL'}  islands={r['islands']}  "
            f"{r.get('slice', '')} {r.get('print_time') or ''} {r.get('filament_g') or ''}{' g' if r.get('filament_g') else ''}"
            f"{'  WARNING: ' + r['slicer_warning'] if r.get('slicer_warning') else ''}")
        rep[name] = r
    return rep


def design_checks(design: Design, log=print) -> dict:
    out = {}
    for name, fn in design.checks():
        t = time.time()
        try:
            r = fn()
            if isinstance(r, bool):
                r = CheckResult(name, r)
            elif isinstance(r, dict):
                r = CheckResult(name, bool(r.get("passed")), r)
        except Exception as e:  # noqa: BLE001 - a crashing check is a failing check
            r = CheckResult(name, False, {"error": repr(e)})
        out[name] = {"passed": r.passed, **r.detail}
        log(f"  {name:40s} {'PASS' if r.passed else 'FAIL'}  ({time.time() - t:.1f} s)")
    return out


def run(design: Design, cfg: Config | None = None, do_slice: bool = True, log=print) -> dict:
    cfg = cfg or load_config(design.path)
    design.out.mkdir(parents=True, exist_ok=True)
    log(f"[1/3] interference sweep over {len(design.states())} states")
    inter = interference(design, log)
    log("[2/3] printability")
    prin = printability(design, cfg, do_slice, log)
    log("[3/3] design checks")
    dchk = design_checks(design, log)
    rep = {"design": design.name, "info": design.info(), "interference": inter, "print": prin, "design_checks": dchk}
    rep["passed"] = (not inter["overlaps"] and all(r["passed"] for r in prin.values())
                     and all(r["passed"] for r in dchk.values()))
    (design.out / "check.json").write_text(json.dumps(rep, indent=1, default=_json_default))
    log(("PASS" if rep["passed"] else "FAIL") + f": {design.out / 'check.json'}")
    if inter["overlaps"]:
        for k, v in inter["overlaps"].items():
            log(f"  overlap {k}: {v} mm3")
    return rep


def _json_default(o):
    if isinstance(o, float) and math.isinf(o):
        return "inf"
    return str(o)
