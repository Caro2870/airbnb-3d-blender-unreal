"""Open an exported GLB in an empty scene and render one interior view with plain lighting (export check).

    blender -b --factory-startup --python check_glb.py -- <in.glb> <out.png>
"""
import sys

import bpy
from mathutils import Vector

src, out = sys.argv[sys.argv.index("--") + 1:][:2]
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
bpy.ops.import_scene.gltf(filepath=src)
S = bpy.context.scene
S.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
S.render.resolution_x, S.render.resolution_y = 540, 960
w = bpy.data.worlds.new("w"); S.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN')); S.collection.objects.link(sun)
sun.data.energy = 3; sun.rotation_euler = (0.9, 0.2, 2.8)
pt = bpy.data.objects.new("pt", bpy.data.lights.new("pt", 'POINT')); S.collection.objects.link(pt)
pt.data.energy = 300; pt.location = (2.0, 4.6, 5.2)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); S.collection.objects.link(cam); S.camera = cam
cam.data.lens = 14
cam.location = Vector((3.4, 3.1, 4.75)); tgt = Vector((1.4, 6.8, 3.9))
cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
S.render.filepath = out
bpy.ops.render.render(write_still=True)
print("rendered", out)
