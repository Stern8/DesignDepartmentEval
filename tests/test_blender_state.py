import copy
import math

from designbench.graders import scene_state as g
from designbench.graders.color import linear_to_hex
from designbench.graders.scene_state import Artifacts
from designbench.run import grade
from designbench.scoring import load_tasks

LIGHTS = [{"name": "Key", "type": "AREA", "energy": 800, "color": [1, 1, 1],
           "location": [4, -4, 5], "rotation": [0, 0, 0]}]


def srgb_to_linear(h):
    v = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in v]


def task(i):
    return next(t for t in load_tasks() if t["id"] == i)


def test_linear_roundtrip_all_greys_and_target():
    assert linear_to_hex(srgb_to_linear("1F3A5C")) == "1F3A5C"
    assert all(linear_to_hex(srgb_to_linear(f"{v:02X}" * 3)) == f"{v:02X}" * 3 for v in range(256))


def cmf_state(hexv="1F3A5C", vt="Standard"):
    return {"materials": {"BodyPaint": {"base_color": srgb_to_linear(hexv) + [1]}},
            "view_transform": vt, "look": "None", "lights": copy.deepcopy(LIGHTS)}


def test_cmf_pass_and_traps():
    t = task("cmf-001-exact-hex")
    base = Artifacts(state=cmf_state(), baseline={"lights": LIGHTS})
    assert grade(t, base)["score"] == 1.0
    agx = Artifacts(state=cmf_state(vt="AgX"), baseline={"lights": LIGHTS})
    assert abs(grade(t, agx)["score"] - 0.8) < 1e-9
    off = Artifacts(state=cmf_state("1F3A5D"), baseline={"lights": LIGHTS})
    assert abs(grade(t, off)["score"] - (0.6 * 0.8 + 0.4)) < 1e-9
    moved = cmf_state()
    moved["lights"][0]["energy"] = 900
    assert abs(grade(t, Artifacts(state=moved, baseline={"lights": LIGHTS}))["score"] - 0.8) < 1e-9


def test_package_dims():
    pk = task("ad-001-brief-to-proportion")["inputs"]["package"]
    def wheel(n, y):
        return {"name": n, "location": [0.9, y, 0.5334], "bbox_min": [0.8, y - .5334, 0], "bbox_max": [1.0, y + .5334, 1.0668]}
    s = {"unit_scale": 1.0, "objects": [
        {"name": "Body", "location": [0, 0, 0], "bbox_min": [-1, -2.25, 0.19], "bbox_max": [1, 2.45, 1.62]},
        wheel("Wheel_FL", 1.425), wheel("Wheel_RL", -1.425)]}
    # length 4.70, height 1.62, wb 2.85, overhang 2450-1425=1025 -> violates <=900; wheel dia 1.0668m=42in -> violates
    r = g.package_dims(Artifacts(state=s), {"package": pk})
    assert 0 < r < 1
    s["objects"][0]["bbox_max"][1] = 2.325                       # overhang 900, length 4.575 (fails length)
    assert g.package_dims(Artifacts(state=s), {"package": pk}) > r - 1e-9


def door_state(max_deg=70, secs=2, lim=70, axis_rot=0.0):
    k = math.radians(max_deg)
    c, s_ = math.cos(axis_rot), math.sin(axis_rot)
    return {"fps": 24, "objects": [{"name": "Door_L", "location": [0.97, 0.85, 0.8],
            "rotation_matrix": [[c, -s_, 0], [s_, c, 0], [0, 0, 1]] if axis_rot == 0 else [[1, 0, 0], [0, c, -s_], [0, s_, c]],
            "constraints": [{"type": "LIMIT_ROTATION", "use_limit_z": True, "min_z": 0, "max_z": math.radians(lim)}],
            "animation": {"rotation_euler": {"2": [[1, 0.0], [1 + 24 * secs, k]]}}}],
            "intersections_by_frame": {"Door_L": [0] * 49}}


def test_rig_task():
    t = task("vis-002-rig-door-opening")
    assert grade(t, Artifacts(state=door_state()))["score"] == 1.0
    assert grade(t, Artifacts(state=door_state(secs=3)))["checks"]["duration_2s"] == 0.0
    assert grade(t, Artifacts(state=door_state(lim=90)))["checks"]["rotation_limits"] == 0.0
    assert grade(t, Artifacts(state=door_state(axis_rot=0.5)))["checks"]["hinge_axis_error_deg"] == 0.0
    hit = door_state()
    hit["intersections_by_frame"]["Door_L"][10:20] = [3] * 10
    assert abs(grade(t, Artifacts(state=hit))["checks"]["no_intersection_all_frames"] - 39 / 49) < 1e-9
    assert grade(t, Artifacts())["score"] == 0.0
