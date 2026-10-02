"""CMF colour grading: exact hex hits, CIEDE2000 distance, region sampling."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"expected 6-digit hex, got {h!r}")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def srgb_to_lab(rgb) -> np.ndarray:
    c = np.asarray(rgb, dtype=float) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])], axis=-1)


def delta_e2000(lab1, lab2) -> float:
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb**7 / (Cb**7 + 25**7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    else:
        dhp = h2p - h1p
        dhp -= 360 * round(dhp / 360)
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2))
    Lbp, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbp = (h1p + h2p) / 2
    else:
        hbp = (h1p + h2p + (360 if h1p + h2p < 360 else -360)) / 2
    T = (1 - 0.17 * math.cos(math.radians(hbp - 30)) + 0.24 * math.cos(math.radians(2 * hbp))
         + 0.32 * math.cos(math.radians(3 * hbp + 6)) - 0.20 * math.cos(math.radians(4 * hbp - 63)))
    dth = 30 * math.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cbp**7 / (Cbp**7 + 25**7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / math.sqrt(20 + (Lbp - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    Rt = -math.sin(math.radians(2 * dth)) * Rc
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2
                     + Rt * (dCp / Sc) * (dHp / Sh))


def delta_e_hex(a: str, b: str) -> float:
    return delta_e2000(srgb_to_lab(hex_to_rgb(a)), srgb_to_lab(hex_to_rgb(b)))


def region_median_hex(img: Image.Image, box: tuple[int, int, int, int]) -> str:
    """Median colour of a pixel box (left, top, right, bottom); robust to AA / noise."""
    px = np.asarray(img.convert("RGB").crop(box)).reshape(-1, 3)
    r, g, b = np.median(px, axis=0).astype(int)
    return f"{r:02X}{g:02X}{b:02X}"


def score_hex(target: str, got: str, exact_tol: float = 0.0, pass_de: float = 1.0,
              zero_de: float = 5.0) -> dict:
    """Exact match -> 1.0. Otherwise linear falloff between pass_de and zero_de (CIEDE2000)."""
    exact = target.lstrip("#").upper() == got.lstrip("#").upper()
    de = 0.0 if exact else delta_e_hex(target, got)
    if exact or de <= exact_tol:
        s = 1.0
    elif de <= pass_de:
        s = 0.8
    else:
        s = max(0.0, 0.8 * (zero_de - de) / (zero_de - pass_de))
    return {"exact": exact, "delta_e": round(de, 3), "score": round(s, 3)}
