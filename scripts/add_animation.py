# -*- coding: utf-8 -*-
"""
Add animated rain, looping ripples and a gentle camera drift to the
Machikado Mart scene.  Saves an animated .blend at 480p / 150 frames.

Run:
  blender -b --factory-startup --python add_animation.py
"""
import bpy
import math
import os
import random
from mathutils import Vector

PROJECT = r"D:\Master\dps harness\deepseek_project3"
STATIC_BLEND = os.path.join(PROJECT, "machikado_mart_static.blend")
OUT_BLEND = os.path.join(PROJECT, "machikado_mart_animated.blend")
RENDERS = os.path.join(PROJECT, "renders")
os.makedirs(RENDERS, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=STATIC_BLEND)
scn = bpy.context.scene
rng = random.Random(20261103)


def srgb_lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_lin(h, a=1.0):
    h = h.lstrip("#")
    return (srgb_lin(int(h[0:2], 16)), srgb_lin(int(h[2:4], 16)),
            srgb_lin(int(h[4:6], 16)), a)


rain_coll = bpy.data.collections.get("07_Rain_FX") or scn.collection

# Hide the original static rain geometry; the animated field replaces it.
for nm in ("Rain_Streaks", "Rain_Streaks_Near"):
    ob = bpy.data.objects.get(nm)
    if ob:
        ob.hide_render = True
        ob.hide_viewport = True

# Remove leftovers if this script is ever rerun.
for nm in ("Rain_Points_Animated", "Rain_Streak_Source", "Cam_Orbit_Target"):
    ob = bpy.data.objects.get(nm)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)
old_gn = bpy.data.node_groups.get("Animated_Rain_GN")
if old_gn:
    bpy.data.node_groups.remove(old_gn)

# ---------------------------------------------------------------------------
# Rain source: a very thin slanted prism, 1 unit long, pointing down.
# Its origin is the top; instancing/scale makes the streaks varied lengths.
# ---------------------------------------------------------------------------
me = bpy.data.meshes.new("Rain_Streak_Source_mesh")
w = 0.0034
dx = 0.050
verts = [(-w, -w, 0.0), (w, -w, 0.0), (w, w, 0.0), (-w, w, 0.0),
         (dx - w, -w, -1.0), (dx + w, -w, -1.0),
         (dx + w, w, -1.0), (dx - w, w, -1.0)]
faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
         (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
me.from_pydata(verts, [], faces)
me.update()
source = bpy.data.objects.new("Rain_Streak_Source", me)
rain_coll.objects.link(source)
source.location = (0.0, 0.0, -100.0)

rain_mat = bpy.data.materials.new("Rain_Animated_Mat")
rain_mat.use_nodes = True
rnt = rain_mat.node_tree
rnt.nodes.clear()
rout = rnt.nodes.new("ShaderNodeOutputMaterial")
rem = rnt.nodes.new("ShaderNodeEmission")
rem.inputs["Color"].default_value = hex_lin("#b6d8f2")
rem.inputs["Strength"].default_value = 1.25
rtr = rnt.nodes.new("ShaderNodeBsdfTransparent")
rmix = rnt.nodes.new("ShaderNodeMixShader")
rmix.inputs["Fac"].default_value = 0.20
rnt.links.new(rtr.outputs[0], rmix.inputs[1])
rnt.links.new(rem.outputs[0], rmix.inputs[2])
rnt.links.new(rmix.outputs[0], rout.inputs["Surface"])
rain_mat.surface_render_method = "DITHERED"
try:
    rain_mat.use_transparent_shadow = False
except Exception:
    pass
me.materials.append(rain_mat)

# ---------------------------------------------------------------------------
# Point cloud which the rain node graph instances onto.
# ---------------------------------------------------------------------------
N_RAIN = 1200
verts = []
for i in range(N_RAIN):
    x = rng.uniform(-8.2, 8.2)
    y = rng.uniform(-8.2, 8.2)
    z = rng.uniform(0.2, 12.0)
    verts.append((x, y, z))
pme = bpy.data.meshes.new("Rain_Points_Animated_mesh")
pme.from_pydata(verts, [], [])
pme.update()
points = bpy.data.objects.new("Rain_Points_Animated", pme)
rain_coll.objects.link(points)

# ---------------------------------------------------------------------------
# Geometry-node graph:
#   Position.z - time*speed, wrapped into a looping 12 m column,
#   then instanced as thin slanted streak meshes.
# ---------------------------------------------------------------------------
ng = bpy.data.node_groups.new("Animated_Rain_GN", "GeometryNodeTree")
ng.interface.new_socket(name="Geometry", in_out="INPUT",
                        socket_type="NodeSocketGeometry")
ng.interface.new_socket(name="Geometry", in_out="OUTPUT",
                        socket_type="NodeSocketGeometry")
nodes = ng.nodes
links = ng.links
gin = nodes.new("NodeGroupInput")
gout = nodes.new("NodeGroupOutput")
position = nodes.new("GeometryNodeInputPosition")
scene_time = nodes.new("GeometryNodeInputSceneTime")
sep = nodes.new("ShaderNodeSeparateXYZ")
speed = nodes.new("ShaderNodeMath")
speed.operation = "MULTIPLY"
speed.inputs[1].default_value = 6.2
sub = nodes.new("ShaderNodeMath")
sub.operation = "SUBTRACT"
wrap = nodes.new("ShaderNodeMath")
wrap.operation = "WRAP"
wrap.inputs[1].default_value = 0.10
wrap.inputs[2].default_value = 12.10
comb = nodes.new("ShaderNodeCombineXYZ")
setpos = nodes.new("GeometryNodeSetPosition")
objinfo = nodes.new("GeometryNodeObjectInfo")
try:
    objinfo.transform_space = "ORIGINAL"
except Exception:
    pass
objinfo.inputs["Object"].default_value = source
rnd_len = nodes.new("FunctionNodeRandomValue")
rnd_len.data_type = "FLOAT"
rnd_len.inputs["Min"].default_value = 0.25
rnd_len.inputs["Max"].default_value = 0.95
rnd_len.inputs["Seed"].default_value = 44
scale_xyz = nodes.new("ShaderNodeCombineXYZ")
scale_xyz.inputs["X"].default_value = 1.0
scale_xyz.inputs["Y"].default_value = 1.0
inst = nodes.new("GeometryNodeInstanceOnPoints")
realize = nodes.new("GeometryNodeRealizeInstances")

links.new(position.outputs["Position"], sep.inputs["Vector"])
links.new(scene_time.outputs["Seconds"], speed.inputs[0])
links.new(sep.outputs["Z"], sub.inputs[0])
links.new(speed.outputs[0], sub.inputs[1])
links.new(sub.outputs[0], wrap.inputs[0])
links.new(sep.outputs["X"], comb.inputs["X"])
links.new(sep.outputs["Y"], comb.inputs["Y"])
links.new(wrap.outputs[0], comb.inputs["Z"])
links.new(gin.outputs["Geometry"], setpos.inputs["Geometry"])
links.new(comb.outputs["Vector"], setpos.inputs["Position"])
links.new(rnd_len.outputs["Value"], scale_xyz.inputs["Z"])
links.new(setpos.outputs["Geometry"], inst.inputs["Points"])
links.new(objinfo.outputs["Geometry"], inst.inputs["Instance"])
links.new(scale_xyz.outputs["Vector"], inst.inputs["Scale"])
links.new(inst.outputs["Instances"], realize.inputs["Geometry"])
links.new(realize.outputs["Geometry"], gout.inputs["Geometry"])

mod = points.modifiers.new("Animated Rain", "NODES")
mod.node_group = ng

# ---------------------------------------------------------------------------
# Ripple / splash animation.  Each ring gets its own material copy so the
# transparent fade can be animated independently.  Cycles begin at varied
# phases; the alpha returns to zero at each cycle boundary so the loop is
# visually seamless.
# ---------------------------------------------------------------------------
def animate_fx(obj, period_lo, period_hi, alpha_max, scale_end):
    if not obj.data.materials:
        return
    base_mat = obj.data.materials[0]
    mat = base_mat.copy()
    mat.name = obj.name + "_AnimatedMat"
    obj.data.materials[0] = mat
    mix = None
    if mat.use_nodes:
        for n in mat.node_tree.nodes:
            if n.bl_idname == "ShaderNodeMixShader":
                mix = n
                break
    if mix is None:
        return
    period = rng.randint(period_lo, period_hi)
    phase = rng.uniform(0.0, period)
    start = phase - 2.0 * period
    while start < 150.0 + period:
        mid = start + period * 0.55
        end = start + period * 0.90
        # birth
        obj.scale = (0.18, 0.18, 0.18)
        obj.keyframe_insert("scale", frame=start)
        mix.inputs[0].default_value = 0.0
        mix.inputs[0].keyframe_insert("default_value", frame=start)
        # maximum
        obj.scale = (0.95, 0.95, 0.95)
        obj.keyframe_insert("scale", frame=mid)
        mix.inputs[0].default_value = alpha_max
        mix.inputs[0].keyframe_insert("default_value", frame=mid)
        # faded out at large radius
        obj.scale = (scale_end, scale_end, scale_end)
        obj.keyframe_insert("scale", frame=end)
        mix.inputs[0].default_value = 0.0
        mix.inputs[0].keyframe_insert("default_value", frame=end)
        start += period


for ob in bpy.data.objects:
    if ob.name.startswith("RainRipple_"):
        animate_fx(ob, 22, 34, 0.60, 1.45)
    elif ob.name.startswith("Splash_"):
        animate_fx(ob, 11, 19, 0.50, 1.32)

# ---------------------------------------------------------------------------
# Gentle looping camera drift: IsoCamera swings very slightly left/up and
# returns to its original position at frame 150.  A Track To constraint keeps
# the view anchored on the shop.
# ---------------------------------------------------------------------------
cam = bpy.data.objects.get("IsoCamera")
if cam is None:
    raise RuntimeError("IsoCamera not found")
cam.animation_data_clear()
for c in list(cam.constraints):
    cam.constraints.remove(c)
target = bpy.data.objects.new("Cam_Orbit_Target", None)
scn.collection.objects.link(target)
target.location = (0.0, -0.10, 2.05)
target.empty_display_type = "SPHERE"
target.empty_display_size = 0.18
con = cam.constraints.new("TRACK_TO")
con.name = "Look at the shop"
con.target = target
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"

cam.location = (13.2, -16.6, 11.6)
cam.keyframe_insert("location", frame=1)
cam.location = (12.52, -16.98, 11.84)
cam.keyframe_insert("location", frame=75)
cam.location = (13.2, -16.6, 11.6)
cam.keyframe_insert("location", frame=150)
# Smooth interpolation where the API allows it.
try:
    for fc in cam.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"
except Exception as exc:
    print("camera handle tweak:", exc)

# ---------------------------------------------------------------------------
# Render setup: 150 frames, 854x480 (16:9 480p), 24 fps.
# Keep FFMPEG image format from the source file: Blender 5.2.2's enum exposes
# it but rejects direct assignment in some fresh sessions.
# ---------------------------------------------------------------------------
scn.render.engine = "BLENDER_EEVEE"
scn.render.resolution_x = 854
scn.render.resolution_y = 480
scn.render.resolution_percentage = 100
scn.render.fps = 24
scn.frame_start = 1
scn.frame_end = 150
scn.eevee.taa_render_samples = 20
scn.eevee.volumetric_samples = 32
scn.render.use_motion_blur = False
scn.render.image_settings.media_type = "VIDEO"
scn.render.image_settings.file_format = "FFMPEG"
scn.render.image_settings.color_mode = "RGB"
scn.render.use_file_extension = False
scn.render.filepath = os.path.join(RENDERS, "machikado_mart_rain_480p.mp4")
print("image format at save:", scn.render.image_settings.file_format)
try:
    scn.render.ffmpeg.format = "MPEG4"
    scn.render.ffmpeg.codec = "H264"
    scn.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scn.render.ffmpeg.ffmpeg_preset = "GOOD"
    scn.render.ffmpeg.audio_codec = "NONE"
    print("video settings:", scn.render.ffmpeg.format,
          scn.render.ffmpeg.codec)
except Exception as exc:
    print("video settings failed:", exc)

vl = bpy.context.view_layer
vl.use_freestyle = True
try:
    ls = vl.freestyle_settings.linesets[0]
    ls.linestyle.thickness = 1.0
except Exception as exc:
    print("freestyle tweak:", exc)

scn.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print("SAVED", OUT_BLEND)
print("OBJECTS", len(bpy.data.objects), "ACTIONS", len(bpy.data.actions))
