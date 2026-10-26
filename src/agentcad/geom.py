"""Geometry helpers on top of build123d, in the style every design in this repo uses.

All functions return build123d ``Solid`` objects in millimetres, positioned in world coordinates, so a design
is plain boolean arithmetic: ``body = box(...) - cyl(...) + teardrop(...)``.

Print-oriented helpers (``teardrop``, ``slot``) exist because the checks in ``agentcad.check`` will fail a
part whose horizontal holes need support; use them for any hole that is horizontal in the print orientation.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

import build123d as bd

Vec = Sequence[float]


def box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> bd.Solid:
    """Axis-aligned box between two corners."""
    return bd.Solid.make_box(x1 - x0, y1 - y0, z1 - z0, bd.Plane(origin=(x0, y0, z0)))


def cyl(center: Vec, r: float, h: float, axis: Vec) -> bd.Solid:
    """Cylinder of length ``h`` centred on ``center`` along ``axis``."""
    a = bd.Vector(*axis).normalized()
    base = bd.Vector(*center) - a * (h / 2)
    return bd.Solid.make_cylinder(r, h, bd.Plane(origin=base, z_dir=a))


def cone(base: Vec, r0: float, r1: float, h: float, axis: Vec) -> bd.Solid:
    """Frustum from radius ``r0`` at ``base`` to ``r1`` at ``base + h * axis`` (countersinks, chamfers)."""
    return bd.Solid.make_cone(r0, r1, h, bd.Plane(origin=bd.Vector(*base), z_dir=bd.Vector(*axis).normalized()))


def ring(center: Vec, r_out: float, r_in: float, h: float, axis: Vec) -> bd.Solid:
    """Annulus (bearing, pulley with a bore)."""
    return cyl(center, r_out, h, axis) - cyl(center, r_in, h + 0.2, axis)


def teardrop(center: Vec, r: float, length: float, axis: Vec, up: Vec) -> bd.Solid:
    """Horizontal hole along ``axis`` with a 45-degree roof toward ``up`` (the print's +Z) so it bridges without
    support. Use for every hole that is horizontal when the part is printed."""
    a, u = bd.Vector(*axis).normalized(), bd.Vector(*up).normalized()
    w = a.cross(u)
    c = bd.Vector(*center) - a * (length / 2)
    k = r / math.sqrt(2)
    tri = bd.Face(bd.Wire.make_polygon([c + (u + w) * k, c + u * (r * math.sqrt(2)), c + (u - w) * k], close=True))
    return cyl(center, r, length, axis) + bd.Solid.extrude(tri, a * length)


def slot(c0: Vec, c1: Vec, r: float, length: float, axis: Vec) -> bd.Solid:
    """Stadium slot (adjustment / tension) between centres ``c0`` and ``c1``, cut ``length`` deep along ``axis``."""
    p0, p1 = bd.Vector(*c0), bd.Vector(*c1)
    a = bd.Vector(*axis).normalized()
    s = cyl(tuple(p0), r, length, axis) + cyl(tuple(p1), r, length, axis)
    d = p1 - p0
    if d.length > 1e-9:
        side = d.normalized().cross(a).normalized() * r
        base = p0 - a * (length / 2)
        quad = bd.Face(bd.Wire.make_polygon([base + side, base - side, base - side + d, base + side + d], close=True))
        s += bd.Solid.extrude(quad, a * length)
    return s


def polygon_face(points: Iterable[Vec]) -> bd.Face:
    """Planar polygon face from 3D points."""
    return bd.Face(bd.Wire.make_polygon([bd.Vector(*p) for p in points], close=True))


def union(solids: Iterable[bd.Shape]) -> bd.Shape | None:
    """Fuse an iterable of solids (``None`` if empty)."""
    out = None
    for s in solids:
        out = s if out is None else out + s
    return out


def bolt_circle(center: Vec, radius: float, angles_deg: Iterable[float], plane: str = "xz") -> list[tuple]:
    """Points on a bolt circle. ``plane`` names the two world axes the circle lies in (axis = the third)."""
    i, j = "xyz".index(plane[0]), "xyz".index(plane[1])
    pts = []
    for a in angles_deg:
        p = list(center)
        p[i] += radius * math.cos(math.radians(a))
        p[j] += radius * math.sin(math.radians(a))
        pts.append(tuple(p))
    return pts
