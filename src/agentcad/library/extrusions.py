"""4080 aluminium extrusion profiles. Frame: x in [0, 80], y in [-20, 20], length along +z from z = 0.
The two 80 mm faces are y = +20 ("front") and y = -20 ("back").

``SLOT8_4080``: 40-series 4080 with 8 mm slots, from a supplier drawing the user provided (2026-10-25):
opening 8.2, lip 1.8, cavity 20.5 wide, 90-degree V narrowing to 8.24 at 14.5 deep; one slot per 40 mm section
(x = 20, 60 on the 80 mm faces; y = 0 on the 40 mm faces); cores 6.8 mm at (20, 0) and (60, 0); a central
cavity behind 1.8 mm walls at x = 40 (a clean place to drill through). Hardware: M8 (or M5/M6) slot-8 T-nuts.

``VSLOT_4080``: 20-series V-slot 4080 with 6 mm slots (OpenBuilds-style): x = 10, 30, 50, 70 on the 80 mm
faces, y = -10, +10 on the 40 mm faces. Simplified (slot openings only).

Check which one you have: the two look alike in photos, and rail placement depends on it. MGN12H blocks on a
slot-8 4080 sit on x = 20/60 and leave only 13 mm between them.
"""

from __future__ import annotations

from dataclasses import dataclass

import build123d as bd

from ..geom import box, cyl


@dataclass(frozen=True)
class Profile:
    name: str
    width: float
    depth: float
    face_slots_x: tuple       # slot centres on the 80 mm faces
    side_slots_y: tuple       # slot centres on the 40 mm faces
    slot_opening: float
    slot_depth: float
    core_d: float | None
    core_x: tuple
    central_cavity_x: tuple | None   # (x0, x1) of a cavity you can drill into without webs, if any


SLOT8_4080 = Profile("4080 slot 8 (40-series)", 80, 40, (20.0, 60.0), (0.0,), 8.2, 14.5, 6.8, (20.0, 60.0), (32.2, 47.8))
VSLOT_4080 = Profile("V-slot 4080 (6 mm slot)", 80, 40, (10.0, 30.0, 50.0, 70.0), (-10.0, 10.0), 6.2, 6.0, 4.2,
                     (20.0, 60.0), None)


def simple(p: Profile, length: float, holes=()) -> bd.Solid:
    """Envelope for interference checks: slot openings at full depth, cores, central cavity, and drilled holes
    ``holes`` = [(x, z, diameter)] through the 40 mm depth (along y)."""
    ext = box(0, p.width, -p.depth / 2, p.depth / 2, 0, length)
    hs = p.slot_opening / 2
    for x in p.face_slots_x:
        ext -= box(x - hs, x + hs, p.depth / 2 - p.slot_depth, p.depth / 2 + 0.1, -1, length + 1)
        ext -= box(x - hs, x + hs, -p.depth / 2 - 0.1, -p.depth / 2 + p.slot_depth, -1, length + 1)
    for y in p.side_slots_y:
        ext -= box(-0.1, p.slot_depth, y - hs, y + hs, -1, length + 1)
        ext -= box(p.width - p.slot_depth, p.width + 0.1, y - hs, y + hs, -1, length + 1)
    if p.core_d:
        for x in p.core_x:
            ext -= cyl((x, 0, length / 2), p.core_d / 2, length + 2, (0, 0, 1))
    if p.central_cavity_x:
        ext -= box(p.central_cavity_x[0] - 1.2, p.central_cavity_x[1] + 1.2, -18.2, 18.2, -1, length + 1)
    for x, z, d in holes:
        ext -= cyl((x, 0, z), d / 2, p.depth + 1, (0, 1, 0))
    return ext


def _poly(pts, z=0.0):
    return bd.Face(bd.Wire.make_polygon([bd.Vector(a, b, z) for a, b in pts], close=True))


def detailed_slot8(length: float, holes=()) -> bd.Solid:
    """Presentation model of SLOT8_4080 with the T-slot shape, cores, corner and central cavities."""
    p = SLOT8_4080
    d = [(4.1, 0.0), (4.1, 1.8), (10.25, 1.8), (10.25, 8.37), (4.12, 14.5)]
    prof = _poly([(0, -20), (80, -20), (80, 20), (0, 20)])
    cuts = []
    for cx in p.face_slots_x:
        for fy, sgn in ((20, -1), (-20, 1)):
            r = [(cx + w, fy + sgn * t) for w, t in d]
            cuts.append(_poly(r + [(cx - w, fy + sgn * t) for w, t in reversed(d)]))
    for fx, sgn in ((0, 1), (80, -1)):
        u = [(fx + sgn * t, w) for w, t in d]
        cuts.append(_poly(u + [(fx + sgn * t, -w) for w, t in reversed(d)]))
    c = 3.0
    cuts.append(_poly([(32.2 + c, -18.2), (47.8 - c, -18.2), (47.8, -18.2 + c), (47.8, 18.2 - c), (47.8 - c, 18.2),
                       (32.2 + c, 18.2), (32.2, 18.2 - c), (32.2, -18.2 + c)]))
    for x0 in (1.5, 72.5):
        for y0 in (12.5, -18.5):
            cuts.append(_poly([(x0, y0), (x0 + 6, y0), (x0 + 6, y0 + 6), (x0, y0 + 6)]))
    for f in cuts:
        prof -= f
    for cx in p.core_x:
        prof -= bd.Face(bd.Wire.make_circle(p.core_d / 2, bd.Plane(origin=(cx, 0, 0))))
    solid = bd.Solid.extrude(prof, bd.Vector(0, 0, length))
    for x, z, dia in holes:
        solid -= cyl((x, 0, z), dia / 2, 41, (0, 1, 0))
    return solid
