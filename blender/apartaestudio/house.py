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
MODULES = ["shell", "interior", "props", "muebles", "detalles", "atmosfera", "surroundings",
           "imperfecciones", "biblioteca"]   # muebles replaces generados; imperfecciones over everything built by
# code; biblioteca (library textiles/decor, BIBLIO=0 turns it off) after it so the models keep their own detail


def materials():
    """Default library + the finishes seen in the photos."""
    import bpy
    from archviz import materials as _m
    M = _m.build_materials(perf_z0=ZC)
    # beige, not near-white: the old 0.84 albedo floor rendered brighter than the white walls (photos 1/5: darker, warmer)
    M['piso'] = _m.tiles("Piso_Porcelanato", (0.72, 0.66, 0.58, 1), grout=(0.66, 0.61, 0.54, 1), size=(0.6, 0.6),
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
        paquete(M)
        ficha(M)
    return M


def ficha(M):
    """Apply the project's finish sheet (ACABADOS_FICHA=<json>): each slot gets the catalogue product of its code."""
    from .catalogo_acabados import leer_ficha, material
    f = leer_ficha()
    if not f:
        return
    keys = {"piso": "piso", "cocina_pared": "salpicadero_pkg"}
    for slot, code in f.items():
        M[keys[slot]] = material(code, slot, pbr)
    print("[ficha] acabados:", f)


# ---- finish packages (MVP): the same unit with another set of finishes, chosen with ACABADOS=<name>.
# 'original' is the unit as photographed; each other package overrides only the finish slots a buyer would choose:
# floor, kitchen cabinets, countertop, splashback, sofa fabric, wall paint, bed wood.
PAQUETE = os.environ.get("ACABADOS", "original")
PAQUETES = {
    'original': "Como en las fotos: porcelanato beige, gabinetes amarillos, cuarzo gris",
    'moderno': "Porcelanato gris 60x60, gabinetes grafito mate, cuarzo blanco, metro blanco, sofá gris",
    'calido': "Piso de roble, gabinetes de nogal, cuarzo crema, azulejo terracota, sofá oliva, paredes cálidas",
}


def paquete(M):
    """Override the buyer-selectable finish slots of M for the chosen package (no-op for 'original')."""
    from archviz import materials as _m
    if PAQUETE == 'moderno':
        M['piso'] = _m.tiles("Porcelanato_Gris", (0.52, 0.52, 0.51, 1), grout=(0.44, 0.44, 0.43, 1), size=(0.6, 0.6),
                             gap=0.002, rough=0.4, variation=0.03, mottle=0.25, bump=0.1)
        M['amarillo'] = _m.new_mat("Grafito_Mate", (0.07, 0.075, 0.08, 1), rough=0.45)
        M['cuarzo'] = _m.new_mat("Cuarzo_Blanco", (0.86, 0.85, 0.83, 1), rough=0.22)
        M['salpicadero_pkg'] = _m.tiles("Metro_Blanco", (0.90, 0.90, 0.89, 1), grout=(0.72, 0.72, 0.70, 1),
                                        size=(0.3, 0.075), gap=0.002, rough=0.12, plane='YZ', variation=0.02,
                                        bump=0.3, offset=0.5)
        M['sofa'] = pbr("Sofa_Gris", "poly_wool_herringbone", (0.40, 0.40, 0.40, 1), var=0.5, rough=0.95, sheen=0.5)
        M['white_int'] = _m.new_mat("Pintura_Blanco_Puro", (0.90, 0.90, 0.89, 1), rough=0.9)
        M['oak'] = M['oak_pale'] = pbr("Nogal_Cama", "walnut_veneer", (0.30, 0.20, 0.14, 1), var=0.8, rough=0.45, normal=0.3)
    elif PAQUETE == 'calido':
        M['piso'] = pbr("Piso_Roble", "oak_veneer_01", (0.58, 0.42, 0.28, 1), var=0.8, rough=0.45, normal=0.5, scale=0.7)
        M['amarillo'] = pbr("Gabinete_Nogal", "walnut_veneer", (0.36, 0.23, 0.15, 1), var=0.8, rough=0.4, normal=0.3)
        M['cuarzo'] = _m.new_mat("Cuarzo_Crema", (0.80, 0.75, 0.66, 1), rough=0.25)
        M['salpicadero_pkg'] = _m.tiles("Azulejo_Terracota", (0.62, 0.36, 0.24, 1), grout=(0.80, 0.76, 0.68, 1),
                                        size=(0.15, 0.15), gap=0.003, rough=0.3, plane='YZ', variation=0.12,
                                        mottle=0.4, bump=0.4)
        M['sofa'] = pbr("Sofa_Oliva", "rough_linen", (0.36, 0.38, 0.24, 1), var=0.5, rough=0.95, sheen=0.5)
        M['white_int'] = _m.new_mat("Pintura_Blanco_Calido", (0.90, 0.86, 0.78, 1), rough=0.9)
    elif PAQUETE != 'original':
        raise ValueError(f"ACABADOS={PAQUETE!r}: unknown package, use one of {sorted(PAQUETES)}")


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
        # 3 deg sun: soft-edged shadows like the pro scenes (Italian Flat uses 5 deg; 0.6 drew hard, fake edges)
        _sky.setup_day(S, sun_dir=SUN_DIR, sun_energy=6.0, sun_color=(1.0, 0.76, 0.52), sun_angle=3.0, strength=0.7, clouds=0.4)
    # stills: no motion blur (run.py turns it back on for the film)
    S.render.use_motion_blur = False
    luces_pro()
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
    _sky_haze(nt, env, bg, tc)


SKY_SAT = 0.65                     # photos 2-3: the sky is paler than the HDRI's saturated blue
SKY_HAZE = (0.86, 0.83, 0.76)      # warm milky band at the horizon (photo 2)
SKY_HAZE_MAX, SKY_HAZE_TOP = 0.45, 0.10  # only hugging the horizon: from inside the window shows low sky only
SKY_CAMERA = 0.55                  # camera rays see the sky dimmer than it lights the room (Italian Flat trick):
                                   # the interior exposure no longer burns the clouds in the window to white


def _sky_haze(nt, env, bg, tc):
    """Desaturate the HDRI and fade it into a warm haze toward the horizon (the open view should melt, not pop)."""
    hs = nt.nodes.new("ShaderNodeHueSaturation"); hs.inputs["Saturation"].default_value = SKY_SAT
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ab = nt.nodes.new("ShaderNodeMath"); ab.operation = 'ABSOLUTE'
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = SKY_HAZE_TOP
    mr.inputs["To Min"].default_value = SKY_HAZE_MAX; mr.inputs["To Max"].default_value = 0.0
    mr.interpolation_type = 'SMOOTHSTEP'
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    ca = next(i for i in mix.inputs if i.name == "A" and i.type == 'RGBA')
    cb = next(i for i in mix.inputs if i.name == "B" and i.type == 'RGBA')
    fac = next(i for i in mix.inputs if i.name == "Factor" and i.type == 'VALUE')
    res = next(o for o in mix.outputs if o.name == "Result" and o.type == 'RGBA')
    cb.default_value = (*SKY_HAZE, 1)
    nt.links.new(env.outputs["Color"], hs.inputs["Color"])
    nt.links.new(hs.outputs["Color"], ca)
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ab.inputs[0])
    nt.links.new(ab.outputs["Value"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], fac)
    nt.links.new(res, bg.inputs["Color"])
    # camera rays: dimmer sky so the clouds survive the interior exposure; lighting keeps the full strength
    lp = nt.nodes.new("ShaderNodeLightPath")
    k = nt.nodes.new("ShaderNodeMath"); k.operation = 'MULTIPLY_ADD'
    k.inputs[1].default_value = SKY_CAMERA - 1.0; k.inputs[2].default_value = 1.0      # 1 + (c - 1) * is_camera
    full = bg.inputs["Strength"].default_value
    st = nt.nodes.new("ShaderNodeMath"); st.operation = 'MULTIPLY'; st.inputs[1].default_value = full
    nt.links.new(lp.outputs["Is Camera Ray"], k.inputs[0])
    nt.links.new(k.outputs["Value"], st.inputs[0])
    nt.links.new(st.outputs["Value"], bg.inputs["Strength"])


