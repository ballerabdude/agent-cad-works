"""Z lift: a belt-driven vertical axis for a robot arm on a 4080 extrusion, driven by a RobStride 03.

This is the worked example for agent-cad-works: a real design that went through six versions, ported to the
``Design`` interface. Read it next to ``README.md`` (requirements, decisions, results).

Requirements (from the user, 2026-10-25):
  * Lift a robot arm (3-5 kg) up and down a 4080 aluminium extrusion (40-series, 8 mm slots, M8 hardware).
  * Two MGN12H rails on the 80 mm front face; the belt runs between them.
  * RobStride 03 actuator, stationary, mounted low on the back face, driving through ONE hole drilled through
    the extrusion.
  * The bottom ~40 mm of the extrusion sits inside the robot's chassis: nothing of ours below Z_KEEP.
  * Mount only on the 80 mm faces.

Frame (mm): extrusion x in [0, 80], y in [-20, 20], z in [0, L]; front (arm) face y = +20, back y = -20.
The state is the carriage's bottom edge height z0.
"""

from __future__ import annotations

import math

import build123d as bd

from agentcad import vendor
from agentcad.design import BomItem, CheckResult, Design, Shot, ShowPart
from agentcad.geom import box, cone, cyl, teardrop
from agentcad.kernel import overlap_volume
from agentcad.library import belts, extrusions, linear
from agentcad.library.actuators import RS03_SPEC as RS, rs03_envelope, rs03_output_angles, rs03_vendor_rotations
from agentcad.library.fasteners import INSERT_M4, M3, M4, M5, M8, socket_screw

# ------------------------------------------------------------------------------------------------ parameters
L = 500.0                         # extrusion length
Z_KEEP = 45.0                     # chassis top (40) + 5 mm margin
PROFILE = extrusions.SLOT8_4080
FACE_Y = 20.0
RAIL_X = PROFILE.face_slots_x     # rails can only go on the slots: x = 20 and 60
SPACER_T, SPACER_W = 10.0, 15.0   # 10 mm bars lift the rails so the blocks clear the belt (13 mm gap otherwise)
MG = linear.SPEC
RAIL_Y0 = FACE_Y + SPACER_T
PLATE_Y0 = RAIL_Y0 + MG.block_h   # carriage underside = block tops (43)

X_C = 41.0                        # drive shaft + top idler; 41 not 40 so the comb wall clears the left block
TEETH = 20
BELT_Y0, BELT_Y1 = 22.0, 32.0
R_B = belts.belt_centre_radius(TEETH)
RUN_A, RUN_B = X_C - R_B, X_C + R_B
FLANGE_R = 9.0
Z_TOP = L + 10.0                  # top idler (tension slot +-3)
TENSION = 3.0
Y_IDLER = (BELT_Y0 - 1, BELT_Y1 + 1)

MOUNT_A0 = 0.0                    # RS03 turned 22.5 deg from its drawing: M4 holes stay >19 mm from the M8 bolts
OUT_SCREWS, OUT_PINS = rs03_output_angles(MOUNT_A0)
HUB_FLANGE_R, HUB_FLANGE_T, HUB_BOSS_R = 20.0, 5.0, 9.0
HUB_ZONE = RS.proud + HUB_FLANGE_T + 1.0
SHAFT_D = 8.0
PLATE_T = 18.0
Y_RS = -FACE_Y - PLATE_T          # actuator mounting face
TNUT_EDGE = 7.5
TNUT_CLEAR = RS.body_d / 2 + M8.socket_head_d / 2 + 1.25     # M8 heads stay outside the actuator outline
ZD = math.ceil(2 * (Z_KEEP + 0.5 + TNUT_EDGE + math.sqrt(TNUT_CLEAR ** 2 - (RAIL_X[1] - X_C) ** 2))) / 2   # 108.0
PLATE_X = (X_C - 56.0, X_C + 56.0)
SHAFT_Y = (Y_RS + RS.proud + 1.0, 40.0)

CAR_H, CAR_T, CLAMP_L = 110.0, 18.0, 50.0
COMB_X = (RUN_A + belts.BELT_T / 2 + 0.1, RUN_A + belts.BELT_T / 2 + 3.9)
BLK_Z_TOP = 1.0                   # blocks at the carriage's top end: they never pass over the pulley hub
ARM_X = (10.0, 30.0, 50.0, 70.0)

