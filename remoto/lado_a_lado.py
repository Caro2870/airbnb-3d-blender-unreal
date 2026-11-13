"""Side-by-side strip: photo | render v0 | render v1 ... at a common height, with labels.  PRIVATE output (real photo).

    python remoto/lado_a_lado.py <salida.jpg> <foto.jpg> <render1.png> [<render2.png> ...] [--alto 900]
          [--recorte x0,y0,x1,y1]   (fractions of the image, same crop for all; e.g. 0.3,0.4,0.9,0.8)
          [--etiquetas foto,v0,v1]
"""
import argparse

import cv2
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("salida"); ap.add_argument("imgs", nargs="+")
ap.add_argument("--alto", type=int, default=900); ap.add_argument("--recorte"); ap.add_argument("--etiquetas")
a = ap.parse_args()

ref = cv2.imread(a.imgs[1] if len(a.imgs) > 1 else a.imgs[0])
H, W = ref.shape[:2]
tiles = []
labels = a.etiquetas.split(",") if a.etiquetas else [""] * len(a.imgs)
for p, lab in zip(a.imgs, labels + [""] * len(a.imgs)):
    im = cv2.resize(cv2.imread(p), (W, H), interpolation=cv2.INTER_AREA)
    if a.recorte:
        x0, y0, x1, y1 = map(float, a.recorte.split(","))
        im = im[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)]
    h, w = im.shape[:2]
    im = cv2.resize(im, (round(w * a.alto / h), a.alto), interpolation=cv2.INTER_AREA)
    if lab:
        cv2.rectangle(im, (0, 0), (18 * len(lab) + 20, 44), (0, 0, 0), -1)
        cv2.putText(im, lab, (10, 32), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
    tiles.append(im)
    tiles.append(np.zeros((a.alto, 6, 3), np.uint8))
cv2.imwrite(a.salida, np.hstack(tiles[:-1]), [cv2.IMWRITE_JPEG_QUALITY, 88])
print(a.salida)
