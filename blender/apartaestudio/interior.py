"""Interior: floor finish, kitchen, bathroom, laundry/fridge nook, bedroom-living staging, lights.
Fixtures (kitchen, bath, appliances) follow the photos; loose furniture and decor are staging read from the photos."""
import math
from .plan import *
from archviz.mesh import *
from archviz.lights import *
from archviz.parts import *
from archviz import stagekit as sk


def build(M):
    fl = MB(); fl.box(0.0, W, 0.0, Y_WIN + 0.1, Z0 - 0.02, Z0); fl.build("Floor", [M['piso']])
    kitchen(M)
    bathroom(M)
    laundry(M)
    room(M)
    lights(M)


def kitchen(M):
    x0, x1, y0, y1 = KITCHEN
    k = MB()
    cabinet_run(k, x0, x1 - 0.02, y0, y1, Z0 + 0.1, Z0 + 0.87, mi=0, doors='Y', n=5, mi_gap=3)    # white base units
    k.box(x0 + 0.05, x1 - 0.06, y0, y1, Z0, Z0 + 0.1, 3)                                         # toe kick
    k.box(x0, x1, y0, y1, Z0 + 0.87, Z0 + 0.9, 1)                                               # grey quartz top
    k.box(x0, x0 + 0.02, y0, y1, Z0 + 0.9, Z0 + 1.5, 2)                                         # 3D tile splashback
    k.box(x0, 0.35, y0 + 0.75, y1, Z0 + 1.5, Z0 + 1.53, 0)                                      # open shelf (white)
    k.build("Kitchen", [M['white_gloss'], M['meson'], M['salpicadero'], M['black']])
    u = MB()                                                                                      # yellow uppers
    cabinet_run(u, x0, 0.35, y0, y0 + 0.75, Z0 + 1.55, ZC - 0.25, mi=0, doors='Y', n=1, mi_gap=1)
    cabinet_run(u, x0, 0.35, y0 + 0.75, y1, Z0 + 1.82, ZC - 0.25, mi=0, doors='Y', n=3, mi_gap=1)
    u.build("Kitchen_Uppers", [M['amarillo'], M['black']], bevel=0.004)
    a = MB()                                                                                      # cooktop, hood, sink, tap
    a.box(0.06, 0.56, y0 + 0.12, y0 + 0.66, Z0 + 0.9, Z0 + 0.91, 0)
    for cx, cy in ((0.2, y0 + 0.25), (0.42, y0 + 0.25), (0.2, y0 + 0.52), (0.42, y0 + 0.52)):
        a.cylinder(cx, cy, Z0 + 0.91, Z0 + 0.935, 0.045, seg=12, mi=1)
    a.box(0.0, 0.45, y0 + 0.08, y0 + 0.7, Z0 + 1.48, Z0 + 1.55, 1)                              # slim hood
    a.box(0.15, 0.5, y1 - 0.75, y1 - 0.35, Z0 + 0.86, Z0 + 0.905, 1)                            # undermount sink
    faucet(a, 0.08, y1 - 0.55, Z0 + 0.9, h=0.3, mi=0, reach=0.15, dir=(1, 0))
    a.build("Kitchen_Appliances", [M['black'], M['steel']])
    d = MB()                                                                                      # countertop dressing
    d.box(0.2, 0.24, y0 + 1.1, y0 + 1.38, Z0 + 0.9, Z0 + 1.12, 0)                               # 'Bienvenidos' frame
    potted_plant(d, 0.25, y0 + 1.55, Z0 + 0.9, pot_r=0.05, pot_h=0.08, h=0.18, mi_pot=1, mi_leaf=2, mi_stem=2, seed=3)
    d.cylinder(0.18, y0 + 1.6, Z0 + 1.53, Z0 + 1.78, 0.07, seg=12, mi=3)                        # blender on the shelf
    d.build("Kitchen_Decor", [M['black'], M['clay'], M['leaf_plant'], M['glass']])