def luces_pro():
    """What the dissected pro scenes do (REGLAS_ARCHVIZ.md 5b): a light portal filling the window so Cycles samples
    the sky through it (less noise, brighter bounce), and small warm area fills hidden near the hero furniture."""
    import bpy
    from archviz.mesh import collection

    def area(name, loc, rot, size, energy=0.0, color=(1, 1, 1), portal=False):
        ld = bpy.data.lights.new(name, 'AREA')
        ld.shape = 'RECTANGLE'; ld.size, ld.size_y = size
        ld.energy = energy; ld.color = color
        ld.cycles.is_portal = portal
        ob = bpy.data.objects.new(name, ld)
        ob.location = loc; ob.rotation_euler = rot
        collection('Lights').objects.link(ob)
        return ob
    # window wall y = Y_WIN, full width and height; an area light emits along its local -Z: rotated -90 deg about X
    # that points into the room (-Y)
    area("Portal_Ventana", ((WIN_X[0] + WIN_X[1]) / 2, Y_WIN - 0.03, Z0 + 1.2), (math.radians(-90), 0, 0), (WIN_X[1] - WIN_X[0], 2.4),
         portal=True)
    warm = (1.0, 0.80, 0.62)
    # fills facing down onto the bed and the sofa from just under the ceiling, as the Italian Flat does at its lounge
    area("Relleno_Cama", (W - 1.0, BED_Y, ZC - 0.25), (0, 0, 0), (0.8, 0.6), energy=25.0, color=warm)
    area("Relleno_Sofa", (0.6, 5.7, ZC - 0.25), (0, 0, 0), (0.6, 0.8), energy=18.0, color=warm)


