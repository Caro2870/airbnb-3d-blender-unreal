"""Ajuste por SILUETAS: mueve cada mueble del modelo hasta que su silueta calce con la de la foto.

Entradas:
  - <geo.npz> de remoto/exportar_siluetas.py (triángulos de mundo por etiqueta + cámara gemela), sin render;
  - fotos/siluetas_fotoNN.json (PRIVADO): polígono visible de cada mueble en la foto, marcado a mano (o con SAM).
Para cada etiqueta optimiza (Nelder-Mead) una corrección pequeña y devuelve cuánto mover:
  modo "piso":  dx, dy (m), giro en Z (°) y escala uniforme, alrededor del centro del mueble en planta;
  modo "pared": dx, dz (m) y escala en ancho/alto (persianas, cuadros).
La medida es IoU suave (máscaras con desenfoque de 2 px) contando solo píxeles que no pertenecen a OTRO mueble
marcado: así una oclusión (la mesa de noche tapando la cama) no castiga a ninguno de los dos.

    python remoto/siluetas.py <geo.npz> fotos/siluetas_foto01.json [--solo-medir]
Salida: tabla por mueble (IoU antes -> después y corrección) + fotos/siluetas_foto01_ajuste.png (PRIVADA).
No cambia el modelo: la corrección se pasa a plan.py / muebles.py a mano (la escena se genera por código).
"""
import json
import math
import sys

import cv2
import numpy as np
from scipy.optimize import minimize

geo = np.load(sys.argv[1])
cfg = json.load(open(sys.argv[2], encoding="utf-8"))
SOLO = "--solo-medir" in sys.argv
Wp, Hp = [int(x) for x in geo["size"]]
mw = geo["cam_mw"]; R, t = mw[:3, :3], mw[:3, 3]
f = geo["lens"] / geo["sensor"] * max(Wp, Hp)
cx = Wp / 2 + geo["shift"][0] * max(Wp, Hp); cy = Hp / 2 - geo["shift"][1] * max(Wp, Hp)
SIG = 2.0


def proyectar(P):
    c = (P - t) @ R                        # coordenadas de cámara (x der, y arriba, mirando -z)
    z = -c[..., 2]
    return np.stack([cx + f * c[..., 0] / np.maximum(z, 1e-6), cy - f * c[..., 1] / np.maximum(z, 1e-6)], -1), z


def silueta(T):
    uv, z = proyectar(T)
    ok = (z > 0.05).all(1)
    m = np.zeros((Hp, Wp), np.uint8)
    pts = np.round(uv[ok] * 16).astype(np.int32)
    pts = pts[(np.abs(pts) < 2 ** 26).all((1, 2))]
    for tri in pts:                        # fillPoly con varios polígonos hace XOR donde se solapan: uno por uno
        cv2.fillConvexPoly(m, tri, 1, lineType=cv2.LINE_8, shift=4)
    return m


def transformar(T, p, modo, c0):
    if modo == "piso":
        dx, dy, yaw, s = p
        a = math.radians(yaw); ca, sa = math.cos(a), math.sin(a)
        X = T - c0
        Xr = np.stack([ca * X[..., 0] - sa * X[..., 1], sa * X[..., 0] + ca * X[..., 1], X[..., 2]], -1) * s
        return Xr + c0 + [dx, dy, 0.0]
    dx, dz, sx, sz = p
    X = T - c0
    return np.stack([X[..., 0] * sx, X[..., 1], X[..., 2] * sz], -1) + c0 + [dx, 0.0, dz]


def blur(m):
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), SIG)


mascaras = {}
for et, s in cfg["siluetas"].items():
    m = np.zeros((Hp, Wp), np.uint8)
    cv2.fillPoly(m, [np.round(np.array(s["poligono"])).astype(np.int32)], 1)
    mascaras[et] = m

foto = cv2.imread("fotos/jpg/" + cfg["foto"])
vis = foto.copy()
filas = []
for et, s in cfg["siluetas"].items():
    if "tri_" + et not in geo:
        print(f"{et:12s} sin geometría en el .npz"); continue
    T = geo["tri_" + et].astype(np.float64)
    modo = s.get("modo", "piso")
    c0 = T.reshape(-1, 3).mean(0)
    if modo == "piso":
        c0[2] = 0
    otros = np.zeros((Hp, Wp), np.uint8)
    for k, m in mascaras.items():
        if k != et:
            otros |= m
    valido = blur(1 - otros) > 0.5
    obj = blur(mascaras[et])

    def iou(p, dura=False):
        sm = silueta(transformar(T, p, modo, c0))
        if dura:
            a, b = (sm > 0) & valido, (mascaras[et] > 0) & valido
            return (a & b).sum() / max(1, (a | b).sum())
        a = blur(sm) * valido; b = obj * valido
        return (np.minimum(a, b).sum()) / max(1e-6, np.maximum(a, b).sum())

    p0 = np.array([0.0, 0.0, 0.0, 1.0]) if modo == "piso" else np.array([0.0, 0.0, 1.0, 1.0])
    i0 = iou(p0, True)
    if SOLO:
        p, i1 = p0, i0
    else:
        paso = [0.06, 0.06, 4.0, 0.04] if modo == "piso" else [0.06, 0.06, 0.05, 0.05]
        best = None
        for arranque in ([0, 0], [0.1, 0], [-0.1, 0], [0, 0.1], [0, -0.1]):
            x0 = p0 + [arranque[0], arranque[1], 0, 0]
            simplex = [x0] + [x0 + np.eye(4)[k] * paso[k] for k in range(4)]
            r = minimize(lambda q: 1 - iou(q), x0, method="Nelder-Mead",
                         options={"initial_simplex": simplex, "xatol": 1e-3, "fatol": 1e-4, "maxiter": 300})
            if best is None or r.fun < best.fun:
                best = r
        p = best.x
        lim = [0.4, 0.4, 15, 0.15] if modo == "piso" else [0.4, 0.4, 0.3, 0.3]
        if any(abs(p[k] - p0[k]) > lim[k] for k in range(4)):
            print(f"{et:12s} corrección fuera de rango {np.round(p, 3)}: se descarta (revisar la máscara)")
            p = p0
        i1 = iou(p, True)
    fila = {"mueble": et, "modo": modo, "iou_antes": round(float(i0), 3), "iou_despues": round(float(i1), 3)}
    if modo == "piso":
        fila.update(dx=round(p[0], 3), dy=round(p[1], 3), giro=round(p[2], 1), escala=round(p[3], 3))
    else:
        fila.update(dx=round(p[0], 3), dz=round(p[1], 3), escala_ancho=round(p[2], 3), escala_alto=round(p[3], 3))
    filas.append(fila)
    # dibujo: foto (verde), modelo antes (rojo), después (amarillo)
    for m, col in ((mascaras[et], (0, 220, 0)), (silueta(transformar(T, p0, modo, c0)), (0, 0, 255)),
                   (silueta(transformar(T, p, modo, c0)), (0, 230, 255))):
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, cs, -1, col, 1)

print(f"\n{'mueble':12s} {'IoU antes':>9s} {'después':>8s}   corrección")
for r in filas:
    extra = {k: v for k, v in r.items() if k not in ("mueble", "modo", "iou_antes", "iou_despues")}
    print(f"{r['mueble']:12s} {r['iou_antes']:9.3f} {r['iou_despues']:8.3f}   {extra}")
base = sys.argv[2].replace(".json", "")
cv2.imwrite(base + "_ajuste.png", cv2.resize(vis, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST))
json.dump(filas, open(base + "_ajuste.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
