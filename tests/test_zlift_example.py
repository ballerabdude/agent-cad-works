"""The worked example must keep reproducing the numbers of the design it was ported from (Z lift v6)."""

from pathlib import Path

import pytest

from agentcad import check
from agentcad.design import load_design

EX = Path(__file__).resolve().parents[1] / "examples" / "zlift"


@pytest.mark.slow
def test_zlift_numbers_and_interference():
    d = load_design(EX)
    info = d.info()
    assert info["travel"] == 328.0
    assert info["drive_axis_z"] == 108.0
    assert info["hole_C"]["x"] == 41.0
    assert check.interference(d, log=lambda *a: None)["overlaps"] == {}


@pytest.mark.slow
def test_zlift_over_travel_is_detected():
    d = load_design(EX)
    name, fn = d.checks()[0]
    assert "vacuous" in name and fn().passed
