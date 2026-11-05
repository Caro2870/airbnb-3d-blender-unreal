import sys, pathlib
from PIL import Image
src = sorted(pathlib.Path(sys.argv[1]).glob("*.jpg"))
th = [Image.open(f) for f in src]
for t in th: t.thumbnail((360, 640))
sheet = Image.new("RGB", (360*4, 640*2), "white")
for i, t in enumerate(th): sheet.paste(t, ((i%4)*360, (i//4)*640))
sheet.save(sys.argv[2], quality=80)
