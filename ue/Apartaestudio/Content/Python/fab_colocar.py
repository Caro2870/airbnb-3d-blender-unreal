"""Place the Fab models in /Game/Apto/Mapa_Apto (run after armar_apto.py, before escena_apto.py; no GPU needed).

- sofa: the scanned-quality sofa (canape.obj) replaces the coded Sofa_Cama + bolster + throw, fitted to the same
  footprint against the west wall and dressed in the coded sofa's own fabric (it matches the photo)
- palms (Palm_4_1.fbx): along the parking lot, across the field and on the seafront; leaf material rewired to its
  texture with an alpha mask (the .tga did not come in with the FBX)
- cars: the BMW coupe (body + 4 wheels) and the red sport coupe (GLB scene) in the parking bays below the balcony

Positions are Blender metres (the house package's frame); ue() maps them like escena_apto.py.
"""
import math
import os
import random

import unreal

FAB = os.path.join(os.environ["USERPROFILE"], "recorrido-3d", "fab")
MAP = "/Game/Apto/Mapa_Apto"
REPORT = os.path.join(os.environ["USERPROFILE"], "recorrido-3d", "ue", "fab_colocar.txt")
W, Z0, WT = 4.05, 3.0, 0.15
Y_WIN = 6.80
Y_BAL = Y_WIN + WT + 1.09

els = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
mel = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary
open(REPORT, "w").close()


def log(*a):
    line = "[fab_colocar] " + " ".join(str(x) for x in a)
    unreal.log(line)
    with open(REPORT, "a", encoding="utf-8") as f:       # the commandlet log drops unreal.log lines
        f.write(line + "\n")


def ue(x, y, z):
    return unreal.Vector(100 * x, -100 * y, 100 * z)


def import_file(path, dest):
    if eal.does_directory_exist(dest) and eal.list_assets(dest):
        return
    t = unreal.AssetImportTask()
    t.filename, t.destination_path = path, dest
    t.automated, t.save, t.replace_existing = True, True, True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    log("imported", path)


def meshes(folder):
    return [eal.load_asset(p) for p in eal.list_assets(folder, recursive=True)
            if isinstance(eal.load_asset(p), unreal.StaticMesh)]


def bounds(ms):
    lo = [min(m.get_bounding_box().min.to_tuple()[i] for m in ms) for i in range(3)]
    hi = [max(m.get_bounding_box().max.to_tuple()[i] for m in ms) for i in range(3)]
    return lo, hi


def place(ms, label, base, yaw, scale, roll=0.0):
    """Spawn every mesh of a model with one shared transform, then shift them all so the group's world bounds sit
    with their bottom-centre on base (cm)."""
    out = []
    for i, m in enumerate(ms):
        # spawn_actor_from_object returns None in the commandlet for some meshes: spawn the actor, then set the mesh
        a = els.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator(roll, 0, yaw))
        a.static_mesh_component.set_static_mesh(m)
        a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
        a.set_actor_label(f"{label}_{i}" if len(ms) > 1 else label)
        out.append(a)
    lo = [1e9] * 3; hi = [-1e9] * 3
    for a in out:
        o, e = a.get_actor_bounds(False)
        for k, (c, h) in enumerate(zip(o.to_tuple(), e.to_tuple())):
            lo[k] = min(lo[k], c - h); hi[k] = max(hi[k], c + h)
    d = unreal.Vector(base.x - (lo[0] + hi[0]) / 2, base.y - (lo[1] + hi[1]) / 2, base.z - lo[2])
    for a in out:
        a.set_actor_location(a.get_actor_location() + d, False, False)
    return out, [hi[k] - lo[k] for k in range(3)]


def set_tex(mi, name, tex, weight):
    mel.set_material_instance_texture_parameter_value(mi, name, tex)
    mel.set_material_instance_scalar_parameter_value(mi, name + "Weight", weight)


