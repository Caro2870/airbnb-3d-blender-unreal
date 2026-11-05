"""Second pass over /Game/Apto/Mapa_Apto (after armar_apto.py): light direction, glass, interior haze, downlights,
the walkthrough cameras and sequence from houses/apartaestudio/shots.py, and Movie Render Queue configs.

    UnrealEditor-Cmd.exe Apartaestudio.uproject -run=pythonscript -script="<this file>" -unattended -nosplash -nullrhi

Blender metres -> Unreal centimetres, measured from the imported floor / bed bounds:  UE = (100 x, -100 y, 100 z).
"""
import math
import os

import unreal

MAP = "/Game/Apto/Mapa_Apto"
OUT_DIR = os.path.join(os.environ["USERPROFILE"], "recorrido-3d", "ue", "renders").replace("\\", "/")
FPS = 24

# plan.py / shots.py values (kept here so the script has no Blender-side imports)
Z0, ZC, W, Y_WIN, BED_Y = 3.0, 5.5, 4.05, 6.80, 5.15
E = Z0 + 1.55
SUN_TOWARD = (-0.30, 0.93, 0.24)            # Blender: direction from the scene toward the sun
DOWNLIGHTS = [(1.5, 5.8), (2.0, 3.3), (1.2, 1.2), (3.4, 1.9), (3.4, 0.6), (2.24, 0.55), (W / 2, 7.35)]   # as interior.py
# one continuous walk at eye height like the reference (a guest walking in): entrance -> kitchen -> bathroom door ->
# bed -> past the sofa -> out onto the balcony to the sea. Each waypoint: (second, camera, look-at); `stills` picks the
# waypoints rendered as test photos.
WALK = [
    (0.0, (1.25, 0.25, E), (1.4, Y_WIN, Z0 + 1.2)),          # door: the whole unit down to the window
    (3.0, (1.35, 0.85, E), (0.2, 1.6, Z0 + 1.15)),           # turn to the kitchen
    (6.5, (1.45, 1.6, E), (0.0, 1.9, Z0 + 1.05)),            # along the counter
    (9.5, (1.6, 2.4, E), (2.6, 6.0, Z0 + 1.1)),              # out of the kitchen, eyes on the room (not the wall)
    # turns only happen out in the open part of the room: turning next to the partitions swept walls across the frame
    (12.0, (2.2, 3.5, E), (2.8, 5.5, Z0 + 1.05)),
    (14.5, (2.4, 3.7, E), (3.3, 1.5, Z0 + 1.0)),             # look back into the bathroom (old bano shot angles)
    (17.5, (3.0, 3.05, E), (3.7, 0.7, Z0 + 0.9)),
    (20.0, (2.5, 3.75, E), (3.3, 1.5, Z0 + 1.0)),            # step back out still facing the bathroom
    (22.5, (2.3, 3.9, E), (W, 5.0, Z0 + 0.95)),              # the bed and the prints
    (26.0, (1.55, 4.7, E), (W, 5.6, Z0 + 1.1)),
    (29.5, (1.7, 5.7, E), (1.6, 9.0, Z0 + 1.2)),             # past the sofa toward the light
    (33.0, (2.0, 6.6, E), (1.9, 11.0, Z0 + 1.0)),
    (36.5, (2.75, 7.3, E), (1.0, 80.0, Z0 - 0.6)),           # on the balcony: palms, field, sea
    (40.5, (3.3, 7.6, E + 0.05), (6.0, 120.0, Z0 - 1.2)),
]
WALK_STILLS = (0, 2, 6, 8, 12)
SHOTS = [dict(name='recorrido', sec=WALK[-1][0] + 1.0, lens=18, fstop=5.6, walk=WALK)]
OLD_SHOTS = [
    dict(name='entrada', sec=5.0, lens=22, fstop=5.6,
         wp=[((1.25, 0.3, E), (1.5, Y_WIN, Z0 + 1.2)), ((1.25, 1.3, E), (1.1, Y_WIN, Z0 + 1.1)), ((1.3, 2.3, E), (1.0, 5.5, Z0 + 1.0))]),
    dict(name='cocina', sec=5.0, lens=20, fstop=5.6,
         wp=[((1.55, 0.55, E), (0.0, 0.9, Z0 + 1.2)), ((1.5, 1.4, E), (0.0, 1.7, Z0 + 1.2)), ((1.45, 2.3, E), (0.2, 3.0, Z0 + 1.1))]),
    dict(name='habitacion', sec=6.0, lens=21, fstop=5.6,
         wp=[((1.3, 3.3, E), (3.8, BED_Y, Z0 + 0.9)), ((1.2, 4.5, E), (W, BED_Y, Z0 + 1.0)), ((1.5, 5.9, E), (3.6, 4.4, Z0 + 1.0))]),
    dict(name='bano', sec=4.0, lens=18, fstop=5.6,
         wp=[((2.4, 3.7, E), (3.3, 1.5, Z0 + 1.0)), ((3.2, 2.95, E), (3.7, 0.6, Z0 + 0.8))]),
    dict(name='balcon', sec=7.0, lens=22, fstop=8,
         wp=[((2.0, 5.2, E), (2.0, 8.5, Z0 + 1.2)), ((2.0, 6.6, E), (1.9, 11.0, Z0 + 1.0)),
             ((2.75, 7.25, E), (1.0, 80.0, Z0 - 1.0)), ((3.35, 7.55, E + 0.1), (6.0, 120.0, Z0 - 2.0))]),
]

els = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
at = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary


def log(*a):
    unreal.log("[escena_apto] " + " ".join(str(x) for x in a))


def prop(obj, names, v):
    for k in ([names] if isinstance(names, str) else names):
        try:
            obj.set_editor_property(k, v)
            return True
        except Exception:
            pass
    log("no property", names, "on", type(obj).__name__)
    return False


def enum(cls, *names):
    """First enum value this engine version has (Python enum names drift between UE releases)."""
    for n in names:
        if hasattr(cls, n):
            return getattr(cls, n)
    log("enum", cls.__name__, "has none of", names, "; values:", [k for k in dir(cls) if k.isupper()])
    return None


def ue(p):
    return unreal.Vector(100 * p[0], -100 * p[1], 100 * p[2])


def look(pos, tgt):
    d = (tgt[0] - pos[0], -(tgt[1] - pos[1]), tgt[2] - pos[2])
    yaw = math.degrees(math.atan2(d[1], d[0]))
    pitch = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
    return pitch, yaw


def labelled(name):
    return [a for a in els.get_all_level_actors() if a.get_actor_label() == name]


def fresh_actor(cls, name, loc=unreal.Vector(0, 0, 0), rot=unreal.Rotator(0, 0, 0)):
    for a in labelled(name):
        els.destroy_actor(a)
    a = els.spawn_actor_from_class(cls, loc, rot)
    a.set_actor_label(name)
    return a


def fresh_asset(name, folder, cls, factory):
    path = f"{folder}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.delete_asset(path)
    return at.create_asset(name, folder, cls, factory)


les.load_level(MAP)

# ---- sun: a directional light points along its forward vector, i.e. away from the sun
fx, fy, fz = -SUN_TOWARD[0], SUN_TOWARD[1], -SUN_TOWARD[2]          # negate, then Blender y -> -UE y
sun = labelled("Sol")[0]
sun.set_actor_rotation(unreal.Rotator(roll=0, pitch=math.degrees(math.asin(fz)), yaw=math.degrees(math.atan2(fy, fx))), False)
sc = sun.get_component_by_class(unreal.DirectionalLightComponent)
prop(sc, "intensity", 20000.0)                      # lux, low golden-hour sun
prop(sc, ["use_temperature"], True); prop(sc, "temperature", 4300.0)
prop(sc, "volumetric_scattering_intensity", 4.0)    # makes the shafts through the window read in the haze
log("sun rotation", sun.get_actor_rotation())

