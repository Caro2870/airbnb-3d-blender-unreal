"""Download CC0 assets from Poly Haven (api.polyhaven.com) into houses/apartaestudio/assets/.

    python polyhaven.py <assets_dir>

Textures -> tex/<id>/{diff,nor_gl,rough}.jpg (2k), models -> models/<id>/<id>_1k.blend + textures/,
HDRI -> hdri/<id>.hdr (2k).  Files already present are skipped; sources.json records every URL.
"""
import json
import pathlib
import sys
import urllib.request

TEXTURES = ["large_floor_tiles_02", "large_grey_tiles", "oak_veneer_01", "walnut_veneer", "rough_linen",
            "waffle_pique_cotton", "poly_wool_herringbone", "white_plaster_02", "concrete_floor_02"]
MODELS = ["potted_plant_01", "potted_plant_02", "potted_plant_04", "pachira_aquatica_01", "throw_pillows_01",
          "desk_lamp_arm_01", "outdoor_table_chair_set_01", "ceramic_vase_01", "decorative_book_set_01"]
HDRIS = ["kloofendal_43d_clear_puresky"]
UA = {"User-Agent": "openhouse-apartaestudio/1.0"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def fetch(url, dst, log):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        dst.write_bytes(get(url))
    log.append({"url": url, "file": str(dst)})


def main(root):
    root = pathlib.Path(root)
    log = []
    for tid in TEXTURES:
        f = json.loads(get(f"https://api.polyhaven.com/files/{tid}"))
        for key, name in (("Diffuse", "diff"), ("nor_gl", "nor_gl"), ("Rough", "rough")):
            fetch(f[key]["2k"]["jpg"]["url"], root / "tex" / tid / f"{name}.jpg", log)
        print("texture", tid)
    for mid in MODELS:
        b = json.loads(get(f"https://api.polyhaven.com/files/{mid}"))["blend"]["1k"]["blend"]
        fetch(b["url"], root / "models" / mid / f"{mid}_1k.blend", log)
        for rel, inc in b.get("include", {}).items():
            fetch(inc["url"], root / "models" / mid / rel, log)
        print("model", mid)
    for hid in HDRIS:
        h = json.loads(get(f"https://api.polyhaven.com/files/{hid}"))["hdri"]["2k"]["hdr"]
        fetch(h["url"], root / "hdri" / f"{hid}.hdr", log)
        print("hdri", hid)
    (root / "sources.json").write_text(json.dumps({"license": "CC0 (Poly Haven)", "files": log}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
