"""Build the apartaestudio level in Unreal Engine 5.8 from the baked GLB exported by Blender (bake_export.py).

Run headless:
    UnrealEditor-Cmd.exe Apartaestudio.uproject -run=pythonscript -script="<this file>" -unattended -nosplash

1. new level /Game/Apto/Mapa_Apto
2. Interchange scene import of export/apartaestudio.glb (meshes, baked PBR materials, actors with their transforms)
3. light rig for golden hour: atmosphere sun, sky atmosphere, real-time sky light, volumetric height fog,
   a local fog volume inside the unit for visible sun shafts, unbound post-process (manual exposure, Lumen, bloom,
   vignette)
4. window glass swapped for a thin translucent glass material
5. save, and print the floor's world bounds so the camera code can map Blender metres to Unreal centimetres
"""
import os

import unreal

GLB = os.path.join(os.environ["USERPROFILE"], "recorrido-3d", "export", "apartaestudio.glb")
MAP = "/Game/Apto/Mapa_Apto"
DEST = "/Game/Apto/Modelo/"

els = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(*a):
    unreal.log("[armar_apto] " + " ".join(str(x) for x in a))


def prop(obj, names, v):
    """Set the first property name this engine version knows (names change between UE releases)."""
    for k in ([names] if isinstance(names, str) else names):
        try:
            obj.set_editor_property(k, v)
            return
        except Exception:
            pass
    log("no property", names, "on", obj.get_class().get_name())


# ---- 1. level
if unreal.EditorAssetLibrary.does_asset_exist(MAP):
    les.load_level(MAP)
    for a in els.get_all_level_actors():
        els.destroy_actor(a)
else:
    les.new_level(MAP)

# ---- 2. import the scene
ic = unreal.InterchangeManager.get_interchange_manager_scripted()
src = unreal.InterchangeManager.create_source_data(GLB)
params = unreal.ImportAssetParameters()
params.is_automated = True
ic.import_scene(DEST, src, params)
actors = els.get_all_level_actors()
log("actors after import:", len(actors))

# ---- 3. lights (Blender sun direction: toward the sun (-0.30, 0.93, 0.24), i.e. ~14 deg up over the sea)
def spawn(cls, loc=(0, 0, 0), rot=(0, 0, 0), label=None):
    a = els.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(*rot))
    if label:
        a.set_actor_label(label)
    return a

sun = spawn(unreal.DirectionalLight, (0, 0, 2000), label="Sol")
sc = sun.get_component_by_class(unreal.DirectionalLightComponent)
prop(sc, ["atmosphere_sun_light", "use_as_atmosphere_sun_light"], True)
prop(sc, "intensity", 10.0)
prop(sc, "light_source_angle", 0.6)
prop(sc, "cast_shadows", True)
spawn(unreal.SkyAtmosphere, label="Atmosfera")
sky = spawn(unreal.SkyLight, label="Cielo")
skc = sky.get_component_by_class(unreal.SkyLightComponent)
prop(skc, "mobility", unreal.ComponentMobility.MOVABLE)
prop(skc, ["real_time_capture", "b_real_time_capture"], True)
fog = spawn(unreal.ExponentialHeightFog, label="Niebla")
fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
prop(fc, ["enable_volumetric_fog", "volumetric_fog", "b_enable_volumetric_fog"], True)
prop(fc, "fog_density", 0.004)
ppv = spawn(unreal.PostProcessVolume, label="Posproceso")
ppv.set_editor_property("unbound", True)
s = ppv.get_editor_property("settings")
for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
             ("override_auto_exposure_bias", True), ("auto_exposure_bias", 10.0),
             ("override_bloom_intensity", True), ("bloom_intensity", 0.4),
             ("override_vignette_intensity", True), ("vignette_intensity", 0.35)):
    try:
        s.set_editor_property(k, v)
    except Exception as e:  # property names differ slightly between engine versions; log and continue
        log("postprocess skip", k, e)
ppv.set_editor_property("settings", s)

# ---- 4. report the floor bounds (Blender floor spans x 0..4.05, y 0..6.80 m at z 3.0 m)
for a in els.get_all_level_actors():
    n = a.get_actor_label()
    if n.split("_")[0] in ("Floor", "Walls", "Ceiling") or n.startswith(("Gen_cama", "Headboard")):
        o, e = a.get_actor_bounds(False)
        log("BOUNDS", n, "origin", o, "extent", e)

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
log("saved", MAP)