for sky in labelled("Cielo"):            # gone once ambiente.py has put the HDRI dome (and its sky light) in
    prop(sky.get_component_by_class(unreal.SkyLightComponent), "intensity", 1.6)

# ---- global fog: thin outdoors, volumetric on so local fog and the sun shafts render into it
fog = labelled("Niebla")[0]
fog.set_actor_location(unreal.Vector(0, 0, 300), False, False)
fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
prop(fc, "fog_density", 0.0015)
prop(fc, ["enable_volumetric_fog", "volumetric_fog"], True)
prop(fc, "volumetric_fog_extinction_scale", 1.0)
prop(fc, "volumetric_fog_scattering_distribution", 0.6)
prop(fc, "volumetric_fog_start_distance", 0.0)

# ---- interior haze (only inside the unit, so the sea view stays clear)
haze = fresh_actor(unreal.LocalFogVolume, "Bruma_Interior", ue((W / 2, 4.6, Z0 + 1.25)))
haze.set_actor_scale3d(unreal.Vector(2.6, 3.4, 1.6))
hc = haze.get_component_by_class(unreal.LocalFogVolumeComponent)
if hc:
    prop(hc, "radial_fog_extinction", 0.06)
    prop(hc, "height_fog_extinction", 0.0)
    prop(hc, "fog_phase_g", 0.55)
    prop(hc, "fog_albedo", unreal.LinearColor(1.0, 0.97, 0.92, 1.0))

# ---- exposure: histogram auto exposure clamped to an interior-in-daylight range
ppv = labelled("Posproceso")[0]
s = ppv.get_editor_property("settings")
for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_HISTOGRAM),
             ("override_auto_exposure_bias", True), ("auto_exposure_bias", 0.0),
             ("override_auto_exposure_min_brightness", True), ("auto_exposure_min_brightness", 10.5),
             ("override_auto_exposure_max_brightness", True), ("auto_exposure_max_brightness", 12.5),
             ("override_auto_exposure_speed_up", True), ("auto_exposure_speed_up", 1.5),
             ("override_auto_exposure_speed_down", True), ("auto_exposure_speed_down", 1.0),
             ("override_indirect_lighting_intensity", True), ("indirect_lighting_intensity", 1.8),
             ("override_lumen_scene_lighting_quality", True), ("lumen_scene_lighting_quality", 2.0),
             ("override_lumen_final_gather_quality", True), ("lumen_final_gather_quality", 2.0),
             ("override_lumen_max_trace_distance", True), ("lumen_max_trace_distance", 2000.0),
             ("override_bloom_intensity", True), ("bloom_intensity", 0.5),
             ("override_vignette_intensity", True), ("vignette_intensity", 0.4),
             ("override_film_grain_intensity", True), ("film_grain_intensity", 0.08),
             ("override_scene_fringe_intensity", True), ("scene_fringe_intensity", 0.4),
             ("override_motion_blur_amount", True), ("motion_blur_amount", 0.5)):
    prop(s, k, v)
ppv.set_editor_property("settings", s)

# ---- downlights (Blender's warm ceiling points; the bake exported no lights)
for a in [a for a in els.get_all_level_actors() if a.get_actor_label().startswith("Foco_")]:
    els.destroy_actor(a)
for i, (x, y) in enumerate(DOWNLIGHTS):
    l = fresh_actor(unreal.SpotLight, f"Foco_{i}", ue((x, y, ZC - 0.03)), unreal.Rotator(roll=0, pitch=-90, yaw=0))
    lc = l.get_component_by_class(unreal.SpotLightComponent)
    prop(lc, "intensity_units", unreal.LightUnits.LUMENS)
    prop(lc, "intensity", 1400.0)
    prop(lc, "use_temperature", True); prop(lc, "temperature", 3000.0)
    prop(lc, "outer_cone_angle", 55.0); prop(lc, "inner_cone_angle", 25.0)
    prop(lc, "source_radius", 4.0)
    prop(lc, "attenuation_radius", 600.0)

