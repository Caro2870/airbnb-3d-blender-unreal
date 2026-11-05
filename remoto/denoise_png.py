# Blender -b --python denoise_png.py -- <in_dir> <out_dir> [first last]
# Removes path-tracer grain from Unreal PNG frames with Blender's OpenImageDenoise compositor node.
import bpy, sys, os, glob

args = sys.argv[sys.argv.index("--") + 1:]
src, dst = args[0], args[1]
files = sorted(glob.glob(os.path.join(src, "f.*.png")))
if len(args) >= 4:
    files = files[int(args[2]):int(args[3]) + 1]
os.makedirs(dst, exist_ok=True)

sc = bpy.context.scene
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGB"
sc.view_settings.view_transform = "Standard"

tree = bpy.data.node_groups.new("Denoise", "CompositorNodeTree")
sc.compositing_node_group = tree
img_node = tree.nodes.new("CompositorNodeImage")
den = tree.nodes.new("CompositorNodeDenoise")
out = tree.nodes.new("NodeGroupOutput")
tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
tree.links.new(img_node.outputs["Image"], den.inputs["Image"])
tree.links.new(den.outputs["Image"], out.inputs[0])

for f in files:
    im = bpy.data.images.load(f)
    im.colorspace_settings.name = "sRGB"
    img_node.image = im
    sc.render.resolution_x, sc.render.resolution_y = im.size
    sc.render.filepath = os.path.join(dst, os.path.basename(f))
    bpy.ops.render.render(write_still=True)
    bpy.data.images.remove(im)
    print("denoised", os.path.basename(f))
