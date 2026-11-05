"""Third pass over /Game/Apto/Mapa_Apto (after escena_apto.py): the look of the reference walkthrough.

- sky: the cloudy HDRI (partly cloudy pure sky) on an HDRI backdrop dome instead of the empty sky atmosphere; the
  backdrop's own sky light lights the scene from it
- sea: reflective deep-teal water with two panning layers of a generated wave normal map (was a flat painted plane)
- sun: softer shadows (larger source angle) and warmer
- lamps: the bedside gooseneck lamp switched on
- grade: warm gain, softer contrast, a little more bloom

Run headless (no GPU needed):
    UnrealEditor-Cmd.exe Apartaestudio.uproject -run=pythonscript -script="<this file>" -unattended -nosplash -nullrhi
"""
import os

import unreal

MAP = "/Game/Apto/Mapa_Apto"
R = os.path.join(os.environ["USERPROFILE"], "recorrido-3d")
HDR = os.path.join(R, "openhouse-3d", "houses", "apartaestudio", "assets", "hdri",
                   "kloofendal_48d_partly_cloudy_puresky_2k.hdr")
SEA_N = os.path.join(R, "openhouse-3d", "houses", "apartaestudio", "assets", "gen", "mar_normal.png")
REPORT = os.path.join(R, "ue", "ambiente.txt")
W, Z0 = 4.05, 3.0

els = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
mel = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()
open(REPORT, "w").close()


def log(*a):
    line = "[ambiente] " + " ".join(str(x) for x in a)
    unreal.log(line)
    with open(REPORT, "a", encoding="utf-8") as f:       # the commandlet log drops unreal.log lines
        f.write(line + "\n")


def prop(obj, names, v):
    for k in ([names] if isinstance(names, str) else names):
        try:
            obj.set_editor_property(k, v)
            return True
        except Exception:
            pass
    log("no property", names, "on", type(obj).__name__)
    return False


def ue(x, y, z):
    return unreal.Vector(100 * x, -100 * y, 100 * z)


def import_file(path, dest, name):
    if eal.does_asset_exist(f"{dest}/{name}"):
        return eal.load_asset(f"{dest}/{name}")
    t = unreal.AssetImportTask()
    t.filename, t.destination_path, t.destination_name = path, dest, name
    t.automated, t.save, t.replace_existing = True, True, True
    at.import_asset_tasks([t])
    log("imported", path, "->", t.imported_object_paths)
    return eal.load_asset(f"{dest}/{name}")


def fresh_asset(name, folder, cls, factory):
    path = f"{folder}/{name}"
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    return at.create_asset(name, folder, cls, factory)


les.load_level(MAP)
actors = els.get_all_level_actors()

# ---- sky: HDRI backdrop with the cloudy sky
sky_tex = import_file(HDR, "/Game/Ambiente", "Cielo_Nublado")
log("sky texture", type(sky_tex).__name__ if sky_tex else None)
for a in actors:
    n = a.get_actor_label()
    if n in ("Atmosfera", "Cielo", "Cielo_HDRI") or isinstance(a, (unreal.SkyAtmosphere, unreal.SkyLight)):
        els.destroy_actor(a)
bp = eal.load_blueprint_class("/HDRIBackdrop/Blueprints/HDRIBackdrop")
dome = els.spawn_actor_from_class(bp, unreal.Vector(0, 0, 0))
dome.set_actor_label("Cielo_HDRI")
SKY_GAIN = float(os.environ.get("AMB_SKY", "40"))   # the dome's sky, as seen; the sun-lit scene is ~EV 14
prop(dome, "cubemap", sky_tex)
prop(dome, "intensity", SKY_GAIN)
prop(dome, "size", 300000.0)                  # 3 km dome: beyond the sea plane's visible edge
# the dome has a projected floor (the HDRI's lower half): sink it 60 m so the grass, parking and sea cover it
dome.set_actor_location(unreal.Vector(0, 0, -6000), False, False)
for c in dome.get_components_by_class(unreal.SkyLightComponent):
    # light it adds: the HDRI's captured sky is far stronger than the old atmosphere's, so scale it down with the gain
    prop(c, "intensity", float(os.environ.get("AMB_SKYLIGHT", "2.0")) / SKY_GAIN)
log("hdri dome", dome.get_actor_label(), "gain", SKY_GAIN,
    [c.get_name() for c in dome.get_components_by_class(unreal.ActorComponent)])

# ---- sea material
sea_n = import_file(SEA_N, "/Game/Ambiente", "Mar_Normal")
if sea_n:
    sea_n.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    sea_n.set_editor_property("srgb", False)
    eal.save_loaded_asset(sea_n)
mar = fresh_asset("M_Mar", "/Game/Ambiente", unreal.Material, unreal.MaterialFactoryNew())


def const3(c, x, y):
    e = mel.create_material_expression(mar, unreal.MaterialExpressionConstant3Vector, x, y)
    e.set_editor_property("constant", unreal.LinearColor(*c, 1.0))
    return e


def const(v, x, y):
    e = mel.create_material_expression(mar, unreal.MaterialExpressionConstant, x, y)
    e.set_editor_property("r", v)
    return e


