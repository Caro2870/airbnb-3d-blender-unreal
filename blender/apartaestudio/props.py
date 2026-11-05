"""Scanned CC0 props from Poly Haven (assets/models, fetched by polyhaven.py), appended from their .blend files and
placed in plan coordinates.  Real-world scale unless `h` (target height, m) is given.  Staging, not evidence."""
import math
import os

import bpy

from .plan import *
from .house import ASSETS

# model id, (x, y, z), rotation about Z (deg), target height or None
PLACE = [
    ("pachira_aquatica_01",        (0.40, 2.85, Z0),        0,   1.25),   # floor plant where the kitchen run ends
    ("potted_plant_04",            (3.78, 3.10, Z0),        30,  0.9),    # alcoba corner beside the bath door
    ("potted_plant_02",            (0.30, 1.45, Z0 + 0.9),  0,   0.28),   # kitchen counter
    ("potted_plant_01",            (3.62, Y_WIN - 0.25, Z0 + 0.75), 0, 0.3),   # desk
    ("desk_lamp_arm_01",           (3.62, Y_WIN - 0.85, Z0 + 0.75), 200, 0.45),
    ("throw_pillows_01",           (0.55, 5.72, Z0 + 0.46), 90,  None),   # sofa bed
    ("ceramic_vase_01",            (0.25, 1.0, Z0 + 1.53),  0,   0.22),   # open shelf
]
REPLACES = {}
KEEP = {"pachira_aquatica_01": "_a"}        # files that ship several variants side by side: keep one (name suffix)


def _append(mid):
    path = os.path.join(ASSETS, "models", mid, f"{mid}_1k.blend")
    before = set(bpy.data.images)
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = [n for n in src.objects]
    for img in set(bpy.data.images) - before:        # texture paths are relative to the source .blend
        if img.filepath.startswith("//"):
            img.filepath = os.path.join(os.path.dirname(path), img.filepath[2:])
            img.reload()
    return [o for o in dst.objects if o is not None]


def _bounds(obs):
    pts = [o.matrix_world @ v.co for o in obs if o.type == 'MESH' for v in o.data.vertices]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    return lo, hi


def build(M):
    coll = bpy.data.collections.get("Props") or bpy.data.collections.new("Props")
    if coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)
    for mid, (x, y, z), rot, h in PLACE:
        if not os.path.isfile(os.path.join(ASSETS, "models", mid, f"{mid}_1k.blend")):
            continue
        obs = _append(mid)
        if mid in KEEP:
            drop = [o for o in obs if o.type == 'MESH' and not o.name.endswith(KEEP[mid])]
            obs = [o for o in obs if o not in drop]
            for o in drop:
                bpy.data.objects.remove(o)
        for o in obs:
            coll.objects.link(o)
        bpy.context.view_layer.update()
        lo, hi = _bounds(obs)
        k = h / (hi[2] - lo[2]) if h else 1.0
        root = bpy.data.objects.new(f"Prop_{mid}", None)
        coll.objects.link(root)
        # pivot: centre of the footprint, on the floor of the model
        root.location = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2])
        bpy.context.view_layer.update()
        for o in obs:
            if o.parent is None:
                mw = o.matrix_world.copy()
                o.parent = root
                o.matrix_world = mw
        root.location = (x, y, z)
        root.rotation_euler = (0, 0, math.radians(rot))
        root.scale = (k, k, k)
        old = bpy.data.objects.get(REPLACES.get(mid, ""))
        if old is not None:
            bpy.data.objects.remove(old)
