"""Run inside Blender to generate task start files procedurally (no binary assets in git):
    blender -b --python make_assets.py -- assets/
"""
import sys

import bpy


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def cmf_start(path):
    reset()
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1)
    body = bpy.context.object
    body.name = "BodyPanel"
    mat = bpy.data.materials.new("BodyPaint")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1)
    body.data.materials.append(mat)
    for name, loc, e in (("Key", (4, -4, 5), 800), ("Fill", (-4, -3, 2), 200)):
        bpy.ops.object.light_add(type="AREA", location=loc)
        bpy.context.object.name, bpy.context.object.data.energy = name, e
    bpy.context.scene.view_settings.view_transform = "AgX"  # trap: task needs Standard
    bpy.ops.wm.save_as_mainfile(filepath=path)


def car_unrigged(path):
    reset()
    bpy.context.scene.unit_settings.scale_length = 1.0
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.75))
    body = bpy.context.object
    body.name, body.dimensions = "Body", (1.9, 4.6, 1.0)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.97, 0.3, 0.8))
    door = bpy.context.object
    door.name, door.dimensions = "Door_L", (0.05, 1.1, 0.8)
    bpy.ops.wm.save_as_mainfile(filepath=path)


if __name__ == "__main__":
    out = sys.argv[sys.argv.index("--") + 1]
    cmf_start(out.rstrip("/") + "/cmf_start.blend")
    car_unrigged(out.rstrip("/") + "/car_unrigged.blend")
