"""Furniture modelled to measure from the listing photos (replaces the Hunyuan3D shapes of generados.py, which came out
melted): the bed with draped bedding (cloth simulation), the balcony bistro set and the mesh office chair.

Bed (photos 1 and 5): oak frame on four straight legs, low cream upholstered headboard, white quilt with lengthwise
channel stitching hanging over the sides, palm-print runner across the foot third, two quilted white pillows, two pale
blue cushions, rolled and fan-folded towels.  Balcony (photo 3): two brown folding chairs with sling seats, round
brown-tinted glass table, white lantern.  Office chair (photo 5): black mesh back, flip-up arms, five-star base.
"""
import math
import os

import bpy

from .plan import *
from .house import ASSETS
from archviz.mesh import MB
from archviz import materials as _m

REPLACES = ["Bed", "Cushions_Blue", "Balcony_Set", "Office_Chair"]
BED_L, BED_W = 1.95, 1.40
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


def _drape(ob, colliders, frames=48, bend=6.0, mass=0.4, thick=0.01):
    """Drop the cloth onto the colliders, freeze the final shape, then give it thickness."""
    S = bpy.context.scene
    for c in colliders:
        c.modifiers.new("_col", 'COLLISION')
        c.collision.thickness_outer = 0.004
        c.collision.cloth_friction = 8.0
    cl = ob.modifiers.new("_cloth", 'CLOTH')
    s = cl.settings
    s.quality = 8; s.mass = mass; s.air_damping = 2.0
    s.tension_stiffness = 25; s.compression_stiffness = 25; s.shear_stiffness = 10; s.bending_stiffness = bend
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
    rz0, rz1 = Z0 + 0.13, Z0 + 0.30
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
    hb = MB(); hb.rbox(HX + 0.01, HX + 0.07, by - hw - 0.04, by + hw + 0.04, Z0 + 0.32, Z0 + 1.08, r=0.025, puff=0.15)
    hb.build("Cama_Cabecero", [K['head']], smooth=True)
    mt = MB(); mt.rbox(FX + 0.01, HX - 0.02, by - hw + 0.01, by + hw - 0.01, MATT_Z0, MATT_Z1, r=0.06, puff=0.12)
    matt = mt.build("Cama_Colchon", [K['sheet']], smooth=True)

    # pillows leaning on the headboard, then the blue cushions in front of them
    pil = []
    for dy in (-0.33, 0.33):
        p = MB(); p.rbox(-0.08, 0.08, -0.33, 0.33, -0.23, 0.23, r=0.07, puff=0.6)
        pil.append(_placed(p, "Cama_Almohada", [K['pillow']], (HX - 0.17, by + dy, MATT_Z1 + 0.2),
                           (0, math.radians(18), 0), smooth=True))     # top leans back onto the headboard
    for dy, yaw in ((-0.2, 8), (0.2, -10)):       # square 45 cm cushions with crisp piped edges (photo 5)
        c = MB(); c.rbox(-0.06, 0.06, -0.22, 0.22, -0.22, 0.22, r=0.025, puff=0.45)
        _placed(c, "Cama_Cojin", [K['cushion']], (HX - 0.36, by + dy, MATT_Z1 + 0.19),
                (0, math.radians(24), math.radians(yaw)), smooth=True)

    # quilt from the foot to just below the pillows, hanging ~30 cm over the sides and foot
    # overhang ~18 cm: it covers the mattress side and stops on the oak rail, which stays visible (photo 5)
    quilt = _grid("Cama_Colcha", FX - 0.14, HX - 0.52, by - hw - 0.15, by + hw + 0.15, MATT_Z1 + 0.05, 0.022, K['quilt'])
    _drape(quilt, [matt, frame], bend=12.0, mass=0.5)
    # runner across the foot third, draped over the quilt
    rx = FX + 0.55
    runner = _grid("Cama_Camino", rx - 0.26, rx + 0.26, by - hw - 0.3, by + hw + 0.3, MATT_Z1 + 0.12, 0.02, K['runner'],
                   tile=(0.26, 0.6))              # straight repeat of the photographed print, ~25 cm palms
    _drape(runner, [quilt, matt, frame], bend=2.0, mass=0.2, thick=0.004)

    # towel "swan" (photos 1 and 5): a roll lying across the bed with a pleated fan spreading from one end
    tz = _top_z(runner, rx, by)
    tw = MB()
    r0 = 0.05
    tw.tube((rx + 0.02, by - 0.22, tz + r0), (rx + 0.02, by + 0.05, tz + r0), r0, r0, seg=20)
    for e in (by - 0.22, by + 0.05):
        tw.sphere((rx + 0.02, e, tz + r0), r0, seg=20, rings=8)
    n, R, a0, a1 = 9, 0.30, math.radians(-70), math.radians(70)            # fan: alternating ridge / valley pleats
    cx, cy = rx + 0.02, by + 0.06
    for i in range(n):
        ta, tm, tb = (a0 + (a1 - a0) * f for f in (i / n, (i + 0.5) / n, (i + 1) / n))
        h = 0.035 if i % 2 else 0.012
        p_a = (cx - R * math.sin(ta) * 0.6, cy + R * math.cos(ta), tz + 0.012)
        p_m = (cx - R * math.sin(tm) * 0.6, cy + R * math.cos(tm), tz + h)
        p_b = (cx - R * math.sin(tb) * 0.6, cy + R * math.cos(tb), tz + 0.012)
        hub = (cx, cy, tz + 0.03)
        tw._add([hub, p_a, p_m, p_b], [(0, 1, 2), (0, 2, 3), (0, 2, 1), (0, 3, 2)], 0)   # both sides
    tw.build("Cama_Toalla", [K['towel']], smooth=True)


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
    nx, ny, w, d, h = W - 0.24, by - 1.2, 0.42, 0.40, 0.52
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
    lp = MB()                                                                     # gooseneck lamp
    bx, byy, bz = nx + 0.04, ny + 0.05, Z0 + h
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
    import random
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
    x0, x1, y0, y1 = W - 1.75, W - 0.55, BED_Y - 1.40, BED_Y - 0.80             # 120 x 60 cm
    g = _grid("Tapete", x0, x1, y0, y1, Z0 + 0.008, 0.05, K['rug'])
    g.modifiers.new("thick", 'SOLIDIFY').thickness = 0.008
    fr = MB()
    for x, d in ((x0, -1), (x1, 1)):
        for i in range(36):
            y = y0 + 0.01 + i * (y1 - y0 - 0.02) / 35
            ang = 0.15 * math.sin(i * 2.3)
            fr.tube((x, y, Z0 + 0.008), (x + d * 0.06, y + ang * 0.06, Z0 + 0.003), 0.003, 0.002, seg=4)
    fr.build("Tapete_Flecos", [K['jute']])