SUN_DIR = (-0.30, 0.93, 0.24)             # unit vector TOWARD the sun: west-ish over the sea, ~14 deg up
SKY = dict(sun_dir=SUN_DIR, sun_energy=6.0, sun_color=(1.0, 0.76, 0.52), strength=0.7, sun_elevation=14)

E = 1.6                                   # eye height above the floor
# cameras: one per listing photo (approximate solves; iPhone ultra-wide ~14 mm, main ~24 mm, 36 mm sensor)
CAMS = {
    # re-solved after the independent audit (it found 1, 4, 5 and 7 framed noticeably off)
    # photo 1: solved from vanishing points (floor joints toward the window, window horizontals, mullions) and the two
    # window-wall corners with the plan width; remoto/fuga_piso.py.  Implies 1.41 m eye height and ~0.51 m floor tiles.
    'cuarto':   ((3.767, 3.325, Z0 + 1.63), (2.149, 6.892, Z0 + 0.817), 14.5),
    'mesa':     ((W - 1.35, 7.25, Z0 + 1.1), (W - 0.05, Y_BAL - 0.05, Z0 + 0.8), 24),   # photo 2: table height, at the rail corner
    'balcon':   ((0.2, 7.7, Z0 + 1.5), (3.6, 6.95, Z0 + 1.36), 14),     # photo 3: along the balcony (pitch -2.3, GeoCalib)
    'cocina':   ((1.55, 0.65, Z0 + 1.5), (-0.1, 1.85, Z0 + 1.2), 14),   # photo 4: oblique from the kitchen's south end
    'cabecero': ((1.511, 4.655, Z0 + 1.526), (3.738, 5.670, Z0 + 1.019), 13.63),   # photo 5: position from the floor grid (remoto/camara_piso05.py), pitch/roll/lens GeoCalib, yaw 24.5;        # photo 5: from the bed's foot-right corner, AC in frame
    'bano':     ((3.0, 2.85, Z0 + 1.55), (3.75, 0.8, Z0 + 1.278), 14),  # photo 6: from the door, toward vanity + shower (pitch -7.1, GeoCalib)
    'pasillo':  ((1.042, 0.069, Z0 + 1.434), (2.449, 2.051, Z0 + 0.849), 14.88),   # photo 7, PnP on 8 model corners (remoto/pnp_pasillo.py), GeoCalib lens: from the entry looking NE: room window left, fridge centre, washer right
}
CAM_RES = {c: (1080, 1920) for c in CAMS}
CAM_ROLL = {'cuarto': 4.1, 'mesa': 3.7, 'cabecero': 3.3, 'bano': -3.0, 'pasillo': 0.5}   # cuarto: vanishing points; rest: GeoCalib (fotos/geocalib.json)                     # degrees, photo 1 was held slightly tilted
CAM_RES['pasillo'] = (1080, 1440)
CAM_RES['mesa'] = (1080, 1920)