RS03_STEP = "robstride/RS03.stp"  # inside the vendor dir (not redistributable: download it, see README)


def tnut_points():
    """M8 into the back-face slots (x = 20, 60), above and below the actuator, outside its outline."""
    pts = []
    for x in RAIL_X:
        dz = math.sqrt(TNUT_CLEAR ** 2 - (x - X_C) ** 2)
        pts += [(x, ZD - dz), (x, ZD + dz)]
    return pts


def plate_z():
    zs = [z for _, z in tnut_points()]
    return min(zs) - TNUT_EDGE, max(zs) + TNUT_EDGE


def rs_screw_points():
    return [(X_C + RS.mount_pcd / 2 * math.cos(math.radians(MOUNT_A0 + 45 * i)),
             ZD + RS.mount_pcd / 2 * math.sin(math.radians(MOUNT_A0 + 45 * i))) for i in range(RS.mount_n)]


def car_limits():
    """Bottom: clamp and blocks stop 1 mm above the drive pulley's flange; stay out of the chassis.
    Top: clamp stops under the top idler's flange (lowest tension position); blocks stay on the rails."""
    zmin = max(ZD + FLANGE_R + 1.0 - (CAR_H - CLAMP_L), ZD + FLANGE_R + 1.0 - (CAR_H - BLK_Z_TOP - MG.block_l), Z_KEEP + 0.5)
    zmax = min(Z_TOP - TENSION - FLANGE_R - 1.0, L - 0.5, L - 5.0 + BLK_Z_TOP) - CAR_H
    return zmin, zmax


def _y(c_xz, y):
    return (c_xz[0], y, c_xz[1])


# ------------------------------------------------------------------------------------------------ printed parts
def rs03_mount():
    """Plate on the back face. Its back takes the RS03's 70 mm pilot in a pocket (that locates the actuator); the
    pocket mouth has a 0.7 mm chamfer because the pilot's base fillet makes it ~71 mm at the face (found by
    checking RobStride's STEP). 8x M4x18 from the front into the RS03; 4x M8 T-nut bolts outside its outline."""
    y0, y1 = Y_RS, -FACE_Y
    body = box(*PLATE_X, y0, y1, *plate_z())
    body -= cyl((X_C, y0 + (RS.proud + 0.3) / 2 - 0.05, ZD), RS.pilot_d / 2 + 0.2, RS.proud + 0.4, (0, 1, 0))
    body -= cone((X_C, y0 - 0.01, ZD), RS.pilot_d / 2 + 0.9, RS.pilot_d / 2 + 0.2, 0.71, (0, 1, 0))
    body -= cyl((X_C, y0 + HUB_ZONE / 2 - 0.05, ZD), HUB_FLANGE_R + 1.5, HUB_ZONE + 0.1, (0, 1, 0))
    body -= cyl((X_C, (y0 + HUB_ZONE + y1) / 2, ZD), HUB_BOSS_R + 2.0, y1 - y0 - HUB_ZONE + 0.2, (0, 1, 0))
    for x, z in tnut_points():
        body -= cyl((x, (y0 + y1) / 2, z), 8.5 / 2, PLATE_T + 1, (0, 1, 0))
    for x, z in rs_screw_points():
        body -= cyl((x, (y0 + y1) / 2, z), M4.clearance / 2, PLATE_T + 1, (0, 1, 0))
        body -= cyl((x, y1 - 3.0, z), 4.1, 6.1, (0, 1, 0))          # 6 mm counterbore: M4x18 -> 6 mm thread
    return body


