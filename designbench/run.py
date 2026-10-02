"""Grade one task:  python -m designbench.run <task_id> [--state state.json] [--baseline b.json] [--outdir dir]
Checks whose grader isn't implemented (vlm_rubric, per-tool adapters) score 0 and are reported as such."""
from __future__ import annotations

import argparse
import json

from .graders import render_engine, scene_state
from .graders.scene_state import Artifacts
from .scoring import aggregate, load_tasks

REGISTRY = {f"scene_state.{n}": getattr(scene_state, n) for n in
            ("hex_exact", "view_transform_standard", "lights_untouched", "package_dims", "rotation_limits",
             "hinge_axis_error", "duration", "no_intersection_all_frames")}
REGISTRY.update({f"render_engine.{n}": getattr(render_engine, n) for n in
                 ("sandbox", "furnace_error", "prism_deviation", "caustic")})


def grade(task: dict, art: Artifacts) -> dict:
    scores, unimplemented = {}, []
    for c in task["checks"]:
        fn = REGISTRY.get(c["grader"])
        if fn is None:
            unimplemented.append(c["name"])
            continue
        scores[c["name"]] = float(fn(art, c.get("params", {})))
    return {"task": task["id"], "score": round(aggregate(task, scores), 4), "checks": scores,
            "unimplemented": unimplemented}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task_id")
    ap.add_argument("--state"), ap.add_argument("--baseline"), ap.add_argument("--outdir", default=".")
    a = ap.parse_args()
    task = next(t for t in load_tasks() if t["id"] == a.task_id)
    art = Artifacts(state=json.load(open(a.state)) if a.state else {},
                    baseline=json.load(open(a.baseline)) if a.baseline else {}, outdir=a.outdir)
    print(json.dumps(grade(task, art), indent=1))


if __name__ == "__main__":
    main()
