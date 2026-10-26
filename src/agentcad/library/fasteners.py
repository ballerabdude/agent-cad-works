"""Metric fasteners. Sources: ISO 4762 (socket head cap screws), ISO 10642 (countersunk), ISO 4032 (hex nuts),
ISO 273 medium-fit clearance holes, common tap-drill sizes. Clearances for printed parts are the medium fit
plus nothing: FDM holes print slightly small, so 0.1-0.3 mm extra may be needed per printer.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..geom import cone, cyl


@dataclass(frozen=True)
class Metric:
    d: float              # nominal diameter
    clearance: float      # ISO 273 medium
    tap_drill: float
    socket_head_d: float  # ISO 4762 dk
    socket_head_h: float  # ISO 4762 k
    csk_head_d: float     # ISO 10642 dk (90 degrees)
    nut_af: float         # ISO 4032 s (across flats)
    nut_h: float


M3 = Metric(3, 3.4, 2.5, 5.5, 3.0, 6.72, 5.5, 2.4)
M4 = Metric(4, 4.5, 3.3, 7.0, 4.0, 8.96, 7.0, 3.2)
M5 = Metric(5, 5.5, 4.2, 8.5, 5.0, 11.2, 8.0, 4.7)
M6 = Metric(6, 6.6, 5.0, 10.0, 6.0, 13.44, 10.0, 5.2)
M8 = Metric(8, 9.0, 6.8, 13.0, 8.0, 17.92, 13.0, 6.8)
SIZES = {"M3": M3, "M4": M4, "M5": M5, "M6": M6, "M8": M8}

INSERT_M4 = 5.6     # heat-set insert hole for common M4 inserts (5.6 mm x 6 mm); check your insert's datasheet


def engagement(length: float, grip: float) -> float:
    """Thread engaged = screw length - material under the head. Keep it below the tapped depth of the target
    (or the screw bottoms out) and above about one diameter in aluminium."""
    return length - grip


def socket_screw(head_at, axis, m: Metric, length: float):
    """Socket head cap screw for presentation: head starts at ``head_at``, shank runs along ``axis``."""
    import build123d as bd
    a = bd.Vector(*axis).normalized()
    c = bd.Vector(*head_at)
    s = cyl(tuple(c + a * (m.socket_head_h / 2)), m.socket_head_d / 2, m.socket_head_h, tuple(a))
    s += cyl(tuple(c + a * (m.socket_head_h + length / 2)), m.d / 2, length, tuple(a))
    return s - cyl(tuple(c + a * 0.9), m.socket_head_d * 0.22, 1.9, tuple(a))   # hex socket hint


def countersink(top, axis_into, m: Metric):
    """Countersink cutter (90 degrees) whose wide end sits at ``top`` and narrows along ``axis_into``."""
    import build123d as bd
    a = bd.Vector(*axis_into).normalized()
    depth = (m.csk_head_d - m.clearance) / 2
    return cone(tuple(bd.Vector(*top) - a * 0.01), m.csk_head_d / 2 + 0.2, m.clearance / 2, depth + 0.01, tuple(a))
