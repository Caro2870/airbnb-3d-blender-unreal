"""Bake every procedural / box-projected material of the saved apartaestudio scene to UV textures and export a GLB
that game engines and the web can read (Unreal Engine Interchange, three.js).

    blender -b apartaestudio.blend --python bake_export.py -- <out.glb> [texture size] [AUTO|JPEG] [site]

JPEG + a small size gives the light web copy; 'site' keeps only the block next to the unit (drops ground, street,
neighbours and sea, which the web viewer draws itself).

Per object that uses such a material: modifiers applied, Smart UV Project into a new 'bake' UV map, base colour /
roughness / normal baked with Cycles on the GPU, materials replaced by plain Principled + image textures.  Materials
that already sample images through UVs (Poly Haven props, photo-projected furniture) are exported unchanged.  Lights,
the haze volume and dust motes are left to the engine.
"""
import math
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]
SIZE = int(argv[1]) if len(argv) > 1 else 1024
FMT = argv[2] if len(argv) > 2 else 'AUTO'
LIGHT_SITE = len(argv) > 3 and argv[3] == 'site'
BIG = {"Walls", "Floor", "Ceiling", "Slabs", "Block", "Floor_Balcony", "Kitchen", "Bath_Tiles"}
DROP = {"Aire_Interior", "Polvo"}
PROC = {'TEX_BRICK', 'TEX_NOISE', 'TEX_VORONOI', 'TEX_WAVE', 'TEX_MAGIC', 'TEX_GRADIENT', 'TEX_CHECKER'}
TEXDIR = os.path.join(os.path.dirname(OUT), "baked")
os.makedirs(TEXDIR, exist_ok=True)

S = bpy.context.scene
S.render.engine = 'CYCLES'
S.cycles.device = 'GPU'
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'OPTIX'; prefs.refresh_devices()
for d in prefs.devices:
    d.use = d.type == 'OPTIX'
S.cycles.samples = 4
S.render.bake.margin = 8


def principled(m):
    return next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if m and m.use_nodes else None


def needs_bake(m):
    if not m or not m.use_nodes or principled(m) is None:
        return False
    for n in m.node_tree.nodes:
        if n.type in PROC or (n.type == 'TEX_IMAGE' and n.projection == 'BOX'):
            return True
        if n.type == 'TEX_COORD' and any(o.is_linked for o in (n.outputs['Object'], n.outputs['Generated'])):
            return True
    return False


def simple_glass(m):
    """Swap the shadow-transparent architectural glass for a plain transmissive Principled (glTF transmission)."""
    nt = m.node_tree
    p = principled(m)
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    nt.links.new(out.inputs['Surface'], p.outputs['BSDF'])


for ob in list(bpy.data.objects):
    far = LIGHT_SITE and ob.name.split(".")[0] in {"Ground", "Street", "Parking", "Neighbours", "Seafront", "Sea"}
    if ob.name in DROP or ob.type in ('LIGHT', 'CAMERA') or ob.name.startswith("Treeline") or far:
        bpy.data.objects.remove(ob)
for m in bpy.data.materials:
    if m.name.startswith("Vidrio_Ventana"):
        simple_glass(m)

# generated furniture (Hunyuan3D meshes) has no clean surface for Smart UV islands: baking leaves black seams, so
# its procedural slots become a flat colour sampled from the material instead
for ob in [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("Gen_")]:
    for s in ob.material_slots:
        if needs_bake(s.material):
            flat = bpy.data.materials.new(s.material.name + "_flat"); flat.use_nodes = True
            p = flat.node_tree.nodes["Principled BSDF"]
            p.inputs["Base Color"].default_value = (0.86, 0.86, 0.84, 1); p.inputs["Roughness"].default_value = 0.9
            s.material = flat

dg = bpy.context.evaluated_depsgraph_get()
targets = [o for o in bpy.data.objects if o.type == 'MESH' and any(needs_bake(s.material) for s in o.material_slots)]
print("objects to bake:", len(targets), flush=True)