def bathroom(M):
    """Plan: basin by the door on the east wall, WC mid-wall, shower across the far (south) end behind a glass screen."""
    x0, x1, y0, y1 = BATH
    t = MB()                                                                                      # tiled walls
    t.box(x1 - 0.01, x1, y0, y1, Z0, ZC - 0.02, 0)
    t.box(x0, x1, y0, y0 + 0.01, Z0, ZC - 0.02, 0)
    t.box(x0, x0 + 0.01, y0, 1.05, Z0, ZC - 0.02, 0)
    t.build("Bath_Tiles", [M['bano_pared']])
    v = MB()
    v.box(x1 - 0.47, x1 - 0.01, 1.95, 2.6, Z0 + 0.45, Z0 + 0.82, 0)                             # floating walnut vanity
    v.box(x1 - 0.49, x1 - 0.01, 1.93, 2.62, Z0 + 0.82, Z0 + 0.86, 1)                            # cast basin top
    basin(v, x1 - 0.26, 2.27, Z0 + 0.76, r=0.17, mi=1)
    faucet(v, x1 - 0.05, 2.27, Z0 + 0.86, h=0.18, mi=2, reach=0.1, dir=(-1, 0))
    v.box(x1 - 0.02, x1 - 0.01, 1.1, 2.65, Z0 + 1.0, Z0 + 1.9, 3)                               # long mirror
    v.build("Bath_Vanity", [M['walnut'], M['ceramic'], M['black'], M['mirror']])
    wc = MB(); wy = 1.45
    wc.cbox(x1 - 0.36, wy, Z0 + 0.2, 0.5, 0.36, 0.4, 0)
    wc.rcbox(x1 - 0.1, wy, Z0 + 0.58, 0.18, 0.4, 0.36, r=0.04, mi=0)
    wc.rcbox(x1 - 0.42, wy, Z0 + 0.42, 0.48, 0.38, 0.04, r=0.03, mi=0)
    wc.build("WC", [M['ceramic']], smooth=True)
    sh = MB()                                                                                     # shower: glass screen + rain head
    sh.box(x0 + 0.45, x1, 1.05, 1.05 + T, Z0, Z0 + 2.0, 0)
    sh.box(x0 + 0.45, x0 + 0.47, 1.04, 1.07, Z0, Z0 + 2.0, 1)
    sh.cylinder((x0 + x1) / 2, 0.45, ZC - 0.3, ZC - 0.28, 0.12, seg=24, mi=1)
    sh.tube(((x0 + x1) / 2, 0.01, ZC - 0.25), ((x0 + x1) / 2, 0.45, ZC - 0.25), 0.01, 0.01, mi=1)
    sh.build("Shower", [M['glass'], M['black']])
    bw = MB()                                                                                     # high window in the shower
    glass_wall(bw, x0 + 0.3, x1 - 0.3, -WT / 2, -WT / 2 + T, Z0 + 1.7, Z0 + 2.2, frame_w=0.03, mullions=((x0 + x1) / 2,))
    bw.build("Bath_Window", [M['glass_frost'], M['frame']])
    tw = MB(); tw.box(x0 + 0.01, x0 + 0.03, 1.6, 2.0, Z0 + 1.0, Z0 + 1.55, 0)
    tw.build("Towel", [M['linen_white']])


def laundry(M):
    x0, x1, y0, y1 = LAUNDRY
    wm = MB()                                                                                     # top-load washer
    wm.rcbox(x1 - 0.32, 0.6, Z0 + 0.45, 0.56, 0.58, 0.9, r=0.03, mi=0)
    wm.box(x1 - 0.6, x1 - 0.04, 0.32, 0.88, Z0 + 0.9, Z0 + 0.93, 1)
    wm.build("Washer", [M['white_gloss'], M['black']])
    x0, x1, y0, y1 = FRIDGE
    fr = MB()
    fr.rcbox((x0 + x1) / 2 + 0.03, (y0 + y1) / 2, Z0 + 0.85, 0.6, 0.68, 1.7, r=0.02, mi=0)
    fr.box(x0 + 0.02, x0 + 0.03, y0 + 0.08, y1 - 0.08, Z0 + 1.15, Z0 + 1.16, 1)                  # door split
    fr.box(x0 + 0.01, x0 + 0.02, y0 + 0.3, y0 + 0.45, Z0 + 0.95, Z0 + 1.1, 1)                    # water dispenser
    fr.build("Fridge", [M['steel'], M['black']])
    up = MB(); cabinet_run(up, x0, x1, y0, y1, Z0 + 1.85, ZC - 0.02, mi=0, doors='Y', n=2, mi_gap=1)
    up.build("Fridge_Cabinet", [M['amarillo'], M['black']], bevel=0.004)


