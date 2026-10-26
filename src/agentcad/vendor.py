"""Fit a design against a manufacturer's own CAD model (STEP).

A datasheet drawing is not enough. In the project this repo grew out of, a mount was designed from a drawing
that turned out to belong to a different model, and the real part's pilot had a base fillet that would have
stopped it seating. Both were found only by placing the vendor's STEP on the design and measuring.

Three measurements, all exact (OCCT booleans and distances):

``clearance``
    overlap volume and minimum distance between the vendor model and each of your parts. Contact (distance 0)
    with zero overlap is a correct seat.
``hole_alignment``
    probe cylinders where your screws/dowels go. Compare the overlap with the analytic value for "aligned"
    (screw thread ring only) and "misaligned" (whole cross-section) from :func:`expected_overlap`.
``control``
    the same probes rotated by a wrong angle must give a clearly different overlap. If they do not, the
    alignment test cannot tell right from wrong and proves nothing.

Vendor STEP files are usually not redistributable: keep them in ``vendor/`` (git-ignored) and document where
to download them.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Callable, Iterable, Sequence

import build123d as bd

from .geom import cyl
from .kernel import overlap_volume


def load_step(path: Path | str) -> bd.Shape:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"vendor model not found: {path} (download it into the vendor directory)")
    return bd.import_step(str(path))


def place(shape: bd.Shape, rotations: Sequence[tuple[str, float]] = (), translate=(0.0, 0.0, 0.0)) -> bd.Shape:
    """Apply rotations in order, e.g. ``[("Z", -22.5), ("X", -90)]``, then a translation."""
    for ax, deg in rotations:
        shape = shape.rotate({"X": bd.Axis.X, "Y": bd.Axis.Y, "Z": bd.Axis.Z}[ax], deg)
    return shape.translate(translate)


def split_solids(shape: bd.Shape, predicate: Callable[[bd.Solid], bool]) -> tuple[bd.Compound, bd.Compound]:
    """Split a vendor assembly into (matching, rest), e.g. rotating output parts vs housing.
    Bounding boxes from STEP solids can sit 1e-4 below a round number: compare with a margin."""
    yes, no = [], []
    for s in shape.solids():
        (yes if predicate(s) else no).append(s)
    return bd.Compound(yes), bd.Compound(no)


def clearance(vendor: bd.Shape, others: dict[str, bd.Shape]) -> dict[str, dict]:
    out = {}
    for name, other in others.items():
        out[name] = {"overlap_mm3": round(overlap_volume(vendor, other), 3),
                     "min_distance_mm": round(vendor.distance_to(other), 3)}
    return out


def probes(centers: Iterable[Sequence[float]], axis: Sequence[float], radius: float, depth: float,
           start_offset: float = 0.0) -> bd.Shape:
    """Cylinders of ``radius`` and ``depth`` starting at each centre (+ ``start_offset`` along ``axis``)."""
    a = bd.Vector(*axis).normalized()
    s = None
    for c in centers:
        mid = bd.Vector(*c) + a * (start_offset + depth / 2)
        p = cyl(tuple(mid), radius, depth, tuple(a))
        s = p if s is None else s + p
    return s


def expected_overlap(n: int, probe_r: float, hole_r: float, depth: float) -> dict:
    """Analytic overlaps for n probes of radius probe_r in holes of radius hole_r (0 if the probe fits)."""
    aligned = n * math.pi * max(0.0, probe_r ** 2 - hole_r ** 2) * depth
    return {"aligned": round(aligned, 1), "misaligned": round(n * math.pi * probe_r ** 2 * depth, 1)}


def hole_alignment(target: bd.Shape, probe: bd.Shape, control: bd.Shape, expect: dict, tol: float = 0.25) -> dict:
    """Pass when the probe overlap is within ``tol`` (fraction of the aligned/misaligned gap) of the aligned
    value AND the control overlap differs from it by more than that gap fraction."""
    v, vc = overlap_volume(target, probe), overlap_volume(target, control)
    gap = max(expect["misaligned"] - expect["aligned"], 1e-6)
    ok = abs(v - expect["aligned"]) <= tol * gap
    discriminates = abs(vc - v) > tol * gap
    return {"passed": bool(ok and discriminates), "overlap_mm3": round(v, 1), "control_mm3": round(vc, 1),
            **expect, "aligned_ok": ok, "control_discriminates": discriminates}
