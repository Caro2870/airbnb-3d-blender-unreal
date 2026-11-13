"""Cut the A/B finish video: title card, room shot with a wipe A -> B, kitchen shot with a wipe A -> B, end card.
Runs ON THE RTX (numpy, Pillow, imageio-ffmpeg in the openhouse venv) over remoto/video_ab.ps1 output:
<dir>/<ficha>/frames/<toma>/f_####.png.  Nothing is copied to the laptop.

    python remoto/montar_ab.py <dir> <salida.mp4> [--fps 24] [--wipe 33-63]

Ficha A is rendered for frames 1..end of the wipe and ficha B from the start of the wipe to the end of the shot,
so only the overlap is rendered twice.
"""
import argparse
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("dir"); ap.add_argument("salida")
ap.add_argument("--fps", type=int, default=24); ap.add_argument("--wipe", default="33-63")
a = ap.parse_args()
W0, W1 = map(int, a.wipe.split("-"))

TOMAS = [
    ("ab_cuarto", "PISO", ("Madera Fashion Cerezo Beige 60×60", "110015675"), ("Concreto Gris 60×60", "110012936")),
    ("ab_cocina", "PARED DE COCINA", ("Tropic New II White 30×60", "110017507"), ("Brick New Black 30×60", "110017429")),
]
FONT = r"C:\Windows\Fonts\segoeui.ttf"
BOLD = r"C:\Windows\Fonts\seguisb.ttf" if os.path.exists(r"C:\Windows\Fonts\seguisb.ttf") else r"C:\Windows\Fonts\segoeuib.ttf"
MONO = r"C:\Windows\Fonts\consola.ttf"
GOLD, WHITE, MUTED = (232, 178, 92), (240, 236, 228), (170, 176, 172)


def font(p, s):
    return ImageFont.truetype(p, s)


def frame(toma, ficha, f):
    p = os.path.join(a.dir, ficha, "frames", toma, f"f_{f:04d}.png")
    return Image.open(p).convert("RGB")


def frames_of(toma):
    d = os.path.join(a.dir, "ficha_b", "frames", toma)
    return max(int(n[2:6]) for n in os.listdir(d) if n.startswith("f_"))


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def pill(img, xy, titulo, linea1, codigo, alpha):
    """Bottom label: FICHA X / product / code, on a dark translucent card."""
    if alpha <= 0:
        return img
    W, H = img.size
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    f1, f2, f3 = font(BOLD, 22), font(FONT, 26), font(MONO, 22)
    x, y = xy
    w = max(d.textlength(titulo, font=f1), d.textlength(linea1, font=f2), d.textlength("código " + codigo, font=f3)) + 40
    d.rounded_rectangle((x, y, x + w, y + 120), 14, fill=(10, 14, 16, int(190 * alpha)))
    d.text((x + 20, y + 12), titulo, font=f1, fill=GOLD + (int(255 * alpha),))
    d.text((x + 20, y + 42), linea1, font=f2, fill=WHITE + (int(255 * alpha),))
    d.text((x + 20, y + 80), "código " + codigo, font=f3, fill=MUTED + (int(255 * alpha),))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def wipe(A, B, t):
    """B revealed left -> right behind a soft, slightly slanted edge with a thin light line."""
    W, H = A.size
    if t <= 0:
        return A
    if t >= 1:
        return B
    x = np.arange(W)[None, :] - (np.arange(H)[:, None] - H / 2) * 0.12      # slanted edge
    edge = -60 + t * (W + 120)
    m = np.clip((edge - x) / 30.0 + 0.5, 0, 1)[..., None]
    out = np.asarray(B, np.float32) * m + np.asarray(A, np.float32) * (1 - m)
    line = np.exp(-((x - edge) / 2.5) ** 2)[..., None] * 160
    return Image.fromarray(np.clip(out + line, 0, 255).astype(np.uint8))


def card(size, lineas, n):
    W, H = size
    out = []
    for i in range(n):
        al = min(1.0, i / 10, (n - 1 - i) / 10)
        img = Image.new("RGB", size, (13, 18, 20)); d = ImageDraw.Draw(img)
        y = H / 2 - sum(s for _, s, _, _ in lineas) * 0.75
        for txt, s, col, fp in lineas:
            f = font(fp, s); w = d.textlength(txt, font=f)
            d.text(((W - w) / 2, y), txt, font=f, fill=tuple(int(c * al) for c in col))
            y += s * 1.5
        out.append(img)
    return out


def main():
    seq = []
    size = frame(TOMAS[0][0], "ficha_a", 1).size
    seq += card(size, [("Cambiar un acabado", 64, WHITE, BOLD), ("es cambiar un código", 64, GOLD, BOLD),
                       ("Mismo departamento · ficha A → ficha B", 28, MUTED, FONT)], 2 * a.fps)
    for toma, que, fa, fb in TOMAS:
        n = frames_of(toma)
        for f in range(1, n + 1):
            A = frame(toma, "ficha_a", f) if f <= W1 else None
            B = frame(toma, "ficha_b", f) if f >= W0 else None
            t = ease((f - W0) / max(1, W1 - W0))
            img = wipe(A, B, t) if A is not None and B is not None else (A if A is not None else B)
            # A's card fades as the wipe starts, B's appears as it ends
            img = pill(img, (36, size[1] - 156), f"FICHA A · {que}", *fa, alpha=1 - ease((f - W0 + 6) / 10))
            img = pill(img, (36, size[1] - 156), f"FICHA B · {que}", *fb, alpha=ease((f - W1 + 4) / 10))
            if f <= 8:                                   # short fade in from the dark cards
                img = Image.blend(Image.new("RGB", size, (13, 18, 20)), img, f / 8)
            if f > n - 8:
                img = Image.blend(Image.new("RGB", size, (13, 18, 20)), img, (n - f) / 8)
            seq.append(img)
    seq += card(size, [("La ficha del proyecto son dos líneas", 44, WHITE, BOLD),
                       ('{"piso": "110012936", "cocina_pared": "110017429"}', 30, GOLD, MONO),
                       ("Se cambia el código y se vuelve a renderizar. El modelo no se toca.", 28, MUTED, FONT)],
                int(2.5 * a.fps))
    import imageio_ffmpeg
    W, H = size
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(a.fps), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", a.salida]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for img in seq:
        pr.stdin.write(np.asarray(img, np.uint8).tobytes())
    pr.stdin.close(); pr.wait()
    print(f"{a.salida}: {len(seq)} cuadros, {len(seq) / a.fps:.1f} s")


if __name__ == "__main__":
    main()
