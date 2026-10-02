"""Surface-continuity grading (digital modelling / Class-A).

Works on sampled geometry exported from the CAD tool (e.g. NX/CATIA/Blender dumping
points + derivatives along a shared edge), so grading is tool-agnostic.
"""
from __future__ import annotations

import numpy as np


def _unit(v):
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(n == 0, 1, n)


def g0_gap(pts_a: np.ndarray, pts_b: np.ndarray) -> float:
    """Max positional gap (model units, typically mm) between matched edge samples."""
    return float(np.max(np.linalg.norm(pts_a - pts_b, axis=-1)))


def g1_angle_deg(tan_a: np.ndarray, tan_b: np.ndarray) -> float:
    """Max tangent/normal deviation (deg) across the join. Sign-insensitive."""
    d = np.abs(np.sum(_unit(tan_a) * _unit(tan_b), axis=-1)).clip(0, 1)
    return float(np.degrees(np.max(np.arccos(d))))


def curvature_jump(curv_a: np.ndarray, curv_b: np.ndarray) -> float:
    """Max relative curvature difference across join (G2 proxy), in [0, inf)."""
    denom = np.maximum(np.maximum(np.abs(curv_a), np.abs(curv_b)), 1e-9)
    return float(np.max(np.abs(curv_a - curv_b) / denom))


def curvature_of_polyline(p: np.ndarray) -> np.ndarray:
    """Discrete curvature of a 2D/3D polyline sampled at ~uniform parameter."""
    d1 = np.gradient(p, axis=0)
    d2 = np.gradient(d1, axis=0)
    if p.shape[1] == 2:
        cross = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]
    else:
        cross = np.linalg.norm(np.cross(d1, d2), axis=1)
    return cross / np.maximum(np.linalg.norm(d1, axis=1) ** 3, 1e-12)


def grade_join(pts_a, pts_b, tan_a, tan_b, curv_a, curv_b, required: str,
               g0_tol_mm=0.005, g1_tol_deg=0.1, g2_tol_rel=0.05) -> dict:
    """`required` in {'G0','G1','G2'}. Each level also requires those below it."""
    res = {"g0_gap_mm": g0_gap(pts_a, pts_b),
           "g1_deg": g1_angle_deg(tan_a, tan_b),
           "g2_rel": curvature_jump(curv_a, curv_b)}
    ok = {"G0": res["g0_gap_mm"] <= g0_tol_mm,
          "G1": res["g1_deg"] <= g1_tol_deg,
          "G2": res["g2_rel"] <= g2_tol_rel}
    levels = ["G0", "G1", "G2"]
    achieved = "none"
    for lv in levels:
        if ok[lv]:
            achieved = lv
        else:
            break
    res["achieved"] = achieved
    res["score"] = levels.index(achieved) + 1 if achieved != "none" else 0
    res["score"] = min(res["score"], levels.index(required) + 1) / (levels.index(required) + 1)
    return res