# sales cameras (v_*): how the pro scenes shoot (REGLAS_ARCHVIZ.md 5b). The target sits at the camera's own height,
# so the camera is LEVEL and verticals stay parallel; framing comes from the lens shift (negative = more floor).
# Wide 20-24 mm only for whole-room views, 50 mm for corner/detail views at table height with soft depth of field.
VENTA = {
    'v_cuarto':  ((0.45, 2.95, Z0 + 1.25), (2.7, Y_WIN, Z0 + 1.25), 20, -0.06),   # room from the inner corner to the window
    'v_cama':    ((0.9, 6.45, Z0 + 1.15), (W, 4.4, Z0 + 1.15), 24, -0.08),       # bed and prints from the window side
    'v_cocina':  ((1.55, 2.6, Z0 + 1.25), (0.0, 0.9, Z0 + 1.25), 24, -0.10),     # counter from the room end
    'v_bano':    ((3.25, 3.15, Z0 + 1.3), (3.4, 0.4, Z0 + 1.3), 20, -0.08),      # bath from its door
    # nightstand, lamp and the bed's pillow corner, from the room side at table height (first try sat on the pillow)
    'v_detalle': ((2.35, 3.0, Z0 + 0.95), (3.85, 4.25, Z0 + 0.95), 40, -0.22),     # shift down: nightstand in frame
}
for _n, (_loc, _tgt, _lens, _sy) in VENTA.items():
    CAMS[_n] = (_loc, _tgt, _lens)
    CAM_RES[_n] = (1920, 1080)
CAM_SHIFT = {n: (0.0, v[3]) for n, v in VENTA.items()}
EXT = []
EXPOSURE_DEFAULT = {'int': 0.0}
EXPOSURE = {'mesa': -0.6, 'balcon': -0.5, 'bano': 0.4, 'pasillo': 0.3, 'cocina': 0.8}   # kitchen sits in the dim corridor
if NEUTRA:   # photo-twin renders: per-camera exposure measured against each listing photo (median linear luminance)
    EXPOSURE = {'cuarto': 0.67, 'mesa': -0.34, 'balcon': -0.53, 'cocina': 1.33, 'cabecero': -0.22, 'bano': 0.8, 'pasillo': 1.09}
DOF = {'v_detalle': 2.4}                  # f-stop: soft background on the detail shot, as in the pro scenes
PHOTO_PAIRS = [('cuarto', 1), ('mesa', 2), ('balcon', 3), ('cocina', 4), ('cabecero', 5), ('bano', 6), ('pasillo', 7)]

GRASS = []
DOORS = None
PROBE_WALLS = []


# ---------------------------------------------------------------- per-photo light mix (LUZ=neutra)
# Solved, not eyeballed: remoto/luces_separadas.py renders each light group alone (linear), remoto/ajustar_luz.py
# finds the group weights / tints whose sum best matches the photo per object (CIELAB medians).  Both photos agree
# on the main point: the studio fill lights (Relleno_*) were ~60 % of the light in frame and the real room has none.
LUZ_FOTO = {
    # photo 1, physical model (ajustar_luz.py --fisico, each lamp rendered alone): no fills, warm ~3000 K downlights,
    # one camera white balance for the whole frame.  Free per-lamp weights + free tints gave unphysical, unstable mixes.
    # exp: closed-loop exposure trim (stops) after measuring the real render: the per-channel tone table of
    # ajustar_luz.py over-predicts AgX whites, so walls came out ~1.75x darker than predicted
    'cuarto':   dict(exp=0.0, wb=(0.828, 0.806, 0.662), calido=(1.0, 0.72, 0.45),
                     pesos={'cielo': 4.886, 'otros': 0.032, 'foco_L_Down_1.2_1.2': 1.867, 'foco_L_Down_1.5_5.8': 7.727, 'foco_L_Down_2.0_3.3': 0.376, 'foco_L_Down_2.2_0.6': 4.76, 'foco_L_Down_3.4_0.6': 0.292, 'foco_L_Down_3.4_1.9': 0.074, 'focos_emis': 0.592}),
    'cabecero': dict(cielo=(1.645, (0.999, 1.510, 1.247)), focos=(0.870, (1.040, 0.768, 1.137)), rellenos=0.321),
}
_LUZ_BASE = {}


def grupo_luz(nombre, tipo=""):
    """Same grouping as remoto/luces_separadas.py: each downlight and each fill is its own group."""
    n = nombre.lower()
    if tipo == 'SUN' or any(k in n for k in ("cielo", "sky", "mar", "sea", "sol")):
        return "cielo"
    if "down" in n:
        return ("foco_" + nombre) if tipo else "focos_emis"
    if "relleno" in n:
        return "rell_" + nombre
    return "otros"


