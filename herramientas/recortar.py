import sys, pathlib
from PIL import Image
src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
crops = {  # name: (photo, left, top, right, bottom) in full-resolution pixels
    "cama":          ("foto05", 0, 1750, 2268, 3800),
    "silla_oficina": ("foto05", 230, 1900, 1100, 2900),
    "mesita":        ("foto05", 1900, 2150, 2268, 2750),
    "silla_balcon":  ("foto03", 340, 2250, 980, 3400),
}
ims = []
for n, (p, *box) in crops.items():
    im = Image.open(src / f"{p}.jpg").crop(box); im.save(out / f"{n}.png"); t = im.copy(); t.thumbnail((400, 400)); ims.append(t)
sh = Image.new("RGB", (1600, 400), "white")
for i, t in enumerate(ims): sh.paste(t, (i * 400, 0))
sh.save(out / "recortes.jpg", quality=85)
