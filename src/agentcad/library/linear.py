"""MGN12 miniature linear guide (rail + MGN12H block).

Source: HIWIN MG series catalogue (MGN12, MGN12H): rail width 12, rail height 8, mounting hole pitch 25,
M3 rail screws (holes 3.5 through, 6 x 3.5 counterbore); block MGN12H width 27, length 45.4, height 13 from the
rail's base, 3 mm under the block; block screw pattern 20 x 20, M3, about 3.5 mm thread depth.
Thread depth matters: carriage screws must stop short of it (``fasteners.engagement``).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..geom import box, cyl


@dataclass(frozen=True)
class MGN12:
    rail_w: float = 12.0
    rail_h: float = 8.0
    pitch: float = 25.0
    block_w: float = 27.0
    block_l: float = 45.4
    block_h: float = 13.0          # top of block above the rail's base
    block_gap: float = 3.0         # rail base to block underside
    block_holes: tuple = (20.0, 20.0)
    block_thread_depth: float = 3.5


SPEC = MGN12()


def rail(x: float, base_y: float, z0: float, z1: float, detailed: bool = False, s: MGN12 = SPEC):
    """Rail along +z, centred on x, base on the plane y = base_y, top towards +y."""
    r = box(x - s.rail_w / 2, x + s.rail_w / 2, base_y, base_y + s.rail_h, z0, z1)
    if not detailed:
        return r
    for sgn in (-1, 1):                                          # ball grooves
        r -= box(x + sgn * s.rail_w / 2 - 0.8, x + sgn * s.rail_w / 2 + 0.8, base_y + 4.2, base_y + 5.8, z0 - 1, z1 + 1)
    z = z0 + s.pitch / 2
    while z < z1 - 5:
        r -= cyl((x, base_y + 4, z), 1.75, 8.2, (0, 1, 0)) + cyl((x, base_y + s.rail_h - 1.75, z), 3.0, 3.6, (0, 1, 0))
        z += s.pitch
    return r


def block(x: float, base_y: float, zc: float, detailed: bool = False, s: MGN12 = SPEC):
    """MGN12H block centred at height zc. Envelope: a solid box over the rail (declare the rail/block overlap in
    ``Design.hardware_overlaps``). Detailed: returns (steel body, end seals) with the rail channel cut out."""
    y0, y1 = base_y + s.block_gap, base_y + s.block_h
    hl = s.block_l / 2
    if not detailed:
        return box(x - s.block_w / 2, x + s.block_w / 2, y0, y1, zc - hl, zc + hl)
    body = box(x - s.block_w / 2, x + s.block_w / 2, y0, y1, zc - hl + 4, zc + hl - 4)
    seals = box(x - s.block_w / 2, x + s.block_w / 2, y0, y1 - 0.5, zc - hl, zc - hl + 4) + \
        box(x - s.block_w / 2, x + s.block_w / 2, y0, y1 - 0.5, zc + hl - 4, zc + hl)
    chan = box(x - s.rail_w / 2 - 0.3, x + s.rail_w / 2 + 0.3, y0 - 1, base_y + s.rail_h + 0.3, zc - hl - 1, zc + hl + 1)
    for dx in (-s.block_holes[0] / 2, s.block_holes[0] / 2):
        for dz in (-s.block_holes[1] / 2, s.block_holes[1] / 2):
            body -= cyl((x + dx, y1 - 1.5, zc + dz), 1.5, 3.2, (0, 1, 0))
    return body - chan, seals - chan
