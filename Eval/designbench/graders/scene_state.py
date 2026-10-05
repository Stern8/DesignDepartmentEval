"""Graders over scene_state_v1 JSON exported from Blender (see designbench/blender/export_state.py).

Each grader: (art: Artifacts, params: dict) -> float in [0, 1].
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from . import color


@dataclass
class Artifacts:
    state: dict = field(default_factory=dict)
    baseline: dict = field(default_factory=dict)
    outdir: str = "."


def _obj(state, name):
    for o in state.get("objects", []):
        if o["name"] == name:
            return o
    return None


def hex_exact(art: Artifacts, p: dict) -> float:
    mat = art.state.get("materials", {}).get(p["material"])
    if not mat:
        return 0.0
    return color.score_hex(p["target"], color.linear_to_hex(mat["base_color"]))["score"]


def view_transform_standard(art: Artifacts, p: dict) -> float:
    s = art.state
    return float(s.get("view_transform") == "Standard" and s.get("look", "None") == "None"
                 and abs(s.get("exposure", 0.0)) < 1e-6 and abs(s.get("gamma", 1.0) - 1.0) < 1e-6)


def lights_untouched(art: Artifacts, p: dict) -> float:
    a = {l["name"]: l for l in art.state.get("lights", [])}
    b = {l["name"]: l for l in art.baseline.get("lights", [])}
    if a.keys() != b.keys():
        return 0.0
    for n, l in b.items():
        o = a[n]
        for k in ("energy",):
            if abs(o[k] - l[k]) > 1e-6 * max(1, abs(l[k])):
                return 0.0
        for k in ("color", "location", "rotation"):
            if np.max(np.abs(np.array(o[k]) - np.array(l[k]))) > 1e-6:
                return 0.0
    return 1.0


def package_dims(art: Artifacts, p: dict) -> float:
    """All package targets (mm) must be within tol (default 1%); score = fraction satisfied."""
    s = art.state
    k = 1000.0 * s.get("unit_scale", 1.0)
    body, fl, rl = _obj(s, "Body"), _obj(s, "Wheel_FL"), _obj(s, "Wheel_RL")
    if not (body and fl and rl):
        return 0.0
    pk, tol = p["package"], p.get("tol", 0.01)
    bmin, bmax = np.array(body["bbox_min"]) * k, np.array(body["bbox_max"]) * k
    wheels_min = np.minimum(np.array(fl["bbox_min"]), np.array(rl["bbox_min"])) * k
    front_x = bmax[1]  # Y is vehicle length axis, +Y forward
    vals = {
        "length_mm": bmax[1] - bmin[1],
        "height_mm": bmax[2] - min(bmin[2], wheels_min[2]),
        "wheelbase_mm": abs(fl["location"][1] - rl["location"][1]) * k,
        "wheel_dia_in": (np.array(fl["bbox_max"]) - np.array(fl["bbox_min"]))[2] * k / 25.4,
        "clearance_mm": bmin[2] - wheels_min[2],
        "front_overhang_mm": front_x - fl["location"][1] * k,
    }
    ok = []
    for key, target in pk.items():
        if key == "front_overhang_max_mm":
            ok.append(vals["front_overhang_mm"] <= target)
        else:
            ok.append(abs(vals[key] - target) <= tol * target)
    return sum(ok) / len(ok) if ok else 0.0


def rotation_limits(art: Artifacts, p: dict) -> float:
    o = _obj(art.state, p["object"])
    if not o:
        return 0.0
    ax = "xyz"[p["axis"]]
    for c in o.get("constraints", []):
        if c["type"] == "LIMIT_ROTATION" and c.get(f"use_limit_{ax}"):
            lo, hi = math.degrees(c[f"min_{ax}"]), math.degrees(c[f"max_{ax}"])
            return float(abs(lo - p["min_deg"]) < 0.5 and abs(hi - p["max_deg"]) < 0.5)
    return 0.0


def hinge_axis_error(art: Artifacts, p: dict) -> float:
    """Animated local axis, rotated to world by the object's rest orientation, must align with target."""
    o = _obj(art.state, p["object"])
    if not o or "rotation_matrix" not in o:
        return 0.0
    local = np.zeros(3)
    local[p["axis"]] = 1.0
    world = np.array(o["rotation_matrix"]) @ local
    t = np.array(p["target_axis"], float)
    ang = math.degrees(math.acos(min(1.0, abs(world @ t) / (np.linalg.norm(world) * np.linalg.norm(t)))))
    pivot_err = np.linalg.norm(np.array(o["location"]) - np.array(p["hinge_point"]))
    return float(ang <= p.get("tol_deg", 1.0) and pivot_err <= p.get("tol_m", 0.01))


def duration(art: Artifacts, p: dict) -> float:
    o = _obj(art.state, p["object"])
    kf = (o or {}).get("animation", {}).get("rotation_euler", {}).get(str(p["axis"]))
    if not kf or len(kf) < 2:
        return 0.0
    secs = (kf[-1][0] - kf[0][0]) / art.state.get("fps", 24)
    peak = max(abs(math.degrees(v)) for _, v in kf)
    return float(abs(secs - p["seconds"]) <= 0.05 and abs(peak - p["max_deg"]) <= 0.5)


def no_intersection_all_frames(art: Artifacts, p: dict) -> float:
    frames = art.state.get("intersections_by_frame", {}).get(p["object"])
    if not frames:
        return 0.0
    return 1.0 - sum(1 for n in frames if n > 0) / len(frames)
