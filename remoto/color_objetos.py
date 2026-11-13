"""Color POR OBJETO: foto vs render, con números (no a ojo).  Corre en la PC local (numpy + OpenCV), sin Blender.

    python remoto/color_objetos.py <foto.jpg> <render.png> --mapa <mapa.npz>          # regiones = objeto|material
    python remoto/color_objetos.py <foto.jpg> <render.png> --siluetas fotos/siluetas_foto01.json   # regiones a mano
    opciones: --salida <base>  (escribe <base>.json y <base>.jpg, PRIVADOS)   --min-px 400   --erosion 4

Por cada región (erosionada, para que un desajuste de 2-4 px en la silueta no contamine):
  1. dE   diferencia de color foto/render en CIELAB (mediana; <5 casi igual, 5-10 se nota, >10 otro color).
  2. factor por canal (en lineal) = foto / render.  El color base nuevo es  base * factor^0.8  (amortiguado: la luz
     indirecta cambia cuando cambia el color, así que converge en 2-3 pasadas en vez de oscilar).  Si el mapa trae
     el color base del material, se imprime ya calculado, listo para pegar en el código.
  3. DOS COLORES: 2-medias en Lab dentro de la región de la FOTO.  Si la foto tiene dos grupos claros (separación
     dE > 18, el menor >= 15 % del área) y el render no, el objeto del modelo es en realidad DOS cosas (la sábana
     caqui bajo la colcha blanca pasó así: el modelo era todo blanco).  Es el aviso de "te falta un objeto/capa".
  4. forma: IoU de la región del modelo contra la misma región segmentada por color en la foto (solo con --mapa).
La tabla sale ordenada por (dE x área): arriba, lo que más se nota en la imagen.
"""
import argparse
import json

import cv2
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("foto"); ap.add_argument("render")
ap.add_argument("--mapa"); ap.add_argument("--siluetas"); ap.add_argument("--salida")
ap.add_argument("--min-px", type=int, default=400); ap.add_argument("--erosion", type=int, default=4)
ap.add_argument("--amort", type=float, default=0.8)
a = ap.parse_args()

ren = cv2.imread(a.render, cv2.IMREAD_COLOR)
H, W = ren.shape[:2]
fot = cv2.resize(cv2.imread(a.foto, cv2.IMREAD_COLOR), (W, H), interpolation=cv2.INTER_AREA)


