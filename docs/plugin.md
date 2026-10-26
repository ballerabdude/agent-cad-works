# The Claude Code plugin

`plugin/` is a Claude Code plugin, and the repository root is a plugin marketplace
(`.claude-plugin/marketplace.json`).

## Install

```text
/plugin install agent-cad-works --marketplace <owner>/agent-cad-works     # Claude Code 2.1.275 or later
```

Or in two steps (any version; a local path works instead of `<owner>/<repo>`):

```text
/plugin marketplace add <owner>/agent-cad-works
/plugin install agent-cad-works@agent-cad-works
```

The skills call the `agentcad` CLI, so install the package too (`uv tool install <repo>`) and run
`agentcad doctor`.

## What it adds

| component | kind | use |
|---|---|---|
| `design-part` | skill | requirements → design.py → `agentcad check` until it passes → BOM → renders → report |
| `vendor-fit` | skill | place a vendor STEP, measure clearance and hole alignment with a control |
| `product-renders` | skill | FreeCAD exploded views and Blender photoreal renders with callouts |
| `cad-reviewer` | agent | independent audit of a design after it passes: envelopes, states, declared overlaps, sources, fasteners, evidence |

Skills load automatically when a request matches. You can also invoke them directly, e.g.
`/agent-cad-works:design-part`.

## Developing the plugin

```bash
claude plugin validate plugin      # manifest, skills and agent front matter
claude plugin validate .           # the marketplace
```

The plugin's reference files are the canonical docs for agents. When you change the CLI or the `Design`
interface, update `plugin/skills/design-part/references/` in the same commit.
