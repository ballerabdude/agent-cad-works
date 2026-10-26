"""__TITLE__

Requirements (write them down first, with the date and who said so):
  * ...

Frame (mm): say where the origin is and which way +X, +Y, +Z point relative to the machine.
Sources: every dimension of a bought part cites its datasheet or the vendor STEP (see agentcad.library).
"""

from __future__ import annotations

from agentcad.design import BomItem, Design, ShowPart
from agentcad.geom import box, cyl, teardrop

# ---------------------------------------------------------------- parameters (all in mm)
PLATE = (60.0, 40.0, 6.0)


class Part(Design):
    name = "__NAME__"
    title = "__TITLE__"
    print_rotation = {"bracket": (0, 0, 0)}

    def states(self):
        return [None]                       # list every pose of a moving mechanism (both ends of travel)

    def printed(self, state):
        w, d, t = PLATE
        body = box(0, w, 0, d, 0, t)
        body -= cyl((w / 2, d / 2, t / 2), 5.5 / 2, t + 1, (0, 0, 1))      # M5 clearance
        return {"bracket": body}

    def hardware(self, state):
        w, d, t = PLATE
        return {"m5_bolt": cyl((w / 2, d / 2, t + 2), 2.5, 4, (0, 0, 1))}  # model bought parts at their envelope

    def bom(self):
        return [BomItem(1, "M5x12 socket head", "bracket to frame")]

    def presentation(self):
        st = self.states()[0]
        return [ShowPart("bracket", self.printed(st)["bracket"], "printed", label="Bracket (printed)", print_axis="Z"),
                ShowPart("m5_bolt", self.hardware(st)["m5_bolt"], "black_oxide", (0, 0, 20), label="M5 bolt")]
