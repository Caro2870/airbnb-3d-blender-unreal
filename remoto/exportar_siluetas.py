"""Exporta (sin render) la geometría de los muebles y la cámara gemela de una foto, para remoto/siluetas.py.

    blender -b apartaestudio.blend --python exportar_siluetas.py -- <salida.npz> <camara> <ancho_px> <alto_px>
Guarda por etiqueta los triángulos en coordenadas de mundo y la matriz/lente de la cámara.  Corre en segundos.
"""
import sys

import bpy
import numpy as np

GRUPOS = {   # etiqueta de siluetas_fotoNN.json -> prefijos de objetos en la escena (código o biblioteca)
    "cama": ["Cama_Base", "Cama_Colchon", "Cube.009", "Plane.015", "Plane.016", "Plane.017", "Plane.018", "Plane.021",
             "Bed", "Cushions_Blue", "Cama_Toalla"],
    "cabecero": ["Wall_Fabric", "Cama_Cabecero", "Headboard"],
    "mesa_noche": ["Mesa_Noche", "Nightstand"],
    "alfombra": ["Tapete", "Rug"],
    "persiana": ["Roller_Blind"],
    "sofa": ["Sofa"],
}

MAX_TRIS = 3000
argv = sys.argv[sys.argv.index("--") + 1:]
out, cam_name, wpx, hpx = argv[0], argv[1], int(argv[2]), int(argv[3])
dg = bpy.context.evaluated_depsgraph_get()
cam = bpy.data.objects.get(cam_name) or next(o for o in bpy.data.objects if o.type == 'CAMERA' and o.name.endswith(cam_name))
d = {"cam_mw": np.array(cam.matrix_world), "lens": cam.data.lens, "sensor": cam.data.sensor_width,
     "shift": np.array([cam.data.shift_x, cam.data.shift_y]), "size": np.array([wpx, hpx])}
for et, pref in GRUPOS.items():
    tris, nombres = [], []
    for o in bpy.context.scene.objects:
        if o.type != 'MESH' or o.hide_render or not any(o.name.startswith(p) for p in pref):
            continue
        dec = None
        ev0 = o.evaluated_get(dg); n_ev = len(ev0.data.polygons)    # después de subdivisión y demás modificadores
        if n_ev > MAX_TRIS:                                          # para la silueta basta una versión simplificada
            dec = o.modifiers.new("dec_siluetas", 'DECIMATE'); dec.ratio = MAX_TRIS / n_ev
            dg.update()
        ev = o.evaluated_get(dg); me = ev.to_mesh(); me.calc_loop_triangles()
        mw = np.array(ev.matrix_world)
        v = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", v); v = v.reshape(-1, 3)
        v = v @ mw[:3, :3].T + mw[:3, 3]
        t = np.empty(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get("vertices", t)
        tris.append(v[t.reshape(-1, 3)]); nombres.append(o.name)
        ev.to_mesh_clear()
        if dec:
            o.modifiers.remove(dec); dg.update()
    if tris:
        d["tri_" + et] = np.concatenate(tris).astype(np.float32)
        print(f"[siluetas] {et}: {len(nombres)} objetos, {len(d['tri_' + et])} triángulos  ({', '.join(nombres[:6])})")
    else:
        print(f"[siluetas] {et}: no hay objetos")
np.savez_compressed(out, **d)
