"""Reference (known-good) tracers used to validate the graders end to end. Not a ceiling for models."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from designbench.graders.optics import ior


def _refract(d, n, eta):
    """d unit incident, n unit normal facing the incident side, eta = n1/n2."""
    c = -np.dot(n, d)
    k = 1 - eta**2 * (1 - c**2)
    if k < 0:
        return None
    return eta * d + (eta * c - math.sqrt(k)) * n


def prism_deviation_by_tracing(wavelength_nm, material="SF11", apex=60.0, incidence=65.0) -> float:
    """2D vector ray trace through a prism (independent of the closed-form Snell expression)."""
    A = math.radians(apex)
    n1 = np.array([-math.cos(A / 2), math.sin(A / 2)])
    n2 = np.array([math.cos(A / 2), math.sin(A / 2)])
    th = math.atan2(-n1[1], -n1[0]) + math.radians(incidence)
    d0 = np.array([math.cos(th), math.sin(th)])
    n = ior(material, wavelength_nm)
    d1 = _refract(d0, n1, 1 / n)          # entering through face 1 (normal faces the incoming ray)
    d2 = _refract(d1, -n2, n)             # exiting through face 2 (flip normal to face the inside ray)
    if d2 is None:
        return float("nan")
    return math.degrees(math.acos(np.clip(np.dot(d0, d2), -1, 1)))


def render_prism(outdir):
    w = list(range(450, 651, 25))
    Path(outdir, "deviation.json").write_text(json.dumps({
        "wavelengths_nm": w, "exit_deviation_deg": [prism_deviation_by_tracing(x) for x in w]}))


def render_furnace(outdir, size=48, spp=16, max_bounces=64, seed=0):
    """Two near-touching unit-albedo diffuse spheres in a uniform unit environment."""
    rng = np.random.default_rng(seed)
    centers = np.array([[-1.1, 0, 3.0], [1.1, 0, 3.0]])
    f = math.tan(math.radians(20))
    u = (np.arange(size) + 0.5) / size * 2 - 1
    px, py = np.meshgrid(u * f, -u * f)
    d0 = np.stack([px, py, np.ones_like(px)], -1).reshape(-1, 3)
    d0 /= np.linalg.norm(d0, axis=1, keepdims=True)

    def hit(o, d):
        best_t = np.full(len(o), np.inf)
        best_n = np.zeros_like(o)
        for c in centers:
            oc = o - c
            b = np.sum(oc * d, 1)
            disc = b * b - (np.sum(oc * oc, 1) - 1)
            t = -b - np.sqrt(np.maximum(disc, 0))
            ok = (disc > 0) & (t > 1e-4) & (t < best_t)
            best_t[ok] = t[ok]
            p = o + d * t[:, None]
            best_n[ok] = (p - c)[ok]
        return np.isfinite(best_t), best_t, best_n

    h0, _, _ = hit(np.zeros_like(d0), d0)
    acc = np.zeros(len(d0))
    for _ in range(spp):
        o, d = np.zeros_like(d0), d0.copy()
        alive = np.ones(len(d0), bool)
        val = np.zeros(len(d0))
        for _b in range(max_bounces):
            if not alive.any():
                break
            idx = np.nonzero(alive)[0]
            hh, t, n = hit(o[idx], d[idx])
            miss = idx[~hh]
            val[miss] = 1.0                      # escaped to unit-radiance environment
            alive[miss] = False
            h = idx[hh]
            if len(h) == 0:
                break
            nn = n[hh] / np.linalg.norm(n[hh], axis=1, keepdims=True)
            o[h] = o[h] + d[h] * t[hh][:, None]
            # cosine-weighted hemisphere sample about nn
            r1, r2 = rng.random(len(h)), rng.random(len(h))
            phi, rr = 2 * math.pi * r1, np.sqrt(r2)
            a = np.where(np.abs(nn[:, :1]) > 0.9, np.array([[0, 1, 0]]), np.array([[1, 0, 0]]))
            tx = np.cross(a, nn)
            tx /= np.linalg.norm(tx, axis=1, keepdims=True)
            ty = np.cross(nn, tx)
            d[h] = (np.cos(phi)[:, None] * rr[:, None] * tx + np.sin(phi)[:, None] * rr[:, None] * ty
                    + np.sqrt(1 - r2)[:, None] * nn)
        acc += val
    img = (acc / spp).reshape(size, size)
    np.save(Path(outdir, "furnace.npy"), np.repeat(img[..., None], 3, -1))
    np.save(Path(outdir, "mask.npy"), h0.reshape(size, size))
