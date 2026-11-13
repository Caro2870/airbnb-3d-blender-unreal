"""Which sun direction lands sun patches where the A/B camera sees them?  Rays from a grid on the visible room floor
and on the bed top toward each candidate sun; glass counts as open (the window glass passes shadow rays).

    blender -b apartaestudio.blend --python rayo_sol.py -- "x,y,z;x,y,z;..."   (directions toward the sun)
"""
import sys

import bpy
from mathutils import Vector

S = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()
fl = bpy.data.objects["Floor"]
zf = max((fl.matrix_world @ Vector(c)).z for c in fl.bound_box) + 0.005
SKIP = ("Aire_Interior", "Polvo")
# floor between sofa and bed and in front of the bed (seen by ab_cuarto), and the bed top
PTS = [Vector((x, y, zf)) for x in (1.45, 1.7, 1.95) for y in (4.2, 4.8, 5.4, 6.0, 6.5)] + \
      [Vector((x, y, zf)) for x in (2.2, 2.8, 3.4) for y in (3.6, 4.1)] + \
      [Vector((x, y, zf + 0.62)) for x in (2.3, 2.8, 3.3) for y in (4.9, 5.4)]


def open_(ob, idx):
    if ob.name.startswith(SKIP):
        return True
    if ob.type == 'MESH' and ob.material_slots and ob.data.polygons:
        m = ob.material_slots[ob.data.polygons[min(idx, len(ob.data.polygons) - 1)].material_index].material
        return bool(m) and "vidrio" in m.name.lower() or (m and "glass" in m.name.lower())
    return False


for txt in sys.argv[sys.argv.index("--") + 1].split(";"):
    d = Vector([float(t) for t in txt.split(",")]).normalized()
    lit, block = 0, {}
    for o in PTS:
        p = o.copy()
        for _ in range(30):
            ok, loc, nor, idx, ob, mat = S.ray_cast(dg, p, d)
            if not ok:
                lit += 1
                break
            if open_(ob, idx):
                p = loc + d * 0.002
                continue
            block[ob.name] = block.get(ob.name, 0) + 1
            break
    top = sorted(block.items(), key=lambda kv: -kv[1])[:4]
    print(f"[rayo] sol {txt}: {lit}/{len(PTS)} puntos al sol · tapan {top}")
