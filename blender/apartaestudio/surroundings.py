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
    # grey multi-storey parking deck across the drive to the north-east (photo 2): two storeys + roof deck, solid
    # spandrels and lintels with long horizontal openings between piers every 6 m, parapet on the roof
    pd = MB()
    px0, px1, py0, py1 = W + 5.0, W + 34.0, Y_BAL + 9.0, Y_BAL + 24.0
    LV = 3.0                                                                     # storey height of the deck
    for k in range(3):                                                           # slabs: ground, first, roof
        z = k * LV
        pd.box(px0, px1, py0, py1, z, z + 0.3)
    pd.box(px0, px1, py0, py0 + 0.2, 2 * LV + 0.3, 2 * LV + 1.2)                 # roof parapet facing the unit
    pd.box(px0, px0 + 0.2, py0, py1, 2 * LV + 0.3, 2 * LV + 1.2)
    for k in range(2):                                                           # each storey's facades
        z = k * LV + 0.3
        for (a0, a1, b0, b1) in ((px0, px1, py0, py0 + 0.25), (px0, px0 + 0.25, py0, py1)):
            pd.box(a0, a1, b0, b1, z, z + 0.95)                                  # spandrel (car barrier)
            pd.box(a0, a1, b0, b1, z + 2.25, z + LV - 0.3)                       # lintel / slab edge band
    for x in range(int(px0), int(px1) + 1, 6):                                   # piers on the long facade
        pd.box(x - 0.3, x + 0.3, py0, py0 + 0.45, 0.0, 2 * LV + 0.3)
    for y in range(int(py0), int(py1) + 1, 6):                                   # piers on the short facade
        pd.box(px0, px0 + 0.45, y - 0.3, y + 0.3, 0.0, 2 * LV + 0.3)
    for x in range(int(px0) + 6, int(px1), 6):                                   # interior columns (shadowed)
        for y in (py0 + 5.0, py0 + 10.0):
            pd.box(x - 0.25, x + 0.25, y - 0.25, y + 0.25, 0.0, 2 * LV)
    from archviz import materials as _mc
    gris = _mc.new_mat("Concreto_Parqueo", (0.40, 0.40, 0.38, 1), rough=0.9)   # photo 2: weathered grey, not white
    _weather(gris)
    pd.build("Parqueadero", [gris], coll='Site')
    s.build("Block_Balconies", [M['fachada']], coll='Site')
    r.build("Block_Rails", [M['glass'], M['frame']], coll='Site')
    # ground, street, parking, low buildings, sea
    # photo 3: rust-brown interlocking pavers with yellow bay lines in the lot below, grey asphalt drive, then a wide
    # green field before the sea (it was all pale concrete before, which flattened the view)
    from archviz import materials as _mm
    pavers = _mm.tiles("Adoquin_Cafe", (0.26, 0.15, 0.10, 1), grout=(0.20, 0.17, 0.14, 1), size=(0.2, 0.1),
                       gap=0.004, rough=0.85, variation=0.15, mottle=0.4, bump=0.3, offset=0.5)
    grass = _dry_field("Pasto_Explanada")    # photos 2-3: light olive grass field to the sea, patchy, not flat neon
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
    gr = MB(); gr.box(-200, 200, 48, 60, 0.0, 0.05); gr.build("Seafront", [grass], coll='Site')
    sea = MB(); sea.box(-2000, 2000, 60, 3000, -0.4, -0.05); sea.build("Sea", [M['mar']], coll='Site')
    # street lights along the drive (photo 2: a tall grey pole beside the parking deck)
    lp = MB()
    for x in range(-15, 30, 12):
        lp.cylinder(x, 15.8, 0.0, 7.5, 0.07, 0.05, seg=12)
        lp.box(x - 0.05, x + 0.05, 15.8 - 1.2, 15.8, 7.4, 7.5)
        lp.box(x - 0.12, x + 0.12, 14.55, 14.85, 7.3, 7.42)
    lp.build("Postes_Luz", [M['steel']], coll='Site')
    _aerial_haze()


HAZE_COLOR = (0.78, 0.80, 0.82)   # pale, slightly blue-grey: the horizon in photo 2 is milky
HAZE_DIST = 350.0                 # metres for ~63 % haze; the parking deck (10-35 m) stays clear, the sea melts


def _dry_field(name):
    """Dry scrub ground: two tan/olive tones in large patches + fine speckle and bump; read from 10 m to 2 km."""
    import bpy
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.95
    big = nt.nodes.new("ShaderNodeTexNoise"); big.inputs["Scale"].default_value = 0.02; big.inputs["Detail"].default_value = 6
    fine = nt.nodes.new("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 3.0; fine.inputs["Detail"].default_value = 8
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.13, 0.17, 0.07, 1)     # darker grass patches
    ramp.color_ramp.elements[1].color = (0.30, 0.35, 0.16, 1)     # light olive grass (photo 3), never neon
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.38, 0.62
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
    ca = next(i for i in mix.inputs if i.name == "A" and i.type == 'RGBA')
    cb = next(i for i in mix.inputs if i.name == "B" and i.type == 'RGBA')
    fac = next(i for i in mix.inputs if i.name == "Factor" and i.type == 'VALUE'); fac.default_value = 0.35
    out = next(o for o in mix.outputs if o.name == "Result" and o.type == 'RGBA')
    nt.links.new(big.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], ca)
    nt.links.new(fine.outputs["Color"], cb)
    nt.links.new(out, b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.3
    nt.links.new(fine.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def _aerial_haze():
    """Aerial perspective on everything outside (collection 'Site'): mix each surface toward a pale emission by view
    distance, 1 - exp(-d / HAZE_DIST).  Cheap (no volume) and the interior is untouched: at 5 m the mix is ~1 %."""
    import bpy
    site = bpy.data.collections.get("Site")
    if site is None:
        return
    mats = {s.material for o in site.all_objects for s in getattr(o, "material_slots", []) if s.material}
    for m in mats:
        if not m.use_nodes or m.get("bruma"):
            continue
        nt = m.node_tree
        outn = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputMaterial" and n.is_active_output), None)
        if outn is None or not outn.inputs["Surface"].is_linked:
            continue
        surf = outn.inputs["Surface"].links[0].from_socket
        cam = nt.nodes.new("ShaderNodeCameraData")
        div = nt.nodes.new("ShaderNodeMath"); div.operation = 'DIVIDE'; div.inputs[1].default_value = -HAZE_DIST
        ex = nt.nodes.new("ShaderNodeMath"); ex.operation = 'EXPONENT'
        inv = nt.nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (*HAZE_COLOR, 1); em.inputs["Strength"].default_value = 1.0
        mx = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(cam.outputs["View Distance"], div.inputs[0])
        nt.links.new(div.outputs["Value"], ex.inputs[0])
        nt.links.new(ex.outputs["Value"], inv.inputs[1])
        nt.links.new(inv.outputs["Value"], mx.inputs["Fac"])
        nt.links.new(surf, mx.inputs[1])
        nt.links.new(em.outputs["Emission"], mx.inputs[2])
        nt.links.new(mx.outputs["Shader"], outn.inputs["Surface"])
        m["bruma"] = True


def _weather(m):
    """Stains and value variation on a flat concrete colour (large noise multiplied in): reads as weathered."""
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    base = tuple(b.inputs["Base Color"].default_value)
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.6; nz.inputs["Detail"].default_value = 8
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = tuple(c * 0.7 for c in base[:3]) + (1,)
    ramp.color_ramp.elements[1].color = tuple(min(c * 1.15, 1) for c in base[:3]) + (1,)
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
