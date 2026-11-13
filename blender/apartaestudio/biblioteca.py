"""Telas y decoración de biblioteca (BlenderKit, licencia libre de regalías; ver CONTINUAR.md 6c) en lugar de las
generadas por código.  El código sigue mandando en arquitectura, acabados y la base de roble de la cama.

Lee assets/blenderkit/biblioteca.blend (bajado con remoto/bk_descargar.py; NO se redistribuye: queda fuera del repo
público).  BIBLIO=0 lo apaga para el render "antes".  Corre al final de MODULES, después de imperfecciones, para que
los modelos no reciban el desplazamiento ni el bisel procedurales.

Piezas:
- Cama: textiles del modelo "Double Bed" (Russo 3D): edredón, sábana, manta al pie y 2 almohadas, sobre su colchón
  (1,40 x 1,90 -> escalado a 1,95), girado para que la cabecera quede en x = HX.  Sin su base ni patas.
- Cabecero: el tapizado del mismo modelo (Wall_Fabric), teñido al color del paquete de acabados.
- Cojines azules de la foto 5: "Blue velvet button cushion B", de pie contra las almohadas.
- Sofá: los 2 almohadones oliva pasan a "Linen rustic pillow-01" teñido oliva.
- Cortinas: "Gray linen curtain" (solo el lino), un paño recogido a cada lado de la ventana (staging, no en fotos).
- Monstera: descargada pero sin colocar (ningún rincón libre para 1,2 m de ancho; ver _monstera).
"""
import math
import os

import bpy
from mathutils import Matrix, Vector

from .plan import *
from .house import ASSETS
from .muebles import HX, FX, BED_L, BED_W, MATT_Z1

LIB = os.path.join(ASSETS, "blenderkit", "biblioteca.blend")
LIB_SOFA = os.path.join(ASSETS, "blenderkit", "sofa.blend")      # "Teddy sofa" (Joris LM), aprobado después

# paleta de las fotos (igual que muebles._mats)
BLANCO_COLCHA = (0.86, 0.86, 0.84)
SABANA = (0.66, 0.57, 0.42)            # sábana caqui bajo la colcha (foto 1)
BLANCO_ALMOHADA = (0.90, 0.90, 0.88)
AZUL_CAMINO = (0.26, 0.36, 0.50)
AZUL_COJIN = (0.36, 0.455, 0.625)      # medido en la foto 5 contra la colcha de al lado: cojín/colcha 0,62 (el render daba 0,80)
OLIVA = (0.055, 0.06, 0.04)            # era (0,13, 0,15, 0,09): medido en la foto 1
BEIGE_MANTA = (0.90, 0.70, 0.42)       # era (0,86, 0,68, 0,50): la foto la da algo más amarilla
CAFE_SOFA = (0.17, 0.12, 0.085)        # 1ª pasada (0,10, 0,075, 0,055) quedó más oscuro que la foto
ESTAMPADO_SOFA = (0.45, 0.42, 0.30)

CAMA_QUITAR = ("Cama_Colcha", "Cama_Camino", "Cama_Almohada", "Cama_Cojin", "Cama_Colchon")   # towel kept: _towel
SOFA_QUITAR = ("Sofa_Almohadon",)


def _remove_prefix(prefixes):
    for ob in [o for o in bpy.data.objects if o.name.startswith(prefixes)]:
        bpy.data.objects.remove(ob, do_unlink=True)


def _load(coll, path=None):
    """Append every object of the library into coll; returns {original name: new object}.  They are linked and the
    view layer updated before anything reads matrix_world (fresh objects carry stale parent transforms)."""
    with bpy.data.libraries.load(path or LIB, link=False) as (src, dst):
        names = [str(n) for n in src.objects]
        dst.objects = list(names)       # Blender swaps the names for objects in place in the list it is given
    L = {n: o for n, o in zip(names, dst.objects) if o is not None}
    for o in L.values():
        coll.objects.link(o)
        o.hide_viewport = False                    # ray casts (_settle) only see objects visible in the view layer
        o.hide_set(False)
    bpy.context.view_layer.update()
    return L


KEPT = set()
SOFA = []


def _keep(objs, coll):
    """Unparent (keeping the world transform) and mark as used."""
    for o in objs:
        KEPT.add(o)
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
        if o.name not in coll.objects:
            coll.objects.link(o)


def _place(objs, M_):
    for o in objs:
        o.matrix_world = M_ @ o.matrix_world


def _image_source(sock, depth=0):
    """Follow a colour chain (ramps, HSV, mixes...) back to the first image texture: (its Color socket, image)."""
    node = sock.node
    if node.bl_idname == "ShaderNodeTexImage" and node.image is not None and node.image.size[0] > 0:
        return node.outputs["Color"], node.image
    if depth > 6:
        return None, None
    for i in node.inputs:
        if i.is_linked and i.type in ('RGBA', 'VALUE'):
            out = _image_source(i.links[0].from_socket, depth + 1)
            if out[0] is not None:
                return out
    return None, None


def _mean_lum(img):
    import numpy as np
    px = np.empty(img.size[0] * img.size[1] * img.channels, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(-1, img.channels)[::97, :3]
    if img.colorspace_settings.name == 'sRGB' and not img.is_float:
        px = px ** 2.2                                   # byte pixels come sRGB-encoded; the shader sees linear
    return float(max((px @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)).mean(), 0.02))


