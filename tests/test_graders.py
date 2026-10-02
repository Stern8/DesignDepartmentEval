import numpy as np
from PIL import Image

from designbench.graders import color, continuity, optics, render
from designbench.scoring import aggregate, load_tasks


def test_hex_exact_and_near():
    assert color.score_hex("1F3A5C", "#1f3a5c")["score"] == 1.0
    near = color.score_hex("1F3A5C", "203A5C")
    assert 0 < near["delta_e"] < 1 and near["score"] == 0.8
    assert color.score_hex("1F3A5C", "C03A1C")["score"] == 0.0


def test_delta_e2000_reference_pair():
    # Sharma et al. test data, pair 1
    de = color.delta_e2000((50.0, 2.6772, -79.7751), (50.0, 0.0, -82.7485))
    assert abs(de - 2.0425) < 1e-3


def test_region_median():
    img = Image.new("RGB", (10, 10), (31, 58, 92))
    assert color.region_median_hex(img, (0, 0, 10, 10)) == "1F3A5C"


def test_continuity_levels():
    t = np.linspace(0, 1, 50)
    a = np.stack([t, t**2, 0 * t], 1)
    tan = np.stack([np.ones_like(t), 2 * t, 0 * t], 1)
    curv = np.full(50, 2.0)
    assert continuity.grade_join(a, a, tan, tan, curv, curv, "G2")["score"] == 1.0
    r = continuity.grade_join(a, a, tan, tan, curv, curv * 2, "G2")
    assert r["achieved"] == "G1" and abs(r["score"] - 2 / 3) < 1e-9
    r = continuity.grade_join(a, a + 1, tan, tan, curv, curv, "G1")
    assert r["achieved"] == "none" and r["score"] == 0


def test_circle_curvature():
    th = np.linspace(0, np.pi, 400)
    p = np.stack([5 * np.cos(th), 5 * np.sin(th)], 1)
    k = continuity.curvature_of_polyline(p)[5:-5]
    assert np.allclose(np.abs(k), 0.2, atol=1e-3)


def test_dispersion_physics():
    assert abs(optics.ior("BK7", 589.3) - 1.5168) < 1e-3
    assert optics.dispersion_spread_deg() > 1.0
    assert optics.ior("SF11", 450) > optics.ior("SF11", 650)
    assert abs(optics.fresnel_unpolarized(1.0, 1.0, 1.5) - 0.04) < 1e-3


def test_prism_grader():
    w = np.arange(450, 651, 25.0)
    truth = np.array([optics.prism_deviation_deg(60, 65, optics.ior("SF11", x)) for x in w])
    assert optics.grade_prism_render(None, w, truth)["score"] == 1.0
    assert optics.grade_prism_render(None, w, truth[::-1])["score"] == 0.0


def test_render_light_direction():
    a = np.tile(np.linspace(20, 240, 100, dtype=np.uint8), (50, 1))
    right_lit = Image.fromarray(np.stack([a] * 3, -1))
    assert render.key_light_direction(right_lit) > 0.3
    assert render.key_light_direction(right_lit.transpose(Image.FLIP_LEFT_RIGHT)) < -0.3


def test_tasks_load_and_aggregate():
    tasks = load_tasks()
    assert len(tasks) >= 10 and len({t["id"] for t in tasks}) == len(tasks)
    t = tasks[0]
    assert aggregate(t, {}) == 0.0
    assert abs(aggregate(t, {c["name"]: 1.0 for c in t["checks"]}) - 1.0) < 1e-9
