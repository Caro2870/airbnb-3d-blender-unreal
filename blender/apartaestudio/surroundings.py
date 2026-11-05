"""Context seen through the window and from the balcony: the rest of the block (balcony rhythm above/below and to the
sides), the street, low neighbouring buildings and the sea on the horizon (photos 2-3).  All of it is inferred."""
from .plan import *
from archviz.mesh import *
from archviz.parts import *

FLOOR = 3.0                    # storey height of the block


def build(M):
    # the block itself: mass behind the unit's facade, one bay = one unit width
    b = MB()
    b.box(-4 * W, -WT, -12.0, Y_WIN + WT, 0.0, Z0 + 3 * FLOOR)          # left of the unit
    b.box(-WT, W + WT, -12.0, Y_WIN + WT, 0.0, Z0 - 0.25)               # below
    b.box(-WT, W + WT, -12.0, Y_WIN + WT, ZC + 0.25, Z0 + 3 * FLOOR)    # above
    b.box(-WT, W + WT, -12.0, -WT, Z0 - 0.25, ZC + 0.25)                # behind (corridor side)
    b.build("Block", [M['fachada']], coll='Site')
    # balcony slabs + rails for every other bay and floor
    s = MB(); r = MB()
    for i in range(-4, 1):           # the unit is the east end of its wing (photos 2-3): bays only to the west
        for k in range(-3, 3):
            if i == 0 and k == 0:
                continue
            x0, z = i * (W + WT), Z0 + k * FLOOR
            if z < 2.0:
                continue
            s.box(x0 - WT, x0 + W + WT, Y_WIN + WT, Y_BAL + 0.05, z - 0.25, z)
            glass_rail(r, [(x0, Y_BAL - 0.05), (x0 + W, Y_BAL - 0.05)], z, h=1.05)
            s.box(x0 + 0.15, x0 + W - 0.15, Y_WIN + 0.05, Y_WIN + 0.06, z, z + 2.4)
    # the tower's other wing, perpendicular, ~7 m east of the balcony end: white facade facing the unit with windows
    # and stacked glass-railed balconies (photos 2-3); closer than that it read as a wall right behind the table
    WX = W + 7.0
    wing = MB()
    # it only fills the right (south-east) half of the view from the table; to the north-east the view is open
    wing.box(WX, WX + 12.0, -14.0, Y_BAL + 1.2, 0.0, Z0 + 3 * FLOOR)
    wing.build("Torre_Ala", [M['fachada']], coll='Site')
    wwin = MB()
    for k in range(-1, 3):
        z = Z0 + k * FLOOR
        if z < 0.5:
            continue
        for y0 in (Y_WIN - 10.5, Y_WIN - 8.0, Y_WIN - 1.6, Y_WIN - 0.2):
            wwin.box(WX - 0.02, WX + 0.02, y0, y0 + 1.0, z + 0.4, z + 2.3, 0)       # dark window
            wwin.box(WX - 0.06, WX, y0 - 0.04, y0 + 1.04, z + 0.36, z + 0.4, 1)      # sill
            wwin.box(WX - 0.04, WX, y0 + 0.48, y0 + 0.52, z + 0.4, z + 2.3, 1)       # mullion
    wwin.build("Torre_Ala_Ventanas", [M['tv'], M['white_gloss']], coll='Site')
    for k in range(0, 3):                                                      # its balconies, stacked (photo 3)
        z = Z0 + k * FLOOR
        for y0 in (Y_WIN - 6.2, Y_WIN - 3.0):
            s.box(WX - 1.1, WX, y0, y0 + 2.6, z - 0.22, z)
            glass_rail(r, [(WX, y0), (WX - 1.1, y0), (WX - 1.1, y0 + 2.6), (WX, y0 + 2.6)], z, h=1.05)
    # grey multi-storey parking deck across the drive to the north-east (photos 2-3): open floors on columns
    pd = MB()
    px0, px1, py0, py1 = W + 5.0, W + 34.0, Y_BAL + 9.0, Y_BAL + 24.0
    for zf in (0.0, 2.6):                                                        # two low decks: the sea shows above
        pd.box(px0, px1, py0, py1, zf, zf + 0.3)
        pd.box(px0, px1, py0 - 0.05, py0 + 0.15, zf + 0.3, zf + 1.0)             # parapet facing the unit
    for x in range(int(px0), int(px1) + 1, 6):
        for y in (py0 + 0.3, py1 - 0.3):
            pd.box(x - 0.25, x + 0.25, y - 0.25, y + 0.25, 0.0, 2.6)
    pd.build("Parqueadero", [M['concrete']], coll='Site')
    s.build("Block_Balconies", [M['fachada']], coll='Site')
    r.build("Block_Rails", [M['glass'], M['frame']], coll='Site')
    # ground, street, parking, low buildings, sea
    # photo 3: rust-brown interlocking pavers with yellow bay lines in the lot below, grey asphalt drive, then a wide
    # green field before the sea (it was all pale concrete before, which flattened the view)
    from archviz import materials as _mm
    pavers = _mm.tiles("Adoquin_Cafe", (0.26, 0.15, 0.10, 1), grout=(0.20, 0.17, 0.14, 1), size=(0.2, 0.1),
                       gap=0.004, rough=0.85, variation=0.15, mottle=0.4, bump=0.3, offset=0.5)
    grass = _mm.new_mat("Potrero", (0.20, 0.30, 0.10, 1), rough=0.95)
    yellow = _mm.new_mat("Linea_Amarilla", (0.80, 0.62, 0.08, 1), rough=0.7)
    g = MB(); g.box(-200, 200, -100, 60, -0.3, 0.0); g.build("Ground", [grass], coll='Site')
    st = MB(); st.box(-200, 200, 16.0, 26.0, 0.0, 0.02); st.build("Street", [M['asphalt']], coll='Site')
    pk = MB(); pk.box(-20, 25, Y_BAL + 1.0, 15.5, 0.0, 0.03); pk.build("Parking", [pavers], coll='Site')
    ln = MB()
    for x in range(-18, 25, 3):                                                     # parking bay lines
        ln.box(x - 0.05, x + 0.05, Y_BAL + 2.5, Y_BAL + 7.3, 0.03, 0.035)
    ln.box(-20, 25, Y_BAL + 7.3, Y_BAL + 7.4, 0.03, 0.035)
    ln.build("Lineas_Parqueo", [yellow], coll='Site')
    # (no generic low blocks toward the sea: the photos show open grass field all the way to the water)
    gr = MB(); gr.box(-200, 200, 48, 60, 0.0, 0.05); gr.build("Seafront", [M['lawn']], coll='Site')
    sea = MB(); sea.box(-2000, 2000, 60, 3000, -0.4, -0.05); sea.build("Sea", [M['mar']], coll='Site')