def _mezcla(mix, g):
    """(weight, rgb tint) of light group g under a LUZ_FOTO entry (physical or legacy format)."""
    if not mix:
        return 1.0, (1.0, 1.0, 1.0)
    if 'pesos' in mix:
        wb = mix.get('wb', (1, 1, 1))
        if g.startswith("rell"):
            return 0.0, wb
        t = tuple(a * b for a, b in zip(wb, mix.get('calido', (1, 1, 1)))) if g.startswith("foco") else wb
        return mix['pesos'].get(g, 1.0), t
    v = mix.get("focos" if g.startswith("foco") else "rellenos" if g.startswith("rell") else g, 1.0)
    return v if isinstance(v, tuple) else (v, (1.0, 1.0, 1.0))


def before_render(S, name):
    """run.py hook, once per camera: apply that photo's solved light mix (photo-check mode only)."""
    import bpy
    if not NEUTRA or os.environ.get("LUZ_FOTO", "1") == "0":
        return
    B = _LUZ_BASE
    if not B:                                           # remember the base values once
        B['luces'] = [(o, o.data.energy, tuple(o.data.color), grupo_luz(o.name, o.data.type))
                      for o in bpy.data.objects if o.type == 'LIGHT']
        B['emis'] = []
        for m in bpy.data.materials:
            if not m.use_nodes:
                continue
            for nd in m.node_tree.nodes:
                s = (nd.inputs.get("Emission Strength") if nd.bl_idname == "ShaderNodeBsdfPrincipled"
                     else nd.inputs.get("Strength") if nd.bl_idname == "ShaderNodeEmission" else None)
                if s is not None and not s.is_linked and s.default_value > 0:
                    B['emis'].append((s, s.default_value, grupo_luz(m.name)))
        B['mundo'] = []
        if S.world and S.world.use_nodes:
            nt = S.world.node_tree
            for nd in [n for n in nt.nodes if n.bl_idname == "ShaderNodeBackground"]:
                st, col = nd.inputs["Strength"], nd.inputs["Color"]
                tint = None
                if col.is_linked:                        # tint a textured sky through a multiply node
                    tint = nt.nodes.new("ShaderNodeMix"); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'
                    tint.inputs["Factor"].default_value = 1.0
                    src = col.links[0].from_socket
                    nt.links.new(tint.inputs["A"], src); nt.links.new(col, tint.outputs["Result"])
                    tint.inputs["B"].default_value = (1, 1, 1, 1)
                esc = None
                if st.is_linked:                         # strength driven by nodes (camera-ray dimming): scale after
                    esc = nt.nodes.new("ShaderNodeMath"); esc.operation = 'MULTIPLY'; esc.inputs[1].default_value = 1.0
                    nt.links.new(esc.inputs[0], st.links[0].from_socket); nt.links.new(st, esc.outputs["Value"])
                B['mundo'].append((st, None if esc else st.default_value, col, tuple(col.default_value), tint, esc))
    mix = LUZ_FOTO.get(name, {})
    # The sky keeps its own strength and the common factor goes to the view exposure (exact, linear).  Scaling the
    # lights themselves x5 lost energy to Cycles' indirect clamp, so renders came out ~1.7x darker than solved.
    kc, tc = _mezcla(mix, "cielo")
    norm = kc * max(tc) if kc * max(tc) > 1e-6 else 1.0
    S.view_settings.exposure += mix.get('exp', 0.0) + math.log2(norm)   # run.py has just set the base exposure
    for o, e, c, g in B['luces']:
        k, t = _mezcla(mix, g)
        o.data.energy = e * k * max(t) / norm; o.data.color = tuple(min(1.0, a * b / max(t)) for a, b in zip(c, t))
    for s, v, g in B['emis']:
        k, t = _mezcla(mix, g)
        s.default_value = v * k * (0.2126 * t[0] + 0.7152 * t[1] + 0.0722 * t[2]) / norm   # emission keeps its colour
    k, t = kc / norm, tc
    for st, v, col, c, tint, esc in B['mundo']:
        if esc is not None:
            esc.inputs[1].default_value = k * max(t)
        else:
            st.default_value = v * k * max(t)
        tn = tuple(x / max(t) for x in t) + (1,)
        if tint is not None:
            tint.inputs["B"].default_value = tn
        else:
            col.default_value = tuple(a * b for a, b in zip(c, tn))
    print(f"[luz] {name}: {mix if mix else 'mezcla base'}")
