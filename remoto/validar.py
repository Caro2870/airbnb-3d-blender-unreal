"""Validación geométrica SIN render del apartaestudio (idea de la usuaria, 2026-11-06).

Corre en Blender sobre la escena ya armada (run.py --norender --save) y revisa en segundos lo que antes se descubría
renderizando:
  1. medidas: piezas clave contra el plano / la foto / la ficha del producto (tolerancia en cm);
  2. flotantes: objetos apoyados que no tocan nada debajo (rayos BVH en coordenadas de mundo desde su base);
  3. paredes: muebles y telas con vértices fuera del departamento (atraviesan muros o la ventana);
  4. choques: pares de muebles que se interpenetran (BVH overlap), salvo los permitidos (telas blandas);
  5. reproyección: puntos 3D conocidos (esquinas de ventana, cama, techo) proyectados con la cámara gemela de cada
     foto y comparados con los píxeles marcados en la foto (fotos/puntos.json, ver remoto/marcar_puntos.py).
Lo que NO valida: materiales, luz ni "si se ve natural" (eso sigue necesitando render).

    blender -b output/apartaestudio.blend --python validar.py -- <repo openhouse> <salida.json> [puntos.json]
Sale con código 1 si algo falla (útil antes de lanzar un render largo).
"""
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:]
REPO, OUT = argv[0], argv[1]
PUNTOS = argv[2] if len(argv) > 2 else ""
sys.path.insert(0, REPO)
from houses.apartaestudio.plan import *          # noqa: E402,F401  (W, Y_WIN, Z0, ZC, BED_Y...)

BED_L, BED_W = 1.95, 1.20                       # muebles.py
HX = W - 0.1
FX = HX - BED_L
MATT_Z1 = Z0 + 0.52

t0 = time.time()
rep = {"fallas": [], "avisos": [], "medidas": [], "flotantes": [], "paredes": [], "choques": [], "reproyeccion": []}
dg = bpy.context.evaluated_depsgraph_get()


def falla(msg):
    rep["fallas"].append(msg)


def aviso(msg):
    rep["avisos"].append(msg)


def mesh_objs():
    return [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.visible_get() and not o.hide_render]


def world_geo(o):
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ev.matrix_world
    v = [mw @ x.co for x in me.vertices]
    f = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return v, f


GEO = {}


def geo(o):
    if o.name not in GEO:
        GEO[o.name] = world_geo(o)
    return GEO[o.name]


def bbox(objs):
    pts = [p for o in objs for p in geo(o)[0]]
    if not pts:
        return None
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def find(prefix):
    return [o for o in mesh_objs() if o.name.startswith(prefix)]


# ---------------------------------------------------------------- 1. medidas
# (etiqueta, prefijo, {eje: (min, max)} en metros sobre la caja de mundo; "top"/"bot" = z máx/mín)
MEDIDAS = [
    ("colchón: largo (plano 1,95)",  "Cube.009",   {"dx": (1.92, 1.98)}),
    ("colchón: ancho (foto 5: 1,20)", "Cube.009",  {"dy": (1.17, 1.23)}),
    ("colchón: alto de la cara superior", "Cube.009", {"top": (MATT_Z1 - 0.015, MATT_Z1 + 0.015)}),
    ("cama: centrada en BED_Y",      "Cube.009",   {"cy": (BED_Y - 0.03, BED_Y + 0.03)}),
    ("cabecero: alto 1,08 m",        "Wall_Fabric", {"top": (Z0 + 1.04, Z0 + 1.12)}),
    ("sofá: largo junto a la pared (foto/plano 1,95)", "Sofa_Cama", {"dy": (1.85, 2.05)}),
    ("sofá: fondo (ficha 0,85, plano 0,92)", "Sofa_Cama", {"dx": (0.83, 0.95)}),
    ("sofá: respaldo (foto ~0,72 m)", "Sofa_Cama", {"top": (Z0 + 0.66, Z0 + 0.82)}),
    ("sofá: apoyado en el piso",     "Sofa_Cama",  {"bot": (Z0 - 0.01, Z0 + 0.01)}),
    ("cortinas: del piso al techo",  "curtain",    {"bot": (Z0 - 0.01, Z0 + 0.03), "top": (ZC - 0.10, ZC + 0.001)}),
]
for label, pre, ax in MEDIDAS:
    objs = find(pre)
    if not objs:
        aviso(f"medidas: no está '{pre}' ({label})")
        continue
    lo, hi = bbox(objs)
    val = {"dx": hi.x - lo.x, "dy": hi.y - lo.y, "dz": hi.z - lo.z, "top": hi.z, "bot": lo.z,
           "cx": (lo.x + hi.x) / 2, "cy": (lo.y + hi.y) / 2}
    for k, (a, b) in ax.items():
        v = val[k]
        ok = a <= v <= b
        ref = v - Z0 if k in ("top", "bot") else v
        rep["medidas"].append({"pieza": label, "eje": k, "valor_m": round(ref, 3),
                               "rango_m": [round(a - Z0, 3), round(b - Z0, 3)] if k in ("top", "bot") else [a, b],
                               "ok": ok})
        if not ok:
            falla(f"medida fuera de rango: {label} ({k} = {ref:.3f} m)")