def overrides(mi, blend=None, two_sided=None):
    o = mi.get_editor_property("base_property_overrides")
    if blend is not None:
        o.set_editor_property("override_blend_mode", True)
        o.set_editor_property("blend_mode", blend)
    if two_sided is not None:
        o.set_editor_property("override_two_sided", True)
        o.set_editor_property("two_sided", two_sided)
    mi.set_editor_property("base_property_overrides", o)


# ---- assets
import_file(os.path.join(FAB, "canape.obj"), "/Game/Fab/SofaObj")
import_file(os.path.join(FAB, "palma", "Leaf_Atlas.tga"), "/Game/Fab/PalmaTex")
import_file(os.path.join(FAB, "palma", "Trunk_Atlas_Normal.png"), "/Game/Fab/PalmaTex")

leaf_tex = eal.load_asset("/Game/Fab/PalmaTex/Leaf_Atlas")
trunk_n = eal.load_asset("/Game/Fab/PalmaTex/Trunk_Atlas_Normal")
if trunk_n:
    trunk_n.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    trunk_n.set_editor_property("srgb", False)
leaf = eal.load_asset("/Game/Fab/Palma/Leaf_Atlas")
set_tex(leaf, "DiffuseColorMap", leaf_tex, 1.0)
set_tex(leaf, "OpacityMaskMap", leaf_tex, 1.0)
mel.set_material_instance_scalar_parameter_value(leaf, "OpacitySourceChannel", 3.0)    # alpha
overrides(leaf, unreal.BlendMode.BLEND_MASKED, True)
trunk = eal.load_asset("/Game/Fab/Palma/Trunk_Atlas1")
if trunk_n:
    set_tex(trunk, "NormalMap", trunk_n, 1.0)
car = eal.load_asset("/Game/Fab/Coupe/PBR_BMWM635")
mel.set_material_instance_scalar_parameter_value(car, "EmissiveColorMapWeight", 0.0)  # daytime: lights off
for mi in (leaf, trunk, car):
    mel.update_material_instance(mi)
    eal.save_loaded_asset(mi)
log("materials: palm leaf masked + two-sided, trunk normal, car emissive off")

# ---- level
les.load_level(MAP)
actors = els.get_all_level_actors()
labels = [a.get_actor_label() for a in actors]

# sofa: take the coded sofa's fabric, then remove the coded sofa
fabric = None
for a in actors:
    n = a.get_actor_label()
    if n.startswith("Sofa_Cama"):
        c = a.get_component_by_class(unreal.StaticMeshComponent)
        if c and fabric is None:
            fabric = c.get_material(0)
    if n.startswith(("Sofa_Cama", "Sofa_Cojin_Estampado", "Sofa_Manta", "Sofa_Almohadon", "Fab_")):
        els.destroy_actor(a)
# the coded sofa's baked texture follows the old mesh's UVs (dark blotches on this one): use the model's own fabric
# material instead, tinted to the photo's warm brown, with its fabric roughness map
fabric = eal.load_asset("/Game/Fab/Sofa/Brown_Fabric")
for n in mel.get_vector_parameter_names(fabric.get_editor_property("parent")):
    if str(n) == "DiffuseColor":
        mel.set_material_instance_vector_parameter_value(fabric, n, unreal.LinearColor(0.20, 0.135, 0.09, 1.0))
mel.set_material_instance_scalar_parameter_value(fabric, "Shininess", 4.0)
mel.update_material_instance(fabric)
eal.save_loaded_asset(fabric)
log("sofa fabric from coded sofa:", fabric.get_path_name() if fabric else None)

