"""Kitchen, bathroom and laundry/fridge nook rebuilt to the photos after the independent audit (photos 4, 6 and 7),
replacing the generic fixtures of interior.py.  Tile patterns that are hard to model (the faceted 3D splashback, the
triangle shower tile) are the photos themselves, cropped and tiled.

Kitchen (photo 4): white handleless base run with a two-drawer stack, grey quartz top, four-burner gas hob with cast
grates and side knobs, slim stainless hood, gloss-yellow uppers (a tall pair over the hob, a high pair over an open
white niche with a shelf), undermount steel sink and black gooseneck tap, letter board, plant, coasters, blender,
rice cooker, wine glasses and jars on the shelf, a blue towel on a hook.
Bathroom (photo 6): floating walnut vanity (drawer + two doors) with an integrated white basin, black tap, wide mirror
over grey 30x60 wainscot, one-piece WC, shower with grey walls and a triangle-pattern back wall, wall-arm rain head,
black mixer and soap rack, high barred window with a trailing plant, towel bar, bath mat, paper holder.
Laundry (photo 7): LG-style stainless two-door fridge with dispenser, top-load washer, beige tiled niche, a single
yellow door with a lock over the fridge.
"""
import math

import bpy

from .plan import *
from .house import ASSETS
from archviz.mesh import MB
from archviz import materials as _m
from .muebles import _image_mat, _remove, _lathe, _placed

import os

GEN = os.path.join(ASSETS, "gen")