def drive_hub():
    """On the RS03 output flange: 3x 4 mm dowels take the torque, 6x countersunk M4 hold it, 2x M3 set screws
    (captive nuts) hold the 8 mm shaft. Printed is fine under a 1 N m torque limit."""
    y0 = Y_RS + RS.proud
    yt = y0 + HUB_FLANGE_T
    yb1 = -22.0
    body = cyl((X_C, (y0 + yt) / 2, ZD), HUB_FLANGE_R, HUB_FLANGE_T, (0, 1, 0))
    body += cyl((X_C, (yt + yb1) / 2, ZD), HUB_BOSS_R, yb1 - yt, (0, 1, 0))
    body -= cyl((X_C, (SHAFT_Y[0] + yb1 + 0.1) / 2, ZD), SHAFT_D / 2, yb1 + 0.1 - SHAFT_Y[0], (0, 1, 0))
    for deg in OUT_PINS:
        a = math.radians(deg)
        body -= cyl((X_C + RS.output_pcd / 2 * math.cos(a), (y0 + yt) / 2, ZD + RS.output_pcd / 2 * math.sin(a)),
                    2.075, HUB_FLANGE_T + 1, (0, 1, 0))
    for deg in OUT_SCREWS:
        a = math.radians(deg)
        x, z = X_C + RS.output_pcd / 2 * math.cos(a), ZD + RS.output_pcd / 2 * math.sin(a)
        body -= cyl((x, (y0 + yt) / 2, z), M4.clearance / 2, HUB_FLANGE_T + 1, (0, 1, 0))
        body -= cone((x, yt - (4.1 - M4.clearance / 2), z), M4.clearance / 2, 4.1, 4.1 - M4.clearance / 2 + 0.01, (0, 1, 0))
    ys = -26.5
    for sgn in (-1, 1):
        body -= teardrop((X_C + sgn * 6.5, ys, ZD), M3.clearance / 2, 6, (1, 0, 0), (0, 1, 0))
        body -= box(X_C + sgn * 5.2 - 1.3, X_C + sgn * 5.2 + 1.3, ys - 3.0, yb1 + 0.1, ZD - 2.9, ZD + 2.9)
    return body


def top_cap():
    """Sits on the extrusion's top end, M8 into the back-face slots. Holds the 20T idler in tension slots.
    Printed roof-down; the roof is open behind the back wall so the axle head can be reached."""
    zt = L
    yf = (Y_IDLER[1] + 1.0, Y_IDLER[1] + 8.0)
    body = (box(12, 68, 8, yf[1], zt + 30, zt + 36) + box(8, 72, -26, -20, zt - 40, zt + 36)
            + box(12, 16, -26, yf[1], zt, zt + 36) + box(64, 68, -26, yf[1], zt, zt + 36)
            + box(8, 72, -26, 20, zt, zt + 6) + box(16, 64, 8, 20, zt, zt + 30) + box(16, 64, *yf, zt, zt + 30))
    down = (0, 0, -1)
    for y0, y1 in ((8, 20), yf):
        yc = (y0 + y1) / 2
        body -= cyl((X_C, yc, Z_TOP + TENSION), M5.clearance / 2, y1 - y0 + 1, (0, 1, 0))
        body -= teardrop((X_C, yc, Z_TOP - TENSION), M5.clearance / 2, y1 - y0 + 1, (0, 1, 0), down)
        body -= box(X_C - M5.clearance / 2, X_C + M5.clearance / 2, y0 - 0.5, y1 + 0.5, Z_TOP - TENSION, Z_TOP + TENSION)
    for x in RAIL_X:
        for z in (zt - 12.0, zt - 30.0):
            body -= teardrop((x, -23, z), 8.5 / 2, 8, (0, 1, 0), down)
    return body - box(X_C - 6, X_C + 6, 3.0, 8.01, zt + 1.5, zt + 7)


