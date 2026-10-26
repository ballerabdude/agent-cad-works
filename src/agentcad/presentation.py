"""Export ``Design.presentation()`` for the FreeCAD and Blender pipelines, and draw callouts.

``export(design, dest)`` writes ``dest/parts/<name>.step|.stl`` and ``dest/manifest.json``. The manifest is the
only interface between this package and the scripts that run inside FreeCAD and Blender, so those scripts need
nothing but the standard library and the host application.
"""

from __future__ import annotations

import json
from pathlib import Path

import build123d as bd
from PIL import Image, ImageDraw, ImageFont

from .design import Design

FONT_CANDIDATES = ("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                   "/System/Library/Fonts/Supplemental/Arial.ttf", "C:/Windows/Fonts/arial.ttf")
FONT_BOLD = ("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf")
ACCENT, INK = (232, 112, 26), (40, 42, 46)


def export(design: Design, dest: Path, stl: bool = True, log=print) -> Path:
    (dest / "parts").mkdir(parents=True, exist_ok=True)
    man = []
    for p in design.presentation():
        step = dest / "parts" / f"{p.name}.step"
        bd.export_step(p.shape, str(step))
        if stl:
            bd.export_stl(p.shape, str(dest / "parts" / f"{p.name}.stl"), tolerance=0.01, angular_tolerance=0.08)
        bb = p.shape.bounding_box()
        man.append({"name": p.name, "step": step.name, "stl": f"{p.name}.stl", "material": p.material,
                    "print_axis": p.print_axis, "explode": list(p.explode), "label": p.label,
                    "center": [bb.center().X, bb.center().Y, bb.center().Z]})
    (dest / "manifest.json").write_text(json.dumps({"design": design.name, "title": design.title, "parts": man}, indent=1))
    log(f"presentation: {len(man)} components -> {dest}")
    return dest / "manifest.json"


def _font(cands, size):
    for f in cands:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default(size)


def _crosses(p1, p2, p3, p4):
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])
    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)


def callouts(img: Image.Image, anchors: dict[str, tuple[float, float]], labels: dict[str, str]) -> Image.Image:
    """Numbered labels in two columns beside ``img``, leader lines to the anchor points (img pixels).
    Labels keep the vertical order of their anchors; neighbours whose leaders would cross are swapped."""
    W0, H = img.size
    cw = int(W0 * 0.58)
    W = W0 + 2 * cw
    canvas = Image.new("RGB", (W, H), "white")
    canvas.paste(img.convert("RGB"), (cw, 0))
    d = ImageDraw.Draw(canvas)
    fs = max(24, H // 62)
    f, fb = _font(FONT_CANDIDATES, fs), _font(FONT_BOLD, fs)
    items = [(k, labels[k], x + cw, y) for k, (x, y) in anchors.items()]
    cx = cw + W0 / 2
    n = 1
    for col, side in ((0, sorted([i for i in items if i[2] < cx], key=lambda i: i[3])),
                      (1, sorted([i for i in items if i[2] >= cx], key=lambda i: i[3]))):
        gap, ys, last = fs * 2.6, [], -1e9
        for it in side:
            y = max(it[3], last + gap)
            ys.append(y)
            last = y
        over = (ys[-1] + fs * 2 - H) if ys else 0
        if over > 0:
            ys = [y - over for y in ys]
        ex = cw * 0.9 if col == 0 else W - cw * 0.9
        for _ in range(len(side) ** 2):
            swapped = False
            for i in range(len(side) - 1):
                a, b = side[i], side[i + 1]
                if _crosses((ex, ys[i]), (a[2], a[3]), (ex, ys[i + 1]), (b[2], b[3])):
                    side[i], side[i + 1] = b, a
                    swapped = True
            if not swapped:
                break
        for (k, label, px, py), ly in zip(side, ys):
            num = f"{n}"
            tw = d.textlength(label, font=f) + d.textlength(num + "  ", font=fb)
            tx = fs if col == 0 else W - fs
            lx = tx + tw + fs * 0.6 if col == 0 else tx - tw - fs * 0.6
            d.line([(lx, ly), (lx + (fs if col == 0 else -fs), ly), (px, py)], fill=INK, width=max(2, fs // 12))
            r = fs * 0.24
            d.ellipse([px - r, py - r, px + r, py + r], fill=ACCENT, outline="white", width=max(2, fs // 14))
            if col == 0:
                d.text((tx, ly), num, font=fb, fill=ACCENT, anchor="lm")
                d.text((tx + d.textlength(num + "  ", font=fb), ly), label, font=f, fill=INK, anchor="lm")
            else:
                d.text((tx - d.textlength(label, font=f), ly), label, font=f, fill=INK, anchor="lm")
                d.text((tx - tw, ly), num, font=fb, fill=ACCENT, anchor="lm")
            n += 1
    return canvas


def gallery(dest: Path, title: str, cards: list[tuple[str, str, list[tuple[str, str]]]], note: str = "") -> Path:
    """Static gallery page. ``cards``: (image file, caption, [(link text, href), ...])."""
    items = "".join(
        f'<figure><a href="{img}"><img src="{img}" alt="{cap}" loading="lazy"></a><figcaption>{cap}<br>'
        + " · ".join(f'<a href="{h}" download>{t}</a>' for t, h in links) + "</figcaption></figure>"
        for img, cap, links in cards)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>
<style>
:root {{ --bg:#f6f6f4; --fg:#26282c; --muted:#6b6f76; --card:#fff; --accent:#e8701a; --line:#e2e2de; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#16171a; --fg:#e8e8e6; --muted:#9a9ea6; --card:#202226; --line:#33363b; }} }}
:root[data-theme="dark"] {{ --bg:#16171a; --fg:#e8e8e6; --muted:#9a9ea6; --card:#202226; --line:#33363b; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.5 system-ui, sans-serif; }}
main {{ max-width:1200px; margin:0 auto; padding:16px; }}
nav a {{ color:var(--accent); margin-right:16px; }}
h1 {{ font-size:1.4rem; margin:12px 0 4px; }} p {{ color:var(--muted); margin:0 0 16px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(280px, 1fr)); gap:16px; }}
figure {{ margin:0; background:var(--card); border:1px solid var(--line); border-radius:10px; overflow:hidden; }}
figure img {{ width:100%; display:block; background:#fff; }}
figcaption {{ padding:10px 12px; font-size:.9rem; }} figcaption a {{ color:var(--accent); }}
</style></head><body><main><nav><a href="../">&larr; Design viewer</a></nav>
<h1>{title}</h1><p>{note}</p><div class="grid">{items}</div></main></body></html>"""
    (dest / "index.html").write_text(html)
    return dest / "index.html"
