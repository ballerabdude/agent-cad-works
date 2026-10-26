"""Kernel-independent mesh validation (trimesh + manifold3d).

Every check here takes plain arrays (points, triangles) so neither kernel's self-report is
trusted. Two independent libraries are used: trimesh (topology, winding, volume, ray
parity) and manifold3d (its own manifold reconstruction).
"""

from __future__ import annotations

import numpy as np
import trimesh
import manifold3d


def _edge_incidence(tris: np.ndarray) -> tuple[int, int]:
    """Count boundary edges (1 incident face) and non-manifold edges (>2) on merged vertices."""
    e = np.sort(np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]]), axis=1)
    _, counts = np.unique(e, axis=0, return_counts=True)
    return int((counts == 1).sum()), int((counts > 2).sum())


def ray_parity_inward(mesh: trimesh.Trimesh, max_tris: int = 4000, seed: int = 0) -> tuple[int, int]:
    """Count triangles whose normal points into the solid.

    A ray is cast from just off each sampled triangle's centroid along its normal; an odd number
    of hits on the rest of the mesh means the normal points inward. Returns (inward, sampled).
    """
    n = len(mesh.faces)
    idx = np.arange(n)
    if n > max_tris:
        idx = np.random.default_rng(seed).choice(n, max_tris, replace=False)
    normals = mesh.face_normals[idx]
    scale = float(np.linalg.norm(mesh.extents)) or 1.0
    origins = mesh.triangles_center[idx] + normals * (1e-6 * scale)
    _, ray_idx, _ = mesh.ray.intersects_location(origins, normals, multiple_hits=True)
    hits = np.bincount(ray_idx, minlength=len(idx))
    return int((hits % 2 == 1).sum()), int(len(idx))


def check_mesh(points: np.ndarray, tris: np.ndarray, ref_normals: np.ndarray | None = None,
               exact_volume: float | None = None, ray_check: bool = True, drop_degenerate: bool = False) -> dict:
    """Validate a triangle soup as a printable solid.

    ref_normals: optional per-triangle normals of the source exact surface (outward). Triangles
    whose geometric normal opposes them are counted as `flipped_vs_surface`.
    """
    points = np.asarray(points, dtype=np.float64)
    tris = np.asarray(tris, dtype=np.int64)
    out: dict = {"triangles": int(len(tris)), "points_raw": int(len(points))}

    g = np.cross(points[tris[:, 1]] - points[tris[:, 0]], points[tris[:, 2]] - points[tris[:, 0]])
    area2 = np.linalg.norm(g, axis=1)
    out["degenerate_tris"] = int((area2 <= 1e-14 * max(1.0, float(area2.max(initial=0.0)))).sum())
    if ref_normals is not None:
        d = np.einsum("ij,ij->i", g, np.asarray(ref_normals, dtype=np.float64))
        out["flipped_vs_surface"] = int((d < 0).sum())

    # Merge coincident vertices (kernels emit per-face vertex copies) before topology checks.
    m = trimesh.Trimesh(points, tris, process=True, validate=False)
    if drop_degenerate:  # what slicers do on load (OrcaSlicer drops zero-area facets silently)
        m.update_faces(m.nondegenerate_faces())
        m.remove_unreferenced_vertices()
    out["points_merged"] = int(len(m.vertices))
    b, nm = _edge_incidence(np.asarray(m.faces))
    out["boundary_edges"] = b
    out["nonmanifold_edges"] = nm
    out["watertight"] = bool(m.is_watertight)
    out["winding_consistent"] = bool(m.is_winding_consistent)
    out["mesh_volume"] = float(m.volume)
    out["outward"] = bool(m.volume > 0)
    out["bodies"] = int(m.body_count)
    if exact_volume:
        out["mesh_vol_rel_err"] = abs(m.volume - exact_volume) / abs(exact_volume)

    try:
        man = manifold3d.Manifold(manifold3d.Mesh(
            vert_properties=np.asarray(m.vertices, dtype=np.float32),
            tri_verts=np.asarray(m.faces, dtype=np.uint32)))
        st = man.status()
        out["manifold3d_status"] = st.name
        out["manifold3d_ok"] = st == manifold3d.Error.NoError
        out["manifold3d_volume"] = float(man.volume()) if out["manifold3d_ok"] else None
    except Exception as ex:  # noqa: BLE001 - record any checker failure as data
        out["manifold3d_status"] = f"exception: {ex}"
        out["manifold3d_ok"] = False

    if ray_check and out["watertight"]:
        inward, sampled = ray_parity_inward(m)
        out["ray_inward_tris"] = inward
        out["ray_sampled"] = sampled

    out["printable"] = bool(out["watertight"] and out["winding_consistent"] and out["outward"]
                            and out["nonmanifold_edges"] == 0 and out["manifold3d_ok"]
                            and out.get("ray_inward_tris", 0) == 0)
    return out


def write_stl(points: np.ndarray, tris: np.ndarray, path: str) -> int:
    """Write a binary STL without any repair, so defects survive into the file."""
    trimesh.Trimesh(np.asarray(points, dtype=np.float64), np.asarray(tris), process=False).export(path)
    import os
    return os.path.getsize(path)
