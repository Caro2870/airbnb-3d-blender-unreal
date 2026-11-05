import sys, pathlib
from PIL import Image
root = pathlib.Path(sys.argv[1]); shots = ['entrada','cocina','habitacion','bano','balcon']
rows = []
for s in shots:
    fs = sorted((root / s).glob("f_*.png")); pick = [fs[0], fs[len(fs)//3], fs[2*len(fs)//3], fs[-1]]
    ims = [Image.open(f).convert("RGB") for f in pick]
    for im in ims: im.thumbnail((400, 225))
    r = Image.new("RGB", (1600, 225)); [r.paste(im, (i*400, 0)) for i, im in enumerate(ims)]; rows.append(r)
sh = Image.new("RGB", (1600, 225*len(rows))); [sh.paste(r, (0, i*225)) for i, r in enumerate(rows)]
sh.save(sys.argv[2], quality=85)