# world-space UVs (the sea plane is km wide), two scales panning in different directions
wp = mel.create_material_expression(mar, unreal.MaterialExpressionWorldPosition, -1400, 0)
mask = mel.create_material_expression(mar, unreal.MaterialExpressionComponentMask, -1250, 0)
mask.set_editor_property("r", True); mask.set_editor_property("g", True)
mel.connect_material_expressions(wp, "", mask, "")
layers = []
for i, (scale, speed) in enumerate(((1.0 / 2400.0, (0.004, 0.011)), (1.0 / 700.0, (-0.009, 0.006)))):
    mul = mel.create_material_expression(mar, unreal.MaterialExpressionMultiply, -1100, i * 250)
    mel.connect_material_expressions(mask, "", mul, "A")
    s = const(scale, -1250, 150 + i * 250)
    mel.connect_material_expressions(s, "", mul, "B")
    pan = mel.create_material_expression(mar, unreal.MaterialExpressionPanner, -950, i * 250)
    pan.set_editor_property("speed_x", speed[0]); pan.set_editor_property("speed_y", speed[1])
    mel.connect_material_expressions(mul, "", pan, "Coordinate")
    tex = mel.create_material_expression(mar, unreal.MaterialExpressionTextureSample, -750, i * 250)
    tex.set_editor_property("texture", sea_n)
    tex.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    mel.connect_material_expressions(pan, "", tex, "UVs")
    layers.append(tex)
# (blend-angle-corrected and flatten-normal are material functions, not expressions: plain add, normalize, then lerp
# toward straight up so the far swells stay gentle)
add = mel.create_material_expression(mar, unreal.MaterialExpressionAdd, -550, 100)
mel.connect_material_expressions(layers[0], "RGB", add, "A")
mel.connect_material_expressions(layers[1], "RGB", add, "B")
nrm = mel.create_material_expression(mar, unreal.MaterialExpressionNormalize, -450, 100)
mel.connect_material_expressions(add, "", nrm, "")
flat = mel.create_material_expression(mar, unreal.MaterialExpressionLinearInterpolate, -300, 100)
mel.connect_material_expressions(nrm, "", flat, "A")
mel.connect_material_expressions(const3((0.0, 0.0, 1.0), -450, 250), "", flat, "B")
mel.connect_material_expressions(const(0.35, -450, 350), "", flat, "Alpha")
mel.connect_material_property(flat, "", unreal.MaterialProperty.MP_NORMAL)
mel.connect_material_property(const3((0.015, 0.09, 0.10), -300, -200), "", unreal.MaterialProperty.MP_BASE_COLOR)
mel.connect_material_property(const(0.06, -300, -100), "", unreal.MaterialProperty.MP_ROUGHNESS)
mel.connect_material_property(const(0.6, -300, -50), "", unreal.MaterialProperty.MP_SPECULAR)
mel.recompile_material(mar)
eal.save_loaded_asset(mar)
n_sea = 0
for a in els.get_all_level_actors():
    if a.get_actor_label().split("_")[0] == "Sea":
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            for i in range(c.get_num_materials()):
                c.set_material(i, mar)
            n_sea += 1
log("sea material on", n_sea, "components")

# ---- sun: softer, warmer
for a in els.get_all_level_actors():
    if a.get_actor_label() == "Sol":
        sc = a.get_component_by_class(unreal.DirectionalLightComponent)
        prop(sc, "light_source_angle", 2.5)      # soft-edged shadows like the reference (was 0.6)
        prop(sc, "temperature", 3900.0)
        prop(sc, "intensity", 14000.0)

# ---- bedside lamp on (gooseneck lamp on the nightstand, muebles.bedside)
for a in els.get_all_level_actors():
    if a.get_actor_label() == "Lampara_Mesa":
        els.destroy_actor(a)
lamp = els.spawn_actor_from_class(unreal.PointLight, ue(W - 0.44, 5.15 - 1.22, Z0 + 0.80))   # under the lamp head
lamp.set_actor_label("Lampara_Mesa")
lc = lamp.get_component_by_class(unreal.PointLightComponent)
prop(lc, "intensity_units", unreal.LightUnits.LUMENS)
prop(lc, "intensity", 350.0)
prop(lc, "use_temperature", True); prop(lc, "temperature", 2700.0)
prop(lc, "source_radius", 3.0)
prop(lc, "attenuation_radius", 400.0)

# ---- grade: warm, gentle contrast, soft glow
for a in els.get_all_level_actors():
    if a.get_actor_label() == "Posproceso":
        s = a.get_editor_property("settings")
        for k, v in (("override_color_gain", True), ("color_gain", unreal.Vector4(1.05, 1.0, 0.93, 1.0)),
                     ("override_color_contrast", True), ("color_contrast", unreal.Vector4(0.92, 0.92, 0.92, 1.0)),
                     ("override_color_saturation", True), ("color_saturation", unreal.Vector4(1.06, 1.06, 1.06, 1.0)),
                     ("override_bloom_intensity", True), ("bloom_intensity", 0.9),
                     ("override_bloom_threshold", True), ("bloom_threshold", 0.8),
                     ("override_vignette_intensity", True), ("vignette_intensity", 0.3)):
            prop(s, k, v)
        a.set_editor_property("settings", s)
        log("grade set")

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
log("saved", MAP)
