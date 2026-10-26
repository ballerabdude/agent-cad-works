"""The interface every design implements, and the loader the CLI uses.

A design is a Python file that defines one subclass of :class:`Design` (or a module-level ``DESIGN``
instance). Everything else (checks, slicing, renders, exploded views, BOM) is driven from it, so a design
never needs its own scripts. See ``docs/design-interface.md`` for the full contract and
``examples/zlift/design.py`` for a complete one.

Coordinates are millimetres. ``state`` is whatever describes a pose of the mechanism (a carriage height,
a joint angle, a dict); :meth:`Design.states` lists the poses the interference sweep must cover.
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import build123d as bd

# Presentation materials understood by the FreeCAD and Blender pipelines.
MATERIALS = ("printed", "aluminium", "steel", "chrome", "black_oxide", "rubber", "black", "bright", "seal")


@dataclass
class ShowPart:
    """One component of the presentation model (exploded views, photoreal renders).

    ``explode`` is the offset in mm in the exploded view. ``label`` is the callout text (``None`` = no callout).
    ``print_axis`` ("X", "Y" or "Z", world axis) adds 0.2 mm layer lines to a ``printed`` material.
    """
    name: str
    shape: bd.Shape
    material: str = "printed"
    explode: tuple[float, float, float] = (0.0, 0.0, 0.0)
    label: str | None = None
    print_axis: str | None = None


@dataclass
class BomItem:
    qty: int | float | str
    item: str
    note: str = ""
    group: str = "Hardware"


@dataclass
class Shot:
    """A photoreal camera. ``direction`` is where the camera looks (world Z is up on screen)."""
    name: str
    title: str
    exploded: bool = False
    direction: tuple[float, float, float] = (-0.5, -1.0, -0.38)
    lens_mm: float = 100.0
    resolution: tuple[int, int] = (2400, 3000)
    hidden: tuple[str, ...] = ()
    frame_box: tuple[tuple[float, float, float], tuple[float, float, float]] | None = None   # mm, else everything
    callouts: bool = False


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: dict = field(default_factory=dict)


class Design:
    """Base class. Override the methods marked *required*; everything else has a sensible default."""

    #: short identifier, used for output folders and titles
    name: str = "design"
    #: one-line human title
    title: str = ""
    #: printed part -> (rx, ry, rz) degrees, applied X then Y then Z, putting the part in its print orientation
    print_rotation: dict[str, tuple[float, float, float]] = {}
    #: (printed part, hardware) pairs that are meant to overlap (a belt clamped in a comb, a part bolted on)
    expected_contacts: set[tuple[str, str]] = set()
    #: (hardware, hardware) pairs that are meant to overlap (simplified models: a block box over its rail)
    hardware_overlaps: set[tuple[str, str]] = set()
    #: keep-out hardware name -> names of hardware allowed inside it (e.g. the frame inside a chassis zone)
    keepouts: dict[str, set[str]] = {}

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else Path(inspect.getfile(type(self)))
        self.out = self.path.parent / "out"

    # ---------------------------------------------------------------- required
    def printed(self, state: Any) -> dict[str, bd.Shape]:
        """*Required.* The printed parts in assembly position for ``state``."""
        raise NotImplementedError

    def hardware(self, state: Any) -> dict[str, bd.Shape]:
        """*Required.* Bought parts (and keep-out zones) in assembly position for ``state``. Model them at their
        real envelope: the interference sweep is only as good as these shapes."""
        raise NotImplementedError

    # ---------------------------------------------------------------- optional
    def states(self) -> list[Any]:
        """Poses to sweep for interference. Include both ends of every motion range."""
        return [None]

    def tools(self) -> dict[str, bd.Shape]:
        """Printed fixtures that are not part of the assembly (drill jigs, gauges). Sliced, not swept."""
        return {}

    def info(self) -> dict:
        """Key numbers to report (travel, hole positions, ...)."""
        return {}

    def bom(self) -> list[BomItem]:
        return []

    def checks(self) -> list[tuple[str, Callable[[], CheckResult | dict | bool]]]:
        """Design-specific checks (vendor-model fit, clearances, alignment). Each returns a CheckResult, a dict with
        ``passed``, or a bool. They run with ``agentcad check`` after the generic ones."""
        return []

    def presentation(self) -> list[ShowPart]:
        """Components for exploded views and photoreal renders. Default: every printed part and piece of
        hardware at the middle state, no explode offsets, keep-outs left out."""
        st = self.states()[len(self.states()) // 2]
        parts = [ShowPart(n, s, "printed", label=n) for n, s in self.printed(st).items()]
        parts += [ShowPart(n, s, "aluminium", label=n) for n, s in self.hardware(st).items() if n not in self.keepouts]
        return parts

    def shots(self) -> list[Shot]:
        """Photoreal cameras. Default: exploded front/back with callouts, assembled front/back."""
        return [Shot("exploded_front", "Exploded, front", True, (-0.5, -1.0, -0.38), callouts=True),
                Shot("exploded_back", "Exploded, back", True, (0.62, 1.0, -0.32), callouts=True),
                Shot("assembled_front", "Assembled, front", False, (-0.62, -1.0, -0.22), resolution=(2000, 3000)),
                Shot("assembled_back", "Assembled, back", False, (0.70, 1.0, -0.30), resolution=(2000, 3000))]

    def render_details(self) -> list[dict]:
        """Close-ups for the quick (matplotlib) renders: dicts with ``z`` (lo, hi), ``view`` (elev, azim),
        ``title`` and optional ``hide`` (names)."""
        return []


def load_design(path: str | Path) -> Design:
    """Import a design file and return its Design instance (``DESIGN`` if defined, else the single subclass)."""
    path = Path(path).resolve()
    if path.is_dir():
        path = path / "design.py"
    spec = importlib.util.spec_from_file_location(f"agentcad_design_{path.parent.name}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(path.parent))
    if isinstance(getattr(mod, "DESIGN", None), Design):
        d = mod.DESIGN
        d.path, d.out = path, path.parent / "out"
        return d
    classes = [c for c in vars(mod).values()
               if inspect.isclass(c) and issubclass(c, Design) and c is not Design and c.__module__ == mod.__name__]
    if len(classes) != 1:
        raise SystemExit(f"{path}: expected one Design subclass or a DESIGN instance, found {len(classes)}")
    return classes[0](path)
