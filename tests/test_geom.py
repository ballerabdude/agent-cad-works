import math

from agentcad import kernel
from agentcad.geom import box, cyl, ring, slot, teardrop


def test_teardrop_is_one_valid_solid_with_a_roof():
    t = teardrop((0, 0, 0), 2.0, 10, (1, 0, 0), (0, 0, 1))
    m = kernel.measure(t)
    assert m["kernel_valid"] and m["solids"] == 1
    assert m["bbox"][1][2] > 2.0 * 1.4          # the 45-degree roof rises above the circle
    assert m["volume"] > math.pi * 4 * 10


def test_ring_volume():
    r = ring((0, 0, 0), 8, 2.5, 5, (0, 1, 0))
    assert abs(r.volume - math.pi * (64 - 6.25) * 5) < 0.5


def test_slot_spans_both_centres():
    s = slot((0, 0, 0), (0, 0, 10), 2, 4, (1, 0, 0))
    bb = s.bounding_box()
    assert abs(bb.size.Z - 14) < 1e-6 and abs(bb.size.X - 4) < 1e-6


def test_overlap_volume_empty_is_zero():
    assert kernel.overlap_volume(box(0, 1, 0, 1, 0, 1), box(5, 6, 5, 6, 5, 6)) == 0.0
    assert abs(kernel.overlap_volume(box(0, 2, 0, 2, 0, 2), box(1, 3, 1, 3, 1, 3)) - 1.0) < 1e-9
