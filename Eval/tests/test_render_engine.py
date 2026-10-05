import json

import numpy as np
from PIL import Image

from designbench.graders import render_engine as g
from designbench.graders.scene_state import Artifacts
from designbench.render_engine import harness, reference

REF = "examples/reference_submission"


def test_reference_prism_matches_closed_form_independently():
    from designbench.graders.optics import ior, prism_deviation_deg
    for w in (450, 550, 650):
        assert abs(reference.prism_deviation_by_tracing(w) - prism_deviation_deg(60, 65, ior("SF11", w))) < 1e-9


def test_reference_through_harness(tmp_path):
    for task, fn in (("prism", g.prism_deviation), ("furnace", g.furnace_error)):
        d = tmp_path / task
        harness.run_submission(REF, task, str(d))
        a = Artifacts(outdir=str(d))
        assert abs(fn(a, {}) - 1.0) < 1e-9 and g.sandbox(a, {}) == 1.0


def test_harness_timeout_and_crash(tmp_path):
    sub = tmp_path / "s"
    sub.mkdir()
    (sub / "main.py").write_text("import time; time.sleep(5)")
    m = harness.run_submission(str(sub), "prism", str(tmp_path / "o"), timeout=1)
    assert m["timed_out"] and g.sandbox(Artifacts(outdir=str(tmp_path / "o")), {}) == 0.0
    (sub / "main.py").write_text("raise SystemExit(3)")
    harness.run_submission(str(sub), "prism", str(tmp_path / "o2"))
    assert g.sandbox(Artifacts(outdir=str(tmp_path / "o2")), {}) == 0.0


def test_furnace_rejects_energy_loss_and_gaming(tmp_path):
    d = tmp_path
    mask = np.zeros((48, 48), bool); mask[10:30, 10:30] = True
    for val, expect in ((1.0, 1.0), (0.9, 0.0), (1.1, 0.0)):
        np.save(d / "furnace.npy", np.full((48, 48, 3), val)); np.save(d / "mask.npy", mask)
        assert g.furnace_error(Artifacts(outdir=str(d)), {}) == expect
    np.save(d / "mask.npy", np.zeros((48, 48), bool))          # empty mask cannot game it
    assert g.furnace_error(Artifacts(outdir=str(d)), {}) == 0.0


def test_prism_rejects_wrong_grid_and_nan(tmp_path):
    good = {"wavelengths_nm": list(range(450, 651, 25)),
            "exit_deviation_deg": [reference.prism_deviation_by_tracing(w) for w in range(450, 651, 25)]}
    for mut in (lambda d: d.update(wavelengths_nm=[500]), lambda d: d["exit_deviation_deg"].__setitem__(0, float("nan")),
                lambda d: d.update(exit_deviation_deg=[40.0] * 9)):
        bad = json.loads(json.dumps(good)); mut(bad)
        (tmp_path / "deviation.json").write_text(json.dumps(bad))
        assert g.prism_deviation(Artifacts(outdir=str(tmp_path)), {}) == 0.0


def synth_caustic(peak=True, offset=0.0, size=200):
    xs = (np.arange(size) + .5) / size * 8 - 4
    X, Z = np.meshgrid(xs, xs)
    R = np.hypot(X, Z)
    img = np.full((size, size), 0.2)
    img[(R > 1) & (R < 1.6)] = 0.05                       # shadow ring
    if peak:
        img[np.hypot(X - offset, Z) < 0.2] = 1.0           # focused caustic
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).convert("RGB")


def test_caustic_grader(tmp_path):
    a = Artifacts(outdir=str(tmp_path))
    synth_caustic().save(tmp_path / "render.png")
    assert g.caustic(a, {}) == 1.0
    synth_caustic(peak=False).save(tmp_path / "render.png")
    assert g.caustic(a, {}) < 0.4
    synth_caustic(offset=1.5).save(tmp_path / "render.png")
    assert g.caustic(a, {}) < 1.0