# ---------------------------------------------------------------- 2. flotantes
# objetos que deben apoyarse en algo (prefijos); los colgados de la pared/techo no se revisan
APOYADOS = ("Cama_", "Sofa_", "Linen", "Blue velvet", "Plane.015", "Plane.016", "Plane.017", "Plane.018",
            "Plane.021", "Mesa", "Silla", "Prop_", "Velador", "Nightstand", "Tapete", "Rug", "Esfera_Rattan")
COLGADOS = ("Prints", "Cuadro", "Repisa", "Shelf", "Lampara_Techo", "AC", "Cortina", "curtain", "Tringle", "Wall_Fabric")
todos = mesh_objs()
TREES = {}


def tree(o):
    if o.name not in TREES:
        v, f = geo(o)
        TREES[o.name] = BVHTree.FromPolygons(v, f) if f else None
    return TREES[o.name]


cands = [o for o in todos if o.name.startswith(APOYADOS) and not o.name.startswith(COLGADOS)]
for o in cands:
    v, _ = geo(o)
    if not v:
        continue
    z0 = min(p.z for p in v)
    # rest point: the smallest drop from ANY vertex (a draped duvet rests on its top while its hem hangs free)
    base = v[::max(1, len(v) // 6000)]
    lo, hi = bbox([o])
    best = 9.0
    for t in todos:
        if t is o or t.parent is o or o.parent is t:
            continue
        tl, th = bbox([t])
        if th.x < lo.x or tl.x > hi.x or th.y < lo.y or tl.y > hi.y or tl.z > hi.z:
            continue                                    # nothing of t is under o
        tr = tree(t)
        if tr is None:
            continue
        for p in base:
            hit = tr.ray_cast(p + Vector((0, 0, 0.005)), Vector((0, 0, -1)), 1.0)
            if hit[0] is not None:
                best = min(best, hit[3] - 0.005)
    gap = 0.0 if best < 0 else best
    rep["flotantes"].append({"objeto": o.name, "hueco_cm": round(gap * 100, 1)})
    if gap > 0.015:
        falla(f"flota: {o.name} queda {gap * 100:.1f} cm sobre lo que tiene debajo")

# ---------------------------------------------------------------- 3. paredes
# caja interior del departamento (sin balcón): x 0..W, y 0..Y_WIN, z Z0..ZC; tolerancia 1 cm
INTERIOR = ("Cama_", "Sofa_", "Linen", "Blue velvet", "Plane.01", "Plane.021", "Wall_Fabric", "curtain", "Tringle",
            "Mesa", "Silla", "Prop_", "Velador", "Nightstand", "Esfera_Rattan", "Tapete", "Rug")
TOL = 0.01
for o in [o for o in todos if o.name.startswith(INTERIOR)]:
    v, _ = geo(o)
    out = [p for p in v if p.x < -TOL or p.x > W + TOL or p.y < -TOL or p.y > Y_WIN + TOL or p.z < Z0 - TOL
           or p.z > ZC + TOL]
    if out:
        far = max(max(-p.x, p.x - W, -p.y, p.y - Y_WIN, Z0 - p.z, p.z - ZC) for p in out)
        rep["paredes"].append({"objeto": o.name, "vertices_fuera": len(out), "max_cm": round(far * 100, 1)})
        if far > 0.02:
            falla(f"atraviesa muro/ventana/piso: {o.name} ({len(out)} vértices, hasta {far * 100:.1f} cm)")
        else:
            aviso(f"roza el muro: {o.name} ({far * 100:.1f} cm)")

# ---------------------------------------------------------------- 4. choques entre muebles
MUEBLES = ("Cama_Base", "Cube.009", "Wall_Fabric", "Sofa_Cama", "Mesa", "Silla", "Velador", "Nightstand", "Closet",
           "Esfera_Rattan", "Linen", "Blue velvet", "Plane.017", "Plane.018")
# blandos que pueden hundirse unos en otros (telas, cojines contra almohadas/respaldo)
PERMITIDOS = [("Blue velvet", "Plane.01"), ("Blue velvet", "Wall_Fabric"), ("Plane.01", "Wall_Fabric"),
              ("Linen", "Sofa_"), ("Plane.01", "Cube.009"), ("Cube.009", "Cama_Base"), ("Plane.01", "Plane.01"),
              ("Blue velvet", "Blue velvet"), ("Linen", "Linen"),
              ("Wall_Fabric", "Wall_Fabric"),            # frame and padding of the same headboard model
              ("Mesa_Auxiliar", "Esfera_Rattan")]        # the ball rests on the table top


def permitido(a, b):
    return any((a.startswith(x) and b.startswith(y)) or (a.startswith(y) and b.startswith(x)) for x, y in PERMITIDOS)


mu = [o for o in todos if o.name.startswith(MUEBLES)]
for i, a in enumerate(mu):
    la, ha = bbox([a])
    for b in mu[i + 1:]:
        lb, hb = bbox([b])
        if ha.x < lb.x or hb.x < la.x or ha.y < lb.y or hb.y < la.y or ha.z < lb.z or hb.z < la.z:
            continue
        ta, tb = tree(a), tree(b)
        if ta is None or tb is None:
            continue
        n = len(ta.overlap(tb))
        if n == 0:
            continue
        ok = permitido(a.name, b.name)
        rep["choques"].append({"a": a.name, "b": b.name, "triangulos": n, "permitido": ok})
        if not ok and n > 20:
            falla(f"choque: {a.name} con {b.name} ({n} pares de triángulos)")

# ---------------------------------------------------------------- 5. reproyección contra las fotos
if PUNTOS and os.path.isfile(PUNTOS):
    from bpy_extras.object_utils import world_to_camera_view
    data = json.load(open(PUNTOS, encoding="utf-8"))
    S = bpy.context.scene
    rx, ry, pct = S.render.resolution_x, S.render.resolution_y, S.render.resolution_percentage
    for foto in data.get("fotos", []):
        cam = bpy.data.objects.get(foto["camara"]) or bpy.data.objects.get("Cam_" + foto["camara"])   # run.py: Cam_<name>
        pts = [p for p in foto["puntos"] if p.get("px")]
        if cam is None or not pts:
            aviso(f"reproyección: {foto['foto']} sin cámara '{foto['camara']}' o sin puntos marcados")
            continue
        Wp, Hp = foto["tamano"]
        S.render.resolution_x, S.render.resolution_y, S.render.resolution_percentage = Wp, Hp, 100
        errs = []
        for p in pts:
            ndc = world_to_camera_view(S, cam, Vector(p["xyz"]))
            u, v = ndc.x * Wp, (1 - ndc.y) * Hp
            e = math.hypot(u - p["px"][0], v - p["px"][1])
            errs.append(e)
            rep["reproyeccion"].append({"foto": foto["foto"], "punto": p["nombre"], "error_px": round(e, 1),
                                        "proyectado": [round(u), round(v)], "marcado": p["px"]})
        media = sum(errs) / len(errs)
        lim = foto.get("tolerancia_px", 0.015 * max(Wp, Hp))         # ~1,5 % del lado mayor por defecto
        if media > lim:
            falla(f"reproyección {foto['foto']}: error medio {media:.0f} px (> {lim:.0f}); cámara o geometría no calzan")
        rep.setdefault("reproyeccion_resumen", []).append({"foto": foto["foto"], "puntos": len(errs),
                                                           "error_medio_px": round(media, 1), "max_px": round(max(errs), 1),
                                                           "tolerancia_px": round(lim)})
    S.render.resolution_x, S.render.resolution_y, S.render.resolution_percentage = rx, ry, pct
else:
    aviso("reproyección: sin fotos/puntos.json con puntos marcados (usar remoto/marcar_puntos.py)")

rep["segundos"] = round(time.time() - t0, 1)
rep["ok"] = not rep["fallas"]
json.dump(rep, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"[validar] {'OK' if rep['ok'] else 'FALLA'}: {len(rep['fallas'])} fallas, {len(rep['avisos'])} avisos, "
      f"{rep['segundos']} s")
for m in rep["fallas"]:
    print("[validar] FALLA", m)
for m in rep["avisos"]:
    print("[validar] aviso", m)
sys.exit(0 if rep["ok"] else 1)
