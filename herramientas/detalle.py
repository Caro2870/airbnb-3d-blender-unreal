import sys, pathlib
from PIL import Image
src = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2])
for grp, names in {"a": ["foto01","foto03","foto05"], "b": ["foto04","foto06","foto07"]}.items():
    ims = [Image.open(src / f"{n}.jpg") for n in names]
    for im in ims: im.thumbnail((620, 1100))
    W = sum(i.width for i in ims); H = max(i.height for i in ims)
    sh = Image.new("RGB", (W, H), "white"); x = 0
    for im in ims: sh.paste(im, (x, 0)); x += im.width
    sh.save(out / f"detalle_{grp}.jpg", quality=85)
