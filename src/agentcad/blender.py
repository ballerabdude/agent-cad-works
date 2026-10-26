"""Photoreal renders in Blender: ``agentcad photoreal``.

Renders ``Design.shots()`` from ``Design.presentation()`` with Cycles (OptiX/CUDA when a GPU is available) and
writes ``out/photoreal/final/``: a JPEG on white with a soft floor shadow and a transparent PNG per shot, plus
numbered-callout versions of the shots that ask for them. The gallery lands in ``out/site/photoreal/``.

Lessons built in:

* Exposure: AgX view transform, studio gradient world at 0.15, key light 16 W per m^2 of camera distance. The
  first attempt (world 0.55, lights 16x brighter) rendered a black actuator white.
* Shadows: a shadow-catcher floor; fill and top lights cast no shadow; the key is high so shadows fall short.
  Post-processing fades the shadow towards the crop edges, because a shadow that runs out of the camera frame
  otherwise ends in a hard line.
* Callouts: a label's anchor is a mesh vertex that a ray from the camera reaches first, nearest the part's
  projected centre. Parts with no visible vertex are left unlabelled (and reported).
* Bounding boxes from STEP solids can be 1e-4 off a round number; any threshold on them needs a margin.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

import numpy as np
from PIL import Image

from .config import Config, load_config
from .design import Design
from .presentation import callouts, export, gallery


def run(design: Design, cfg: Config | None = None, samples: int = 512, pct: int = 100, only: list[str] | None = None,
        log=print) -> Path:
    cfg = cfg or load_config(design.path)
    if not cfg.blender:
        raise SystemExit("Blender not found: set [tools] blender in agentcad.local.toml (see `agentcad doctor`)")
    out = design.out / "photoreal"
    raw = out / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    man = export(design, out / "presentation", stl=True, log=log)
    shots = [s for s in design.shots() if not only or s.name in only]
    job = {"manifest": str(man), "parts_dir": str(out / "presentation" / "parts"), "out": str(raw),
           "samples": samples, "pct": pct, "shots": [asdict(s) for s in shots]}
    (out / "job.json").write_text(json.dumps(job, indent=1))
    script = Path(__file__).parent / "data" / "blender_scene.py"
    log(f"Blender ({cfg.blender}): {len(shots)} shots, {samples} samples, {pct} % resolution")
    p = subprocess.run([str(cfg.blender), "-b", "-P", str(script), "--", str(out / "job.json")],
                       capture_output=True, text=True)
    for line in p.stdout.splitlines():
        if line.startswith(("RENDER DEVICE", "DONE", "no visible anchor")):
            log("  " + line)
    if p.returncode != 0 or "Traceback" in p.stdout + p.stderr:
        raise SystemExit("Blender failed:\n" + (p.stdout + p.stderr)[-3000:])
    finish(design, out, shots, log)
    return out


def _feather_shadow(im: Image.Image, box) -> Image.Image:
    """Fade semi-transparent (shadow) pixels to zero towards the crop box edges; opaque pixels untouched."""
    a = np.asarray(im).astype(np.float32)
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    x0, y0, x1, y1 = box
    edge = np.minimum.reduce([xx - x0, x1 - 1 - xx, yy - y0, y1 - 1 - yy]).astype(np.float32)
    fade = np.clip(edge / (0.10 * min(x1 - x0, y1 - y0)), 0, 1) ** 1.5
    alpha = a[..., 3] / 255.0
    shadow = alpha < 0.98
    alpha[shadow] *= fade[shadow]
    a[..., 3] = alpha * 255
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def finish(design: Design, out: Path, shots, log=print) -> None:
    raw, fin = out / "raw", out / "final"
    fin.mkdir(exist_ok=True)
    man = json.loads((out / "presentation" / "manifest.json").read_text())
    labels = {p["name"]: p["label"] for p in man["parts"] if p["label"]}
    cards = []
    for s in shots:
        im = Image.open(raw / f"{s.name}.png").convert("RGBA")
        bbox = im.getchannel("A").point(lambda a: 255 if a > 245 else 0).getbbox()     # the model, not its shadow
        m = int(0.07 * max(bbox[2] - bbox[0], bbox[3] - bbox[1]))
        box = (max(0, bbox[0] - m), max(0, bbox[1] - m), min(im.width, bbox[2] + m), min(im.height, bbox[3] + m))
        im = _feather_shadow(im, box)
        white = Image.new("RGBA", im.size, (255, 255, 255, 255))
        white.alpha_composite(im)
        w = white.convert("RGB").crop(box)
        w.save(fin / f"{s.name}.jpg", quality=93)
        im.crop(box).save(fin / f"{s.name}_transparent.png")
        if s.callouts and (raw / f"{s.name}_anchors.json").exists():
            a = json.loads((raw / f"{s.name}_anchors.json").read_text())["anchors"]
            pts = {k: (v["px"][0] - box[0], v["px"][1] - box[1]) for k, v in a.items() if k in labels}
            missing = sorted(set(labels) - set(pts) - set(s.hidden))
            if missing:
                log(f"  {s.name}: hidden from this view, left unlabelled: {', '.join(missing)}")
            callouts(w, pts, {k: labels[k] for k in pts}).save(fin / f"{s.name}_callouts.jpg", quality=93)
            cards.append((f"{s.name}_callouts.jpg", s.title + ", with callouts", [("JPEG", f"{s.name}_callouts.jpg")]))
        cards.append((f"{s.name}.jpg", s.title, [("JPEG", f"{s.name}.jpg"), ("transparent PNG", f"{s.name}_transparent.png")]))
    web = design.out / "site" / "photoreal"
    web.mkdir(parents=True, exist_ok=True)
    for f in fin.iterdir():
        shutil.copy(f, web / f.name)
    gallery(web, f"{design.title or design.name}: photoreal renders", cards, "Blender, Cycles.")
    log(f"photoreal: {fin}  gallery: {web}")
