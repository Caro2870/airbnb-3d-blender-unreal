"""Cinematic atmosphere: a faint participating medium inside the unit so the low sun draws visible beams through the
window, and dust motes that only read where a beam lights them.  Staging (photographic effect), not architecture."""
import random

import bpy

from .plan import *
from archviz.mesh import MB
from archviz import materials as _m

DENSITY = 0.012        # 1/m: enough for beams, little haze in the shadows
DUST = 2600


def build(M):
    vol = bpy.data.materials.new("Aire_Volumen"); vol.use_nodes = True
    nt = vol.node_tree; nt.nodes.clear()
    pv = nt.nodes.new("ShaderNodeVolumePrincipled")
    pv.inputs["Density"].default_value = DENSITY
    pv.inputs["Anisotropy"].default_value = 0.55
    pv.inputs["Color"].default_value = (1.0, 0.97, 0.92, 1)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(out.inputs["Volume"], pv.outputs["Volume"])
    v = MB(); v.box(0.01, W - 0.01, 0.01, Y_WIN - 0.01, Z0 + 0.005, ZC - 0.03)
    ob = v.build("Aire_Interior", [vol])
    ob.visible_shadow = False

    rng = random.Random(7)
    d = MB()
    for _ in range(DUST):
        c = (rng.uniform(0.3, W - 0.3), rng.uniform(2.6, Y_WIN - 0.2), Z0 + rng.uniform(0.3, H - 0.3))
        d.sphere(c, rng.uniform(0.0006, 0.0014), seg=5, rings=3, mi=0)
    dust = _m.new_mat("Polvo", (1.0, 0.95, 0.85, 1), rough=1.0, transmission=0.3)
    ob = d.build("Polvo", [dust])
    ob.visible_shadow = False
