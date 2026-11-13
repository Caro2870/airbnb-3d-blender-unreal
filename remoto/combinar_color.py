"""Combina las mediciones de color de VARIAS fotos (salidas .json de color_objetos.py) y separa material de luz.

    python remoto/combinar_color.py avance/img/color_objetos_foto01.json avance/img/color_objetos_foto05.json [--ref Walls]

Cada foto tiene su exposición y su balance de blancos, así que el factor crudo foto/render mezcla luz y material.
1. Normaliza: divide el factor de cada objeto por el de una referencia de color conocido en ESA foto (la pared
   blanca).  Lo que queda es cuánto más claro u oscuro es el objeto respecto a la pared, en foto y en render.
2. Junta las fotos: si los factores normalizados coinciden (razón < 1,6 por canal) la diferencia es del MATERIAL y
   se propone el color base nuevo (media geométrica, amortiguada 0,8).  Si no coinciden, es LUZ u oclusión (o la
   región está mal alineada): no tocar el material.
"""
import json
import sys

import numpy as np

args = [x for x in sys.argv[1:] if not x.startswith("--")]
ref = sys.argv[sys.argv.index("--ref") + 1] if "--ref" in sys.argv else "Walls"
fotos = []
for p in args:
    d = {r["region"]: r for r in json.load(open(p, encoding="utf-8"))["regiones"]}
    k = next((n for n in d if n.startswith(ref)), None)
    if k is None:
        raise SystemExit(f"{p}: sin región de referencia {ref}")
    fr = np.array(d[k]["factor"])
    print(f"{p}: referencia {k} factor {fr}")
    fotos.append({n: (np.array(r["factor"]) / fr, r) for n, r in d.items()})
nombres = sorted(set().union(*fotos), key=lambda n: -max(f[n][1]["area"] * f[n][1]["dE"] for f in fotos if n in f))
print(f"\n{'región':42s} {'veredicto':10s} factor normalizado por foto            base nueva")
for n in nombres:
    fs = [f[n][0] for f in fotos if n in f]
    recorte = any(min(f[n][1]["factor"]) <= 0.31 or max(f[n][1]["factor"]) >= 2.99 for f in fotos if n in f)
    txt = "  |  ".join(" ".join(f"{x:.2f}" for x in v) for v in fs)
    if len(fs) < 2:
        ver = "1 foto"
    else:
        ver = "MATERIAL" if max(np.max(np.maximum(fs[0], fs[1]) / np.minimum(fs[0], fs[1])), 1) < 1.6 else "luz/forma"
    g = np.exp(np.mean([np.log(v) for v in fs], 0))
    base = next((f[n][1].get("base") for f in fotos if n in f and f[n][1].get("base")), None)
    nueva = ""
    if ver == "MATERIAL" and np.max(np.abs(np.log(g))) > 0.12:
        nueva = f"x{np.round(g ** 0.8, 2)}" + (f" -> {np.round(np.clip(np.array(base) * g ** 0.8, 0, 0.95), 3)}" if base else "")
    elif ver == "MATERIAL":
        nueva = "ok"
    print(f"{n[:42]:42s} {ver:10s} {txt:40s} {nueva}{'  (factor recortado: es mayor)' if recorte else ''}")
