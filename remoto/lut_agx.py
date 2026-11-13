"""Saca la curva de tono EXACTA del render (AgX + look de la escena) como tabla 3D, una sola vez.  Sin GPU, por ssh.

    blender -b apartaestudio.blend --python lut_agx.py -- <salida.png>
Escribe una imagen de 33x33x33 colores lineales (0 y 2^-13 .. 2^6 por canal) pasada por la gestión de color de la
escena con exposición 0.  remoto/ajustar_luz.py la interpola (trilineal en log2) para predecir el PNG final desde
la suma lineal de luces; la tabla por canal que usaba antes sobrestimaba los blancos (AgX mezcla canales).
"""
import sys

import bpy
import numpy as np

out = sys.argv[sys.argv.index("--") + 1]
N = 33
v = np.concatenate([[0.0], 2.0 ** np.linspace(-13, 6, N - 1)]).astype(np.float32)
r, g, b = np.meshgrid(v, v, v, indexing="ij")                    # px[x = r + N*g, y = b]
px = np.zeros((N, N * N, 4), np.float32)                         # filas = b, columnas = g*N + r
for ib in range(N):
    for ig in range(N):
        px[ib, ig * N:(ig + 1) * N, 0] = v; px[ib, ig * N:(ig + 1) * N, 1] = v[ig]; px[ib, ig * N:(ig + 1) * N, 2] = v[ib]
px[..., 3] = 1.0
im = bpy.data.images.new("lut_lineal", N * N, N, float_buffer=True, is_data=False)
im.colorspace_settings.name = bpy.context.scene.display_settings.id_data.sequencer_colorspace_settings.name if False else im.colorspace_settings.name
im.pixels.foreach_set(px.ravel())
S = bpy.context.scene
S.view_settings.exposure = 0.0
S.render.image_settings.file_format = 'PNG'; S.render.image_settings.color_depth = '16'; S.render.image_settings.color_mode = 'RGB'
im.save_render(out, scene=S)
print(f"[lut] {S.view_settings.view_transform} / {S.view_settings.look}, espacio de la imagen {im.colorspace_settings.name} -> {out}")
