"""Apartaestudio de playa — THE PLAN (bpy-free).

Dimensions from the architect's floor plan (1:20):
alcoba 4.05 x 4.35, cocina 1.78 x 2.45, labores 0.84 x 1.07, baño 1.33 x 2.75, balcón 1.09 x 4.70,
34.18 m2 private area.  Positions not dimensioned on the sheet (doors, fridge nook, closet) are read off the drawing
at 1:20; the ceiling height is assumed.  See REFERENCES.md.

Coordinates (metres): X = left(-)/right(+) as seen from the entry door looking at the window, Y = entry(0) -> balcony(+),
Z up.  The unit is one storey above grade.

PLAN (interior faces)
  unit        x 0 .. 4.05, y 0 .. 6.80, floor Z0, ceiling Z0 + 2.5
  kitchen     counter along x = 0, y 0.10 .. 2.45 (cooktop by the entry, sink toward the room)
  corridor    x 0.60 .. 1.75 (kitchen side), entry door on y = 0 at x 0.85 .. 1.70
  laundry     x 1.85 .. 2.62, y 0 .. 1.07     doorway on its west wall
  fridge nook x 1.85 .. 2.62, y 1.12 .. 1.90  yellow cabinet above, opens west to the corridor
  closet      x 1.75 .. 2.62, y 1.90 .. 2.85
  bathroom    x 2.72 .. 4.05, y 0 .. 2.75     door on its north wall into the alcoba
  alcoba      x 0 .. 4.05, y 2.45 .. 6.80     bed head on x = 4.05, window wall y = 6.80
  balcony     x 0 .. 4.05 (4.70 incl. the side return), y 6.95 .. 8.04
"""
Z0 = 3.0                       # finished floor of the unit (one 3.0 m storey above grade, assumed)
H = 2.5                        # floor-to-ceiling (assumed; not on the sheet)
ZC = Z0 + H
WT = 0.15                      # exterior wall thickness
PT = 0.10                      # partition thickness
T = 0.012                      # glass thickness

W = 4.05                       # alcoba width
Y_WIN = 6.80                   # inner face of the window wall (kitchen 2.45 + alcoba 4.35)
Y_BAL = Y_WIN + WT + 1.09      # balcony rail line

BATH = (2.72, W, 0.0, 2.75)
BATH_DOOR = (2.85, 3.55)       # on the bath's north wall (y = 2.75)
LAUNDRY = (1.85, 2.62, 0.0, 1.07)
LAUNDRY_DOOR = (0.12, 0.92)    # on the laundry's west wall (x = 1.85)
FRIDGE = (1.85, 2.62, 1.12, 1.90)
CLOSET = (1.75, 2.62, 1.90, 2.85)
ENTRY_DOOR = (0.85, 1.70)
KITCHEN = (0.0, 0.60, 0.10, 2.45)
WIN_OPEN = (1.2, 2.8)          # open sliding leaf (staging: left open so the walkthrough can step out)

BED_Y = 5.15                   # bed centre line (drawing), head on x = W
ROOMS = {
    'main':     (0.0, W, 2.45, Y_WIN, Z0, ZC),
    'corridor': (0.60, 1.75, 0.0, 2.45, Z0, ZC),
    'bath':     (BATH[0], BATH[1], BATH[2], BATH[3], Z0, ZC),
    'laundry':  (LAUNDRY[0], LAUNDRY[1], LAUNDRY[2], LAUNDRY[3], Z0, ZC),
}
