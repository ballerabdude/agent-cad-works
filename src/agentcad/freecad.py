"""Exploded view in FreeCAD: ``agentcad explode``.

Builds two FreeCAD documents (assembled and exploded, with dashed explosion lines and finishes) from
``Design.presentation()`` and renders orthographic views with numbered callouts. Outputs ``out/explode/``:
``<name>_exploded.FCStd``, ``<name>_assembled.FCStd``, ``final/*.png`` and a gallery at ``out/site/explode/``.

How it runs, and why (each point was a real failure first):

* FreeCAD's GUI is needed to render, so it runs under Xvfb with a macro (``data/freecad_explode.FCMacro``).
* The FreeCAD **snap** cannot read macros or files under paths outside your home (``/mnt``, ``/tmp``), and inside
  the snap ``~`` is the snap's private home. Inputs are therefore staged in ``Config.stage_dir`` (default
  ``~/agentcad-stage``, not hidden) with absolute paths written into the macro.
* The macro must end with ``os._exit(0)``; any exception before that would leave FreeCAD idle until a timeout.
* Navigation animation is turned off and the camera is measured after every move. With animation on, the
  camera was read mid-move and the views came out 10-20 degrees off.
* Callouts go only on visible faces: an ID pass renders each part in a flat emissive colour, and an anchor
  must sit in a patch of its own colour.
* ``saveImage`` does not reproduce the viewport's framing (a portrait image is scaled by width/height), so the
  viewport-to-image mapping is fitted per view from the ID render, not assumed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from .config import Config, load_config
from .design import Design
from .presentation import callouts, export, gallery

VIEWS = [("exploded_front", True, (-0.55, -1.0, -0.42), "Exploded, front"),
         ("exploded_back", True, (0.75, 1.0, -0.40), "Exploded, back"),
         ("exploded_side", True, (-1.0, 0.0, 0.0), "Exploded, side"),
         ("assembled_front", False, (-0.55, -1.0, -0.42), "Assembled, front"),
         ("assembled_back", False, (0.75, 1.0, -0.40), "Assembled, back")]
CALLOUT_VIEWS = ("exploded_front", "exploded_back")


def run(design: Design, cfg: Config | None = None, timeout: int = 1800, log=print) -> Path:
    cfg = cfg or load_config(design.path)
    if not cfg.freecad:
        raise SystemExit("FreeCAD not found: set [tools] freecad in agentcad.local.toml (see `agentcad doctor`)")
    out = design.out / "explode"
    if out.exists():
        shutil.rmtree(out)
    man_path = export(design, out, stl=False, log=log)
    man = json.loads(man_path.read_text())
    lo = np.min([[c - 1 for c in p["center"]] for p in man["parts"]], axis=0)   # rough model extent
    hi = np.max([[c + 1 for c in p["center"]] for p in man["parts"]], axis=0)
    tall = (hi[2] - lo[2]) > 1.2 * max(hi[0] - lo[0], hi[1] - lo[1])
    window = (2600, 3800) if tall else (3800, 2600)
    job = {"doc_name": "".join(ch for ch in design.name.title() if ch.isalnum()) or "Design",
           "window": window, "scale": 3, "center": [float((lo[0] + hi[0]) / 2), float((lo[1] + hi[1]) / 2)],
           "z_range": [float(lo[2]), float(hi[2])],
           "views": [{"name": n, "exploded": e, "direction": d} for n, e, d, _ in VIEWS]}
    stage = cfg.stage_dir / design.name if cfg.freecad_is_snap else out
    if stage != out:
        if stage.exists():
            shutil.rmtree(stage)
        shutil.copytree(out, stage)
    (stage / "job.json").write_text(json.dumps(job, indent=1))
    macro = (Path(__file__).parent / "data/freecad_explode.FCMacro").read_text().replace("__ROOT__", str(stage))
    (stage / "explode.FCMacro").write_text(macro)
    log(f"FreeCAD ({cfg.freecad}) under Xvfb, staged in {stage}")
    subprocess.run(["xvfb-run", "-a", "-s", f"-screen 0 {window[0]}x{window[1]}x24", str(cfg.freecad),
                    str(stage / "explode.FCMacro")], env={**_env(), "QT_QPA_PLATFORM": "xcb"},
                   capture_output=True, timeout=timeout)
    logtxt = (stage / "explode.log").read_text() if (stage / "explode.log").exists() else ""
    if "done" not in logtxt.split("\n")[-2:]:
        raise SystemExit("FreeCAD macro did not finish:\n" + logtxt[-2000:])
    if stage != out:
        for f in list(stage.glob("*.FCStd")) + list(stage.glob("render_*.png")) + [stage / "views.json", stage / "explode.log"]:
            shutil.copy(f, out / f.name)
    finish(design, out, log)
    return out


def _env():
    import os
    return dict(os.environ)


def _fit_mapping(view, idim):
    """Viewport -> ID-image pixels, fitted per axis from the largest labelled part's samples vs its pixels."""
    w, h = view["viewport"]
    a = np.asarray(idim)
    best = None
    for p in view["points"].values():
        ys, xs = np.nonzero(np.all(a == np.array(p["id"]), axis=2))
        if len(xs) > (0 if best is None else len(best[1])):
            best = (p, xs, ys)
    p, xs, ys = best
    smp = np.array(p["samples"])
    sx = smp[:, 0]
    sy = (h - smp[:, 1]) if view["y_up"] else smp[:, 1]
    kx = (xs.max() - xs.min()) / max(1e-9, sx.max() - sx.min())
    ky = (ys.max() - ys.min()) / max(1e-9, sy.max() - sy.min())
    bx, by = xs.min() - kx * sx.min(), ys.min() - ky * sy.min()
    return lambda x, y: (kx * x + bx, ky * ((h - y) if view["y_up"] else y) + by)


