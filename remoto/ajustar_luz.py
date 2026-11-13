"""Ajusta la MEZCLA DE LUCES de una cámara contra su foto, sin tanteo.  PC local (numpy + OpenCV + scipy).

    python remoto/ajustar_luz.py <foto.jpg> <luces_cam.npz> <mapa_cam.npz> <render_actual.png> [--salida base]

Entradas: los grupos de luz renderizados por separado (remoto/luces_separadas.py, lineales), el mapa de objetos y el
render actual (todas las luces a peso 1) para aprender la curva de tono del render (AgX + exposición).
Modelo:   lineal = suma_g  peso_g * tinte_g * I_g      ->  curva de tono (tabla por canal)  ->  comparar con la foto
Incógnitas: un peso por grupo (cada lámpara aparte si el npz las trae), tinte RGB del cielo y tinte común de focos.
Subir o bajar todos los pesos a la vez equivale a la exposición.  Mínimos cuadrados robustos (soft-L1) con cotas.
Medida: dE en CIELAB entre las medianas por objeto de la foto y del render sintetizado (L1, peso raíz del área), que
aguanta que algunos materiales estén mal.  Salida: pesos, dE antes/después y una vista previa sintetizada.
"""
import json
import sys

import cv2
import numpy as np
from scipy.optimize import minimize

