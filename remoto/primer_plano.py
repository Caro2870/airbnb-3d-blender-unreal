"""blender -b apartaestudio.blend --python primer_plano.py -- out.png x y z tx ty tz [lens]: quick Cycles close-up
from a temporary camera (debugging helper)."""
import sys

import bpy
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
out = a[0]
pos, tgt = Vector(map(float, a[1:4])), Vector(map(float, a[4:7]))
lens = float(a[7]) if len(a) > 7 else 35.0
S = bpy.context.scene
cam = bpy.data.objects.new("_cerca", bpy.data.cameras.new("_cerca"))
S.collection.objects.link(cam)
cam.location = pos
cam.rotation_euler = (tgt - pos).to_track_quat('-Z', 'Y').to_euler()
cam.data.lens = lens
S.camera = cam
S.render.engine = 'CYCLES'
S.cycles.device = 'GPU'
S.cycles.samples = 32
S.render.resolution_x = S.render.resolution_y = 600
S.render.resolution_percentage = 100
S.render.filepath = out
bpy.ops.render.render(write_still=True)
print("WROTE", out)
