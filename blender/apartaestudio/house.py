"""Apartaestudio con balcón — configuration read by run.py and the tools (bpy-free)."""
import math
import os
from .plan import *

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")   # Poly Haven CC0, see assets/sources.json
# texture id -> real-world size of one tile of the image (m), from the Poly Haven asset info
TEX_SIZE = {"large_floor_tiles_02": 3.0, "large_grey_tiles": 3.0, "oak_veneer_01": 1.83, "walnut_veneer": 1.8,
            "rough_linen": 0.27, "waffle_pique_cotton": 0.28, "poly_wool_herringbone": 0.27, "white_plaster_02": 1.0,
            "concrete_floor_02": 2.0}


def pbr(name, tid, albedo, var=0.6, rough=None, normal=1.0, coat=0.0, sheen=0.0, scale=1.0):
    """Principled material from a downloaded Poly Haven texture set, box-projected in object space at true scale.
    The scan's own colour is discarded: its luminance, normalised by its mean, modulates `albedo` (the colour read
    from the listing photos) with strength `var`, so grain, joints and weave survive but the hue matches the unit."""
    import bpy
    import numpy as np
    from archviz import materials as _m
    m, nt, b = _m._new(name)
    s = 1.0 / (TEX_SIZE[tid] * scale)
    vec = _m.mapped(nt, (s, s, s))
    d = os.path.join(ASSETS, "tex", tid)
    tex = _m.image_texture(nt, os.path.join(d, "diff.jpg"), vec, box=True)
    px = np.empty(len(tex.image.pixels), np.float32); tex.image.pixels.foreach_get(px)
    px = px.reshape(-1, 4)[::97, :3]
    mean = float((px @ np.array([0.2126, 0.7152, 0.0722], np.float32)).mean()) or 0.5
    bw = nt.nodes.new("ShaderNodeRGBToBW"); nt.links.new(bw.inputs["Color"], tex.outputs["Color"])
    v = nt.nodes.new("ShaderNodeMath"); v.operation = 'MULTIPLY_ADD'; v.use_clamp = False
    nt.links.new(v.inputs[0], bw.outputs["Val"]); v.inputs[1].default_value = var / mean; v.inputs[2].default_value = 1.0 - var
    col = _m._mixrgb(nt, 1.0, albedo, v.outputs["Value"], 'MULTIPLY')
    nt.links.new(b.inputs["Base Color"], col)
    if rough is None:
        nt.links.new(b.inputs["Roughness"], _m.image_texture(nt, os.path.join(d, "rough.jpg"), vec, data=True, box=True).outputs["Color"])
    else:
        _m._set(b, "Roughness", rough)
    if normal > 0:
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = normal
        nt.links.new(nm.inputs["Color"], _m.image_texture(nt, os.path.join(d, "nor_gl.jpg"), vec, data=True, box=True).outputs["Color"])
        nt.links.new(b.inputs["Normal"], nm.outputs["Normal"])
    _m._set(b, "Coat Weight", coat); _m._set(b, "Sheen Weight", sheen)
    return m
from .shots import SHOTS, BY_NAME, TITLES

NAME = "apartaestudio"
TITLE = "Apartaestudio con balcón"
BLEND = "apartaestudio.blend"
MODULES = ["shell", "interior", "props", "muebles", "detalles", "atmosfera", "surroundings"]   # muebles replaces generados