def carriage(z0):
    """Plate on the two blocks (at its top end). The run-A clamp is one comb wall (teeth in) dropping between
    the blocks; the belt end is zip-tied against it. Arm interface: 16 M4 heat-set inserts on a 20 mm grid."""
    y0, y1 = PLATE_Y0, PLATE_Y0 + CAR_T
    z1 = z0 + CAR_H
    zc0 = z1 - CLAMP_L
    body = box(-6, 86, y0, y1, z0, z1) + box(COMB_X[0], COMB_X[1], FACE_Y + 0.8, y0 + 0.01, zc0, z1)
    comb = None
    for i in range(int(CLAMP_L / 2.0)):
        r = cyl((COMB_X[0], (BELT_Y0 + BELT_Y1) / 2, zc0 + 1.0 + 2.0 * i), 0.55, BELT_Y1 - BELT_Y0 + 0.6, (0, 1, 0))
        comb = r if comb is None else comb + r
    body += comb & box(COMB_X[0] - 0.6, COMB_X[0] + 0.01, BELT_Y0 - 0.3, BELT_Y1 + 0.3, zc0, z1)
    for zz in (zc0 + 6, z1 - 6):
        body -= box(COMB_X[0] - 0.1, COMB_X[1] + 0.1, 24.0, 27.5, zz - 2, zz + 2)
    zc = z1 - BLK_Z_TOP - MG.block_l / 2
    for rx in RAIL_X:
        for dx in (-10.0, 10.0):
            for dz in (-10.0, 10.0):
                body -= cyl((rx + dx, (y0 + y1) / 2, zc + dz), M3.clearance / 2, CAR_T + 1, (0, 1, 0))
                body -= cyl((rx + dx, y1 - 4.5, zc + dz), M3.socket_head_d / 2 + 0.35, 9.2, (0, 1, 0))  # M3x12: 3.1 mm thread
    for x in ARM_X:
        for dz in (-40.0, -20.0, 20.0, 40.0):
            body -= cyl((x, y1 - 3.0, z0 + CAR_H / 2 + dz), INSERT_M4 / 2, 6.2, (0, 1, 0))
    return body


def drill_jig():
    """Keys into the x = 20 / 60 slots (before the rails go on); a 4.2 mm pilot bore for hole C; notches mark
    its centre line. Flip it top-over-bottom to pilot from the back face too."""
    y0, y1 = FACE_Y, FACE_Y + 14.0
    body = box(12, 68, y0, y1, ZD - 22, ZD + 22)
    for x in RAIL_X:
        body += box(x - 3.9, x + 3.9, y0 - 3.0, y0 + 0.01, ZD - 22, ZD + 22)
    body -= cyl((X_C, (y0 + y1) / 2 - 1.5, ZD), 2.1, y1 - y0 + 4, (0, 1, 0))
    for x in (12, 68):
        n = bd.Face(bd.Wire.make_polygon([bd.Vector(x, y0 - 0.1, ZD - 2), bd.Vector(x, y0 - 0.1, ZD + 2),
                                          bd.Vector(x + (2 if x < 40 else -2), y0 - 0.1, ZD)], close=True))
        body -= bd.Solid.extrude(n, bd.Vector(0, y1 - y0 + 0.2, 0))
    return body


