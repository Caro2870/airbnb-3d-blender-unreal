"""blender -b apartaestudio.blend --python inspeccion.py -- Name [Name ...]: print location, size, materials, images and
UVs of the named objects (debugging helper)."""
import sys

import bpy

for n in sys.argv[sys.argv.index("--") + 1:]:
    ob = bpy.data.objects.get(n)
    if ob is None:
        print("MISSING", n)
        continue
    me = ob.data
    print("OBJ", n, "loc", tuple(round(c, 3) for c in ob.location), "dims", tuple(round(c, 3) for c in ob.dimensions),
          "verts", [tuple(round(c, 3) for c in v.co) for v in me.vertices][:4])
    print("  normals", [tuple(round(c, 2) for c in p.normal) for p in me.polygons][:2])
    print("  uv", [tuple(round(c, 2) for c in d.uv) for d in me.uv_layers[0].data][:4] if me.uv_layers else None)
    for m in me.materials:
        imgs = [(nd.image.name, nd.image.filepath, tuple(nd.image.size)) for nd in m.node_tree.nodes
                if nd.type == 'TEX_IMAGE' and nd.image]
        print("  MAT", m.name, imgs)
