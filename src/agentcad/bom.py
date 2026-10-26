"""Bill of materials: ``agentcad bom`` writes ``out/BOM.md`` from ``Design.bom()`` plus the printed parts.

Quantities and lengths come from the design, where they should be computed from the geometry (screw length =
grip + engagement, checked against the thread depth of the part it goes into), not typed by hand. Print time
and filament come from the last ``agentcad check``.
"""

from __future__ import annotations

import json
import shutil
from collections import OrderedDict

from .design import Design


def write(design: Design, log=print):
    chk = json.loads((design.out / "check.json").read_text()) if (design.out / "check.json").exists() else {}
    lines = [f"# {design.title or design.name}: bill of materials", ""]
    if not chk:
        lines += ["> Run `agentcad check` first to include print times and filament.", ""]
    elif not chk.get("passed"):
        lines += ["> **The last `agentcad check` FAILED. Do not order or print from this list yet.**", ""]
    groups: "OrderedDict[str, list]" = OrderedDict()
    for it in design.bom():
        groups.setdefault(it.group, []).append(it)
    for g, items in groups.items():
        lines += [f"## {g}", "", "| qty | item | note |", "|---|---|---|"]
        lines += [f"| {it.qty} | {it.item} | {it.note} |" for it in items]
        lines.append("")
    pr = chk.get("print", {})
    if pr:
        lines += ["## Printed parts", "", "| part | print time | filament | size (print orientation, mm) |", "|---|---|---|---|"]
        tot = 0.0
        for name, r in pr.items():
            lines.append(f"| {name} | {r.get('print_time') or '-'} | {r.get('filament_g') or '-'} g | "
                         f"{' x '.join(str(v) for v in r.get('print_bbox_mm', []))} |")
            tot += r.get("filament_g") or 0
        lines += ["", f"Filament total: {tot:.0f} g.", ""]
    out = design.out / "BOM.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    if (design.out / "site").exists():
        shutil.copy(out, design.out / "site" / "BOM.md")
    log(f"BOM: {out}")
    return out
