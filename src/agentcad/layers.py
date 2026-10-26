"""Layer-by-layer printability analysis of an STL in its print orientation, independent of any slicer.

``islands``: cross-section pieces with (almost) nothing under them in the previous layer. A part with islands
prints in mid-air without supports. This catches thin slivers that the slicer's own "floating regions" warning
misses or over-reports.
``unsupported``: area overhanging the previous layer by more than a 45-degree slope.
"""

import numpy as np
import trimesh
from shapely.ops import unary_union


def analyse(stl_path, layer: float = 0.2, min_area: float = 1.0) -> dict:
    m = trimesh.load(stl_path)
    zs = np.arange(layer / 2, m.bounds[1][2], layer)
    secs = m.section_multiplane(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], heights=zs)
    prev, islands, unsupported = None, [], []
    for z, s in zip(zs, secs):
        cur = unary_union(list(s.polygons_full)) if s is not None else None
        if cur is not None and prev is not None:
            for p in getattr(cur, "geoms", [cur]):
                if p.area > 0.02 and p.intersection(prev.buffer(layer)).area < 0.05 * p.area:
                    islands.append({"z": round(float(z), 2), "area": round(p.area, 2),
                                    "bounds": [round(v, 1) for v in p.bounds]})
            un = cur.difference(prev.buffer(layer))
            for g in getattr(un, "geoms", [un]):
                if g.area > min_area:
                    unsupported.append({"z": round(float(z), 2), "area": round(g.area, 1),
                                        "bounds": [round(v, 1) for v in g.bounds]})
        prev = cur
    unsupported.sort(key=lambda r: -r["area"])
    return {"islands": islands, "unsupported_top": unsupported[:10],
            "unsupported_total_mm2": round(sum(r["area"] for r in unsupported), 1)}