def _anchors(view, idim):
    to_px = _fit_mapping(view, idim)
    W, H = idim.size
    px = idim.load()
    out = {}
    for name, p in view["points"].items():
        want, (cx, cy), best = tuple(p["id"]), to_px(*p["center"]), None
        for r in (3, 1, 0):                      # thin parts (belts) only pass with a small neighbourhood
            for x, y in p["samples"]:
                ix, iy = (int(round(c)) for c in to_px(x, y))
                if 3 <= ix < W - 3 and 3 <= iy < H - 3 and all(
                        px[ix + dx, iy + dy] == want for dx in (-r, 0, r) for dy in (-r, 0, r)):
                    dist = (ix - cx) ** 2 + (iy - cy) ** 2
                    if best is None or dist < best[0]:
                        best = (dist, ix, iy)
            if best:
                break
        if best:
            out[name] = (best[1], best[2])
    return out


def finish(design: Design, out: Path, log=print) -> None:
    views = json.loads((out / "views.json").read_text())
    fin = out / "final"
    fin.mkdir(exist_ok=True)
    cards = []
    for name, _, _, title in VIEWS:
        view = views[name]
        tr = Image.open(out / f"render_{name}_transparent.png").convert("RGBA")
        x0, y0, x1, y1 = tr.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
        m = int(0.06 * max(x1 - x0, y1 - y0))
        box = (x0 - m, y0 - m, x1 + m, y1 + m)
        for bg in ("transparent", "white"):
            im = Image.open(out / f"render_{name}_{bg}.png").convert("RGBA")
            canvas = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0) if bg == "transparent" else (255, 255, 255, 255))
            canvas.paste(im.crop((max(box[0], 0), max(box[1], 0), box[2], box[3])), (max(-box[0], 0), max(-box[1], 0)))
            canvas.resize((canvas.width // 2, canvas.height // 2), Image.LANCZOS).save(fin / f"{name}_{bg}.png")
        links = [("PNG", f"{name}_white.png"), ("transparent PNG", f"{name}_transparent.png")]
        if name in CALLOUT_VIEWS:
            idim = Image.open(out / f"render_{name}_id.png").convert("RGB")
            anchors = _anchors(view, idim)
            missing = sorted(set(view["points"]) - set(anchors))
            if missing:
                log(f"  {name}: hidden from this view, left unlabelled: {', '.join(missing)}")
            white = Image.open(out / f"render_{name}_white.png").convert("RGB")
            sx, sy = white.width / idim.width, white.height / idim.height
            pts = {k: (a[0] * sx - box[0], a[1] * sy - box[1]) for k, a in anchors.items()}
            img = white.crop(box)
            labels = {k: view["points"][k]["label"] for k in pts}
            c = callouts(img, pts, labels)
            c.resize((c.width // 2, c.height // 2), Image.LANCZOS).save(fin / f"{name}_callouts.png")
            cards.append((f"{name}_callouts.png", title + ", with callouts", [("PNG", f"{name}_callouts.png")]))
        cards.append((f"{name}_white.png", title, links))
    web = design.out / "site" / "explode"
    web.mkdir(parents=True, exist_ok=True)
    for f in fin.iterdir():
        shutil.copy(f, web / f.name)
    docs = []
    for f in out.glob("*.FCStd"):
        shutil.copy(f, web / f.name)
        docs.append(f.name)
    gallery(web, f"{design.title or design.name}: exploded view", cards,
            "FreeCAD documents: " + " · ".join(f'<a href="{d}" download>{d}</a>' for d in docs))
    log(f"exploded view: {fin}  gallery: {web}")