def lineal(bgr):
    c = bgr.astype(np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lab(bgr):
    return cv2.cvtColor(bgr.astype(np.float32) / 255.0, cv2.COLOR_BGR2Lab)


fl, rl, fL, rL = lineal(fot), lineal(ren), lab(fot), lab(ren)

regiones = {}                                                   # nombre -> (máscara bool, color base o None)
if a.mapa:
    m = np.load(a.mapa, allow_pickle=False)
    ids = cv2.resize(m["ids"], (W, H), interpolation=cv2.INTER_NEAREST)
    for k, (clave, base) in enumerate(zip(m["claves"], m["base"])):
        regiones[str(clave)] = (ids == k, None if np.isnan(base).any() else base)
elif a.siluetas:
    cfg = json.load(open(a.siluetas, encoding="utf-8"))
    sx, sy = W / cfg["tamano"][0], H / cfg["tamano"][1]
    for nom, s in cfg["siluetas"].items():
        msk = np.zeros((H, W), np.uint8)
        cv2.fillPoly(msk, [np.round(np.array(s["poligono"], np.float32) * (sx, sy)).astype(np.int32)], 1)
        regiones[nom] = (msk.astype(bool), None)
    orden = sorted(regiones, key=lambda n: regiones[n][0].sum())    # lo chico tapa a lo grande (mesa sobre cama)
    visto = np.zeros((H, W), bool)
    for nom in orden:
        msk, b = regiones[nom]; regiones[nom] = (msk & ~visto, b); visto |= msk
else:
    raise SystemExit("falta --mapa o --siluetas")


def dos_medias(L):
    """Separación (dE) y reparto de los dos grupos de color de una región."""
    if len(L) < 200:
        return 0.0, 1.0, None
    Z = L.astype(np.float32).copy(); Z[:, 0] *= 0.5              # el brillo (sombras) pesa la mitad que el tono
    _, lbl, cen = cv2.kmeans(Z, 2, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5), 3,
                             cv2.KMEANS_PP_CENTERS)
    lbl = lbl.ravel(); frac = float(min((lbl == 0).mean(), (lbl == 1).mean()))
    c0, c1 = np.median(L[lbl == 0], 0), np.median(L[lbl == 1], 0)
    return float(np.linalg.norm(c0 - c1)), frac, (c0, c1)


ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * a.erosion + 1,) * 2)
filas = []
for nom, (msk, base) in regiones.items():
    area = int(msk.sum())
    if area < a.min_px:
        continue
    er = cv2.erode(msk.astype(np.uint8), ker).astype(bool)
    if er.sum() < a.min_px // 2:
        continue
    mf, mr = np.median(fL[er], 0), np.median(rL[er], 0)
    dE = float(np.linalg.norm(mf - mr))
    lf, lr = np.median(fl[er], 0)[::-1], np.median(rl[er], 0)[::-1]          # BGR -> RGB
    fac = np.clip(lf / np.maximum(lr, 1e-3), 0.3, 3.0)
    sep_f, frac_f, _ = dos_medias(fL[er]); sep_r, _, _ = dos_medias(rL[er])
    # solo en regiones grandes: en las chicas, 3-4 px de desajuste de silueta ya meten al vecino y dan falsos avisos
    dos = bool(sep_f > 18 and frac_f >= 0.15 and sep_r < 0.5 * sep_f and area >= 0.015 * W * H)
    fila = dict(region=nom, area=area, dE=round(dE, 1), factor=[round(float(x), 2) for x in fac],
                foto_lab=[round(float(x), 1) for x in mf], render_lab=[round(float(x), 1) for x in mr],
                sep_foto=round(sep_f, 1), sep_render=round(sep_r, 1), frac=round(frac_f, 2), dos_colores=dos)
    if base is not None:
        fila["base"] = [round(float(x), 3) for x in base]
        fila["base_nueva"] = [round(float(x), 3) for x in np.clip(base * fac ** a.amort, 0.0, 0.95)]
    if a.mapa:                                    # forma: en la FOTO, ¿qué parte de la región tiene "su" color?
        cerca = np.linalg.norm(fL - mf, axis=2) < 14
        cerca = cv2.morphologyEx(cerca.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
        dil = cv2.dilate(msk.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool)
        cand = cerca & dil
        fila["iou_color"] = round(float((cand & msk).sum() / max(1, (cand | msk).sum())), 2)
    filas.append(fila)

filas.sort(key=lambda f: -f["dE"] * f["area"])
tot = sum(f["area"] for f in filas)
print(f"{'región':44s} {'área%':>6s} {'dE':>5s}  factor R G B        2 colores (foto/render)")
for f in filas:
    extra = f"  base -> {f['base_nueva']}" if "base_nueva" in f else ""
    aviso = f"  ** DOS COLORES en la foto ({f['sep_foto']} vs {f['sep_render']}, {int(f['frac'] * 100)} %)" if f["dos_colores"] else ""
    print(f"{f['region'][:44]:44s} {100 * f['area'] / (W * H):6.1f} {f['dE']:5.1f}  "
          f"{f['factor'][0]:.2f} {f['factor'][1]:.2f} {f['factor'][2]:.2f}{extra}{aviso}")
dEm = sum(f["dE"] * f["area"] for f in filas) / max(1, tot)
print(f"dE medio ponderado por área: {dEm:.1f}   (regiones: {len(filas)}, cubren {100 * tot / (W * H):.0f} % de la imagen)")

if a.salida:
    json.dump(dict(dE_medio=round(dEm, 2), regiones=filas), open(a.salida + ".json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    err = np.linalg.norm(cv2.GaussianBlur(fL, (0, 0), 3) - cv2.GaussianBlur(rL, (0, 0), 3), axis=2)
    mapa = cv2.applyColorMap(np.clip(err * 255 / 40, 0, 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
    for f in filas[:8]:
        msk = regiones[f["region"]][0].astype(np.uint8)
        cs, _ = cv2.findContours(msk, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        col = (0, 255, 255) if f["dos_colores"] else (255, 255, 255)
        cv2.drawContours(mapa, cs, -1, col, 1)
        ys, xs = np.nonzero(msk)
        cv2.putText(mapa, f"{f['dE']:.0f}", (int(xs.mean()) - 8, int(ys.mean())), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1)
    cv2.imwrite(a.salida + ".jpg", np.hstack([fot, ren, mapa]), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f"-> {a.salida}.json / .jpg  (PRIVADOS: llevan la foto real)")
