import sys, pathlib
from PIL import Image
src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
for n in ("cama", "silla_balcon", "silla_oficina"):
    im = Image.open(src / f"{n}_cutout.png").convert("RGBA")
    bb = im.getchannel("A").point(lambda a: 255 if a > 128 else 0).getbbox()
    im.crop(bb).save(dst / f"{n}_tex.png")
    print(n, bb)
