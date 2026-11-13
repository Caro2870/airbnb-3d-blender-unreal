"""Walkthrough film (bpy-free): entry -> kitchen -> alcoba -> bathroom -> balcony at sunset.  Format: archviz/filmkit.py."""
from .plan import Z0, W, Y_WIN, BED_Y

E = Z0 + 1.55                   # eye height
TITLES = dict(main="APARTAESTUDIO CON BALCÓN", sub="APARTAESTUDIO DE PLAYA", end="RESERVA TU ESTADÍA")

SHOTS = [
    dict(name='entrada', sec=5.0, lens=(16, 16), fstop=5.6, exp=0.0, caption=None, ease=(0.0, 0.6),
         wp=[((1.25, 0.3, E), (1.5, Y_WIN, Z0 + 1.2)), ((1.25, 1.3, E), (1.1, Y_WIN, Z0 + 1.1)), ((1.3, 2.3, E), (1.0, 5.5, Z0 + 1.0))]),
    dict(name='cocina', sec=5.0, lens=(16, 16), fstop=5.6, exp=0.0, caption='COCINA', ease=(0.6, 0.6),
         wp=[((1.55, 0.55, E), (0.0, 0.9, Z0 + 1.2)), ((1.5, 1.4, E), (0.0, 1.7, Z0 + 1.2)), ((1.45, 2.3, E), (0.2, 3.0, Z0 + 1.1))]),
    dict(name='habitacion', sec=6.0, lens=(16, 16), fstop=5.6, exp=0.0, caption='HABITACIÓN', ease=(0.6, 0.6),
         wp=[((1.3, 3.3, E), (3.8, BED_Y, Z0 + 0.9)), ((1.2, 4.5, E), (W, BED_Y, Z0 + 1.0)), ((1.5, 5.9, E), (3.6, 4.4, Z0 + 1.0))]),
    dict(name='bano', sec=4.0, lens=(15, 15), fstop=5.6, exp=0.3, caption='BAÑO', ease=(0.6, 0.6),
         wp=[((2.4, 3.7, E), (3.3, 1.5, Z0 + 1.0)), ((3.2, 2.95, E), (3.7, 0.6, Z0 + 0.8))]),
    dict(name='balcon', sec=7.0, lens=(16, 18), fstop=8, exp=-0.6, caption='BALCÓN CON VISTA AL MAR', ease=(0.6, 0.0),
         wp=[((2.0, 5.2, E), (2.0, 8.5, Z0 + 1.2)), ((2.55, 6.6, E), (2.45, 11.0, Z0 + 1.0)),
             ((2.75, 7.25, E), (1.0, 80.0, Z0 - 1.0)), ((3.35, 7.55, E + 0.1), (6.0, 120.0, Z0 - 2.0))]),
]
# A/B finish demo (MVP, 2026-11-13): two slow, level moves built from the sales cameras v_cuarto / v_cocina.  Rendered
# once per finish sheet (ACABADOS_FICHA, HOUSE_FILM_DIR) and cut with a wipe A -> B mid-shot (remoto/montar_ab.py).
AB_SHOTS = [
    dict(name='ab_cuarto', sec=4.0, lens=(20, 20), fstop=8, exp=0.0, caption=None, ease=(0.5, 0.5),
         wp=[((0.55, 2.80, Z0 + 1.05), (2.55, Y_WIN, Z0 + 0.55)), ((0.95, 3.30, Z0 + 1.05), (3.05, Y_WIN, Z0 + 0.50))]),
    dict(name='ab_cocina', sec=4.0, lens=(24, 24), fstop=8, exp=0.8, caption=None, ease=(0.5, 0.5),
         wp=[((1.65, 2.95, Z0 + 1.25), (0.0, 1.15, Z0 + 1.15)), ((1.52, 2.30, Z0 + 1.25), (0.0, 0.75, Z0 + 1.10))]),
]
BY_NAME = {s['name']: s for s in SHOTS + AB_SHOTS}
