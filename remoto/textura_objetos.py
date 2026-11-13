"""Imperfección medida: cuánta VARIACIÓN tiene cada objeto en la foto y en el render, por tamaño de detalle.

    python remoto/textura_objetos.py <foto.jpg> <render.png> --mapa <mapa.npz> [--salida base] [--min-px 3000]

Por objeto (región del mapa, erosionada) y por banda de tamaño (detalle de ~2, 4, 8, 16, 32 px a 1080 px de ancho):
  energía = desviación estándar de la luminosidad L* filtrada en esa banda (diferencia de gaussianas),
            dividida por la L* media del objeto (contraste relativo: no depende de la exposición).
  razón   = foto / render.   > 1,5: al render le falta variación de ese tamaño;  < 0,67: le sobra.
Bandas finas (2-4 px) = grano, trama, poro;  medias (8-16) = manchas, vetas, costuras;  gruesas (32) = pliegues,
degradados de luz.  Ojo: la banda de 2 px incluye el ruido y el enfoque del teléfono; pesa menos como evidencia.
También da la variación de TONO (a*, b*) en la banda media, y la DIRECCIÓN (anisotropía del tensor de estructura
en 8-16 px): 0 = manchas sin dirección, 1 = líneas paralelas.  Igualar la energía sin igualar la dirección dio telas
con manchas de humedad: la cantidad sola no basta.
"""
import argparse
import json

import cv2
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("foto"); ap.add_argument("render"); ap.add_argument("--mapa", required=True)
ap.add_argument("--salida"); ap.add_argument("--min-px", type=int, default=3000)
a = ap.parse_args()
ren = cv2.imread(a.render); H, W = ren.shape[:2]
fot = cv2.resize(cv2.imread(a.foto), (W, H), interpolation=cv2.INTER_AREA)
esc = W / 1080.0
SIG = [1, 2, 4, 8, 16]                                   # sigma en px a 1080 de ancho (detalle ~2 sigma)


def lab(bgr):
    return cv2.cvtColor(bgr.astype(np.float32) / 255, cv2.COLOR_BGR2Lab)


def bandas(L):
    g = [L] + [cv2.GaussianBlur(L, (0, 0), s * esc * 1.0) for s in SIG] + [cv2.GaussianBlur(L, (0, 0), SIG[-1] * 2 * esc)]
    return [g[i + 1] - g[i + 2] for i in range(len(SIG))]   # entre sigma y el siguiente


def mad(x):
    """Dispersión robusta (mediana de desvíos x 1,4826): un cuadro o un cable corrido unos px dentro de la región
    no la infla, como sí pasaba con la desviación estándar (pared 2-5 % -> irreal para pintura lisa)."""
    return float(np.median(np.abs(x - np.median(x))) * 1.4826)


fL, rL = lab(fot), lab(ren)
fb, rb = bandas(fL[..., 0]), bandas(rL[..., 0])
fcol = [cv2.GaussianBlur(fL[..., c], (0, 0), 4 * esc) - cv2.GaussianBlur(fL[..., c], (0, 0), 16 * esc) for c in (1, 2)]
rcol = [cv2.GaussianBlur(rL[..., c], (0, 0), 4 * esc) - cv2.GaussianBlur(rL[..., c], (0, 0), 16 * esc) for c in (1, 2)]
m = np.load(a.mapa)
ids = cv2.resize(m["ids"], (W, H), interpolation=cv2.INTER_NEAREST)
ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(40 * esc) | 1,) * 2)   # lejos de los bordes: solo el interior
filas = []
for k, clave in enumerate(m["claves"]):
    er = cv2.erode((ids == k).astype(np.uint8), ker).astype(bool)
    if er.sum() < a.min_px * esc * esc:
        continue
    Lf, Lr = max(float(fL[..., 0][er].mean()), 5), max(float(rL[..., 0][er].mean()), 5)
    ef = [mad(b[er]) / Lf * 100 for b in fb]; er_ = [mad(b[er]) / Lr * 100 for b in rb]
    cf = float(np.hypot(mad(fcol[0][er]), mad(fcol[1][er]))); cr = float(np.hypot(mad(rcol[0][er]), mad(rcol[1][er])))
    ani = []                                     # anisotropía en las bandas medias (8 y 16 px): 0 manchas, 1 líneas
    for bb in (fb, rb):
        gx = cv2.Sobel(bb[2] + bb[3], cv2.CV_32F, 1, 0)[er]; gy = cv2.Sobel(bb[2] + bb[3], cv2.CV_32F, 0, 1)[er]
        jxx, jyy, jxy = float((gx * gx).mean()), float((gy * gy).mean()), float((gx * gy).mean())
        ani.append(round(float(np.hypot(jxx - jyy, 2 * jxy) / max(jxx + jyy, 1e-9)), 2))
    filas.append(dict(region=str(clave), area=int(er.sum()), anisotropia_foto=ani[0], anisotropia_render=ani[1], foto=[round(x, 2) for x in ef], render=[round(x, 2) for x in er_],
                      razon=[round(x / max(y, 0.02), 2) for x, y in zip(ef, er_)], tono_foto=round(cf, 2), tono_render=round(cr, 2)))
filas.sort(key=lambda f: -f["area"])
# piso de ruido de la cámara: el techo es pintura lisa, lo que mide ahí es grano + compresión del teléfono.
# textura propia del objeto = raíz(foto^2 - ruido^2); "falta" = lo que hay que AGREGAR al render (en cuadratura)
ref = next((f for f in filas if f["region"].startswith("Ceiling")), None)
for f in filas:
    rui = ref["foto"] if ref else [0] * len(SIG)
    f["propia"] = [round(float(np.sqrt(max(x * x - n * n, 0))), 2) for x, n in zip(f["foto"], rui)]
    f["falta"] = [round(float(np.sqrt(max(x * x - y * y, 0))), 2) for x, y in zip(f["propia"], f["render"])]
if ref:
    print("ruido de cámara (techo), % de L por banda:", ref["foto"])
print(f"{'objeto':38s} banda px:  " + "   ".join(f"{2 * s:>4d}" for s in SIG) + "    tono(foto/render)")
for f in filas:
    print(f"{f['region'][:38]:38s} foto      " + "  ".join(f"{x:5.2f}" for x in f["foto"]) + f"    {f['tono_foto']:.2f}")
    print(f"{'':38s} render    " + "  ".join(f"{x:5.2f}" for x in f["render"]) + f"    {f['tono_render']:.2f}")
    print(f"{'':38s} propia    " + "  ".join(f"{x:5.2f}" for x in f["propia"]) + f"    dirección foto {f['anisotropia_foto']:.2f} / render {f['anisotropia_render']:.2f}")
    print(f"{'':38s} FALTA     " + "  ".join(f"{x:5.2f}" for x in f["falta"]))
if a.salida:
    json.dump(filas, open(a.salida + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
