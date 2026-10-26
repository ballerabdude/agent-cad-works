# Roadmap

Not done yet, in rough priority order:

1. **Licence.** Choose one (the plugin directory requires a LICENSE file).
2. **Container image** pinning OrcaSlicer (AppImage), FreeCAD (AppImage; the snap's sandbox caused most of the
   FreeCAD workarounds), Blender LTS and Xvfb, with an optional GPU. One command to a working toolchain.
3. **More library parts:** 2020/2040/4040 profiles, MGN9/MGN15, NEMA 23, common bearings, GT2 6 mm, T8 lead
   screws.
4. **Printer profiles beyond Bambu:** Prusa and generic Klipper via OrcaSlicer system profiles; test `doctor`
   against them.
5. **CI:** run `pytest` (fast tests) on every push; run the slow example nightly with OrcaSlicer in the
   container.
6. **MCP server** exposing `check`, `render` and friends, for agents other than Claude Code.
7. **Plugin evals** (`claude plugin eval`): prompts with graders that check the agent ran `agentcad check` and
   reported its numbers.