def sofa_bed(K):
    """Sofa bed on the west wall (photo 1): low brown upholstered futon with short arms, a patterned bolster along the
    top of the back, two big dark olive pillows and a beige blanket over the seat hanging down the front."""
    _remove("Sofa_Bed", "Prop_throw_pillows_01")
    cy, L = 5.72, 1.95
    y0, y1 = cy - L / 2, cy + L / 2
    so = MB()
    so.rbox(0.02, 0.92, y0, y1, Z0 + 0.08, Z0 + 0.30, r=0.03, mi=0)                  # base
    so.rbox(0.10, 0.92, y0 + 0.12, y1 - 0.12, Z0 + 0.30, Z0 + 0.42, r=0.05, puff=0.3, mi=0)   # seat mattress
    so.rbox(0.02, 0.24, y0 + 0.12, y1 - 0.12, Z0 + 0.30, Z0 + 0.72, r=0.05, puff=0.3, mi=0)   # back
    for a, b in ((y0, y0 + 0.12), (y1 - 0.12, y1)):
        so.rbox(0.02, 0.92, a, b, Z0 + 0.08, Z0 + 0.56, r=0.04, mi=0)                # low arms
    for x in (0.08, 0.86):
        for y in (y0 + 0.06, y1 - 0.06):
            so.cylinder(x, y, Z0, Z0 + 0.08, 0.02, seg=10, mi=1)
    sofa = so.build("Sofa_Cama", [K['sofa'], K['black']], smooth=True)
    bo = MB(); bo.rbox(0.03, 0.22, y0 + 0.14, y1 - 0.14, Z0 + 0.72, Z0 + 0.84, r=0.05, puff=0.5)
    bo.build("Sofa_Cojin_Estampado", [K['bolster']], smooth=True)
    for dy, yaw in ((-0.42, 5), (0.30, -7)):
        c = MB(); c.rbox(-0.08, 0.08, -0.30, 0.30, -0.26, 0.26, r=0.08, puff=0.7)
        _placed(c, "Sofa_Almohadon", [K['olive']], (0.36, cy + dy, Z0 + 0.66), (0, math.radians(-22), math.radians(yaw)),
                smooth=True)
    # blanket: shaped directly (the cloth solver let it fall through the sofa): flat over the seat, rolling over the
    # front edge, hanging in soft folds to just above the floor
    _hang_sheet("Sofa_Manta", K['throw'], x_back=0.28, x_edge=0.92, z_top=Z0 + 0.435, z_bottom=Z0 + 0.06,
                y0=y0 + 0.22, y1=y1 - 0.3)


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
    K = _mats(M)
    bed(K)
    bedside(K)
    rug(K)
    sofa_bed(K)
    balcony(K)
    side_desk(K)
    office_chair(K)
    ac_details(K)
