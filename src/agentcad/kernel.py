"""OCCT (build123d / OCP) adapter: measurement, validity and tessellation.

``measure`` reports what the kernel itself says about a shape. ``agentcad.meshcheck`` then re-checks the
tessellated mesh with two independent libraries, because the kernel's own validity flag has passed shapes that
were not printable (an edge-only joint between two bodies, for example).
"""

from __future__ import annotations

import numpy as np
import build123d as bd
from OCP.BRep import BRep_Tool
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp, BRepGProp_Face
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepTools import BRepTools
from OCP.Bnd import Bnd_Box
from OCP.GProp import GProp_GProps
from OCP.TopAbs import TopAbs_REVERSED
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Pnt, gp_Vec


def measure(shape: bd.Shape) -> dict:
    """Volume, optimal bounding box, topology counts and the kernel's validity verdicts."""
    if shape.wrapped is None or not shape.faces():
        return {"volume": 0.0, "bbox": None, "faces": 0, "solids": 0, "kernel_valid": False, "closed_solid": False}
    s = shape.wrapped
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(s, props, 1e-9)
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(s, b, False, False)
    lo, hi = b.CornerMin(), b.CornerMax()
    return {
        "volume": props.Mass(),
        "bbox": [[lo.X(), lo.Y(), lo.Z()], [hi.X(), hi.Y(), hi.Z()]],
        "faces": len(shape.faces()),
        "solids": len(shape.solids()),
        "kernel_valid": bool(BRepCheck_Analyzer(s).IsValid()),
        "closed_solid": len(shape.solids()) == 1 and all(BRep_Tool.IsClosed_s(sh.wrapped) for sh in shape.shells()),
    }


def tessellate(shape: bd.Shape, chord: float = 0.01, angle_deg: float = 25.0):
    """Mesh with BRepMesh. Returns ``(points, tris, ref_normals)`` with outward winding; ``ref_normals`` are
    the exact surface normals at each triangle, independent of the triangle's own winding."""
    s = shape.wrapped
    BRepTools.Clean_s(s)                      # drop cached triangulation so the requested chord is used
    BRepMesh_IncrementalMesh(s, chord, False, np.radians(angle_deg), True)
    pts, tris, refs, base = [], [], [], 0
    for f in shape.faces():
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(f.wrapped, loc)
        if tri is None:
            continue
        trsf = loc.Transformation()
        rev = f.wrapped.Orientation() == TopAbs_REVERSED
        nodes = np.array([[p.X(), p.Y(), p.Z()] for p in
                          (tri.Node(i).Transformed(trsf) for i in range(1, tri.NbNodes() + 1))])
        uv = np.array([[tri.UVNode(i).X(), tri.UVNode(i).Y()] for i in range(1, tri.NbNodes() + 1)])
        gf = BRepGProp_Face(f.wrapped)
        for i in range(1, tri.NbTriangles() + 1):
            a, b, c = tri.Triangle(i).Get()
            if rev:
                b, c = c, b
            tris.append((base + a - 1, base + b - 1, base + c - 1))
            u, v = uv[[a - 1, b - 1, c - 1]].mean(axis=0)
            p, n = gp_Pnt(), gp_Vec()
            gf.Normal(float(u), float(v), p, n)
            refs.append((n.X(), n.Y(), n.Z()))
        pts.append(nodes)
        base += len(nodes)
    return np.vstack(pts), np.array(tris), np.array(refs)


def overlap_volume(a: bd.Shape, b: bd.Shape) -> float:
    """Volume of ``a & b``. An empty intersection returns 0.0. A boolean that raises returns ``inf``, so a
    failed check is reported as an interference to investigate and never passes silently."""
    try:
        r = a & b
        return 0.0 if r is None or not r.faces() else float(r.volume)
    except Exception:  # noqa: BLE001
        return float("inf")


def rotate_xyz(shape: bd.Shape, rot: tuple[float, float, float]) -> bd.Shape:
    """Rotate about world X, then Y, then Z (degrees). Used for print orientation."""
    rx, ry, rz = rot
    return shape.rotate(bd.Axis.X, rx).rotate(bd.Axis.Y, ry).rotate(bd.Axis.Z, rz)
