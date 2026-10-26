"""GT2 timing belts and pulleys (2 mm pitch). Source: Gates GT2 2MGT profile: pitch 2.0 mm, pitch diameter
= teeth x 2 / pi; belt about 1.38 mm thick (teeth included). Common 20T pulleys for 10 mm belt: flange about
18-19 mm, hub 16 mm, bore 5 or 8 mm (check the seller's drawing; flange size sets clearances).
"""

from __future__ import annotations

import math

import build123d as bd

from ..geom import box, cyl, ring

PITCH = 2.0
BELT_T = 1.4


def pitch_diameter(teeth: int) -> float:
    return teeth * PITCH / math.pi


def belt_centre_radius(teeth: int) -> float:
    """Belt centre line radius on a pulley (teeth in): pitch radius + half the belt thickness."""
    return pitch_diameter(teeth) / 2 + BELT_T / 2


def pulley_envelope(center_xz, teeth: int, bore: float, y0: float, y1: float, flange_r: float = 9.0,
                    hub: tuple[float, float] | None = None):
    """Interference envelope of a flanged pulley on an axis along y: teeth body between y0 and y1, 1 mm flanges
    outside that, optional hub (radius, length) beyond y1."""
    x, z = center_xz
    pd = pitch_diameter(teeth)
    p = ring((x, (y0 + y1) / 2, z), pd / 2, bore / 2, y1 - y0, (0, 1, 0))
    p += ring((x, y0 - 0.5, z), flange_r, bore / 2, 1.0, (0, 1, 0)) + ring((x, y1 + 0.5, z), flange_r, bore / 2, 1.0, (0, 1, 0))
    if hub:
        hr, hl = hub
        p += ring((x, y1 + 1 + hl / 2, z), hr, bore / 2, hl, (0, 1, 0))
    return p


def pulley_detailed(center_xz, teeth: int, bore: float, y0: float, y1: float, flange_r: float = 9.0,
                    hub: tuple[float, float] | None = None):
    """Presentation model with tooth grooves and a set-screw hole in the hub."""
    x, z = center_xz
    pd = pitch_diameter(teeth)
    p = cyl((x, (y0 + y1) / 2, z), pd / 2 - 0.25, y1 - y0, (0, 1, 0))
    for i in range(teeth):
        a = 2 * math.pi * i / teeth
        p -= cyl((x + (pd / 2 - 0.27) * math.cos(a), (y0 + y1) / 2, z + (pd / 2 - 0.27) * math.sin(a)), 0.55,
                 y1 - y0 + 0.2, (0, 1, 0))
    p += cyl((x, y0 - 0.5, z), flange_r, 1.0, (0, 1, 0)) + cyl((x, y1 + 0.5, z), flange_r, 1.0, (0, 1, 0))
    if hub:
        hr, hl = hub
        p += cyl((x, y1 + 1 + hl / 2, z), hr, hl, (0, 1, 0))
        p -= cyl((x + hr - 1.5, y1 + 1 + hl / 2, z), 1.5, 4, (1, 0, 0))
    return p - cyl((x, (y0 + y1) / 2 + 10, z), bore / 2, (y1 - y0) + 40, (0, 1, 0))


def belt_segment(p0, p1, y0: float, y1: float, t: float = BELT_T):
    """Straight belt piece in the XZ plane (width along y) between two (x, z) centre-line points."""
    (xa, za), (xb, zb) = p0, p1
    ln = math.hypot(xb - xa, zb - za)
    n = bd.Vector(-(zb - za) / ln, 0, (xb - xa) / ln)
    o = n * (-t / 2)
    quad = bd.Face(bd.Wire.make_polygon([bd.Vector(xa, y0, za) + o, bd.Vector(xa, y1, za) + o,
                                         bd.Vector(xb, y1, zb) + o, bd.Vector(xb, y0, zb) + o], close=True))
    return bd.Solid.extrude(quad, n * t)


def belt_arc(center_xz, teeth: int, y0: float, y1: float, upper: bool):
    """Half-wrap of a belt (teeth in) around a pulley, above (``upper``) or below its centre."""
    x, z = center_xz
    r_in = pitch_diameter(teeth) / 2
    a = ring((x, (y0 + y1) / 2, z), r_in + BELT_T, r_in, y1 - y0, (0, 1, 0))
    half = box(x - 30, x + 30, y0 - 1, y1 + 1, z, z + 30) if upper else box(x - 30, x + 30, y0 - 1, y1 + 1, z - 30, z)
    return a & half
