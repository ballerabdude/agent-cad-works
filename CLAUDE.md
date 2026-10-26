# agent-cad-works: notes for agents working on this repo

- Environment: `uv sync`; run everything with `uv run` or `.venv/bin/...`. Python 3.12, versions pinned.
- Tests: `uv run pytest -q` must pass before every commit (about 10 s). After changing check, vendor,
  library or example code, also run `uv run agentcad check examples/zlift`. It must still report travel 328.0
  and all gates PASS.
- The `Design` interface and CLI are documented for agents in `plugin/skills/design-part/references/`. Update
  those files in the same change as the code. `docs/` is for humans and links to them instead of copying.
- Never commit vendor CAD (`vendor/`), anything derived from it (FCStd files, presentation exports), tool
  binaries (`third_party/`) or design outputs (`**/out/`). `.gitignore` covers these; check `git status`.
- Every bought-part number in `src/agentcad/library/` cites its source in a comment.
- A check must be able to fail: when adding one, add a test that makes it fail (see `tests/test_gates.py`,
  `tests/test_vendor.py`).
- Scripts in `src/agentcad/data/` run inside FreeCAD or Blender: standard library and host API only.
- Validate the plugin after editing it: `claude plugin validate plugin` and `claude plugin validate .`.
