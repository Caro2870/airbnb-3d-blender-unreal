import sys, pathlib
from PIL import Image
fotos, rend, out = map(pathlib.Path, sys.argv[1:4])
pairs = [('cuarto',1),('mesa',2),('balcon',3),('cocina',4),('cabecero',5),('bano',6),('pasillo',7)]
cols = []
for cam, n in pairs:
    a = Image.open(fotos / f"foto{n:02d}.jpg").convert("RGB"); b = Image.open(rend / f"{cam}.png").convert("RGB")
    for im in (a, b): im.thumbnail((260, 470))
    c = Image.new("RGB", (260, 940), "white"); c.paste(a, (0, 0)); c.paste(b, (0, 470)); cols.append(c)
sh = Image.new("RGB", (260 * len(cols), 940), "white")
for i, c in enumerate(cols): sh.paste(c, (i * 260, 0))
sh.save(out, quality=85)
