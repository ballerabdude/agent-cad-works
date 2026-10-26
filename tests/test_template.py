from agentcad import check
from agentcad.cli import main
from agentcad.config import Config
from agentcad.design import load_design


def test_new_design_passes_its_checks(tmp_path):
    main(["new", str(tmp_path / "bracket")])
    d = load_design(tmp_path / "bracket")
    rep = check.run(d, Config(), do_slice=False, log=lambda *a: None)
    assert rep["passed"], rep
