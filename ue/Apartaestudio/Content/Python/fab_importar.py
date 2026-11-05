"""Import the Fab models (recorrido-3d\\fab) into /Game/Fab and report their meshes, material slots and sizes.

Run headless (no GPU needed):
    UnrealEditor-Cmd.exe Apartaestudio.uproject -run=pythonscript -script="<this file>" -unattended -nosplash -nullrhi
"""
import os

import unreal

FAB = os.path.join(os.environ["USERPROFILE"], "recorrido-3d", "fab")
MODELS = {                       # destination folder -> source file
    "Sofa": "canape3.fbx",
    "Palma": os.path.join("palma", "Palm_4_1.fbx"),
    "Coupe": os.path.join("coupe", "Coupe#1Packed.fbx"),
    "Deportivo": "generic_sport_coupe_car.glb",
}


REPORT = os.path.join(os.environ["USERPROFILE"], "recorrido-3d", "ue", "fab_reporte.txt")
open(REPORT, "w").close()


def log(*a):
    line = "[fab_importar] " + " ".join(str(x) for x in a)
    unreal.log(line)
    with open(REPORT, "a", encoding="utf-8") as f:       # the commandlet log drops these lines
        f.write(line + "\n")


tasks = []
for folder, rel in MODELS.items():
    dest = "/Game/Fab/" + folder
    if unreal.EditorAssetLibrary.does_directory_exist(dest) and unreal.EditorAssetLibrary.list_assets(dest):
        log("already imported", dest)
        continue
    t = unreal.AssetImportTask()
    t.filename = os.path.join(FAB, rel)
    t.destination_path = dest
    t.automated = True
    t.save = True
    t.replace_existing = True
    tasks.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
for t in tasks:
    log("imported", t.filename, "->", len(t.imported_object_paths or []), "objects")

for folder in MODELS:
    for path in unreal.EditorAssetLibrary.list_assets("/Game/Fab/" + folder, recursive=True):
        a = unreal.EditorAssetLibrary.load_asset(path)
        if isinstance(a, unreal.StaticMesh):
            b = a.get_bounding_box()
            size = b.max - b.min
            slots = [(m.material_slot_name, m.material_interface.get_path_name() if m.material_interface else None)
                     for m in a.static_materials]
            log("MESH", path, "size_cm", round(size.x), round(size.y), round(size.z),
                "min", round(b.min.x), round(b.min.y), round(b.min.z), "slots", slots)
        elif isinstance(a, unreal.Texture2D):
            log("TEX", path, a.blueprint_get_size_x(), "x", a.blueprint_get_size_y())
        elif isinstance(a, unreal.MaterialInterface):
            log("MAT", path, a.get_class().get_name())
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
log("done")
