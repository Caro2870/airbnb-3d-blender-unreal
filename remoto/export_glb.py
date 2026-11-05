"""Export the saved apartaestudio scene to GLB for the web viewer.

    blender -b apartaestudio.blend --python export_glb.py -- out.glb

glTF only carries plain PBR values, so every procedural Base Color is flattened to a representative colour first
(the .blend is not saved afterwards).  Exterior context far from the unit is dropped to keep the file small.
"""
import sys
import bpy

out = sys.argv[sys.argv.index("--") + 1]
KEEP_SITE = {"Block", "Block_Balconies", "Block_Rails", "Ground", "Street", "Parking", "Neighbours", "Seafront"}


def upstream_color(sock, depth=0):
    """First plausible constant colour feeding a socket (brick Color1, ramp stop, RGB node, mix inputs)."""
    if depth > 8 or not sock.is_linked:
        v = getattr(sock, "default_value", None)
        return tuple(v)[:4] if v is not None and hasattr(v, "__len__") and len(v) >= 3 else None
    node = sock.links[0].from_node
    if node.type == 'TEX_BRICK':
        return tuple(node.inputs["Color1"].default_value)
    if node.type == 'VALTORGB':
        els = node.color_ramp.elements
        c = [sum(e.color[i] for e in els) / len(els) for i in range(4)]
        return tuple(c)
    if node.type == 'RGB':
        return tuple(node.outputs[0].default_value)
    for name in ("Color1", "A", "Color", "Base Color", "Color2", "B"):
        s = node.inputs.get(name)
        if s is not None and s.type == 'RGBA':
            c = upstream_color(s, depth + 1)
            if c:
                return c
    return None


for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    for n in m.node_tree.nodes:
        if n.type != 'BSDF_PRINCIPLED':
            continue
        bc = n.inputs["Base Color"]
        if bc.is_linked:
            c = upstream_color(bc) or (0.8, 0.8, 0.8, 1.0)
            for l in list(bc.links):
                m.node_tree.links.remove(l)
            bc.default_value = (c[0], c[1], c[2], 1.0)
        for name in ("Roughness", "Metallic", "Normal"):
            s = n.inputs.get(name)
            if s is not None and s.is_linked:
                for l in list(s.links):
                    m.node_tree.links.remove(l)

for ob in list(bpy.data.objects):
    if ob.type == 'MESH' and any(c.name == 'Site' for c in ob.users_collection) and ob.name not in KEEP_SITE:
        bpy.data.objects.remove(ob)
    elif ob.type in ('LIGHT', 'CAMERA'):
        bpy.data.objects.remove(ob)
# hair/particle systems do not export; drop them
for ob in bpy.data.objects:
    for mod in list(ob.modifiers):
        if mod.type == 'PARTICLE_SYSTEM':
            ob.modifiers.remove(mod)

# bake modifiers (bevel / subsurf) into the meshes, then scrub NaN vertices: a few degenerate lathes and bevels
# produce them, and glTF cannot encode them
import math
dg = bpy.context.evaluated_depsgraph_get()
for ob in [o for o in bpy.data.objects if o.type == 'MESH' and o.modifiers]:
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    ob.modifiers.clear()
    ob.data = me
for me in bpy.data.meshes:
    if not any(math.isnan(c) for v in me.vertices for c in v.co):
        continue
    import bmesh
    bm = bmesh.new(); bm.from_mesh(me)
    bad = [v for v in bm.verts if any(math.isnan(c) for c in v.co)]
    bmesh.ops.delete(bm, geom=bad, context='VERTS')
    bm.to_mesh(me); bm.free()
    print("dropped NaN verts", me.name, len(bad))
    me.validate()

bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_apply=True, export_yup=True,
                          export_lights=False, export_cameras=False)
print("GLB written", out)
