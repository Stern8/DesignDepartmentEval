"""Render grading: light/shadow/studio-setup checks from image statistics alone.

These are deliberately coarse, deterministic proxies; pair with a VLM rubric for
subjective items (see DESIGN.md). Every function takes a PIL image.
"""
from __future__ import annotations

import numpy as np
from PIL import Image


def luminance(img: Image.Image) -> np.ndarray:
    a = np.asarray(img.convert("RGB"), dtype=float) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return lin @ np.array([0.2126, 0.7152, 0.0722])


def key_light_direction(img: Image.Image, mask: np.ndarray | None = None) -> float:
    """Horizontal bias of brightness over the subject: -1 (lit from left) .. +1 (from right)."""
    y = luminance(img)
    if mask is None:
        mask = y > 0.02
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return 0.0
    mid = (xs.min() + xs.max()) / 2
    left, right = y[ys, xs][xs < mid].mean(), y[ys, xs][xs >= mid].mean()
    return float((right - left) / max(right + left, 1e-9))


def contrast_ratio(img: Image.Image, p_hi=99, p_lo=1) -> float:
    y = luminance(img)
    return float((np.percentile(y, p_hi) + 0.05) / (np.percentile(y, p_lo) + 0.05))


def clipped_fraction(img: Image.Image) -> dict:
    a = np.asarray(img.convert("RGB"))
    return {"highlights": float((a.max(axis=-1) >= 253).mean()),
            "shadows": float((a.max(axis=-1) <= 2).mean())}


def ground_shadow_present(img: Image.Image, floor_rows: slice, floor_cols: slice,
                          min_drop: float = 0.25) -> bool:
    """A contact shadow exists if the darkest floor band is >= min_drop darker than its median."""
    y = luminance(img)[floor_rows, floor_cols]
    return bool(np.percentile(y, 2) < (1 - min_drop) * np.median(y))


def mean_color_temperature_bias(img: Image.Image) -> float:
    """>0 warm (R>B), <0 cool. Normalised to [-1, 1]."""
    a = np.asarray(img.convert("RGB"), dtype=float)
    r, b = a[..., 0].mean(), a[..., 2].mean()
    return float((r - b) / max(r + b, 1e-9))