# ---- glass: thin translucent material, no shadow, so the low sun reaches the floor
glass = fresh_asset("M_Vidrio", "/Game/Apto/Mat", unreal.Material, unreal.MaterialFactoryNew())
prop(glass, "blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
tlm = enum(unreal.TranslucencyLightingMode, "TLM_SURFACE_FORWARD_SHADING", "TLM_SURFACE_PER_PIXEL_LIGHTING",
           "TLM_SURFACE", "SURFACE_FORWARD_SHADING")
if tlm is not None:
    prop(glass, "translucency_lighting_mode", tlm)
for cls, v, prop_id, x in ((unreal.MaterialExpressionConstant, 0.08, unreal.MaterialProperty.MP_OPACITY, -300),
                           (unreal.MaterialExpressionConstant, 0.02, unreal.MaterialProperty.MP_ROUGHNESS, -300),
                           (unreal.MaterialExpressionConstant3Vector, (0.92, 0.97, 0.96), unreal.MaterialProperty.MP_BASE_COLOR, -500)):
    n = mel.create_material_expression(glass, cls, x, 0)
    if cls is unreal.MaterialExpressionConstant:
        n.set_editor_property("r", v)
    else:
        n.set_editor_property("constant", unreal.LinearColor(*v, 1.0))
    mel.connect_material_property(n, "", prop_id)
mel.recompile_material(glass)

# mirror: the baked copy lost its metal, so Lumen draws it black
mirror = fresh_asset("M_Espejo", "/Game/Apto/Mat", unreal.Material, unreal.MaterialFactoryNew())
for v, prop_id in ((1.0, unreal.MaterialProperty.MP_METALLIC), (0.03, unreal.MaterialProperty.MP_ROUGHNESS)):
    n = mel.create_material_expression(mirror, unreal.MaterialExpressionConstant, -300, 0)
    n.set_editor_property("r", v)
    mel.connect_material_property(n, "", prop_id)
n = mel.create_material_expression(mirror, unreal.MaterialExpressionConstant3Vector, -500, 0)
n.set_editor_property("constant", unreal.LinearColor(0.95, 0.96, 0.96, 1.0))
mel.connect_material_property(n, "", unreal.MaterialProperty.MP_BASE_COLOR)
mel.recompile_material(mirror)

# paint: the baked wall / ceiling maps came out grey-brown; the photos show matte white paint
paint = fresh_asset("M_Pintura", "/Game/Apto/Mat", unreal.Material, unreal.MaterialFactoryNew())
n = mel.create_material_expression(paint, unreal.MaterialExpressionConstant3Vector, -500, 0)
n.set_editor_property("constant", unreal.LinearColor(0.80, 0.79, 0.76, 1.0))
mel.connect_material_property(n, "", unreal.MaterialProperty.MP_BASE_COLOR)
n = mel.create_material_expression(paint, unreal.MaterialExpressionConstant, -300, 200)
n.set_editor_property("r", 0.85)
mel.connect_material_property(n, "", unreal.MaterialProperty.MP_ROUGHNESS)
mel.recompile_material(paint)
PAINT_ACTORS = ("Ceiling",)

mats = set()
n_glass = 0
for a in els.get_all_level_actors():
    for comp in a.get_components_by_class(unreal.StaticMeshComponent):
        for i in range(comp.get_num_materials()):
            m = comp.get_material(i)
            if m is None:
                continue
            mats.add(m.get_name())
            if m.get_name().lower().startswith("mirror"):
                comp.set_material(i, mirror)
            elif m.get_name().startswith("Pared_PH") or a.get_actor_label().split("_")[0] in PAINT_ACTORS:
                comp.set_material(i, paint)
            elif any(k in m.get_name().lower() for k in ("vidrio", "glass", "cristal")) and "negro" not in m.get_name().lower():
                comp.set_material(i, glass)
                prop(comp, "cast_shadow", False)
                n_glass += 1
log("materials:", sorted(mats))

# leaves are single planes: two-sided, or the path tracer renders their back faces black
for path in unreal.EditorAssetLibrary.list_assets("/Game/Apto/Modelo", recursive=True, include_folder=False):
    if "leaves" not in path.lower() and "leaf" not in path.lower():
        continue
    mi = unreal.EditorAssetLibrary.load_asset(path)
    if isinstance(mi, unreal.MaterialInstanceConstant):
        o = mi.get_editor_property("base_property_overrides")
        prop(o, "override_two_sided", True); prop(o, "two_sided", True)
        mi.set_editor_property("base_property_overrides", o)
        unreal.MaterialEditingLibrary.update_material_instance(mi)
        unreal.EditorAssetLibrary.save_loaded_asset(mi)
        log("two-sided", path)
log("glass slots replaced:", n_glass)

# ---- cameras + sequences
EXPOSURE_BIAS = 2.5     # EV on top of the physical camera exposure below (bracketed: 0 crushes the shadow side)
PT_BIAS = float(__import__("os").environ.get("LUZ_PT_BIAS", "0.5"))   # path tracer: 2.5 blew the sunlit room out
PT_DENOISE = 1
# the default NNE denoiser (ONNX on DirectML) returned all-black frames on the RTX 5060 Ti: route the path tracer to
# the OIDN plugin instead (or another NNE runtime), picked with LUZ_DENOISER=oidn|nne_gpu|nne_cpu
import os as _os
DENOISER = _os.environ.get("LUZ_DENOISER", "oidn")
DENOISER_CMDS = {
    "oidn": ["NNEDenoiser 0", "r.PathTracing.Denoiser.Name OIDN Denoiser Plugin"],
    "nne_gpu": ["NNEDenoiser.Runtime.Type 1", "NNEDenoiser.Runtime.Name NNERuntimeORTDml"],
    "nne_cpu": ["NNEDenoiser.Runtime.Type 0", "NNEDenoiser.Runtime.Name NNERuntimeORTCpu"],
}[DENOISER]
PT_TEST_SPP = int(_os.environ.get("LUZ_PT_SPP", "256"))


def camera(name, lens, fstop, focus=250.0, bias=None):
    """Cine camera with physical exposure (ISO 100, 1/60 s, its own f-stop), set on the camera itself so nothing in
    the level's post-process stack can override it."""
    cam = fresh_actor(unreal.CineCameraActor, name)
    cc = cam.get_cine_camera_component()
    prop(cc, "filmback", unreal.CameraFilmbackSettings(sensor_width=36.0, sensor_height=20.25))
    prop(cc, "current_focal_length", float(lens))
    prop(cc, "current_aperture", float(fstop))
    fs = unreal.CameraFocusSettings()
    fs.focus_method = unreal.CameraFocusMethod.MANUAL
    fs.manual_focus_distance = focus
    prop(cc, "focus_settings", fs)
    pp = cc.get_editor_property("post_process_settings")
    for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                 ("override_auto_exposure_apply_physical_camera_exposure", True), ("auto_exposure_apply_physical_camera_exposure", True),
                 ("override_auto_exposure_bias", True), ("auto_exposure_bias", EXPOSURE_BIAS if bias is None else bias),
                 ("override_camera_iso", True), ("camera_iso", 100.0),
                 ("override_camera_shutter_speed", True), ("camera_shutter_speed", 60.0),
                 ("override_depth_of_field_fstop", True), ("depth_of_field_fstop", float(fstop))):
        prop(pp, k, v)
    prop(cc, "post_process_settings", pp)
    prop(cc, "post_process_blend_weight", 1.0)
    return cam


