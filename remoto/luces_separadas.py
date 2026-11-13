"""Renderiza cada GRUPO DE LUCES por separado (lineal, sin tono) para ajustar la mezcla contra una foto sin tanteo.

    blender -b apartaestudio.blend --python luces_separadas.py -- <salida.npz> <camara> [escala_% = 47] [muestras = 64] [ancho,alto = 1080,1920]
La imagen es lineal en las luces:  imagen = suma_g  peso_g * color_g * I_g.  Con las I_g guardadas, remoto/ajustar_luz.py
resuelve pesos y colores en la PC local en segundos, y solo se vuelve a renderizar para comprobar.
Grupos:  cielo (mundo + sol + emisivos de cielo/mar)  |  foco_<lámpara> (cada L_Down_* sola)  |  focos_emis (sus
         difusores)  |  rell_<nombre> (áreas Relleno_*: luces de estudio que el cuarto real NO tiene)  |  otros.
Usa la GPU: lanzarlo como tarea programada (lanzar_luces.ps1).
"""
import os
import sys
import tempfile
import time

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
out, cam_name = argv[0], argv[1]
escala = int(float(argv[2])) if len(argv) > 2 else 47
muestras = int(argv[3]) if len(argv) > 3 else 64
rx, ry = [int(x) for x in (argv[4] if len(argv) > 4 else "1080,1920").split(",")]
S = bpy.context.scene
S.camera = bpy.data.objects.get(cam_name) or next(o for o in bpy.data.objects if o.type == 'CAMERA' and o.name.endswith(cam_name))
S.render.resolution_x, S.render.resolution_y, S.render.resolution_percentage = rx, ry, escala
S.render.image_settings.file_format = 'OPEN_EXR'; S.render.image_settings.color_depth = '32'
S.render.use_compositing = False
S.cycles.samples = muestras; S.cycles.device = 'GPU'
pr = bpy.context.preferences.addons['cycles'].preferences
try:
    pr.compute_device_type = 'OPTIX'; pr.get_devices()
    for d in pr.devices:
        d.use = d.type == 'OPTIX'
except Exception as e:
    print(f"[luces] sin OPTIX: {e}")
for n in os.environ.get("HOUSE_HIDE", "").split(","):
    o = bpy.data.objects.get(n)
    if o is not None:
        o.hide_render = True


def grupo_de(nombre, tipo=""):
    n = nombre.lower()
    if tipo == 'SUN' or any(k in n for k in ("cielo", "sky", "mar", "sea", "sol")):
        return "cielo"
    if "down" in n:
        return ("foco_" + nombre) if tipo else "focos_emis"      # cada lámpara por separado; sus difusores, juntos
    if "relleno" in n:
        return "rell_" + nombre
    return "otros"


luces = [(o, o.data.energy, grupo_de(o.name, o.data.type)) for o in bpy.data.objects
         if o.type == 'LIGHT' and not o.hide_render and o.data.energy > 0]
emis = []                                         # (socket, valor, grupo): emisión de materiales, no enlazada
for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    for nd in m.node_tree.nodes:
        s = None
        if nd.bl_idname == "ShaderNodeBsdfPrincipled":
            s = nd.inputs.get("Emission Strength")
        elif nd.bl_idname == "ShaderNodeEmission":
            s = nd.inputs.get("Strength")
        if s is not None and not s.is_linked and s.default_value > 0:
            emis.append((s, s.default_value, grupo_de(m.name)))
mundo = S.world
negro = bpy.data.worlds.new("Mundo_Negro"); negro.use_nodes = True
negro.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
print("[luces] luces:", [(o.name, round(e, 1), g) for o, e, g in luces])
print("[luces] emisivos:", sorted(set((s.id_data.name, round(v, 2), g) for s, v, g in emis)))

tmp = os.path.join(tempfile.gettempdir(), "luces_grupo.exr")
res = {}
grupos = ["cielo", "otros"] + sorted(set(g for *_, g in luces) | set(g for *_, g in emis) - {"cielo", "otros"})
for g in grupos:
    t = time.time()
    S.world = mundo if g == "cielo" else negro
    for o, e, og in luces:
        o.data.energy = e if og == g else 0.0
    for s, v, sg in emis:
        s.default_value = v if sg == g else 0.0
    S.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(tmp, check_existing=False)
    w, h = im.size
    px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px)
    res[g] = px.reshape(h, w, 4)[::-1, :, :3].astype(np.float16)
    bpy.data.images.remove(im)
    print(f"[luces] {g}: media {res[g].astype(np.float32).mean():.4f}  ({time.time() - t:.0f}s)")
for o, e, _ in luces:
    o.data.energy = e
for s, v, _ in emis:
    s.default_value = v
S.world = mundo
np.savez_compressed(out, camara=cam_name, exposicion=S.view_settings.exposure,
                    grupos=np.array(grupos), luces=np.array([f"{o.name}|{e}|{g}|{tuple(round(c, 3) for c in o.data.color)}" for o, e, g in luces]), **res)
print(f"[luces] -> {out}")
