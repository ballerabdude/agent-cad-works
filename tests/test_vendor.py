"""The alignment method must tell aligned, misaligned and a wrong control apart."""

from agentcad import vendor
from agentcad.geom import box, cyl


def plate_with_holes(xs):
    p = box(-50, 50, -10, 0, -50, 50)
    for x in xs:
        p -= cyl((x, -5, 0), 1.65, 12, (0, 1, 0))       # M4 tap drill
    return p


def test_aligned_misaligned_control():
    holes = [-30, 0, 30]
    target = plate_with_holes(holes)
    exp = vendor.expected_overlap(3, 2.0, 1.65, 6)
    good = vendor.probes([(x, 0, 0) for x in holes], (0, -1, 0), 2.0, 6)
    bad = vendor.probes([(x + 12, 0, 0) for x in holes], (0, -1, 0), 2.0, 6)
    r = vendor.hole_alignment(target, good, bad, exp)
    assert r["passed"], r
    r2 = vendor.hole_alignment(target, bad, good, exp)
    assert not r2["passed"], r2
    useless = vendor.hole_alignment(target, good, good, exp)          # a control that equals the probe proves nothing
    assert not useless["passed"]
