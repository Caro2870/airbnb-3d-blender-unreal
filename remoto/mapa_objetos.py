"""Mapa de objetos SIN render: qué objeto y qué material se ve en cada píxel de una cámara gemela de foto.

    blender -b apartaestudio.blend --python mapa_objetos.py -- <salida.npz> <camara> [escala_% = 47] [paso_px = 1]
Lanza un rayo por píxel (scene.ray_cast) desde la cámara, atravesando vidrios, y guarda:
  ids   (alto, ancho) int16: índice en `claves`, -1 = nada
  claves  "Objeto|Material" por índice;  base  color base (lineal) del material, NaN si viene de una textura
  prof  profundidad en metros (para separar oclusiones)
Sirve a remoto/color_objetos.py para comparar color y forma POR OBJETO contra la foto (no a ojo).  Tarda segundos y
no usa la GPU, así que corre por ssh directo (no hace falta tarea programada).
"""
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
out, cam_name = argv[0], argv[1]
escala = float(argv[2]) if len(argv) > 2 else 47.0
paso = int(argv[3]) if len(argv) > 3 else 2
S = bpy.context.scene
cam = bpy.data.objects.get(cam_name) or next(o for o in bpy.data.objects if o.type == 'CAMERA' and o.name.endswith(cam_name))
S.camera = cam
# resolución de ESA cámara (las gemelas de foto son verticales: house.CAM_RES), no la de la escena
rx_, ry_ = S.render.resolution_x, S.render.resolution_y
try:
    sys.path.insert(0, bpy.path.abspath("//../../.."))
    from houses.apartaestudio import house as _H
    rx_, ry_ = _H.CAM_RES.get(cam_name, (rx_, ry_))
except Exception as e:                                   # sin el paquete: argumento 5 = "ancho,alto"
    print(f"[mapa] sin house.CAM_RES ({e})")
if len(argv) > 4:
    rx_, ry_ = [int(x) for x in argv[4].split(",")]
S.render.resolution_x, S.render.resolution_y = rx_, ry_
W = int(rx_ * escala / 100); H = int(ry_ * escala / 100)
dg = bpy.context.evaluated_depsgraph_get()
mw = cam.matrix_world
o0 = mw.translation.copy()
tr, br, bl, tl = [mw @ v for v in cam.data.view_frame(scene=S)]          # esquinas del cuadro, con shift incluido

VIDRIO = ("glass", "vidrio", "cristal")
import os
OCULTOS = set(x for x in os.environ.get("HOUSE_HIDE", "").split(",") if x)


def base_color(mat):
    if mat is None or not mat.use_nodes:
        return (np.nan,) * 3
    b = next((n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if b is None or b.inputs["Base Color"].is_linked:
        return (np.nan,) * 3
    return tuple(b.inputs["Base Color"].default_value[:3])


def transparente(ob, mat):
    if ob.hide_render or ob.name in OCULTOS:      # lo que el render no dibuja (HOUSE_HIDE: aire, polvo) no tapa
        return True
    n = (ob.name + "|" + (mat.name if mat else "")).lower()
    if "volum" in n:
        return True
    if any(k in n for k in VIDRIO):
        return True
    if mat is not None and mat.use_nodes:
        b = next((x for x in mat.node_tree.nodes if x.bl_idname == "ShaderNodeBsdfPrincipled"), None)
        if b is not None and "Transmission Weight" in b.inputs and b.inputs["Transmission Weight"].default_value > 0.5:
            return True
    return False


t0 = time.time()
claves, idx, bases = [], {}, []
mat_cache = {}                                   # (objeto, índice de cara) es caro: cachear materiales por objeto
ids = np.full((H // paso, W // paso), -1, np.int16)
prof = np.zeros(ids.shape, np.float32)
for j in range(ids.shape[0]):
    v = (j * paso + 0.5) / H
    izq = tl.lerp(bl, v); der = tr.lerp(br, v)
    for i in range(ids.shape[1]):
        u = (i * paso + 0.5) / W
        d = (izq.lerp(der, u) - o0).normalized()
        o = o0; dist = 0.0
        for _ in range(6):                       # hasta 5 vidrios / volúmenes seguidos
            hit, loc, nor, fi, ob, _m = S.ray_cast(dg, o, d)
            if not hit:
                break
            key = ob.name
            if key not in mat_cache:
                ev = ob.evaluated_get(dg)
                me = ev.data
                mat_cache[key] = (np.array([p.material_index for p in me.polygons], np.int16) if hasattr(me, "polygons") else None,
                                  [s.material for s in ev.material_slots])
            mi, slots = mat_cache[key]
            mat = slots[mi[fi]] if (mi is not None and slots and fi < len(mi) and mi[fi] < len(slots)) else None
            dist += (loc - o).length
            if transparente(ob, mat):
                o = loc + d * 1e-3
                continue
            k = ob.name + "|" + (mat.name if mat else "-")
            if k not in idx:
                idx[k] = len(claves); claves.append(k); bases.append(base_color(mat))
            ids[j, i] = idx[k]; prof[j, i] = dist
            break
np.savez_compressed(out, ids=ids, claves=np.array(claves), base=np.array(bases, np.float32), prof=prof,
                    size=np.array([W, H]), paso=paso, camara=cam_name)
print(f"[mapa] {cam_name}: {ids.shape[1]}x{ids.shape[0]} rayos, {len(claves)} objeto|material, {time.time() - t0:.1f}s -> {out}")
