"""Furniture modelled to measure from the listing photos (replaces the Hunyuan3D shapes of generados.py, which came out
melted): the bed with draped bedding (cloth simulation), the balcony bistro set and the mesh office chair.

Bed (photos 1 and 5): oak frame on four straight legs, low cream upholstered headboard, white quilt with lengthwise
channel stitching hanging over the sides, palm-print runner across the foot third, two quilted white pillows, two pale
blue cushions, rolled and fan-folded towels.  Balcony (photo 3): two brown folding chairs with sling seats, round
brown-tinted glass table, white lantern.  Office chair (photo 5): black mesh back, flip-up arms, five-star base.
"""
import math
import os
import random

import bpy

from .plan import *
from .house import ASSETS
from archviz.mesh import MB
from archviz import materials as _m

REPLACES = ["Bed", "Cushions_Blue", "Balcony_Set", "Office_Chair"]
BED_L, BED_W = 1.95, 1.20       # semidoble: photo 5 legs 1.97 tiles apart (~1.16 m) and the desk beside it
HX = W - 0.1                     # head end of the bed (headboard on the east wall)
FX = HX - BED_L                  # foot end
MATT_Z0, MATT_Z1 = Z0 + 0.28, Z0 + 0.52
BAL_TABLE_X = W - 0.8


