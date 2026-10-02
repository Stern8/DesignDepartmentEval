"""Graders for from-scratch render-engine tasks. Each: (art, params) -> float in [0, 1]."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from . import optics, render
from .scene_state import Artifacts


def sandbox(art: Artifacts, p: dict) -> float:
    f = Path(art.outdir) / "run.json"
    if not f.exists():
        return 0.0
    m = json.loads(f.read_text())
    return float(m["returncode"] == 0 and not m["timed_out"] and m["seconds"] <= p.get("max_seconds", 60))


def furnace_error(art: Artifacts, p: dict) -> float:
    """White-furnace: object pixels must be 1.0 within tol (mean and 95th-percentile pixel error)."""
    try:
        img = np.load(Path(art.outdir) / "furnace.npy")
        mask = np.load(Path(art.outdir) / "mask.npy").astype(bool)
    except (OSError, ValueError):
        return 0.0
    if img.ndim != 3 or mask.shape != img.shape[:2] or mask.sum() < 50 or not np.isfinite(img).all():
        return 0.0
    err = np.abs(img[mask] - 1.0)
    tol = p.get("tol", 0.02)
    mean_ok = abs(img[mask].mean() - 1.0) <= tol
    p95 = np.percentile(err, 95)
    return float(mean_ok) * float(max(0.0, 1 - max(0.0, p95 - tol) / (4 * tol)))


def prism_deviation(art: Artifacts, p: dict) -> float:
    try:
        d = json.loads((Path(art.outdir) / "deviation.json").read_text())
        w = np.array(d["wavelengths_nm"], float)
        ang = np.array(d["exit_deviation_deg"], float)
    except (OSError, ValueError, KeyError):
        return 0.0
    expected = np.arange(450, 651, 25.0)
    if w.shape != expected.shape or not np.allclose(w, expected) or ang.shape != w.shape or not np.isfinite(ang).all():
        return 0.0
    return optics.grade_prism_render(None, w, ang, p.get("material", "SF11"), p.get("apex", 60.0),
                                     p.get("incidence", 65.0), p.get("tol_deg", 0.15))["score"]


def caustic(art: Artifacts, p: dict) -> float:
    """Top-down ortho render, world [-4,4]^2, glass sphere (r=1) at origin, light overhead.
    Expect: bright focused peak near the origin, much brighter than the floor, ringed by shadow."""
    try:
        img = Image.open(Path(art.outdir) / "render.png").convert("RGB")
    except OSError:
        return 0.0
    y = render.luminance(img)
    h, w = y.shape
    xs = (np.arange(w) + 0.5) / w * 8 - 4
    zs = (np.arange(h) + 0.5) / h * 8 - 4
    X, Z = np.meshgrid(xs, zs)
    R = np.hypot(X, Z)
    floor = R > 2.0                                      # outside any sphere-silhouette pixels
    inner = R <= 1.0
    if not inner.any() or not floor.any():
        return 0.0
    floor_med = np.median(y[floor]) + 1e-6
    thr = np.percentile(y[inner], 99)
    peak_ratio = thr / floor_med
    ys, xs_ = np.nonzero((y >= thr) & inner)
    centroid_off = np.hypot(X[ys, xs_].mean(), Z[ys, xs_].mean())
    ring = (R > 1.0) & (R < 1.6)
    shadow = np.median(y[ring]) < 0.8 * floor_med
    s_peak = min(1.0, max(0.0, (peak_ratio - 1) / (p.get("min_peak_ratio", 5.0) - 1)))
    s_pos = float(centroid_off <= p.get("max_offset", 0.4))
    return round(s_peak * (0.5 + 0.3 * s_pos + 0.2 * float(shadow)), 3)  # position/shadow only count given a real peak
