"""Envelope of the unit: exterior walls, partitions, slabs, window wall, doors, balcony and its rail."""
from .plan import *
from archviz.mesh import *
from archviz.lights import *
from archviz.parts import *


def build(M):
    # ---- exterior walls (outside faces of the 0..W x 0..Y_WIN box)
    w = MB()
    w.wall('X', -WT, W + WT, -WT, 0.0, Z0, ZC, holes=[(ENTRY_DOOR[0], ENTRY_DOOR[1], Z0, Z0 + 2.1)])     # entry wall
    w.wall('Y', -WT, Y_BAL, -WT, 0.0, Z0, ZC)                                                             # left
    w.wall('Y', -WT, Y_WIN + WT, W, W + WT, Z0, ZC)        # right: stops at the window; the balcony's east end is open (photo 2)
    # window wall: short returns either side of the full-height glazing + a header
    w.wall('X', 0.0, W, Y_WIN, Y_WIN + WT, Z0, ZC, holes=[(0.15, W - 0.15, Z0, Z0 + 2.4)])
    # ---- partitions (floor plan)
    bx0, bx1, by0, by1 = BATH
    w.wall('Y', 0.0, by1 + PT, bx0 - PT, bx0, Z0, ZC)                                                     # laundry/closet | bath
    w.wall('X', bx0 - PT, W, by1, by1 + PT, Z0, ZC, holes=[(BATH_DOOR[0], BATH_DOOR[1], Z0, Z0 + 2.1)])   # bath | alcoba
    lx0, lx1, ly0, ly1 = LAUNDRY
    w.wall('Y', 0.0, ly1, lx0 - PT, lx0, Z0, ZC, holes=[(LAUNDRY_DOOR[0], LAUNDRY_DOOR[1], Z0, Z0 + 2.1)])
    w.wall('X', lx0 - PT, lx1, ly1, ly1 + 0.05, Z0, ZC)                                                   # laundry | fridge
    w.wall('X', FRIDGE[0] - PT, FRIDGE[1], FRIDGE[2], FRIDGE[2] + 0.01, ZC - 0.35, ZC)                    # bulkhead over nook
    w.build("Walls", [M['white_int']])
    # built-in closet beside the fridge nook (white melamine, flush doors)
    cl = MB(); cabinet_run(cl, CLOSET[0], CLOSET[1], CLOSET[2], CLOSET[3], Z0, ZC - 0.02, mi=0, doors='Y', n=2, mi_gap=1)
    cl.build("Closet", [M['white_gloss'], M['black']])

    # ---- slabs: floor, ceiling, balcony (the floor tiles live in interior.py)
    s = MB()
    s.plate(-WT, W + WT, -WT, Y_WIN + WT, Z0 - 0.25, Z0 - 0.02)
    s.plate(-WT, W + WT, -WT, Y_BAL + 0.05, ZC, ZC + 0.25)
    s.plate(-WT, W + WT, Y_WIN + WT, Y_BAL + 0.05, Z0 - 0.25, Z0 - 0.02)
    s.build("Slabs", [M['fachada']])
    c = MB(); c.box(0.0, W, 0.0, Y_BAL, ZC - 0.02, ZC); c.build("Ceiling", [M['white_int']])
    fb = MB(); fb.box(0.0, W, Y_WIN + WT, Y_BAL, Z0 - 0.02, Z0); fb.build("Floor_Balcony", [M['piso_balcon']])

    # ---- window wall: fixed panes either side of the open sliding leaf; the leaf is parked behind the right pane
    g = MB()
    yg = Y_WIN + 0.05
    glass_wall(g, 0.15, WIN_OPEN[0], yg, yg + T, Z0, Z0 + 2.4, frame_w=0.05)
    glass_wall(g, WIN_OPEN[1], W - 0.15, yg, yg + T, Z0, Z0 + 2.4, frame_w=0.05)
    glass_wall(g, WIN_OPEN[1] - 0.05, W - 0.2, yg + 0.06, yg + 0.06 + T, Z0, Z0 + 2.4, frame_w=0.05)
    g.box(0.15, W - 0.15, yg - 0.04, yg + 0.1, Z0, Z0 + 0.03, 1)                     # track
    g.box(0.15, W - 0.15, yg - 0.04, yg + 0.1, Z0 + 2.37, Z0 + 2.4, 1)               # head
    g.build("Glazing", [M['glass'], M['frame']])
    # roller blind, half lowered as in photo 1
    rb = MB()
    rb.box(0.15, W - 0.15, Y_WIN - 0.12, Y_WIN - 0.02, ZC - 0.14, ZC - 0.02)          # cassette
    rb.box(0.2, W - 0.2, Y_WIN - 0.08, Y_WIN - 0.07, Z0 + 1.85, ZC - 0.14)            # fabric
    rb.build("Roller_Blind", [M['cortina']])

    # ---- doors: entry (closed), bathroom (open against the bath wall), laundry doorway left open
    d = MB()
    door_leaf(d, ENTRY_DOOR[0], ENTRY_DOOR[1], -WT / 2, Z0, Z0 + 2.1)
    door_leaf(d, BATH[3] - 0.70, BATH[3], BATH_DOOR[0] - 0.03, Z0, Z0 + 2.1, along='Y')   # swung into the bath
    d.build("Doors", [M['puerta_madera']])
    f = MB()
    door_frame(f, ENTRY_DOOR[0], ENTRY_DOOR[1], -WT / 2, Z0, Z0 + 2.1, w=0.05, d=WT + 0.02)
    door_frame(f, BATH_DOOR[0], BATH_DOOR[1], BATH[3] + PT / 2, Z0, Z0 + 2.1, w=0.05, d=0.12)
    door_frame(f, LAUNDRY_DOOR[0], LAUNDRY_DOOR[1], LAUNDRY[0] - PT / 2, Z0, Z0 + 2.1, w=0.05, d=0.12, along='Y')
    f.build("Door_Frames", [M['white_gloss']])

    # ---- balcony: glass rail on the outer edge, side walls are the neighbours' party walls (shell walls above)
    r = MB()
    glass_rail(r, [(0.0, Y_BAL - 0.05), (W - 0.05, Y_BAL - 0.05), (W - 0.05, Y_WIN + WT)], Z0, h=1.05)   # returns at the east end
    r.build("Balcony_Rail", [M['glass'], M['frame']])
    # balcony ceiling downlight (photo 3)
    bl = MB(); downlights(bl, [(W / 2, (Y_WIN + Y_BAL) / 2)], ZC - 0.005, mi=0); bl.build("Balcony_Downlight", [M['emit_down']])
