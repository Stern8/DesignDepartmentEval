"""Physics references for from-scratch render-engine tasks (caustics, dispersion, spectral)."""
from __future__ import annotations

import math

import numpy as np

# Sellmeier coefficients (wavelength in micrometres)
SELLMEIER = {
    "BK7": ((1.03961212, 0.231792344, 1.01046945), (0.00600069867, 0.0200179144, 103.560653)),
    "SF11": ((1.73759695, 0.313747346, 1.89878101), (0.013188707, 0.0623068142, 155.23629)),
}


def ior(material: str, wavelength_nm: float) -> float:
    (b1, b2, b3), (c1, c2, c3) = SELLMEIER[material]
    l2 = (wavelength_nm / 1000.0) ** 2
    return math.sqrt(1 + b1 * l2 / (l2 - c1) + b2 * l2 / (l2 - c2) + b3 * l2 / (l2 - c3))


def prism_deviation_deg(apex_deg: float, incidence_deg: float, n: float) -> float:
    """Total deviation through a prism of apex angle A for incidence angle i (exact Snell)."""
    A, i = math.radians(apex_deg), math.radians(incidence_deg)
    r1 = math.asin(math.sin(i) / n)
    r2 = A - r1
    s = n * math.sin(r2)
    if abs(s) > 1:
        return float("nan")  # total internal reflection
    return math.degrees(i + math.asin(s) - A)


def dispersion_spread_deg(material="SF11", apex=60.0, incidence=65.0,
                          lo_nm=450.0, hi_nm=650.0) -> float:
    return abs(prism_deviation_deg(apex, incidence, ior(material, lo_nm))
               - prism_deviation_deg(apex, incidence, ior(material, hi_nm)))


def fresnel_unpolarized(cos_i: float, n1: float, n2: float) -> float:
    sin_t2 = (n1 / n2) ** 2 * (1 - cos_i**2)
    if sin_t2 >= 1:
        return 1.0
    cos_t = math.sqrt(1 - sin_t2)
    rs = ((n1 * cos_i - n2 * cos_t) / (n1 * cos_i + n2 * cos_t)) ** 2
    rp = ((n1 * cos_t - n2 * cos_i) / (n1 * cos_t + n2 * cos_i)) ** 2
    return (rs + rp) / 2


def furnace_error(mean_radiance: np.ndarray, expected: float = 1.0) -> float:
    """White-furnace test: energy-conserving, unit-albedo scene should return `expected` everywhere."""
    return float(np.max(np.abs(mean_radiance - expected)))


def grade_prism_render(spectrum_rows: np.ndarray, wavelengths_nm: np.ndarray,
                       exit_angles_deg: np.ndarray, material="SF11", apex=60.0,
                       incidence=65.0, tol_deg=0.15) -> dict:
    """Submission reports, per wavelength, the measured exit-ray deviation; compare to Sellmeier truth."""
    truth = np.array([prism_deviation_deg(apex, incidence, ior(material, w)) for w in wavelengths_nm])
    err = np.abs(exit_angles_deg - truth)
    monotone = bool(np.all(np.diff(exit_angles_deg) <= 0))  # shorter wavelength bends more
    return {"max_err_deg": float(err.max()), "monotonic": monotone,
            "score": float(monotone) * float(max(0.0, 1 - err.max() / (4 * tol_deg)))}