foto_p, luces_p, mapa_p, ren_p = sys.argv[1:5]
salida = sys.argv[sys.argv.index("--salida") + 1] if "--salida" in sys.argv else None
L = np.load(luces_p)
NOMBRES = [str(g) for g in L["grupos"]] if "grupos" in L else ["cielo", "focos", "rellenos", "otros"]
NOMBRES = list(dict.fromkeys(NOMBRES))
G = {g: L[g].astype(np.float32) for g in NOMBRES}
H, W = G["cielo"].shape[:2]
ren = cv2.cvtColor(cv2.resize(cv2.imread(ren_p), (W, H)), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
fot = cv2.cvtColor(cv2.resize(cv2.imread(foto_p), (W, H), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
total = sum(G.values())      # el render actual = todos los grupos a peso 1 (¡debe ser SIN house.LUZ_FOTO!)

# curva de tono del render: tabla monótona por canal, lineal (suma de grupos) -> píxel del PNG actual
xs = np.concatenate([[0], np.geomspace(1e-3, 30, 60)])
tabla = []
for c in range(3):
    x, y = total[..., c].ravel(), ren[..., c].ravel()
    ys = [0.0]
    for a, b in zip(xs[:-1], xs[1:]):
        m = (x >= a) & (x < b)
        ys.append(float(np.median(y[m])) if m.sum() > 50 else np.nan)
    ys = np.array(ys[1:] + [np.nan]); ok = ~np.isnan(ys)
    yi = np.maximum.accumulate(np.interp(xs, xs[ok], ys[ok])); yi[0] = 0.0
    tabla.append(yi)


def tono_tabla(lin):
    return np.stack([np.interp(lin[..., c], xs, tabla[c]) for c in range(3)], -1)


# --lut <lut_agx.png> --exp <pasos>: curva de tono EXACTA de Blender (remoto/lut_agx.py), trilineal en log2
LUT = None
if "--lut" in sys.argv:
    from scipy.ndimage import map_coordinates
    _l = cv2.imread(sys.argv[sys.argv.index("--lut") + 1], cv2.IMREAD_UNCHANGED)[::-1, :, ::-1].astype(np.float32) / 65535
    NL = _l.shape[0]
    LUT = _l.reshape(NL, NL, NL, 3)                       # [b, g, r] -> rgb de pantalla
    EXP = 2.0 ** float(sys.argv[sys.argv.index("--exp") + 1]) if "--exp" in sys.argv else 1.0
    V1 = 2.0 ** -13


def tono(lin):
    if LUT is None:
        return tono_tabla(lin)
    x = np.asarray(lin, np.float64) * EXP
    i = np.where(x <= V1, np.maximum(x, 0) / V1, 1 + (np.log2(np.maximum(x, V1)) + 13) * (NL - 2) / 19)
    i = np.clip(i, 0, NL - 1)
    co = [i[..., 2].ravel(), i[..., 1].ravel(), i[..., 0].ravel()]
    return np.stack([map_coordinates(LUT[..., c], co, order=1) for c in range(3)], -1).reshape(x.shape).astype(np.float32)


def lab(rgb):
    return cv2.cvtColor(np.ascontiguousarray(rgb, np.float32).reshape(-1, 1, 3), cv2.COLOR_RGB2Lab).reshape(-1, 3)


print(f"curva de tono ({'tabla 3D de Blender' if LUT is not None else 'tabla por canal'}): error medio al re-sintetizar el render base = {np.abs(tono(total) - ren).mean() * 255:.1f} / 255")

m = np.load(mapa_p)
ids = cv2.resize(m["ids"], (W, H), interpolation=cv2.INTER_NEAREST)
ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
reg = []                                             # (nombre, peso, mediana foto Lab, medianas lineales por grupo)
for k, clave in enumerate(m["claves"]):
    er = cv2.erode((ids == k).astype(np.uint8), ker).astype(bool)
    if er.sum() < 250:
        continue
    reg.append((str(clave), np.sqrt(er.sum()), lab(np.median(fot[er], 0)[None])[0],
                {g: np.median(G[g][er], 0) for g in G}))
pesos = np.array([r[1] for r in reg]); pesos /= pesos.sum()
F = np.array([r[2] for r in reg])
M = {g: np.array([r[3][g] for r in reg]) for g in G}     # ojo: mediana de la suma ~ suma de medianas (regiones lisas)


# incógnitas: un peso por grupo (cada lámpara aparte), tinte RGB del cielo y tinte RGB común de los focos
ES_FOCO = np.array([g.startswith("foco") for g in NOMBRES])   # lámparas y sus difusores
N = len(NOMBRES); ic = NOMBRES.index("cielo")
MG = np.stack([M[g] for g in NOMBRES])                     # (grupo, región, 3)


FISICO = "--fisico" in sys.argv        # solo lo que existe en el cuarto real: sin rellenos, focos cálidos (~3000 K)
CALIDO = np.array([1.0, 0.72, 0.45])   # y UN balance de blancos de cámara para toda la imagen (p[N:N+3])
ES_RELL = np.array([g.startswith("rell") for g in NOMBRES])


def desarmar(p):
    w = np.asarray(p[:N], float)[:, None] * np.ones((N, 3))
    if FISICO:
        w[ES_RELL] = 0.0
        w[ES_FOCO] *= CALIDO
        return w * np.asarray(p[N:N + 3])[None, :]
    w[ic] *= p[N:N + 3]
    w[ES_FOCO] *= p[N + 3:N + 6]
    return w                                               # (grupo, 3): peso por canal


def sint(p):
    return np.einsum("gc,grc->rc", desarmar(p), MG)


# --curva: curva de la CÁMARA de la foto (procesado del teléfono), una gamma por canal en pantalla: y = x^g_c.
# Con g_azul > 1 los tonos medios (piso) pierden azul y los claros (paredes) casi no cambian: la foto 1 hace eso.
CURVA = "--curva" in sys.argv
NP = N + 9 if CURVA else N + 6


def pantalla(lin, p):
    t = tono(lin)
    return np.clip(t, 1e-4, 1) ** np.asarray(p[N + 6:N + 9]) if CURVA else t


def residuos(p):
    d = (lab(pantalla(sint(p), p)) - F) * np.sqrt(pesos)[:, None] * 10
    return np.concatenate([d.ravel(), 0.5 * np.log(np.maximum(p[N:], 1e-3))])   # tintes cerca de 1 salvo evidencia


from scipy.optimize import least_squares
p0 = np.ones(NP)
lo = np.concatenate([np.zeros(N), np.full(NP - N, 0.4)]); hi = np.concatenate([np.full(N, 12.0), np.full(NP - N, 2.5)])
mejor = None
rng = np.random.default_rng(0)
for k in range(8):
    ini = p0 if k == 0 else np.clip(p0 * np.exp(rng.normal(0, 0.8, NP)), lo + 1e-3, hi - 1e-3)
    r = least_squares(residuos, ini, bounds=(lo, hi), loss="soft_l1", f_scale=3.0, max_nfev=600, diff_step=0.03)  # paso grande: Lab va en float32
    if mejor is None or r.cost < mejor.cost:
        mejor = r
p = mejor.x


def dEm(q):
    return float((pesos * np.linalg.norm(lab(pantalla(sint(q), q)) - F, axis=1)).sum())


res = dict(pesos={g: round(float(p[i]), 3) for i, g in enumerate(NOMBRES)},
           tinte_cielo=[round(float(x), 3) for x in p[N:N + 3]], tinte_focos=[round(float(x), 3) for x in p[N + 3:N + 6]], curva=[round(float(x), 3) for x in p[N + 6:NP]],
           dE_antes=round(dEm(p0), 2), dE_despues=round(dEm(p), 2))
print(json.dumps(res, ensure_ascii=False, indent=1))
print("por objeto (dE antes -> después):")
d0 = np.linalg.norm(lab(pantalla(sint(p0), p0)) - F, axis=1); d1 = np.linalg.norm(lab(pantalla(sint(p), p)) - F, axis=1)
for i in np.argsort(-pesos)[:14]:
    print(f"  {reg[i][0][:40]:40s} {d0[i]:5.1f} -> {d1[i]:5.1f}")
if salida:
    json.dump(res, open(salida + ".json", "w", encoding="utf-8"), indent=1)
    lin = np.einsum("gc,ghwc->hwc", desarmar(p), np.stack([G[g] for g in NOMBRES]))
    pre = np.hstack([fot, ren, pantalla(lin, p)])
    cv2.imwrite(salida + ".jpg", cv2.cvtColor((np.clip(pre, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f"-> {salida}.json / .jpg  (foto | render actual | vista previa sintetizada; PRIVADO)")
