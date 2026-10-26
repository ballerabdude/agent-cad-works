"""Quick renders (matplotlib, seconds) and the design's viewer site.

``agentcad render`` writes ``out/site/``: ``index.html`` (phone-friendly, three.js STL viewer), ``manifest.json``,
print-oriented STL/STEP of every printed part, ``assembly.stl`` and ``renders/{assembly,parts,details}.png``. The
site links to the exploded-view and photoreal galleries when those exist. Serve it with ``agentcad serve``.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from . import kernel  # noqa: E402
from .design import Design  # noqa: E402

COLORS = {"printed": (0.93, 0.48, 0.13), "aluminium": (0.78, 0.80, 0.83), "steel": (0.50, 0.53, 0.57),
          "chrome": (0.72, 0.72, 0.74), "black_oxide": (0.15, 0.15, 0.16), "rubber": (0.12, 0.12, 0.12),
          "black": (0.12, 0.12, 0.13), "bright": (0.85, 0.85, 0.87), "seal": (0.70, 0.12, 0.10)}
LIGHT = np.array([-0.45, -0.75, 0.5]) / np.linalg.norm([-0.45, -0.75, 0.5])


def mesh_of(shape, chord=0.1):
    pts, tris, _ = kernel.tessellate(shape, chord, 20.0)
    return trimesh.Trimesh(pts, tris, process=True)


def _clip(m, zlim):
    if not zlim:
        return m
    try:
        m = trimesh.intersections.slice_mesh_plane(m, (0, 0, 1), (0, 0, zlim[0]))
        return trimesh.intersections.slice_mesh_plane(m, (0, 0, -1), (0, 0, zlim[1]))
    except Exception:  # noqa: BLE001 - mesh entirely outside the window
        return None


def draw(ax, items, zlim=None, view=(18, -55), title=""):
    tri, cols = [], []
    for m, col in items:
        m = _clip(m, zlim)
        if m is None or len(m.faces) == 0:
            continue
        shade = 0.35 + 0.65 * np.clip(np.abs(m.face_normals @ LIGHT), 0, 1)
        tri.append(m.triangles)
        cols.append(shade[:, None] * np.array(col)[None, :])
    if not tri:
        return
    T, C = np.vstack(tri), np.vstack(cols)
    ax.add_collection3d(Poly3DCollection(T, facecolors=np.clip(C, 0, 1), edgecolors="none"))
    lo, hi = T.reshape(-1, 3).min(0), T.reshape(-1, 3).max(0)
    ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(tuple(np.maximum(hi - lo, 1e-6)))
    ax.view_init(*view)
    ax.set_axis_off()
    ax.set_title(title, fontsize=10)


def run(design: Design, log=print) -> Path:
    site = design.out / "site"
    ren = site / "renders"
    ren.mkdir(parents=True, exist_ok=True)
    show = design.presentation()
    items = {p.name: (mesh_of(p.shape, 0.08 if p.material == "printed" else 0.2), COLORS.get(p.material, (0.6, 0.6, 0.6)))
             for p in show}
    fig = plt.figure(figsize=(9, 12), dpi=120)
    draw(fig.add_subplot(1, 2, 1, projection="3d"), items.values(), view=(12, 55), title="front")
    draw(fig.add_subplot(1, 2, 2, projection="3d"), items.values(), view=(12, -125), title="back")
    fig.tight_layout(); fig.savefig(ren / "assembly.png"); plt.close(fig)
    det = design.render_details()
    if det:
        fig = plt.figure(figsize=(14, 6 * ((len(det) + 1) // 2)), dpi=110)
        for i, d in enumerate(det):
            its = [v for k, v in items.items() if k not in d.get("hide", ())]
            draw(fig.add_subplot((len(det) + 1) // 2, 2, i + 1, projection="3d"), its, zlim=d.get("z"),
                 view=d.get("view", (18, -55)), title=d.get("title", ""))
        fig.tight_layout(); fig.savefig(ren / "details.png"); plt.close(fig)
    st = design.states()[0]
    parts = {**design.printed(st), **design.tools()}
    n = len(parts)
    rows = 1 if n <= 4 else 2
    fig = plt.figure(figsize=(4.5 * -(-n // rows), 5 * rows), dpi=110)
    for i, (name, s) in enumerate(parts.items()):
        draw(fig.add_subplot(rows, -(-n // rows), i + 1, projection="3d"), [(mesh_of(s, 0.08), COLORS["printed"])],
             view=(24, -60), title=name)
    fig.tight_layout(); fig.savefig(ren / "parts.png"); plt.close(fig)
    trimesh.util.concatenate([m for m, _ in items.values()]).export(site / "assembly.stl")
    chk = json.loads((design.out / "check.json").read_text()) if (design.out / "check.json").exists() else {}
    entries = []
    for name in parts:
        files = []
        for ext in ("stl", "step"):
            src = design.out / "print" / f"{name}.{ext}"
            if src.exists():
                shutil.copy(src, site / f"{name}.{ext}")
                files.append(f"{name}.{ext}")
        c = chk.get("print", {}).get(name, {})
        entries.append({"name": name, "stl": f"{name}.stl" if files else "assembly.stl", "files": files,
                        "passed": c.get("passed", False), "print_time": c.get("print_time"),
                        "filament_g": c.get("filament_g"),
                        "stats": {k: c.get(k) for k in ("volume_cm3", "print_bbox_mm", "kernel_valid", "watertight",
                                                        "manifold3d_ok", "islands", "slice", "print_time",
                                                        "filament_g", "slicer_warning") if k in c}})
    links = [{"href": "assembly.stl", "text": "assembly.stl"}]
    for sub, text in (("explode", "Exploded view (FreeCAD)"), ("photoreal", "Photoreal renders"), ("BOM.md", "BOM")):
        if (site / sub).exists():
            links.append({"href": f"{sub}/" if "." not in sub else sub, "text": text})
    (site / "manifest.json").write_text(json.dumps({"title": design.title or design.name, "passed": chk.get("passed", False),
                                                    "info": design.info(), "parts": entries, "links": links},
                                                   indent=1, default=str))
    shutil.copy(Path(__file__).parent / "data" / "viewer.html", site / "index.html")
    log(f"site: {site}")
    return site


def update_links(design: Design) -> None:
    """Refresh the viewer's links after the exploded view, photoreal renders or BOM were (re)generated."""
    site = design.out / "site"
    mf = site / "manifest.json"
    if not mf.exists():
        return
    man = json.loads(mf.read_text())
    links = [{"href": "assembly.stl", "text": "assembly.stl"}]
    for sub, text in (("explode", "Exploded view (FreeCAD)"), ("photoreal", "Photoreal renders"), ("BOM.md", "BOM")):
        if (site / sub).exists():
            links.append({"href": f"{sub}/" if "." not in sub else sub, "text": text})
    man["links"] = links
    mf.write_text(json.dumps(man, indent=1, default=str))
