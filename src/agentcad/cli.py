"""``agentcad``: the command line for designs written against ``agentcad.design.Design``.

    agentcad new <dir>                 start a design from the template
    agentcad doctor [<design>]         which tools are available
    agentcad check <design>            all verification gates (exit code 1 on failure)
    agentcad bom <design>              out/BOM.md
    agentcad render <design>           quick renders + viewer site (out/site)
    agentcad explode <design>          FreeCAD exploded view (out/explode, out/site/explode)
    agentcad photoreal <design>        Blender renders (out/photoreal, out/site/photoreal)
    agentcad all <design>              check, bom, render, explode*, photoreal*  (* when the tool is available)
    agentcad serve <design>            serve out/site on the LAN (default 0.0.0.0:8765)

<design> is a design file or a directory containing design.py.
"""

from __future__ import annotations

import argparse
import http.server
import shutil
import socketserver
import sys
import time
from functools import partial
from pathlib import Path

from . import __version__


def _design(path):
    from .design import load_design
    return load_design(path)


def cmd_new(a):
    d = Path(a.dir)
    if (d / "design.py").exists():
        raise SystemExit(f"{d}/design.py exists")
    d.mkdir(parents=True, exist_ok=True)
    name = d.resolve().name.replace("-", "_")
    title = a.title or name.replace("_", " ").title()
    t = (Path(__file__).parent / "data/template/design.py").read_text()
    (d / "design.py").write_text(t.replace("__NAME__", name).replace("__TITLE__", title))
    (d / "README.md").write_text(f"# {title}\n\nRequirements, decisions and check results go here.\n\n"
                                 "```bash\nagentcad check .\nagentcad all .\n```\n")
    print(f"created {d / 'design.py'}; next: agentcad check {d}")


def cmd_doctor(a):
    from .doctor import run
    sys.exit(0 if run(Path(a.design or ".")) else 1)


def cmd_check(a):
    from .check import run
    rep = run(_design(a.design), do_slice=not a.no_slice)
    sys.exit(0 if rep["passed"] else 1)


def cmd_bom(a):
    from .bom import write
    from .render import update_links
    d = _design(a.design)
    write(d)
    update_links(d)


def cmd_render(a):
    from .render import run, update_links
    d = _design(a.design)
    run(d)
    update_links(d)


def cmd_explode(a):
    from .freecad import run
    from .render import update_links
    d = _design(a.design)
    run(d)
    update_links(d)


def cmd_photoreal(a):
    from .blender import run
    from .render import update_links
    d = _design(a.design)
    run(d, samples=a.samples, pct=a.pct, only=a.shots.split(",") if a.shots else None)
    update_links(d)


def cmd_all(a):
    from . import bom, check, render
    from .config import load_config
    d = _design(a.design)
    cfg = load_config(d.path)
    t = time.time()
    rep = check.run(d, cfg, do_slice=not a.no_slice)
    bom.write(d)
    render.run(d)
    if not rep["passed"]:
        print("checks failed: skipping the exploded view and photoreal renders (fix the design first)")
        sys.exit(1)
    if cfg.freecad and shutil.which("xvfb-run"):
        from . import freecad
        freecad.run(d, cfg)
    else:
        print("FreeCAD or Xvfb not available: skipping the exploded view")
    if cfg.blender:
        from . import blender
        blender.run(d, cfg, samples=a.samples)
    else:
        print("Blender not available: skipping photoreal renders")
    bom.write(d)
    render.update_links(d)
    print(f"all done in {time.time() - t:.0f} s: {d.out / 'site'}  (agentcad serve {a.design})")


def cmd_serve(a):
    from .config import load_config
    p = Path(a.design)
    site = p if (p / "index.html").exists() else _design(p).out / "site"
    cfg = load_config(p)
    port = a.port or cfg.serve_port
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer((cfg.serve_host, port), handler) as srv:
        print(f"serving {site} on http://{cfg.serve_host}:{port}/  (Ctrl-C to stop)")
        srv.serve_forever()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="agentcad", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"agentcad {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("new", help="start a design from the template"); s.add_argument("dir"); s.add_argument("--title")
    s.set_defaults(fn=cmd_new)
    s = sub.add_parser("doctor", help="check the toolchain"); s.add_argument("design", nargs="?"); s.set_defaults(fn=cmd_doctor)
    for name, fn, h in (("check", cmd_check, "run every verification gate"), ("bom", cmd_bom, "write out/BOM.md"),
                        ("render", cmd_render, "quick renders and the viewer site"),
                        ("explode", cmd_explode, "FreeCAD exploded view"),
                        ("photoreal", cmd_photoreal, "Blender photoreal renders"),
                        ("all", cmd_all, "everything, in order"), ("serve", cmd_serve, "serve out/site")):
        s = sub.add_parser(name, help=h)
        s.add_argument("design")
        if name in ("check", "all"):
            s.add_argument("--no-slice", action="store_true", help="skip OrcaSlicer (faster)")
        if name in ("photoreal", "all"):
            s.add_argument("--samples", type=int, default=512)
        if name == "photoreal":
            s.add_argument("--pct", type=int, default=100, help="resolution percentage (40 for a quick look)")
            s.add_argument("--shots", help="comma-separated shot names (default: all)")
        if name == "serve":
            s.add_argument("--port", type=int)
        s.set_defaults(fn=fn)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
