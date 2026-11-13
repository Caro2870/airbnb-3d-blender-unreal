"""Imperfection pass, run last: what makes the pro scenes read as photos and ours as a catalogue (REGLAS_ARCHVIZ.md).

- fabrics: soft random wrinkles (subdivide + two noise displacements along the normal) on bedding, pillows, throws
- hard surfaces: a 2-3 mm bevel on every edge sharper than 30 deg (nothing real has a perfect 90-degree arista)
- materials: roughness varies across each surface (wear, fingerprints), +-15% around its value
- props: placed "by hand": a few degrees of yaw and a centimetre of drift on cushions, pillows, plants and decor

IMPERF=0 skips the whole pass (for before/after comparisons); IMPERF=<float> scales the wrinkle strength.
"""
import math
import os
import random

import bpy

STRENGTH = float(os.environ.get("IMPERF", "1"))
FABRIC = ("Cama_Colcha", "Cama_Camino", "Cama_Almohada", "Cama_Cojin", "Cama_Colchon", "Cama_Toalla", "Sofa_Cama",
          "Sofa_Cojin", "Sofa_Almohadon", "Sofa_Manta", "Cortina", "Tapete", "Toalla", "Bano_Toalla")
LOOSE = ("Almohada", "Cojin", "Almohadon", "Planta", "Jarron", "Libro", "Vaso", "Taza", "Decor", "Farol", "Prop_")
SKIP_BEVEL = ("Ground", "Sea", "Seafront", "Street", "Parking", "Lineas", "Polvo", "Aire", "Fab_", "Vidrio", "Glass")


def _tex(name, scale, depth):
    t = bpy.data.textures.get(name) or bpy.data.textures.new(name, 'CLOUDS')
    t.noise_scale = scale
    t.noise_depth = depth
    t.noise_basis = 'ORIGINAL_PERLIN'
    return t


def _wrinkle(ob, rng):
    """Two octaves of displacement: broad soft undulation + finer creases; strength in metres."""
    if not any(m.type == 'SUBSURF' for m in ob.modifiers) and len(ob.data.vertices) < 20000:
        sd = ob.modifiers.new("Imp_Sub", 'SUBSURF')
        sd.levels = sd.render_levels = 1
    # the real folds now come from the cloth simulation (muebles._drape / _inflate); this only adds a fine texture
    # of small creases on top (random displacement alone cannot make believable folds)
    for name, scale, depth, amount in (("Imp_Ondas", 0.18, 1, 0.006), ("Imp_Pliegues", 0.045, 2, 0.003)):
        d = ob.modifiers.new(name, 'DISPLACE')
        d.texture = _tex(name, scale, depth)
        d.texture_coords = 'OBJECT'
        d.direction = 'NORMAL'
        d.mid_level = 0.5
        d.strength = amount * STRENGTH * rng.uniform(0.8, 1.2)


def _bevel(ob):
    b = ob.modifiers.new("Imp_Bisel", 'BEVEL')
    b.width = 0.0025
    b.segments = 2
    b.limit_method = 'ANGLE'
    b.angle_limit = math.radians(30)
    b.harden_normals = False


