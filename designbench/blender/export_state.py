"""Run inside Blender:  blender -b scene.blend --python export_state.py -- out.json [DoorName]

Dumps scene_state_v1 JSON for the graders. Untested outside Blender 4.x; keep it dependency-free.
"""
import json
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def world_bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def keyframes(o):
    out = {}
    ad = o.animation_data
    if ad and ad.action:
        for fc in ad.action.fcurves:
            if fc.data_path == "rotation_euler":
                out.setdefault("rotation_euler", {})[str(fc.array_index)] = [
                    [kp.co[0], kp.co[1]] for kp in fc.keyframe_points]
    return out


def constraints(o):
    res = []
    for c in o.constraints:
        d = {"type": c.type}
        if c.type == "LIMIT_ROTATION":
            for a in "xyz":
                d[f"use_limit_{a}"] = getattr(c, f"use_limit_{a}")
                d[f"min_{a}"] = getattr(c, f"min_{a}")
                d[f"max_{a}"] = getattr(c, f"max_{a}")
        res.append(d)
    return res


def intersections(scene, door, frames):
    others = [o for o in scene.objects if o.type == "MESH" and o is not door and o.parent is None]
    deps = bpy.context.evaluated_depsgraph_get()
    counts = []
    for f in frames:
        scene.frame_set(f)
        deps.update()
        dm = door.evaluated_get(deps)
        dt = BVHTree.FromObject(dm, deps)
        n = 0
        for o in others:
            ot = BVHTree.FromObject(o.evaluated_get(deps), deps)
            n += len(dt.overlap(ot))
        counts.append(n)
    return counts


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out, door_name = argv[0], (argv[1] if len(argv) > 1 else None)
    sc = bpy.context.scene
    state = {
        "schema": "scene_state_v1", "unit_scale": sc.unit_settings.scale_length,
        "fps": sc.render.fps, "frame_start": sc.frame_start, "frame_end": sc.frame_end,
        "view_transform": sc.view_settings.view_transform, "look": sc.view_settings.look,
        "exposure": sc.view_settings.exposure, "gamma": sc.view_settings.gamma,
        "lights": [{"name": o.name, "type": o.data.type, "energy": o.data.energy,
                    "color": list(o.data.color), "location": list(o.location),
                    "rotation": list(o.rotation_euler)} for o in sc.objects if o.type == "LIGHT"],
        "materials": {},
        "objects": [],
    }
    for m in bpy.data.materials:
        bsdf = m.node_tree.nodes.get("Principled BSDF") if m.use_nodes and m.node_tree else None
        if bsdf:
            state["materials"][m.name] = {"base_color": list(bsdf.inputs["Base Color"].default_value)}
    for o in sc.objects:
        if o.type == "LIGHT":
            continue
        lo, hi = world_bbox(o) if o.type == "MESH" else (list(o.location),) * 2
        state["objects"].append({
            "name": o.name, "type": o.type, "parent": o.parent.name if o.parent else None,
            "location": list(o.matrix_world.translation), "bbox_min": lo, "bbox_max": hi,
            "rotation_matrix": [list(r) for r in o.matrix_world.to_3x3().normalized()],
            "constraints": constraints(o), "animation": keyframes(o)})
    if door_name and door_name in sc.objects:
        door = sc.objects[door_name]
        state["intersections_by_frame"] = {door_name: intersections(
            sc, door, range(sc.frame_start, sc.frame_end + 1))}
    json.dump(state, open(out, "w"), indent=1)


main()