def materials():
    """Default library + the finishes seen in the photos."""
    import bpy
    from archviz import materials as _m
    M = _m.build_materials(perf_z0=ZC)
    M['piso'] = _m.tiles("Piso_Porcelanato", (0.84, 0.82, 0.78, 1), grout=(0.78, 0.76, 0.72, 1), size=(0.6, 0.6),
                         gap=0.004, rough=0.28, variation=0.03, mottle=0.25, bump=0.1)
    M['piso_balcon'] = _m.tiles("Piso_Balcon", (0.66, 0.67, 0.66, 1), grout=(0.58, 0.58, 0.57, 1), size=(0.6, 0.6),
                                gap=0.004, rough=0.45, variation=0.04, bump=0.1)
    M['amarillo'] = _m.new_mat("Amarillo_Brillante", (0.93, 0.68, 0.04, 1), rough=0.12, coat=1.0)
    M['meson'] = _m.new_mat("Meson_Gris", (0.30, 0.30, 0.30, 1), rough=0.35)
    M['salpicadero'] = _m.tiles("Salpicadero_3D", (0.72, 0.72, 0.72, 1), grout=(0.55, 0.55, 0.55, 1), size=(0.25, 0.25),
                                gap=0.01, rough=0.3, plane='YZ', variation=0.25, mottle=0.5, bump=1.0)
    M['bano_pared'] = _m.tiles("Bano_Pared", (0.62, 0.62, 0.60, 1), grout=(0.55, 0.55, 0.53, 1), size=(0.6, 0.3),
                               gap=0.004, rough=0.3, plane='XZ', variation=0.05, bump=0.2)
    M['cortina'] = _m.new_mat("Cortina_Enrollable", (0.86, 0.84, 0.78, 1), rough=0.9, sheen=0.3)
    M['cojin_azul'] = _m.fabric("Cojin_Azul", (0.50, 0.64, 0.75, 1))
    M['cabecero'] = _m.fabric("Cabecero_Lino", (0.88, 0.84, 0.74, 1))
    M['sofa'] = _m.fabric("Sofa_Cafe", (0.42, 0.33, 0.26, 1))
    M['pie_cama'] = _m.fabric("Pie_Cama_Negro", (0.10, 0.12, 0.14, 1))
    M['metal_cafe'] = _m.new_mat("Metal_Cafe", (0.16, 0.11, 0.08, 1), rough=0.4, metal=0.7)
    M['puerta_madera'] = _m.wood("Puerta_Madera", light=(0.62, 0.52, 0.42, 1), dark=(0.48, 0.38, 0.30, 1))
    M['fachada'] = _m.new_mat("Fachada", (0.80, 0.80, 0.78, 1), rough=0.8)
    M['mar'] = _m.new_mat("Mar", (0.10, 0.28, 0.36, 1), rough=0.08, spec=0.6)
    # architectural glass: refracts for camera rays but lets shadow and diffuse rays straight through, so the sun
    # lands on the floor (Cycles renders here with refractive caustics off, which would otherwise block it)
    g = bpy.data.materials.new("Vidrio_Ventana"); g.use_nodes = True
    nt = g.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Transmission Weight"].default_value = 1.0; b.inputs["Roughness"].default_value = 0.0
    b.inputs["Base Color"].default_value = (0.96, 0.98, 0.98, 1)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); lp = nt.nodes.new("ShaderNodeLightPath")
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = 'MAXIMUM'
    nt.links.new(mx.inputs[0], lp.outputs["Is Shadow Ray"]); nt.links.new(mx.inputs[1], lp.outputs["Is Diffuse Ray"])
    ms = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(ms.inputs["Fac"], mx.outputs["Value"])
    nt.links.new(ms.inputs[1], b.outputs["BSDF"]); nt.links.new(ms.inputs[2], tr.outputs["BSDF"])
    nt.links.new(nt.nodes["Material Output"].inputs["Surface"], ms.outputs["Shader"])
    M['glass'] = g
    # photographed finishes, replaced by real scanned textures where they exist
    if os.path.isdir(os.path.join(ASSETS, "tex")):
        # matte 60x60 porcelain (audit G2): the scanned glossy tiles mirrored the room and hid the joints
        M['piso'] = _m.tiles("Porcelanato_Mate", (0.68, 0.64, 0.56, 1), grout=(0.56, 0.53, 0.47, 1), size=(0.6, 0.6),
                             gap=0.003, rough=0.45, variation=0.04, mottle=0.2, bump=0.15)
        # photo 3: 60 cm grey-green porcelain with pale, clearly visible joints; the joints carry the depth of the
        # long narrow balcony, so they are drawn explicitly instead of relying on the scan texture
        M['piso_balcon'] = _m.tiles("Piso_Balcon", (0.30, 0.34, 0.31, 1), grout=(0.62, 0.63, 0.60, 1), size=(0.6, 0.6),
                                    gap=0.006, rough=0.35, variation=0.05, mottle=0.25, bump=0.2)
        M['bano_pared'] = pbr("Bano_PH", "large_grey_tiles", (0.56, 0.56, 0.54, 1), var=0.4, rough=0.3, normal=0.4, scale=0.6)
        # smooth matte white paint (audit G1): the plaster scan read as dirty speckles on every wall and ceiling
        M['white_int'] = _m.new_mat("Pintura_Blanca", (0.86, 0.85, 0.81, 1), rough=0.9)
        M['oak'] = M['oak_pale'] = pbr("Roble_PH", "oak_veneer_01", (0.62, 0.47, 0.33, 1), var=0.8, rough=0.5, normal=0.3)
        M['walnut'] = pbr("Nogal_PH", "walnut_veneer", (0.32, 0.20, 0.13, 1), var=0.8, rough=0.45, normal=0.3)
        M['linen_white'] = pbr("Pique_PH", "waffle_pique_cotton", (0.90, 0.90, 0.88, 1), var=0.5, rough=0.9, normal=1.0, sheen=0.5)
        M['cabecero'] = pbr("Cabecero_PH", "rough_linen", (0.80, 0.74, 0.62, 1), var=0.5, rough=0.9, sheen=0.4)
        M['cortina'] = pbr("Cortina_PH", "rough_linen", (0.85, 0.82, 0.75, 1), var=0.4, rough=0.9, sheen=0.3, scale=1.5)
        M['sofa'] = pbr("Sofa_PH", "poly_wool_herringbone", (0.38, 0.30, 0.24, 1), var=0.6, rough=0.95, sheen=0.5)
        M['fachada'] = pbr("Fachada_PH", "concrete_floor_02", (0.78, 0.78, 0.76, 1), var=0.3, rough=0.8, normal=0.4)
    return M