def _tint(mat, rgb, strength=0.6):
    """Recolour to a photographed colour.  If an image texture feeds Base Color (through any ramp/HSV chain), use
    its luminance as detail around the target: base = rgb * (1 - s + s * lum / mean).  Otherwise (procedural or a
    flat ramp) set the colour directly; bump and roughness stay as the author made them."""
    if mat is None or not mat.use_nodes:
        return
    nt = mat.node_tree
    for b in [n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"]:
        inp = b.inputs["Base Color"]
        src, img = (_image_source(inp.links[0].from_socket) if inp.is_linked else (None, None))
        if src is None:
            for l in list(inp.links):
                nt.links.remove(l)
            inp.default_value = (*rgb, 1)
            print(f"[biblioteca] tinte {mat.name}: color plano")
            continue
        mean = _mean_lum(img)
        print(f"[biblioteca] tinte {mat.name}: textura {img.name}, brillo medio {mean:.2f}")
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        ma = nt.nodes.new("ShaderNodeMath"); ma.operation = 'MULTIPLY_ADD'; ma.use_clamp = False
        ma.inputs[1].default_value = strength / mean
        ma.inputs[2].default_value = 1.0 - strength
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        # ShaderNodeMix has float/vector/colour sockets with the same names: pick the RGBA ones
        ca = next(i for i in mix.inputs if i.name == "A" and i.type == 'RGBA')
        cb = next(i for i in mix.inputs if i.name == "B" and i.type == 'RGBA')
        out = next(o for o in mix.outputs if o.name == "Result" and o.type == 'RGBA')
        next(i for i in mix.inputs if i.name == "Factor" and i.type == 'VALUE').default_value = 1.0
        ca.default_value = (*rgb, 1)
        nt.links.new(src, bw.inputs["Color"])
        nt.links.new(bw.outputs["Val"], ma.inputs[0])
        nt.links.new(ma.outputs["Value"], cb)
        nt.links.new(out, inp)


def _tint_obj(o, rgb, own=True, strength=0.6):
    """Tint the object's materials; own=True copies them first so other users keep their colour."""
    for slot in o.material_slots:
        if slot.material is None:
            continue
        if own:
            slot.material = slot.material.copy()
        _tint(slot.material, rgb, strength=strength)


def _bed(L, coll):
    parts = {n: L[n] for n in ("Cube.009", "Plane.015", "Plane.016", "Plane.017", "Plane.018", "Plane.021") if n in L}
    _keep(parts.values(), coll)
    # model: head toward +Y, mattress 1.40 x 1.90 centred on the origin, top at z = 0.42
    k = BED_L / 1.90
    rot = Matrix.Rotation(math.radians(-90), 4, 'Z')                      # +Y (head) -> +X
    cx = (FX + HX) / 2
    M_ = Matrix.Translation((cx, BED_Y, MATT_Z1 - 0.42)) @ rot @ Matrix.Diagonal((BED_W / 1.40, k, 1.0, 1.0))
    _place(parts.values(), M_)
    # photo 1: white quilted duvet over a khaki sheet; the sheet shows along the side below the duvet's short drop
    if "Plane.016" in parts:
        _tint_obj(parts["Plane.016"], BLANCO_COLCHA)
    for n in ("Plane.015", "Cube.009"):                                    # sábana y colchón (la sábana ajustable)
        if n in parts:
            _tint_obj(parts[n], SABANA)
    if "Plane.016" in parts:
        for slot in parts["Plane.016"].material_slots:
            _quilting(slot.material)
    # Photo 5 (close-up): white quilted shams, horizontal stitch lines every ~4 cm and a fine crinkle all over.
    # The model's own texture gave a grey mottle (terrazzo-like) and a darker pillow: little of it is kept (0.12).
    for n in ("Plane.017", "Plane.018"):                                   # almohadas
        if n in parts:
            _tint_obj(parts[n], BLANCO_ALMOHADA, strength=0.12)
            for slot in parts[n].material_slots:
                _quilting_pillow(slot.material)
    if "Plane.021" in parts:                                              # manta al pie: el azul del camino
        _tint_obj(parts["Plane.021"], AZUL_CAMINO)
    # photo 5: the bedspread ends at the mattress bottom and the wooden frame shows; the model's duvet fell to 10 cm
    # off the floor and 23 cm past the foot (remoto/sonda_colcha.py).  Sheet tucked 3 cm higher so it stays hidden.
    # hem above the oak base top (Z0 + 0.33): at 0.30 the pulled-in foot drop ended inside the rail and its folds
    # poked through the wood as white shards at the foot corner (photo 5)
    for n, hem in (("Plane.016", Z0 + 0.345), ("Plane.015", Z0 + 0.36)):
        if n in parts:
            _hem(parts[n], hem)
    if "Plane.015" in parts:
        _flat_sheet(parts["Plane.015"])
    if "Plane.016" in parts:
        _tuck(parts["Plane.016"])
        _smooth_drop(parts["Plane.016"])
    return parts


def _quilting(mat, period=0.04):
    """Photo 5 at full resolution: the bedspread is quilted with stitch lines ALONG the bed (head to foot) every
    ~4 cm; they run down the foot drop as vertical lines and the side drops stay plain.  So the grooves are a
    function of world Y (constant along X).  They are nearly straight (+-2 mm wander), with a cross seam every
    65 cm.  (Until 2026-11-11 they ran across the bed, wavy, with lengthwise seams: the user caught it.)
    Shaped as narrow grooves between broad puffs: |sin|^0.35."""
    if mat is None or not mat.use_nodes:
        return
    nt = mat.node_tree
    b = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if b is None:
        return
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Position"], sep.inputs["Vector"])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = math.pi / period
    wy = nt.nodes.new("ShaderNodeMath"); wy.operation = 'MULTIPLY'; wy.inputs[1].default_value = 2 * math.pi / 0.25
    nt.links.new(sep.outputs["X"], wy.inputs[0])
    ws = nt.nodes.new("ShaderNodeMath"); ws.operation = 'SINE'; nt.links.new(wy.outputs["Value"], ws.inputs[0])
    wx = nt.nodes.new("ShaderNodeMath"); wx.operation = 'MULTIPLY_ADD'; wx.inputs[1].default_value = 0.002
    nt.links.new(ws.outputs["Value"], wx.inputs[0]); nt.links.new(sep.outputs["Y"], wx.inputs[2])
    nt.links.new(wx.outputs["Value"], mul.inputs[0])
    sn = nt.nodes.new("ShaderNodeMath"); sn.operation = 'SINE'; nt.links.new(mul.outputs["Value"], sn.inputs[0])
    ab = nt.nodes.new("ShaderNodeMath"); ab.operation = 'ABSOLUTE'; nt.links.new(sn.outputs["Value"], ab.inputs[0])
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 0.35   # narrow dips
    nt.links.new(ab.outputs["Value"], pw.inputs[0])
    bump = nt.nodes.new("ShaderNodeBump")
    # Amounts from remoto/textura_objetos.py (photo 5): 12 mm relief + 14 % darker grooves overshot (3.3 % at 8 px
    # against 0.95 %) and read as a striped cloth; 6 mm + 4 % is close.
    so = nt.nodes.new("ShaderNodeMath"); so.operation = 'ADD'; so.inputs[1].default_value = -(FX + 0.02)
    nt.links.new(sep.outputs["X"], so.inputs[0])
    sy = nt.nodes.new("ShaderNodeMath"); sy.operation = 'MULTIPLY'; sy.inputs[1].default_value = math.pi / 0.65
    nt.links.new(so.outputs["Value"], sy.inputs[0])                      # cross seams every 65 cm from the foot edge
    ss = nt.nodes.new("ShaderNodeMath"); ss.operation = 'SINE'; nt.links.new(sy.outputs["Value"], ss.inputs[0])
    sa = nt.nodes.new("ShaderNodeMath"); sa.operation = 'ABSOLUTE'; nt.links.new(ss.outputs["Value"], sa.inputs[0])
    sp = nt.nodes.new("ShaderNodeMath"); sp.operation = 'POWER'; sp.inputs[1].default_value = 0.12
    nt.links.new(sa.outputs["Value"], sp.inputs[0])
    hh = nt.nodes.new("ShaderNodeMath"); hh.operation = 'MULTIPLY'
    nt.links.new(pw.outputs["Value"], hh.inputs[0]); nt.links.new(sp.outputs["Value"], hh.inputs[1])
    bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 0.006
    nt.links.new(hh.outputs["Value"], bump.inputs["Height"])
    oc = nt.nodes.new("ShaderNodeMath"); oc.operation = 'MULTIPLY_ADD'
    oc.inputs[1].default_value = 0.04; oc.inputs[2].default_value = 0.96          # 0.96 in the groove .. 1 on the puff
    nt.links.new(hh.outputs["Value"], oc.inputs[0])
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
    mx.inputs["Factor"].default_value = 1.0
    col = b.inputs["Base Color"]
    if col.is_linked:
        nt.links.new(mx.inputs["A"], col.links[0].from_socket)
    else:
        mx.inputs["A"].default_value = tuple(col.default_value)
    nt.links.new(mx.inputs["B"], oc.outputs["Value"]); nt.links.new(col, mx.outputs["Result"])
    nin = b.inputs["Normal"]
    if nin.is_linked:                                    # keep the fabric's own weave bump underneath
        nt.links.new(nin.links[0].from_socket, bump.inputs["Normal"])
    nt.links.new(bump.outputs["Normal"], nin)


def _quilting_pillow(mat, period=0.04, crinkle=0.022, uv_lines=22, uv_axis='U'):   # 'V' drew them vertical
    """Pillow sham (photo 5): stitch lines across the pillow, stacked up its height, so on a pillow standing against
    the headboard they are a function of world Z; they wander +-3 mm, and a ~1 cm crinkle covers the whole cloth."""
    if mat is None or not mat.use_nodes or mat.get("acolchado"):
        return
    nt = mat.node_tree
    b = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if b is None:
        return
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Position"], sep.inputs["Vector"])
    wy = nt.nodes.new("ShaderNodeMath"); wy.operation = 'MULTIPLY'; wy.inputs[1].default_value = 2 * math.pi / 0.12
    nt.links.new(sep.outputs["Y"], wy.inputs[0])
    ws = nt.nodes.new("ShaderNodeMath"); ws.operation = 'SINE'; nt.links.new(wy.outputs["Value"], ws.inputs[0])
    # Lines of constant world Z bent with the pillow's bulge and read as waves; drawn on the pillow's own UVs they
    # stay straight on the cloth (uv_lines = stitch rows over the UV height; 0 falls back to world Z).
    wz = nt.nodes.new("ShaderNodeMath"); wz.operation = 'MULTIPLY_ADD'; wz.inputs[1].default_value = 0.001
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'
    if uv_lines:
        uv = nt.nodes.new("ShaderNodeUVMap"); su = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(uv.outputs["UV"], su.inputs["Vector"])
        nt.links.new(ws.outputs["Value"], wz.inputs[0]); nt.links.new(su.outputs["X" if uv_axis == 'U' else "Y"], wz.inputs[2])
        mul.inputs[1].default_value = math.pi * uv_lines
    else:
        nt.links.new(ws.outputs["Value"], wz.inputs[0]); nt.links.new(sep.outputs["Z"], wz.inputs[2])
        mul.inputs[1].default_value = math.pi / period
    nt.links.new(wz.outputs["Value"], mul.inputs[0])
    sn = nt.nodes.new("ShaderNodeMath"); sn.operation = 'SINE'; nt.links.new(mul.outputs["Value"], sn.inputs[0])
    ab = nt.nodes.new("ShaderNodeMath"); ab.operation = 'ABSOLUTE'; nt.links.new(sn.outputs["Value"], ab.inputs[0])
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 0.35
    nt.links.new(ab.outputs["Value"], pw.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.0 / crinkle
    nz.inputs["Detail"].default_value = 2.0
    nt.links.new(geo.outputs["Position"], nz.inputs["Vector"])
    hh = nt.nodes.new("ShaderNodeMath"); hh.operation = 'MULTIPLY_ADD'; hh.inputs[1].default_value = 0.9
    nt.links.new(nz.outputs[0], hh.inputs[0]); nt.links.new(pw.outputs["Value"], hh.inputs[2])     # stitches + crinkle
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 0.006
    nt.links.new(hh.outputs["Value"], bump.inputs["Height"])
    nin = b.inputs["Normal"]
    if nin.is_linked:
        nt.links.new(nin.links[0].from_socket, bump.inputs["Normal"])
    nt.links.new(bump.outputs["Normal"], nin)
    oc = nt.nodes.new("ShaderNodeMath"); oc.operation = 'MULTIPLY_ADD'
    oc.inputs[1].default_value = 0.05; oc.inputs[2].default_value = 0.95
    nt.links.new(pw.outputs["Value"], oc.inputs[0])
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
    mx.inputs["Factor"].default_value = 1.0
    col = b.inputs["Base Color"]
    if col.is_linked:
        nt.links.new(mx.inputs["A"], col.links[0].from_socket)
    else:
        mx.inputs["A"].default_value = tuple(col.default_value)
    nt.links.new(mx.inputs["B"], oc.outputs["Value"]); nt.links.new(col, mx.outputs["Result"])
    mat["acolchado"] = True


def _hem(o, hem, z_top=MATT_Z1 + 0.02, out=0.3, knee=0.07, side_drop=None):
    """Shorten a draped cloth with a soft clamp on the drop below z_top: drops shorter than (z_top - hem - knee)
    stay as they are (the sides only hung to the mattress bottom), longer ones are squeezed so nothing passes `hem`
    (the foot fell to 10 cm off the floor).  A uniform scale shortened the sides too and bared the mattress.
    What hangs outside the mattress footprint is pulled in to `out` of its overhang (the head end is left alone)."""
    bpy.context.view_layer.update()
    mw = o.matrix_world; inv = mw.inverted()
    pts = [mw @ v.co for v in o.data.vertices]
    zmin = min(p.z for p in pts)
    if zmin >= hem:
        return
    D = z_top - hem; k = D - knee
    x0, y0, y1 = FX, BED_Y - BED_W / 2, BED_Y + BED_W / 2                       # mattress foot and sides
    for v, p in zip(o.data.vertices, pts):
        d = z_top - p.z
        if d > k:
            p.z = z_top - (k + knee * math.tanh((d - k) / knee))
        if side_drop and (p.y < y0 or p.y > y1):                                 # sides only hang side_drop (photo 1:
            w = min(1.0, max(0.0, (p.x - x0) / 0.15))                           # the sheet shows below); eased in
            ds, ks, kn = z_top - p.z, side_drop - 0.03, 0.03                     # from the foot corner
            if ds > ks:
                p.z += w * (ds - (ks + kn * math.tanh((ds - ks) / kn)))
        if p.x < x0:
            p.x = x0 - (x0 - p.x) * out
        if p.y < y0:
            p.y = y0 - (y0 - p.y) * out
        elif p.y > y1:
            p.y = y1 + (p.y - y1) * out
        v.co = inv @ p
    o.data.update()
    print(f"[biblioteca] dobladillo {o.name}: caída máx {z_top - zmin:.2f} -> {D:.2f} m, borde a z {hem - Z0:.2f} m")



def _flat_sheet(o, lift=0.003):
    """The model's sheet is as puffy as its duvet (top up to 3 cm over the mattress) and poked through the thinned
    duvet; a fitted sheet lies flat: everything over the mattress top goes to `lift` above it."""
    bpy.context.view_layer.update()
    mw = o.matrix_world; inv = mw.inverted()
    for v in o.data.vertices:
        p = mw @ v.co
        if p.z > MATT_Z1 - 0.005:
            p.z = MATT_Z1 + lift
            v.co = inv @ p
    o.data.update()



def _smooth_drop(o, iters=150, factor=1.0, band=0.06, corner_r=0.35):
    """Photo 5: the model's corner drape, squeezed by the hem, left a big curved fold at the foot corner, right on the
    mattress edge.  Smooth what lies outside the mattress footprint (edge roll and drop), eased in over `band` inside
    it, so the quilted top keeps its shape.  (Smoothing only below the mattress top missed the fold.)"""
    mw = o.matrix_world
    vg = o.vertex_groups.new(name="caida")
    y0, y1 = BED_Y - BED_W / 2, BED_Y + BED_W / 2
    for v in o.data.vertices:
        p = mw @ v.co
        d = min(p.x - FX, p.y - y0, y1 - p.y)                              # distance inside the footprint (<0 out)
        w = min(1.0, max(0.0, (band - d) / band))
        # foot corners: the model's drape folds into a flap where the foot and side drops meet; the hem keeps it,
        # lying over the corner top (photo 5).  Heavy smoothing within corner_r of each foot corner flattens it.
        rc = min(math.hypot(p.x - FX, p.y - yc) for yc in (y0, y1))
        wc = min(1.0, max(0.0, (corner_r - rc) / (corner_r * 0.4)))
        w = max(w * w * (3 - 2 * w), wc * wc * (3 - 2 * wc))
        if w > 0:
            vg.add([v.index], w, 'REPLACE')
    sm = o.modifiers.new("alisar_caida", 'SMOOTH'); sm.factor = factor; sm.iterations = iters; sm.vertex_group = "caida"


TUCK_F = (0.62, 0.80)                  # duvet fold line, as a fraction of the bed from the foot: nightstand / wall side


def _tuck(o, f_near=TUCK_F[0], f_far=TUCK_F[1], ramp=0.05, sink=0.016, thin=0.3, flap=0.28, flap_h=0.022):
    """Photo 1: the white duvet is folded back toward the foot; the head end of the bed shows the khaki sheet, on top
    and down the sides, with the fold running on a slant (~62 % of the length on the nightstand side, under the
    cushions on the wall side).  (A first reading as a strip along the nightstand side was wrong: that side is the
    one facing the camera and it is white.)  Duvet vertices past the fold are pulled inside the mattress footprint
    and sunk under the sheet, with a short ramp so the edge rolls down instead of stepping."""
    bpy.context.view_layer.update()
    # the duvet is a coarse cage under a subdivision modifier: moving its few vertices dragged half the bed down,
    # so freeze the evaluated (subdivided) mesh first and tuck that
    print(f"[biblioteca] colcha: {len(o.data.vertices)} vértices base, modificadores {[m.type for m in o.modifiers]}")
    me = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    o.modifiers.clear(); o.data = me
    mw = o.matrix_world; inv = mw.inverted()
    y0, y1 = BED_Y - BED_W / 2, BED_Y + BED_W / 2
    zs = MATT_Z1 - sink
    zt = MATT_Z1 + 0.008                                                   # just over the flattened sheet
    n = 0
    for v in o.data.vertices:
        p = mw @ v.co
        inside = FX < p.x and abs(p.y - BED_Y) < BED_W / 2
        if inside and p.z > MATT_Z1 - 0.02:
            p.z = max(p.z, zt)            # never under the flattened sheet
        if p.z > zt:                  # the model's duvet is a 5-11 cm puffy comforter; photo 1 is a thin quilted
            p.z = zt + thin * (p.z - zt)  # coverlet, and a thick one left a white slab where it ends
        u = min(1.0, max(0.0, (p.y - y0) / BED_W))                        # 0 nightstand side, 1 wall side
        ex = FX + (HX - FX) * (f_near + (f_far - f_near) * u)              # fold line
        # the duvet is folded back on itself (user, photo 5): a second layer lies on a band before the fold line,
        # ending in a rounded roll at the fold; without it the fold was a paper-thin edge
        d = ex - ramp - p.x                                                # distance before the fold, toward the foot
        if 0.0 <= d <= flap and p.z > MATT_Z1 - 0.02 and FX < p.x:
            roll = math.exp(-(d / 0.035) ** 2)                             # bulge of the fold itself
            fin = min(1.0, (flap - d) / 0.02)                              # the flap's free edge: a 2 cm step
            p.z += (flap_h + 0.012 * roll) * fin
        w = min(1.0, (p.x - ex + ramp) / ramp)                             # 1 past the fold, 0 before the ramp
        if w > 0:
            w = w * w * (3 - 2 * w)
            if p.y < y0 + 0.02:                                            # side drops past the fold go under too
                p.y += w * (y0 + 0.02 - p.y)
            elif p.y > y1 - 0.02:
                p.y += w * (y1 - 0.02 - p.y)
            if p.z > zs:
                p.z += w * (zs - p.z)
            n += 1
        v.co = inv @ p
    o.data.update()
    print(f"[biblioteca] colcha doblada: {n} vértices bajo la sábana (doblez {f_near:.2f}-{f_far:.2f})")


def _runner(parts, coll):
    """Photos 1/5: white quilted bedspread with a narrow palm-print runner across the foot (no blue blanket).
    The runner is a 2 cm grid shrink-wrapped down onto the duvet; procedural navy print on off-white."""
    import bmesh
    duvet = parts.get("Plane.016") or parts.get("Plane.015")
    if duvet is None:
        return
    x0, x1 = FX + 0.28, FX + 0.75                              # ~47 cm band, starting ~28 cm from the foot (photo 5)
    y0, y1 = BED_Y - BED_W / 2 + 0.01, BED_Y + BED_W / 2 - 0.01
    me = bpy.data.meshes.new("Camino"); bm = bmesh.new()
    nx, ny = int((x1 - x0) / 0.02), int((y1 - y0) / 0.02)
    vs = [[bm.verts.new((x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny, MATT_Z1 + 0.35)) for j in range(ny + 1)] for i in range(nx + 1)]
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:
        for lp in f.loops:
            lp[uv].uv = ((lp.vert.co.x - x0) / (x1 - x0), (lp.vert.co.y - y0) / (y1 - y0))
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("Camino", me); coll.objects.link(ob)
    sw = ob.modifiers.new("drape", 'SHRINKWRAP'); sw.target = duvet; sw.wrap_method = 'PROJECT'
    sw.use_project_z = True; sw.use_negative_direction = True; sw.use_positive_direction = False; sw.offset = 0.004
    ob.modifiers.new("thick", 'SOLIDIFY').thickness = 0.003
    for p in me.polygons:
        p.use_smooth = True
    m = bpy.data.materials.new("Camino_Palmas"); m.use_nodes = True; nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.feature = 'DISTANCE_TO_EDGE'; vo.inputs["Scale"].default_value = 26.0
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 60.0; nz.inputs["Detail"].default_value = 6.0
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = 'ADD'
    nt.links.new(tc.outputs["Object"], vo.inputs["Vector"]); nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nt.links.new(vo.outputs["Distance"], mx.inputs[0])
    sc = nt.nodes.new("ShaderNodeMath"); sc.operation = 'MULTIPLY'; sc.inputs[1].default_value = 0.12
    nt.links.new(nz.outputs["Fac"], sc.inputs[0]); nt.links.new(sc.outputs["Value"], mx.inputs[1])
    rp = nt.nodes.new("ShaderNodeValToRGB")                       # thin navy fronds on off-white
    # remoto/color_objetos.py (fotos 1 y 5, normalizado por la pared): el camino real es ~2,3x más oscuro que con
    # trazos finos (0,10-0,16): el estampado tiene mucho más azul que fondo
    rp.color_ramp.elements[0].position = 0.20; rp.color_ramp.elements[0].color = (0.035, 0.05, 0.08, 1)
    rp.color_ramp.elements[1].position = 0.27; rp.color_ramp.elements[1].color = (0.74, 0.72, 0.66, 1)
    nt.links.new(mx.outputs["Value"], rp.inputs["Fac"])
    # tan border along the long edges (photo 5)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["UV"], sep.inputs["Vector"])
    bd = nt.nodes.new("ShaderNodeMapRange"); bd.inputs["From Min"].default_value = 0.0; bd.inputs["From Max"].default_value = 1.0
    ed = nt.nodes.new("ShaderNodeMath"); ed.operation = 'PINGPONG'; ed.inputs[1].default_value = 0.5
    nt.links.new(sep.outputs["X"], ed.inputs[0])
    gt = nt.nodes.new("ShaderNodeMath"); gt.operation = 'LESS_THAN'; gt.inputs[1].default_value = 0.035
    nt.links.new(ed.outputs["Value"], gt.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    ins = {s.identifier: s for s in mix.inputs}; outs = {s.identifier: s for s in mix.outputs}
    nt.links.new(gt.outputs["Value"], ins["Factor_Float"]); nt.links.new(rp.outputs["Color"], ins["A_Color"])
    ins["B_Color"].default_value = (0.55, 0.45, 0.32, 1)
    nt.links.new(outs["Result_Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85
    if "Sheen Weight" in b.inputs:
        b.inputs["Sheen Weight"].default_value = 0.3
    me.materials.append(m)


def _base_rgb(mat, default):
    """Target colour of one of our materials (so the finish packages keep driving the headboard colour)."""
    try:
        b = next(n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
        if not b.inputs["Base Color"].is_linked:
            return tuple(b.inputs["Base Color"].default_value[:3])
    except (StopIteration, AttributeError):
        pass
    return default


def _headboard(L, coll, M):
    """Upholstered headboard of the Double Bed model (frame + padded panel) instead of the smooth coded box."""
    parts = [L[n] for n in ("Wall_Fabric_1.001", "Wall_Fabric_2.001") if n in L]
    if not parts:
        return
    _keep(parts, coll)
    old = bpy.data.objects.get("Cama_Cabecero")
    target = _base_rgb(old.active_material, (0.80, 0.74, 0.62)) if old else (0.80, 0.74, 0.62)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    # model: 1.72 wide on X, depth on Y (toward +Y = wall), 1.0 tall from the floor; ours: 1.48 wide, top at 1.08
    rot = Matrix.Rotation(math.radians(-90), 4, 'Z')
    # depth squeezed to the 10 cm between the wall and the bed head (HX): the mattress went 7 cm into the padding
    _place(parts, rot @ Matrix.Diagonal(((BED_W + 0.15) / 1.72, (W - HX - 0.02) / 0.16, 1.08, 1.0)))   # 2 cm clear of mattress and rail
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in parts for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    d = Vector(((W - 0.005) - hi.x, BED_Y - (lo.y + hi.y) / 2, Z0 - lo.z))
    for o in parts:
        o.location += d
        _tint_obj(o, target)


def _trees(targets):
    """World-space BVH trees of the evaluated target meshes (BVHTree.FromObject would be in object space)."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for t in targets:
        if t is None or t.type != 'MESH':
            continue
        ev = t.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ev.matrix_world
        verts = [mw @ v.co for v in me.vertices]
        polys = [tuple(p.vertices) for p in me.polygons]
        out.append(BVHTree.FromPolygons(verts, polys))
        ev.to_mesh_clear()
    return out


def _cast_gap(o, direction, trees, max_d=0.45, step=5):
    """Smallest free distance from the object's vertices along `direction` to the target meshes (BVH ray casts)."""
    mw = o.matrix_world
    d = Vector(direction).normalized()
    best = max_d
    verts = o.data.vertices
    pts = [mw @ verts[i].co for i in range(0, len(verts), step)]
    if abs(d.z) < 0.5:          # sideways push: skip the bottom 6 cm, which rests on (and would snag) the surface below
        z0 = min(p.z for p in pts)
        pts = [p for p in pts if p.z > z0 + 0.06]
    for p in pts:
        for t in trees:
            loc, _n, _i, dist = t.ray_cast(p, d, max_d)
            if loc is not None:
                best = min(best, dist)
    return best


def _world_verts(o, dg=None):
    dg = dg or bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    out = [ev.matrix_world @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    return out


def _push_to(o, targets, axis=0, sign=1, gap=0.004):
    """Slide o along one world axis until its leading vertices meet the targets' vertices in the same band
    (vertex comparison: robust for open cloth meshes where ray casts miss)."""
    bpy.context.view_layer.update()
    mine = _world_verts(o)
    z0 = min(p.z for p in mine)
    mine = [p for p in mine if p.z > z0 + 0.06]
    other = [ax for ax in (0, 1, 2) if ax != axis]
    lo = [min(p[a] for p in mine) for a in other]
    hi = [max(p[a] for p in mine) for a in other]
    tv = [p for t in targets if t is not None for p in _world_verts(t)
          if all(lo[k] <= p[a] <= hi[k] for k, a in enumerate(other))]
    if not tv:
        return 0.0
    if sign > 0:
        d = min(p[axis] for p in tv) - max(p[axis] for p in mine)
    else:
        d = min(p[axis] for p in mine) - max(p[axis] for p in tv)
    d = max(min(d - gap, 0.45), 0.0)
    v = Vector((0, 0, 0)); v[axis] = sign * d
    o.location += v
    bpy.context.view_layer.update()
    return d


def _settle(objs, targets, push=None, push_targets=None, gap=0.004):
    """Rest soft props on the target meshes (and against what is behind them) instead of hand-placed heights:
    drop until touching, push along `push` until touching, drop again.  Start the props clear of the targets."""
    bpy.context.view_layer.update()
    trees = _trees(targets)
    ptrees = _trees(push_targets) if push_targets else trees
    for o in objs:
        for dvec in [(0, 0, -1)] + ([push] if push else []) + [(0, 0, -1)]:
            if not dvec[2] and push_targets:
                ax = 0 if dvec[0] else 1
                _push_to(o, push_targets, axis=ax, sign=1 if dvec[ax] > 0 else -1, gap=gap)
                continue
            dist = _cast_gap(o, dvec, trees if dvec[2] else ptrees)
            if dist < 0.45:
                o.location += Vector(dvec).normalized() * max(dist - gap, 0.0)
                bpy.context.view_layer.update()
        print(f"[biblioteca] asentado {o.name}: {tuple(round(c, 3) for c in o.location)}")


def _square_cushion(name, a=0.225, h=0.075, n=36, pinch=0.12, seed=0):
    """Square throw cushion (photo 5: two light-blue 45 cm squares, not round).  Two puffed faces that meet at the
    seam, edges drawn in at mid-side; flat on Z with the origin at the bottom, like the library cushion."""
    import bmesh
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new()
    g = [-1 + 2 * i / n for i in range(n + 1)]

    # Photo 5 (close-up): a filled cushion is not a smooth lens.  Edges drawn in more (pointed "ears"), two or three
    # broad soft dents on each face, and short wrinkles fanning out of every corner where the filling pulls the cover.
    import random as _r
    rnd = _r.Random(seed)
    ph = [rnd.uniform(0, 2 * math.pi) for _ in range(6)]
    # 2026-11-13: at 16 % / 13 % the relief did not read at photo-5 distance.  Stronger dents and corner wrinkles,
    # plus one soft diagonal CREASE per face: where the filling bends, the cover folds into a valley (photo 5 close-up)
    ca = rnd.uniform(0.5, 1.1) * (1 if rnd.random() < 0.5 else -1)
    cn = (math.cos(ca), math.sin(ca)); c0 = rnd.uniform(-0.25, 0.25)

    def pos(u, v, side):
        f = max((1 - u * u) * (1 - v * v), 0.0) ** 0.35
        k = 0 if side > 0 else 3                                         # each face its own dents
        dent = 0.6 * math.sin(2.1 * u + 1.3 * v + ph[k]) + 0.4 * math.sin(-1.4 * u + 2.6 * v + ph[k + 1])
        cu, cv = (1.0 if u > 0 else -1.0), (1.0 if v > 0 else -1.0)      # nearest corner
        rc = math.hypot(u - cu, v - cv)
        th = math.atan2(v - cv, u - cu)
        arr = math.exp(-rc / 0.35) * math.cos(6.0 * th + ph[k + 2]) * min(1.0, rc / 0.08)
        dc = u * cn[0] + v * cn[1] - c0 * side                           # distance to the crease line
        crease = -math.exp(-(dc / 0.09) ** 2) * (1 - 0.5 * abs(u * cn[1] - v * cn[0]))   # fades toward its ends
        rel = f * (1.0 + 0.30 * dent + 0.22 * arr + 0.28 * crease)
        return (a * u * (1 - pinch * (1 - v * v)), a * v * (1 - pinch * (1 - u * u)), h + side * h * rel)
    top = [[bm.verts.new(pos(u, v, 1)) for v in g] for u in g]
    bot = [[top[i][j] if i in (0, n) or j in (0, n) else bm.verts.new(pos(g[i], g[j], -1))
            for j in range(n + 1)] for i in range(n + 1)]
    for grid, flip in ((top, False), (bot, True)):
        for i in range(n):
            for j in range(n):
                q = [grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]]
                f = bm.faces.new(q[::-1] if flip else q)
                for lp in f.loops:
                    lp[uvl].uv = (lp.vert.co.x / (2 * a) + 0.5, lp.vert.co.y / (2 * a) + 0.5)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    ob.modifiers.new("sub", 'SUBSURF').levels = 1
    return ob


def _front_pillows(coll):
    """Photo 5: a second row of white pillows in front of the two leaning on the headboard (the blue cushions sit on
    it).  Copies of the library pillows, 90 % size, set 17 cm in front of the back row on the same duvet height
    (a _settle push against the back row overshot into it: identical leaning shapes nest)."""
    back = [bpy.data.objects.get(n) for n in ("Plane.017", "Plane.018")]
    back = [o for o in back if o is not None]
    out = []
    for k, o in enumerate(back):
        c = o.copy(); c.name = f"Almohada_Frente_{k}"
        coll.objects.link(c)
        pts = [o.matrix_world @ Vector(b) for b in o.bound_box]
        c0 = sum(pts, Vector()) / 8; c0.z = min(p.z for p in pts)          # scale about the bottom centre
        c.matrix_world = (Matrix.Translation(c0 + Vector((-0.17, 0, -0.01))) @ Matrix.Diagonal((0.9, 0.9, 0.9, 1.0))
                          @ Matrix.Translation(-c0) @ o.matrix_world)
        out.append(c)
    _keep(out, coll)
    return out


def _towel(coll):
    """Photos 1 and 5: the towel 'swan' on the runner.  The coded one (muebles.bed) was laid on the coded runner;
    with the library bedspread it is kept and re-seated on whatever is under it now."""
    tw = bpy.data.objects.get("Cama_Toalla")
    if tw is None:
        return
    under = [o for o in (bpy.data.objects.get("Camino"), bpy.data.objects.get("Plane.016")) if o is not None]
    if not under:
        return
    bpy.context.view_layer.update()
    trees = _trees(under)
    pts = _world_verts(tw)
    zmin = min(p.z for p in pts)
    lows = [p for p in pts if p.z < zmin + 0.015]                 # the face that rests on the bed
    gaps = []
    for p in lows[::max(1, len(lows) // 60)]:
        for t in trees:
            loc, _n, _i, _d = t.ray_cast(Vector((p.x, p.y, p.z + 0.5)), Vector((0, 0, -1)), 1.5)
            if loc is not None:
                gaps.append(p.z - loc.z)
    if gaps:
        tw.location.z -= sorted(gaps)[len(gaps) // 2] - 0.003     # median: sits on the folds, does not float
    _tint_obj(tw, (0.56, 0.49, 0.38))                  # beige, as photographed (the cream read white on the white bed)
    print(f"[biblioteca] toalla asentada en z {tw.location.z:.3f}")


def _cushions(L, coll):
    src = L.get("Blue velvet button cushion B")
    mats = [s.material for s in src.material_slots if s.material] if src else []
    velvet = next((m for m in mats if "velvet" in m.name.lower()), mats[0] if mats else None)
    if velvet is None:
        velvet = bpy.data.materials.new("Cojin_Terciopelo"); velvet.use_nodes = True
    out = []
    for k in range(2):
        ob = _square_cushion(f"Cushions_Blue_{k}", seed=11 + k)
        ob.data.materials.append(velvet)
        coll.objects.link(ob); out.append(ob)
    _keep(out, coll)
    # Photo 5 (close-up): the cushions are not upright squares side by side.  Each is turned on its face so it rests
    # near a corner (a diamond), the window-side one (+y, left in the photo) behind and the other in front of it,
    # overlapping.  Roll = rotation about the cushion's own face normal, applied before standing it up.
    POSE = ((0.17, 10, -5, 0.0), (-0.10, -12, 14, -0.13))             # dy, yaw, roll (deg), extra x after settling
    # (user, 2026-11-11: at -14 / 27 deg the front cushion balanced on a corner like a rigid diamond, with air under
    # it.  A soft cushion slumps: the back one is nearly upright, the front one only tipped and sunk into the duvet.)
    # (rolls of -32 / 36 deg stood them on a corner, floating up the headboard: the photo's turn is smaller)
    for o, (dy, yaw, roll, _dx) in zip(out, POSE):
        # flat model (thickness on Z, origin at the bottom): stand it up leaning back 24 deg toward the head
        o.matrix_world = (Matrix.Translation((HX - 0.85, BED_Y + dy, MATT_Z1 + 0.45))   # clear of both pillow rows
                          @ Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Rotation(math.radians(-66), 4, 'Y')
                          @ Matrix.Rotation(math.radians(roll), 4, 'Z'))
    bpy.context.view_layer.update()
    bed = [bpy.data.objects.get(n) for n in ("Plane.015", "Plane.016", "Plane.017", "Plane.018", "Plane.021",
                                             "Almohada_Frente_0", "Almohada_Frente_1",
                                             "Wall_Fabric_1.001", "Wall_Fabric_2.001")]
    lean = [bpy.data.objects.get(n) for n in ("Plane.017", "Plane.018", "Almohada_Frente_0", "Almohada_Frente_1",
                                              "Wall_Fabric_1.001", "Wall_Fabric_2.001")]
    _settle(out, bed, push=(1, 0, 0), push_targets=lean)         # sit on the duvet, lean on the pillows
    for o, (_dy, _yaw, roll, dx) in zip(out, POSE):              # soft: they sink a few cm into the pillows
        o.location.x += 0.07 + dx
        o.location.z -= 0.012 + 0.0015 * abs(roll)               # ... and the tipped one's low corner into the duvet
    _tint(velvet, AZUL_COJIN)


SOFA_MODO = os.environ.get("SOFA_MODO", "codigo")     # codigo | hunyuan | teddy (comparación A/B del 2026-11-06)
HY_SOFA = os.path.join(ASSETS, "gen", "sofa_santiago.glb")


def _box_project(mat):
    """Image textures of a library material on meshes without good UVs: object-space box projection (metres)."""
    nt = mat.node_tree
    tc = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeTexCoord"), None) or nt.nodes.new("ShaderNodeTexCoord")
    for n in [n for n in nt.nodes if n.bl_idname == "ShaderNodeTexImage"]:
        n.projection = 'BOX'
        n.projection_blend = 0.25
        v = n.inputs["Vector"]
        src = v.links[0].from_node if v.is_linked else None
        if src is not None and src.bl_idname == "ShaderNodeMapping":
            for l in list(src.inputs["Vector"].links):
                nt.links.remove(l)
            nt.links.new(tc.outputs["Object"], src.inputs["Vector"])
        else:
            for l in list(v.links):
                nt.links.remove(l)
            nt.links.new(tc.outputs["Object"], v)


def _sofa_materials(coll):
    """Velour (body), Indian print (bolster) and velvet (throw) from the Teddy sofa, as standalone materials."""
    if not os.path.isfile(LIB_SOFA):
        return {}
    L = _load(coll, LIB_SOFA)
    pick = {"cuerpo": ("Roundcube.010", 0), "estampado": ("cushion.007", 0), "manta": ("Plane.008", 0)}
    out = {}
    for k, (n, i) in pick.items():
        o = L.get(n)
        if o is not None and len(o.material_slots) > i and o.material_slots[i].material:
            m = o.material_slots[i].material.copy()
            m.name = f"Sofa_{k}"
            _box_project(m)
            out[k] = m
    for o in L.values():
        if o.name in bpy.data.objects:
            bpy.data.objects.remove(o, do_unlink=True)
    return out


def _oscurecer_felpa(mat, rgb):
    """The Teddy velour keeps a pale sheen / velvet lobe of its own: with a dark base colour the sofa still rendered
    camel (remoto/color_objetos.py: factor 0.30 -> 0.35 only).  Pull every sheen-like lobe to the body colour."""
    info = []
    for n in mat.node_tree.nodes:
        if n.bl_idname == "ShaderNodeBsdfPrincipled":
            for k in ("Sheen Weight", "Coat Weight"):
                if k in n.inputs and not n.inputs[k].is_linked:
                    info.append((k, round(n.inputs[k].default_value, 2)))
                    n.inputs[k].default_value = min(n.inputs[k].default_value, 0.15)
            if "Sheen Tint" in n.inputs and not n.inputs["Sheen Tint"].is_linked:
                n.inputs["Sheen Tint"].default_value = (*[min(1.0, 2.5 * c) for c in rgb], 1)
            for k in ("Emission Strength", "Subsurface Weight"):
                if k in n.inputs and not n.inputs[k].is_linked and n.inputs[k].default_value > 0:
                    info.append((k, round(n.inputs[k].default_value, 2))); n.inputs[k].default_value = 0.0
        elif n.bl_idname in ("ShaderNodeBsdfSheen", "ShaderNodeBsdfVelvet", "ShaderNodeBsdfDiffuse", "ShaderNodeBsdfGlossy"):
            c = n.inputs.get("Color")
            if c is not None:
                for l in list(c.links):
                    mat.node_tree.links.remove(l)
                c.default_value = (*[min(1.0, 1.5 * x) for x in rgb], 1)
                info.append((n.bl_idname, "color"))
    print(f"[biblioteca] felpa {mat.name}: nodos {[n.bl_idname for n in mat.node_tree.nodes][:14]} cambios {info}")


def _sofa_codigo(coll):
    """A: the photographed futon built by code (plan/photo/product dimensions) dressed in the Teddy's real fabrics."""
    mats = _sofa_materials(coll)
    body = bpy.data.objects.get("Sofa_Cama")
    if body is None or not mats:
        return []
    # remoto/color_objetos.py, photo 1 (2026-11-11): body L* 20 in the photo against 41 with the package colour
    # (0.38, 0.30, 0.24), and less saturated: a dark chocolate brown, ~4x less reflectance relative to the wall
    m = mats["cuerpo"]; _tint(m, CAFE_SOFA)
    _oscurecer_felpa(m, CAFE_SOFA)
    body.material_slots[0].material = m
    if body.data.polygons and not any(md.type == 'BEVEL' for md in body.modifiers):
        bv = body.modifiers.new("Bisel", 'BEVEL'); bv.width = 0.012; bv.segments = 3; bv.limit_method = 'ANGLE'
    bol = bpy.data.objects.get("Sofa_Cojin_Estampado")
    if bol is not None and "estampado" in mats:
        _tint(mats["estampado"], ESTAMPADO_SOFA)        # photo 1: a light beige-green print (L* 51); it rendered L* 6
        bol.material_slots[0].material = mats["estampado"]
    manta = bpy.data.objects.get("Sofa_Manta")
    if manta is not None and "manta" in mats:
        mm = mats["manta"]; _tint(mm, BEIGE_MANTA, strength=0.12)   # plain peach blanket: at 0.6 the velvet's own
                                                                    # light/dark map read as stains with holes
        manta.material_slots[0].material = mm
    return []                                   # pillows settle on the coded sofa (Sofa_Cama is a target already)


def _sofa_hunyuan(coll):
    """B: Hunyuan3D-2.1 shape from the product photo (MICA Santiago), fitted to the plan box, Teddy velour on it."""
    if not os.path.isfile(HY_SOFA):
        print("[biblioteca] sofa hunyuan: falta", HY_SOFA)
        return []
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=HY_SOFA)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    for o in new:
        if o.name not in coll.objects:
            coll.objects.link(o)
        for c in list(o.users_collection):
            if c is not coll:
                c.objects.unlink(o)
    _keep(meshes, coll)
    for o in new:
        if o.type != 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)
    body = bpy.data.objects.get("Sofa_Cama")
    target = _base_rgb(body.active_material, (0.36, 0.26, 0.18)) if body else (0.36, 0.26, 0.18)
    for n in ("Sofa_Cama", "Sofa_Cojin_Estampado", "Sofa_Manta"):
        o = bpy.data.objects.get(n)
        if o is not None:
            bpy.data.objects.remove(o, do_unlink=True)
    # Hunyuan output: Y-up glTF -> Blender Z-up already; front of the photo looks toward -Y.  Long axis = X.
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    size = hi - lo
    long_x = size.x >= size.y
    rot = Matrix.Rotation(math.radians(-90 if long_x else 0), 4, 'Z')      # long side along the wall (world Y)
    sl, sd = (size.x, size.y) if long_x else (size.y, size.x)
    S = Matrix.Diagonal((0.90 / sd, 1.95 / sl, 0.80 / size.z, 1.0)) if not long_x else Matrix.Diagonal((1.95 / sl, 0.90 / sd, 0.80 / size.z, 1.0))
    _place(meshes, rot @ S)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    d = Vector((0.02 - lo.x, 5.72 - (lo.y + hi.y) / 2, Z0 - lo.z))
    mats = _sofa_materials(coll)
    for o in meshes:
        o.location += d
        if mats:
            m = mats["cuerpo"]; _tint(m, target)
            o.data.materials.clear(); o.data.materials.append(m)
        for p in o.data.polygons:
            p.use_smooth = True
        o.name = "Sofa_Hunyuan"
    print(f"[biblioteca] sofa hunyuan: {sum(len(o.data.polygons) for o in meshes)} caras, caja original {tuple(round(v, 2) for v in size)}")
    return meshes


def _sofa(coll):
    """Teddy sofa (Joris LM) in place of the coded futon: base + seat cushions tinted to the package's sofa colour,
    its velvet throw tinted to the photographed peach blanket.  Its own 5 cushions and the black/white throw go."""
    if not os.path.isfile(LIB_SOFA):
        return []
    L = _load(coll, LIB_SOFA)
    keep = [L[n] for n in ("Cube.058", "Roundcube.010", "Roundcube.011", "Plane.008") if n in L]
    _keep(keep, coll)
    old = bpy.data.objects.get("Sofa_Cama")
    target = _base_rgb(old.active_material, (0.36, 0.26, 0.18)) if old else (0.36, 0.26, 0.18)
    for n in ("Sofa_Cama", "Sofa_Cojin_Estampado", "Sofa_Manta"):
        o = bpy.data.objects.get(n)
        if o is not None:
            bpy.data.objects.remove(o, do_unlink=True)
    for o in L.values():
        if o not in KEPT and o.name in bpy.data.objects:
            bpy.data.objects.remove(o, do_unlink=True)
    # model: 2.06 long on X, back toward +Y, 1.03 deep; ours: 1.95 long on Y, back on the west wall (x = 0), 0.92 deep
    cy, L_, D = 5.72, 1.95, 0.92
    rot = Matrix.Rotation(math.radians(90), 4, 'Z')                   # +Y (back) -> -X (wall)
    orig = {o: o.matrix_world.copy() for o in keep}
    # seat top 0.53 m in the model once it stands on the floor; the photographed futon sits at 0.42 -> 0.8 vertically
    _place(keep, rot @ Matrix.Diagonal((L_ / 2.06, D / 1.03, 0.8, 1.0)))
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in keep for c in o.bound_box]   # boxes: the base has a nodes modifier
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    d = Vector((0.02 - lo.x, cy - (lo.y + hi.y) / 2, Z0 - lo.z))
    for o in keep:
        o.location += d
        if o.name.startswith("Plane"):
            _tint_obj(o, BEIGE_MANTA)
        else:
            _tint_obj(o, target)
    print(f"[biblioteca] sofa: alto {hi.z - lo.z:.2f} m, largo {hi.y - lo.y:.2f}, fondo {hi.x - lo.x:.2f}")
    # back: this Teddy variant is a daybed; the photographed futon has back pads (photo 1).  Stand a copy of each seat
    # pad against the wall: model X -> world Y (length), model Y -> up (0.42 m), model Z -> thickness (0.18 m)
    bpy.context.view_layer.update()            # the seat was just moved: refresh matrix_world before measuring
    seat_top = max((o.matrix_world @ Vector(c)).z for o in keep if o.name.startswith("Roundcube") for c in o.bound_box)
    backs = []
    for pad in [o for o in keep if o.name.startswith("Roundcube")]:
        py = sum((pad.matrix_world @ Vector(c)).y for c in pad.bound_box) / 8
        b_ = pad.copy(); b_.data = pad.data
        coll.objects.link(b_)
        b_.matrix_world = (Matrix.Rotation(math.radians(-8), 4, 'Y') @ Matrix.Rotation(math.radians(90), 4, 'Z')
                           @ Matrix.Rotation(math.radians(90), 4, 'X')
                           @ Matrix.Diagonal((0.92 / 1.0, 0.42 / 1.03, 0.18 / 0.37, 1.0)) @ orig[pad])
        bpy.context.view_layer.update()
        bb = [b_.matrix_world @ Vector(c) for c in b_.bound_box]
        b_.location += Vector((0.02 - min(p.x for p in bb), py - sum(p.y for p in bb) / 8, seat_top - 0.03 - min(p.z for p in bb)))
        b_.name = "Sofa_Respaldo"
        KEPT.add(b_)
        backs.append(b_)
    bpy.context.view_layer.update()
    return keep + backs


def _sofa_pillows(L, coll):
    src = L.get("Linen rustic pillow-01")
    if src is None:
        return
    cy = 5.72
    out = [src, src.copy()]
    out[1].data = src.data
    _keep(out, coll)
    # photo 1: plain dark olive pillows (L* 16-35); with the cords in their own colour they rendered L* 51 with a
    # white grid.  Every slot goes dark olive, with little of the texture's own contrast.
    for slot in src.material_slots:
        if slot.material:
            _tint(slot.material, OLIVA, strength=0.2)
    # photo 1: both pillows together at the door end (left in the photo), the second overlapping the first, lying
    # back more than upright; the rest of the back shows the printed band.  (They were apart: -0.42 / +0.40.)
    for o, dy, yaw in zip(out, (-0.62, -0.08), (4, -9)):
        o.matrix_world = Matrix.Identity(4)
        # model stands upright, thin axis Y: turn the face toward the room (+X) and lean it back on the sofa back
        o.rotation_mode = 'ZYX'                          # yaw first, then lean about the world Y axis
        o.rotation_euler = (0.0, math.radians(-34), math.radians(90 + yaw))
        o.scale = (1.4, 1.2, 0.88)                     # photo 1: rectangular bed pillows, wider than tall
        o.location = (0.80, cy + dy, Z0 + 0.80)        # start clear of the sofa; _settle rests it
    bpy.context.view_layer.update()
    sofa = [o for o in bpy.data.objects if o.name.startswith(("Sofa_Cama", "Sofa_Cojin", "Sofa_Manta"))] + SOFA
    back = ([o for o in SOFA if o.name.startswith("Sofa_Respaldo")] or SOFA) if SOFA else sofa
    _settle(out, sofa, push=(-1, 0, 0), push_targets=back)


def _curtains(L, coll):
    src = L.get("curtain")
    if src is None:
        return
    # model: 1.74 wide (X), 0.32 deep (Y), 3.04 tall, origin at the floor; hang from just under the ceiling
    h = (ZC - 0.04) - Z0
    sz = h / 3.04
    sx = 0.62 / 1.74                                    # gathered to ~62 cm at each side of the glazing
    sy = 0.09 / 0.32                                    # only 10 cm between the sofa end and the window wall
    out = [src, src.copy()]
    out[1].data = src.data
    _keep(out, coll)
    for o, x in zip(out, (WIN_X[0] - 0.19, WIN_X[1] + 0.19)):       # stacked beside the opening (photo-1 measurement)
        o.matrix_world = Matrix.Identity(4)
        o.rotation_euler = (0, 0, 0)
        o.scale = (sx, sy, sz)
        bpy.context.view_layer.update()
        lo = Vector([min((o.matrix_world @ Vector(c))[i] for c in o.bound_box) for i in range(3)])
        hi = Vector([max((o.matrix_world @ Vector(c))[i] for c in o.bound_box) for i in range(3)])
        o.location += Vector((x - (lo.x + hi.x) / 2, (Y_WIN - 0.005) - hi.y, Z0 + 0.01 - lo.z))
    # rod across the opening, under the ceiling
    rod = L.get("Tringle")
    if rod is not None:
        _keep([rod], coll)
        rod.matrix_world = Matrix.Identity(4)
        bpy.context.view_layer.update()
        lo = [min(c[i] for c in rod.bound_box) for i in range(3)]
        hi = [max(c[i] for c in rod.bound_box) for i in range(3)]
        rod.scale = ((W - 0.1) / (hi[0] - lo[0]), 1, 1)
        # top 2 cm under the ceiling (it was 4 cm into it; remoto/validar.py)
        rod.location = (W / 2 - (lo[0] + hi[0]) / 2 * rod.scale[0], Y_WIN - 0.07 - lo[1], ZC - 0.02 - hi[2])


def _monstera(L, coll):
    names = ("Fiber stick", "Leaves", "Soil", "Vase", "Soil.001")
    parts = [L[n] for n in names if n in L]
    if not parts:
        return
    _keep(parts, coll)
    old = bpy.data.objects.get("Prop_potted_plant_04")
    if old is not None:
        for c in list(old.children_recursive) + [old]:
            bpy.data.objects.remove(c, do_unlink=True)
    # model centred at x = 24, floor at z = 0; corner of the alcoba beside the bath door
    _place(parts, Matrix.Translation((3.70 - 24.0, 3.15, Z0)) @ Matrix.Rotation(math.radians(30), 4, 'Z'))
    # the rotation above was about the world origin: re-centre the plant on its spot
    bpy.context.view_layer.update()
    lo = [min((o.matrix_world @ Vector(c))[i] for o in parts for c in o.bound_box) for i in range(2)]
    hi = [max((o.matrix_world @ Vector(c))[i] for o in parts for c in o.bound_box) for i in range(2)]
    d = Vector((3.70 - (lo[0] + hi[0]) / 2, 3.15 - (lo[1] + hi[1]) / 2, 0))
    for o in parts:
        o.location += d


LIB_AUTO = os.path.join(ASSETS, "blenderkit", "auto.blend")   # "Generic Sport Sedan 2022" (P.-L. Baril), aprobado
# parked cars (photos 2-3: cars in the lot below and on the drive).  (x, y, heading deg); bays between the yellow
# lines of surroundings.py (x every 3 m from -18, y Y_BAL+2.5 .. +7.3)
AUTOS = [(4.5, Y_BAL + 4.9, 0), (7.5, Y_BAL + 4.9, 180), (13.5, Y_BAL + 4.9, 0), (19.5, Y_BAL + 4.9, 180),
         (10.0, 19.6, 90)]
PINTURAS = [(0.80, 0.80, 0.80), (0.45, 0.46, 0.47), (0.18, 0.19, 0.20), (0.20, 0.25, 0.32)]   # white, silver, grey, blue-grey


def _autos():
    if not os.path.isfile(LIB_AUTO):
        return
    src = bpy.data.collections.new("Auto_Src")                    # not linked to the scene: instanced only
    with bpy.data.libraries.load(LIB_AUTO, link=False) as (s_, d_):
        names = [str(n) for n in s_.objects]
        d_.objects = list(names)
    for o in d_.objects:
        if o is not None:
            src.objects.link(o)
    # per-instance paint: Object Info > Random picks one of the common colours
    for m in {sl.material for o in src.objects for sl in getattr(o, "material_slots", []) if sl.material}:
        if not m.name.startswith("Car Paint") or not m.use_nodes:
            continue
        nt = m.node_tree
        # the paint is a node group with its own "Base Color"; only the body paint (not the dark trim) changes
        b = next((n for n in nt.nodes if "Base Color" in n.inputs and n.bl_idname in ("ShaderNodeGroup", "ShaderNodeBsdfPrincipled")), None)
        if b is None:
            continue
        c0 = b.inputs["Base Color"].default_value
        if 0.2126 * c0[0] + 0.7152 * c0[1] + 0.0722 * c0[2] < 0.05 and max(c0[:3]) < 0.2:
            continue
        oi = nt.nodes.new("ShaderNodeObjectInfo")
        ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.interpolation = 'CONSTANT'
        els = ramp.color_ramp.elements
        els[0].position, els[0].color = 0.0, (*PINTURAS[0], 1)
        els[1].position, els[1].color = 0.25, (*PINTURAS[1], 1)
        for k, c in enumerate(PINTURAS[2:], start=2):
            e = els.new(k / len(PINTURAS)); e.color = (*c, 1)
        for l in list(b.inputs["Base Color"].links):
            nt.links.remove(l)
        nt.links.new(oi.outputs["Random"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
        if "Flakes Color" in b.inputs:                 # metallic flakes were red too: same colour
            for l in list(b.inputs["Flakes Color"].links):
                nt.links.remove(l)
            nt.links.new(ramp.outputs["Color"], b.inputs["Flakes Color"])
    site = bpy.data.collections.get("Site") or bpy.context.scene.collection
    for i, (x, y, h) in enumerate(AUTOS):
        e = bpy.data.objects.new(f"Auto_{i}", None)
        e.instance_type = 'COLLECTION'
        e.instance_collection = src
        e.location = (x, y, 0.03)                                  # on the pavers / asphalt
        e.rotation_euler = (0, 0, math.radians(h))
        site.objects.link(e)
    print(f"[biblioteca] autos: {len(AUTOS)} instancias de {len(src.objects)} objetos")


def build(M):
    if os.environ.get("BIBLIO", "1") == "0" or not os.path.isfile(LIB):
        return
    KEPT.clear()
    coll = bpy.data.collections.get("Biblioteca") or bpy.data.collections.new("Biblioteca")
    if coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)
    _remove_prefix(CAMA_QUITAR + SOFA_QUITAR)
    L = _load(coll)
    parts = _bed(L, coll)
    if os.environ.get("ACABADOS", "original") == "original":
        _runner(parts, coll)
    _headboard(L, coll, M)
    _front_pillows(coll)
    _cushions(L, coll)
    _towel(coll)
    SOFA[:] = {"teddy": _sofa, "hunyuan": _sofa_hunyuan}.get(SOFA_MODO, _sofa_codigo)(coll)
    _sofa_pillows(L, coll)
    if os.environ.get("ACABADOS", "original") != "original":     # photos 1/5: roller blind only, no curtains
        _curtains(L, coll)
    _autos()
    # _monstera(L, coll): 1.2 m wide, no free corner (bath door 50 cm, sofa and desk at the window, v_cuarto camera)
    # drop everything of the library that was not used (roots, guides, the other bed and curtain, legs, headboard)
    used = KEPT
    for o in L.values():
        if o not in used and o.name in bpy.data.objects:
            bpy.data.objects.remove(o, do_unlink=True)
    from . import imperfecciones
    imperfecciones.variacion_medida()                 # after the library objects exist (measured against photo 5)
    print(f"[biblioteca] {len(coll.objects)} objetos de biblioteca")
    for o in coll.objects:
        o.hide_render = o.hide_viewport = False
        for m in [m for m in o.modifiers if m.type in ('COLLISION',)]:
            o.modifiers.remove(m)
    if os.environ.get("ACABADOS", "original") == "original":       # after the unhide loop: drop the blue foot blanket
        for o in coll.objects:
            if o.name.startswith("Plane.021"):
                o.hide_render = o.hide_viewport = True