sofa = meshes("/Game/Fab/SofaObj")
lo, hi = bounds(sofa)
size = [hi[i] - lo[i] for i in range(3)]
log("sofa obj size", [round(s, 3) for s in size], "meshes", [m.get_name() for m in sofa])
L = 195.0                                                    # the coded sofa: 1.95 m along the west wall
scale = L / max(size[0], size[1])
# the OBJ is Y-up (it came in lying on its back): roll it upright, then turn its length along the wall (Unreal Y)
# with the seat facing the room (+X); FAB_SOFA_ROLL / FAB_SOFA_YAW flip it if a test shows its back or underside
SOFA_ROLL = float(os.environ.get("FAB_SOFA_ROLL", "90"))
SOFA_YAW = float(os.environ.get("FAB_SOFA_YAW", "90"))
cy = 5.72
s_actors, s_size = place(sofa, "Fab_Sofa", ue(0.47, cy, Z0), SOFA_YAW, scale, SOFA_ROLL)
for a in s_actors:                       # back against the wall: the group's west face at x = 0.02 m
    a.set_actor_location(a.get_actor_location() + unreal.Vector(2 + s_size[0] / 2 - 47, 0, 0), False, False)
depth = s_size[0]
if fabric:
    for a in s_actors:
        c = a.get_component_by_class(unreal.StaticMeshComponent)
        for i in range(c.get_num_materials()):
            c.set_material(i, fabric)
log("sofa scale", round(scale, 3), "size cm", [round(s) for s in s_size], "roll", SOFA_ROLL, "yaw", SOFA_YAW)

# palms: 21 m model scaled to 8-12 m, random yaw
palm = meshes("/Game/Fab/Palma")
random.seed(202)
PALMS = [(-3.0, Y_BAL + 1.4), (7.5, Y_BAL + 1.6), (-10.0, Y_BAL + 1.3), (-17.0, Y_BAL + 1.5),       # parking edge
         (-25, 30), (-12, 35), (-3, 41), (6, 36), (15, 43), (27, 39), (41, 33), (-36, 44), (33, 46),  # field
         (-44, 50), (-22, 51), (0, 50), (19, 51), (38, 50), (55, 51)]                                 # seafront
for i, (x, y) in enumerate(PALMS):
    h = random.uniform(8.0, 12.0)
    place(palm, f"Fab_Palma{i:02d}", ue(x, y, 0.0), random.uniform(0, 360), h / 21.11)
log("palms", len(PALMS))

# cars in the bays below the balcony (bays 3 m wide between the yellow lines at x = -18 + 3k, nose toward the
# building); alternate the model and heading
bay_y = Y_BAL + 4.9
coupe = meshes("/Game/Fab/Coupe")
for i, (x, yaw) in enumerate(((-7.5, 90), (7.5, -90), (16.5, 90))):
    place(coupe, f"Fab_Carro{i}", ue(x, bay_y, 0.035), yaw, 1.0)

# red sport coupe: its parts only keep their places as a scene import; collect the new actors, then move them
before = set(els.get_all_level_actors())
ic = unreal.InterchangeManager.get_interchange_manager_scripted()
params = unreal.ImportAssetParameters()
params.is_automated = True
ic.import_scene("/Game/Fab/DeportivoEscena/", unreal.InterchangeManager.create_source_data(
    os.path.join(FAB, "generic_sport_coupe_car.glb")), params)
new = [a for a in els.get_all_level_actors() if a not in before]
root = els.spawn_actor_from_class(unreal.Actor, unreal.Vector(0, 0, 0))
root.set_actor_label("Fab_Deportivo")
if not root.get_editor_property("root_component"):
    root.set_editor_property("root_component", unreal.SceneComponent())
for a in new:
    if a.get_attach_parent_actor() is None:
        a.attach_to_actor(root, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                          unreal.AttachmentRule.KEEP_WORLD, False)
    a.set_actor_label("Fab_Dep_" + a.get_actor_label())
# glTF is Y-up: Interchange already converts; the car's length runs along Unreal Y, nose at +Y
root.set_actor_location(ue(1.5, bay_y, 0.035), False, False)
root.set_actor_rotation(unreal.Rotator(0, 0, 180), False)
log("sport coupe actors", len(new))

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
log("saved", MAP)