def room(M):
    # bed: head on the right wall (x = W), white quilt, black palm-print runner, blue cushions, oak frame
    bx, by = W - 0.1 - 1.95 / 2, BED_Y
    b = MB(); bed(b, bx, by, rot=-math.pi / 2, z=Z0, w=1.4, l=1.95, mi_frame=0, mi_linen=1, mi_pillow=1, mi_throw=2,
                 head_h=1.1, channels=0, seed=2)
    b.build("Bed", [M['oak'], M['linen_white'], M['pie_cama']], smooth=True, bevel=0.01)
    # balcony bistro set (photos 2-3): round dark glass-top table, two folding chairs, white lantern
    bt = MB()
    round_table(bt, 0.9, 8.75, Z0, 0.3, h=0.72, top_t=0.02, mi=0, mi_leg=1, legs='three')
    for cx, rot in ((0.42, -math.pi / 2), (1.38, math.pi / 2)):
        dining_chair(bt, cx, 8.7, rot=rot, z=Z0, mi_wood=1, mi_seat=1, w=0.44, d=0.46)
    bt.cylinder(0.85, 8.65, Z0 + 0.72, Z0 + 0.94, 0.07, seg=16, mi=2)
    bt.build("Balcony_Set", [M['black_gloss'], M['metal_cafe'], M['ceramic']])
    cu = MB()
    for i, dy in enumerate((-0.33, 0.33)):
        cushion(cu, W - 0.42, by + dy, Z0 + 0.62, w=0.45, d=0.45, t=0.14, mi=0, rot=math.pi / 2, upright=True)
    cu.build("Cushions_Blue", [M['cojin_azul']])
    ns = MB()
    nightstand(ns, W - 0.25, by - 1.2, z=Z0, w=0.4, d=0.4, h=0.5, mi=0)
    ns.box(W - 0.44, W - 0.43, by - 1.35, by - 1.05, Z0 + 0.3, Z0 + 0.32, 1)
    ns.build("Nightstand", [M['white_gloss'], M['steel']])
    lm = MB(); lm.cylinder(W - 0.25, by - 1.2, Z0 + 0.5, Z0 + 0.52, 0.06, mi=0)
    lm.tube((W - 0.25, by - 1.2, Z0 + 0.52), (W - 0.3, by - 1.25, Z0 + 0.85), 0.008, 0.008, mi=0)
    lm.build("Desk_Lamp", [M['white_gloss']])
    rg = MB(); rg.box(W - 1.5, W - 0.6, by - 1.45, by - 0.95, Z0, Z0 + 0.012, 0)
    rg.build("Rug", [M['rug_blue']])
    # framed prints and floating shelf with a plant above the headboard
    p = MB()
    for (c, h) in ((by - 0.95, 0.42), (by + 0.05, 0.34), (by + 0.75, 0.42)):
        picture(p, c - 0.15, c + 0.15, W, Z0 + 1.55, Z0 + 1.55 + h, along='Y', face=-1)
    p.build("Prints", [M['black'], M['art_teal']])
    sh = MB(); sh.box(W - 0.2, W, by + 1.2, by + 1.6, Z0 + 1.5, Z0 + 1.53, 0)
    potted_plant(sh, W - 0.12, by + 1.45, Z0 + 1.53, pot_r=0.06, pot_h=0.1, h=0.3, mi_pot=1, mi_leaf=2, mi_stem=2,
                 seed=5, kind='broad')
    sh.build("Shelf_Plant", [M['white_gloss'], M['clay'], M['leaf_plant']])
    # air conditioner split high on the right wall
    ac = MB(); ac.rbox(W - 0.22, W, 3.15, 4.0, ZC - 0.42, ZC - 0.12, r=0.03, mi=0)
    ac.build("AC_Split", [M['white_gloss']])
    # desk + mesh office chair by the window (photo 5)
    dk = MB(); sk.desk(dk, W - 0.27, Y_WIN - 0.55, -math.pi / 2, 0.8, 0.45, h=0.75, mi=0, z=Z0)
    dk.build("Desk", [M['white_gloss']])
    ch = MB(); sk.office_chair(ch, W - 0.85, Y_WIN - 0.6, math.pi / 2, mi=0, mi_metal=1, z=Z0)
    ch.build("Office_Chair", [M['black'], M['black_metal']])
    # sofa bed on the left wall by the window, patterned back cushions
    so = MB(); sofa(so, 0.48, 5.72, 1.95, 0.9, rot=math.pi / 2, z=Z0, mi_seat=0, pillows=3, mi_pillow=1)
    so.build("Sofa_Bed", [M['sofa'], M['fabric_dark']], smooth=True)
    tvm = MB(); tv(tvm, 3.4, 4.2, 0.0, Z0 + 1.35, Z0 + 1.82, mi=0, along='Y', d=-0.04)
    tvm.build("TV", [M['tv']])


def lights(M):
    # room: one downlight near the window (photo 1) + one over the middle; bath: two (photo 6); corridor/kitchen: two
    pts = [(1.5, 5.8), (2.0, 3.3), (1.2, 1.2), (3.4, 1.9), (3.4, 0.6), (2.24, 0.55)]
    dl = MB(); downlights(dl, pts, ZC - 0.025, mi=0); dl.build("Downlights", [M['emit_down']])
    for (x, y) in pts:
        add_light(f"L_Down_{x:.1f}_{y:.1f}", 'SPOT', (x, y, ZC - 0.06), 14, size=0.05)
    room_light("L_Bath", 'bath', energy=8)       # the bath has no daylight beyond its small frosted window