HDRI = os.path.join(ASSETS, "hdri", "kloofendal_48d_partly_cloudy_puresky_2k.hdr")   # photos 2-3 show scattered cumulus
# LUZ=neutra: daylight like the listing photos (high white sun, brighter sky) for photo-vs-render checks;
# the film keeps the golden-hour look
NEUTRA = os.environ.get("LUZ") == "neutra"


def setup_scene(S):
    """Clear Caribbean afternoon light from the sea side (+Y): a real HDRI sky plus the sun lamp for crisp shadows."""
    import bpy
    from archviz import sky as _sky
    # low golden-hour sun straight off the sea, raking through the window wall across the floor and the bed
    if NEUTRA:
        # bright overcast like the listing photos: weak diffuse sun, sky does the lighting
        _sky.setup_day(S, sun_dir=(-0.35, 0.45, 0.82), sun_energy=1.0, sun_color=(1.0, 0.97, 0.93), sun_angle=8.0,
                       strength=1.6, clouds=0.8)
    else:
        _sky.setup_day(S, sun_dir=SUN_DIR, sun_energy=6.0, sun_color=(1.0, 0.76, 0.52), sun_angle=0.6, strength=0.7, clouds=0.4)
    S.render.use_motion_blur = True
    S.cycles.volume_step_rate = 2.0
    if not os.path.isfile(HDRI):
        return
    w = S.world; nt = w.node_tree; nt.nodes.clear()
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value[2] = math.radians(200)
    env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(HDRI, check_existing=True)
    bg = nt.nodes.new("ShaderNodeBackground"); bg.inputs["Strength"].default_value = 1.6 if NEUTRA else 0.55
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(mp.inputs["Vector"], tc.outputs["Generated"]); nt.links.new(env.inputs["Vector"], mp.outputs["Vector"])
    nt.links.new(bg.inputs["Color"], env.outputs["Color"]); nt.links.new(out.inputs["Surface"], bg.outputs["Background"])


SUN_DIR = (-0.30, 0.93, 0.24)             # unit vector TOWARD the sun: west-ish over the sea, ~14 deg up
SKY = dict(sun_dir=SUN_DIR, sun_energy=6.0, sun_color=(1.0, 0.76, 0.52), strength=0.7, sun_elevation=14)

E = 1.6                                   # eye height above the floor
# cameras: one per listing photo (approximate solves; iPhone ultra-wide ~14 mm, main ~24 mm, 36 mm sensor)
CAMS = {
    # re-solved after the independent audit (it found 1, 4, 5 and 7 framed noticeably off)
    'cuarto':   ((3.4, 3.1, Z0 + 1.9), (2.43, 7.19, Z0 + 0.9), 14),     # photo 1: ~15 deg further right, higher
    'mesa':     ((W - 1.35, 7.25, Z0 + 1.1), (W - 0.05, Y_BAL - 0.05, Z0 + 0.8), 24),   # photo 2: table height, at the rail corner
    'balcon':   ((0.2, 7.7, Z0 + 1.5), (3.6, 6.95, Z0 + 1.0), 14),      # photo 3: along the balcony
    'cocina':   ((1.55, 0.65, Z0 + 1.5), (-0.1, 1.85, Z0 + 1.2), 14),   # photo 4: oblique from the kitchen's south end
    'cabecero': ((1.5, 4.2, Z0 + 1.6), (W, 4.95, Z0 + 1.0), 14),        # photo 5: from the bed's foot-right corner, AC in frame
    'bano':     ((3.0, 2.85, Z0 + 1.55), (3.75, 0.8, Z0 + 0.9), 14),    # photo 6: from the door, toward vanity + shower
    'pasillo':  ((0.75, 0.35, Z0 + 1.6), (2.0, 2.3, Z0 + 1.0), 14),     # photo 7: from the entry looking NE: room window left, fridge centre, washer right
}
CAM_RES = {c: (1080, 1920) for c in CAMS}
CAM_RES['pasillo'] = (1080, 1440)
CAM_RES['mesa'] = (1080, 1920)
EXT = []
EXPOSURE_DEFAULT = {'int': 0.0}
EXPOSURE = {'mesa': -0.6, 'balcon': -0.5, 'bano': 0.4, 'pasillo': 0.3, 'cocina': 0.8}   # kitchen sits in the dim corridor
DOF = {}
PHOTO_PAIRS = [('cuarto', 1), ('mesa', 2), ('balcon', 3), ('cocina', 4), ('cabecero', 5), ('bano', 6), ('pasillo', 7)]

GRASS = []
DOORS = None
PROBE_WALLS = []
