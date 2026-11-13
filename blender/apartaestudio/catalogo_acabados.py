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


def _juntas(m, size, grout_k=0.72, var=0.10, gap=0.0025, bump=0.25):
    """Lay the piece grid over a material: joints (grout_k x the piece colour) and a slightly different tone per
    piece, through one Brick texture in object XY.  Without it the wood-look porcelain read as a continuous plank
    floor and the 60x60 pieces did not exist (2026-11-13, A/B demo)."""
    import bpy
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(sep.inputs["Vector"], tc.outputs["Object"])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(comb.inputs["X"], sep.outputs["X"]); nt.links.new(comb.inputs["Y"], sep.outputs["Y"])
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset = 0.0
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = gap
    br.inputs["Mortar Smooth"].default_value = 0.2
    br.inputs["Brick Width"].default_value = size[0]
    br.inputs["Row Height"].default_value = size[1]
    br.inputs["Color1"].default_value = (1, 1, 1, 1)
    br.inputs["Color2"].default_value = (1 - var, 1 - var, 1 - var, 1)
    br.inputs["Mortar"].default_value = (grout_k, grout_k, grout_k, 1)
    nt.links.new(br.inputs["Vector"], comb.outputs["Vector"])
    src = b.inputs["Base Color"].links[0].from_socket if b.inputs["Base Color"].is_linked else None
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
    mx.inputs["Factor"].default_value = 1.0
    if src is not None:
        nt.links.new(mx.inputs["A"], src)
    else:
        mx.inputs["A"].default_value = tuple(b.inputs["Base Color"].default_value)
    nt.links.new(mx.inputs["B"], br.outputs["Color"])
    nt.links.new(b.inputs["Base Color"], mx.outputs["Result"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump; bp.inputs["Distance"].default_value = 0.002
    bp.invert = True                                   # joints sink
    nt.links.new(bp.inputs["Height"], br.outputs["Fac"])
    if b.inputs["Normal"].is_linked:
        nt.links.new(bp.inputs["Normal"], b.inputs["Normal"].links[0].from_socket)
    nt.links.new(b.inputs["Normal"], bp.outputs["Normal"])
    return m


def material(code, slot, pbr):
    """Blender material for a catalogue code in a given slot (walls tile on the YZ plane, floors on XY)."""
    from archviz import materials as _m
    c = CATALOGO[code]
    col = (*c["rgb"], 1.0)
    rough = 0.15 if c["acabado"] == "brillante" else 0.45
    name = f"{c['marca']}_{code}"
    if c["kind"] == "madera":
        # wood-look porcelain: scanned oak grain tinted to the swatch, with the 60x60 joints and per-piece tone
        return _juntas(pbr(name, "oak_veneer_01", col, var=0.8, rough=rough, normal=0.3, scale=0.7), c["size"])
    # grout darker than the piece (it was 0.9x + 0.08: the same colour, so light tiles showed no joints at all)
    grout = tuple(v * 0.70 for v in c["rgb"]) + (1.0,)
    plane = 'YZ' if slot != "piso" else 'XY'
    if c["kind"] == "pared":
        # glazed wall tile: a thin clear coat gives the reflections that tell it from painted plaster
        return _m.tiles(name, col, grout=(0.8, 0.8, 0.78, 1) if c["rgb"][0] < 0.3 else grout, size=c["size"],
                        gap=0.003, rough=rough, plane=plane, variation=0.04, bump=0.8,
                        coat=0.4 if c["acabado"] == "brillante" else 0.0)
    mottle = 0.45 if c["kind"] == "cemento" else 0.15
    return _m.tiles(name, col, grout=grout, size=c["size"], gap=0.003, rough=rough, plane=plane,
                    variation=0.06, mottle=mottle, bump=0.25)
