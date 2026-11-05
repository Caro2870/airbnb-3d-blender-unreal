"""Print the world bounding box of every Prop_* group in the open .blend (diagnostic)."""
import bpy

for root in [o for o in bpy.data.objects if o.name.startswith("Prop_")]:
    obs = [o for o in root.children_recursive if o.type == 'MESH']
    pts = [o.matrix_world @ v.co for o in obs for v in o.data.vertices]
    if not pts:
        print(root.name, "no meshes"); continue
    lo = [round(min(p[i] for p in pts), 2) for i in range(3)]
    hi = [round(max(p[i] for p in pts), 2) for i in range(3)]
    print(root.name, len(obs), "lo", lo, "hi", hi, "meshes", [o.name for o in obs][:6])
