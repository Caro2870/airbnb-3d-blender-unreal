"""Contact sheet of chosen frames of an mp4 (runs on the RTX; ffmpeg from imageio-ffmpeg).

    python hoja_mp4.py <video.mp4> <salida.jpg> <n1,n2,...> [cols=3]
"""
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image

vid, out, frames = sys.argv[1], sys.argv[2], [int(v) for v in sys.argv[3].split(",")]
cols = int(sys.argv[4]) if len(sys.argv) > 4 else 3
ff = imageio_ffmpeg.get_ffmpeg_exe()
r = imageio_ffmpeg.read_frames(vid)
meta = next(r)
W, H = meta["size"]
want, tiles = set(frames), {}
for i, buf in enumerate(r):
    if i in want:
        tiles[i] = Image.fromarray(np.frombuffer(buf, np.uint8).reshape(H, W, 3)).resize((640, round(640 * H / W)))
    if i > max(frames):
        break
ims = [tiles[f] for f in frames if f in tiles]
th = ims[0].height
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 646 - 6, rows * (th + 6) - 6))
for k, im in enumerate(ims):
    sheet.paste(im, ((k % cols) * 646, (k // cols) * (th + 6)))
sheet.save(out, quality=85)
print(out, len(ims), "cuadros")
