"""Tamaño del sofá por silueta, con un modelo de cajas (no solo mover/escalar el mueble entero).

    python remoto/sofa_caja.py <geo.npz de exportar_siluetas.py> fotos/siluetas_foto01.json
El ajuste general (siluetas.py) solo traslada, gira y escala parejo: para el sofá pedía moverlo 55 cm hacia el cuarto
(a través de la pared no puede), señal de que lo que cambia es la PROFUNDIDAD.  Aquí el sofá son cajas pegadas a la
pared oeste (x = 0,02) y se ajustan: fondo D, extremo de la ventana y1, alto del asiento hs, alto del respaldo hb y
alto del brazo.  IoU contra el polígono marcado en la foto, sin contar los píxeles de otros muebles (la cama lo tapa).
"""
import json
import sys

import cv2
import numpy as np
from scipy.optimize import minimize

geo = np.load(sys.argv[1]); cfg = json.load(open(sys.argv[2], encoding="utf-8"))
Wp, Hp = [int(x) for x in geo["size"]]
mw = geo["cam_mw"]; R, t = mw[:3, :3], mw[:3, 3]
f = geo["lens"] / geo["sensor"] * max(Wp, Hp)
cx = Wp / 2 + geo["shift"][0] * max(Wp, Hp); cy = Hp / 2 - geo["shift"][1] * max(Wp, Hp)
Z0 = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
Y0 = 5.72 - 1.95 / 2                       # extremo del lado de la puerta: queda fuera del cuadro, no se ajusta
CARAS = [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6), (1, 2, 6), (1, 6, 5), (0, 3, 7), (0, 7, 4)]


def caja(x0, x1, y0, y1, z0, z1):
    v = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])
    return v[np.array(CARAS)]


def silueta(T):
    c = (T - t) @ R; z = -c[..., 2]
    uv = np.stack([cx + f * c[..., 0] / np.maximum(z, 1e-6), cy - f * c[..., 1] / np.maximum(z, 1e-6)], -1)
    m = np.zeros((Hp, Wp), np.uint8)
    for tri in np.round(uv[(z > 0.05).all(1)] * 16).astype(np.int32):
        if (np.abs(tri) < 2 ** 26).all():
            cv2.fillConvexPoly(m, tri, 1, lineType=cv2.LINE_8, shift=4)
    return m


def sofa(p):
    D, y1, hs, hb, ha = p
    return np.concatenate([caja(0.02, D, Y0, y1, Z0, Z0 + hs),                 # base + asiento + manta que cuelga
                           caja(0.02, 0.26, Y0, y1 - 0.12, Z0, Z0 + hb),       # respaldo con la banda estampada
                           caja(0.02, min(D, 0.92), y1 - 0.14, y1, Z0, Z0 + ha)])   # brazo del lado de la ventana


mas = {}
for et, s in cfg["siluetas"].items():
    m = np.zeros((Hp, Wp), np.uint8); cv2.fillPoly(m, [np.round(np.array(s["poligono"])).astype(np.int32)], 1); mas[et] = m
otros = np.zeros((Hp, Wp), np.uint8)
for k, m in mas.items():
    if k != "sofa":
        otros |= m
val = otros == 0
obj = cv2.GaussianBlur(mas["sofa"].astype(np.float32), (0, 0), 2)


def iou(p, dura=False):
    sm = silueta(sofa(p))
    if dura:
        a, b = (sm > 0) & val, (mas["sofa"] > 0) & val
        return (a & b).sum() / max(1, (a | b).sum())
    a = cv2.GaussianBlur(sm.astype(np.float32), (0, 0), 2)
    return float((np.minimum(a, obj) * val).sum() / max(1e-6, (np.maximum(a, obj) * val).sum()))


p0 = np.array([0.92, 5.72 + 1.95 / 2, 0.42, 0.84, 0.56])
mejor = None
for ini in (p0, p0 * [1.3, 1, 1, 1, 1], p0 * [1.6, 1.02, 1.1, 0.9, 1]):
    r = minimize(lambda p: 1 - iou(p), ini, method="Nelder-Mead", options=dict(xatol=2e-3, fatol=1e-4, maxiter=800))
    if mejor is None or r.fun < mejor.fun:
        mejor = r
p = mejor.x
print(f"modelo actual  fondo {p0[0]:.2f}  extremo ventana y {p0[1]:.2f}  asiento {p0[2]:.2f}  respaldo {p0[3]:.2f}  brazo {p0[4]:.2f}   IoU {iou(p0, True):.3f}")
print(f"ajustado       fondo {p[0]:.2f}  extremo ventana y {p[1]:.2f}  asiento {p[2]:.2f}  respaldo {p[3]:.2f}  brazo {p[4]:.2f}   IoU {iou(p, True):.3f}")
for i, n in enumerate(("fondo", "extremo y", "asiento", "respaldo", "brazo")):        # sensibilidad: cuánto fija la foto
    q = p.copy(); fila = []
    for d in (-0.10, -0.05, 0.05, 0.10):
        q[i] = p[i] + d; fila.append(f"{d:+.2f}: {iou(q, True):.3f}")
    print(f"  {n:10s} " + "   ".join(fila))
foto = cv2.imread("fotos/jpg/" + cfg["foto"])
for q, col in ((p0, (0, 0, 255)), (p, (0, 255, 0))):
    cs, _ = cv2.findContours(silueta(sofa(q)), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE); cv2.drawContours(foto, cs, -1, col, 1)
cv2.imwrite("fotos/siluetas_foto01_sofa.png", cv2.resize(foto[380:680, 0:300], None, fx=2.6, fy=2.6, interpolation=cv2.INTER_CUBIC))
print("-> fotos/siluetas_foto01_sofa.png (PRIVADA): rojo = modelo actual, verde = ajustado")