def channels(sec):
    for f in (lambda: sec.get_all_channels(), lambda: sec.get_channels_by_type(unreal.MovieSceneScriptingDoubleChannel),
              lambda: sec.get_channels_by_type(unreal.MovieSceneScriptingFloatChannel)):
        try:
            ch = list(f())
            if ch:
                return ch
        except Exception:
            pass
    raise RuntimeError("no transform channels")


def binding_id(seq, b):
    for f in (lambda: seq.get_portable_binding_id(seq, b), lambda: unreal.MovieSceneSequenceExtensions.get_portable_binding_id(seq, seq, b),
              lambda: seq.get_binding_id(b), lambda: b.get_binding_id()):
        try:
            return f()
        except Exception:
            pass
    raise RuntimeError("no binding id")


def sequence(name, cuts):
    """cuts: [(camera actor, [(frame, pos, tgt), ...], length)] played back to back."""
    seq = fresh_asset(name, "/Game/Apto", unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    seq.set_display_rate(unreal.FrameRate(FPS, 1))
    total = sum(c[2] for c in cuts)
    seq.set_playback_start(0); seq.set_playback_end(total)
    cut_track = seq.add_track(unreal.MovieSceneCameraCutTrack)
    t0 = 0
    for cam, keys, length in cuts:
        b = seq.add_possessable(cam)
        sec = b.add_track(unreal.MovieScene3DTransformTrack).add_section()
        sec.set_range(t0, t0 + length)
        ch = channels(sec)
        prev_yaw = None
        for f, pos, tgt in keys:
            pitch, yaw = look(pos, tgt)
            if prev_yaw is not None:                     # unwrap so keys never spin the long way round
                yaw = prev_yaw + ((yaw - prev_yaw + 180) % 360 - 180)
            prev_yaw = yaw
            p = ue(pos)
            for c, v in zip(ch[:6], (p.x, p.y, p.z, 0.0, pitch, yaw)):
                c.add_key(unreal.FrameNumber(t0 + f), v)
        cs = cut_track.add_section()
        cs.set_range(t0, t0 + length)
        cs.set_camera_binding_id(binding_id(seq, b))
        t0 += length
    return seq


film = []
film_pt = []
stills = []
pt_stills = []
for sh in SHOTS:
    n = int(round(sh['sec'] * FPS))
    if 'walk' in sh:                     # timed waypoints of the continuous walk
        keys = [(round(t * FPS), p, g) for t, p, g in sh['walk']]
        film.append((camera(f"Cam_{sh['name']}", sh['lens'], sh['fstop']), keys, n))
        film_pt.append((camera(f"CamPT_{sh['name']}", sh['lens'], sh['fstop'], bias=PT_BIAS), keys, n))
        for j in WALK_STILLS:
            _, p, t = sh['walk'][j]
            stills.append((camera(f"Foto_{j:02d}", sh['lens'], sh['fstop']), [(0, p, t), (1, p, t)], 2))
            pt_stills.append((camera(f"PT_{j:02d}", sh['lens'], sh['fstop'], bias=PT_BIAS), [(0, p, t), (1, p, t)], 2))
        continue
    wp = sh['wp']
    keys = [(round(i * (n - 1) / (len(wp) - 1)), p, t) for i, (p, t) in enumerate(wp)]
    film.append((camera(f"Cam_{sh['name']}", sh['lens'], sh['fstop']), keys, n))
    # the path-traced film needs the path tracer's exposure: the Lumen cameras (+2.5 EV) burned it out
    film_pt.append((camera(f"CamPT_{sh['name']}", sh['lens'], sh['fstop'], bias=PT_BIAS), keys, n))
    # still: the middle of the move
    m = len(wp) // 2
    if len(wp) % 2:
        p, t = wp[m]
    else:
        (p0, t0_), (p1, t1) = wp[m - 1], wp[m]
        p = tuple((a + b) / 2 for a, b in zip(p0, p1)); t = tuple((a + b) / 2 for a, b in zip(t0_, t1))
    stills.append((camera(f"Foto_{sh['name']}", sh['lens'], sh['fstop']), [(0, p, t), (1, p, t)], 2))
    # the path tracer gets the real bounce light that Lumen underestimates, so it needs ~2 EV less
    pt_stills.append((camera(f"PT_{sh['name']}", sh['lens'], sh['fstop'], bias=PT_BIAS), [(0, p, t), (1, p, t)], 2))
sequence("Recorrido", film)
sequence("Recorrido_PT", film_pt)
sequence("Prueba", stills)
sequence("Prueba_PT", pt_stills)
log("sequences: Recorrido", sum(c[2] for c in film), "frames, Prueba", len(stills), "stills")

# ---- Movie Render Queue configs
def mrq(name, res, temporal, fmt, pattern, path_traced=False, spp=1):
    cfg = fresh_asset(name, "/Game/Apto", unreal.MoviePipelinePrimaryConfig, None)
    if cfg is None:
        log("could not create", name)
        return
    o = cfg.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    o.set_editor_property("output_directory", unreal.DirectoryPath(OUT_DIR))
    o.set_editor_property("output_resolution", unreal.IntPoint(*res))
    o.set_editor_property("file_name_format", pattern)
    o.set_editor_property("zero_pad_frame_numbers", 4)
    if path_traced:     # offline-quality light transport; the denoiser plugin cleans the remaining noise
        pt = cfg.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPass_PathTracer)
        prop(pt, ["denoiser", "use_denoiser", "b_denoiser"], True)
    else:
        cfg.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
    cfg.find_or_add_setting_by_class(fmt)
    aa = cfg.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
    prop(aa, "override_anti_aliasing", path_traced)
    prop(aa, "spatial_sample_count", spp)
    prop(aa, "temporal_sample_count", temporal)
    prop(aa, "engine_warm_up_count", 64)          # let Lumen and auto exposure settle on every cut
    prop(aa, "render_warm_up_count", 32)
    prop(aa, "render_warm_up_frames", True)
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineGameOverrideSetting)
    cv = cfg.find_or_add_setting_by_class(unreal.MoviePipelineConsoleVariableSetting)
    cvars = [("r.MotionBlurQuality", 4), ("r.VolumetricFog.GridPixelSize", 4), ("r.VolumetricFog.GridSizeZ", 128),
             ("r.LocalFogVolume.GlobalStartDistance", 0)]
    if path_traced:
        cvars += [("r.PathTracing.Denoiser", PT_DENOISE)]
    for k, v in cvars:
        try:
            cv.add_or_update_console_variable(k, v)
        except Exception as e:
            log("cvar skip", k, e)
    if path_traced and PT_DENOISE:      # string cvars (denoiser name) only go in as console commands
        prop(cv, "start_console_commands", DENOISER_CMDS)
        log("denoiser", DENOISER, DENOISER_CMDS)
    unreal.EditorAssetLibrary.save_loaded_asset(cfg)
    log("config", name, res)


mrq("MRQ_Prueba", (1920, 1080), 4, unreal.MoviePipelineImageSequenceOutput_JPG, "{sequence_name}_{camera_name}.{frame_number}")
mrq("MRQ_Recorrido", (1920, 1080), 8, unreal.MoviePipelineImageSequenceOutput_PNG, "{sequence_name}/f.{frame_number}")
mrq("MRQ_PT_Prueba", (1920, 1080), 1, unreal.MoviePipelineImageSequenceOutput_JPG, "PT_{camera_name}.{frame_number}",
    path_traced=True, spp=PT_TEST_SPP)
# with the denoiser on, 32 spp is already clean; 1 temporal sample (no motion blur) halves the render time
mrq("MRQ_PT_Recorrido", (1920, 1080), 1, unreal.MoviePipelineImageSequenceOutput_PNG, "PT/f.{frame_number}",
    path_traced=True, spp=32)

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
log("saved")
