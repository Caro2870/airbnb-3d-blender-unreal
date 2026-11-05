import os
"""Download the furniture check renders from the RTX and tile them next to the matching listing photos.
    python comparar_muebles.py [output name]"""
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

R = os.path.join(os.environ["USERPROFILE"], "Desktop", "recorrido-3d")
PAIRS = [("foto05", "cabecero"), ("foto01", "cuarto"), ("foto03", "balcon"), ("foto02", "mesa")]
out = sys.argv[1] if len(sys.argv) > 1 else "comparacion_muebles"
if len(sys.argv) > 2 and sys.argv[2] == "todas":     # every listing photo against its matched camera
    PAIRS += [("foto04", "cocina"), ("foto06", "bano"), ("foto07", "pasillo")]
for _, cam in PAIRS:
    subprocess.run([r"C:\Windows\System32\OpenSSH\scp.exe", "-q",
                    f"rtx:recorrido-3d/openhouse-3d/houses/apartaestudio/output/renders/{cam}.png",
                    rf"{R}\renders\muebles_{cam}.png"], check=True)
try:
    font = ImageFont.truetype("arialbd.ttf", 34)
except OSError:
    font = None
cols = []
for ph, cam in PAIRS:
    a = Image.open(rf"{R}\fotos\jpg\{ph}.jpg").convert("RGB")
    b = Image.open(rf"{R}\renders\muebles_{cam}.png").convert("RGB")
    H = 900
    a = a.resize((int(a.width * H / a.height), H)); b = b.resize((int(b.width * H / b.height), H))
    c = Image.new("RGB", (a.width + b.width + 10, H + 50), "white")
    c.paste(a, (0, 50)); c.paste(b, (a.width + 10, 50))
    d = ImageDraw.Draw(c)
    d.text((10, 8), "FOTO REAL", fill="black", font=font); d.text((a.width + 20, 8), "MODELO 3D", fill="black", font=font)
    cols.append(c)
Wc = max(c.width for c in cols)
s = Image.new("RGB", (Wc * 2 + 20, (cols[0].height + 20) * ((len(cols) + 1) // 2)), "white")
for i, c in enumerate(cols):
    s.paste(c, ((i % 2) * (Wc + 20), (i // 2) * (c.height + 20)))
s.save(rf"{R}\renders\{out}.jpg", quality=88)
print(rf"{R}\renders\{out}.jpg")
