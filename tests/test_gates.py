"""The interference gate must find a planted collision and respect declared contacts."""

from agentcad import check
from agentcad.design import Design
from agentcad.geom import box


class TwoBlocks(Design):
    name = "two_blocks"

    def __init__(self, gap, path=None):
        super().__init__(path)
        self.gap = gap

    def printed(self, state):
        return {"a": box(0, 10, 0, 10, 0, 10)}

    def hardware(self, state):
        return {"b": box(10 + self.gap, 20, 0, 10, 0, 10)}


def test_planted_collision_is_found(tmp_path):
    d = TwoBlocks(-1.0, tmp_path / "design.py")
    r = check.interference(d, log=lambda *a: None)
    assert r["overlaps"] == {"a x b": 100.0}


def test_clear_design_passes(tmp_path):
    d = TwoBlocks(0.5, tmp_path / "design.py")
    assert check.interference(d, log=lambda *a: None)["overlaps"] == {}


def test_expected_contact_is_allowed(tmp_path):
    d = TwoBlocks(-1.0, tmp_path / "design.py")
    d.expected_contacts = {("a", "b")}
    assert check.interference(d, log=lambda *a: None)["overlaps"] == {}


def test_keepout_catches_hardware(tmp_path):
    class K(TwoBlocks):
        keepouts = {"zone": set()}

        def hardware(self, state):
            return {"b": box(30, 40, 0, 10, 0, 10), "zone": box(35, 50, 0, 10, 0, 10)}
    d = K(0, tmp_path / "design.py")
    assert "b x zone" in check.interference(d, log=lambda *a: None)["overlaps"]


def test_printability_flags_two_bodies(tmp_path):
    class Split(TwoBlocks):
        def printed(self, state):
            return {"a": box(0, 10, 0, 10, 0, 10) + box(20, 30, 0, 10, 0, 10)}
    d = Split(5, tmp_path / "design.py")
    from agentcad.config import Config
    r = check.printability(d, Config(), do_slice=False, log=lambda *a: None)
    assert r["a"]["solids"] == 2 and not r["a"]["passed"]
