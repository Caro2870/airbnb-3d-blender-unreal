"""Finish catalogue by manufacturer code (MVP) and the per-project finish sheet ("ficha") that points rooms at codes.

The products are real Celima (Peru) items from its public 2025 catalogue: code, name, size and finish are copied from
it; the codes were read from the PDF text next to each swatch and must be confirmed against the product sheet before a
client delivery (marked `verificar`). Colours are read from the catalogue swatches. The textures are CC0 look-alikes
(Poly Haven scans or procedural tiles) tinted to that colour at the product's real size: the manufacturer's own
images are not redistributed. To swap a discontinued finish, change its code in the ficha.
"""
import json
import os

FUENTE = "https://celima-trebol.com/wp-content/uploads/2025/05/CELIMA_Catalogo-2025.pdf"

# code -> product. kind: 'madera' (wood-look plank, scanned oak grain), 'cemento' (concrete-look), 'mate'
# (plain matte), 'pared' (wall tile). size = (w, h) of one piece in metres. rgb = swatch colour (linear-ish 0..1).
CATALOGO = {
    "110015675": dict(marca="Celima", producto="Piso Madera Fashion Cerezo Beige", formato="60x60", acabado="mate",
                      kind="madera", size=(0.6, 0.6), rgb=(0.56, 0.50, 0.42), pagina=20, verificar=False),
    "110015677": dict(marca="Celima", producto="Piso Cerezo Café", formato="60x60", acabado="mate",
                      kind="madera", size=(0.6, 0.6), rgb=(0.40, 0.32, 0.25), pagina=19, verificar=True),
    "110015679": dict(marca="Celima", producto="Piso Cerezo Gris", formato="60x60", acabado="mate",
                      kind="madera", size=(0.6, 0.6), rgb=(0.62, 0.61, 0.58), pagina=19, verificar=True),
    "110012932": dict(marca="Celima", producto="Piso Concreto Blanco", formato="60x60", acabado="mate",
                      kind="cemento", size=(0.6, 0.6), rgb=(0.84, 0.84, 0.82), pagina=21, verificar=True),
    "110012936": dict(marca="Celima", producto="Piso Concreto Gris", formato="60x60", acabado="mate",
                      kind="cemento", size=(0.6, 0.6), rgb=(0.55, 0.54, 0.51), pagina=21, verificar=True),
    "110012918": dict(marca="Celima", producto="Piso Mate Plata", formato="60x60", acabado="mate",
                      kind="mate", size=(0.6, 0.6), rgb=(0.66, 0.66, 0.65), pagina=23, verificar=True),
    "110017507": dict(marca="Celima", producto="Pared Tropic New II White (estructurado)", formato="30x60",
                      acabado="brillante", kind="pared", size=(0.6, 0.3), rgb=(0.90, 0.90, 0.89), pagina=77,
                      verificar=True),
    "110017429": dict(marca="Celima", producto="Pared Brick New Black", formato="30x60", acabado="brillante",
                      kind="pared", size=(0.6, 0.3), rgb=(0.05, 0.05, 0.055), pagina=78, verificar=True),
}

# the unit's slots a sheet may set; anything left out keeps the photographed finish. (The bathroom walls are built in
# detalles.py with their own tiles; wiring a 'bano_pared' slot there is the next step.)
SLOTS = ("piso", "cocina_pared")


def leer_ficha():
    """The project sheet from ACABADOS_FICHA (a JSON file {slot: code}), or None."""
    p = os.environ.get("ACABADOS_FICHA")
    if not p:
        return None
    with open(p, encoding="utf-8") as f:
        ficha = json.load(f)
    for slot, code in ficha.items():
        if slot not in SLOTS:
            raise ValueError(f"ficha: unknown slot {slot!r}, use {SLOTS}")
        if code not in CATALOGO:
            raise ValueError(f"ficha: code {code} for {slot} is not in the catalogue")
    return ficha


def material(code, slot, pbr):
    """Blender material for a catalogue code in a given slot (walls tile on the YZ plane, floors on XY)."""
    from archviz import materials as _m
    c = CATALOGO[code]
    col = (*c["rgb"], 1.0)
    rough = 0.15 if c["acabado"] == "brillante" else 0.45
    name = f"{c['marca']}_{code}"
    if c["kind"] == "madera":
        # wood-look porcelain: scanned oak grain tinted to the swatch, with the 60x60 joints drawn over it
        return pbr(name, "oak_veneer_01", col, var=0.8, rough=rough, normal=0.3, scale=0.7)
    grout = tuple(min(1.0, v * 0.9 + 0.08) for v in c["rgb"]) + (1.0,)
    plane = 'YZ' if slot != "piso" else 'XY'
    if c["kind"] == "pared":
        return _m.tiles(name, col, grout=(0.8, 0.8, 0.78, 1) if c["rgb"][0] < 0.3 else grout, size=c["size"],
                        gap=0.002, rough=rough, plane=plane, variation=0.03, bump=0.4)
    mottle = 0.45 if c["kind"] == "cemento" else 0.15
    return _m.tiles(name, col, grout=grout, size=c["size"], gap=0.002, rough=rough, plane=plane,
                    variation=0.05, mottle=mottle, bump=0.15)
