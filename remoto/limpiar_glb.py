"""Remove the ground slab Hunyuan3D bakes under some objects and keep the furniture.

    python limpiar_glb.py <in.glb> <out.glb>

Works in the GLB's own frame (Y up).  Splits into connected parts and drops flat, wide parts lying at the bottom;
if the slab is fused to the object, cuts away faces whose vertices all sit in the bottom slab band.
"""
import sys

import numpy as np
import trimesh

src, dst = sys.argv[1:3]
m = trimesh.load(src, force='mesh')
ext = m.bounds[1] - m.bounds[0]
y0 = m.bounds[0][1]
parts = m.split(only_watertight=False)
keep = []
for p in parts:
    e = p.bounds[1] - p.bounds[0]
    flat_wide = e[1] < 0.06 * ext.max() and max(e[0], e[2]) > 0.6 * max(ext[0], ext[2]) and p.bounds[0][1] - y0 < 0.03
    if not flat_wide and len(p.faces) > 200:
        keep.append(p)
m2 = trimesh.util.concatenate(keep) if keep else m
# fused slab: drop faces entirely inside the bottom band if that band spans the whole footprint
band = y0 + 0.035 * ext[1] + 0.01
fy = m2.vertices[m2.faces][:, :, 1]
low = (fy < band).all(axis=1)
e2 = m2.bounds[1] - m2.bounds[0]
if low.any():
    lv = m2.vertices[m2.faces[low].ravel()]
    span = lv.max(axis=0) - lv.min(axis=0)
    if max(span[0], span[2]) > 0.9 * max(e2[0], e2[2]) and (e2[0] * e2[2]) > 0:
        m2.update_faces(~low)
        m2.remove_unreferenced_vertices()
m2.export(dst)
print(src, "parts", len(parts), "kept", len(keep), "faces", len(m2.faces), "size", np.round(m2.bounds[1] - m2.bounds[0], 2))