for i, ob in enumerate(targets):
    # 1. apply modifiers, own copies of the materials
    if ob.modifiers:
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        ob.modifiers.clear(); ob.data = me
    ob.data = ob.data.copy()
    for s in ob.material_slots:
        if s.material:
            s.material = s.material.copy()
    # 2. UVs
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    uv = ob.data.uv_layers.new(name="bake"); ob.data.uv_layers.active = uv
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.01, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    size = SIZE * 2 if ob.name.split(".")[0] in BIG else SIZE
    imgs = {}
    for kind, cs in (("color", 'sRGB'), ("rough", 'Non-Color'), ("normal", 'Non-Color')):
        img = bpy.data.images.new(f"{ob.name}_{kind}", size, size, alpha=False, float_buffer=False)
        img.colorspace_settings.name = cs
        if kind == "normal":
            img.generated_color = (0.5, 0.5, 1.0, 1.0)
        imgs[kind] = img
    # 3. bake each pass into all slots
    for kind, btype in (("color", 'DIFFUSE'), ("rough", 'ROUGHNESS'), ("normal", 'NORMAL')):
        for s in ob.material_slots:
            nt = s.material.node_tree
            n = nt.nodes.get("_bake") or nt.nodes.new("ShaderNodeTexImage"); n.name = "_bake"
            n.image = imgs[kind]; nt.nodes.active = n
        kw = dict(type=btype, use_clear=True)
        if btype == 'DIFFUSE':
            kw["pass_filter"] = {'COLOR'}
        bpy.ops.object.bake(**kw)
        path = os.path.join(TEXDIR, f"{ob.name}_{kind}.png".replace(" ", "_"))
        imgs[kind].filepath_raw = path; imgs[kind].file_format = 'PNG'; imgs[kind].save()
    # 4. replace with plain PBR materials sharing the baked maps (keep metal / coat / emission of each slot)
    for s in ob.material_slots:
        old = s.material; po = principled(old)
        m = bpy.data.materials.new(old.name + "_baked"); m.use_nodes = True
        nt = m.node_tree; p = nt.nodes["Principled BSDF"]
        for k in ("Metallic", "Coat Weight", "Transmission Weight", "Emission Strength", "IOR"):
            if po.inputs.get(k) is not None and not po.inputs[k].is_linked:
                p.inputs[k].default_value = po.inputs[k].default_value
        if not po.inputs["Emission Color"].is_linked:
            p.inputs["Emission Color"].default_value = po.inputs["Emission Color"].default_value
        uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = "bake"
        for kind, sock in (("color", "Base Color"), ("rough", "Roughness")):
            t = nt.nodes.new("ShaderNodeTexImage"); t.image = imgs[kind]
            nt.links.new(t.inputs["Vector"], uvn.outputs["UV"]); nt.links.new(p.inputs[sock], t.outputs["Color"])
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = imgs["normal"]
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.uv_map = "bake"
        nt.links.new(t.inputs["Vector"], uvn.outputs["UV"]); nt.links.new(nm.inputs["Color"], t.outputs["Color"])
        nt.links.new(p.inputs["Normal"], nm.outputs["Normal"])
        s.material = m
    print(f"baked {i + 1}/{len(targets)} {ob.name} {size}px", flush=True)

# remaining modifiers and NaN scrub as in export_glb.py, then export
import bmesh
for ob in [o for o in bpy.data.objects if o.type == 'MESH' and o.modifiers]:
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    ob.modifiers.clear(); ob.data = me
if LIGHT_SITE:          # web copy: cap dense meshes (generated furniture, scanned plants) at ~15k faces
    for ob in [o for o in bpy.data.objects if o.type == 'MESH' and len(o.data.polygons) > 15000]:
        cap = 30000 if ob.name.startswith("Gen_cama") else 15000      # the bed is the hero object: keep its folds
        if len(ob.data.polygons) <= cap:
            continue
        dec = ob.modifiers.new("web", 'DECIMATE'); dec.ratio = cap / len(ob.data.polygons)
        dec.use_collapse_triangulate = True
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        ob.modifiers.clear(); ob.data = me
for me in bpy.data.meshes:
    if any(math.isnan(c) for v in me.vertices for c in v.co):
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if any(math.isnan(c) for c in v.co)], context='VERTS')
        bm.to_mesh(me); bm.free()
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLTF_SEPARATE' if OUT.endswith(".gltf") else 'GLB',
                          export_apply=True, export_yup=True,
                          export_lights=False, export_cameras=False, export_image_format=FMT,
                          export_jpeg_quality=80)
print("GLB written", OUT, flush=True)
