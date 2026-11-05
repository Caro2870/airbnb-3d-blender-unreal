"""Generate untextured furniture meshes from photo crops with Hunyuan3D-2.1 (shape model only).

    python gen_muebles.py <hy3d repo> <crops dir> <out dir>

Each crop is cut out with rembg, then turned into a mesh (GLB).  Materials are applied later in Blender.
"""
import pathlib
import sys
import time

repo, crops, out = map(pathlib.Path, sys.argv[1:4])
sys.path.insert(0, str(repo / "hy3dshape"))

import torch
from PIL import Image
from hy3dshape.rembg import BackgroundRemover
from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline

out.mkdir(parents=True, exist_ok=True)
pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained("tencent/Hunyuan3D-2.1")
rembg = BackgroundRemover()
for png in sorted(crops.glob("*.png")):
    t0 = time.time()
    img = rembg(Image.open(png).convert("RGB"))
    img.save(out / f"{png.stem}_cutout.png")
    mesh = pipe(image=img, num_inference_steps=30, octree_resolution=256,
                generator=torch.manual_seed(1234))[0]
    mesh.export(out / f"{png.stem}.glb")
    print(png.stem, "faces", len(mesh.faces), f"{time.time() - t0:.0f}s",
          f"vram {torch.cuda.max_memory_allocated() / 2**30:.1f} GB", flush=True)
