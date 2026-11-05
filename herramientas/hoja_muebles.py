import sys, pathlib
from PIL import Image
d = pathlib.Path(sys.argv[1]); names = ["cama", "mesita", "silla_balcon", "silla_oficina"]
sh = Image.new("RGB", (4 * 360, 720), "white")
for i, n in enumerate(names):
    a = Image.open(d / f"{n}_cutout.png").convert("RGBA"); bg = Image.new("RGBA", a.size, "white"); bg.alpha_composite(a); a = bg.convert("RGB")
    b = Image.open(d / f"{n}_preview.png").convert("RGB")
    for im in (a, b): im.thumbnail((360, 360))
    sh.paste(a, (i * 360, 0)); sh.paste(b, (i * 360, 360))
sh.save(d / "muebles_preview.jpg", quality=85)
