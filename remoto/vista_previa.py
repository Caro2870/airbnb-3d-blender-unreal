"""Small JPG contact sheet of images on the RTX, to look at from the laptop without copying full frames.

    python vista_previa.py <salida.jpg> <cols> <img1> [<img2> ...]   (each tile 800 px wide)
"""
import sys

from PIL import Image

out, cols, paths = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
ims = [Image.open(p).convert("RGB") for p in paths]
tw = 800
ims = [im.resize((tw, round(tw * im.height / im.width))) for im in ims]
th = max(im.height for im in ims)
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tw + (cols - 1) * 6, rows * th + (rows - 1) * 6))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * (tw + 6), (i // cols) * (th + 6)))
sheet.save(out, quality=85)
print(out, sheet.size)