# ---------------------------------------------------------------- materials
def _quilt(name, base):
    """White cotton quilt: lengthwise stitched channels as a bump (baked to a normal map on export)."""
    m = _m.new_mat(name, base, rough=0.9, sheen=0.6)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wv = nt.nodes.new("ShaderNodeTexWave"); wv.wave_type = 'BANDS'; wv.bands_direction = 'Y'; wv.wave_profile = 'SIN'
    wv.inputs["Scale"].default_value = 18.0                       # ~3.5 cm between stitch lines
    nt.links.new(wv.inputs["Vector"], tc.outputs["Object"])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 300.0
    nt.links.new(nz.inputs["Vector"], tc.outputs["Object"])
    mix = nt.nodes.new("ShaderNodeMath"); mix.operation = 'MULTIPLY_ADD'; mix.inputs[1].default_value = 0.15
    nt.links.new(mix.inputs[0], nz.outputs["Fac"]); nt.links.new(mix.inputs[2], wv.outputs["Fac"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.45; bp.inputs["Distance"].default_value = 0.005
    nt.links.new(bp.inputs["Height"], mix.outputs["Value"]); nt.links.new(b.inputs["Normal"], bp.outputs["Normal"])
    return m


def _image_mat(name, path, rough=0.85, sheen=0.4):
    m = _m.new_mat(name, (1, 1, 1, 1), rough=rough, sheen=sheen)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = bpy.data.images.load(path, check_existing=True)
    nt.links.new(b.inputs["Base Color"], tx.outputs["Color"])
    return m


def _matte(m):
    """No specular highlight at all (photo paper behind a non-reflective glazing)."""
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    for k in ("Specular IOR Level", "Specular"):
        if b.inputs.get(k) is not None:
            b.inputs[k].default_value = 0.0
    return m


def _glow(m, strength):
    """Let an image material emit a little of its own colour: glazed prints on a wall in shade otherwise read as
    blank grey rectangles in renders."""
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tx = next(n for n in nt.nodes if n.type == 'TEX_IMAGE')
    nt.links.new(b.inputs["Emission Color"], tx.outputs["Color"])
    b.inputs["Emission Strength"].default_value = strength
    return m


def _lantern(name):
    """White ceramic lantern (photo 2): the pierced rosette pattern is the photo itself, wrapped around the barrel;
    the lit openings also glow a little."""
    m = _image_mat(name, os.path.join(ASSETS, "gen", "farol.jpg"), rough=0.3, sheen=0.0)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tx = next(n for n in nt.nodes if n.type == 'TEX_IMAGE')
    b.inputs["Emission Color"].default_value = (1.0, 0.75, 0.38, 1)
    sep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(sep.inputs[0], tx.outputs["Color"])
    glow = nt.nodes.new("ShaderNodeMath"); glow.operation = 'SUBTRACT'                 # yellow openings: R - B is high
    nt.links.new(glow.inputs[0], sep.outputs["Red"]); nt.links.new(glow.inputs[1], sep.outputs["Blue"])
    gs = nt.nodes.new("ShaderNodeMath"); gs.operation = 'MULTIPLY'; gs.inputs[1].default_value = 6.0
    nt.links.new(gs.inputs[0], glow.outputs["Value"])
    nt.links.new(b.inputs["Emission Strength"], gs.outputs["Value"])
    return m


def _lathe(name, profile, mat, seg=48, u_repeat=1):
    """Surface of revolution about Z from (height, radius) pairs, with a cylindrical UV wrap (u around, v up)."""
    h0, h1 = profile[0][0], profile[-1][0]
    vs, fs = [], []
    for h, r in profile:
        for i in range(seg + 1):                                  # duplicated seam column keeps the UVs continuous
            a = 2 * math.pi * i / seg
            vs.append((r * math.cos(a), r * math.sin(a), h))
    for k in range(len(profile) - 1):
        for i in range(seg):
            a, b = k * (seg + 1) + i, (k + 1) * (seg + 1) + i
            fs.append((a, a + 1, b + 1, b))
    me = bpy.data.meshes.new(name); me.from_pydata(vs, [], fs)
    uv = me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        vi = loop.vertex_index
        k, i = divmod(vi, seg + 1)
        uv.data[loop.index].uv = (u_repeat * i / seg, (profile[k][0] - h0) / (h1 - h0))
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.data.collections["House"].objects.link(ob)
    return ob


# With the library on (biblioteca.py), the coded quilt, runner, pillows and cushions are deleted right after being
# built (CAMA_QUITAR / SOFA_QUITAR).  Their cloth simulations were 38 of the 59 s of every build: skip them.
CON_BIBLIO = (os.environ.get("BIBLIO", "1") != "0"
              and os.path.isfile(os.path.join(ASSETS, "blenderkit", "biblioteca.blend")))


def _mats(M):
    return dict(
        quilt=_quilt("Colcha_Acolchada", (0.86, 0.86, 0.84, 1)),
        pillow=_quilt("Almohada_Acolchada", (0.90, 0.90, 0.88, 1)),
        sheet=_m.new_mat("Sabana_Blanca", (0.88, 0.88, 0.86, 1), rough=0.9, sheen=0.5),
        runner=_image_mat("Camino_Palmeras", os.path.join(ASSETS, "gen", "camino_azul.jpg")),
        rug=_image_mat("Tapete_Zigzag", os.path.join(ASSETS, "gen", "tapete.jpg"), rough=0.95, sheen=0.2),
        jute=_m.fabric("Fleco_Yute", (0.70, 0.62, 0.48, 1), weave=120.0),
        olive=_m.fabric("Cojin_Oliva", (0.13, 0.15, 0.09, 1)),
        throw=_m.fabric("Manta_Durazno", (0.86, 0.68, 0.50, 1), weave=90.0, bump=0.4),
        sofa=M['sofa'],
        bolster=_m.fabric("Cojin_Estampado", (0.48, 0.44, 0.32, 1), weave=40.0, bump=0.5),
        black_glass=_m.new_mat("Vidrio_Negro", (0.015, 0.015, 0.015, 1), rough=0.03, coat=1.0),
        towel=_m.fabric("Toalla_Crema", (0.80, 0.74, 0.62, 1), weave=180.0, bump=0.6, sheen=0.8),
        cushion=_m.fabric("Cojin_Azul_Acero", (0.30, 0.43, 0.56, 1)),
        white=_m.new_mat("Melamina_Blanca", (0.86, 0.86, 0.84, 1), rough=0.35),
        leaf=M['leaf_plant'],
        label=_m.new_mat("Etiqueta_Amarilla", (0.95, 0.80, 0.10, 1), rough=0.5),
        grey_top=_m.new_mat("Melamina_Gris", (0.42, 0.42, 0.41, 1), rough=0.4),
        steel=M['steel'], frame_black=_m.new_mat("Marco_Negro", (0.02, 0.02, 0.02, 1), rough=0.4),
        mat_board=_m.new_mat("Paspartu", (0.88, 0.88, 0.86, 1), rough=0.8),
        # matte prints: a glossy finish caught the white wall at the wide cameras' grazing angle and washed them grey
        prints={n: _glow(_matte(_image_mat(f"Cuadro_{n}", os.path.join(ASSETS, "gen", f"cuadro_{n}.jpg"), rough=0.9,
                                           sheen=0.0)), 0.25) for n in ("flor", "atardecer", "ciudad")},
        # smooth pale oak veneer (photo 5); the Poly Haven oak scan read as woven rattan at bed-rail scale
        oak=_m.wood("Roble_Cama", light=(0.74, 0.56, 0.38, 1), dark=(0.60, 0.44, 0.29, 1), grain_axis='X', rough=0.5),
        head=M['cabecero'],
        brown=_m.new_mat("Metal_Cafe_Mate", (0.07, 0.045, 0.035, 1), rough=0.45, metal=0.6),
        sling=_m.fabric("Malla_Cafe", (0.08, 0.05, 0.04, 1), weave=220.0, bump=0.5, sheen=0.2),
        glass_top=_m.new_mat("Vidrio_Cafe", (0.10, 0.06, 0.04, 1), rough=0.05, coat=1.0),
        lantern=_lantern("Farol_Calado"),
        ceramic_white=_m.new_mat("Ceramica_Blanca", (0.90, 0.90, 0.88, 1), rough=0.25),
        mesh=_m.fabric("Malla_Negra", (0.03, 0.03, 0.03, 1), weave=260.0, bump=0.8, sheen=0.1),
        black=M['black'], black_metal=M['black_metal'],
    )


# ---------------------------------------------------------------- cloth
def _grid(name, x0, x1, y0, y1, z, step, mat, tile=None):
    nx, ny = max(2, round((x1 - x0) / step)), max(2, round((y1 - y0) / step))
    vs = [(x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny, z) for j in range(ny + 1) for i in range(nx + 1)]
    fs = [(j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i)
          for j in range(ny) for i in range(nx)]
    me = bpy.data.meshes.new(name); me.from_pydata(vs, [], fs)
    uv = me.uv_layers.new(name="UVMap")
    tu, tv = tile or (x1 - x0, y1 - y0)
    for loop in me.loops:
        x, y, _ = vs[loop.vertex_index]
        uv.data[loop.index].uv = ((x - x0) / tu, (y - y0) / tv)
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.data.collections["House"].objects.link(ob)
    return ob


def _drape(ob, colliders, frames=48, bend=6.0, mass=0.4, thick=0.01, ripple=0.0, compression=25.0):
    """Drop the cloth onto the colliders, freeze the final shape, then give it thickness.
    ripple > 0 seeds the flat grid with a random up/down wave of that amplitude (m) before the drop, and a low
    `compression` lets the fabric buckle instead of staying a stiff sheet: that is what leaves folds on a bed."""
    S = bpy.context.scene
    if ripple > 0:
        rng = random.Random(len(ob.data.vertices))
        ph = [rng.uniform(0, 6.28) for _ in range(4)]
        for v in ob.data.vertices:
            x, y = v.co.x, v.co.y
            v.co.z += ripple * (0.6 * math.sin(x * 7.0 + ph[0]) * math.sin(y * 5.0 + ph[1])
                                + 0.4 * math.sin(x * 17.0 + y * 11.0 + ph[2]) + 0.25 * rng.uniform(-1, 1))
    for c in colliders:
        c.modifiers.new("_col", 'COLLISION')
        c.collision.thickness_outer = 0.004
        c.collision.cloth_friction = 8.0
    cl = ob.modifiers.new("_cloth", 'CLOTH')
    s = cl.settings
    s.quality = 8; s.mass = mass; s.air_damping = 2.0
    s.tension_stiffness = 25; s.compression_stiffness = compression; s.shear_stiffness = 10; s.bending_stiffness = bend
    cl.collision_settings.distance_min = 0.004
    cl.point_cache.frame_start = 1; cl.point_cache.frame_end = frames
    f0, f1 = S.frame_start, S.frame_end
    S.frame_start, S.frame_end = 1, frames
    for f in range(1, frames + 1):
        S.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    ob.modifiers.clear(); ob.data = me
    for c in colliders:
        c.modifiers.remove(c.modifiers["_col"])
    S.frame_start, S.frame_end = f0, f1
    S.frame_set(f0)
    so = ob.modifiers.new("thick", 'SOLIDIFY'); so.thickness = thick; so.offset = 1.0
    return ob


def _inflate(ob, colliders=(), frames=8, pressure=30.0, sub=2):
    """Pillow / cushion as a closed cloth bag inflated with pressure and no gravity, pressing on the colliders:
    edges pinch and the faces dimple like a real filled pillow. The box is subdivided first so it can crease."""
    S = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    sd = ob.modifiers.new("_sub", 'SUBSURF'); sd.levels = sd.render_levels = sub
    dg.update()
    ob.data = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    ob.modifiers.clear()
    for c in colliders:
        if "_col" not in c.modifiers:
            c.modifiers.new("_col", 'COLLISION')
        c.collision.thickness_outer = 0.003
    cl = ob.modifiers.new("_cloth", 'CLOTH')
    s = cl.settings
    # first try (shrink 6%, pressure 3-4, soft tension, colliders it started inside of) deflated the pillows into
    # crumpled bags and shoved them off the bed: now a taut cover, real pressure, a few frames, no colliders
    s.quality = 6; s.mass = 0.3; s.air_damping = 5.0
    # second try (pressure 10-12, bending 0.2) crumpled them like shirts: stiffer cover, higher pressure, so the
    # pillow stays full and only its seams and corners pinch
    s.tension_stiffness = 60; s.compression_stiffness = 20; s.shear_stiffness = 20; s.bending_stiffness = 1.5
    s.use_pressure = True; s.uniform_pressure_force = pressure
    s.effector_weights.gravity = 0.0
    cl.collision_settings.use_self_collision = True
    cl.point_cache.frame_start = 1; cl.point_cache.frame_end = frames
    f0, f1 = S.frame_start, S.frame_end
    S.frame_start, S.frame_end = 1, frames
    for f in range(1, frames + 1):
        S.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    ob.modifiers.clear(); ob.data = me
    for p in me.polygons:
        p.use_smooth = True
    for c in colliders:
        if "_col" in c.modifiers:
            c.modifiers.remove(c.modifiers["_col"])
    S.frame_start, S.frame_end = f0, f1
    S.frame_set(f0)
    return ob


def _top_z(ob, x, y, r=0.15):
    zs = [(ob.matrix_world @ v.co).z for v in ob.data.vertices
          if abs((ob.matrix_world @ v.co).x - x) < r and abs((ob.matrix_world @ v.co).y - y) < r]
    return max(zs) if zs else MATT_Z1


def _placed(mb, name, mats, loc, rot=(0, 0, 0), **kw):
    ob = mb.build(name, mats, **kw)
    ob.location = loc; ob.rotation_euler = rot
    return ob


# ---------------------------------------------------------------- bed
def bed(K):
    by, hw = BED_Y, BED_W / 2
    fr = MB()                                           # frame: four rails, slats, round tapered legs
    rz0, rz1 = Z0 + 0.13, MATT_Z0 + 0.05        # rails reach the library mattress bottom: no slats show (photo 5)
    fr.box(FX - 0.03, HX, by - hw - 0.03, by - hw, rz0, rz1)
    fr.box(FX - 0.03, HX, by + hw, by + hw + 0.03, rz0, rz1)
    fr.box(FX - 0.03, FX, by - hw, by + hw, rz0, rz1)
    fr.box(HX - 0.03, HX, by - hw, by + hw, rz0, rz1)
    for i in range(9):
        x = FX + 0.1 + i * (BED_L - 0.2) / 8
        fr.box(x - 0.04, x + 0.04, by - hw, by + hw, MATT_Z0 - 0.02, MATT_Z0)
    for lx in (FX + 0.05, HX - 0.05):
        for ly in (by - hw + 0.03, by + hw - 0.03):
            fr.cylinder(lx, ly, Z0, rz0, 0.026, 0.034, seg=20)          # chunky round tapered legs
    frame = fr.build("Cama_Base", [K['oak']], bevel=0.004)
    hb = MB(); hb.rbox(HX + 0.01, HX + 0.07, by - hw - 0.075, by + hw + 0.075, Z0 + 0.32, Z0 + 1.08, r=0.025, puff=0.15)
    hb_ob = hb.build("Cama_Cabecero", [K['head']], smooth=True)
    mt = MB(); mt.rbox(FX + 0.01, HX - 0.02, by - hw + 0.01, by + hw - 0.01, MATT_Z0, MATT_Z1, r=0.06, puff=0.12)
    matt = mt.build("Cama_Colchon", [K['sheet']], smooth=True)

    tz = MATT_Z1 + 0.06
    if CON_BIBLIO:
        return _towel_bow(K, FX + 0.55, by, tz)       # biblioteca._towel re-seats it on the library runner
    # pillows leaning on the headboard, then the blue cushions in front of them
    pil = []
    for dy in (-0.33, 0.33):
        p = MB(); p.rbox(-0.08, 0.08, -0.33, 0.33, -0.23, 0.23, r=0.07, puff=0.6)
        pil.append(_placed(p, "Cama_Almohada", [K['pillow']], (HX - 0.17, by + dy, MATT_Z1 + 0.2),
                           (0, math.radians(18), 0), smooth=True))     # top leans back onto the headboard
    cush = []
    for dy, yaw in ((-0.2, 8), (0.2, -10)):       # square 45 cm cushions with crisp piped edges (photo 5)
        c = MB(); c.rbox(-0.06, 0.06, -0.22, 0.22, -0.22, 0.22, r=0.025, puff=0.45)
        cush.append(_placed(c, "Cama_Cojin", [K['cushion']], (HX - 0.36, by + dy, MATT_Z1 + 0.19),
                            (0, math.radians(24), math.radians(yaw)), smooth=True))
    # filled-bag pillows pressing on the headboard and mattress (the rigid boxes read as foam blocks)
    for p in pil:
        _inflate(p)
    for c in cush:
        _inflate(c, pressure=25.0)

    # quilt from the foot to just below the pillows, hanging ~30 cm over the sides and foot
    # overhang ~18 cm: it covers the mattress side and stops on the oak rail, which stays visible (photo 5)
    # soft, low-compression cloth dropped with a seeded ripple: settles with folds instead of a flat board
    quilt = _grid("Cama_Colcha", FX - 0.14, HX - 0.52, by - hw - 0.15, by + hw + 0.15, MATT_Z1 + 0.08, 0.02, K['quilt'])
    _drape(quilt, [matt, frame], frames=70, bend=1.5, mass=0.5, ripple=0.03, compression=4.0)
    # runner across the foot third, draped over the quilt
    rx = FX + 0.55
    runner = _grid("Cama_Camino", rx - 0.26, rx + 0.26, by - hw - 0.3, by + hw + 0.3, MATT_Z1 + 0.15, 0.02, K['runner'],
                   tile=(0.26, 0.6))              # straight repeat of the photographed print, ~25 cm palms
    _drape(runner, [quilt, matt, frame], frames=60, bend=0.6, mass=0.2, thick=0.004, ripple=0.015, compression=3.0)

    # towel "bow" (photos 1 and 5): a rolled towel lying lengthwise on the middle of a second towel, which is
    # gathered under it and fans out to both sides in pleated wings (photo 5: big fan toward the window side)
    _towel_bow(K, rx, by, _top_z(runner, rx, by))


def _towel_bow(K, rx, by, tz):
    tw = MB()

    def sheet(P, nu, nv):                              # open quad grid surface from P(i, j)
        vs = [P(i, j) for i in range(nu + 1) for j in range(nv + 1)]
        fs = [(i * (nv + 1) + j, (i + 1) * (nv + 1) + j, (i + 1) * (nv + 1) + j + 1, i * (nv + 1) + j + 1)
              for i in range(nu) for j in range(nv)]
        tw._add(vs, fs, 0)

    cx = rx + 0.03
    for side, R, a, npl in ((-1, 0.30, math.radians(38), 4), (1, 0.22, math.radians(28), 3)):   # -y: right in photo 5
        def wing(i, j, side=side, R=R, a=a, npl=npl):
            s = 0.12 + 0.88 * i / 14
            ph = -a + 2 * a * j / 48
            lift = 0.05 * (1 - s) ** 2                 # gathered up into the roll at the centre
            pleat = 0.025 * s * 0.5 * (1 - math.cos(2 * math.pi * npl * (ph + a) / (2 * a)))
            return (cx + R * s * math.sin(ph), by + side * R * s * math.cos(ph), tz + 0.005 + lift + pleat)
        sheet(wing, 14, 48)
    # the roll: a real spiral (4 turns) so its ends show the rolled layers, as in the photo
    L, x0, zc, turns = 0.32, rx - 0.13, tz + 0.085, 4

    def roll(i, j):
        t = i / 10
        th = 2 * math.pi * turns * j / (36 * turns)
        r = 0.012 + 0.043 * j / (36 * turns)
        return (x0 + L * t, by + r * math.cos(th), zc + 0.03 * t + r * math.sin(th))
    sheet(roll, 10, 36 * turns)
    tob = tw.build("Cama_Toalla", [K['towel']], smooth=True)
    so = tob.modifiers.new("grosor", 'SOLIDIFY'); so.thickness = 0.012; so.offset = 0.0          # terry: thick, soft edges


def _wall_image(name, mat, y0, y1, z0, z1, x):
    """Picture plane on the east wall (x = const) facing the room, UV-mapped to the whole image."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x, y1, z0), (x, y0, z0), (x, y0, z1), (x, y1, z1)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for loop, c in zip(me.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[loop.index].uv = c
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.data.collections["House"].objects.link(ob)
    return ob


def _remove(*names):
    for n in names:
        ob = bpy.data.objects.get(n)
        if ob is None:
            continue
        for c in list(ob.children_recursive):
            bpy.data.objects.remove(c)
        bpy.data.objects.remove(ob)


def bedside(K):
    """Photo 5: white nightstand (grey top, one drawer, open cubby, plinth) with a white gooseneck LED lamp; the three
    black-framed prints above the bed are the listing's own photos (flower in a white mat, sunset, city)."""
    _remove("Nightstand", "Desk_Lamp", "Prints", "Prop_potted_plant_04", "Prop_desk_lamp_arm_01", "Shelf_Plant")
    by = BED_Y
    # beside the bed rail (photo 1, remoto/siluetas.py: was 27 cm too far toward the door once BED_Y moved)
    nx, ny, w, d, h = W - 0.32, by - BED_W / 2 - 0.245, 0.42, 0.40, 0.52   # remoto/siluetas.py: IoU 0.67 -> 0.96
    x0, x1, y0, y1 = nx - d / 2, nx + d / 2, ny - w / 2, ny + w / 2
    ns = MB(); t = 0.016
    ns.box(x0, x1, y0, y1, Z0 + h - 0.02, Z0 + h, 1)                              # grey top
    ns.box(x0, x1, y0, y0 + t, Z0 + 0.04, Z0 + h - 0.02, 0)                       # sides
    ns.box(x0, x1, y1 - t, y1, Z0 + 0.04, Z0 + h - 0.02, 0)
    ns.box(x1 - t, x1, y0, y1, Z0 + 0.04, Z0 + h - 0.02, 0)                       # back
    ns.box(x0 + 0.02, x1, y0 + t, y1 - t, Z0 + 0.04, Z0 + 0.06, 0)                # bottom shelf
    ns.box(x0 + 0.02, x1, y0 + t, y1 - t, Z0 + h - 0.17, Z0 + h - 0.155, 0)       # drawer bottom
    ns.box(x0, x0 + 0.018, y0 + t + 0.002, y1 - t - 0.002, Z0 + h - 0.155, Z0 + h - 0.025, 0)   # drawer front
    ns.box(x0 - 0.012, x0, ny - 0.07, ny + 0.07, Z0 + h - 0.095, Z0 + h - 0.085, 2)              # bar handle
    ns.box(x0 + 0.03, x1 - 0.03, y0 + 0.02, y1 - 0.02, Z0, Z0 + 0.04, 0)          # recessed plinth
    ns.build("Mesa_Noche", [K['white'], K['grey_top'], K['steel']], bevel=0.002)
    # grey ribbed place mat over most of the top (photo 1): 4 mm pad, ribs every 12 mm running front to back
    mt = 0.004
    mx0, mx1, my0, my1 = x0 + 0.025, x1 - 0.015, y0 + 0.02, y1 - 0.02
    mm = MB(); mm.box(mx0, mx1, my0, my1, Z0 + h, Z0 + h + mt * 0.6, 0)
    ny_r = int((my1 - my0) / 0.012)
    for i in range(ny_r):
        yc = my0 + (i + 0.5) * (my1 - my0) / ny_r
        mm.box(mx0, mx1, yc - 0.0035, yc + 0.0035, Z0 + h + mt * 0.6, Z0 + h + mt, 0)
    mm.build("Mesa_Individual", [_m.fabric("Individual_Gris", (0.36, 0.37, 0.37, 1), weave=200.0, bump=0.4, sheen=0.2)],
             bevel=0.001)
    # small boxwood-like plant in a satin gold pot at the front corner (photo 1)
    px_, py_, pz = nx - 0.085, ny - 0.05, Z0 + h + mt
    pt = MB()
    pt.cylinder(px_, py_, pz, pz + 0.075, 0.042, 0.05, seg=28, mi=0)
    pt.cylinder(px_, py_, pz + 0.068, pz + 0.07, 0.046, 0.046, seg=28, mi=1)                  # soil
    rnd = random.Random(11)
    for i in range(70):
        a = rnd.uniform(0, 2 * math.pi); el = rnd.uniform(math.radians(15), math.radians(85))
        L = rnd.uniform(0.07, 0.12)
        base = (px_ + 0.01 * math.cos(a), py_ + 0.01 * math.sin(a), pz + 0.07)
        tip = (px_ + L * math.cos(el) * math.cos(a), py_ + L * math.cos(el) * math.sin(a), pz + 0.07 + L * math.sin(el))
        pt.tube(base, tip, 0.0015, 0.001, seg=4, mi=2)
        for k in range(3):
            t = 0.45 + 0.27 * k + rnd.uniform(-0.05, 0.05)
            c = tuple(b + (q - b) * t + rnd.uniform(-0.008, 0.008) for b, q in zip(base, tip))
            pt.sphere(c, rnd.uniform(0.011, 0.016), seg=8, rings=5, mi=2, squash=0.45)
    pt.build("Mesa_Planta", [_m.new_mat("Maceta_Dorada", (0.66, 0.53, 0.30, 1), rough=0.35, metal=0.6),
                             _m.new_mat("Tierra", (0.06, 0.045, 0.03, 1), rough=0.95), K['leaf']], smooth=True)
    lp = MB()                                                                     # gooseneck lamp
    bx, byy, bz = nx + 0.04, ny + 0.05, Z0 + h + mt
    lp.cylinder(bx, byy, bz, bz + 0.02, 0.06, 0.055, seg=32)
    pts = [(bx, byy, bz + 0.02)]
    for i in range(1, 15):              # gooseneck: rises, then arcs over toward the bed so the head faces down
        a = i / 14 * math.radians(150)
        R = 0.13
        pts.append((bx - R * (1 - math.cos(a)) * 0.9, byy - 0.02 * i / 14, bz + 0.17 + R * math.sin(a)))
    pts.insert(1, (bx, byy, bz + 0.17))
    for p, q in zip(pts, pts[1:]):
        lp.tube(p, q, 0.006, 0.006, seg=10)
    lp.sphere((pts[-1][0] - 0.02, pts[-1][1], pts[-1][2] - 0.02), 0.035, seg=16, rings=8, squash=0.45)
    lp.build("Lampara_Flexible", [K['white']], smooth=True)

    # floating shelf left of the bed: the flower print stands on it, a trailing plant at its window end (photo 5)
    sz = Z0 + 1.42
    sh = MB(); sh.box(W - 0.16, W, by + 0.55, by + 1.12, sz - 0.025, sz, 0)
    sh.build("Repisa", [K['white']])
    pl = MB()                                            # small pot with trailing heart-shaped leaves (monstera adansonii)
    px_, py_ = W - 0.09, by + 1.0
    pl.cylinder(px_, py_, sz, sz + 0.09, 0.045, 0.055, seg=20, mi=0)
    rnd = random.Random(7)
    for i in range(16):
        a = rnd.uniform(0, 2 * math.pi); L = rnd.uniform(0.08, 0.30); droop = rnd.uniform(0.0, 0.25)
        tip = (px_ + 0.07 * math.cos(a) - 0.03, py_ + L * math.sin(a), sz + 0.10 + 0.06 - droop)
        pl.tube((px_, py_, sz + 0.09), tip, 0.003, 0.002, seg=4, mi=1)
        pl.sphere(tip, 0.035, seg=8, rings=5, mi=1, squash=0.25)
    pl.build("Repisa_Planta", [K['white'], K['leaf']], smooth=True)
    # prints: (name, centre y, bottom z, width, height, white mat border); the flower stands on the shelf, the other
    # two hang at stepped heights (photo 5)
    fx = W - 0.003
    for n, cy, z0, pw, ph, matb in (("flor", by + 0.74, sz, 0.26, 0.30, 0.07),
                                     ("atardecer", by + 0.0, Z0 + 1.56, 0.26, 0.36, 0.0),
                                     ("ciudad", by - 0.92, Z0 + 1.64, 0.30, 0.40, 0.0)):
        fr = MB(); b = 0.018
        fr.box(fx - 0.02, fx, cy - pw / 2, cy + pw / 2, z0, z0 + b, 0)
        fr.box(fx - 0.02, fx, cy - pw / 2, cy + pw / 2, z0 + ph - b, z0 + ph, 0)
        fr.box(fx - 0.02, fx, cy - pw / 2, cy - pw / 2 + b, z0, z0 + ph, 0)
        fr.box(fx - 0.02, fx, cy + pw / 2 - b, cy + pw / 2, z0, z0 + ph, 0)
        fr.box(fx - 0.006, fx, cy - pw / 2 + b, cy + pw / 2 - b, z0 + b, z0 + ph - b, 1)        # mat / backing
        fr.build(f"Marco_{n}", [K['frame_black'], K['mat_board']])
        m = b + matb
        _wall_image(f"Cuadro_{n}", K['prints'][n], cy - pw / 2 + m, cy + pw / 2 - m, z0 + m, z0 + ph - m, fx - 0.007)


def rug(K):
    """Jute rug with navy zigzag bands and fringed ends beside the bed (photos 1 and 5)."""
    ob = bpy.data.objects.get("Rug")
    if ob is not None:
        bpy.data.objects.remove(ob)
    # measured on photo 1 (remoto/medir_foto01.py, 59 cm tile scale): ~68 x 44 cm, fringed ends along X, far edge at the bed rail
    side = BED_Y - BED_W / 2                     # room-side rail: the rug's far edge sits 3 cm short of it (silhouettes)
    x0, x1, y0, y1 = W - 1.42, W - 0.74, side - 0.47, side - 0.03
    g = _grid("Tapete", x0, x1, y0, y1, Z0 + 0.008, 0.05, K['rug'])
    g.modifiers.new("thick", 'SOLIDIFY').thickness = 0.008
    fr = MB()
    for x, d in ((x0, -1), (x1, 1)):
        for i in range(36):
            y = y0 + 0.01 + i * (y1 - y0 - 0.02) / 35
            ang = 0.15 * math.sin(i * 2.3)
            fr.tube((x, y, Z0 + 0.008), (x + d * 0.06, y + ang * 0.06, Z0 + 0.003), 0.003, 0.002, seg=4)
    fr.build("Tapete_Flecos", [K['jute']])


SOFA_FONDO = 1.40          # m from the west wall to the front of the pulled-out sofa bed (photo 1, sofa_caja.py)


def sofa_bed(K):
    """Sofa bed on the west wall (photo 1): low brown upholstered futon with short arms, a patterned bolster along the
    top of the back, two big dark olive pillows and a beige blanket over the seat hanging down the front."""
    _remove("Sofa_Bed", "Prop_throw_pillows_01")
    cy, L = 5.72, 1.95
    y0, y1 = cy - L / 2, cy + L / 2
    so = MB()
    # Photo 1: the sofa bed is pulled out.  remoto/sofa_caja.py (silhouette, box model): depth 1.43 m against the
    # 0.92 m of the closed futon (IoU 0.75 -> 0.93; the photo pins it to about +-10 cm), seat top ~0.34-0.42 m.
    # The arms stay 0.92 m deep; the pulled-out section runs between them.
    D = SOFA_FONDO
    so.rbox(0.02, 0.92, y0, y1, Z0 + 0.08, Z0 + 0.30, r=0.03, mi=0)                  # base
    so.rbox(0.90, D, y0 + 0.12, y1 - 0.12, Z0 + 0.08, Z0 + 0.28, r=0.03, mi=0)       # pulled-out frame
    so.rbox(0.10, 0.92, y0 + 0.12, y1 - 0.12, Z0 + 0.30, Z0 + 0.42, r=0.05, puff=0.3, mi=0)   # seat mattress
    so.rbox(0.90, D, y0 + 0.13, y1 - 0.13, Z0 + 0.28, Z0 + 0.40, r=0.05, puff=0.3, mi=0)      # its second half
    for y in (y0 + 0.2, y1 - 0.2):
        so.cylinder(D - 0.06, y, Z0, Z0 + 0.08, 0.02, seg=10, mi=1)
    so.rbox(0.02, 0.24, y0 + 0.12, y1 - 0.12, Z0 + 0.30, Z0 + 0.72, r=0.05, puff=0.3, mi=0)   # back
    for a, b in ((y0, y0 + 0.12), (y1 - 0.12, y1)):
        so.rbox(0.02, 0.92, a, b, Z0 + 0.08, Z0 + 0.56, r=0.04, mi=0)                # low arms
    for x in (0.08, 0.86):
        for y in (y0 + 0.06, y1 - 0.06):
            so.cylinder(x, y, Z0, Z0 + 0.08, 0.02, seg=10, mi=1)
    sofa = so.build("Sofa_Cama", [K['sofa'], K['black']], smooth=True)
    # photo 1: the print covers the upper ~25 cm of the back along its whole length (it was a 12 cm roll on top)
    bo = MB(); bo.rbox(0.03, 0.27, y0 + 0.13, y1 - 0.13, Z0 + 0.60, Z0 + 0.86, r=0.05, puff=0.4)
    bo.build("Sofa_Cojin_Estampado", [K['bolster']], smooth=True)
    for dy, yaw in (() if CON_BIBLIO else ((-0.42, 5), (0.30, -7))):     # the library brings its own (SOFA_QUITAR)
        c = MB(); c.rbox(-0.08, 0.08, -0.30, 0.30, -0.26, 0.26, r=0.08, puff=0.7)
        pc = _placed(c, "Sofa_Almohadon", [K['olive']], (0.36, cy + dy, Z0 + 0.66),
                     (0, math.radians(-22), math.radians(yaw)), smooth=True)
        _inflate(pc, pressure=25.0)                       # filled bag: pinched edges, soft dimples
    # blanket: shaped directly (the cloth solver let it fall through the sofa): flat over the seat, rolling over the
    # front edge, hanging in soft folds to just above the floor
    # photo 1: the blanket lies on the pulled-out half (a strip of brown seat shows behind it) and hangs at the front
    if os.environ.get("MANTA", "tela") == "rigida":
        _hang_sheet("Sofa_Manta", K['throw'], x_back=0.66, x_edge=D, z_top=Z0 + 0.415, z_bottom=Z0 + 0.05,
                    y0=y0 + 0.16, y1=y1 - 0.15)
    else:
        _throw_cloth("Sofa_Manta", K['throw'], D, y0, y1)


def _throw_cloth(name, mat, D, y0, y1, step=0.025):
    """Blanket dropped by the cloth solver onto proxy boxes of the sofa (seat, pulled-out half, arms, back) and the
    floor.  The shaped sheet (_hang_sheet) read as a rigid board: straight hem, no sag (2026-11-13, photo 1).
    Photo 1: it lies on the pulled-out half, hangs at the front in soft waves to just above the floor, and its corner
    on the door side hangs past the side of the pulled-out frame.  A small yaw gives that corner its overhang.
    Proxies instead of Sofa_Cama itself: the cloth fell through the rounded, overlapping boxes of the real mesh."""
    W_, L_ = 1.20, 1.55                                 # across (x) and along the sofa (y), m
    PIN_U = 0.42                                        # back strip held on the seat (friction of a real blanket)
    xa, ya = 0.60, y0 + 0.13                            # back corner on the door side
    yaw = math.radians(-8)                              # front edge swings toward the door side
    nx, ny = round(W_ / step), round(L_ / step)
    rng = random.Random(1311)
    ph = [rng.uniform(0, 6.28) for _ in range(4)]
    vs = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, v = W_ * i / nx, L_ * j / ny
            x = xa + u * math.cos(yaw) - v * math.sin(yaw)
            y = ya + u * math.sin(yaw) + v * math.cos(yaw)
            # starts resting on the seat (top + collision gap); the back strip is PINNED there (v1, 2026-11-13: free,
            # the whole sheet slid off the front in 90 frames and ended as a wad on the floor)
            z = Z0 + (0.42 if x < 0.90 else 0.40) + 0.015
            # seed ripple on the free part: without it the solver hangs a perfectly symmetric single flat panel
            if u > PIN_U:
                z += 0.010 * math.sin(u * 9 + ph[0]) * math.sin(v * 6 + ph[1]) + 0.005 * math.sin(v * 17 + ph[2])
            vs.append((x, y, z))
    fs = [(j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i)
          for j in range(ny) for i in range(nx)]
    me = bpy.data.meshes.new(name); me.from_pydata(vs, [], fs)
    uv = me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        k = loop.vertex_index
        uv.data[loop.index].uv = ((k % (nx + 1)) / nx * W_, (k // (nx + 1)) / ny * L_)
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.data.collections["House"].objects.link(ob)
    vg = ob.vertex_groups.new(name="pin")
    vg.add([k for k in range(len(vs)) if (k % (nx + 1)) / nx * W_ < PIN_U], 1.0, 'REPLACE')
    # proxies (same numbers as sofa_bed): pulled-out half, seat mattress, arms, back, floor
    boxes = [(0.88, D, y0 + 0.12, y1 - 0.12, Z0, Z0 + 0.40), (0.10, 0.92, y0 + 0.12, y1 - 0.12, Z0, Z0 + 0.42),
             (0.02, 0.92, y0, y0 + 0.12, Z0, Z0 + 0.56), (0.02, 0.92, y1 - 0.12, y1, Z0, Z0 + 0.56),
             (0.02, 0.24, y0, y1, Z0, Z0 + 0.86), (-1.0, 4.0, y0 - 2.0, y1 + 2.0, Z0 - 0.2, Z0)]
    prox = []
    for k, (a, b, c, d, e, f) in enumerate(boxes):
        bm = bpy.data.meshes.new(f"_px{k}")
        bm.from_pydata([(a, c, e), (b, c, e), (b, d, e), (a, d, e), (a, c, f), (b, c, f), (b, d, f), (a, d, f)], [],
                       [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
        po = bpy.data.objects.new(f"_px{k}", bm); bpy.data.collections["House"].objects.link(po)
        po.modifiers.new("_col", 'COLLISION')
        po.collision.thickness_outer = 0.008; po.collision.cloth_friction = 12.0
        prox.append(po)
    S = bpy.context.scene
    cl = ob.modifiers.new("_cloth", 'CLOTH')
    s = cl.settings
    # soft fleece: low bending so it waves, low compression so the hang buckles into folds instead of a stiff panel
    s.quality = 12; s.mass = 0.35; s.air_damping = 1.5
    s.vertex_group_mass = "pin"; s.pin_stiffness = 1.0
    s.tension_stiffness = 15; s.compression_stiffness = 4; s.shear_stiffness = 5; s.bending_stiffness = 0.6
    cl.collision_settings.collision_quality = 4; cl.collision_settings.distance_min = 0.006
    frames = 90
    cl.point_cache.frame_start = 1; cl.point_cache.frame_end = frames
    f0, f1 = S.frame_start, S.frame_end
    S.frame_start, S.frame_end = 1, frames
    for f in range(1, frames + 1):
        S.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    ob.modifiers.clear(); ob.data = me2
    S.frame_start, S.frame_end = f0, f1
    S.frame_set(f0)
    for po in prox:
        bpy.data.objects.remove(po, do_unlink=True)
    # second face 6 mm under, reversed (closed-looking blanket; the solidify shell rendered black in the engine)
    co = [v.co.copy() for v in me2.vertices]
    nr = [v.normal.copy() for v in me2.vertices]
    faces = [tuple(p.vertices) for p in me2.polygons]
    vs2 = [tuple(c) for c in co] + [tuple(c - n * 0.006) for c, n in zip(co, nr)]
    off = len(co)
    fs2 = faces + [tuple(off + k for k in reversed(f)) for f in faces]
    me3 = bpy.data.meshes.new(name); me3.from_pydata(vs2, [], fs2); me3.validate()
    uv3 = me3.uv_layers.new(name="UVMap")
    for loop in me3.loops:
        k = loop.vertex_index % off
        uv3.data[loop.index].uv = ((k % (nx + 1)) / nx * W_, (k // (nx + 1)) / ny * L_)
    for p in me3.polygons:
        p.use_smooth = True
    me3.materials.append(mat)
    ob.data = me3
    zmin = min(v[2] for v in vs2[:off])
    print(f"[muebles] manta tela: {off} vértices, borde más bajo a {zmin - Z0:.3f} m del piso")
    return ob


def _hang_sheet(name, mat, x_back, x_edge, z_top, z_bottom, y0, y1, r=0.05, step=0.02, fold=0.012):
    """Sheet lying on a horizontal surface toward +x, wrapping a rounded front edge and hanging straight down, with
    vertical folds that grow toward the hem."""
    ny = max(2, round((y1 - y0) / step))
    path = []                                                   # (x, z, hang 0..1) along the cross-section
    n_top = max(2, round((x_edge - r - x_back) / step))
    for i in range(n_top + 1):
        path.append((x_back + (x_edge - r - x_back) * i / n_top, z_top, 0.0))
    for i in range(1, 7):
        a = math.pi / 2 * i / 6
        path.append((x_edge - r + r * math.sin(a), z_top - r + r * math.cos(a), 0.0))
    n_hang = max(2, round((z_top - r - z_bottom) / step))
    for i in range(1, n_hang + 1):
        t = i / n_hang
        path.append((x_edge + 0.01 * t, z_top - r - (z_top - r - z_bottom) * t, t))
    vs, fs = [], []
    for j in range(ny + 1):
        y = y0 + (y1 - y0) * j / ny
        for x, z, h in path:
            vs.append((x + fold * h * math.sin(y * 21.0) * (0.6 + 0.4 * math.sin(y * 7.3)), y, z))
    n = len(path)
    for j in range(ny):
        for i in range(n - 1):
            fs.append((j * n + i, j * n + i + 1, (j + 1) * n + i + 1, (j + 1) * n + i))
    # second layer 6 mm under, reversed: a closed-looking blanket without the solidify shell (its flipped normals
    # rendered as black triangles in the engine)
    off = len(vs)
    vs += [(x, y, z - 0.006) for x, y, z in vs]
    fs += [tuple(off + k for k in reversed(f)) for f in list(fs)]
    me = bpy.data.meshes.new(name); me.from_pydata(vs, [], fs); me.validate()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.data.collections["House"].objects.link(ob)
    return ob


# ---------------------------------------------------------------- balcony
def folding_chair(mb, cx, cy, face, z=Z0):
    """Bistro folding chair: X legs on each side, sling seat and back. `face` = yaw (rad) the sitter looks along."""
    ca, sa = math.cos(face), math.sin(face)

    def P(u, v, h):                 # u forward, v left, h up -> world
        return (cx + u * ca - v * sa, cy + u * sa + v * ca, z + h)
    r = 0.011
    for v in (-0.21, 0.21):
        mb.tube(P(0.22, v, 0), P(-0.2, v, 0.85), r, r, mi=0)              # back leg running up into the backrest
        mb.tube(P(-0.18, v, 0), P(0.2, v, 0.46), r, r, mi=0)              # front leg crossing it
        mb.tube(P(-0.15, v, 0.46), P(0.22, v, 0.46), r, r, mi=0)          # seat rail
    for (u, h) in ((0.22, 0.46), (-0.15, 0.46), (-0.2, 0.85), (-0.17, 0.6)):
        mb.tube(P(u, -0.21, h), P(u, 0.21, h), r, r, mi=0)
    def sling(corner, n=8, sag=0.025, t=0.003):
        """Fabric panel stretched between the rails; corner(s, v) -> (u, h) over s in 0..1 (front-back), sagging
        in the middle; two faces back to back so it shows from both sides in the engine."""
        pts = [[None] * (n + 1) for _ in range(n + 1)]
        for i in range(n + 1):
            for j in range(n + 1):
                s, w = i / n, j / n
                u, h = corner(s)
                d = sag * math.sin(math.pi * s) * math.sin(math.pi * w)
                pts[i][j] = (u, -0.2 + 0.4 * w, h - d)
        for off, flip in ((0.0, False), (-t, True)):
            for i in range(n):
                for j in range(n):
                    q = [P(*pts[a][b][:2], pts[a][b][2] + off) for a, b in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))]
                    mb.quad(*(q[::-1] if flip else q), mi=1)
    sling(lambda s: (0.21 - 0.36 * s, 0.46))                                                  # seat
    sling(lambda s: (-0.17 - 0.03 * s, 0.6 + 0.24 * s), sag=-0.02)                          # back


def balcony(K):
    # photo 3 looks east along the balcony from its west end: the set sits at the far (east) end, by the end wall
    yb = (Y_WIN + WT + Y_BAL) / 2
    tx, ty = BAL_TABLE_X, yb
    bs = MB()
    bs.cylinder(tx, ty, Z0 + 0.70, Z0 + 0.715, 0.30, seg=40, mi=2)                 # glass top
    bs.cylinder(tx, ty, Z0 + 0.68, Z0 + 0.70, 0.305, seg=40, mi=4)                 # dark rim
    for i in range(3):
        a = 2 * math.pi * i / 3 + 0.4
        bs.tube((tx + 0.06 * math.cos(a), ty + 0.06 * math.sin(a), Z0 + 0.68),
                (tx + 0.25 * math.cos(a), ty + 0.25 * math.sin(a), Z0), 0.012, 0.012, mi=4)
    folding_chair(bs, tx - 0.52, ty - 0.05, 0.0)            # near chair, facing the table and the end wall
    folding_chair(bs, tx + 0.5, ty + 0.05, math.pi)         # far chair between the table and the end wall
    bs.build("Balcon_Juego", [K['brown'], K['sling'], K['black_glass'], K['lantern'], K['black_metal']], smooth=True)
    # lantern (photo 2): white ceramic, barrel body with a pierced lattice lit from inside, domed lid, wire handle
    lx, ly, lz = 0.0, 0.0, 0.0             # built about its own axis, then placed
    # straight open cylinder, 17 cm across x 24 cm, thick rolled rim, thin wire bail from side to side (photo 2)
    body = _lathe("Farol_Cuerpo", [(0.0, 0.085), (0.22, 0.085)], K['lantern'], u_repeat=2)
    body.location = (tx - 0.08, ty - 0.08, Z0 + 0.715)
    la = MB()
    la.cylinder(lx, ly, lz + 0.22, lz + 0.24, 0.088, 0.083, seg=48, mi=1)                    # rim
    la.cylinder(lx, ly, lz + 0.235, lz + 0.24, 0.072, seg=48, mi=1)                          # dark open mouth
    la.cylinder(lx, ly, lz, lz + 0.012, 0.087, seg=48, mi=1)                                  # foot ring
    for i in range(16):                                                                       # wire bail
        a0, a1 = math.pi * i / 16, math.pi * (i + 1) / 16
        la.tube((lx + 0.088 * math.cos(a0), ly, lz + 0.20 + 0.10 * math.sin(a0)),
                (lx + 0.088 * math.cos(a1), ly, lz + 0.20 + 0.10 * math.sin(a1)), 0.0025, 0.0025, seg=6, mi=1)
    _placed(la, "Farol", [K['ceramic_white'], K['ceramic_white']], (tx - 0.08, ty - 0.08, Z0 + 0.715), smooth=True)


# ---------------------------------------------------------------- office chair
def ac_details(K):
    """Split AC (photos 1 and 5): dark louvre slot along the underside and the yellow energy label on the front."""
    x = W - 0.22
    d = MB()
    d.box(x - 0.004, x + 0.02, 3.2, 3.95, ZC - 0.40, ZC - 0.36, 0)                 # louvre slot
    d.box(x - 0.003, x, 3.78, 3.92, ZC - 0.33, ZC - 0.17, 1)                       # energy label
    d.build("AC_Detalle", [K['black'], K['label']])


def side_desk(K):
    """Photo 5: not a wall desk but a small laptop table: grey top on a white C-shaped frame, with a rattan ball."""
    _remove("Desk")
    x0, x1, y0, y1, h = W - 0.48, W - 0.08, Y_WIN - 0.85, Y_WIN - 0.25, 0.74
    t = MB()
    t.box(x0, x1, y0, y1, Z0 + h - 0.018, Z0 + h, 1)
    for y in (y0 + 0.03, y1 - 0.03):
        t.box(x1 - 0.06, x1 - 0.03, y - 0.015, y + 0.015, Z0 + 0.03, Z0 + h - 0.018, 0)       # upright at the wall side
        t.box(x0 + 0.02, x1 - 0.03, y - 0.02, y + 0.02, Z0, Z0 + 0.03, 0)                     # foot rail under the top
        t.box(x0 + 0.05, x1 - 0.06, y - 0.012, y + 0.012, Z0 + h - 0.05, Z0 + h - 0.018, 0)   # top bracket
    t.build("Mesa_Auxiliar", [K['white'], K['grey_top']], bevel=0.002)
    ball = MB(); ball.sphere((x1 - 0.1, y0 + 0.08, Z0 + h + 0.05), 0.05, seg=16, rings=10)
    ball.build("Esfera_Rattan", [K['towel']], smooth=True)


def office_chair(K):
    cx, cy, z = W - 0.85, Y_WIN - 0.6, Z0
    ch = MB()
    ch.rbox(cx - 0.24, cx + 0.24, cy - 0.25, cy + 0.25, z + 0.44, z + 0.52, r=0.03, puff=0.3, mi=0)      # seat
    # high mesh back: thin mesh panel inside a black tube frame, wider at the shoulders, tilted back ~10 deg
    def bk(h, s):                       # point on the back at height h (0..1) and side s (-1..1)
        half = 0.20 + 0.04 * math.sin(math.pi * min(1.0, h * 1.2))
        return (cx - 0.27 - 0.08 * h, cy + s * half, z + 0.58 + 0.46 * h)   # mid-height back (photo 5)
    rows = 8
    for i in range(rows):
        a0, a1 = i / rows, (i + 1) / rows
        for s0, s1 in ((-1, 0), (0, 1)):
            q = [bk(a0, s0), bk(a0, s1), bk(a1, s1), bk(a1, s0)]
            ch.quad(*q, mi=1); ch.quad(*q[::-1], mi=1)
    ring = [bk(i / rows, -1) for i in range(rows + 1)] + [bk(1, s / 4) for s in range(-3, 4)] + \
           [bk(1 - i / rows, 1) for i in range(rows + 1)]
    for p, q in zip(ring, ring[1:]):
        ch.tube(p, q, 0.012, 0.012, seg=8, mi=0)
    ch.tube((cx - 0.22, cy, z + 0.47), (cx - 0.29, cy, z + 0.6), 0.02, 0.02, mi=2)
    for s in (-1, 1):                                                                                  # flip-up arms
        ch.tube((cx - 0.22, cy + s * 0.25, z + 0.5), (cx - 0.15, cy + s * 0.26, z + 0.66), 0.012, 0.012, mi=2)
        ch.rbox(cx - 0.17, cx + 0.12, cy + s * 0.26 - 0.03, cy + s * 0.26 + 0.03, z + 0.65, z + 0.68, r=0.01, mi=0)
    ch.cylinder(cx, cy, z + 0.08, z + 0.44, 0.025, seg=12, mi=2)
    for i in range(5):
        a = 2 * math.pi * i / 5
        ch.tube((cx, cy, z + 0.09), (cx + 0.3 * math.cos(a), cy + 0.3 * math.sin(a), z + 0.06), 0.018, 0.014, mi=2)
        ch.sphere((cx + 0.3 * math.cos(a), cy + 0.3 * math.sin(a), z + 0.03), 0.03, seg=8, rings=5, mi=0)
    ch.build("Silla_Oficina", [K['black'], K['mesh'], K['black_metal']], smooth=True)


def build(M):
    for n in REPLACES:
        ob = bpy.data.objects.get(n)
        if ob is not None:
            bpy.data.objects.remove(ob)
    import time
    t = time.time(); K = _mats(M); print(f"[muebles] materiales {time.time() - t:5.1f}s")
    for f in (bed, bedside, rug, sofa_bed, balcony, side_desk, office_chair, ac_details):   # perfil: 50 de los 59 s del
        t = time.time(); f(K); print(f"[muebles] {f.__name__:12s} {time.time() - t:5.1f}s")    # armado estaban aquí
