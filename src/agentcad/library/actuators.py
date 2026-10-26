"""Actuators.

RobStride 03 (RS03), quasi-direct-drive, 9:1. Sources, which agree with each other:
  * RobStride's STEP model: github.com/RobStride/Product_Information, Product Literature/CAN2.0/RS03/RS03.stp
    (file dated 2025-08-20; axis +Z, output toward +Z, mounting face at z = 35, first M4 hole at 22.5 deg)
  * RS03 user manual, section 1.1 "Outline and mounting dimensions" (RS03User Manual261013.pdf)
  * Electrical (manual 1.3): rated 20 N m at 100 rpm, peak 60 N m, no-load 200 rpm +-10 %, 48 V (24-60 V), CAN.
  WARNING: a widely shared drawing with a 120 mm body, 10x M4 on 106 and 9x M5 + 6 mm dowels on 36 is the RS04,
  not the RS03. A mount designed from it does not fit an RS03. Always check against the STEP (agentcad.vendor).
  The RS03 has no brake: a vertical axis drops when unpowered.

NEMA 17: 42.3 mm square, M3 on a 31 mm square, 22 mm pilot, 5 mm shaft (NEMA ICS 16).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..geom import cyl


@dataclass(frozen=True)
class RS03:
    body_d: float = 100.5               # across the mounting lugs (STEP)
    length: float = 54.1                # mounting face to rear cover (manual)
    housing_len: float = 39.5           # manual
    rear_d: float = 79.5                # manual
    mount_pcd: float = 98.0             # 8x M4, 8 deep (manual "8-M4 v8 EQS")
    mount_n: int = 8
    mount_a0_vendor: float = 22.5       # angle of the first mounting hole in the vendor model
    pilot_d: float = 70.0               # manual; ~71 mm right at the face (base fillet, seen in the STEP)
    proud: float = 2.5                  # pilot and output flange stand 2.5 mm proud of the mounting face
    output_d: float = 47.0              # STEP
    output_pcd: float = 30.36           # 6x M4 6 deep + 3x 4 mm dowel holes 7 deep (manual)
    output_screws_vendor: tuple = (30, 90, 150, 210, 270, 330)
    output_pins_vendor: tuple = (60, 180, 300)
    step_mount_face_z: float = 35.0     # vendor model: mounting face plane


RS03_SPEC = RS03()


def rs03_envelope(center_xz, face_y: float, s: RS03 = RS03_SPEC):
    """Interference envelope for an RS03 whose axis runs along -y from the mounting face at ``face_y``
    (output toward +y). Full cylinder of the lug diameter: conservative."""
    x, z = center_xz
    body = cyl((x, face_y - s.housing_len / 2, z), s.body_d / 2, s.housing_len, (0, 1, 0))
    body += cyl((x, face_y - s.housing_len - (s.length - s.housing_len) / 2, z), s.rear_d / 2, s.length - s.housing_len,
                (0, 1, 0))
    return body + cyl((x, face_y + s.proud / 2, z), s.pilot_d / 2, s.proud, (0, 1, 0))


def rs03_vendor_rotations(mount_a0: float, s: RS03 = RS03_SPEC):
    """Rotations for ``agentcad.vendor.place`` that put the vendor RS03's axis along +y (output toward +y) with its
    first mounting hole at ``mount_a0`` degrees in the x-z plane. Then translate by
    (x, face_y - s.step_mount_face_z, z). Rotating the housing also rotates the output pattern: the output
    holes land at -(vendor angle + mount_a0 - mount_a0_vendor)."""
    return [("Z", mount_a0 - s.mount_a0_vendor), ("X", -90)]


def rs03_output_angles(mount_a0: float, s: RS03 = RS03_SPEC):
    """Output screw and dowel angles (x-z plane, degrees) after ``rs03_vendor_rotations``."""
    turn = mount_a0 - s.mount_a0_vendor
    f = lambda a: (-(a + turn)) % 360
    return tuple(sorted(f(a) for a in s.output_screws_vendor)), tuple(sorted(f(a) for a in s.output_pins_vendor))


NEMA17 = {"square": 42.3, "hole_square": 31.0, "pilot_d": 22.0, "shaft_d": 5.0, "screw": "M3"}
