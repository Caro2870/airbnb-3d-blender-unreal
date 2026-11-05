"""Workbench 3/4 preview of every GLB in a folder (diagnostic).

    blender -b --factory-startup --python preview_glb.py -- <dir>
"""
import math
import pathlib
import sys

import bpy
from mathutils import Vector

d = pathlib.Path(sys.argv[sys.argv.index("--") + 1])
S = bpy.context.scene
S.render.engine = 'BLENDER_WORKBENCH'
S.display.shading.light = 'STUDIO'; S.display.shading.show_cavity = True
S.render.resolution_x = S.render.resolution_y = 512
for glb in sorted(d.glob("*.glb")):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    obs = [o for o in bpy.data.objects if o.type == 'MESH']
    pts = [o.matrix_world @ Vector(c) for o in obs for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    c = (lo + hi) / 2; r = (hi - lo).length
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); S.collection.objects.link(cam); S.camera = cam
    cam.location = c + Vector((math.cos(-0.9), math.sin(-0.9), 0.55)) * r * 1.4
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    S.render.filepath = str(d / f"{glb.stem}_preview.png")
    bpy.ops.render.render(write_still=True)
    print(glb.stem, "size", [round(v, 2) for v in (hi - lo)])