# ------------------------------------------------------------------------------------------------ the design
class ZLift(Design):
    name = "zlift"
    title = "Z lift: RobStride 03 belt drive on a 4080 extrusion"
    print_rotation = {"rs03_mount": (-90, 0, 0), "drive_hub": (90, 0, 0), "top_cap": (180, 0, 0),
                      "carriage": (-90, 0, 0), "drill_jig": (-90, 0, 0)}
    expected_contacts = {("carriage", "belt"), ("carriage", "blocks")}     # belt in the comb; blocks bolted on
    hardware_overlaps = {("rails", "blocks")}                               # blocks modelled as boxes over the rail
    keepouts = {"chassis_keepout": {"extrusion"}}                           # the extrusion goes into the chassis

    def states(self):
        lo, hi = car_limits()
        return [round(lo, 2), round((lo + hi) / 2, 2), round(hi, 2)]

    def printed(self, z0):
        return {"rs03_mount": rs03_mount(), "drive_hub": drive_hub(), "top_cap": top_cap(), "carriage": carriage(z0)}

    def tools(self):
        return {"drill_jig": drill_jig()}

    def hardware(self, z0):
        hw = {"extrusion": extrusions.simple(PROFILE, L, holes=[(X_C, ZD, 10.0)])}
        hw["spacers"] = box(RAIL_X[0] - SPACER_W / 2, RAIL_X[0] + SPACER_W / 2, FACE_Y, RAIL_Y0, Z_KEEP, L - 5) + \
            box(RAIL_X[1] - SPACER_W / 2, RAIL_X[1] + SPACER_W / 2, FACE_Y, RAIL_Y0, Z_KEEP, L - 5)
        hw["rails"] = linear.rail(RAIL_X[0], RAIL_Y0, Z_KEEP, L - 5) + linear.rail(RAIL_X[1], RAIL_Y0, Z_KEEP, L - 5)
        zc = z0 + CAR_H - BLK_Z_TOP - MG.block_l / 2
        hw["blocks"] = linear.block(RAIL_X[0], RAIL_Y0, zc) + linear.block(RAIL_X[1], RAIL_Y0, zc)
        hw["rs03"] = rs03_envelope((X_C, ZD), Y_RS)
        hw["shaft"] = cyl((X_C, sum(SHAFT_Y) / 2, ZD), SHAFT_D / 2, SHAFT_Y[1] - SHAFT_Y[0], (0, 1, 0))
        hw["drive_pulley"] = belts.pulley_envelope((X_C, ZD), TEETH, SHAFT_D, BELT_Y0, BELT_Y1, FLANGE_R, hub=(8.0, 7.0))
        hw["top_idler"] = belts.pulley_envelope((X_C, Z_TOP), TEETH, 5.0, BELT_Y0, BELT_Y1, FLANGE_R)
        ya, yb = 8.0 - 3.5, Y_IDLER[1] + 8.0 + 5.0
        bolts = cyl((X_C, (ya + 3.5 + yb) / 2, Z_TOP), 2.5, yb - ya - 3.5, (0, 1, 0)) + \
            cyl((X_C, ya + 1.75, Z_TOP), 4.6, 3.5, (0, 1, 0))
        for x, z in tnut_points():                                   # M8x25: head behind the plate, end in the slot
            bolts += cyl((x, Y_RS - M8.socket_head_h / 2, z), M8.socket_head_d / 2, M8.socket_head_h, (0, 1, 0)) + \
                cyl((x, (Y_RS - 14) / 2, z), 4.0, -14 - Y_RS, (0, 1, 0))
        hw["bolts"] = bolts
        top = z0 + CAR_H
        hw["belt"] = (belts.belt_segment((RUN_A, ZD), (RUN_A, top - 3), BELT_Y0, BELT_Y1)
                      + belts.belt_segment((RUN_A, top - CLAMP_L + 3), (RUN_A, Z_TOP), BELT_Y0, BELT_Y1)
                      + belts.belt_segment((RUN_B, ZD), (RUN_B, Z_TOP), BELT_Y0, BELT_Y1))
        hw["chassis_keepout"] = box(-60, 160, -100, 70, -10, Z_KEEP)
        return hw

    def info(self):
        lo, hi = car_limits()
        return {"L": L, "travel": round(hi - lo, 1), "carriage_z0_range": [round(lo, 1), round(hi, 1)],
                "hole_C": {"x": X_C, "z": ZD, "diameter": 10.0, "note": "through both 80 mm faces"},
                "drive_axis_z": ZD, "belt_loop_mm": round(2 * (Z_TOP - ZD) + 2 * math.pi * R_B),
                "shaft_mm": round(SHAFT_Y[1] - SHAFT_Y[0], 1),
                "shaft_cantilever_mm": round((BELT_Y0 + BELT_Y1) / 2 - (Y_RS + RS.proud), 1),
                "rs03_overhang_mm": [round(RS.body_d / 2 - X_C, 1), round(X_C + RS.body_d / 2 - 80, 1)],
                "lift_torque_Nm_5kg": round(5 * 9.81 * 1.1 * belts.pitch_diameter(TEETH) / 2 / 1000, 2)}

    # ---------------------------------------------------------------------------------------------- checks
    def checks(self):
        c = [("sweep is not vacuous (6 mm over-travel collides)", self._over_travel_detected)]
        step = self._rs03_step()
        if step:
            c += [("RS03 STEP: no overlap with plate, hub, bolts, extrusion", lambda: self._vendor_clearance(step)),
                  ("RS03 STEP: 8x M4 housing screws align", lambda: self._vendor_housing_holes(step)),
                  ("RS03 STEP: hub dowels align (with control)", lambda: self._vendor_hub(step, "pins")),
                  ("RS03 STEP: hub M4 screws align (with control)", lambda: self._vendor_hub(step, "screws"))]
        else:      # say so loudly: a mount that was never checked against the real part is not verified
            c.append(("RS03 STEP not found: 4 vendor-fit checks SKIPPED (put it in vendor/robstride/RS03.stp)",
                      lambda: CheckResult("vendor fit", True, {"skipped": True})))
        return c

    def _over_travel_detected(self):
        lo, _ = car_limits()
        v = overlap_volume(carriage(lo - 6.0), self.hardware(lo - 6.0)["drive_pulley"])
        return CheckResult("over-travel", v > 1.0, {"overlap_mm3": round(v, 1)})

    def _rs03_step(self):
        from agentcad.config import load_config
        d = load_config(self.path).vendor_dir
        return d / RS03_STEP if d and (d / RS03_STEP).exists() else None

    def _rs03_vendor(self, step):
        if not hasattr(self, "_vendor_cache"):
            raw = vendor.load_step(step)
            placed = vendor.place(raw, rs03_vendor_rotations(MOUNT_A0), (X_C, Y_RS - RS.step_mount_face_z, ZD))
            # output parts: in front of z = 25.5 in the vendor frame, within r 31 (margin: boxes sit at 25.9999)
            self._vendor_cache = vendor.split_solids(
                placed, lambda s: s.bounding_box().min.Y >= Y_RS - 9.6 and
                max(abs(s.bounding_box().min.X - X_C), abs(s.bounding_box().max.X - X_C)) <= 31)
        return self._vendor_cache

    def _vendor_clearance(self, step):
        out, housing = self._rs03_vendor(step)
        st = self.states()[1]
        hw = self.hardware(st)
        parts = {"rs03_mount": rs03_mount(), "drive_hub": drive_hub(), "bolts": hw["bolts"],
                 "extrusion": hw["extrusion"], "chassis_keepout": hw["chassis_keepout"]}
        res = {k: {"housing": vendor.clearance(housing, {k: v})[k], "output": vendor.clearance(out, {k: v})[k]}
               for k, v in parts.items()}
        ok = all(r["housing"]["overlap_mm3"] <= 1e-3 and r["output"]["overlap_mm3"] <= 1e-3 for r in res.values())
        return CheckResult("clearance", ok, res)

    def _vendor_housing_holes(self, step):
        _, housing = self._rs03_vendor(step)
        centers = [(x, Y_RS, z) for x, z in rs_screw_points()]
        probe = vendor.probes(centers, (0, -1, 0), M4.d / 2, 6.0)
        wrong = [(X_C + RS.mount_pcd / 2 * math.cos(math.radians(MOUNT_A0 + 22.5 + 45 * i)), Y_RS,
                  ZD + RS.mount_pcd / 2 * math.sin(math.radians(MOUNT_A0 + 22.5 + 45 * i))) for i in range(8)]
        control = vendor.probes(wrong, (0, -1, 0), M4.d / 2, 6.0)
        r = vendor.hole_alignment(housing, probe, control, vendor.expected_overlap(8, M4.d / 2, M4.tap_drill / 2, 6.0))
        return CheckResult("housing holes", r["passed"], r)

    def _vendor_hub(self, step, which):
        out, _ = self._rs03_vendor(step)
        y0 = Y_RS + RS.proud
        angles, r_probe, r_hole = (OUT_PINS, 1.95, 2.0) if which == "pins" else (OUT_SCREWS, 2.0, 1.75)
        pts = lambda degs: [(X_C + RS.output_pcd / 2 * math.cos(math.radians(a)), y0,
                             ZD + RS.output_pcd / 2 * math.sin(math.radians(a))) for a in degs]
        probe = vendor.probes(pts(angles), (0, -1, 0), r_probe, 5.0)
        control = vendor.probes(pts([a + 15 for a in angles]), (0, -1, 0), r_probe, 5.0)   # 15: lands on solid
        r = vendor.hole_alignment(out, probe, control, vendor.expected_overlap(len(angles), r_probe, r_hole, 5.0))
        return CheckResult(which, r["passed"], r)

    # ---------------------------------------------------------------------------------------------- outputs
    def bom(self):
        lo, hi = car_limits()
        rail_len = L - 5 - Z_KEEP
        n_rail_screws = 2 * int(rail_len // MG.pitch)
        g1, g2, g3 = "Drive", "Linear guide", "Fasteners"
        return [
            BomItem(1, "RobStride 03 actuator", "48 V, CAN; set a 1 N m torque limit", g1),
            BomItem(1, "48 V DC supply, >= 5 A; USB-CAN adapter + 120 ohm termination", "", g1),
            BomItem(1, f"8 mm hardened shaft, cut to {SHAFT_Y[1] - SHAFT_Y[0]:.1f} mm", "file a flat for the set screws", g1),
            BomItem(1, "GT2 20T pulley, 10 mm belt, 8 mm bore", "flange <= 19 mm", g1),
            BomItem(1, "GT2 20T toothed idler, 10 mm belt, 5 mm bore", "", g1),
            BomItem("1 m", "GT2 10 mm belt, fibreglass or steel reinforced", f"loop {self.info()['belt_loop_mm']} mm", g1),
            BomItem(3, "4 mm dowel pin, 4 x 10", "hub to RS03 output (holes 7 deep)", g1),
            BomItem(2, f"MGN12 rail, {rail_len:.0f} mm + MGN12H block", "", g2),
            BomItem(2, f"aluminium flat bar 10 x 15, {rail_len:.0f} mm", "rail spacers; drill 3.4 at 25 mm pitch", g2),
            BomItem(n_rail_screws, "M3x20 + M3 T-nut for 8 mm slot", "rails (MGN12 takes M3 only)", g2),
            BomItem(8, "M4x18 socket head", "RS03 to plate: 12 mm grip, 6 mm into its 8 mm threads", g3),
            BomItem(6, "M4x10 countersunk (ISO 10642)", "hub to RS03 output: 5 mm into its 6 mm threads", g3),
            BomItem(4, "M8x25 socket head + M8 T-nut (slot 8)", "plate to back face", g3),
            BomItem(4, "M8x12 socket head + M8 T-nut (slot 8)", "top cap", g3),
            BomItem(8, "M3x12 socket head", "carriage to blocks: 3.1 mm into 3.5 mm threads", g3),
            BomItem(2, "M3x6 set screw + M3 nut", "hub to shaft", g3),
            BomItem(1, "M5x45 + nyloc + washers", "top idler axle", g3),
            BomItem(16, "M4 heat-set insert (5.6 mm hole, <= 6 mm long)", "arm grid", g3),
            BomItem(4, "zip tie, <= 3 mm wide", "belt ends", g3),
        ]

    def presentation(self):
        lo, hi = car_limits()
        z0 = lo + 0.55 * (hi - lo)
        zb = z0 + CAR_H - BLK_Z_TOP - MG.block_l / 2
        b0, s0 = linear.block(RAIL_X[0], RAIL_Y0, zb, detailed=True)
        b1, s1 = linear.block(RAIL_X[1], RAIL_Y0, zb, detailed=True)
        hw = self.hardware(z0)
        zmid = z0 + CAR_H - CLAMP_L / 2
        xa0, xa1 = X_C - belts.pitch_diameter(TEETH) / 2 - belts.BELT_T, X_C - belts.pitch_diameter(TEETH) / 2
        belt = (box(X_C + belts.pitch_diameter(TEETH) / 2, X_C + belts.pitch_diameter(TEETH) / 2 + belts.BELT_T,
                    BELT_Y0, BELT_Y1, ZD, Z_TOP) + box(xa0, xa1, BELT_Y0, BELT_Y1, ZD, zmid - 1)
                + box(xa0, xa1, BELT_Y0, BELT_Y1, zmid + 1, Z_TOP)
                + belts.belt_arc((X_C, Z_TOP), TEETH, BELT_Y0, BELT_Y1, True)
                + belts.belt_arc((X_C, ZD), TEETH, BELT_Y0, BELT_Y1, False))
        screws_c = [socket_screw((rx + dx, PLATE_Y0 + CAR_T - 9.1, zb + dz), (0, -1, 0), M3, 12)
                    for rx in RAIL_X for dx in (-10, 10) for dz in (-10, 10)]
        screws_p = [socket_screw((x, Y_RS - M8.socket_head_h, z), (0, 1, 0), M8, 25) for x, z in tnut_points()]
        screws_rs = [socket_screw((x, -FACE_Y - 6.0, z), (0, -1, 0), M4, 18) for x, z in rs_screw_points()]
        screws_cap = [socket_screw((x, -26.0 - M8.socket_head_h, z), (0, 1, 0), M8, 12) for x in RAIL_X for z in (L - 12, L - 30)]
        U = lambda ss: bd.Compound(ss)
        step = self._rs03_step()
        if step:
            rs_out, rs_body = self._rs03_vendor(step)
        else:
            rs_body, rs_out = hw["rs03"], cyl((X_C, Y_RS + RS.proud / 2, ZD), RS.output_d / 2, RS.proud, (0, 1, 0))
        return [
            ShowPart("extrusion", extrusions.detailed_slot8(L, holes=[(X_C, ZD, 10.0)]), "aluminium", label="4080 aluminium extrusion (8 mm slot)"),
            ShowPart("spacers", hw["spacers"], "aluminium", (0, 30, 0), "10 mm spacer bars"),
            ShowPart("rails", linear.rail(RAIL_X[0], RAIL_Y0, Z_KEEP, L - 5, True) + linear.rail(RAIL_X[1], RAIL_Y0, Z_KEEP, L - 5, True),
                     "steel", (0, 65, 0), "MGN12 rails"),
            ShowPart("blocks", b0 + b1, "steel", (0, 100, 0), "MGN12H blocks"),
            ShowPart("block_seals", s0 + s1, "seal", (0, 100, 0)),
            ShowPart("belt", belt, "rubber", label="GT2 10 mm belt"),
            ShowPart("carriage", carriage(z0), "printed", (0, 150, 0), "Carriage (printed)", print_axis="Y"),
            ShowPart("carriage_screws", U(screws_c), "black_oxide", (0, 205, 0)),
            ShowPart("drive_pulley", belts.pulley_detailed((X_C, ZD), TEETH, SHAFT_D, BELT_Y0, BELT_Y1, FLANGE_R, hub=(8.0, 7.0)),
                     "aluminium", (0, 45, 0), "20T drive pulley"),
            ShowPart("shaft", hw["shaft"], "chrome", label="8 mm shaft through the extrusion"),
            ShowPart("rs03_mount", rs03_mount(), "printed", (0, -50, 0), "Actuator mount plate (printed)", print_axis="Y"),
            ShowPart("rs03_screws", U(screws_rs), "black_oxide", (0, -50, 0)),
            ShowPart("plate_screws", U(screws_p), "black_oxide", (0, -75, 0)),
            ShowPart("drive_hub", drive_hub(), "printed", (0, -100, 0), "Output hub (printed)", print_axis="Y"),
            ShowPart("rs03", rs_body, "black", (0, -150, 0), "RobStride 03 actuator"),
            ShowPart("rs03_output", rs_out, "bright", (0, -150, 0)),
            ShowPart("top_cap", top_cap(), "printed", (0, 0, 75), "Top cap with tensioner (printed)", print_axis="Z"),
            ShowPart("cap_screws", U(screws_cap), "black_oxide", (0, -25, 75)),
            ShowPart("top_idler", belts.pulley_detailed((X_C, Z_TOP), TEETH, 5.0, BELT_Y0, BELT_Y1, FLANGE_R), "aluminium",
                     (0, 0, 38), "20T idler"),
        ]

    def shots(self):
        return super().shots() + [
            Shot("detail_actuator", "Detail: RobStride 03 on its mount", False, (0.85, 0.95, -0.38), resolution=(2400, 2400),
                 frame_box=((-15, -100, 45), (100, 25, 165))),
            Shot("detail_pulley", "Detail: drive pulley and belt", False, (-0.55, -1.0, -0.30), resolution=(2400, 2400),
                 hidden=("carriage", "carriage_screws"), frame_box=((15, 0, 60), (70, 45, 150)))]

    def render_details(self):
        return [{"z": (Z_KEEP - 5, ZD + 45), "view": (15, 60), "title": "bottom, front: 20T drive pulley", "hide": ("carriage",)},
                {"z": (Z_KEEP - 5, ZD + 70), "view": (15, -130), "title": "bottom, back: RS03 on its plate"},
                {"z": (L - 50, L + 50), "view": (20, 55), "title": "top cap: 20T idler in tension slots"}]


DESIGN = ZLift(__file__)
