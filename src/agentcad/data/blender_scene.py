"""agentcad: photoreal renders in Blender (Cycles, GPU when available). Started by agentcad.blender; runs
inside Blender's own Python (standard library + bpy only).

usage: blender -b -P blender_scene.py -- <job.json>
job.json: {"manifest": ..., "parts_dir": ..., "out": ..., "samples": 512, "pct": 100,
           "shots": [{"name", "exploded", "direction", "lens_mm", "resolution", "hidden", "frame_box"}]}
Writes, per shot: <out>/<shot>.png (RGBA, transparent with the floor shadow from a shadow catcher) and
<out>/<shot>_anchors.json (a visible point per labelled part, found by ray casting from the camera).
"""

import json
import math
import sys

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

JOB = json.load(open(sys.argv[sys.argv.index("--") + 1]))
MAN = json.load(open(JOB["manifest"]))
OUT = JOB["out"]
SAMPLES = int(JOB.get("samples", 256))
PCT = int(JOB.get("pct", 100))
MM = 0.001
LIGHT_W = 16.0          # key light, W per m^2 of camera distance; tuned by test renders (AgX, white backdrop)

# ------------------------------------------------------------------------------------------ materials
def principled(name, base, metallic=0.0, rough=0.5, coat=0.0, sss=0.0, aniso=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base, 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Subsurface Weight"].default_value = sss
    if aniso:
        b.inputs["Anisotropic"].default_value = aniso
    return m


def add_bump(m, axis, period_m, strength, noise=0.0):
    """Layer lines (sine bands along `axis`, object space) and/or a fine noise bump."""
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    height = None
    if axis is not None:
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Object"], sep.inputs[0])
        mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
        mul.inputs[1].default_value = 2 * math.pi / period_m
        nt.links.new(sep.outputs["XYZ".index(axis)], mul.inputs[0])
        sin = nt.nodes.new("ShaderNodeMath"); sin.operation = "SINE"
        nt.links.new(mul.outputs[0], sin.inputs[0])
        height = sin.outputs[0]
    if noise:
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = noise
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        if height is None:
            height = nz.outputs["Fac"]
        else:
            add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD"
            nt.links.new(height, add.inputs[0]); nt.links.new(nz.outputs["Fac"], add.inputs[1])
            height = add.outputs[0]
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = 0.00005
    nt.links.new(height, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def materials():
    M = {}
    M["alu"] = add_bump(principled("anodised aluminium", (0.66, 0.67, 0.69), 1.0, 0.38), None, 0, 0.15, noise=900)
    M["steel"] = principled("ground steel", (0.62, 0.63, 0.65), 1.0, 0.18)
    M["chrome"] = principled("hardened shaft", (0.80, 0.80, 0.80), 1.0, 0.08)
    M["oxide"] = principled("black oxide", (0.035, 0.035, 0.04), 1.0, 0.35)
    M["seal"] = principled("seal", (0.55, 0.05, 0.04), 0.0, 0.45)
    M["belt"] = add_bump(principled("belt rubber", (0.025, 0.025, 0.028), 0.0, 0.62), None, 0, 0.25, noise=2500)
    M["rs_black"] = principled("RS03 housing", (0.03, 0.03, 0.035), 0.6, 0.42, coat=0.15)
    for ax in "XYZ":                                                   # PETG, layer lines along the print axis
        M["petg_" + ax] = add_bump(principled(f"PETG ({ax} layers)", (0.80, 0.20, 0.015), 0.0, 0.36, coat=0.2,
                                              sss=0.02), ax, 0.0002, 0.22)
    return M


# manifest material -> material key above ("printed" picks the PETG variant of the part's print axis)
MATERIAL = {"aluminium": "alu", "steel": "steel", "chrome": "chrome", "black_oxide": "oxide", "rubber": "belt",
            "black": "rs_black", "bright": "alu", "seal": "seal"}


# ------------------------------------------------------------------------------------------ scene
def setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
            devs = [d for d in prefs.devices if d.type == kind]
            if devs:
                for d in prefs.devices:
                    d.use = d.type == kind
                sc.cycles.device = "GPU"
                print("RENDER DEVICE", kind, [d.name for d in devs])
                break
        except Exception as e:  # noqa: BLE001
            print("device", kind, "unavailable:", e)
    sc.cycles.samples = SAMPLES
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 10
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.color_depth = "16"
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    # studio world: soft vertical gradient (gives the metals something to reflect)
    w = bpy.data.worlds.new("studio"); sc.world = w; w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = (0.18, 0.18, 0.19, 1)
    ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = (0.75, 0.75, 0.76, 1)
    mp = nt.nodes.new("ShaderNodeMapRange"); mp.inputs["From Min"].default_value = -1; mp.inputs["From Max"].default_value = 1
    nt.links.new(tc.outputs["Normal"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], mp.inputs["Value"])
    nt.links.new(mp.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.15
    return sc


def import_parts(M):
    objs = {}
    for p in MAN["parts"]:
        stl = JOB["parts_dir"] + "/" + p["stl"]
        bpy.ops.wm.stl_import(filepath=stl, global_scale=MM)
        o = bpy.context.selected_objects[0]
        o.name = p["name"]
        bm = bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
        bm.to_mesh(o.data); bm.free()
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30))
        key = "petg_" + (p.get("print_axis") or "Z") if p["material"] == "printed" else MATERIAL.get(p["material"], "alu")
        o.data.materials.append(M[key])
        objs[p["name"]] = o
    return objs


def floor(sc):
    bpy.ops.mesh.primitive_plane_add(size=6.0, location=(0.04, 0.0, 0.0))
    f = bpy.context.active_object
    f.name = "floor"
    f.is_shadow_catcher = True
    return f


def place(objs, exploded):
    for p in MAN["parts"]:
        off = p["explode"] if exploded else (0, 0, 0)
        objs[p["name"]].location = Vector(off) * MM


def world_box(objs, hidden):
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for name, o in objs.items():
        if name in hidden:
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi


def camera(sc, d, lens, res, lo, hi):
    """Perspective camera looking along d (world Z up on screen), fitted to the box lo..hi with a 6 % margin on
    the tighter axis and the box centred in frame."""
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = PCT
    cam_data = bpy.data.cameras.new("cam"); cam_data.lens = lens; cam_data.sensor_fit = "AUTO"
    cam = bpy.data.objects.new("cam", cam_data); sc.collection.objects.link(cam); sc.camera = cam
    d = Vector(d).normalized()
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = d.to_track_quat("-Z", "Y")
    bpy.context.view_layer.update()
    m = cam.matrix_world.to_3x3()
    r, u = m @ Vector((1, 0, 0)), m @ Vector((0, 1, 0))
    centre = (lo + hi) / 2
    corners = [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
    dist = (hi - lo).length * 3
    for _ in range(25):
        cam.location = centre - d * dist
        bpy.context.view_layer.update()
        pts = [world_to_camera_view(sc, cam, c) for c in corners]
        x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
        y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
        frame = dist * 36.0 / lens                              # frame size along the longer image side
        wx, wy = frame * res[0] / max(res), frame * res[1] / max(res)
        centre = centre + r * ((x0 + x1) / 2 - 0.5) * wx + u * ((y0 + y1) / 2 - 0.5) * wy
        dist *= max(x1 - x0, y1 - y0) / 0.88
    cam.location = centre - d * dist
    bpy.context.view_layer.update()
    return cam, centre, dist


def lights(sc, cam, centre, dist):
    """Studio rig in the camera's frame: key upper left front, fill right, rim behind, soft top."""
    for o in [o for o in sc.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(o)
    m = cam.matrix_world.to_3x3()
    r, u, f = m @ Vector((1, 0, 0)), m @ Vector((0, 1, 0)), m @ Vector((0, 0, -1))
    rigs = [("key", -0.7, 1.5, 0.5, 0.55, 1.0), ("fill", 0.9, 0.05, 0.7, 0.8, 0.35),   # high key: short shadows
            ("rim", 0.5, 0.9, -0.8, 0.35, 0.9), ("top", 0.0, 1.3, 0.1, 0.7, 0.3)]
    for name, a, b, c, size, rel in rigs:
        ld = bpy.data.lights.new(name, "AREA"); ld.shape = "DISK"; ld.size = size * dist
        ld.energy = LIGHT_W * rel * dist ** 2
        lo = bpy.data.objects.new(name, ld); sc.collection.objects.link(lo)
        lo.location = centre + (r * a + u * b - f * c) * dist * 0.8
        lo.rotation_mode = "QUATERNION"
        lo.rotation_quaternion = (centre - lo.location).to_track_quat("-Z", "Y")
        ld.use_shadow = name in ("key", "rim")                  # fewer shadow lobes on the floor


def anchors(sc, cam, objs, hidden):
    """Per labelled part: a vertex the camera can see (ray cast hits this part first), nearest the part's
    projected centre. Pixel coordinates, origin top-left."""
    rx = sc.render.resolution_x * sc.render.resolution_percentage / 100
    ry = sc.render.resolution_y * sc.render.resolution_percentage / 100
    dg = bpy.context.evaluated_depsgraph_get()
    out = {}
    for p in MAN["parts"]:
        if not p["label"] or p["name"] in hidden:
            continue
        o = objs[p["name"]]
        mw = o.matrix_world
        vs = o.data.vertices
        step = max(1, len(vs) // 1500)
        cw = mw @ (sum((Vector(c) for c in o.bound_box), Vector()) / 8)
        c2 = world_to_camera_view(sc, cam, cw)
        best = None
        for i in range(0, len(vs), step):
            v = vs[i]
            w = mw @ v.co
            n = (mw.to_3x3() @ v.normal).normalized()
            q = w + n * 2e-5
            s2 = world_to_camera_view(sc, cam, q)
            if not (0.02 < s2.x < 0.98 and 0.02 < s2.y < 0.98):
                continue
            ray = (q - cam.location)
            hit, loc, _, _, ob, _ = sc.ray_cast(dg, cam.location, ray.normalized(), distance=ray.length * 1.001)
            if hit and ob.name == o.name and (loc - w).length < 5e-4:
                dist = (s2.x - c2.x) ** 2 + (s2.y - c2.y) ** 2
                if best is None or dist < best[0]:
                    best = (dist, s2.x * rx, (1 - s2.y) * ry)
        if best:
            out[p["name"]] = {"label": p["label"], "px": [best[1], best[2]]}
        else:
            print("no visible anchor:", p["name"])
    return out


def main():
    sc = setup()
    M = materials()
    objs = import_parts(M)
    floor(sc)
    for shot in JOB["shots"]:
        name, hidden = shot["name"], tuple(shot.get("hidden", ()))
        res = tuple(shot["resolution"])
        place(objs, shot["exploded"])
        for n, o in objs.items():
            o.hide_render = n in hidden
        bpy.context.view_layer.update()
        if shot.get("frame_box"):
            lo, hi = (Vector(v) * MM for v in shot["frame_box"])
        else:
            lo, hi = world_box(objs, hidden)
        for c in [o for o in sc.objects if o.type == "CAMERA"]:
            bpy.data.objects.remove(c)
        cam, centre, dist = camera(sc, shot["direction"], shot["lens_mm"], res, lo, hi)
        lights(sc, cam, centre, dist)
        sc.render.filepath = f"{OUT}/{name}.png"
        print("RENDER", name, res, "samples", SAMPLES, flush=True)
        bpy.ops.render.render(write_still=True)
        json.dump({"resolution": [res[0] * PCT // 100, res[1] * PCT // 100],
                   "anchors": anchors(sc, cam, objs, hidden) if shot.get("callouts") else {}},
                  open(f"{OUT}/{name}_anchors.json", "w"), indent=1)
        print("DONE", name, flush=True)


main()