def _plane(name, mat, p0, du, dv, tile):
    """Quad from p0 spanning vectors du, dv (metres), UVs repeating every tile=(tu, tv) metres; faces du x dv."""
    lu, lv = math.sqrt(sum(c * c for c in du)), math.sqrt(sum(c * c for c in dv))
    vs = [p0, tuple(a + b for a, b in zip(p0, du)), tuple(a + b + c for a, b, c in zip(p0, du, dv)),
          tuple(a + b for a, b in zip(p0, dv))]
    me = bpy.data.meshes.new(name); me.from_pydata(vs, [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for loop, c in zip(me.loops, ((0, 0), (lu / tile[0], 0), (lu / tile[0], lv / tile[1]), (0, lv / tile[1]))):
        uv.data[loop.index].uv = c
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.data.collections["House"].objects.link(ob)
    return ob


def _mats(M):
    return dict(
        white=_m.new_mat("Cocina_Blanco", (0.84, 0.84, 0.82, 1), rough=0.3),
        # countertop and splashback follow the finish package when one is chosen (house.paquete)
        yellow=M['amarillo'], quartz=M.get('cuarzo') or _m.new_mat("Cuarzo_Gris", (0.22, 0.22, 0.21, 1), rough=0.3),
        # brushed stainless: darker base + some roughness, or under overcast light it reflects the white walls and
        # reads as white plastic (audit 2: fridge, hood, sink)
        steel=_m.new_mat("Inox_Cepillado", (0.42, 0.42, 0.42, 1), rough=0.28, metal=1.0), black=M['black'],
        sky=_m.new_mat("Ventana_Cielo", (0.9, 0.92, 0.95, 1), rough=0.1, emit=(0.85, 0.9, 1.0, 1), emit_str=2.0),
        cast=_m.new_mat("Hierro_Fundido", (0.02, 0.02, 0.02, 1), rough=0.6),
        splash=M.get('salpicadero_pkg') or _image_mat("Salpicadero_3D_Foto", os.path.join(GEN, "salpicadero.jpg"),
                                                      rough=0.6, sheen=0.0),
        shower_tile=_image_mat("Ducha_Triangulos", os.path.join(GEN, "ducha_triangulos.jpg"), rough=0.3, sheen=0.0),
        bath_grey=_m.tiles("Bano_Gris_30x60", (0.40, 0.40, 0.38, 1), grout=(0.47, 0.47, 0.45, 1), size=(0.6, 0.3),
                           gap=0.002, rough=0.35, variation=0.05, mottle=0.3, bump=0.1, plane='YZ'),
        bath_grey_xz=_m.tiles("Bano_Gris_30x60_S", (0.40, 0.40, 0.38, 1), grout=(0.47, 0.47, 0.45, 1),
                              size=(0.6, 0.3), gap=0.002, rough=0.35, variation=0.05, mottle=0.3, bump=0.1, plane='XZ'),
        laundry_tile=_m.tiles("Lavanderia_Beige", (0.70, 0.66, 0.58, 1), grout=(0.76, 0.73, 0.66, 1), size=(0.6, 0.3),
                              gap=0.002, rough=0.4, variation=0.04, mottle=0.2, bump=0.1, plane='YZ'),
        walnut=_m.wood("Nogal_Vanity", light=(0.17, 0.09, 0.05, 1), dark=(0.10, 0.055, 0.03, 1), grain_axis='Y', rough=0.5),
        ceramic=M['ceramic'], mirror=M['mirror'], glass=M['glass'],
        # satin cast-marble basin: the gloss ceramic mirrored the wooden door into the bowl (read as brown)
        basin=_m.new_mat("Lavamanos_Marmol", (0.88, 0.88, 0.87, 1), rough=0.35, spec=0.3),
        board=_image_mat("Letrero_Bienvenidos", os.path.join(GEN, "bienvenidos.jpg"), rough=0.6, sheen=0.0),
        jute=_m.fabric("Yute_Matera", (0.62, 0.52, 0.36, 1), weave=150.0, bump=0.6),
        leaf=M['leaf_plant'], navy=_m.fabric("Toalla_Azul", (0.06, 0.10, 0.22, 1)),
        coaster=_m.new_mat("Posavasos", (0.10, 0.14, 0.26, 1), rough=0.8),
        cream_towel=_m.fabric("Toalla_Crema_Bano", (0.86, 0.82, 0.68, 1), weave=180.0, bump=0.6, sheen=0.8),
        mat_grey=_m.fabric("Tapete_Bano", (0.18, 0.17, 0.16, 1), weave=200.0, bump=0.8),
        chrome=_m.new_mat("Cromo", (0.85, 0.85, 0.85, 1), rough=0.08, metal=1.0),
        frame=M['frame'], red=_m.new_mat("Nevera_Playa_Roja", (0.55, 0.05, 0.04, 1), rough=0.4),
        label=_m.new_mat("Etiqueta_Lavadora", (0.95, 0.80, 0.10, 1), rough=0.5),
    )


# ------------------------------------------------------------------------------------------------ kitchen
def kitchen(K):
    _remove("Kitchen", "Kitchen_Uppers", "Kitchen_Appliances", "Kitchen_Decor",
            "Prop_pachira_aquatica_01", "Prop_ceramic_vase_01", "Prop_potted_plant_02", "Prop_potted_plant_01")
    x0, x1, y0, y1 = KITCHEN                         # run against the west wall, front face at x1
    zt = Z0 + 0.87
    b = MB()
    b.box(x0 + 0.02, x1 - 0.02, y0, y1, Z0 + 0.10, zt, 0)                         # carcass
    b.box(x0 + 0.05, x1 - 0.06, y0, y1, Z0, Z0 + 0.10, 2)                         # toe kick (dark)
    g = 0.003
    fronts = [(y0, 0.52, None), (0.52, 0.95, None), (0.95, 1.40, 'drawers'), (1.40, 1.85, None),
              (1.85, 2.15, None), (2.15, y1, None)]
    for a, c, kind in fronts:
        if kind == 'drawers':
            zm = Z0 + 0.10 + (zt - Z0 - 0.10) * 0.5
            b.box(x1 - 0.02, x1, a + g, c - g, Z0 + 0.10 + g, zm - g, 0)
            b.box(x1 - 0.02, x1, a + g, c - g, zm + g, zt - 0.03, 0)
        else:
            b.box(x1 - 0.02, x1, a + g, c - g, Z0 + 0.10 + g, zt - 0.03, 0)
    b.build("Cocina_Base", [K['white'], K['white'], K['black']], bevel=0.002)
    # quartz top with the sink cut-out, undermount bowl
    sx0, sx1, sy0, sy1 = 0.13, 0.50, 1.88, 2.30
    t = MB()
    t.box(x0, x1 + 0.02, y0, sy0, zt, zt + 0.03, 0); t.box(x0, x1 + 0.02, sy1, y1, zt, zt + 0.03, 0)
    t.box(x0, sx0, sy0, sy1, zt, zt + 0.03, 0); t.box(sx1, x1 + 0.02, sy0, sy1, zt, zt + 0.03, 0)
    bz = zt - 0.17
    t.box(sx0, sx1, sy0, sy1, bz, bz + 0.004, 1)
    for (a0, a1, c0, c1) in ((sx0, sx0 + 0.004, sy0, sy1), (sx1 - 0.004, sx1, sy0, sy1),
                             (sx0, sx1, sy0, sy0 + 0.004), (sx0, sx1, sy1 - 0.004, sy1)):
        t.box(a0, a1, c0, c1, bz, zt, 1)
    t.cylinder((sx0 + sx1) / 2, (sy0 + sy1) / 2, bz + 0.004, bz + 0.008, 0.035, seg=20, mi=1)
    t.build("Cocina_Meson", [K['quartz'], K['steel']])
    # gas hob: stainless plate, four burners, two cast grates, five knobs on its right
    h = MB(); hz = zt + 0.03
    h.box(0.06, 0.56, 0.16, 0.80, hz, hz + 0.006, 0)
    for cx, cy in ((0.19, 0.29), (0.42, 0.29), (0.19, 0.58), (0.42, 0.58)):
        h.cylinder(cx, cy, hz + 0.006, hz + 0.02, 0.05, seg=20, mi=1)
        h.cylinder(cx, cy, hz + 0.02, hz + 0.03, 0.035, seg=20, mi=0)
    for gy0, gy1 in ((0.17, 0.43), (0.45, 0.71)):                                  # grates
        for gx in (0.08, 0.19, 0.31, 0.42, 0.54):
            h.box(gx - 0.006, gx + 0.006, gy0, gy1, hz + 0.03, hz + 0.045, 1)
        for gy in (gy0, (gy0 + gy1) / 2, gy1):
            h.box(0.07, 0.55, gy - 0.006, gy + 0.006, hz + 0.03, hz + 0.045, 1)
    for i in range(5):
        h.cylinder(0.14 + i * 0.075, 0.76, hz + 0.006, hz + 0.03, 0.017, seg=14, mi=1)
    h.build("Cocina_Estufa", [K['steel'], K['cast']], smooth=True)
    # slim stainless hood under the tall uppers
    hd = MB()
    hd.box(0.0, 0.47, 0.12, 0.80, Z0 + 1.46, Z0 + 1.53, 0)
    hd.box(0.47, 0.475, 0.16, 0.50, Z0 + 1.50, Z0 + 1.52, 1)                         # vent slots strip
    for i in range(5):
        hd.cylinder(0.473, 0.58 + i * 0.035, Z0 + 1.49, Z0 + 1.497, 0.008, seg=8, mi=1)
    hd.build("Cocina_Campana", [K['steel'], K['black']])
    # uppers: tall pair over the hob, open white niche with a shelf, high pair over the niche
    u = MB(); gap = 0.004; zc = ZC - 0.30; ud = 0.34
    u.box(x0, ud, 0.10, 0.84, Z0 + 1.55, zc, 1)                                      # carcass over hob
    for a, c in ((0.10, 0.47), (0.47, 0.84)):
        u.box(ud, ud + 0.02, a + gap, c - gap, Z0 + 1.55 + gap, zc - gap, 0)
    u.box(x0, ud + 0.02, 0.84, 0.865, Z0 + 1.42, zc, 1)                              # niche side
    u.box(x0, ud + 0.02, 0.865, y1, Z0 + 1.42, Z0 + 1.45, 1)                         # shelf
    u.box(x0, ud, 0.865, y1, Z0 + 1.80, zc, 1)                                       # high carcass
    u.box(x0, ud + 0.02, 0.865, y1, Z0 + 1.78, Z0 + 1.80, 1)                         # its white underside
    for a, c in ((0.865, 1.82), (1.82, y1)):
        u.box(ud, ud + 0.02, a + gap, c - gap, Z0 + 1.80 + gap, zc - gap, 0)
    u.build("Cocina_Alacenas", [K['yellow'], K['white']])
    # splashback: the photographed faceted tile, from the worktop to the shelf / hood
    _plane("Cocina_Salpicadero", K['splash'], (0.004, y0, zt + 0.03), (0, y1 - y0, 0), (0, 0, Z0 + 1.42 - zt - 0.03),
           (0.62, 0.40))
    # tap: black gooseneck
    f = MB(); fx, fy = 0.07, (sy0 + sy1) / 2
    f.cylinder(fx, fy, zt + 0.03, zt + 0.06, 0.025, seg=16)
    pts = [(fx, fy, zt + 0.06), (fx, fy, zt + 0.30)]
    for i in range(1, 9):
        a = math.pi * i / 8
        pts.append((fx + 0.08 * (1 - math.cos(a)) / 2 * 2, fy, zt + 0.30 + 0.06 * math.sin(a)))
    for p, q in zip(pts, pts[1:]):
        f.tube(p, q, 0.012, 0.012, seg=12)
    f.build("Cocina_Grifo", [K['black']], smooth=True)
    _shelf_and_counter_decor(K, zt + 0.03)


def _shelf_and_counter_decor(K, zc):
    sz = Z0 + 1.45
    d = MB()
    d.cylinder(0.16, 1.02, sz, sz + 0.16, 0.10, 0.085, seg=24, mi=0)                     # rice cooker
    d.cylinder(0.16, 1.22, sz, sz + 0.08, 0.07, seg=20, mi=0)                             # blender base
    d.cylinder(0.16, 1.22, sz + 0.08, sz + 0.30, 0.06, 0.075, seg=20, mi=1)              # glass jug
    for i in range(6):                                                                   # inverted wine glasses
        gx, gy = 0.10 + (i % 2) * 0.1, 1.38 + (i // 2) * 0.08
        d.cylinder(gx, gy, sz, sz + 0.09, 0.04, 0.025, seg=16, mi=1)
        d.cylinder(gx, gy, sz + 0.09, sz + 0.17, 0.004, seg=8, mi=1)
        d.cylinder(gx, gy, sz + 0.17, sz + 0.175, 0.03, seg=16, mi=1)
    for i in range(4):
        d.cylinder(0.14, 1.70 + i * 0.045, sz, sz + 0.09, 0.02, seg=12, mi=1)            # spice jars
    d.cylinder(0.15, 1.95, sz, sz + 0.24, 0.03, 0.02, seg=12, mi=2)                       # olive oil
    d.cylinder(0.16, 2.12, sz, sz + 0.24, 0.055, seg=20, mi=1)                            # pitcher
    # counter: letter board on an easel, plant in a jute pot, two coasters, folded napkins
    d.box(0.09, 0.30, 1.16, 1.18, zc, zc + 0.02, 3)
    d.cylinder(0.32, 1.44, zc, zc + 0.08, 0.05, 0.055, seg=20, mi=4)
    for cy in (1.58, 1.73):
        d.cylinder(0.36, cy, zc, zc + 0.006, 0.05, seg=24, mi=5)
    d.box(0.42, 0.52, 1.20, 1.34, zc, zc + 0.03, 6)
    d.build("Cocina_Decor", [K['black'], K['glass'], K['cast'], K['white'], K['jute'], K['coaster'], K['white']],
            smooth=True)
    # letter board: black frame + photo-style letter panel, leaning back
    lb = MB(); lb.box(-0.01, 0.01, -0.14, 0.14, 0.0, 0.22)
    _placed(lb, "Cocina_Letrero_Marco", [K['black']], (0.20, 1.17, zc), (0, math.radians(-12), 0))
    pl = _plane("Cocina_Letrero", K['board'], (0.0, -0.125, 0.012), (0, 0.25, 0), (0, 0, 0.196), (0.25, 0.196))  # faces +x
    pl.location = (0.212, 1.17, zc); pl.rotation_euler = (0, math.radians(-12), 0)
    # plant on the counter: small leafy dome
    pp = MB()
    for i in range(18):
        a = i * 2.4; r = 0.03 + 0.03 * ((i * 7) % 5) / 5
        pp.sphere((0.32 + r * math.cos(a), 1.44 + r * math.sin(a), zc + 0.11 + 0.04 * ((i * 3) % 4) / 4), 0.03,
                  seg=8, rings=5)
    pp.build("Cocina_Planta", [K['leaf']], smooth=True)
    # blue towel on a hook on the splashback
    tw = MB(); tw.box(0.006, 0.02, 1.08, 1.22, Z0 + 1.02, Z0 + 1.30)
    tw.build("Cocina_Toalla", [K['navy']])


# ------------------------------------------------------------------------------------------------ bathroom
def bathroom(K):
    _remove("Bath_Tiles", "Bath_Vanity", "WC", "Shower", "Bath_Window", "Towel")
    x0, x1, y0, y1 = BATH
    ys = 1.05                                                    # shower screen line
    wz = Z0 + 1.12                                               # wainscot / mirror bottom
    # grey 30x60 tiles: east wall full height in the shower, wainscot elsewhere; west wall in the shower
    t = MB()
    t.box(x1 - 0.008, x1, y0, ys, Z0, ZC - 0.02, 0)
    t.box(x1 - 0.008, x1, ys, y1, Z0, wz, 0)
    t.box(x0, x0 + 0.008, y0, ys, Z0, ZC - 0.02, 0)
    t.build("Bano_Enchape", [K['bath_grey']])
    # triangle-pattern back wall of the shower (photo texture)
    _plane("Bano_Ducha_Fondo", K['shower_tile'], (x1 - 0.01, y0 + 0.006, Z0), (-(x1 - x0 - 0.02), 0, 0),
           (0, 0, ZC - 0.02 - Z0), (0.60, 0.84))            # audit 2: pattern was at half scale
    # floating walnut vanity: drawer over two doors, integrated white basin top
    v = MB(); vx0, vx1, vy0, vy1 = x1 - 0.47, x1 - 0.01, 1.95, 2.62
    vz0, vz1 = Z0 + 0.38, Z0 + 0.80
    v.box(vx0 + 0.02, vx1, vy0, vy1, vz0, vz1 - 0.13, 0)       # carcass stops below the basin bowl
    g = 0.004
    v.box(vx0, vx0 + 0.02, vy0 + g, vy1 - g, vz1 - 0.16, vz1 - g, 0)                       # drawer
    for a, c in ((vy0 + g, (vy0 + vy1) / 2 - g), ((vy0 + vy1) / 2 + g, vy1 - g)):
        v.box(vx0, vx0 + 0.02, a, c, vz0 + g, vz1 - 0.16 - g, 0)                         # doors
    v.build("Bano_Mueble", [K['walnut']], bevel=0.002)
    # integrated basin: a rim around a real 12 cm bowl sloping to a chrome pop-up drain
    bs = MB(); top0, top1 = vz1, vz1 + 0.06
    bx0, bx1, by0, by1 = vx0 + 0.05, vx1 - 0.10, vy0 + 0.06, vy1 - 0.06
    bs.box(vx0 - 0.02, vx1, vy0 - 0.02, by0, top0, top1); bs.box(vx0 - 0.02, vx1, by1, vy1 + 0.02, top0, top1)
    bs.box(vx0 - 0.02, bx0, by0, by1, top0, top1); bs.box(bx1, vx1, by0, by1, top0, top1)
    dz = top1 - 0.12
    cxb, cyb = (bx0 + bx1) / 2, (by0 + by1) / 2
    for (p, q) in (((bx0, by0), (bx1, by0)), ((bx1, by0), (bx1, by1)), ((bx1, by1), (bx0, by1)), ((bx0, by1), (bx0, by0))):
        ring = [(p[0], p[1], top1), (q[0], q[1], top1), (cxb + (q[0] - cxb) * 0.25, cyb + (q[1] - cyb) * 0.25, dz),
                (cxb + (p[0] - cxb) * 0.25, cyb + (p[1] - cyb) * 0.25, dz)]
        bs.quad(*ring); bs.quad(*ring[::-1])                 # both windings: engines cull back faces
    hx_, hy_ = (bx1 - bx0) / 2 * 0.25, (by1 - by0) / 2 * 0.25
    bs.box(cxb - hx_, cxb + hx_, cyb - hy_, cyb + hy_, dz - 0.006, dz, 0)                   # bowl floor (no gap)
    bs.cylinder(cxb, cyb, dz - 0.005, dz + 0.004, 0.032, seg=24, mi=2)                       # drain
    bs.build("Bano_Lavamanos", [K['basin'], K['white'], K['chrome']], smooth=True)
    # black single-lever tap, soap pump, glass, plant in a jute basket
    a = MB()
    a.box(x1 - 0.09, x1 - 0.05, 2.08, 2.12, top1, top1 + 0.16, 0)
    a.box(x1 - 0.17, x1 - 0.05, 2.085, 2.115, top1 + 0.13, top1 + 0.155, 0)
    a.cylinder(x1 - 0.08, 2.32, top1, top1 + 0.13, 0.035, seg=16, mi=0)
    a.cylinder(x1 - 0.08, 2.43, top1, top1 + 0.09, 0.03, seg=16, mi=1)
    a.cylinder(x1 - 0.10, 2.55, top1, top1 + 0.09, 0.05, 0.055, seg=16, mi=2)
    a.build("Bano_Accesorios", [K['black'], K['glass'], K['jute']], smooth=True)
    pp = MB()
    for i in range(16):
        ang = i * 2.4; r = 0.02 + 0.03 * ((i * 7) % 5) / 5
        pp.sphere((x1 - 0.10 + r * math.cos(ang), 2.55 + r * math.sin(ang), top1 + 0.12 + 0.03 * ((i * 3) % 4) / 4),
                  0.025, seg=8, rings=5)
    pp.build("Bano_Planta", [K['leaf']], smooth=True)
    # wide mirror over the wainscot, from the shower wall to the door end
    mr = MB(); mr.box(x1 - 0.012, x1 - 0.006, ys + 0.02, y1 - 0.05, wz + 0.02, Z0 + 2.12, 0)
    mr.build("Bano_Espejo", [K['mirror']])
    # one-piece WC, back to the east wall
    wc = MB(); cx, cy = x1 - 0.40, 1.45
    wc.cylinder(cx + 0.02, cy, Z0, Z0 + 0.30, 0.12, 0.10, seg=24, ry=0.15)                 # pedestal
    wc.sphere((cx - 0.02, cy, Z0 + 0.32), 0.19, seg=24, rings=12, squash=0.55)             # bowl
    wc.rbox(x1 - 0.22, x1 - 0.03, cy - 0.19, cy + 0.19, Z0 + 0.36, Z0 + 0.74, r=0.06)       # tank
    wc.blob((cx - 0.05, cy, Z0 + 0.42), 0.2, seg=32, rings=10, squash=0.12, rx=1.12, ry=0.9)    # oval seat
    wc.blob((cx - 0.05, cy, Z0 + 0.45), 0.19, seg=32, rings=10, squash=0.10, rx=1.12, ry=0.88)  # oval lid
    wc.cylinder(x1 - 0.12, cy, Z0 + 0.74, Z0 + 0.75, 0.025, seg=16, mi=1)
    wc.build("Bano_Sanitario", [K['ceramic'], K['chrome']], smooth=True)
    # shower: fixed glass with a white profile, wall-arm rain head, mixer, soap rack, drain
    sh = MB()
    sh.box(x0 + 0.50, x1 - 0.01, ys, ys + 0.008, Z0, Z0 + 2.0, 0)
    sh.box(x0 + 0.48, x0 + 0.50, ys - 0.01, ys + 0.018, Z0, Z0 + 2.0, 1)
    sh.box(x1 - 0.03, x1 - 0.01, ys - 0.01, ys + 0.018, Z0, Z0 + 2.0, 1)
    # rain head on an arm out of the grey side wall (east, same wall as the mixer), hanging toward the window (photo 6)
    hy = 0.42
    sh.tube((x1 - 0.01, hy, Z0 + 2.15), (x1 - 0.36, hy, Z0 + 2.15), 0.01, 0.01, mi=2)
    sh.tube((x1 - 0.36, hy, Z0 + 2.15), (x1 - 0.40, hy, Z0 + 2.10), 0.01, 0.01, mi=2)
    sh.cylinder(x1 - 0.42, hy, Z0 + 2.08, Z0 + 2.10, 0.11, seg=32, mi=2)
    sh.cylinder(x1 - 0.01, 0.55, Z0 + 1.05, Z0 + 1.06, 0.035, seg=20, mi=2)
    sh.box(x1 - 0.06, x1 - 0.01, 0.53, 0.57, Z0 + 1.04, Z0 + 1.07, 2)
    sh.box(x1 - 0.12, x1 - 0.01, 0.20, 0.34, Z0 + 1.15, Z0 + 1.17, 2)
    sh.cylinder((x0 + x1) / 2, 0.5, Z0, Z0 + 0.003, 0.04, seg=16, mi=3)
    sh.build("Bano_Ducha", [K['glass'], K['white'], K['black'], K['chrome']], smooth=True)
    # high window in the shower back wall with horizontal bars, and a trailing plant
    # high window: a real opening (bright sky behind) 60 x 35 cm in the top right corner, against the ceiling
    wn = MB(); wx0, wx1, wz1 = x0 + 0.10, x0 + 0.70, ZC - 0.06; wz0 = wz1 - 0.35
    wn.box(wx0, wx1, y0 - 0.01, y0 + 0.012, wz0, wz0 + 0.03, 0)
    wn.box(wx0, wx1, y0 - 0.01, y0 + 0.012, wz1 - 0.03, wz1, 0)
    wn.box(wx0, wx0 + 0.03, y0 - 0.01, y0 + 0.012, wz0, wz1, 0)
    wn.box(wx1 - 0.03, wx1, y0 - 0.01, y0 + 0.012, wz0, wz1, 0)
    for i in range(1, 5):
        z = wz0 + (wz1 - wz0) * i / 5
        wn.box(wx0, wx1, y0 + 0.012, y0 + 0.025, z - 0.008, z + 0.008, 0)
    wn.box(wx0 + 0.03, wx1 - 0.03, y0 + 0.007, y0 + 0.009, wz0 + 0.03, wz1 - 0.03, 1)      # bright opening
    wn.build("Bano_Ventana", [K['black'], K['sky']])
    lp = MB()                                         # trailing monstera hanging from the bars: stems + split leaves
    import random
    rnd = random.Random(11)
    hx, hz = wx0 + 0.30, wz0 + 0.02
    for i in range(10):
        L = rnd.uniform(0.10, 0.35); dx = rnd.uniform(-0.18, 0.18)
        tip = (hx + dx, y0 + 0.07 + rnd.uniform(0, 0.05), hz - L)
        lp.tube((hx, y0 + 0.04, hz), tip, 0.003, 0.002, seg=4, mi=0)
        lp.blob(tip, 0.05, seg=10, rings=6, squash=0.18, rx=1.0, ry=0.8, mi=0)
    lp.build("Bano_Planta_Ventana", [K['leaf']], smooth=True)
    # towel bar with a cream towel on the partition facing the vanity, mat, paper holder
    tb = MB()
    # towel bar fixed through the mirror over the vanity, cream towel hanging from it (photo 6)
    tb.tube((x1 - 0.05, 2.05, Z0 + 1.62), (x1 - 0.05, 2.45, Z0 + 1.62), 0.008, 0.008, mi=0)
    for yy in (2.05, 2.45):
        tb.box(x1 - 0.05, x1 - 0.006, yy - 0.01, yy + 0.01, Z0 + 1.61, Z0 + 1.63, 0)
    tb.box(x1 - 0.07, x1 - 0.04, 2.10, 2.40, Z0 + 1.12, Z0 + 1.63, 1)
    tb.box(3.20, 3.70, 1.12, 1.52, Z0, Z0 + 0.012, 2)
    tb.box(x0 + 0.01, x0 + 0.03, 1.55, 1.68, Z0 + 0.62, Z0 + 0.72, 3)
    tb.build("Bano_Toallero", [K['black'], K['cream_towel'], K['mat_grey'], K['chrome']])


# ------------------------------------------------------------------------------------------------ laundry / fridge
def laundry(K):
    _remove("Washer", "Fridge", "Fridge_Cabinet")
    x0, x1, y0, y1 = FRIDGE
    fr = MB()
    fr.rbox(x0 + 0.05, x1 - 0.02, y0 + 0.04, y1 - 0.04, Z0 + 0.02, Z0 + 1.72, r=0.015, mi=0)      # body
    # top freezer, big fresh-food door below with the water dispenser at mid height (photo 7)
    fr.box(x0 + 0.035, x0 + 0.05, y0 + 0.05, y1 - 0.05, Z0 + 1.235, Z0 + 1.245, 1)                # door split
    for zh0, zh1 in ((Z0 + 1.30, Z0 + 1.55), (Z0 + 0.70, Z0 + 1.15)):                             # handles
        fr.box(x0 + 0.02, x0 + 0.04, y1 - 0.10, y1 - 0.08, zh0, zh1, 2)
    fr.box(x0 + 0.04, x0 + 0.05, y1 - 0.32, y1 - 0.12, Z0 + 0.88, Z0 + 1.15, 1)                    # dispenser (left)
    fr.build("Nevera", [K['steel'], K['black'], K['steel']])
    cb = MB(); cz1 = ZC - 0.36; cz0 = cz1 - 0.60                                                   # 60 cm door, lock
    cb.box(x0, x1, y0, y1, cz0, cz1, 1)
    cb.box(x0 - 0.02, x0, y0 + 0.004, y1 - 0.004, cz0 + 0.004, cz1 - 0.004, 0)
    cb.cylinder(x0 - 0.02, y0 + 0.08, cz0 + 0.06, cz0 + 0.065, 0.012, seg=12, mi=2)
    cb.rbox(x0 + 0.05, x0 + 0.35, y0 + 0.30, y0 + 0.70, cz1, cz1 + 0.26, r=0.03, mi=3)          # red beach cooler
    cb.rbox(x0 + 0.04, x0 + 0.36, y0 + 0.29, y0 + 0.71, cz1 + 0.26, cz1 + 0.30, r=0.015, mi=1)  # its white lid
    cb.build("Nevera_Gabinete", [K['yellow'], K['white'], K['chrome'], K['red']])
    lx0, lx1, ly0, ly1 = LAUNDRY
    tl = MB()
    tl.box(lx1 - 0.008, lx1, ly0, ly1, Z0, Z0 + 1.60, 0)
    tl.build("Lavanderia_Enchape", [K['laundry_tile']])
    wm = MB(); wx0, wx1, wy0, wy1 = lx0 + 0.12, lx1 - 0.04, 0.25, 0.85
    wm.rbox(wx0, wx1, wy0, wy1, Z0 + 0.02, Z0 + 0.90, r=0.03, mi=0)                              # silver body
    wm.rbox(wx0 + 0.04, wx1 - 0.12, wy0 + 0.04, wy1 - 0.04, Z0 + 0.90, Z0 + 0.93, r=0.03, mi=1)   # dark glass lid
    wm.rbox(wx1 - 0.13, wx1, wy0, wy1, Z0 + 0.90, Z0 + 1.02, r=0.02, mi=0)                       # control panel
    wm.box(wx0 - 0.002, wx0, wy0 + 0.35, wy0 + 0.50, Z0 + 0.62, Z0 + 0.80, 2)                    # energy label
    wm.build("Lavadora", [K['steel'], K['black'], K['label']], smooth=True)


def build(M):
    K = _mats(M)
    kitchen(K)
    bathroom(K)
    laundry(K)
