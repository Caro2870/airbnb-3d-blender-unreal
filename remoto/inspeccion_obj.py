"""Print an object's materials with face count and area, and its bounding box.  blender -b x.blend --python ... -- Nombre"""
import sys

import bpy
from mathutils import Vector

for name in sys.argv[sys.argv.index("--") + 1].split(","):
    ob = bpy.data.objects.get(name)
    if ob is None:
        print("[obj] no existe", name); continue
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    lo = [round(min(p[i] for p in pts), 3) for i in range(3)]; hi = [round(max(p[i] for p in pts), 3) for i in range(3)]
    print(f"[obj] {name}: caja {lo} -> {hi}, oculto render {ob.hide_render}")
    acc = {}
    for p in ob.data.polygons:
        m = ob.material_slots[p.material_index].material if ob.material_slots else None
        k = m.name if m else "?"
        n, a = acc.get(k, (0, 0.0)); acc[k] = (n + 1, a + p.area)
    for k, (n, a) in acc.items():
        print(f"[obj]   {k}: {n} caras, {a:.2f} m2")
