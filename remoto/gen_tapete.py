"""Textura del tapete como en las fotos 1 y 5 (hecha con código, sin fotos reales: se puede publicar).

    python remoto/gen_tapete.py <salida.jpg>
Fondo beige tostado y 9 franjas atravesadas, simétricas:  rombos | punteada | zigzag triple | punteada | rombitos |
punteada | zigzag triple | punteada | rombos.  La versión anterior (crema, 7 líneas a lo largo) daba dE 44 contra la
foto 1 (remoto/color_objetos.py): el diseño real tiene mucho más azul oscuro y el fondo es más tostado.
"""
import sys

import numpy as np
from PIL import Image, ImageDraw

W, H = 700, 1200
FONDO, AZUL, GRIS = (200, 186, 156), (22, 26, 50), (96, 104, 118)
im = Image.new("RGB", (W, H), FONDO); d = ImageDraw.Draw(im)


def zig(yc, amp, per, w, fase=0.0, col=AZUL):
    pts = [(x, yc + amp * (1 - 4 * abs(((x / per + fase) % 1) - 0.5))) for x in range(-per, W + per, per // 4)]
    d.line(pts, fill=col, width=w, joint="curve")


def rombos(yc, alto=46, per=88, w=17):          # cadena de rombos = dos zigzag en contrafase
    zig(yc, alto, per, w, 0.0); zig(yc, alto, per, w, 0.5)


def punteada(yc, lado=20):                      # dos filas de cuadritos azul / gris alternados
    for k, y in enumerate((yc - lado, yc + 3)):
        for i, x in enumerate(range(8 + k * lado, W, int(lado * 2.2))):
            d.rectangle([x, y, x + lado, y + lado - 3], fill=AZUL if (i + k) % 3 else GRIS)


def zigzag3(yc):
    for dy in (-27, 0, 27):
        zig(yc + dy, 15, 48, 12)


def rombitos(yc):                               # celosía de rombos chicos con punto al centro
    zig(yc, 28, 52, 9, 0.0); zig(yc, 28, 52, 9, 0.5)
    for x in range(13, W, 52):
        d.rectangle([x - 4, yc - 4, x + 4, yc + 4], fill=AZUL)


ys = np.linspace(95, H - 95, 9)
for y, f in zip(ys, (rombos, punteada, zigzag3, punteada, rombitos, punteada, zigzag3, punteada, rombos)):
    f(int(y))
a = np.asarray(im).astype(np.float32)           # trama del tejido: ruido fino + hilos a lo ancho
rng = np.random.default_rng(3)
a += rng.normal(0, 5, (H, W, 1)) + 4 * np.sin(np.arange(H) * 2.1)[:, None, None]
Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(sys.argv[1], quality=92)
