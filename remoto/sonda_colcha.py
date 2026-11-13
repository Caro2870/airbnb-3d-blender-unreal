"""Mide la caída de la colcha de la biblioteca (Plane.015/016) respecto al colchón y la base de la cama.
    blender -b apartaestudio.blend --python sonda_colcha.py"""
import bpy
import numpy as np

dg = bpy.context.evaluated_depsgraph_get()
for n in ("Plane.015", "Plane.016", "Plane.017", "Plane.018", "Cube.009", "Cama_Base", "Camino",
          "Blue velvet button cushion B"):
    o = bpy.data.objects.get(n)
    if o is None:
        print(f"[colcha] {n}: no está"); continue
    ev = o.evaluated_get(dg); me = ev.to_mesh()
    v = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", v); v = v.reshape(-1, 3)
    mw = np.array(ev.matrix_world); v = v @ mw[:3, :3].T + mw[:3, 3]
    ev.to_mesh_clear()
    lo, hi = v.min(0), v.max(0)
    print(f"[colcha] {n:30s} verts {len(v):6d} min {np.round(lo, 3)} max {np.round(hi, 3)} oculto {o.hide_render}")
    if n in ("Plane.015", "Plane.016"):
        for zc in np.arange(hi[2], lo[2] - 0.05, -0.05):
            s = v[(v[:, 2] <= zc) & (v[:, 2] > zc - 0.05)]
            if len(s):
                print(f"[colcha]    z {zc - 0.05:.2f}-{zc:.2f}: x {s[:, 0].min():.3f}..{s[:, 0].max():.3f}  "
                      f"y {s[:, 1].min():.3f}..{s[:, 1].max():.3f}  n {len(s)}")

# borde lateral del lado del cuarto (y mínima): z más baja por tramo de x, y qué hay debajo
o = bpy.data.objects.get("Plane.016")
if o:
    ev = o.evaluated_get(dg); me = ev.to_mesh()
    v = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", v); v = v.reshape(-1, 3)
    mw = np.array(ev.matrix_world); v = v @ mw[:3, :3].T + mw[:3, 3]; ev.to_mesh_clear()
    lado = v[v[:, 1] < 4.66]
    for x0 in np.arange(1.9, 3.9, 0.2):
        s = lado[(lado[:, 0] >= x0) & (lado[:, 0] < x0 + 0.2)]
        if len(s):
            print(f"[colcha] lado x {x0:.1f}: z min {s[:, 2].min():.3f}  y min {s[:, 1].min():.3f}")
for o in bpy.data.objects:
    if o.type == 'MESH' and not o.hide_render and o.name.startswith(("Cama", "Cube.0", "Bed")):
        p = [o.matrix_world @ __import__('mathutils').Vector(c) for c in o.bound_box]
        print(f"[colcha] {o.name:24s} z {min(q.z for q in p):.3f}..{max(q.z for q in p):.3f} "
              f"y {min(q.y for q in p):.3f}..{max(q.y for q in p):.3f} mats {[m.name for m in o.data.materials][:3]}")
for n in ("Almohada_Frente_0", "Almohada_Frente_1", "Cushions_Blue_0", "Cushions_Blue_1", "Cama_Toalla"):
    o = bpy.data.objects.get(n)
    if o:
        p = [o.matrix_world @ __import__('mathutils').Vector(c) for c in o.bound_box]
        print(f"[colcha] {n:24s} x {min(q.x for q in p):.3f}..{max(q.x for q in p):.3f} "
              f"y {min(q.y for q in p):.3f}..{max(q.y for q in p):.3f} z {min(q.z for q in p):.3f}..{max(q.z for q in p):.3f}")
    else:
        print(f"[colcha] {n}: no está")

# cobertura de la colcha arriba: z máx por banda de y (lado de la mesa = y bajo) en el centro de la cama
o = bpy.data.objects.get("Plane.016")
if o:
    ev = o.evaluated_get(dg); me = ev.to_mesh()
    v = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", v); v = v.reshape(-1, 3)
    mw = np.array(ev.matrix_world); v = v @ mw[:3, :3].T + mw[:3, 3]; ev.to_mesh_clear()
    print(f"[colcha] Plane.016 verts {len(v)} mods {[m.type for m in o.modifiers]}")
    for xc in (2.2, 2.8, 3.3):
        s = v[np.abs(v[:, 0] - xc) < 0.05]
        print(f"[colcha] x {xc}: " + " ".join(f"{y:.2f}:{s[np.abs(s[:, 1] - y) < 0.03][:, 2].max() if (np.abs(s[:, 1] - y) < 0.03).any() else 0:.3f}"
                                         for y in np.arange(4.60, 5.95, 0.1)))

# esquina del pie, lado pared (+y; izquierda en la foto 5): qué objetos hay y perfil de la colcha
from mathutils import Vector
for ob in bpy.data.objects:
    if ob.type != 'MESH' or ob.hide_render:
        continue
    p = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    lo = [min(q[i] for q in p) for i in range(3)]; hi = [max(q[i] for q in p) for i in range(3)]
    if lo[0] < 2.3 and hi[0] > 1.9 and lo[1] < 5.95 and hi[1] > 5.5 and lo[2] < 3.65 and hi[2] > 3.3:
        print(f"[esquina] {ob.name:28s} {[round(x, 3) for x in lo]} {[round(x, 3) for x in hi]}")
o = bpy.data.objects.get("Plane.016")
if o:
    ev = o.evaluated_get(dg); me = ev.to_mesh()
    v = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", v); v = v.reshape(-1, 3)
    mw = np.array(ev.matrix_world); v = v @ mw[:3, :3].T + mw[:3, 3]; ev.to_mesh_clear()
    for xc in (1.98, 2.05, 2.15, 2.25, 2.4):
        s = v[np.abs(v[:, 0] - xc) < 0.015]
        row = []
        for y in np.arange(5.45, 5.95, 0.05):
            t = s[np.abs(s[:, 1] - y) < 0.012]
            row.append(f"{y:.2f}:{t[:, 2].max():.3f}/{len(t)}" if len(t) else f"{y:.2f}:-")
        print(f"[esquina] x {xc}: " + " ".join(row))
