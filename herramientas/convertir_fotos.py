import sys, pathlib
from PIL import Image, ImageOps
import pillow_heif
pillow_heif.register_heif_opener()
src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
for i, f in enumerate(sorted(src.iterdir()), 1):
    im = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
    out = dst / f"foto{i:02d}.jpg"
    im.save(out, quality=92)
    print(out.name, "<-", f.name, im.size)
