"""Furniture generated from the listing photos with Hunyuan3D-2.1 (shape only, assets/gen/*.glb), coloured by projecting
the photo cut-out back onto the mesh from the photo's viewing direction.  Replaces the box-built bed, balcony set and
office chair.  Generated geometry is an approximation of the photographed object, not a measured model."""
import math
import os

import bpy

from .plan import *
from .house import ASSETS
from archviz.mesh import MB

GEN = os.path.join(ASSETS, "gen")
# name, (x, y, z of the footprint centre / bottom), rotation (deg), size: ('xy', w, l) or ('h', height),
# camera elevation of the source photo (deg), objects it replaces
ITEMS = [   # elevation None -> plain library material (key in the last field) instead of the photo projection
    ("cama",          (W - 0.1 - 1.02, BED_Y, Z0 + 0.29), -90, ('xy', 1.45, 2.0), None, ["Bed", "Cushions_Blue"], 'linen_white'),
    ("silla_balcon",  (1.35, (Y_WIN + WT + Y_BAL) / 2, Z0), -90, ('h', 0.88),      40,   ["Balcony_Set"], None),
    ("silla_oficina", (W - 0.85, Y_WIN - 0.6, Z0 + 0.45), 90, ('h', 0.66),       15,   ["Office_Chair"], None),
]
HEAD_UP = {}           # auto-orientation by highest part misread the folded towels as the head; see HEAD_TURN
HEAD_TURN = {"cama": -90}  # the generated bed comes with its pillows on local -X; this brings them to +Y (checked in renders)


def _head_to_plus_y(me):
    zs = [v.co.z for v in me.vertices]
    top = max(zs) - 0.2 * (max(zs) - min(zs))
    hi = [v.co for v in me.vertices if v.co.z > top]
    cx = sum(v.co.x for v in me.vertices) / len(me.vertices)
    cy = sum(v.co.y for v in me.vertices) / len(me.vertices)
    hx = sum(c.x for c in hi) / len(hi) - cx; hy = sum(c.y for c in hi) / len(hi) - cy
    a = math.pi / 2 - math.atan2(hy, hx)
    a = round(a / (math.pi / 2)) * (math.pi / 2)          # snap to quarter turns: beds are axis-aligned
    from mathutils import Matrix
    me.transform(Matrix.Rotation(a, 4, 'Z'))


def _photo_material(name, img_path):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = bpy.data.images.load(img_path, check_existing=True)
    tx.extension = 'EXTEND'
    nt.links.new(b.inputs["Base Color"], tx.outputs["Color"])
    b.inputs["Roughness"].default_value = 0.85
    return m


def _project_uv(me, elev):
    """UV = position on the image plane of a camera in front (-Y) of the object looking down by `elev` degrees."""
    e = math.radians(elev)
    up = (0.0, math.sin(e), math.cos(e))
    us = [v.co.x for v in me.vertices]
    vs = [v.co.y * up[1] + v.co.z * up[2] for v in me.vertices]
    u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
    uv = me.uv_layers.new(name="photo")
    for loop in me.loops:
        i = loop.vertex_index
        uv.data[loop.index].uv = ((us[i] - u0) / (u1 - u0), (vs[i] - v0) / (v1 - v0))


def _import(name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(GEN, f"{name}.glb"))
    obs = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    for o in [o for o in bpy.data.objects if o not in before and o.type != 'MESH']:
        bpy.data.objects.remove(o)
    ob = obs[0]
    if len(obs) > 1:
        with bpy.context.temp_override(active_object=ob, selected_editable_objects=obs):
            bpy.ops.object.join()
    ob.parent = None
    ob.data.transform(ob.matrix_world); ob.matrix_world.identity()
    return ob


def build(M):
    for name, (x, y, z), rot, size, elev, replaces, mat in ITEMS:
        if not os.path.isfile(os.path.join(GEN, f"{name}.glb")):
            continue
        for r in replaces:
            old = bpy.data.objects.get(r)
            if old is not None:
                bpy.data.objects.remove(old)
        ob = _import(name)
        ob.name = f"Gen_{name}"
        me = ob.data
        me.materials.clear()
        if elev is not None:
            _project_uv(me, elev)
            me.materials.append(_photo_material(f"Foto_{name}", os.path.join(GEN, f"{name}_tex.png")))
        else:
            me.materials.append(M[mat])
        if name in HEAD_UP:
            _head_to_plus_y(me)
        if name in HEAD_TURN:
            from mathutils import Matrix
            me.transform(Matrix.Rotation(math.radians(HEAD_TURN[name]), 4, 'Z'))
        for p in me.polygons:
            p.use_smooth = True
        xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
        cx, cy, z0 = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)
        if size[0] == 'xy':
            sx, sy = size[1] / (max(xs) - min(xs)), size[2] / (max(ys) - min(ys))
            k = (sx, sy, (sx + sy) / 2)
        else:
            s = size[1] / (max(zs) - z0); k = (s, s, s)
        for v in me.vertices:
            v.co = ((v.co.x - cx) * k[0], (v.co.y - cy) * k[1], (v.co.z - z0) * k[2])
        ob.location = (x, y, z); ob.rotation_euler = (0, 0, math.radians(rot))

    # oak bed frame on legs + linen headboard, as photographed (the generated bed is only mattress and bedding)
    fx0, fx1, fy0, fy1 = W - 0.1 - 1.82, W - 0.1, BED_Y - 0.68, BED_Y + 0.68   # tucked under the mattress
    f = MB()
    f.box(fx0, fx1, fy0, fy1, Z0 + 0.14, Z0 + 0.3, 0)
    for lx in (fx0 + 0.06, fx1 - 0.06):
        for ly in (fy0 + 0.06, fy1 - 0.06):
            f.cylinder(lx, ly, Z0, Z0 + 0.14, 0.03, seg=12, mi=0)
    f.build("Bed_Frame", [M['oak']], bevel=0.008)
    hb = MB(); hb.rbox(W - 0.1, W - 0.02, fy0 - 0.02, fy1 + 0.02, Z0 + 0.3, Z0 + 1.12, r=0.02, mi=0)
    hb.build("Headboard", [M['cabecero']])
    # office chair gas lift + five-star base (the photo shows only the seat and back)
    ch = MB(); cx, cy = W - 0.85, Y_WIN - 0.6
    ch.cylinder(cx, cy, Z0 + 0.08, Z0 + 0.47, 0.025, seg=12, mi=0)
    for i in range(5):
        a = 2 * math.pi * i / 5
        ch.tube((cx, cy, Z0 + 0.09), (cx + 0.3 * math.cos(a), cy + 0.3 * math.sin(a), Z0 + 0.06), 0.018, 0.014, mi=0)
        ch.sphere((cx + 0.3 * math.cos(a), cy + 0.3 * math.sin(a), Z0 + 0.03), 0.03, seg=8, rings=5, mi=0)
    ch.build("Office_Chair_Base", [M['black_metal']])