def _rough_variation(mat):
    """Roughness r becomes r * (0.85..1.15) driven by a world-space noise: uneven wear instead of a uniform sheen."""
    if not mat.use_nodes or mat.get("imp_rough"):
        return
    nt = mat.node_tree
    for b in [n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"]:
        inp = b.inputs["Roughness"]
        if inp.is_linked:
            continue
        r = inp.default_value
        if r < 0.06 or b.inputs["Transmission Weight"].default_value > 0.5:   # glass, mirrors: keep them clean
            continue
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 3.5
        nz.inputs["Detail"].default_value = 6.0
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = r * 0.85
        mr.inputs["To Max"].default_value = min(1.0, r * 1.15)
        nt.links.new(mr.inputs["Value"], nz.outputs["Fac"])
        nt.links.new(inp, mr.outputs["Result"])
    mat["imp_rough"] = True


# ---------------------------------------------------------------- measured variation (photo 5)
# remoto/textura_objetos.py measures, per object and per detail size, how much the photo varies (robust, relative
# to the object's mean lightness, camera noise taken from the flat ceiling and removed) and how much the render does.
# What is missing is synthesised as band-limited noise on the base colour: one noise octave per measured band,
# wavelength = that band's size on the object, amplitude = the missing variation.  Nothing here is eyeballed.
BANDAS_M = (0.008, 0.016, 0.032, 0.064)      # ~2, 4, 8, 16 px of photo 5 at 2-3 m (3.5-5 mm per px at 1080 wide)
RUIDO_STD = 0.10                              # std of a Blender noise octave (Fac, detail 0); trimmed by GAN below
# object-name prefix -> missing variation per band, as a fraction of REFLECTANCE (= 3 x the L* fraction measured)
MEDIDO = {
    "Floor":         (0.022, 0.014, 0.012, 0.014),
    "Plane.016":     (0.023, 0.020, 0.026, 0.045),    # white quilted duvet
    "Cushions_Blue": (0.100, 0.094, 0.100, 0.100),
    "Cama_Toalla":   (0.055, 0.078, 0.100, 0.100),
}
# closed loop: after rendering, textura_objetos.py gives achieved/target per band; multiply the gain by its inverse
# LESSON (pass 2): matching the band energies with isotropic noise in every band made the numbers agree and the
# image wrong: duvet, cushions and towel looked water-stained.  The statistic says HOW MUCH, not WHAT SHAPE; in the
# photo the mid-size variation of fabrics is directional (stitch lines, folds: anisotropy 0.3-0.6 in
# textura_objetos.py).  So: fabrics get only the fine grain here (heather / terry, reads as cloth); their mid bands
# must come from relief (biblioteca._quilting, folds).  Only the tile floor keeps a little mid-size mottle.
GAN = {
    "Floor":         (1.6, 0.5, 0.5, 0.7),
    "Plane.016":     (1.2, 0.3, 0.0, 0.0),
    # pass 3: at 1.6 the cushions read as granite.  Their variation in the photo is directional (0.4-0.6): it is
    # folds and shading of the filled shape, which noise cannot give; only a faint heather stays.
    "Cushions_Blue": (0.5, 0.15, 0.0, 0.0),
    "Cama_Toalla":   (0.8, 0.3, 0.0, 0.0),
}
GAN_ENV = os.environ.get("IMPERF_MEDIDA", "1")


def _variacion(mat, amps, seed):
    """Base colour x (1 + sum_i  a_i / RUIDO_STD * (noise_i - 0.5)), noise_i of wavelength BANDAS_M[i] in world space."""
    if mat is None or not mat.use_nodes or mat.get("imp_var"):
        return False
    nt = mat.node_tree
    b = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if b is None:
        return False
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    acc = None
    for i, (lam, a) in enumerate(zip(BANDAS_M, amps)):
        if a <= 0:
            continue
        nz = nt.nodes.new("ShaderNodeTexNoise"); nz.noise_dimensions = '4D'
        nz.inputs["Scale"].default_value = 1.0 / lam; nz.inputs["Detail"].default_value = 0.0
        nz.inputs["W"].default_value = seed * 7.3 + i * 1.7
        nt.links.new(nz.inputs["Vector"], geo.outputs["Position"])
        m = nt.nodes.new("ShaderNodeMath"); m.operation = 'MULTIPLY_ADD'; m.use_clamp = False
        k = a / RUIDO_STD
        m.inputs[1].default_value = k; m.inputs[2].default_value = -0.5 * k
        nt.links.new(m.inputs[0], nz.outputs["Fac"] if "Fac" in nz.outputs else nz.outputs[0])
        if acc is None:
            acc = m.outputs["Value"]
        else:
            ad = nt.nodes.new("ShaderNodeMath"); ad.operation = 'ADD'; ad.use_clamp = False
            nt.links.new(ad.inputs[0], acc); nt.links.new(ad.inputs[1], m.outputs["Value"]); acc = ad.outputs["Value"]
    if acc is None:
        return False
    one = nt.nodes.new("ShaderNodeMath"); one.operation = 'ADD'; one.inputs[1].default_value = 1.0
    nt.links.new(one.inputs[0], acc)
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.clamp_result = False
    mx.inputs["Factor"].default_value = 1.0
    col = b.inputs["Base Color"]
    if col.is_linked:
        nt.links.new(mx.inputs["A"], col.links[0].from_socket)
    else:
        mx.inputs["A"].default_value = tuple(col.default_value)
    nt.links.new(mx.inputs["B"], one.outputs["Value"])
    nt.links.new(col, mx.outputs["Result"])
    mat["imp_var"] = True
    return True


def variacion_medida():
    """Called by biblioteca.build once the library objects exist (and by build() when the library is off)."""
    if GAN_ENV == "0" or STRENGTH <= 0:
        return
    n = 0
    for ob in bpy.data.objects:
        if ob.type != 'MESH':
            continue
        key = next((k for k in MEDIDO if ob.name.startswith(k)), None)
        if key is None:
            continue
        amps = [a * g * float(GAN_ENV) for a, g in zip(MEDIDO[key], GAN[key])]
        for i, slot in enumerate(ob.material_slots):
            n += bool(_variacion(slot.material, amps, seed=sum(map(ord, key)) % 97))
    print(f"[imperfecciones] variación medida en {n} materiales")


def build(M):
    if STRENGTH <= 0:
        print("[imperfecciones] off")
        return
    rng = random.Random(202)
    n = dict(telas=0, bisel=0, mats=0, sueltos=0)
    for ob in list(bpy.data.objects):
        if ob.type != 'MESH':
            continue
        name = ob.name
        if name.startswith(FABRIC):
            _wrinkle(ob, rng); n['telas'] += 1
        elif not name.startswith(SKIP_BEVEL) and not any(m.type == 'BEVEL' for m in ob.modifiers):
            _bevel(ob); n['bisel'] += 1
        if any(k in name for k in LOOSE):
            # turn about the object's own centre: most coded objects have their origin at the world origin, and a
            # 4 deg turn about it moved the sofa bolster 40 cm into the wall (found by remoto/validar.py)
            from mathutils import Matrix, Vector
            c = ob.matrix_world @ (sum((Vector(v) for v in ob.bound_box), Vector()) / 8)
            R = Matrix.Rotation(math.radians(rng.uniform(-4, 4)), 4, 'Z')
            ob.matrix_world = Matrix.Translation(c) @ R @ Matrix.Translation(-c) @ ob.matrix_world
            ob.location.x += rng.uniform(-0.01, 0.01)
            ob.location.y += rng.uniform(-0.01, 0.01)
            n['sueltos'] += 1
    for mat in bpy.data.materials:
        _rough_variation(mat); n['mats'] += 1
    print("[imperfecciones]", n)
    if os.environ.get("BIBLIO", "1") == "0":
        variacion_medida()
