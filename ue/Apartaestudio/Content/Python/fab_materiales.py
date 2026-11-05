"""Report the parent material, blend mode and texture parameters of the imported Fab materials (headless, no GPU)."""
import os

import unreal

REPORT = os.path.join(os.environ["USERPROFILE"], "recorrido-3d", "ue", "fab_materiales.txt")
mel = unreal.MaterialEditingLibrary
def main():
  with open(REPORT, "w", encoding="utf-8") as f:
    for folder in ("/Game/Fab/Palma", "/Game/Fab/Coupe", "/Game/Fab/Sofa"):
        for path in unreal.EditorAssetLibrary.list_assets(folder, recursive=True):
            a = unreal.EditorAssetLibrary.load_asset(path)
            try:
                report(f, path, a)
            except Exception as e:
                f.write(f"ERR {path} {e!r}\n")
            f.flush()


def report(f, path, a):
            if isinstance(a, unreal.MaterialInstanceConstant):
                parent = a.get_editor_property("parent")
                o = a.get_editor_property("base_property_overrides")
                tex = {}
                for n in mel.get_texture_parameter_names(parent):
                    v = mel.get_material_instance_texture_parameter_value(a, n)
                    tex[str(n)] = v.get_name() if v else None
                scal = {str(n): mel.get_material_instance_scalar_parameter_value(a, n)
                        for n in mel.get_scalar_parameter_names(parent)}
                ov = {k: o.get_editor_property(k) for k in ("blend_mode", "override_blend_mode", "two_sided")}
                f.write(f"MI {path}\n  parent {parent.get_path_name()}\n  {ov}\n  tex {tex}\n  scalar {scal}\n")
            elif isinstance(a, unreal.Texture2D):
                f.write(f"TEX {path}\n")


main()
