from agentcad import kernel
from agentcad.library import belts, extrusions
from agentcad.library.actuators import rs03_output_angles


def test_rs03_output_phase_after_turn():
    # measured against RobStride's STEP: housing turned so the first M4 hole is at 0 deg
    screws, pins = rs03_output_angles(0.0)
    assert screws == (52.5, 112.5, 172.5, 232.5, 292.5, 352.5)
    assert pins == (82.5, 202.5, 322.5)


def test_gt2_pitch_diameter():
    assert abs(belts.pitch_diameter(20) - 12.732) < 1e-3


def test_extrusion_envelope_is_valid():
    e = extrusions.simple(extrusions.SLOT8_4080, 100, holes=[(41, 50, 10)])
    m = kernel.measure(e)
    assert m["kernel_valid"] and m["solids"] == 1
