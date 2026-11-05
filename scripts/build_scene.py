# -*- coding: utf-8 -*-
"""
MACHIKADO MART - rainy-night isometric miniature diorama
Blender 5.2 / EEVEE. Fully procedural scene builder.

Run:
  blender -b --factory-startup --python build_scene.py -- --preview
  blender -b --factory-startup --python build_scene.py -- --final
"""
import bpy
import bmesh
import math
import os
import random
import sys
from mathutils import Vector, Euler

# ----------------------------------------------------------------------------
# CLI / paths
# ----------------------------------------------------------------------------
ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = "--preview" in ARGV
FINAL = "--final" in ARGV
NO_RENDER = "--no-render" in ARGV
QUICK = "--quick" in ARGV
PROJECT = r"D:\Master\dps harness\deepseek_project3"
RENDERS = os.path.join(PROJECT, "renders")
os.makedirs(RENDERS, exist_ok=True)

random.seed(20260517)

# ----------------------------------------------------------------------------
# Scene reset
# ----------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
SCN = bpy.context.scene
SCN.name = "Machikado_Mart_Night"
SCN.render.engine = "BLENDER_EEVEE"
SCN.render.film_transparent = False
SCN.render.use_freestyle = True
SCN.render.image_settings.file_format = "PNG"
SCN.render.image_settings.color_mode = "RGBA"
SCN.render.resolution_percentage = 100
SCN.render.fps = 24
SCN.view_settings.view_transform = "Standard"
try:
    SCN.view_settings.look = "Medium High Contrast"
except Exception:
    pass
SCN.view_settings.exposure = 0.16

# ----------------------------------------------------------------------------
# Collections
# ----------------------------------------------------------------------------
ROOT = bpy.data.collections.new("MACHIKADO_MART")
SCN.collection.children.link(ROOT)


def new_coll(name):
    c = bpy.data.collections.new(name)
    ROOT.children.link(c)
    return c


ARCH = new_coll("00_Architecture")
DETAIL = new_coll("01_Details")
INTERIOR = new_coll("02_Interior")
STREET = new_coll("03_Street")
PROPS = new_coll("04_Props")
VEG = new_coll("05_Greenery")
LIGHTS = new_coll("06_Lights")
RAIN = new_coll("07_Rain_FX")
OUTLINE = bpy.data.collections.new("FS_Outline")
SCN.collection.children.link(OUTLINE)

# ----------------------------------------------------------------------------
# Color helpers
# ----------------------------------------------------------------------------
def lin(c):
    """sRGB 0-1 -> linear."""
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def hexc(h, a=1.0):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return (lin(int(h[0:2], 16) / 255.0),
            lin(int(h[2:4], 16) / 255.0),
            lin(int(h[4:6], 16) / 255.0), a)


PAL = {
    "base": "#0b0e16",
    "base_edge": "#161c28",
    "brass": "#b8945f",
    "asphalt": "#141d29",
    "asphalt2": "#1c2735",
    "sidewalk": "#5b6672",
    "sidewalk2": "#6b7580",
    "curb": "#9da6ad",
    "white": "#e9eaeb",
    "roadwhite": "#cdd6da",
    "tactile": "#d0a746",
    "wall": "#efe6d6",
    "wall_upper": "#f2e8dc",
    "wall_pink": "#dda8b7",
    "trim": "#c9c0b2",
    "dark": "#22262d",
    "metal": "#313b48",
    "metal_light": "#7d8a98",
    "pole": "#3a4656",
    "wood": "#5e4434",
    "wood_light": "#8b674c",
    "signcream": "#f3e8c3",
    "signink": "#27231f",
    "green": "#2f8059",
    "green_dark": "#1f5d43",
    "orange": "#e68643",
    "red": "#cf4b47",
    "red_dark": "#8e2f31",
    "pink": "#f29dbd",
    "cyan": "#93d9ff",
    "warm": "#ffd58e",
    "warm_deep": "#ffae5c",
    "interior": "#ffdda0",
    "glass": "#2b5260",
    "teal": "#2d716c",
    "tree": "#205147",
    "tree_light": "#2b6b58",
    "van": "#9fb4c4",
    "van_dark": "#5d7282",
    "lantern": "#e95636",
    "sakura": "#cf8891",
}

# ----------------------------------------------------------------------------
# Materials
# ----------------------------------------------------------------------------
MATS = {}


def _nodes(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    return nt


def toon_mat(name, color, rim_col=None, rim_strength=0.18, emit=0.09,
             bands=None, roughness=1.0):
    """Cel-shaded emission material (EEVEE Shader-to-RGB)."""
    if name in MATS:
        return MATS[name]
    mat = bpy.data.materials.new(name)
    nt = _nodes(mat)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
    diff.inputs["Color"].default_value = (1, 1, 1, 1)
    s2r = nt.nodes.new("ShaderNodeShaderToRGB")
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    gain = nt.nodes.new("ShaderNodeMath")
    gain.operation = "MULTIPLY"
    gain.inputs[1].default_value = 0.50
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "CONSTANT"
    if bands is None:
        bands = [(0.00, (0.10, 0.13, 0.22, 1)),
                 (0.19, (0.37, 0.40, 0.49, 1)),
                 (0.47, (0.79, 0.81, 0.85, 1)),
                 (0.77, (1.0, 1.0, 1.0, 1))]
    # build stops
    while len(cr.elements) < len(bands):
        cr.elements.new(0.5)
    for i, (pos, col) in enumerate(bands):
        cr.elements[i].position = pos
        cr.elements[i].color = col
    mul = nt.nodes.new("ShaderNodeMixRGB")
    mul.blend_type = "MULTIPLY"
    mul.inputs["Fac"].default_value = 1.0
    mul.inputs["Color1"].default_value = color
    # ambient lift
    amb = nt.nodes.new("ShaderNodeMixRGB")
    amb.blend_type = "ADD"
    amb.inputs["Fac"].default_value = 1.0
    amb.inputs["Color1"].default_value = (color[0] * emit, color[1] * emit,
                                         color[2] * emit, 1)
    # rim light
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.24
    rimramp = nt.nodes.new("ShaderNodeValToRGB")
    rimramp.color_ramp.interpolation = "CONSTANT"
    rimramp.color_ramp.elements[0].position = 0.78
    rimramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    rimramp.color_ramp.elements[1].position = 0.91
    rimramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    rimcol = nt.nodes.new("ShaderNodeMixRGB")
    rimcol.blend_type = "MIX"
    rimcol.inputs["Fac"].default_value = 0.0
    if rim_col is None:
        rim_col = (lin(0.46), lin(0.64), lin(0.88), 1)
    rimcol.inputs["Color1"].default_value = (0, 0, 0, 1)
    rimcol.inputs["Color2"].default_value = (rim_col[0] * rim_strength,
                                             rim_col[1] * rim_strength,
                                             rim_col[2] * rim_strength, 1)
    addrim = nt.nodes.new("ShaderNodeMixRGB")
    addrim.blend_type = "ADD"
    addrim.inputs["Fac"].default_value = 1.0
    emission = nt.nodes.new("ShaderNodeEmission")
    emission.inputs["Strength"].default_value = 1.0
    # links
    nt.links.new(diff.outputs["BSDF"], s2r.inputs["Shader"])
    nt.links.new(s2r.outputs["Color"], bw.inputs["Color"])
    nt.links.new(bw.outputs["Val"], gain.inputs[0])
    nt.links.new(gain.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], mul.inputs["Color2"])
    nt.links.new(mul.outputs["Color"], amb.inputs["Color2"])
    nt.links.new(lw.outputs["Facing"], rimramp.inputs["Fac"])
    nt.links.new(rimramp.outputs["Color"], rimcol.inputs["Fac"])
    nt.links.new(amb.outputs["Color"], addrim.inputs["Color1"])
    nt.links.new(rimcol.outputs["Color"], addrim.inputs["Color2"])
    nt.links.new(addrim.outputs["Color"], emission.inputs["Color"])
    nt.links.new(emission.outputs["Emission"], out.inputs["Surface"])
    MATS[name] = mat
    return mat


def emit_mat(name, color, strength=1.0, alpha=1.0):
    if name in MATS:
        return MATS[name]
    mat = bpy.data.materials.new(name)
    nt = _nodes(mat)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emission = nt.nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = color
    emission.inputs["Strength"].default_value = strength
    if alpha < 1.0:
        transp = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        mix.inputs["Fac"].default_value = alpha
        nt.links.new(transp.outputs[0], mix.inputs[1])
        nt.links.new(emission.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
        mat.surface_render_method = "DITHERED"
    else:
        nt.links.new(emission.outputs[0], out.inputs["Surface"])
    MATS[name] = mat
    return mat


def principled(name, color, roughness=0.5, metallic=0.0, alpha=1.0,
               emission=None, emission_strength=0.0, transmission=0.0,
               ior=1.45):
    if name in MATS:
        return MATS[name]
    mat = bpy.data.materials.new(name)
    nt = _nodes(mat)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["IOR"].default_value = ior
    if transmission:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    if emission:
        bsdf.inputs["Emission Color"].default_value = emission
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        mat.surface_render_method = "DITHERED"
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    MATS[name] = mat
    return mat


def matte(name, color, rough=0.6):
    return principled(name, color, roughness=rough,
                      emission=(color[0] * 0.12, color[1] * 0.12,
                                color[2] * 0.12, 1), emission_strength=1.0)


# --- common palette materials ---
M_BASE = matte("Base_Charcoal", hexc(PAL["base"]), 0.42)
M_BASE_EDGE = matte("Base_Edge", hexc(PAL["base_edge"]), 0.35)
M_BRASS = principled("Base_Brass", hexc(PAL["brass"]), 0.28, 0.75,
                     emission=hexc(PAL["brass"]), emission_strength=0.22)
M_ASPHALT = principled("Wet_Asphalt", hexc(PAL["asphalt"]), 0.36, 0.08,
                       emission=hexc("#0c131d"), emission_strength=0.10)
M_ASPHALT2 = principled("Wet_Asphalt_Patch", hexc(PAL["asphalt2"]), 0.40, 0.05,
                        emission=hexc("#0d1620"), emission_strength=0.09)
M_SIDEWALK = principled("Sidewalk", hexc(PAL["sidewalk"]), 0.5, 0.04,
                        emission=hexc("#1b232c"), emission_strength=0.12)
M_SIDEWALK2 = principled("Sidewalk_Light", hexc(PAL["sidewalk2"]), 0.44, 0.04,
                         emission=hexc("#232c35"), emission_strength=0.12)
M_CURB = toon_mat("Curb", hexc(PAL["curb"]), emit=0.08)
M_WHITE = toon_mat("Road_Paint", hexc(PAL["roadwhite"]), emit=0.12)
M_ROADPAINT = principled("RoadPaint_Wet", hexc("#b9c5ca"), 0.34, 0.03,
                         emission=hexc("#202b32"), emission_strength=0.15)
M_TACTILE = toon_mat("Tactile_Yellow", hexc(PAL["tactile"]), emit=0.2)
M_WALL = toon_mat("Wall_Cream", hexc(PAL["wall"]), emit=0.10)
M_WALL_UP = toon_mat("Wall_Upper", hexc(PAL["wall_upper"]), emit=0.12)
M_WALL_PINK = toon_mat("Wall_Pink_Wash", hexc(PAL["wall_pink"]), emit=0.18)
M_TRIM = toon_mat("Wall_Trim", hexc(PAL["trim"]), emit=0.1)
M_DARK = toon_mat("Dark_Metal", hexc(PAL["dark"]), emit=0.05)
M_METAL = toon_mat("Metal", hexc(PAL["metal"]), emit=0.06)
M_METAL_LIGHT = toon_mat("Metal_Light", hexc(PAL["metal_light"]), emit=0.1)
M_POLE = toon_mat("Utility_Pole", hexc(PAL["pole"]), emit=0.06)
M_WOOD = toon_mat("Wood_Dark", hexc(PAL["wood"]), emit=0.08)
M_WOOD_LIGHT = toon_mat("Wood_Light", hexc(PAL["wood_light"]), emit=0.1)
M_SIGNCREAM = emit_mat("Sign_Cream_Lit", hexc(PAL["signcream"]), 1.25)
M_SIGNINK = emit_mat("Sign_Ink", hexc(PAL["signink"]), 0.30)
M_GREEN = toon_mat("Sign_Green", hexc(PAL["green"]), emit=0.14)
M_GREEN_DARK = toon_mat("Sign_Green_Dark", hexc(PAL["green_dark"]), emit=0.1)
M_ORANGE = emit_mat("Sign_Orange", hexc(PAL["orange"]), 0.65)
M_RED = toon_mat("Sign_Red", hexc(PAL["red"]), emit=0.18)
M_RED_DARK = toon_mat("Sign_Red_Dark", hexc(PAL["red_dark"]), emit=0.12)
M_PINK = emit_mat("Neon_Pink", hexc(PAL["pink"]), 1.0)
M_CYAN = emit_mat("Neon_Cyan", hexc(PAL["cyan"]), 1.5)
M_WARM = emit_mat("Window_Warm", hexc(PAL["warm"]), 1.1)
M_WARM_DEEP = emit_mat("Window_Warm_Deep", hexc(PAL["warm_deep"]), 0.95)
M_INTERIOR = emit_mat("Interior_Glow", hexc(PAL["interior"]), 0.85)
M_GLASS = principled("Glass", hexc(PAL["glass"]), 0.08, 0.0, alpha=0.08,
                     emission=hexc("#17313b"), emission_strength=0.04,
                     transmission=0.0, ior=1.45)
M_GLASS_CLEAR = principled("Glass_Clear", hexc("#6f93a0"), 0.06, 0.0,
                           alpha=0.045, transmission=0.0)
M_TEAL = toon_mat("Teal_Painted", hexc(PAL["teal"]), emit=0.1)
M_TREE = toon_mat("Tree_Green", hexc(PAL["tree"]), emit=0.08)
M_TREE_LIGHT = toon_mat("Tree_Green_Light", hexc(PAL["tree_light"]), emit=0.08)
M_VAN = toon_mat("Van_PaleBlue", hexc(PAL["van"]), emit=0.1)
M_VAN_DARK = toon_mat("Van_Trim", hexc(PAL["van_dark"]), emit=0.08)
M_LANTERN = emit_mat("Lantern_Red", hexc(PAL["lantern"]), 1.15)
M_SAKURA = toon_mat("Noren_Sakura", hexc(PAL["sakura"]), emit=0.1)
M_BLACK = toon_mat("Deep_Black", hexc("#07090d"), emit=0.02)
M_INTERIOR_FLOOR = toon_mat("Interior_Floor", hexc("#b9976e"), emit=0.12)
M_SHELF = toon_mat("Shelf_Wood", hexc("#8a6a4b"), emit=0.1)
M_PRODUCT_COLORS = [
    toon_mat("Product_Red", hexc("#d95047"), emit=0.30),
    toon_mat("Product_Orange", hexc("#e69a47"), emit=0.30),
    toon_mat("Product_Yellow", hexc("#e8cf65"), emit=0.30),
    toon_mat("Product_Green", hexc("#5aa36d"), emit=0.30),
    toon_mat("Product_Blue", hexc("#4a8cc4"), emit=0.30),
    toon_mat("Product_Pink", hexc("#df85aa"), emit=0.30),
    toon_mat("Product_Cream", hexc("#ede5cb"), emit=0.30),
    toon_mat("Product_Purple", hexc("#8a6dab"), emit=0.30),
]

# ----------------------------------------------------------------------------
# Geometry helpers
# ----------------------------------------------------------------------------
def _link(obj, coll, outline):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    if outline:
        OUTLINE.objects.link(obj)
    return obj


def _bevel(obj, width, segments=2):
    if width <= 0:
        return
    mod = obj.modifiers.new("Soft_Edges", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(40)
    try:
        mod.harden_normals = True
    except Exception:
        pass


def box(name, loc, size, mat, bevel=0.0, rot=(0, 0, 0), coll=DETAIL,
        outline=False, smooth=False):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if smooth:
        bpy.ops.object.shade_smooth()
    obj.data.materials.append(mat)
    _bevel(obj, bevel)
    return _link(obj, coll, outline)


def cyl(name, loc, radius, depth, mat, verts=24, rot=(0, 0, 0),
        coll=DETAIL, outline=False, smooth=True, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius,
                                        depth=depth, location=loc,
                                        rotation=rot)
    obj = bpy.context.object
    obj.name = name
    if smooth:
        bpy.ops.object.shade_smooth()
    obj.data.materials.append(mat)
    _bevel(obj, bevel)
    return _link(obj, coll, outline)


def cone(name, loc, r1, r2, depth, mat, verts=24, rot=(0, 0, 0),
         coll=DETAIL, outline=False, smooth=True):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2,
                                    depth=depth, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    if smooth:
        bpy.ops.object.shade_smooth()
    obj.data.materials.append(mat)
    return _link(obj, coll, outline)


def sphere(name, loc, radius, mat, seg=20, rings=12, scale=(1, 1, 1),
           coll=DETAIL, outline=False):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings,
                                         radius=radius, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.shade_smooth()
    obj.data.materials.append(mat)
    return _link(obj, coll, outline)


def ico(name, loc, radius, mat, subdiv=2, scale=(1, 1, 1),
        coll=DETAIL, outline=False):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=radius,
                                          location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.shade_smooth()
    obj.data.materials.append(mat)
    return _link(obj, coll, outline)


def torus(name, loc, major, minor, mat, rot=(0, 0, 0), seg=32, mseg=8,
          coll=DETAIL, outline=False):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                     major_segments=seg, minor_segments=mseg,
                                     location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    bpy.ops.object.shade_smooth()
    obj.data.materials.append(mat)
    return _link(obj, coll, outline)


def mesh_obj(name, verts, faces, mat, coll=DETAIL, outline=False,
             smooth=False, bevel=0.0, material_slots=None, face_mats=None):
    me = bpy.data.meshes.new(name + "_mesh")
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    if outline:
        OUTLINE.objects.link(obj)
    if material_slots:
        for m in material_slots:
            me.materials.append(m)
        if face_mats:
            for p, mi in zip(me.polygons, face_mats):
                p.material_index = mi
    elif mat:
        me.materials.append(mat)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    _bevel(obj, bevel)
    return obj


def plane(name, loc, size, mat, rot=(0, 0, 0), coll=DETAIL, outline=False):
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    if len(size) == 2:
        obj.scale = (size[0], size[1], 1.0)
    else:
        obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return _link(obj, coll, outline)


def text_obj(name, body, loc, size, mat, rot=(math.radians(90), 0, 0),
             align_x="CENTER", align_y="CENTER", extrude=0.006,
             coll=DETAIL, font=None, spacing=1.0, line_spacing=1.0,
             outline=False):
    cu = bpy.data.curves.new(name + "_cu", "FONT")
    cu.body = body
    cu.font = font or FONT_BOLD
    cu.size = size
    cu.align_x = align_x
    cu.align_y = align_y
    cu.extrude = extrude
    cu.space_character = spacing
    cu.space_line = line_spacing
    obj = bpy.data.objects.new(name, cu)
    coll.objects.link(obj)
    if outline:
        OUTLINE.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = Euler(rot, "XYZ")
    cu.materials.append(mat)
    # convert to mesh so renders / outlining behave predictably
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    obj.name = name
    return obj


FONT_BOLD = bpy.data.fonts.load(r"C:\Windows\Fonts\YuGothB.ttc")
FONT_MED = bpy.data.fonts.load(r"C:\Windows\Fonts\YuGothM.ttc")


def wire(name, points, radius, mat, coll=DETAIL, outline=False,
         resolution=12):
    cu = bpy.data.curves.new(name + "_cu", "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = resolution
    cu.bevel_depth = radius
    cu.bevel_resolution = 2
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(points) - 1)
    for bp, co in zip(sp.bezier_points, points):
        bp.co = Vector(co)
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, cu)
    coll.objects.link(obj)
    if outline:
        OUTLINE.objects.link(obj)
    cu.materials.append(mat)
    return obj


class Batch:
    """Fast combined mesh for many tiny boxes."""
    def __init__(self, name, mats, coll=DETAIL, outline=False):
        self.name = name
        self.mats = mats
        self.coll = coll
        self.outline = outline
        self.v = []
        self.f = []
        self.fm = []

    def box(self, center, size, mat_index=0, rot_z=0.0):
        cx, cy, cz = center
        sx, sy, sz = size
        cosr = math.cos(rot_z)
        sinr = math.sin(rot_z)
        base = len(self.v)
        pts = [(-sx / 2, -sy / 2, -sz / 2), (sx / 2, -sy / 2, -sz / 2),
               (sx / 2, sy / 2, -sz / 2), (-sx / 2, sy / 2, -sz / 2),
               (-sx / 2, -sy / 2, sz / 2), (sx / 2, -sy / 2, sz / 2),
               (sx / 2, sy / 2, sz / 2), (-sx / 2, sy / 2, sz / 2)]
        for x, y, z in pts:
            xr = x * cosr - y * sinr
            yr = x * sinr + y * cosr
            self.v.append((xr + cx, yr + cy, z + cz))
        fs = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
              (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
        for f in fs:
            self.f.append(tuple(base + i for i in f))
            self.fm.append(mat_index)

    def pillar(self, center, radius, height, mat_index=0, sides=8):
        cx, cy, cz = center
        base = len(self.v)
        for k in range(sides):
            a = 2 * math.pi * k / sides
            x = cx + math.cos(a) * radius
            y = cy + math.sin(a) * radius
            self.v.append((x, y, cz - height / 2))
            self.v.append((x, y, cz + height / 2))
        for k in range(sides):
            k2 = (k + 1) % sides
            a0 = base + k * 2
            b0 = base + k2 * 2
            self.f.append((a0, b0, b0 + 1, a0 + 1))
            self.fm.append(mat_index)
        # caps
        top = len(self.v)
        self.v.append((cx, cy, cz + height / 2))
        bot = len(self.v)
        self.v.append((cx, cy, cz - height / 2))
        for k in range(sides):
            k2 = (k + 1) % sides
            self.f.append((base + k * 2 + 1, base + k2 * 2 + 1, top))
            self.fm.append(mat_index)
            self.f.append((base + k2 * 2, base + k * 2, bot))
            self.fm.append(mat_index)

    def build(self):
        return mesh_obj(self.name, self.v, self.f, None, self.coll,
                        self.outline, material_slots=self.mats,
                        face_mats=self.fm)


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def puddle(name, cx, cy, rx, ry, z, mat, seed=1, n=18, rot=0.0):
    rr = random.Random(seed)
    verts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        r = 1.0 + rr.uniform(-0.18, 0.16)
        x = math.cos(a) * rx * r
        y = math.sin(a) * ry * r
        xr = x * math.cos(rot) - y * math.sin(rot)
        yr = x * math.sin(rot) + y * math.cos(rot)
        verts.append((cx + xr, cy + yr, z))
    obj = mesh_obj(name, verts, [list(range(n))], mat, STREET, False)
    return obj


def catenary(p0, p1, sag=0.4, n=7):
    pts = []
    for i in range(n):
        t = i / (n - 1)
        x = p0[0] + (p1[0] - p0[0]) * t
        y = p0[1] + (p1[1] - p0[1]) * t
        z = p0[2] + (p1[2] - p0[2]) * t - sag * 4 * t * (1 - t)
        pts.append((x, y, z))
    return pts


print("BUILD: foundations")

# ----------------------------------------------------------------------------
# Base / island plinth
# ----------------------------------------------------------------------------
BASE_HALF = 7.5
box("Plinth_Lower", (0, 0, -0.52), (15.30, 15.30, 0.30), M_BASE,
    bevel=0.10, coll=ARCH, outline=True)
box("Plinth_Main", (0, 0, -0.22), (15.10, 15.10, 0.32), M_BASE_EDGE,
    bevel=0.10, coll=ARCH, outline=True)
box("Base_Ground", (0, 0, 0.015), (14.94, 14.94, 0.07), M_ASPHALT,
    bevel=0.035, coll=STREET, outline=False)

# thin brass pinstripe around the plinth
for nm, loc, size in [
    ("Stripe_F", (0, -7.548, -0.25), (15.02, 0.022, 0.022)),
    ("Stripe_B", (0, 7.548, -0.25), (15.02, 0.022, 0.022)),
    ("Stripe_L", (-7.548, 0, -0.25), (0.022, 15.02, 0.022)),
    ("Stripe_R", (7.548, 0, -0.25), (0.022, 15.02, 0.022)),
]:
    box(nm, loc, size, M_BRASS, coll=ARCH, outline=False)

# little maker's plaque on the front face of the base
box("Base_Plaque", (0, -7.565, -0.46), (2.4, 0.025, 0.16), M_METAL,
    bevel=0.015, coll=ARCH, outline=False)
text_obj("Base_Plaque_Text", "MACHIKADO MART  ·  RAINY NIGHT",
         (0, -7.585, -0.45), 0.052, M_BRASS,
         rot=(math.radians(90), 0, 0), align_x="CENTER",
         align_y="CENTER", extrude=0.002, coll=ARCH, font=FONT_MED)

# ----------------------------------------------------------------------------
# Roads, sidewalks, curbs
# ----------------------------------------------------------------------------
# main asphalt fields (front street + side street are the same dark wet plane)
box("Road_Front", (0, -4.65, 0.046), (14.86, 5.75, 0.012), M_ASPHALT,
    coll=STREET, outline=False)
box("Road_Side", (5.02, 1.1, 0.046), (4.86, 11.55, 0.012), M_ASPHALT,
    coll=STREET, outline=False)
# a subtly lighter road patch
box("Road_Patch", (4.7, -4.1, 0.052), (5.3, 3.1, 0.006), M_ASPHALT2,
    coll=STREET, outline=False)

# L-shaped sidewalk in front and along the store's right flank
box("Sidewalk_Front", (-2.43, -0.82, 0.09), (10.10, 2.02, 0.18),
    M_SIDEWALK, bevel=0.015, coll=STREET, outline=True)
box("Sidewalk_Side", (1.585, 2.45, 0.09), (2.07, 8.35, 0.18),
    M_SIDEWALK, bevel=0.015, coll=STREET, outline=True)
box("Sidewalk_Back", (-3.35, 5.95, 0.09), (8.25, 1.30, 0.18),
    M_SIDEWALK, bevel=0.015, coll=STREET, outline=True)
# lighter paving band near the shop
box("Sidewalk_ShopApron", (-2.4, -0.10, 0.183), (6.1, 0.70, 0.012),
    M_SIDEWALK2, coll=STREET, outline=False)

# building foundation slab
box("Shop_Foundation", (-2.40, 2.78, 0.235), (6.10, 5.02, 0.11),
    M_CURB, bevel=0.035, coll=ARCH, outline=True)

# curbs
box("Curb_Front", (0.0, -1.93, 0.085), (10.35, 0.18, 0.17), M_CURB,
    bevel=0.02, coll=STREET, outline=True)
box("Curb_Side", (2.70, 2.30, 0.085), (0.20, 8.60, 0.17), M_CURB,
    bevel=0.02, coll=STREET, outline=True)
box("Curb_Back", (-3.35, 6.63, 0.085), (8.45, 0.18, 0.17), M_CURB,
    bevel=0.02, coll=STREET, outline=True)
# yellow painted nose on the curb
box("Curb_Yellow_F", (-1.95, -1.922, 0.174), (5.15, 0.035, 0.024),
    M_TACTILE, coll=STREET, outline=False)
box("Curb_Yellow_S", (2.692, 1.25, 0.174), (0.035, 4.8, 0.024),
    M_TACTILE, coll=STREET, outline=False)

# sidewalk tile joints
seams = Batch("Sidewalk_Seams", [M_DARK], STREET, False)
for i in range(9):
    x = -7.35 + i * 1.15
    seams.box((x, -0.82, 0.1815), (0.018, 2.00, 0.004), 0)
for j in range(9):
    y = -1.78 + j * 0.62
    seams.box((-2.43, y, 0.1815), (10.04, 0.014, 0.004), 0)
for j in range(10):
    y = -1.75 + j * 0.82
    seams.box((1.585, y, 0.1815), (2.04, 0.014, 0.004), 0)
seams.build()

# tactile paving
box("Tactile_Front", (-2.95, -1.58, 0.192), (4.35, 0.32, 0.028),
    M_TACTILE, bevel=0.01, coll=STREET, outline=False)
box("Tactile_Corner", (1.63, -1.41, 0.192), (1.30, 0.64, 0.028),
    M_TACTILE, bevel=0.01, coll=STREET, outline=False)
box("Tactile_Side", (1.97, 3.55, 0.192), (0.32, 4.15, 0.028),
    M_TACTILE, bevel=0.01, coll=STREET, outline=False)
dots = Batch("Tactile_Dots", [M_TACTILE], STREET, False)
for i in range(13):
    for j in range(2):
        dots.pillar((-4.95 + i * 0.33, -1.72 + j * 0.24, 0.203), 0.035,
                    0.018, 0, sides=8)
for i in range(3):
    for j in range(3):
        dots.pillar((1.23 + i * 0.36, -1.63 + j * 0.30, 0.203), 0.035,
                    0.018, 0, sides=8)
for j in range(12):
    for i in range(2):
        dots.pillar((1.88 + i * 0.26, 1.80 + j * 0.31, 0.203), 0.035,
                    0.018, 0, sides=8)
dots.build()

# drainage channels / grates
for idx, (gx, gy, ang) in enumerate([(-3.65, -1.80, 0.0), (1.48, -1.79, 0.0),
                                     (2.58, 3.18, math.pi / 2),
                                     (2.58, 5.24, math.pi / 2)]):
    box(f"Drain_Frame_{idx}", (gx, gy, 0.075), (0.92, 0.34, 0.03),
        M_DARK, bevel=0.01, rot=(0, 0, ang), coll=STREET, outline=True)
    for k in range(6):
        off = -0.33 + k * 0.132
        box(f"Drain_Slat_{idx}_{k}", (gx + off, gy, 0.093),
            (0.035, 0.28, 0.018), M_METAL_LIGHT,
            rot=(0, 0, ang), coll=STREET, outline=False)

# manhole covers
for i, (mx, my) in enumerate([(3.35, -3.42), (-5.60, -4.25)]):
    cyl(f"Manhole_{i}", (mx, my, 0.058), 0.44, 0.022, M_METAL,
        verts=32, coll=STREET, outline=True)
    cyl(f"Manhole_Rim_{i}", (mx, my, 0.067), 0.47, 0.008, M_DARK,
        verts=32, coll=STREET, outline=False)
    for k in range(4):
        a = k * math.pi / 4
        box(f"Manhole_Rib_{i}_{k}", (mx + math.cos(a) * 0.19,
                                     my + math.sin(a) * 0.19, 0.071),
            (0.34, 0.025, 0.006), M_METAL_LIGHT,
            rot=(0, 0, a), coll=STREET, outline=False)

# crosswalk - front (bars run away from camera)
for i in range(6):
    x = -4.55 + i * 0.76
    box(f"Crosswalk_F_{i}", (x, -3.08, 0.061), (0.48, 2.02, 0.012),
        M_ROADPAINT, bevel=0.012, coll=STREET, outline=False)
# crosswalk - side
for i in range(6):
    y = 2.73 + i * 0.65
    box(f"Crosswalk_S_{i}", (3.63, y, 0.061), (1.83, 0.40, 0.012),
        M_ROADPAINT, bevel=0.012, coll=STREET, outline=False)

# road lane paint
for i in range(7):
    x = -7.15 + i * 1.52
    if -5.1 < x < -0.3:
        continue
    box(f"LaneDash_F_{i}", (x, -5.65, 0.057), (0.78, 0.105, 0.008),
        M_ROADPAINT, coll=STREET, outline=False)
for i in range(5):
    y = -0.55 + i * 1.55
    box(f"LaneDash_S_{i}", (5.62, y, 0.057), (0.105, 0.75, 0.008),
        M_ROADPAINT, coll=STREET, outline=False)
box("StopLine_F", (-4.20, -1.99, 0.058), (2.7, 0.16, 0.008),
    M_ROADPAINT, coll=STREET, outline=False)
box("StopLine_S", (2.95, 3.72, 0.058), (0.16, 2.1, 0.008),
    M_ROADPAINT, coll=STREET, outline=False)

# parking bay to the right
for i, x in enumerate([3.28, 6.88]):
    box(f"ParkLine_{i}", (x, 3.32, 0.059), (0.08, 2.20, 0.008),
        M_ROADPAINT, coll=STREET, outline=False)
box("ParkLine_End", (5.08, 4.43, 0.059), (3.68, 0.08, 0.008),
    M_ROADPAINT, coll=STREET, outline=False)
box("Park_Block", (5.08, 2.29, 0.075), (0.38, 0.26, 0.12),
    M_CURB, bevel=0.02, coll=STREET, outline=True)

# ----------------------------------------------------------------------------
# Store shell
# ----------------------------------------------------------------------------
SX0, SX1 = -5.35, 0.55
SY0, SY1 = 0.35, 5.20
SCX = (SX0 + SX1) / 2
SCY = (SY0 + SY1) / 2
GF_TOP = 3.18
UPPER_TOP = 5.02

# ground-floor wall mass at rear / left
box("Wall_Rear", (SCX, 5.02, 1.70), (5.70, 0.34, 3.00), M_WALL,
    bevel=0.02, coll=ARCH, outline=True)
box("Wall_Left", (-5.22, SCY, 1.70), (0.28, 4.70, 3.00), M_WALL,
    bevel=0.02, coll=ARCH, outline=True)
box("Wall_Right_Rear", (0.42, 4.10, 1.70), (0.28, 2.18, 3.00), M_WALL,
    bevel=0.02, coll=ARCH, outline=True)
box("Wall_Right_Corner", (0.42, 0.62, 1.70), (0.28, 0.55, 3.00), M_WALL,
    bevel=0.02, coll=ARCH, outline=True)
box("Wall_Right_Header", (0.42, 1.80, 2.80), (0.28, 1.95, 0.76), M_WALL,
    bevel=0.02, coll=ARCH, outline=True)

# front corner piers + header / kick plates
box("Pier_Front_Left", (-5.22, 0.52, 1.70), (0.28, 0.36, 3.00), M_WALL,
    bevel=0.02, coll=ARCH, outline=True)
box("Front_Header", (SCX, 0.50, 2.83), (5.62, 0.30, 0.74), M_WALL,
    bevel=0.02, coll=ARCH, outline=True)
box("Front_Kick", (SCX, 0.49, 0.37), (5.62, 0.28, 0.29), M_TRIM,
    bevel=0.015, coll=ARCH, outline=True)
box("Side_Kick", (0.47, 1.78, 0.37), (0.22, 2.05, 0.29), M_TRIM,
    bevel=0.015, coll=ARCH, outline=True)
box("Side_Header", (0.47, 1.78, 2.80), (0.22, 2.05, 0.76), M_WALL,
    bevel=0.015, coll=ARCH, outline=True)

# glass wall front (slightly recessed behind frames)
for i, (x0, x1) in enumerate([(-4.98, -3.34), (-3.30, -1.58),
                               (-1.52, -0.26), (-0.22, 0.32)]):
    box(f"FrontGlass_{i}", ((x0 + x1) / 2, 0.47, 1.52),
        (x1 - x0 - 0.02, 0.028, 1.86), M_GLASS_CLEAR,
        coll=ARCH, outline=False)
# glass wall side
box("SideGlass", (0.48, 1.78, 1.52), (0.028, 2.00, 1.86), M_GLASS_CLEAR,
    coll=ARCH, outline=False)

# window/door mullions
for i, x in enumerate([-5.00, -3.32, -1.56, -0.24, 0.34]):
    box(f"Mullion_F_{i}", (x, 0.44, 1.53), (0.055, 0.075, 1.95),
        M_METAL, bevel=0.008, coll=ARCH, outline=True)
for i, x in enumerate([-4.57, -3.48, -1.90, -0.75]):
    box(f"DoorPost_{i}", (x, 0.43, 1.53), (0.035, 0.055, 1.92),
        M_METAL_LIGHT, coll=ARCH, outline=False)
box("Front_Glass_Head", (SCX, 0.45, 2.44), (5.6, 0.07, 0.065),
    M_METAL, coll=ARCH, outline=True)
box("Front_Glass_Sill", (SCX, 0.46, 0.57), (5.6, 0.08, 0.06),
    M_METAL, coll=ARCH, outline=True)
for i, y in enumerate([0.49, 0.84, 2.42, 2.70]):
    box(f"SideGlass_Bar_{i}", (0.45, y, 1.53), (0.07, 0.045, 1.93),
        M_METAL, coll=ARCH, outline=True)
box("Side_Glass_Head", (0.45, 1.78, 2.44), (0.07, 2.10, 0.065),
    M_METAL, coll=ARCH, outline=True)
box("Side_Glass_Sill", (0.45, 1.78, 0.57), (0.08, 2.10, 0.06),
    M_METAL, coll=ARCH, outline=True)

# sliding entrance doors
box("Door_Glass_L", (-1.04, 0.45, 1.48), (0.48, 0.03, 1.78), M_GLASS_CLEAR,
    coll=ARCH, outline=False)
box("Door_Glass_R", (-0.54, 0.45, 1.48), (0.48, 0.03, 1.78), M_GLASS_CLEAR,
    coll=ARCH, outline=False)
box("Door_Handle", (-0.80, 0.39, 1.34), (0.075, 0.035, 0.52), M_METAL_LIGHT,
    bevel=0.012, coll=ARCH, outline=True)
box("Door_Threshold", (-0.79, 0.49, 0.53), (1.18, 0.16, 0.035), M_METAL,
    coll=ARCH, outline=False)

# diagonal glass reflections (a classic anime touch)
M_GLARE = emit_mat("Glass_Specular", (0.58, 0.76, 0.88, 1), 0.5, alpha=0.16)
for i, (x, z, w, h) in enumerate([(-4.10, 1.55, 0.10, 1.52),
                                   (-2.50, 1.62, 0.08, 1.28),
                                   (-0.98, 1.25, 0.07, 1.18)]):
    box(f"GlassStreak_F_{i}", (x, 0.405, z), (w, 0.012, h), M_GLARE,
        rot=(0, math.radians(-18), 0), coll=ARCH, outline=False)
for i, (y, z, w, h) in enumerate([(1.35, 1.58, 0.08, 1.28),
                                   (2.12, 1.35, 0.06, 1.05)]):
    box(f"GlassStreak_S_{i}", (0.418, y, z), (0.012, w, h), M_GLARE,
        rot=(0, math.radians(-18), 0), coll=ARCH, outline=False)

# soft warm wash inside the glass
box("Window_Warm_Wash", (-2.2, 0.52, 1.40), (4.6, 0.02, 1.25),
    emit_mat("Window_Wash", hexc("#ffb968"), 0.08, alpha=0.10),
    coll=ARCH, outline=False)

# ----------------------------------------------------------------------------
# Storefront posters & banners
# ----------------------------------------------------------------------------
box("Poster_Sale", (-2.62, 0.422, 2.30), (2.24, 0.025, 0.20), M_RED,
    bevel=0.01, coll=DETAIL, outline=True)
box("Poster_Sale_Inner", (-2.62, 0.406, 2.30), (2.16, 0.01, 0.13),
    emit_mat("Poster_Sale_Inner_Mat", hexc("#f7e8cf"), 0.45),
    coll=DETAIL, outline=False)
text_obj("Poster_Sale_Text", "本日のおすすめ  SALE", (-2.62, 0.396, 2.30),
         0.095, emit_mat("Poster_Sale_Text_Mat", hexc("#a82f35"), 0.35),
         rot=(math.radians(90), 0, 0), extrude=0.002, coll=DETAIL,
         font=FONT_BOLD)

# green seasonal poster, left front window
box("Poster_Oden_Back", (-4.43, 0.425, 1.55), (0.58, 0.018, 0.98),
    M_GREEN, bevel=0.01, coll=DETAIL, outline=True)
box("Poster_Oden_Paper", (-4.43, 0.412, 1.55), (0.50, 0.012, 0.87),
    emit_mat("Poster_Oden_Paper_Mat", hexc("#f4eed8"), 0.45),
    coll=DETAIL, outline=False)
box("Poster_Oden_Header", (-4.43, 0.402, 1.86), (0.50, 0.01, 0.22),
    emit_mat("Poster_Oden_Header_Mat", hexc("#56a06f"), 0.5),
    coll=DETAIL, outline=False)
text_obj("Poster_Oden_Header_Text", "新発売", (-4.43, 0.394, 1.86), 0.12,
         emit_mat("Poster_Oden_Header_Text_Mat", hexc("#fff8e8"), 0.55),
         rot=(math.radians(90), 0, 0), extrude=0.002, coll=DETAIL,
         font=FONT_BOLD)
text_obj("Poster_Oden_Text", "あったか〜い\nおでん", (-4.43, 0.394, 1.53),
         0.095, M_SIGNINK, rot=(math.radians(90), 0, 0), extrude=0.002,
         coll=DETAIL, font=FONT_BOLD, line_spacing=1.2)
text_obj("Poster_Oden_Price", "各  ¥100", (-4.43, 0.394, 1.28), 0.07,
         emit_mat("Poster_Oden_Price_Mat", hexc("#b7463f"), 0.4),
         rot=(math.radians(90), 0, 0), extrude=0.002, coll=DETAIL,
         font=FONT_MED)

# coffee poster
box("Poster_Coffee", (-3.43, 0.422, 1.40), (0.54, 0.018, 0.72),
    emit_mat("Poster_Coffee_Mat", hexc("#f3e8ca"), 0.45), bevel=0.01,
    coll=DETAIL, outline=True)
box("Poster_Coffee_Circle", (-3.43, 0.408, 1.53), (0.28, 0.01, 0.28),
    emit_mat("Poster_Coffee_Circle_Mat", hexc("#d38a3d"), 0.5),
    coll=DETAIL, outline=False)
text_obj("Poster_Coffee_Text", "HOT COFFEE", (-3.43, 0.398, 1.68), 0.062,
         emit_mat("Poster_Coffee_Text_Mat", hexc("#5d3a25"), 0.4),
         rot=(math.radians(90), 0, 0), extrude=0.002, coll=DETAIL,
         font=FONT_BOLD)
text_obj("Poster_Coffee_Price", "¥100", (-3.43, 0.398, 1.30), 0.13,
         emit_mat("Poster_Coffee_Price_Mat", hexc("#b54634"), 0.45),
         rot=(math.radians(90), 0, 0), extrude=0.003, coll=DETAIL,
         font=FONT_BOLD)

# side-window poster facing the side street
box("Poster_Side_Back", (0.426, 1.42, 1.62), (0.02, 0.60, 0.86),
    M_GREEN_DARK, bevel=0.01, coll=DETAIL, outline=True)
box("Poster_Side_Paper", (0.414, 1.42, 1.62), (0.012, 0.52, 0.76),
    emit_mat("Poster_Side_Paper_Mat", hexc("#f1e5c6"), 0.45),
    coll=DETAIL, outline=False)
text_obj("Poster_Side_Text", "SALE\n本日限り", (0.404, 1.42, 1.66), 0.095,
         emit_mat("Poster_Side_Text_Mat", hexc("#a9433c"), 0.4),
         rot=(math.radians(90), 0, math.radians(90)), extrude=0.002,
         coll=DETAIL, font=FONT_BOLD, line_spacing=1.15)
text_obj("Poster_Side_Small", "MACHIKADO MART", (0.404, 1.42, 1.30),
         0.042, M_SIGNINK, rot=(math.radians(90), 0, math.radians(90)),
         extrude=0.002, coll=DETAIL, font=FONT_MED)

# ----------------------------------------------------------------------------
# Upper storey, roof
# ----------------------------------------------------------------------------
box("Upper_Storey", (SCX, SCY, 4.085), (5.88, 4.83, 1.84), M_WALL_UP,
    bevel=0.025, coll=ARCH, outline=True)
box("Upper_Trim_Band", (SCX, 0.33, 3.22), (5.94, 0.10, 0.10), M_TRIM,
    bevel=0.008, coll=ARCH, outline=True)
box("Upper_Trim_Band_S", (0.56, SCY, 3.22), (0.10, 4.82, 0.10), M_TRIM,
    bevel=0.008, coll=ARCH, outline=True)

# upper facade windows (front)
win_specs = [(-4.08, 1.02, "warm"), (-2.42, 0.92, "dark"),
             (-0.58, 0.98, "warm")]
for i, (wx, ww, kind) in enumerate(win_specs):
    z = 4.12
    box(f"UpWin_Frame_{i}", (wx, 0.315, z), (ww + 0.12, 0.055, 1.06),
        M_METAL, bevel=0.01, coll=ARCH, outline=True)
    pane = M_WARM if kind == "warm" else M_DARK
    box(f"UpWin_Pane_{i}", (wx, 0.283, z), (ww, 0.02, 0.94), pane,
        coll=ARCH, outline=False)
    if kind == "warm":
        # curtains / glowing interior strips
        for k in range(3):
            cxx = wx - ww / 2 + (k + 0.5) * ww / 3
            box(f"UpWin_Curtain_{i}_{k}", (cxx, 0.270, z - 0.02),
                (ww / 5.8, 0.014, 0.84),
                emit_mat(f"Curtain_{i}_{k}", hexc("#f7cf96"), 0.65),
                coll=ARCH, outline=False)
    box(f"UpWin_CrossV_{i}", (wx, 0.263, z), (0.045, 0.016, 0.94),
        M_METAL, coll=ARCH, outline=False)
    box(f"UpWin_CrossH_{i}", (wx, 0.262, z), (ww, 0.016, 0.042),
        M_METAL, coll=ARCH, outline=False)
    box(f"UpWin_Sill_{i}", (wx, 0.26, z - 0.57), (ww + 0.20, 0.16, 0.07),
        M_TRIM, bevel=0.01, coll=ARCH, outline=True)
    box(f"UpWin_Hood_{i}", (wx, 0.24, z + 0.58), (ww + 0.16, 0.18, 0.055),
        M_DARK, coll=ARCH, outline=True)

# subtle warm wall wash above the lightbox
wallwash_mat = emit_mat("Warm_Wall_Wash", hexc("#ffd9a0"), 0.35, alpha=0.10)
wallwash_mat.surface_render_method = "BLENDED"
plane("Warm_Upper_Wall_Wash", (-2.35, 0.339, 4.16), (5.75, 1.60),
      wallwash_mat, rot=(math.radians(90), 0, 0), coll=DETAIL,
      outline=False)


# side balcony
box("Balcony_Slab", (0.91, 2.74, 3.48), (0.74, 2.75, 0.12), M_TRIM,
    bevel=0.025, coll=ARCH, outline=True)
for i, y in enumerate([2.10, 3.38]):
    box(f"Balcony_Bracket_{i}", (0.82, y, 3.31), (0.44, 0.10, 0.32),
        M_METAL, coll=ARCH, outline=True)
# railing posts and rails
for i, y in enumerate([1.42, 1.87, 2.32, 2.77, 3.22, 3.67, 4.08]):
    box(f"Balcony_Post_{i}", (1.22, y, 3.74), (0.045, 0.045, 0.62),
        M_DARK, coll=ARCH, outline=True)
box("Balcony_Rail_Top", (1.22, 2.75, 4.04), (0.075, 2.78, 0.055),
    M_DARK, bevel=0.01, coll=ARCH, outline=True)
box("Balcony_Rail_Mid", (1.22, 2.75, 3.79), (0.04, 2.78, 0.035),
    M_DARK, coll=ARCH, outline=False)
box("Balcony_Rail_Low", (1.22, 2.75, 3.57), (0.04, 2.78, 0.035),
    M_DARK, coll=ARCH, outline=False)

# side upper windows / sliding doors
for i, wy in enumerate([2.05, 3.35]):
    ww = 1.0
    box(f"UpWin_S_Frame_{i}", (0.548, wy, 4.10), (0.05, ww + 0.10, 1.02),
        M_METAL, bevel=0.008, coll=ARCH, outline=True)
    box(f"UpWin_S_Pane_{i}", (0.575, wy, 4.10), (0.02, ww, 0.90),
        M_WARM if i == 0 else M_WARM_DEEP, coll=ARCH, outline=False)
    for k in range(2):
        box(f"UpWin_S_Bar_{i}_{k}", (0.59, wy - 0.2 + k * 0.4, 4.1),
            (0.016, 0.035, 0.92), M_METAL, coll=ARCH, outline=False)
    box(f"UpWin_S_Sill_{i}", (0.60, wy, 3.55), (0.18, ww + 0.18, 0.06),
        M_TRIM, coll=ARCH, outline=True)
# curtains
for i, wy in enumerate([1.75, 3.05]):
    box(f"Balcony_Curtain_{i}", (0.58, wy, 4.12), (0.012, 0.30, 0.82),
        emit_mat(f"Balc_Curtain_{i}", hexc("#f6c78d"), 0.55),
        coll=ARCH, outline=False)
# balcony plants
cyl("Balcony_Pot_1", (1.02, 1.62, 3.62), 0.11, 0.20, M_WOOD_LIGHT,
    verts=16, coll=PROPS, outline=True)
ico("Balcony_Plant_1", (1.02, 1.62, 3.80), 0.20, M_TREE, subdiv=2,
    scale=(1, 1, 0.8), coll=VEG, outline=False)
cyl("Balcony_Pot_2", (1.02, 3.84, 3.62), 0.10, 0.18, M_WOOD_LIGHT,
    verts=16, coll=PROPS, outline=True)
ico("Balcony_Plant_2", (1.02, 3.84, 3.78), 0.17, M_TREE_LIGHT, subdiv=2,
    scale=(1, 1, 0.9), coll=VEG, outline=False)
# towels hanging over the balcony rail
box("Balcony_Towel_1", (1.255, 2.30, 3.82), (0.045, 0.36, 0.34),
    toon_mat("Towel_Blue", hexc("#6d92ac"), emit=0.12), bevel=0.012,
    coll=PROPS, outline=True)
box("Balcony_Towel_2", (1.255, 3.02, 3.86), (0.045, 0.26, 0.25),
    toon_mat("Towel_Cream", hexc("#d9c6a0"), emit=0.12), bevel=0.010,
    coll=PROPS, outline=True)
# a little hanging lantern by the balcony door
wire("Balcony_Lantern_Cord", [(0.70, 2.52, 3.90), (0.70, 2.52, 3.72)],
     0.007, M_DARK, PROPS, False)
sphere("Balcony_Lantern", (0.70, 2.52, 3.64), 0.105, M_LANTERN, seg=14,
       rings=10, scale=(1, 1, 1.15), coll=PROPS, outline=True)

# pink neon-ish wash on the corner of the upper wall
wash_mat = emit_mat("Pink_Wash_Mat", hexc("#e777a3"), 0.55, alpha=0.26)
wash_mat.surface_render_method = "BLENDED"
wash = mesh_obj("Pink_Wall_Wash",
                [(0.566, 0.55, 3.25), (0.566, 4.60, 3.25),
                 (0.566, 4.60, 4.96), (0.566, 0.55, 4.96)],
                [(0, 1, 2, 3)], wash_mat, ARCH, False)
# front pink reflection patch near corner
washf_mat = emit_mat("Pink_Wash_Front_Mat", hexc("#e777a3"), 0.40, alpha=0.22)
washf_mat.surface_render_method = "BLENDED"
mesh_obj("Pink_Wall_Wash_Front",
         [(-1.1, 0.337, 3.28), (0.30, 0.337, 3.28),
          (0.30, 0.337, 4.95), (-1.1, 0.337, 4.95)],
         [(0, 1, 2, 3)], washf_mat, ARCH, False)
# slim magenta neon tube on the corner
box("Neon_Pink_Tube", (0.60, 0.48, 3.56), (0.045, 0.045, 0.52),
    emit_mat("Neon_Pink_Tube_Mat", hexc("#ff4f96"), 2.8),
    coll=PROPS, outline=False)
box("Neon_Pink_Tube_Side", (0.60, 1.10, 3.42), (0.04, 0.72, 0.04),
    emit_mat("Neon_Pink_Tube_Side_Mat", hexc("#ff4f96"), 2.4),
    coll=PROPS, outline=False)

# roof slab + parapet
box("Roof_Slab", (SCX, SCY, 5.10), (6.05, 5.02, 0.18), M_DARK,
    bevel=0.025, coll=ARCH, outline=True)
for nm, loc, size in [
    ("Parapet_F", (SCX, 0.25, 5.24), (6.08, 0.14, 0.30)),
    ("Parapet_B", (SCX, 5.30, 5.24), (6.08, 0.14, 0.30)),
    ("Parapet_L", (-5.42, SCY, 5.24), (0.14, 5.10, 0.30)),
    ("Parapet_R", (0.62, SCY, 5.24), (0.14, 5.10, 0.30)),
]:
    box(nm, loc, size, M_TRIM, bevel=0.02, coll=ARCH, outline=True)

# rooftop equipment
for i, (ax, ay, aw, ah) in enumerate([(-3.55, 3.55, 1.10, 0.64),
                                      (-1.55, 4.05, 0.86, 0.52)]):
    box(f"Rooftop_AC_{i}", (ax, ay, 5.22 + ah / 2), (aw, 0.82, ah),
        M_METAL_LIGHT, bevel=0.04, coll=PROPS, outline=True)
    cyl(f"Rooftop_AC_Fan_{i}", (ax, ay - 0.425, 5.22 + ah / 2),
        0.25, 0.02, M_DARK, verts=24,
        rot=(math.radians(90), 0, 0), coll=PROPS, outline=True)
    for k in range(5):
        a = k * math.pi * 2 / 5
        box(f"Rooftop_AC_Blade_{i}_{k}",
            (ax + math.cos(a) * 0.12, ay - 0.44,
             5.22 + ah / 2 + math.sin(a) * 0.12),
            (0.20, 0.008, 0.045), M_METAL_LIGHT,
            rot=(0, 0, a), coll=PROPS, outline=False)
# vent stack, pipes, antenna
cyl("Roof_Vent", (-4.55, 4.55, 5.58), 0.14, 0.92, M_METAL_LIGHT,
    verts=16, coll=PROPS, outline=True)
cyl("Roof_Vent_Cap", (-4.55, 4.55, 6.07), 0.22, 0.10, M_METAL,
    verts=16, coll=PROPS, outline=True)
cyl("Roof_Pipe", (0.10, 4.93, 5.48), 0.055, 0.68, M_METAL_LIGHT,
    verts=12, coll=PROPS, outline=True)
wire("Roof_Antenna", [(-0.15, 4.55, 5.3), (-0.15, 4.55, 7.2)],
     0.018, M_METAL, PROPS, True)
for k in range(3):
    box(f"Antenna_Cross_{k}", (-0.15, 4.55, 6.45 + k * 0.23),
        (0.72 - k * 0.16, 0.025, 0.022), M_METAL, coll=PROPS, outline=False)
# small satellite dish on roof
cyl("Dish_Pole", (-4.65, 1.15, 5.45), 0.045, 0.55, M_METAL,
    verts=12, coll=PROPS, outline=True)
bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=0.32,
                                     location=(-4.65, 1.15, 5.78))
dish = bpy.context.object
dish.name = "Roof_Dish"
dish.scale = (1, 0.32, 1)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
dish.data.materials.append(M_METAL_LIGHT)
_link(dish, PROPS, True)

# downpipe
cyl("Downpipe_Front", (0.43, 0.25, 2.0), 0.052, 3.55, M_METAL_LIGHT,
    verts=12, coll=ARCH, outline=True)
cyl("Downpipe_Side", (-5.28, 0.34, 2.0), 0.052, 3.55, M_METAL_LIGHT,
    verts=12, coll=ARCH, outline=True)
for i in range(4):
    box(f"PipeClamp_{i}", (0.43, 0.26, 0.85 + i * 0.9), (0.12, 0.08, 0.045),
        M_DARK, coll=ARCH, outline=False)

# exterior AC on the rear wall / front wall
box("AC_Upper", (-2.92, 0.23, 3.30), (0.82, 0.34, 0.50), M_METAL_LIGHT,
    bevel=0.04, coll=PROPS, outline=True)
cyl("AC_Upper_Fan", (-2.92, 0.045, 3.30), 0.18, 0.025, M_DARK, verts=24,
    rot=(math.radians(90), 0, 0), coll=PROPS, outline=True)
for k in range(4):
    box(f"AC_Grille_{k}", (-2.92, 0.028, 3.17 + k * 0.075),
        (0.44, 0.01, 0.014), M_METAL_LIGHT, coll=PROPS, outline=False)
box("AC_Side", (0.80, 4.65, 0.58), (0.50, 0.34, 0.62), M_METAL_LIGHT,
    bevel=0.04, coll=PROPS, outline=True)
cyl("AC_Side_Fan", (1.06, 4.65, 0.62), 0.20, 0.02, M_DARK, verts=24,
    rot=(0, math.radians(90), 0), coll=PROPS, outline=True)
wire("AC_Conduit", [(0.98, 4.65, 0.90), (0.98, 4.65, 2.6),
                    (0.58, 4.80, 2.9)], 0.022, M_METAL_LIGHT, PROPS, False)

# ----------------------------------------------------------------------------
# Storefront signage
# ----------------------------------------------------------------------------
# fascia band (cream lightbox)
box("Fascia_Front", (SCX, 0.20, 2.87), (5.78, 0.18, 0.78), M_SIGNCREAM,
    bevel=0.015, coll=ARCH, outline=True)
box("Fascia_Side", (0.65, SCY, 2.87), (0.18, 4.88, 0.78), M_SIGNCREAM,
    bevel=0.015, coll=ARCH, outline=True)
# colored brand blocks
for i, (col, zz) in enumerate([(M_GREEN, 3.05), (M_ORANGE, 2.87),
                                (M_RED, 2.69)]):
    box(f"BrandBlock_F_{i}", (-5.08, 0.098, zz), (0.14, 0.025, 0.16), col,
        coll=DETAIL, outline=False)
for i, (col, yy) in enumerate([(M_GREEN, 1.28), (M_ORANGE, 1.45),
                                (M_RED, 1.62)]):
    box(f"BrandBlock_S_{i}", (0.752, yy, 2.87), (0.025, 0.15, 0.56), col,
        coll=DETAIL, outline=False)

# 24h panel on front fascia
box("Fascia_24Panel", (0.08, 0.098, 2.87), (0.86, 0.025, 0.72), M_DARK,
    coll=DETAIL, outline=True)
text_obj("Fascia_24", "24", (0.08, 0.078, 2.95), 0.27, M_WHITE,
         rot=(math.radians(90), 0, 0), extrude=0.005, coll=DETAIL,
         font=FONT_BOLD)
text_obj("Fascia_HOURS", "H O U R S", (0.08, 0.078, 2.68), 0.058, M_WHITE,
         rot=(math.radians(90), 0, 0), extrude=0.004, coll=DETAIL,
         font=FONT_MED)

# main Japanese fascia lettering
text_obj("Fascia_Main_JP", "まちかどマート", (-2.45, 0.094, 2.97),
         0.55, M_SIGNINK, rot=(math.radians(90), 0, 0), align_x="CENTER",
         align_y="CENTER", extrude=0.011, coll=DETAIL, font=FONT_BOLD,
         spacing=0.94)
text_obj("Fascia_Main_EN", "M A C H I K A D O   M A R T",
         (-2.55, 0.094, 2.59), 0.072, M_SIGNINK,
         rot=(math.radians(90), 0, 0), align_x="CENTER", align_y="CENTER",
         extrude=0.004, coll=DETAIL, font=FONT_MED, spacing=0.9)
text_obj("Fascia_Main_Small", "OPEN 24 HOURS  ·  COFFEE  ·  ATM",
         (-2.55, 0.094, 2.485), 0.040, M_SIGNINK,
         rot=(math.radians(90), 0, 0), align_x="CENTER", align_y="CENTER",
         extrude=0.003, coll=DETAIL, font=FONT_MED)
# side fascia lettering
text_obj("Fascia_Side_JP", "まちかどマート", (0.756, 2.38, 2.97),
         0.50, M_SIGNINK, rot=(math.radians(90), 0, math.radians(90)),
         align_x="CENTER", align_y="CENTER", extrude=0.011, coll=DETAIL,
         font=FONT_BOLD, spacing=0.94)
text_obj("Fascia_Side_EN", "M A C H I K A D O   M A R T",
         (0.756, 2.28, 2.64), 0.070, M_SIGNINK,
         rot=(math.radians(90), 0, math.radians(90)), align_x="CENTER",
         align_y="CENTER", extrude=0.004, coll=DETAIL, font=FONT_MED)
text_obj("Fascia_Side_ATM", "A T M", (0.756, 4.43, 2.88), 0.070, M_RED,
         rot=(math.radians(90), 0, math.radians(90)), align_x="CENTER",
         align_y="CENTER", extrude=0.004, coll=DETAIL, font=FONT_BOLD)

# warm light strip under fascia
box("Fascia_Underglow", (SCX, 0.11, 2.46, ), (5.3, 0.06, 0.035),
    emit_mat("Underglow_Warm", hexc("#ffcea0"), 2.4), coll=DETAIL,
    outline=False)
box("Fascia_Underglow_S", (0.742, 2.55, 2.46), (0.06, 4.2, 0.035),
    emit_mat("Underglow_Warm_S", hexc("#ffcea0"), 2.4), coll=DETAIL,
    outline=False)

# corner pylon sign - 24H / まちかど / ATM
box("Pylon_Frame", (0.10, -0.19, 3.69), (0.58, 0.16, 1.86), M_METAL,
    bevel=0.02, coll=PROPS, outline=True)
box("Pylon_Face", (0.10, -0.275, 3.69), (0.51, 0.025, 1.78),
    M_SIGNCREAM, coll=PROPS, outline=True)
box("Pylon_Top", (0.10, -0.285, 4.48), (0.51, 0.025, 0.25), M_ORANGE,
    coll=PROPS, outline=False)
text_obj("Pylon_24h", "24h", (0.10, -0.302, 4.49), 0.185, M_WHITE,
         rot=(math.radians(90), 0, 0), extrude=0.004, coll=DETAIL,
         font=FONT_BOLD)
for i, ch in enumerate("まちかど"):
    text_obj(f"Pylon_JP_{i}", ch, (0.10, -0.302, 4.12 - i * 0.255),
             0.205, M_SIGNINK, rot=(math.radians(90), 0, 0),
             extrude=0.004, coll=DETAIL, font=FONT_BOLD)
box("Pylon_ATMbar", (0.10, -0.300, 3.00), (0.40, 0.014, 0.045), M_ORANGE,
    coll=DETAIL, outline=False)
text_obj("Pylon_ATM", "ATM", (0.10, -0.303, 2.89), 0.105, M_SIGNINK,
         rot=(math.radians(90), 0, 0), extrude=0.003, coll=DETAIL,
         font=FONT_BOLD)
text_obj("Pylon_Small", "MACHIKADO MART", (0.10, -0.303, 2.77), 0.034,
         M_SIGNINK, rot=(math.radians(90), 0, 0), extrude=0.002,
         coll=DETAIL, font=FONT_MED)
# side face of the pylon
text_obj("Pylon_Side_24h", "24h", (0.407, -0.19, 4.49), 0.15, M_WHITE,
         rot=(math.radians(90), 0, math.radians(90)), extrude=0.003,
         coll=DETAIL, font=FONT_BOLD)
for i, ch in enumerate("まちかど"):
    text_obj(f"Pylon_Side_JP_{i}", ch, (0.407, -0.19, 4.12 - i * 0.22),
             0.17, M_SIGNINK, rot=(math.radians(90), 0, math.radians(90)),
             extrude=0.003, coll=DETAIL, font=FONT_BOLD)
# pylon bracket
box("Pylon_Bracket", (-0.13, -0.18, 3.78), (0.36, 0.09, 0.10),
    M_DARK, coll=PROPS, outline=True)
box("Pylon_Bracket_2", (0.10, -0.09, 2.93), (0.10, 0.24, 0.10),
    M_DARK, coll=PROPS, outline=True)

# awning over entrance
box("Entrance_Awning", (-0.84, -0.18, 2.47), (1.95, 0.72, 0.055),
    M_SIGNCREAM, bevel=0.012, rot=(math.radians(-6), 0, 0),
    coll=ARCH, outline=True)
box("Awning_Edge", (-0.84, -0.535, 2.43), (1.98, 0.035, 0.09), M_ORANGE,
    bevel=0.01, coll=ARCH, outline=True)
for i, xx in enumerate([-1.68, 0.02]):
    wire(f"Awning_Rod_{i}", [(xx, -0.50, 2.44), (xx, -0.12, 2.72)],
         0.014, M_METAL, ARCH, True)
    box(f"Awning_Lamp_{i}", (xx, -0.30, 2.40), (0.07, 0.10, 0.035),
        M_WARM, coll=ARCH, outline=False)

# entrance mat & welcome sign
box("Entrance_Mat", (-0.82, -0.18, 0.198), (1.58, 0.88, 0.025),
    toon_mat("Entrance_Mat_Mat", hexc("#233d36"), emit=0.12),
    bevel=0.02, coll=PROPS, outline=True)
text_obj("Entrance_Mat_Text", "W E L C O M E", (-0.82, -0.18, 0.213),
         0.075, emit_mat("Mat_Text", hexc("#cdbb91"), 0.5),
         rot=(math.radians(90), 0, 0), extrude=0.002, coll=DETAIL,
         font=FONT_MED)
box("Door_Open_Sign", (-0.80, 0.36, 1.95), (0.42, 0.03, 0.30),
    emit_mat("Open_Sign_White", hexc("#f8f1d7"), 0.8), bevel=0.02,
    coll=DETAIL, outline=True)
text_obj("Door_Open_Text", "OPEN", (-0.80, 0.338, 1.95), 0.10,
         emit_mat("Open_Sign_Red", hexc("#b63a39"), 0.55),
         rot=(math.radians(90), 0, 0), extrude=0.002, coll=DETAIL,
         font=FONT_BOLD)

# ----------------------------------------------------------------------------
# Rear service wall / back-of-house details (visible when the model is rotated)
# ----------------------------------------------------------------------------
box("Rear_ServiceDoor", (-2.35, 5.235, 1.22), (1.18, 0.06, 1.94),
    M_METAL_LIGHT, bevel=0.02, coll=ARCH, outline=True)
box("Rear_ServiceDoor_Window", (-2.35, 5.205, 1.62), (0.62, 0.02, 0.46),
    emit_mat("Rear_Door_Glow", hexc("#f0c68d"), 0.42), coll=ARCH,
    outline=False)
for i in range(3):
    box(f"Rear_ServiceDoor_Bar_{i}", (-2.35, 5.19, 1.46 + i * 0.15),
        (0.66, 0.012, 0.022), M_METAL, coll=ARCH, outline=False)
cyl("Rear_ServiceDoor_Handle", (-2.72, 5.195, 1.10), 0.035, 0.13,
    M_METAL, verts=12, rot=(math.radians(90), 0, 0), coll=ARCH,
    outline=False)
box("Rear_ServiceDoor_Step", (-2.35, 5.48, 0.25), (1.42, 0.48, 0.10),
    M_CURB, bevel=0.015, coll=ARCH, outline=True)
# rear wall lamp
wire("Rear_Lamp_Arm", [(-2.35, 5.20, 2.66), (-2.35, 5.45, 2.58)],
     0.018, M_METAL, PROPS, True)
cone("Rear_Lamp_Shade", (-2.35, 5.48, 2.50), 0.20, 0.07, 0.17, M_DARK,
     verts=16, coll=PROPS, outline=True)
sphere("Rear_Lamp_Bulb", (-2.35, 5.48, 2.39), 0.065, M_WARM, seg=12,
       rings=8, coll=PROPS, outline=False)
# rear AC unit
box("Rear_AC", (-4.38, 5.27, 3.30), (0.94, 0.38, 0.60),
    M_METAL_LIGHT, bevel=0.04, coll=PROPS, outline=True)
cyl("Rear_AC_Fan", (-4.38, 5.47, 3.30), 0.21, 0.02, M_DARK, verts=24,
    rot=(math.radians(90), 0, 0), coll=PROPS, outline=True)
wire("Rear_AC_Pipe", [(-4.38, 5.25, 3.00), (-4.38, 5.25, 2.10),
                      (-4.75, 5.23, 1.90)], 0.025, M_METAL_LIGHT,
     PROPS, False)
# rear windows
for i, (wx, wz, ww, wh) in enumerate([(-4.32, 4.15, 0.92, 0.82),
                                      (-0.25, 3.95, 0.82, 0.74)]):
    box(f"Rear_Window_Frame_{i}", (wx, 5.225, wz),
        (ww + 0.12, 0.05, wh + 0.12), M_METAL, bevel=0.01,
        coll=ARCH, outline=True)
    box(f"Rear_Window_Pane_{i}", (wx, 5.195, wz), (ww, 0.02, wh),
        M_DARK if i == 0 else M_WARM_DEEP, coll=ARCH, outline=False)
    box(f"Rear_Window_Bar_{i}", (wx, 5.18, wz), (0.04, 0.02, wh),
        M_METAL, coll=ARCH, outline=False)
# meter boxes and cable conduit
for i, (mx, mz) in enumerate([(0.15, 2.05), (-0.05, 1.80)]):
    box(f"Rear_Meter_{i}", (mx, 5.235, mz), (0.30, 0.13, 0.38),
        M_METAL_LIGHT, bevel=0.015, coll=PROPS, outline=True)
    box(f"Rear_Meter_Door_{i}", (mx, 5.157, mz), (0.24, 0.01, 0.28),
        M_DARK, coll=PROPS, outline=False)
wire("Rear_Conduit", [(0.15, 5.21, 2.25), (0.15, 5.21, 3.05),
                      (-0.25, 5.21, 3.45)], 0.022, M_METAL_LIGHT,
     PROPS, False)
# rear downpipe
cyl("Rear_Downpipe", (-5.28, 5.26, 2.40), 0.05, 4.75,
    M_METAL_LIGHT, verts=12, coll=ARCH, outline=True)
# left-side upper windows (seen when walking around the model)
for i, (wy, warm) in enumerate([(1.55, True), (3.25, False)]):
    z = 4.02
    box(f"LeftWin_Frame_{i}", (-5.375, wy, z), (0.055, 0.86, 0.92),
        M_METAL, bevel=0.01, coll=ARCH, outline=True)
    box(f"LeftWin_Pane_{i}", (-5.405, wy, z), (0.02, 0.74, 0.80),
        M_WARM if warm else M_DARK, coll=ARCH, outline=False)
    box(f"LeftWin_BarV_{i}", (-5.418, wy, z), (0.016, 0.04, 0.80),
        M_METAL, coll=ARCH, outline=False)
    box(f"LeftWin_BarH_{i}", (-5.418, wy, z), (0.016, 0.74, 0.04),
        M_METAL, coll=ARCH, outline=False)
    box(f"LeftWin_Sill_{i}", (-5.40, wy, z - 0.50), (0.16, 0.98, 0.06),
        M_TRIM, coll=ARCH, outline=True)
# small vent and conduit on the left wall
box("Left_Vent", (-5.38, 4.25, 3.25), (0.08, 0.46, 0.32), M_METAL,
    coll=PROPS, outline=True)
for i in range(3):
    box(f"Left_Vent_Slat_{i}", (-5.425, 4.25, 3.17 + i * 0.08),
        (0.01, 0.40, 0.03), M_METAL_LIGHT, coll=PROPS, outline=False)
wire("Left_Conduit", [(-5.36, 0.55, 3.08), (-5.36, 0.55, 4.45),
                      (-5.36, 1.05, 4.60)], 0.018, M_METAL_LIGHT,
     PROPS, False)
# rear downpipe
# delivery crates + bin behind the shop
box("Rear_Crate_A", (-0.90, 5.78, 0.38), (0.62, 0.46, 0.38),
    toon_mat("Rear_Crate_Blue", hexc("#3e7187"), emit=0.1), bevel=0.02,
    coll=PROPS, outline=True)
box("Rear_Crate_B", (-0.88, 5.78, 0.75), (0.55, 0.42, 0.34),
    toon_mat("Rear_Crate_Gold", hexc("#b08d50"), emit=0.1), bevel=0.02,
    coll=PROPS, outline=True)
cyl("Rear_Bin", (-1.85, 5.70, 0.56), 0.24, 0.72, M_TEAL, verts=18,
    coll=PROPS, outline=True)
cyl("Rear_Bin_Lid", (-1.85, 5.70, 0.95), 0.26, 0.08, M_DARK, verts=18,
    coll=PROPS, outline=True)
# rear low railing / gate
for k in range(5):
    gx = -5.28 + k * 1.045
    box(f"Rear_Gate_Post_{k}", (gx, 6.05, 0.56), (0.055, 0.055, 0.72),
        M_DARK, coll=PROPS, outline=True)
for k, zz in enumerate([0.42, 0.82]):
    box(f"Rear_Gate_Rail_{k}", (-3.19, 6.05, zz), (4.18, 0.045, 0.045),
        M_DARK, coll=PROPS, outline=True)
for i in range(2):
    box(f"Rear_Bollard_{i}", (-0.80 + i * 0.35, 6.08, 0.42),
        (0.12, 0.12, 0.44), M_TACTILE, bevel=0.02, coll=PROPS,
        outline=True)

NB_X0, NB_X1 = -7.35, -5.72
NB_Y0, NB_Y1 = 0.42, 4.75
NB_CX = (NB_X0 + NB_X1) / 2
NB_CY = (NB_Y0 + NB_Y1) / 2
box("Neighbour_Body", (NB_CX, NB_CY, 1.62), (NB_X1 - NB_X0, NB_Y1 - NB_Y0, 2.85),
    toon_mat("Neighbour_Wall", hexc("#4a403b"), emit=0.08),
    bevel=0.03, coll=ARCH, outline=True)
box("Neighbour_Base", (NB_CX, NB_CY, 0.29), (NB_X1 - NB_X0 + 0.10,
                                             NB_Y1 - NB_Y0 + 0.10, 0.20),
    M_WOOD, bevel=0.015, coll=ARCH, outline=True)
# shop front / warm window
box("Neighbour_Window", (-6.48, 0.36, 1.57), (1.30, 0.04, 1.06),
    emit_mat("Neighbour_Warm_Window", hexc("#f6b96c"), 0.9),
    coll=ARCH, outline=False)
for k in range(3):
    box(f"Neighbour_WindowBar_{k}", (-6.48, 0.325, 1.18 + k * 0.34),
        (1.34, 0.03, 0.035), M_WOOD, coll=ARCH, outline=False)
box("Neighbour_WindowFrame", (-6.48, 0.34, 1.56), (1.44, 0.055, 1.18),
    M_WOOD, bevel=0.01, coll=ARCH, outline=True)
# noren curtain
for i in range(4):
    box(f"Noren_{i}", (-7.02 + i * 0.35, 0.30, 1.94),
        (0.30, 0.03, 0.42), M_SAKURA if i % 2 else M_WOOD_LIGHT,
        coll=ARCH, outline=True)
text_obj("Noren_Mark", "さくら", (-6.48, 0.278, 1.94), 0.12,
         emit_mat("Noren_Text", hexc("#f5e6d0"), 0.55),
         rot=(math.radians(90), 0, 0), extrude=0.002, coll=DETAIL,
         font=FONT_BOLD)
# shop sign board
box("Neighbour_Sign", (-6.50, 0.27, 2.53), (1.80, 0.07, 0.38), M_WOOD,
    bevel=0.015, coll=ARCH, outline=True)
text_obj("Neighbour_Sign_JP", "小料理  さくら", (-6.50, 0.225, 2.53),
         0.16, emit_mat("Neighbour_Sign_Text", hexc("#efd9a0"), 0.55),
         rot=(math.radians(90), 0, 0), extrude=0.004, coll=DETAIL,
         font=FONT_BOLD)
# noren lantern
wire("Lantern_Cord", [(-5.96, 0.18, 2.60), (-5.96, 0.18, 2.26)],
     0.012, M_DARK, PROPS, False)
cyl("Lantern_Body", (-5.96, 0.18, 2.06), 0.14, 0.34, M_LANTERN,
    verts=20, coll=PROPS, outline=True)
cyl("Lantern_Top", (-5.96, 0.18, 2.25), 0.10, 0.045, M_DARK, verts=16,
    coll=PROPS, outline=True)
cyl("Lantern_Bottom", (-5.96, 0.18, 1.87), 0.10, 0.045, M_DARK, verts=16,
    coll=PROPS, outline=True)
text_obj("Lantern_Text", "酒", (-5.96, 0.036, 2.06), 0.10,
         emit_mat("Lantern_Text_Mat", hexc("#4b2117"), 0.2),
         rot=(math.radians(90), 0, 0), extrude=0.003, coll=DETAIL,
         font=FONT_BOLD)

# gabled roof (two leaning slabs)
box("Neighbour_Roof_L", (-6.86, NB_CY, 3.25), (1.0, 4.55, 0.10),
    M_DARK, bevel=0.02, rot=(0, math.radians(24), 0), coll=ARCH,
    outline=True)
box("Neighbour_Roof_R", (-6.18, NB_CY, 3.25), (1.0, 4.55, 0.10),
    M_DARK, bevel=0.02, rot=(0, math.radians(-24), 0), coll=ARCH,
    outline=True)
box("Neighbour_Ridge", (-6.52, NB_CY, 3.52), (0.18, 4.62, 0.12), M_METAL,
    coll=ARCH, outline=True)
for i in range(7):
    box(f"Roof_Tile_{i}", (-6.52, 0.6 + i * 0.60, 3.44),
        (1.55, 0.035, 0.03), M_METAL_LIGHT, rot=(0, 0, 0),
        coll=ARCH, outline=False)
# small chimney
box("Neighbour_Chimney", (-7.02, 3.75, 3.72), (0.28, 0.34, 0.62),
    M_WOOD, bevel=0.015, coll=ARCH, outline=True)
# wooden facade slats
for i in range(5):
    box(f"Neighbour_Slat_{i}", (-6.85 + i * 0.26, 0.385, 0.93),
        (0.045, 0.03, 0.92), M_WOOD_LIGHT, coll=DETAIL, outline=False)

# hanging alley sign
box("Roji_Sign", (-5.52, 0.10, 2.18), (0.20, 0.70, 0.52), M_WOOD,
    bevel=0.015, coll=PROPS, outline=True)
text_obj("Roji_Sign_Text", "路地", (-5.52, -0.252, 2.18), 0.18,
         emit_mat("Roji_Text_Mat", hexc("#e8d6ae"), 0.55),
         rot=(math.radians(90), 0, 0), extrude=0.004, coll=DETAIL,
         font=FONT_BOLD)
# alley clutter
for i, (ax, ay, az, sx, sy, sz) in enumerate([
        (-5.52, 0.62, 0.38, 0.38, 0.40, 0.42),
        (-5.52, 0.62, 0.73, 0.30, 0.32, 0.28),
        (-5.50, 1.05, 0.36, 0.33, 0.35, 0.36)]):
    box(f"Alley_Crate_{i}", (ax, ay, az), (sx, sy, sz), M_WOOD_LIGHT,
        bevel=0.01, coll=PROPS, outline=True)
box("Alley_Poster", (-5.67, 0.42, 1.52), (0.03, 0.52, 0.65),
    emit_mat("Alley_Poster_Mat", hexc("#d9d2b4"), 0.3),
    coll=DETAIL, outline=False)
text_obj("Alley_Poster_Text", "営業中\nOPEN", (-5.69, 0.42, 1.52), 0.10,
         M_SIGNINK, rot=(math.radians(90), 0, math.radians(90)),
         extrude=0.002, coll=DETAIL, font=FONT_BOLD)
# small warm light in alley
cone("Alley_Lamp_Shade", (-5.52, 1.55, 2.36), 0.16, 0.05, 0.16, M_DARK,
     verts=16, coll=PROPS, outline=True)
sphere("Alley_Bulb", (-5.52, 1.55, 2.27), 0.055, M_WARM, seg=12, rings=8,
       coll=PROPS, outline=False)
wire("Alley_Lamp_Wire", [(-5.52, 1.55, 2.45), (-5.52, 1.55, 2.80)],
     0.01, M_DARK, PROPS, False)

# projecting old-shop sign, catches the eye at the left edge
box("Neighbour_VertSign_Frame", (-6.10, -0.24, 2.28),
    (0.38, 0.09, 0.92), M_WOOD, bevel=0.012, coll=PROPS, outline=True)
box("Neighbour_VertSign_Face", (-6.10, -0.292, 2.28),
    (0.29, 0.02, 0.80), emit_mat("Neighbour_VertSign_Mat",
                                 hexc("#f1ddb2"), 0.55),
    coll=PROPS, outline=False)
text_obj("Neighbour_VertSign_Text", "小料理\nさくら", (-6.10, -0.308, 2.31),
         0.11, M_SIGNINK, rot=(math.radians(90), 0, 0), extrude=0.003,
         coll=DETAIL, font=FONT_BOLD, line_spacing=1.25)
box("Neighbour_VertSign_Bracket", (-6.10, -0.02, 2.60),
    (0.08, 0.44, 0.06), M_METAL, coll=PROPS, outline=True)
# little warm lantern on the other corner
wire("Neighbour_Lantern2_Cord", [(-6.88, -0.06, 2.55),
                                  (-6.88, -0.06, 2.34)],
     0.010, M_DARK, PROPS, False)
cyl("Neighbour_Lantern2", (-6.88, -0.06, 2.16), 0.11, 0.28, M_LANTERN,
    verts=18, coll=PROPS, outline=True)
text_obj("Neighbour_Lantern2_Text", "灯", (-6.88, -0.172, 2.16), 0.08,
         emit_mat("Neighbour_Lantern2_Text_Mat", hexc("#4b2117"), 0.2),
         rot=(math.radians(90), 0, 0), extrude=0.002, coll=DETAIL,
         font=FONT_BOLD)

print("BUILD: store interior")

# ----------------------------------------------------------------------------
# Convenience-store interior (visible through the glass)
# ----------------------------------------------------------------------------
box("Int_Floor", (SCX, 2.74, 0.31), (5.40, 4.35, 0.10), M_INTERIOR_FLOOR,
    coll=INTERIOR, outline=False)
box("Int_Ceiling", (SCX, 2.74, 2.54), (5.40, 4.35, 0.09),
    toon_mat("Ceiling_Cream", hexc("#d9d2c2"), emit=0.2),
    coll=INTERIOR, outline=False)
box("Int_BackWall", (SCX, 4.90, 1.45), (5.38, 0.10, 2.18),
    toon_mat("Interior_BackWall", hexc("#d9c7a8"), emit=0.2),
    coll=INTERIOR, outline=False)
box("Int_LeftWall", (-5.10, 2.72, 1.45), (0.10, 4.30, 2.18),
    toon_mat("Interior_LeftWall", hexc("#cfbfa7"), emit=0.16),
    coll=INTERIOR, outline=False)
box("Int_RightWall", (0.34, 3.78, 1.45), (0.10, 2.20, 2.18),
    toon_mat("Interior_RightWall", hexc("#d9c7a8"), emit=0.16),
    coll=INTERIOR, outline=False)

# ceiling fluorescent strips
for i, (lx, ly) in enumerate([(-3.9, 2.3), (-1.8, 2.3), (-3.9, 3.8),
                               (-1.8, 3.8)]):
    box(f"Fluoro_Housing_{i}", (lx, ly, 2.47), (2.1, 0.22, 0.055),
        M_METAL_LIGHT, coll=INTERIOR, outline=False)
    box(f"Fluoro_Tube_{i}", (lx, ly, 2.435), (1.96, 0.13, 0.026),
        emit_mat(f"Fluoro_Mat_{i}", hexc("#fff4dd"), 3.2),
        coll=INTERIOR, outline=False)

# rear shelf wall
shelf_batch = Batch("Int_BackShelves", [M_SHELF, M_METAL], INTERIOR, False)
for bay in range(3):
    x0 = -4.82 + bay * 1.55
    x1 = x0 + 1.45
    # only a thin back panel: the front must stay open for the stock
    shelf_batch.box(((x0 + x1) / 2, 4.79, 1.22),
                    (x1 - x0, 0.16, 2.02), 1)
    for lev in range(5):
        z = 0.55 + lev * 0.38
        shelf_batch.box(((x0 + x1) / 2, 4.52, z),
                        (x1 - x0 - 0.04, 0.58, 0.045), 0)
    for div in range(2):
        shelf_batch.box((x0 + 0.48 + div * 0.48, 4.52, 1.25),
                        (0.035, 0.57, 1.86), 0)
shelf_batch.build()

# colorful product blocks on rear shelves
prod = Batch("Int_Products_Back", M_PRODUCT_COLORS, INTERIOR, False)
pp = random.Random(4412)
for bay in range(3):
    x0 = -4.78 + bay * 1.55
    for lev in range(4):
        z = 0.59 + lev * 0.38
        for k in range(11):
            px = x0 + 0.08 + k * 0.125 + pp.uniform(-0.012, 0.012)
            ph = pp.uniform(0.12, 0.21)
            pw = pp.uniform(0.075, 0.105)
            prod.box((px, 4.33 + pp.uniform(-0.02, 0.03),
                      z + ph / 2 + 0.025),
                     (pw, pp.uniform(0.10, 0.16), ph),
                     pp.randrange(len(M_PRODUCT_COLORS)))
prod.build()

# left refrigerator bank
fridge = Batch("Int_FridgeBank", [M_METAL_LIGHT, M_METAL, M_DARK],
               INTERIOR, False)
fridge.box((-4.72, 2.92, 1.33), (0.62, 1.95, 2.10), 0)
for i in range(3):
    fy = 2.22 + i * 0.58
    fridge.box((-4.40, fy, 1.46), (0.03, 0.50, 1.56), 2)
    fridge.box((-4.38, fy, 1.50), (0.015, 0.43, 1.38), 0)
fridge.build()
for i in range(3):
    fy = 2.22 + i * 0.58
    box(f"Fridge_DoorGlow_{i}", (-4.36, fy, 1.55), (0.012, 0.39, 1.26),
        emit_mat(f"Fridge_Glow_{i}", hexc("#d9f0e6"), 0.95),
        coll=INTERIOR, outline=False)
    for k in range(3):
        box(f"Fridge_Can_{i}_{k}", (-4.34, fy - 0.10 + k * 0.10,
                                     1.05 + (k % 2) * 0.35),
            (0.025, 0.055, 0.14),
            M_PRODUCT_COLORS[(i + k) % len(M_PRODUCT_COLORS)],
            coll=INTERIOR, outline=False)

# central gondola shelves, low enough to see into the shop
gond = Batch("Int_Gondolas", [M_SHELF, M_METAL], INTERIOR, False)
for gy in [2.78, 3.64]:
    # thin backing panel at the rear of each island (keeps the stock visible)
    gond.box((-3.28, gy + 0.16, 0.82), (2.80, 0.13, 1.12), 1)
    for lev in range(3):
        z = 0.37 + lev * 0.33
        gond.box((-3.28, gy, z), (2.86, 0.52, 0.035), 0)
    for div in range(3):
        gond.box((-4.22 + div * 0.94, gy, 0.83), (0.035, 0.52, 1.02), 0)
gond.build()
gp = Batch("Int_Gondola_Products", M_PRODUCT_COLORS, INTERIOR, False)
pr = random.Random(912)
for gy in [2.78, 3.64]:
    for lev in range(2):
        z = 0.40 + lev * 0.33
        for k in range(20):
            px = -4.55 + k * 0.13
            gp.box((px, gy - 0.18, z + 0.10),
                   (0.085, 0.16, pr.uniform(0.12, 0.20)),
                   pr.randrange(len(M_PRODUCT_COLORS)))
gp.build()

# magazine rack near the front window
mag = Batch("Int_MagazineRack", [M_METAL, M_SHELF], INTERIOR, False)
mag.box((-4.55, 1.10, 0.42), (1.25, 0.38, 0.68), 0)
for k in range(6):
    mag.box((-5.08 + k * 0.19, 1.06, 0.63), (0.15, 0.32, 0.035), 1)
mag.build()
mp = Batch("Int_Magazines", M_PRODUCT_COLORS, INTERIOR, False)
for k in range(6):
    mp.box((-5.06 + k * 0.19, 1.02, 0.70), (0.13, 0.24, 0.12),
           (k + 2) % len(M_PRODUCT_COLORS))
mp.build()

# counter / register near the entrance
box("Int_Counter", (-0.58, 3.00, 0.82), (1.62, 0.62, 0.92), M_WOOD_LIGHT,
    bevel=0.03, coll=INTERIOR, outline=False)
box("Int_Counter_Top", (-0.58, 2.99, 1.29), (1.72, 0.72, 0.06),
    M_SHELF, bevel=0.015, coll=INTERIOR, outline=False)
box("Int_Register", (-0.28, 2.94, 1.48), (0.38, 0.30, 0.31), M_METAL_LIGHT,
    bevel=0.02, coll=INTERIOR, outline=False)
box("Int_Register_Screen", (-0.28, 2.785, 1.53), (0.28, 0.012, 0.20),
    emit_mat("Register_Glow", hexc("#9fe4dc"), 0.9),
    coll=INTERIOR, outline=False)
for i, x in enumerate([-1.15, -0.72, -0.32]):
    box(f"Counter_Item_{i}", (x, 3.00, 1.37), (0.18, 0.20, 0.12),
        M_PRODUCT_COLORS[(i * 2 + 1) % len(M_PRODUCT_COLORS)],
        coll=INTERIOR, outline=False)
cyl("Counter_Coffee", (-1.16, 2.94, 1.52), 0.09, 0.18, M_WHITE,
    verts=16, coll=INTERIOR, outline=False)

# interior hanging menus
box("HangMenu_1", (-2.10, 1.30, 2.11), (0.92, 0.035, 0.31),
    emit_mat("HangMenu_White", hexc("#f1e9d7"), 0.75), bevel=0.015,
    coll=INTERIOR, outline=False)
text_obj("HangMenu_1_Text", "おでん  100円", (-2.10, 1.278, 2.11), 0.095,
         M_SIGNINK, rot=(math.radians(90), 0, 0), extrude=0.002,
         coll=DETAIL, font=FONT_BOLD)
box("HangMenu_2", (-3.72, 1.30, 2.11), (0.92, 0.035, 0.31),
    emit_mat("HangMenu_Red", hexc("#d4534d"), 0.7), bevel=0.015,
    coll=INTERIOR, outline=False)
text_obj("HangMenu_2_Text", "HOT COFFEE", (-3.72, 1.278, 2.11), 0.09,
         emit_mat("HangMenu_Text_W", hexc("#f6eddc"), 0.8),
         rot=(math.radians(90), 0, 0), extrude=0.002,
         coll=DETAIL, font=FONT_BOLD)
for i, x in enumerate([-2.10, -3.72]):
    wire(f"HangMenu_Wire_{i}", [(x, 1.30, 2.27), (x, 1.30, 2.45)],
         0.007, M_DARK, INTERIOR, False)

# small floor poster / basket stack
box("Int_Basket_Stack", (-1.62, 1.34, 0.54), (0.52, 0.42, 0.34),
    M_RED, bevel=0.02, coll=INTERIOR, outline=False)
for i in range(2):
    box(f"Int_Basket_Rim_{i}", (-1.62, 1.34, 0.64 + i * 0.14),
        (0.54, 0.44, 0.03), M_DARK, coll=INTERIOR, outline=False)

# bright rear wall glow panel behind the shelf stock
box("Int_RearGlow", (SCX, 4.82, 1.42), (5.2, 0.02, 2.05),
    emit_mat("RearGlow_Warm", hexc("#ffd99d"), 0.55),
    coll=INTERIOR, outline=False)
box("Int_RearGlow_Base", (SCX, 4.80, 0.44), (5.2, 0.03, 0.16),
    emit_mat("RearGlow_Base_Mat", hexc("#ffc47b"), 0.4),
    coll=INTERIOR, outline=False)
# wall band with small price posters
box("Int_BackBand", (SCX, 4.76, 2.15), (5.1, 0.03, 0.20),
    toon_mat("Int_GreenBand", hexc("#3b7c62"), emit=0.15),
    coll=INTERIOR, outline=False)
for i in range(5):
    box(f"Int_ShelfTag_{i}", (-4.4 + i * 0.94, 4.73, 2.15),
        (0.52, 0.02, 0.11), emit_mat(f"ShelfTag_{i}", hexc("#f3e6bd"),
                                     0.55), coll=INTERIOR, outline=False)

# front display shelf, immediately behind the window
frontshelf = Batch("Int_FrontShelf", [M_SHELF, M_METAL], INTERIOR, False)
frontshelf.box((-3.35, 1.19, 0.61), (2.65, 0.13, 0.72), 1)
for lev in range(2):
    frontshelf.box((-3.35, 1.09, 0.38 + lev * 0.32),
                   (2.70, 0.50, 0.035), 0)
frontshelf.build()
frontprod = Batch("Int_FrontProducts", M_PRODUCT_COLORS, INTERIOR, False)
fp = random.Random(771)
for lev in range(2):
    z = 0.42 + lev * 0.32
    for k in range(16):
        x = -4.55 + k * 0.15
        frontprod.box((x, 0.91, z + 0.08),
                      (0.10, 0.14, fp.uniform(0.10, 0.18)),
                      fp.randrange(len(M_PRODUCT_COLORS)))
frontprod.build()
# magazine rack right next to the door
box("Int_FrontMag", (-2.20, 1.12, 0.72), (0.92, 0.12, 0.48), M_METAL,
    coll=INTERIOR, outline=False)
for k in range(4):
    box(f"Int_FrontMag_{k}", (-2.48 + k * 0.18, 0.98, 0.82),
        (0.15, 0.28, 0.14),
        M_PRODUCT_COLORS[(k + 3) % len(M_PRODUCT_COLORS)],
        coll=INTERIOR, outline=False)

# right-side open cooler, glows through the side window
box("Int_SideCooler", (0.02, 1.65, 1.24), (0.55, 1.45, 1.95),
    M_METAL_LIGHT, bevel=0.02, coll=INTERIOR, outline=False)
box("Int_SideCooler_Glow", (0.305, 1.65, 1.44), (0.02, 1.20, 1.45),
    emit_mat("SideCooler_Glow", hexc("#d9f2ea"), 0.75),
    coll=INTERIOR, outline=False)
for i in range(3):
    fy = 1.12 + i * 0.42
    for k in range(3):
        box(f"Int_SideCooler_Drink_{i}_{k}",
            (0.327, fy - 0.10 + k * 0.12, 1.10 + (k % 2) * 0.30),
            (0.025, 0.055, 0.14),
            M_PRODUCT_COLORS[(i * 3 + k) % len(M_PRODUCT_COLORS)],
            coll=INTERIOR, outline=False)
    box(f"Int_SideCooler_Tag_{i}", (0.322, fy, 1.95), (0.015, 0.34, 0.08),
        emit_mat(f"SideCooler_Tag_{i}", hexc("#f7f0da"), 0.5),
        coll=INTERIOR, outline=False)

# second small counter / register to catch the eye near the door
box("Int_Counter2", (-0.10, 1.55, 0.82), (1.15, 0.52, 0.88),
    M_WOOD_LIGHT, bevel=0.02, coll=INTERIOR, outline=False)
box("Int_Counter2_Top", (-0.10, 1.55, 1.27), (1.24, 0.60, 0.055),
    M_SHELF, bevel=0.015, coll=INTERIOR, outline=False)
box("Int_Register2", (0.18, 1.55, 1.44), (0.30, 0.26, 0.26),
    M_METAL_LIGHT, bevel=0.02, coll=INTERIOR, outline=False)
box("Int_Register2_Screen", (0.18, 1.41, 1.48), (0.22, 0.012, 0.16),
    emit_mat("Register2_Glow", hexc("#8fe7dc"), 1.0),
    coll=INTERIOR, outline=False)
box("Int_Basket2", (-0.65, 1.50, 1.35), (0.42, 0.34, 0.14),
    M_RED, coll=INTERIOR, outline=False)

# entrance interior warm curtain / banner
box("Int_EntranceBanner", (-0.85, 0.72, 2.20), (1.55, 0.03, 0.22),
    emit_mat("EntranceBanner_Mat", hexc("#f0b45d"), 0.45),
    coll=INTERIOR, outline=False)
text_obj("Int_EntranceBanner_Text", "いらっしゃいませ", (-0.85, 0.70, 2.20),
         0.085, M_SIGNINK, rot=(math.radians(90), 0, 0), extrude=0.002,
         coll=DETAIL, font=FONT_BOLD)

print("BUILD: exterior props")

# ----------------------------------------------------------------------------
# Vending machines, bicycle, bins, street furniture
# ----------------------------------------------------------------------------
def vending_machine(name, x, y, body_mat, accent_mat, label, label_col):
    """Faces +X (toward the side street/camera)."""
    z0 = 0.19
    h = 1.94
    w = 0.86       # along y
    d = 0.56       # along x
    cx = x
    box(f"{name}_Body", (cx, y, z0 + h / 2), (d, w, h), body_mat,
        bevel=0.035, coll=PROPS, outline=True)
    box(f"{name}_Top", (cx, y, z0 + h + 0.02), (d + 0.04, w + 0.04, 0.09),
        accent_mat, bevel=0.02, coll=PROPS, outline=True)
    # dark glass display field
    box(f"{name}_Display", (cx + d / 2 + 0.01, y + 0.02, z0 + 1.30),
        (0.022, 0.74, 0.92), M_DARK, coll=PROPS, outline=True)
    box(f"{name}_DisplayGlow", (cx + d / 2 + 0.026, y + 0.02, z0 + 1.30),
        (0.014, 0.68, 0.84),
        emit_mat(f"{name}_Glow", hexc("#e9f4f1"), 0.38),
        coll=PROPS, outline=False)
    # product rows
    vp = random.Random(hash(name) & 0xffff)
    for row in range(3):
        for col in range(4):
            colr = M_PRODUCT_COLORS[vp.randrange(len(M_PRODUCT_COLORS))]
            box(f"{name}_Product_{row}_{col}",
                (cx + d / 2 + 0.038, y - 0.27 + col * 0.18,
                 z0 + 0.98 + row * 0.24),
                (0.018, 0.14, 0.17), colr, coll=PROPS, outline=False)
            box(f"{name}_Price_{row}_{col}",
                (cx + d / 2 + 0.039, y - 0.27 + col * 0.18,
                 z0 + 0.875 + row * 0.24),
                (0.010, 0.14, 0.035),
                emit_mat("Vending_Price", hexc("#fff1b8"), 0.6),
                coll=PROPS, outline=False)
    # lower lit panel + brand
    box(f"{name}_LowerPanel", (cx + d / 2 + 0.02, y, z0 + 0.55),
        (0.018, 0.74, 0.42), accent_mat, coll=PROPS, outline=False)
    text_obj(f"{name}_Brand", label,
             (cx + d / 2 + 0.034, y, z0 + 0.58), 0.11, label_col,
             rot=(math.radians(90), 0, math.radians(90)), extrude=0.003,
             coll=DETAIL, font=FONT_BOLD)
    # coin slot / dispenser
    box(f"{name}_Coin", (cx + d / 2 + 0.03, y + 0.30, z0 + 0.76),
        (0.018, 0.10, 0.22), M_METAL_LIGHT, coll=PROPS, outline=False)
    box(f"{name}_Slot", (cx + d / 2 + 0.03, y - 0.10, z0 + 0.25),
        (0.022, 0.46, 0.14), M_BLACK, coll=PROPS, outline=False)
    box(f"{name}_Base", (cx, y, z0 + 0.06), (d + 0.02, w + 0.02, 0.12),
        M_DARK, coll=PROPS, outline=False)
    # halo point light
    pl = bpy.data.lights.new(f"{name}_Light", "POINT")
    pl.energy = 55
    pl.color = (0.68, 0.87, 1.0)
    pl.shadow_soft_size = 0.35
    lo = bpy.data.objects.new(f"{name}_Light", pl)
    LIGHTS.objects.link(lo)
    lo.location = (cx + 0.75, y, z0 + 1.15)


vending_machine("Vending_SORA", 0.92, 3.02, M_RED,
                toon_mat("Vending_RedBody", hexc("#c73b3e"), emit=0.14),
                "SORA", emit_mat("Vending_SORA_Text", hexc("#fff4e6"), 0.8))
vending_machine("Vending_Coffee", 0.92, 4.02, M_TEAL,
                toon_mat("Vending_BlueBody", hexc("#2e7aa2"), emit=0.14),
                "COFFEE", emit_mat("Vending_Coffee_Text", hexc("#fff4e6"), 0.8))

# bins between / beside vending machines
for i, (bx, by, bmat, lidmat) in enumerate([
        (1.34, 2.42, M_TEAL, M_DARK),
        (1.28, 4.78, toon_mat("Bin_Blue", hexc("#386d8d"), emit=0.12),
         M_DARK)]):
    cyl(f"Bin_{i}", (bx, by, 0.61), 0.24, 0.82, bmat, verts=20,
        coll=PROPS, outline=True)
    cyl(f"Bin_Lid_{i}", (bx, by, 1.035), 0.26, 0.09, lidmat, verts=20,
        coll=PROPS, outline=True)
    box(f"Bin_Label_{i}", (bx + 0.235, by, 0.66), (0.02, 0.20, 0.22),
        emit_mat(f"Bin_Label_Mat_{i}", hexc("#e4e6d8"), 0.4),
        coll=PROPS, outline=False)
    text_obj(f"Bin_Text_{i}", "空き缶", (bx + 0.247, by, 0.66), 0.052,
             M_SIGNINK, rot=(math.radians(90), 0, math.radians(90)),
             extrude=0.002, coll=DETAIL, font=FONT_MED)

# recycling crate stack
box("Crate_A", (1.78, 6.22, 0.35), (0.48, 0.38, 0.33),
    toon_mat("Crate_Blue", hexc("#326b85"), emit=0.1), bevel=0.015,
    coll=PROPS, outline=True)
box("Crate_B", (1.78, 6.22, 0.66), (0.44, 0.34, 0.30),
    toon_mat("Crate_Yellow", hexc("#b59a4d"), emit=0.1), bevel=0.015,
    coll=PROPS, outline=True)

# umbrella parasol in front of the shop
def parasol(name, loc, r, z_top, rot_z=0.0):
    cx, cy, cz = loc
    verts = [(cx, cy, cz + z_top)]
    n = 10
    for i in range(n):
        a = 2 * math.pi * i / n + rot_z
        verts.append((cx + math.cos(a) * r, cy + math.sin(a) * r, cz))
    for i in range(n):
        verts.append((cx + math.cos(2 * math.pi * i / n + rot_z) * r * 0.58,
                      cy + math.sin(2 * math.pi * i / n + rot_z) * r * 0.58,
                      cz + z_top * 0.42))
    faces = []
    fmat = []
    for i in range(n):
        i2 = (i + 1) % n
        faces.append((0, 1 + i, 1 + i2))
        fmat.append(i % 2)
        faces.append((1 + i, 1 + n + i, 1 + n + i2, 1 + i2))
        fmat.append(i % 2)
    m1 = toon_mat("Parasol_Cream", hexc("#f0d98f"), emit=0.26)
    m2 = toon_mat("Parasol_Orange", hexc("#cf8449"), emit=0.26)
    mesh_obj(name + "_Canopy", verts, faces, None, PROPS, True,
             material_slots=[m1, m2], face_mats=fmat)
    for i in range(n):
        a = 2 * math.pi * i / n + rot_z
        wire(f"{name}_Rib_{i}",
             [(cx, cy, cz + z_top + 0.02),
              (cx + math.cos(a) * r * 0.97,
               cy + math.sin(a) * r * 0.97, cz + 0.01)],
             0.008, M_DARK, PROPS, False)
    cyl(name + "_Pole", (cx, cy, cz - z_top * 0.85), 0.024,
        z_top * 0.95, M_METAL_LIGHT, verts=10, coll=PROPS, outline=True)
    sphere(name + "_Finial", (cx, cy, cz + z_top + 0.045), 0.045, M_ORANGE,
           seg=10, rings=7, coll=PROPS, outline=True)


parasol("Front_Parasol", (-3.93, -0.62, 0.19), 0.62, 1.28,
        rot_z=math.radians(8))

# umbrella stand beside the door
cyl("Umbrella_Stand", (-0.04, 0.07, 0.48), 0.22, 0.58, M_METAL,
    verts=16, coll=PROPS, outline=True)
for i, (ux, uy, tilt) in enumerate([(-0.09, 0.05, 0.10),
                                     (0.02, 0.02, -0.13)]):
    cyl(f"Umbrella_{i}", (ux, uy, 0.97), 0.035, 0.92,
        toon_mat(f"Umbrella_Mat_{i}", hexc("#d8d4c6") if i else
                 hexc("#d6b85c"), emit=0.14), verts=12,
        rot=(tilt, 0.05, 0), coll=PROPS, outline=True)
    cone(f"Umbrella_Tip_{i}", (ux, uy, 1.47), 0.03, 0.0, 0.14,
         M_METAL_LIGHT, verts=10, coll=PROPS, outline=False)

# A-frame coffee sign
box("AFrame_Board", (-2.70, -0.68, 0.76), (0.72, 0.08, 1.02),
    emit_mat("AFrame_Cream", hexc("#eee3c4"), 0.35), bevel=0.015,
    rot=(math.radians(-9), 0, 0), coll=PROPS, outline=True)
box("AFrame_Header", (-2.70, -0.714, 1.13), (0.60, 0.014, 0.19),
    M_RED, rot=(math.radians(-9), 0, 0), coll=PROPS, outline=False)
text_obj("AFrame_Header_Text", "HOT COFFEE", (-2.70, -0.726, 1.13), 0.085,
         emit_mat("AFrame_White", hexc("#fff6e1"), 0.6),
         rot=(math.radians(81), 0, 0), extrude=0.002, coll=DETAIL,
         font=FONT_BOLD)
text_obj("AFrame_Price", "¥100", (-2.70, -0.726, 0.88), 0.20, M_SIGNINK,
         rot=(math.radians(81), 0, 0), extrude=0.004, coll=DETAIL,
         font=FONT_BOLD)
text_obj("AFrame_Small", "あったか〜い", (-2.70, -0.726, 0.64), 0.065,
         M_SIGNINK, rot=(math.radians(81), 0, 0), extrude=0.002,
         coll=DETAIL, font=FONT_MED)
# a coffee can on the sign
cyl("AFrame_Can", (-2.42, -0.78, 0.55), 0.085, 0.20, M_WARM_DEEP,
    verts=16, coll=PROPS, outline=True)
cyl("AFrame_Can_Top", (-2.42, -0.78, 0.655), 0.087, 0.018, M_METAL_LIGHT,
    verts=16, coll=PROPS, outline=False)
wire("AFrame_Can_Steam", [(-2.42, -0.78, 0.70), (-2.47, -0.80, 0.85),
                          (-2.39, -0.82, 0.98)], 0.012,
     emit_mat("Steam_Mat", hexc("#f2ead5"), 0.35, alpha=0.45),
     PROPS, False)

# bicycle against the side wall
def bicycle(name, bx, by, scale=1.0):
    z_wheel = 0.43
    wheel_r = 0.36 * scale
    for i, wy in enumerate([by - 0.53 * scale, by + 0.53 * scale]):
        torus(f"{name}_Wheel_{i}", (bx, wy, z_wheel), wheel_r,
              0.025 * scale, M_BLACK, rot=(0, math.radians(90), 0),
              seg=28, mseg=6, coll=PROPS, outline=True)
        cyl(f"{name}_Hub_{i}", (bx, wy, z_wheel), 0.045, 0.05,
            M_METAL_LIGHT, verts=12, rot=(0, math.radians(90), 0),
            coll=PROPS, outline=False)
        for k in range(6):
            a = k * math.pi / 3
            box(f"{name}_Spoke_{i}_{k}",
                (bx, wy, z_wheel),
                (0.008, wheel_r * 2, 0.008),
                M_METAL_LIGHT, rot=(a, 0, 0),
                coll=PROPS, outline=False)
    # frame
    pts = [(bx, by - 0.53 * scale, z_wheel),
           (bx, by - 0.26 * scale, 0.78 * scale + 0.20),
           (bx, by + 0.25 * scale, 0.78 * scale + 0.20),
           (bx, by + 0.53 * scale, z_wheel)]
    for i in range(len(pts) - 1):
        p0, p1 = pts[i], pts[i + 1]
        mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2,
               (p0[2] + p1[2]) / 2)
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        dz = p1[2] - p0[2]
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        rotx = math.atan2(dy, dz)
        cyl(f"{name}_Frame_{i}", mid, 0.028, length, M_METAL_LIGHT,
            verts=10, rot=(rotx, 0, 0), coll=PROPS, outline=True)
    cyl(f"{name}_SeatPost", (bx, by + 0.20, 0.72), 0.022, 0.42,
        M_METAL_LIGHT, rot=(0.16, 0, 0), coll=PROPS, outline=False)
    box(f"{name}_Seat", (bx, by + 0.18, 0.95), (0.16, 0.30, 0.06),
        M_BLACK, bevel=0.02, coll=PROPS, outline=True)
    wire(f"{name}_Handlebar", [(bx, by + 0.53, 0.84),
                               (bx, by + 0.58, 0.98),
                               (bx, by + 0.45, 1.02)],
         0.022, M_METAL_LIGHT, PROPS, True)
    # front basket
    box(f"{name}_Basket", (bx, by + 0.60, 0.83), (0.34, 0.30, 0.24),
        M_METAL, coll=PROPS, outline=True)
    for k in range(3):
        box(f"{name}_BasketGrid_{k}", (bx, by + 0.60, 0.73 + k * 0.1),
            (0.35, 0.31, 0.012), M_METAL_LIGHT, coll=PROPS, outline=False)


bicycle("Side_Bike", 1.14, 5.46, 0.95)

# cork notice board on the side wall (visible above the bicycle)
box("Notice_Board_Back", (0.60, 4.88, 1.58), (0.06, 0.92, 0.94),
    M_WOOD, bevel=0.012, coll=PROPS, outline=True)
box("Notice_Board_Cork", (0.635, 4.88, 1.58), (0.018, 0.82, 0.84),
    toon_mat("Cork_Mat", hexc("#b88b5f"), emit=0.12),
    coll=PROPS, outline=False)
for i, (py, pz, w, h, col) in enumerate([
        (4.67, 1.71, 0.24, 0.30, "#f4ecd3"),
        (4.94, 1.66, 0.26, 0.26, "#e9d6a9"),
        (5.08, 1.43, 0.20, 0.22, "#d9e4da")]):
    box(f"Notice_Paper_{i}", (0.649, py, pz), (0.01, w, h),
        emit_mat(f"Notice_Paper_Mat_{i}", hexc(col), 0.35),
        coll=PROPS, outline=False)
text_obj("Notice_Header", "お知らせ", (0.655, 4.88, 2.10), 0.065,
         M_SIGNINK, rot=(math.radians(90), 0, math.radians(90)),
         extrude=0.002, coll=DETAIL, font=FONT_BOLD)
text_obj("Notice_Paper_Text", "SALE\n10% OFF", (0.655, 4.67, 1.71), 0.037,
         emit_mat("Notice_Text_Mat", hexc("#a64237"), 0.4),
         rot=(math.radians(90), 0, math.radians(90)), extrude=0.001,
         coll=DETAIL, font=FONT_MED, line_spacing=1.1)

# newspaper / vending box on the sidewalk near the neighbour shop
box("NewsBox", (-4.62, -1.25, 0.58), (0.46, 0.40, 0.78),
    toon_mat("NewsBox_Green", hexc("#3d6b60"), emit=0.12),
    bevel=0.025, coll=PROPS, outline=True)
box("NewsBox_Window", (-4.62, -1.455, 0.72), (0.34, 0.015, 0.25),
    emit_mat("NewsBox_Window_Mat", hexc("#d9dfcf"), 0.3),
    coll=PROPS, outline=False)
text_obj("NewsBox_Text", "新聞", (-4.62, -1.465, 0.72), 0.075, M_SIGNINK,
         rot=(math.radians(90), 0, 0), extrude=0.002, coll=DETAIL,
         font=FONT_BOLD)
box("NewsBox_Slot", (-4.62, -1.46, 0.40), (0.28, 0.02, 0.06), M_DARK,
    coll=PROPS, outline=False)

# small ashtray / sand urn by the entrance
cyl("Ashtray", (-0.16, -0.58, 0.27), 0.13, 0.16, M_METAL_LIGHT,
    verts=16, coll=PROPS, outline=True)
cyl("Ashtray_Sand", (-0.16, -0.58, 0.345), 0.105, 0.025,
    toon_mat("Sand_Mat", hexc("#c7b68d"), emit=0.08), verts=16,
    coll=PROPS, outline=False)

# guard rails along the curb
def railing(name, start, end, z=0.19, height=0.78, posts=4):
    sx, sy = start
    ex, ey = end
    for i in range(posts):
        t = i / (posts - 1)
        px = sx + (ex - sx) * t
        py = sy + (ey - sy) * t
        box(f"{name}_Post_{i}", (px, py, z + height / 2),
            (0.055, 0.055, height), M_DARK, coll=PROPS, outline=True)
    for k, zz in enumerate([z + 0.28, z + 0.68]):
        cx = (sx + ex) / 2
        cy = (sy + ey) / 2
        length = math.hypot(ex - sx, ey - sy)
        ang = math.atan2(ey - sy, ex - sx)
        box(f"{name}_Rail_{k}", (cx, cy, zz),
            (length, 0.045, 0.045), M_DARK,
            rot=(0, 0, ang), coll=PROPS, outline=True)


railing("Rail_Front", (-7.25, -1.64), (-5.05, -1.64), posts=5)
railing("Rail_Front2", (0.05, -1.64), (1.15, -1.64), posts=3)
railing("Rail_Side", (2.38, 0.10), (2.38, 1.28), posts=3, height=0.74)
# short black bollards
for i, (px, py) in enumerate([(1.45, -1.55), (2.35, -1.20),
                               (2.38, 0.70)]):
    cyl(f"Bollard_{i}", (px, py, 0.50), 0.055, 0.66, M_DARK, verts=12,
        coll=PROPS, outline=True)
    cyl(f"Bollard_Band_{i}", (px, py, 0.62), 0.06, 0.08, M_TACTILE,
        verts=12, coll=PROPS, outline=False)

# traffic cone near the corner
for i, (cx, cy) in enumerate([(0.96, -1.35), (3.05, 1.00)]):
    cone(f"TrafficCone_{i}", (cx, cy, 0.37), 0.22, 0.055, 0.40,
         toon_mat("Cone_Orange", hexc("#df6b35"), emit=0.18), verts=16,
         coll=PROPS, outline=True)
    box(f"Cone_Base_{i}", (cx, cy, 0.195), (0.42, 0.42, 0.035), M_DARK,
        bevel=0.01, coll=PROPS, outline=True)
    cyl(f"Cone_Band_{i}", (cx, cy, 0.42), 0.150, 0.075, M_WHITE,
        verts=16, coll=PROPS, outline=False)

# potted plants by the storefront
for i, (px, py, pr) in enumerate([(-4.97, -0.30, 0.22),
                                   (-0.10, -0.25, 0.16),
                                   (1.42, 2.10, 0.20)]):
    cyl(f"Shop_Pot_{i}", (px, py, 0.36), pr, 0.30, M_WOOD_LIGHT,
        verts=16, coll=PROPS, outline=True)
    ico(f"Shop_Plant_{i}", (px, py, 0.57 + pr * 0.55), pr * 1.25,
        M_TREE if i % 2 == 0 else M_TREE_LIGHT, subdiv=2,
        scale=(1, 1, 0.8), coll=VEG, outline=True)

# small tree in front of the neighbour shop
cyl("Tree_Trunk", (-6.60, -0.48, 0.72), 0.11, 1.35, M_WOOD,
    verts=12, coll=VEG, outline=True)
for i, (dx, dy, dz, r) in enumerate([(0.0, 0.0, 0.0, 0.62),
                                     (-0.38, 0.12, -0.18, 0.42),
                                     (0.34, -0.08, 0.02, 0.46),
                                     (0.02, 0.28, -0.20, 0.40)]):
    ico(f"Tree_Canopy_{i}", (-6.60 + dx, -0.48 + dy, 1.72 + dz), r,
        M_TREE if i % 2 == 0 else M_TREE_LIGHT, subdiv=2,
        scale=(1.0, 0.92, 0.82), coll=VEG, outline=True)
# low planter box
box("Neighbour_Planter", (-6.55, -1.30, 0.33), (1.55, 0.42, 0.36),
    M_WOOD, bevel=0.02, coll=PROPS, outline=True)
for i in range(5):
    ico(f"Planter_Bush_{i}", (-7.15 + i * 0.31, -1.30, 0.57),
        0.20, M_TREE_LIGHT, subdiv=1, scale=(1, 0.8, 0.9),
        coll=VEG, outline=False)

# curb-side signboard for the neighbour shop
box("Neighbour_Aboard", (-6.93, -1.42, 0.82), (0.46, 0.07, 0.92),
    M_WOOD_LIGHT, bevel=0.015, rot=(math.radians(-7), 0, 0),
    coll=PROPS, outline=True)
text_obj("Neighbour_Aboard_Text", "小料理\nさくら", (-6.93, -1.47, 0.86),
         0.12, emit_mat("Aboard_Text", hexc("#f1ddb0"), 0.45),
         rot=(math.radians(83), 0, 0), extrude=0.003, coll=DETAIL,
         font=FONT_BOLD)

print("BUILD: street infrastructure")

# ----------------------------------------------------------------------------
# Utility poles & overhead wires
# ----------------------------------------------------------------------------
M_WIRE = toon_mat("Wire_Black", hexc("#070a0f"), emit=0.01)
M_INSULATOR = toon_mat("Insulator_Cream", hexc("#d5cbb5"), emit=0.15)


def utility_pole(name, x, y, height=7.4, radius=0.15, crossarm=True,
                 transformer=False):
    cyl(name + "_Pole", (x, y, height / 2), radius, height, M_POLE,
        verts=18, coll=PROPS, outline=True)
    for k in range(6):
        cyl(f"{name}_Foot_{k}", (x, y, 0.18 + k * 0.02), radius * 1.18,
            0.025, M_DARK, verts=18, coll=PROPS, outline=False)
    # pole bands
    for k in range(3):
        cyl(f"{name}_Band_{k}", (x, y, 2.3 + k * 0.42), radius * 1.03,
            0.035, M_TACTILE if k == 1 else M_METAL,
            verts=18, coll=PROPS, outline=False)
    if crossarm:
        # long crossarm along X
        box(name + "_ArmX", (x, y, height - 0.55),
            (2.25, 0.13, 0.14), M_METAL, coll=PROPS, outline=True)
        box(name + "_ArmX2", (x, y, height - 1.05),
            (1.55, 0.11, 0.11), M_METAL, coll=PROPS, outline=True)
        for i in range(4):
            ix = x - 0.90 + i * 0.60
            cyl(f"{name}_InsX_{i}", (ix, y, height - 0.44), 0.055, 0.16,
                M_INSULATOR, verts=12, coll=PROPS, outline=True)
        # second arm along Y
        box(name + "_ArmY", (x, y, height - 0.85),
            (0.12, 1.85, 0.12), M_METAL, coll=PROPS, outline=True)
        for i in range(3):
            iy = y - 0.68 + i * 0.68
            cyl(f"{name}_InsY_{i}", (x, iy, height - 0.74), 0.055, 0.16,
                M_INSULATOR, verts=12, coll=PROPS, outline=True)
    if transformer:
        cyl(name + "_Transformer", (x - 0.34, y, height - 1.65),
            0.28, 0.80, M_METAL_LIGHT, verts=20, coll=PROPS, outline=True)
        cyl(name + "_TransformerTop", (x - 0.34, y, height - 1.22),
            0.20, 0.08, M_METAL, verts=16, coll=PROPS, outline=True)
        for k in range(3):
            cyl(f"{name}_Trans_Rib_{k}", (x - 0.34, y,
                                          height - 1.92 + k * 0.25),
                0.31, 0.025, M_METAL, verts=20, coll=PROPS,
                outline=False)
    # step bolts
    for k in range(4):
        box(f"{name}_Step_{k}", (x + radius * 0.8, y, 2.9 + k * 0.62),
            (0.33, 0.035, 0.035), M_METAL, coll=PROPS, outline=False)
    return (x, y, height - 0.45)


P_CORNER = utility_pole("Pole_Corner", 2.42, -1.42, 7.8, 0.14, True, True)
P_LEFT = utility_pole("Pole_Left", -7.02, -1.02, 7.1, 0.14, True, False)
P_RIGHT = utility_pole("Pole_Right", 7.08, -1.10, 7.3, 0.13, True, False)
P_BACK = utility_pole("Pole_Back", 2.04, 6.76, 7.0, 0.13, True, False)

# overhead wires: front street, side street, crossing diagonals
for k in range(4):
    zoff = 0.0 - k * 0.23
    yoff = -0.10 + k * 0.07
    pts = catenary((2.42 - 0.9, -1.42 + yoff, 7.35 + zoff),
                   (-7.02, -1.02 + yoff, 6.65 + zoff), sag=0.55, n=9)
    wire(f"Wire_Front_{k}", pts, 0.019, M_WIRE, PROPS, False)
for k in range(4):
    zoff = -k * 0.24
    pts = catenary((2.42 + 0.9, -1.42, 7.35 + zoff),
                   (7.08, -1.10, 6.85 + zoff), sag=0.38, n=8)
    wire(f"Wire_Right_{k}", pts, 0.018, M_WIRE, PROPS, False)
for k in range(3):
    xoff = k * 0.18
    pts = catenary((2.42 + xoff, 6.76, 6.65 - k * 0.22),
                   (2.42 + xoff, -1.42, 6.75 - k * 0.22), sag=0.52, n=9)
    wire(f"Wire_Side_{k}", pts, 0.017, M_WIRE, PROPS, False)
# dramatic diagonals over the shop
for k in range(2):
    pts = catenary((-7.02 + k * 0.45, -1.02, 6.85 - k * 0.25),
                   (2.04, 6.76, 6.55 - k * 0.23), sag=1.15, n=11)
    wire(f"Wire_Diag_{k}", pts, 0.017, M_WIRE, PROPS, False)
# service drops to the building
for k, (ex, ey, ez) in enumerate([(-4.15, 0.30, 5.0),
                                  (-0.55, 0.30, 5.0)]):
    pts = catenary((2.42, -1.42, 6.55), (ex, ey, ez), sag=0.28, n=7)
    wire(f"ServiceDrop_{k}", pts, 0.016, M_WIRE, PROPS, False)
# little cable loops on the pole
for k in range(3):
    torus(f"CableLoop_{k}", (2.12, -1.41, 5.92 - k * 0.22),
          0.28 + k * 0.05, 0.02, M_WIRE, rot=(0, math.radians(90), 0),
          seg=24, mseg=6, coll=PROPS, outline=False)

# ----------------------------------------------------------------------------
# Street lamps
# ----------------------------------------------------------------------------
def street_lamp(name, x, y, height, arm_dir=-1, warm=False):
    cyl(name + "_Post", (x, y, height / 2), 0.10, height, M_METAL,
        verts=16, coll=PROPS, outline=True)
    # curved arm via bezier wire
    tipx = x + arm_dir * 1.45
    pts = [(x, y, height - 0.10), (x + arm_dir * 0.55, y, height + 0.26),
           (tipx, y, height + 0.14)]
    wire(name + "_Arm", pts, 0.055, M_METAL, PROPS, True)
    box(name + "_Lamp", (tipx, y, height + 0.04), (0.82, 0.36, 0.12),
        M_DARK, bevel=0.03, coll=PROPS, outline=True)
    box(name + "_LampGlow", (tipx, y, height - 0.035), (0.70, 0.28, 0.02),
        emit_mat(name + "_LampMat",
                 hexc("#ffd89c") if warm else hexc("#b7e6ff"), 6.0),
        coll=PROPS, outline=False)
    sphere(name + "_Bulb", (tipx, y, height - 0.065), 0.10,
           emit_mat(name + "_BulbMat",
                    hexc("#ffe2ae") if warm else hexc("#b6e8ff"), 8.0),
           seg=12, rings=8, coll=PROPS, outline=False)
    pl = bpy.data.lights.new(name + "_Point", "POINT")
    pl.energy = 1450 if not warm else 550
    pl.color = (1.0, 0.80, 0.55) if warm else (0.62, 0.84, 1.0)
    pl.shadow_soft_size = 0.55
    lo = bpy.data.objects.new(name + "_Point", pl)
    LIGHTS.objects.link(lo)
    lo.location = (tipx, y, height - 0.25)
    return tipx, y, height - 0.25


street_lamp("StreetLamp_Right", 6.80, 2.55, 6.15, arm_dir=-1, warm=False)

# ----------------------------------------------------------------------------
# Street signs on the corner pole
# ----------------------------------------------------------------------------
# green destination sign, mounted on the far-right utility pole
sign_z = 4.58
box("StreetName_BoardWhite", (6.536, -1.606, sign_z), (1.48, 0.055, 0.54),
    M_WHITE, bevel=0.02, rot=(0, 0, math.radians(45)), coll=PROPS,
    outline=True)
box("StreetName_BoardGreen", (6.553, -1.623, sign_z), (1.38, 0.035, 0.46),
    M_GREEN_DARK, bevel=0.01, rot=(0, 0, math.radians(45)), coll=PROPS,
    outline=True)
text_obj("StreetName_JP", "坂下二丁目", (6.582, -1.652, sign_z + 0.06),
         0.145, M_WHITE, rot=(math.radians(90), 0, math.radians(45)),
         extrude=0.003, coll=DETAIL, font=FONT_BOLD)
text_obj("StreetName_EN", "SAKAZAKA 2", (6.582, -1.652, sign_z - 0.13),
         0.052, M_WHITE, rot=(math.radians(90), 0, math.radians(45)),
         extrude=0.002, coll=DETAIL, font=FONT_MED, spacing=1.1)
box("StreetName_Mount", (6.865, -1.360, sign_z), (0.52, 0.10, 0.09),
    M_METAL, rot=(0, 0, math.radians(45)), coll=PROPS, outline=True)

# convex traffic mirror
mirror_n = Vector((0.60, -0.80, 0.0))
mirror_c = Vector((1.98, -1.61, 3.18))
mirror_rot = (math.radians(90), 0, math.radians(37))
torus("Mirror_Rim", mirror_c, 0.285, 0.055,
      toon_mat("Mirror_Orange", hexc("#d07438"), emit=0.2),
      rot=mirror_rot, seg=28, mseg=8, coll=PROPS, outline=True)
cyl("Mirror_Face", mirror_c, 0.265, 0.045,
    toon_mat("Mirror_Glass", hexc("#7596a3"), emit=0.22),
    verts=28, rot=mirror_rot, coll=PROPS, outline=True)
box("Mirror_Highlight", (mirror_c.x + 0.11, mirror_c.y - 0.14,
                          mirror_c.z + 0.10), (0.12, 0.012, 0.06),
    emit_mat("Mirror_Highlight_Mat", hexc("#dbedf2"), 0.55),
    rot=(0, 0, math.radians(37)), coll=PROPS, outline=False)
box("Mirror_Bracket", (2.30, -1.42, 3.04), (0.12, 0.30, 0.08), M_METAL,
    coll=PROPS, outline=True)

# speed limit 30 + P sign
cyl("SpeedSign_White", (2.43, -1.69, 2.52), 0.27, 0.035, M_WHITE,
    verts=28, rot=mirror_rot, coll=PROPS, outline=True)
torus("SpeedSign_Rim", (2.425, -1.695, 2.52), 0.245, 0.032, M_RED,
      rot=mirror_rot, seg=28, mseg=6, coll=PROPS, outline=True)
text_obj("SpeedSign_30", "30", (2.455, -1.715, 2.52), 0.20, M_SIGNINK,
         rot=(math.radians(90), 0, math.radians(37)), extrude=0.002,
         coll=DETAIL, font=FONT_BOLD)
cyl("PSign_Pole", (3.14, 1.78, 1.36), 0.045, 2.45, M_METAL, verts=12,
    coll=PROPS, outline=True)
box("PSign_Blue", (3.14, 1.78, 2.38), (0.52, 0.05, 0.52),
    toon_mat("PSign_BlueMat", hexc("#2b5b9a"), emit=0.16), bevel=0.025,
    coll=PROPS, outline=True)
text_obj("PSign_Text", "P", (3.14, 1.744, 2.38), 0.33, M_WHITE,
         rot=(math.radians(90), 0, 0), extrude=0.004, coll=DETAIL,
         font=FONT_BOLD)
text_obj("PSign_Small", "PARKING", (3.14, 1.744, 2.12), 0.042, M_WHITE,
         rot=(math.radians(90), 0, 0), extrude=0.002, coll=DETAIL,
         font=FONT_MED)

# parking-meter style sign near the bay
box("ParkSign", (6.52, 2.42, 1.35), (0.38, 0.05, 0.52),
    toon_mat("ParkSign_Mat", hexc("#d4cfb8"), emit=0.15), bevel=0.02,
    coll=PROPS, outline=True)
text_obj("ParkSign_Text", "P\n24h", (6.52, 2.39, 1.38), 0.13, M_SIGNINK,
         rot=(math.radians(90), 0, 0), extrude=0.003, coll=DETAIL,
         font=FONT_BOLD)
cyl("ParkSign_Pole", (6.52, 2.42, 0.72), 0.035, 1.45, M_METAL,
    verts=10, coll=PROPS, outline=True)

# ----------------------------------------------------------------------------
# Kei van in the parking bay
# ----------------------------------------------------------------------------
VAN_X, VAN_Y = 5.06, 3.34
box("Van_Body", (VAN_X, VAN_Y, 0.95), (1.56, 2.30, 1.18), M_VAN,
    bevel=0.11, coll=PROPS, outline=True)
box("Van_Cabin", (VAN_X, VAN_Y - 0.03, 1.72), (1.48, 2.12, 0.54), M_VAN,
    bevel=0.10, coll=PROPS, outline=True)
box("Van_Roof", (VAN_X, VAN_Y, 2.02), (1.52, 2.10, 0.07), M_VAN_DARK,
    bevel=0.02, coll=PROPS, outline=True)
# windshield
box("Van_Windshield", (VAN_X, VAN_Y - 1.145, 1.67), (1.28, 0.035, 0.48),
    principled("Van_Glass", hexc("#263c4b"), 0.08, 0.2, alpha=0.9),
    rot=(math.radians(-7), 0, 0), coll=PROPS, outline=True)
# side windows
for i, yy in enumerate([-0.58, 0.14, 0.86]):
    box(f"Van_SideWin_{i}", (VAN_X + 0.755, VAN_Y + yy, 1.70),
        (0.025, 0.62, 0.46), principled("Van_SideGlass", hexc("#213744"),
                                        0.1, 0.2), coll=PROPS,
        outline=False)
    box(f"Van_SideWin_Frame_{i}", (VAN_X + 0.768, VAN_Y + yy, 1.70),
        (0.015, 0.66, 0.50), M_VAN_DARK, coll=PROPS, outline=True)
# rear window
box("Van_RearWin", (VAN_X, VAN_Y + 1.16, 1.68), (1.02, 0.03, 0.40),
    principled("Van_RearGlass", hexc("#1b2d38"), 0.1, 0.2),
    coll=PROPS, outline=False)
# grille / bumpers
box("Van_FrontBumper", (VAN_X, VAN_Y - 1.19, 0.46), (1.54, 0.13, 0.24),
    M_VAN_DARK, bevel=0.03, coll=PROPS, outline=True)
box("Van_Grille", (VAN_X, VAN_Y - 1.18, 0.90), (1.20, 0.045, 0.30),
    M_METAL, coll=PROPS, outline=False)
for k in range(5):
    box(f"Van_GrilleBar_{k}", (VAN_X, VAN_Y - 1.205, 0.80 + k * 0.06),
        (1.12, 0.012, 0.018), M_DARK, coll=PROPS, outline=False)
# headlights
for i, xx in enumerate([VAN_X - 0.52, VAN_X + 0.52]):
    box(f"Van_Headlight_{i}", (xx, VAN_Y - 1.187, 0.91),
        (0.32, 0.025, 0.20), emit_mat(f"Headlight_Mat_{i}",
                                      hexc("#ffe6b4"), 3.0),
        bevel=0.02, coll=PROPS, outline=False)
    box(f"Van_Headlight_Rim_{i}", (xx, VAN_Y - 1.178, 0.91),
        (0.36, 0.02, 0.24), M_VAN_DARK, coll=PROPS, outline=False)
# taillights
for i, xx in enumerate([VAN_X - 0.58, VAN_X + 0.58]):
    box(f"Van_Taillight_{i}", (xx, VAN_Y + 1.18, 1.00),
        (0.18, 0.02, 0.28), emit_mat(f"Taillight_Mat_{i}",
                                     hexc("#e4574b"), 0.8),
        coll=PROPS, outline=False)
# license plate
box("Van_Plate", (VAN_X, VAN_Y - 1.235, 0.62), (0.48, 0.02, 0.14),
    M_WHITE, coll=PROPS, outline=False)
text_obj("Van_Plate_Text", "さ 1-24", (VAN_X, VAN_Y - 1.247, 0.62),
         0.06, M_SIGNINK, rot=(math.radians(90), 0, 0), extrude=0.002,
         coll=DETAIL, font=FONT_MED)
# wheels
for i, (xx, yy) in enumerate([(VAN_X - 0.77, VAN_Y - 0.71),
                               (VAN_X + 0.77, VAN_Y - 0.71),
                               (VAN_X - 0.77, VAN_Y + 0.74),
                               (VAN_X + 0.77, VAN_Y + 0.74)]):
    cyl(f"Van_Wheel_{i}", (xx, yy, 0.35), 0.31, 0.20, M_BLACK,
        verts=20, rot=(0, math.radians(90), 0), coll=PROPS, outline=True)
    cyl(f"Van_Hub_{i}", (xx + (0.09 if xx > VAN_X else -0.09), yy, 0.35),
        0.16, 0.04, M_METAL_LIGHT, verts=16,
        rot=(0, math.radians(90), 0), coll=PROPS, outline=False)
# side mirrors
for i, xx in enumerate([VAN_X - 0.81, VAN_X + 0.81]):
    box(f"Van_Mirror_{i}", (xx, VAN_Y - 1.00, 1.70), (0.11, 0.16, 0.10),
        M_VAN_DARK, bevel=0.02, coll=PROPS, outline=True)
# roof rack + little boxes
box("Van_RoofRack", (VAN_X, VAN_Y + 0.25, 2.08), (1.22, 1.25, 0.04),
    M_METAL, coll=PROPS, outline=False)
box("Van_RoofBox", (VAN_X, VAN_Y + 0.44, 2.19), (0.62, 0.72, 0.16),
    M_WOOD_LIGHT, bevel=0.02, coll=PROPS, outline=True)
# subtle van reflection plane
ref = puddle("Van_Reflection", VAN_X, VAN_Y - 1.55, 0.92, 0.52, 0.071,
             principled("Van_Reflect_Mat", hexc("#2b3946"), 0.05, 0.6,
                        emission=hexc("#12202c"), emission_strength=0.2),
             seed=77, n=18)

# ----------------------------------------------------------------------------
# Puddles, wet reflections, rain ripples
# ----------------------------------------------------------------------------
M_PUDDLE = principled("Puddle", hexc("#1a2e44"), 0.08, 0.20,
                      emission=hexc("#081726"), emission_strength=0.28)
M_PUDDLE2 = principled("Puddle_Edge", hexc("#2d455b"), 0.16, 0.12)
puddle_specs = [
    (-3.10, -2.45, 1.10, 0.48, 15),
    (-4.50, -3.20, 0.55, 0.26, 22),
    (-0.15, -3.55, 0.85, 0.38, 31),
    (1.95, -2.70, 0.52, 0.30, 42),
    (4.55, -4.25, 1.38, 0.55, 53),
    (6.05, -2.40, 0.80, 0.38, 64),
    (4.62, -0.25, 0.65, 0.30, 73),
    (3.55, 0.45, 0.44, 0.26, 82),
    (6.15, 4.75, 0.85, 0.40, 94),
    (-1.80, 0.55, 0.48, 0.22, 105),
]
for i, (px, py, rx, ry, sd) in enumerate(puddle_specs):
    puddle(f"Puddle_{i}", px, py, rx, ry, 0.076, M_PUDDLE,
           seed=sd, n=18, rot=random.uniform(-0.5, 0.5))
    # faint rim highlight
    puddle(f"PuddleRim_{i}", px, py, rx * 1.03, ry * 1.03, 0.073,
           M_PUDDLE2, seed=sd + 4, n=18, rot=random.uniform(-0.5, 0.5))
# puddle on sidewalk (storefront reflection pool)
puddle("Puddle_Sidewalk", -2.55, -0.82, 0.70, 0.25, 0.185, M_PUDDLE,
       seed=301, n=18, rot=0.15)


def reflection_streak(name, cx, cy, width, length, color, strength=1.0,
                      rot_z=0.0, z=0.082):
    """A soft vertical light smear on wet ground; gradient along local Y."""
    mat = bpy.data.materials.new(name + "_mat")
    mat.use_nodes = True
    mat.surface_render_method = "DITHERED"
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    uv = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "EASE"
    e0 = ramp.color_ramp.elements[0]
    e1 = ramp.color_ramp.elements[1]
    e0.position = 0.0
    e0.color = (0, 0, 0, 1)
    e1.position = 0.85
    e1.color = (1, 1, 1, 1)
    mul = nt.nodes.new("ShaderNodeMixRGB")
    mul.blend_type = "MIX"
    mul.inputs["Fac"].default_value = 0.0
    mul.inputs["Color1"].default_value = (0, 0, 0, 1)
    mul.inputs["Color2"].default_value = (color[0] * strength,
                                          color[1] * strength,
                                          color[2] * strength, 1)
    em = nt.nodes.new("ShaderNodeEmission")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = 0.42
    nt.links.new(uv.outputs["UV"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Y"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], mul.inputs["Fac"])
    nt.links.new(mul.outputs["Color"], em.inputs["Color"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    obj = plane(name, (cx, cy, z), (width, length), mat,
                rot=(0, 0, rot_z), coll=STREET, outline=False)
    return obj


reflection_streak("Reflect_MartWarm", -2.25, -1.45, 3.15, 3.2,
                  hexc("#ffc27a"), 0.55, rot_z=0.0)
reflection_streak("Reflect_MartWarm2", -0.70, -1.55, 1.4, 2.4,
                  hexc("#ffd89b"), 0.42, rot_z=0.12)
reflection_streak("Reflect_Pylon", 0.55, -1.80, 0.65, 2.7,
                  hexc("#ffd288"), 0.5, rot_z=-0.10)
reflection_streak("Reflect_Lamp", 4.34, -0.45, 0.85, 3.4,
                  hexc("#8fd6ff"), 0.45, rot_z=-0.18)
reflection_streak("Reflect_Vending", 1.72, 3.00, 0.7, 2.6,
                  hexc("#cdedff"), 0.38, rot_z=0.50)
reflection_streak("Reflect_RedVend", 2.10, 2.75, 0.6, 2.0,
                  hexc("#ffad96"), 0.32, rot_z=0.42)
reflection_streak("Reflect_SignSide", 2.65, 3.55, 0.8, 2.8,
                  hexc("#ffc67e"), 0.35, rot_z=0.50)
reflection_streak("Reflect_Lantern", -5.95, -0.85, 0.52, 1.8,
                  hexc("#ff7b4e"), 0.40, rot_z=0.25)

# rain ripples on the puddles and road
M_RIPPLE = emit_mat("Rain_Ripple", hexc("#9ec9e8"), 0.55, alpha=0.45)
ripple_rng = random.Random(1024)
for i in range(28):
    if i < 18:
        px, py = random.choice(puddle_specs)[:2]
        px += ripple_rng.uniform(-0.9, 0.9)
        py += ripple_rng.uniform(-0.32, 0.32)
    else:
        px = ripple_rng.uniform(-7.0, 7.0)
        py = ripple_rng.uniform(-6.5, 6.5)
    rr = ripple_rng.uniform(0.08, 0.25)
    ob = torus(f"RainRipple_{i}", (px, py, 0.083), rr, 0.012,
               M_RIPPLE, seg=24, mseg=4, coll=RAIN, outline=False)
    ob.scale = (1, 1, 0.25)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# small splash spikes at selected spots
for i in range(12):
    px = ripple_rng.uniform(-7, 7)
    py = ripple_rng.uniform(-6, 6)
    for k in range(2):
        cyl(f"Splash_{i}_{k}", (px + ripple_rng.uniform(-0.08, 0.08),
                                py + ripple_rng.uniform(-0.08, 0.08),
                                0.105 + k * 0.02),
            0.008, 0.10 + k * 0.03, M_RIPPLE, verts=6,
            coll=RAIN, outline=False)

print("BUILD: rain, light, camera")

# ----------------------------------------------------------------------------
# Rain
# ----------------------------------------------------------------------------
M_RAIN = emit_mat("Rain_Streak", hexc("#8eb6d8"), 1.3, alpha=0.22)
rain_cu = bpy.data.curves.new("Rain_Curves", "CURVE")
rain_cu.dimensions = "3D"
rain_cu.resolution_u = 1
rain_cu.bevel_depth = 0.0038
rain_cu.bevel_resolution = 0
rn = random.Random(99881)
for i in range(1200):
    x = rn.uniform(-8.2, 8.2)
    y = rn.uniform(-8.2, 8.2)
    z = rn.uniform(0.2, 14.0)
    ln = rn.uniform(0.20, 0.92)
    driftx = rn.uniform(0.02, 0.16)
    drifty = rn.uniform(-0.04, 0.04)
    sp = rain_cu.splines.new("POLY")
    sp.points.add(1)
    sp.points[0].co = (x, y, z, 1)
    sp.points[1].co = (x + driftx * ln, y + drifty * ln, z - ln, 1)
rain_obj = bpy.data.objects.new("Rain_Streaks", rain_cu)
RAIN.objects.link(rain_obj)
rain_cu.materials.append(M_RAIN)

# extra near-camera rain, slightly thicker and dimmer
rain_cu2 = bpy.data.curves.new("Rain_Curves_Near", "CURVE")
rain_cu2.dimensions = "3D"
rain_cu2.bevel_depth = 0.007
rain_cu2.bevel_resolution = 0
rn2 = random.Random(11223)
for i in range(120):
    x = rn2.uniform(-6.8, 6.8)
    y = rn2.uniform(-6.6, 5.0)
    z = rn2.uniform(2.2, 11.5)
    ln = rn2.uniform(0.45, 1.35)
    sp = rain_cu2.splines.new("POLY")
    sp.points.add(1)
    sp.points[0].co = (x, y, z, 1)
    sp.points[1].co = (x + 0.12 * ln, y, z - ln, 1)
rain_obj2 = bpy.data.objects.new("Rain_Streaks_Near", rain_cu2)
RAIN.objects.link(rain_obj2)
rain_cu2.materials.append(emit_mat("Rain_Near", hexc("#89b6dd"), 0.9,
                                   alpha=0.14))

# ----------------------------------------------------------------------------
# Volume atmosphere
# ----------------------------------------------------------------------------
vol_mat = bpy.data.materials.new("Atmosphere_Volume")
vol_mat.use_nodes = True
nt = vol_mat.node_tree
nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial")
pv = nt.nodes.new("ShaderNodeVolumePrincipled")
pv.inputs["Color"].default_value = hexc("#6d8eb5")
pv.inputs["Density"].default_value = 0.004
pv.inputs["Anisotropy"].default_value = 0.35
absn = nt.nodes.new("ShaderNodeVolumeAbsorption")
absn.inputs["Color"].default_value = hexc("#14202f")
absn.inputs["Density"].default_value = 0.002
addv = nt.nodes.new("ShaderNodeAddShader")
nt.links.new(pv.outputs[0], addv.inputs[0])
nt.links.new(absn.outputs[0], addv.inputs[1])
nt.links.new(addv.outputs[0], out.inputs["Volume"])
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 5.0))
vol = bpy.context.object
vol.name = "Atmosphere_Box"
vol.scale = (16.0, 16.0, 11.0)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
vol.data.materials.append(vol_mat)
_link(vol, RAIN, False)
vol.display_type = "BOUNDS"

# ----------------------------------------------------------------------------
# Distant atmospheric backdrop (soft studio-night glow behind the model)
# ----------------------------------------------------------------------------
bd_mat = bpy.data.materials.new("Atmospheric_Backdrop")
bd_mat.use_nodes = True
bnt = bd_mat.node_tree
bnt.nodes.clear()
bout = bnt.nodes.new("ShaderNodeOutputMaterial")
bgen = bnt.nodes.new("ShaderNodeTexCoord")
bsub = bnt.nodes.new("ShaderNodeVectorMath")
bsub.operation = "SUBTRACT"
bsub.inputs[1].default_value = (0.5, 0.5, 0.0)
blen = bnt.nodes.new("ShaderNodeVectorMath")
blen.operation = "LENGTH"
bramp = bnt.nodes.new("ShaderNodeValToRGB")
bramp.color_ramp.interpolation = "EASE"
bramp.color_ramp.elements[0].position = 0.0
bramp.color_ramp.elements[0].color = hexc("#1e3044")
bramp.color_ramp.elements[1].position = 0.58
bramp.color_ramp.elements[1].color = hexc("#07101b")
be1 = bramp.color_ramp.elements.new(1.0)
be1.color = hexc("#010207")
bemi = bnt.nodes.new("ShaderNodeEmission")
bemi.inputs["Strength"].default_value = 0.85
bnt.links.new(bgen.outputs["Generated"], bsub.inputs[0])
bnt.links.new(bsub.outputs["Vector"], blen.inputs[0])
bnt.links.new(blen.outputs["Value"], bramp.inputs["Fac"])
bnt.links.new(bramp.outputs["Color"], bemi.inputs["Color"])
bnt.links.new(bemi.outputs[0], bout.inputs["Surface"])
backdrop = plane("Atmospheric_Backdrop", (-13.5, 17.0, 6.0), (48.0, 32.0),
                 bd_mat, rot=(math.radians(90), 0, math.radians(38.5)),
                 coll=RAIN, outline=False)

# ----------------------------------------------------------------------------
# World: deep blue night sky / ambient
# ----------------------------------------------------------------------------
world = bpy.data.worlds.new("Rainy_Night_World")
SCN.world = world
world.use_nodes = True
wnt = world.node_tree
wnt.nodes.clear()
wout = wnt.nodes.new("ShaderNodeOutputWorld")
wbg = wnt.nodes.new("ShaderNodeBackground")
wcoord = wnt.nodes.new("ShaderNodeTexCoord")
wsep = wnt.nodes.new("ShaderNodeSeparateXYZ")
wramp = wnt.nodes.new("ShaderNodeValToRGB")
wramp.color_ramp.elements[0].position = 0.12
wramp.color_ramp.elements[0].color = hexc("#101c2e")
wramp.color_ramp.elements[1].position = 0.82
wramp.color_ramp.elements[1].color = hexc("#02040a")
wnt.links.new(wcoord.outputs["Window"], wsep.inputs["Vector"])
wnt.links.new(wsep.outputs["Y"], wramp.inputs["Fac"])
wnt.links.new(wramp.outputs["Color"], wbg.inputs["Color"])
wbg.inputs["Strength"].default_value = 0.42
wnt.links.new(wbg.outputs[0], wout.inputs["Surface"])

# ----------------------------------------------------------------------------
# Lights
# ----------------------------------------------------------------------------
def add_area(name, loc, energy, color, size, rot=None, target=(0, 0, 1.5)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.color = color
    ld.shape = "DISK"
    ld.size = size
    ob = bpy.data.objects.new(name, ld)
    LIGHTS.objects.link(ob)
    ob.location = loc
    if rot is None:
        look_at(ob, target)
    else:
        ob.rotation_euler = rot
    return ob


def add_point(name, loc, energy, color, radius=0.2):
    ld = bpy.data.lights.new(name, "POINT")
    ld.energy = energy
    ld.color = color
    ld.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, ld)
    LIGHTS.objects.link(ob)
    ob.location = loc
    return ob


# cool moon key from the front-left
sun_data = bpy.data.lights.new("Moon_Sun", "SUN")
sun_data.energy = 1.65
sun_data.color = (0.68, 0.81, 1.0)
sun_data.angle = math.radians(4)
sun = bpy.data.objects.new("Moon_Sun", sun_data)
LIGHTS.objects.link(sun)
sun.rotation_euler = (math.radians(54), 0, math.radians(-36))

add_area("Sky_Fill", (7.5, -9.0, 8.5), 1050, (0.55, 0.72, 1.0), 9.0,
         target=(-1.0, 1.0, 2.3))
add_area("Facade_Fill", (-7.0, -6.0, 5.2), 360, (0.60, 0.76, 1.0), 5.0,
         target=(-2.2, 1.2, 2.8))
add_area("Upper_Facade_Fill", (2.5, -7.0, 6.4), 360, (0.75, 0.82, 1.0),
         6.0, target=(-1.2, 0.8, 4.3))
add_area("Upper_Front_Fill", (-2.2, -5.8, 5.9), 1000, (1.0, 0.90, 0.78),
         5.5, target=(-2.2, 0.4, 4.1))
add_area("Sign_Upwash", (-2.3, -0.6, 3.2), 260, (1.0, 0.74, 0.48),
         4.0, target=(-2.3, 0.3, 4.6))
add_area("Front_Warm_Fill", (8.0, -10.0, 7.0), 430, (1.0, 0.88, 0.72),
         7.0, target=(-2.0, 1.2, 2.2))
add_area("Shopfront_Light", (-2.1, -3.2, 2.6), 95, (1.0, 0.82, 0.60),
         2.4, target=(-2.1, 0.5, 1.7))
add_area("Store_Interior_Light", (-2.35, 2.3, 2.35), 1150,
         (1.0, 0.72, 0.43), 3.4, target=(-2.35, 2.5, 0.4))
add_area("Shop_Spill", (-2.0, 0.15, 2.05), 150, (1.0, 0.68, 0.39),
         2.1, target=(-2.0, -1.4, 0.2))
add_area("Balcony_Warm", (1.2, 2.9, 4.2), 95, (1.0, 0.60, 0.38), 1.7,
         target=(0.3, 2.9, 3.8))
add_point("Interior_Warm_Point", (-2.0, 1.9, 2.15), 200,
          (1.0, 0.66, 0.35), 0.6)
add_point("Interior_Warm_Point_2", (-3.8, 1.0, 2.0), 75,
          (1.0, 0.70, 0.42), 0.4)
add_point("Interior_Warm_Point_3", (0.0, 1.3, 1.9), 75,
          (0.92, 0.86, 0.72), 0.4)
add_point("Pylon_Glow", (0.10, -0.62, 3.70), 52, (1.0, 0.78, 0.48), 0.35)
add_point("Fascia_Glow", (-2.4, -0.35, 2.9), 62, (1.0, 0.77, 0.48), 0.6)
add_point("Alley_Light", (-5.52, 1.52, 2.23), 30, (1.0, 0.53, 0.28), 0.2)
add_point("Lantern_Glow", (-5.96, 0.10, 2.04), 25, (1.0, 0.38, 0.20), 0.25)
add_point("Neighbour_Warm_Glow", (-6.55, -0.45, 1.75), 38,
          (1.0, 0.55, 0.30), 0.35)
add_point("Vend_Bounce", (1.7, 3.0, 0.9), 55, (0.52, 0.74, 1.0), 0.5)
add_point("SideSign_Glow", (0.9, 2.6, 2.95), 80, (1.0, 0.72, 0.43), 0.4)
add_point("Backstreets_Cool", (5.5, 6.0, 2.5), 70, (0.38, 0.58, 0.95), 0.8)
add_point("Rear_Service_Glow", (-2.35, 5.65, 2.35), 40,
          (1.0, 0.62, 0.34), 0.3)
add_point("Pink_Neon_Glow", (0.8, 0.9, 3.45), 36, (1.0, 0.35, 0.60), 0.35)

# keep storefront fixtures from creating a blinding mirror hotspot on the road
for _nm, _spec in [("Front_Warm_Fill", 0.12), ("Shopfront_Light", 0.18),
                   ("Upper_Front_Fill", 0.18), ("Sign_Upwash", 0.16),
                   ("Shop_Spill", 0.22), ("Fascia_Glow", 0.18),
                   ("Pylon_Glow", 0.25), ("Upper_Facade_Fill", 0.20)]:
    _o = bpy.data.objects.get(_nm)
    if _o and _o.type == "LIGHT":
        _o.data.specular_factor = _spec

# ----------------------------------------------------------------------------
# Camera
# ----------------------------------------------------------------------------
CAM_TARGET = Vector((0.0, -0.10, 2.05))
CAM_LOC = Vector((13.2, -16.6, 11.6))
cam_data = bpy.data.cameras.new("IsoCamera")
cam = bpy.data.objects.new("IsoCamera", cam_data)
SCN.collection.objects.link(cam)
cam.location = CAM_LOC
look_at(cam, CAM_TARGET)
cam.data.type = "ORTHO"
cam.data.ortho_scale = 24.0
cam.data.lens = 55
cam.data.clip_start = 0.1
cam.data.clip_end = 250
SCN.camera = cam

# a few alternative cameras for exploring the miniature
for nm, loc, target, scale in [
    ("Camera_Detail", (8.0, -10.5, 5.0), (-1.2, 0.4, 1.8), 10.8),
    ("Camera_Reverse", (12.8, 12.5, 10.5), (0.0, 0.2, 1.9), 24.8),
    ("Camera_FrontLeft", (-11.5, -13.5, 9.2), (0.0, 0.2, 1.9), 24.8),
]:
    cd = bpy.data.cameras.new(nm)
    c = bpy.data.objects.new(nm, cd)
    SCN.collection.objects.link(c)
    c.location = loc
    look_at(c, target)
    cd.type = "ORTHO"
    cd.ortho_scale = scale

# ----------------------------------------------------------------------------
# Render / EEVEE / Freestyle / compositing
# ----------------------------------------------------------------------------
SCN.render.resolution_x = 1920 if FINAL else 1280
SCN.render.resolution_y = 1080 if FINAL else 720
SCN.render.resolution_percentage = 100
SCN.eevee.taa_render_samples = 96 if FINAL else 28
SCN.eevee.taa_samples = 24
SCN.eevee.use_raytracing = True
SCN.eevee.ray_tracing_method = "SCREEN"
SCN.eevee.ray_tracing_options.trace_max_roughness = 0.55
SCN.eevee.ray_tracing_options.use_denoise = True
SCN.eevee.ray_tracing_options.screen_trace_quality = 0.5
SCN.eevee.use_shadows = True
SCN.eevee.shadow_pool_size = "1024"
SCN.eevee.shadow_resolution_scale = 1.0
SCN.eevee.volumetric_start = 0.15
SCN.eevee.volumetric_end = 42.0
SCN.eevee.volumetric_tile_size = "4"
SCN.eevee.volumetric_samples = 48
SCN.eevee.use_volumetric_shadows = True
SCN.eevee.volumetric_shadow_samples = 16
SCN.eevee.use_fast_gi = True
SCN.eevee.fast_gi_method = "GLOBAL_ILLUMINATION"
SCN.eevee.fast_gi_ray_count = 2
SCN.eevee.fast_gi_step_count = 8
SCN.eevee.fast_gi_distance = 3.0

# Freestyle - one ink lineset for the modelled hero objects
vl = bpy.context.view_layer
vl.use_freestyle = True
fs = vl.freestyle_settings
fs.mode = "EDITOR"
fs.use_culling = True
fs.use_smoothness = True
fs.crease_angle = math.radians(135)
if fs.linesets[0].linestyle is None:
    bpy.ops.scene.freestyle_linestyle_new()
ls = fs.linesets[0]
ls.select_by_collection = True
ls.collection = OUTLINE
ls.select_silhouette = True
ls.select_border = True
ls.select_crease = True
ls.select_contour = True
ls.select_external_contour = False
ls.select_edge_mark = False
ls.select_material_boundary = False
ls.select_ridge_valley = False
ls.select_suggestive_contour = False
ls.select_by_visibility = True
ls.linestyle.color = (0.008, 0.010, 0.018)
ls.linestyle.thickness = 1.25 if FINAL else 1.0
ls.linestyle.alpha = 0.92
# avoid boxing every tiny interior object
ls.qi_start = 0

# post: subtle bloom. Blender 5.x compositor is a compositing node group.
SCN.use_nodes = True
ct = bpy.data.node_groups.new("Mart_Compositing", "CompositorNodeTree")
SCN.compositing_node_group = ct
ct.interface.new_socket(name="Image", in_out="OUTPUT",
                        socket_type="NodeSocketColor")
rl = ct.nodes.new("CompositorNodeRLayers")
glare = ct.nodes.new("CompositorNodeGlare")
glare.inputs["Type"].default_value = "Bloom"
glare.inputs["Quality"].default_value = "High"
glare.inputs["Threshold"].default_value = 0.78
glare.inputs["Strength"].default_value = 0.88
glare.inputs["Size"].default_value = 0.62
bright = ct.nodes.new("CompositorNodeBrightContrast")
try:
    bright.inputs["Bright"].default_value = 0.015
    bright.inputs["Contrast"].default_value = 0.03
except Exception as e:
    print("BrightContrast setup:", e)
# subtle colour grade: cool shadows, warm highlights, a little more saturation
hs = ct.nodes.new("CompositorNodeHueSat")
hs.inputs["Saturation"].default_value = 1.06
hs.inputs["Value"].default_value = 1.0
cb = ct.nodes.new("CompositorNodeColorBalance")
try:
    cb.inputs[4].default_value = (0.99, 1.0, 1.02, 1)
    cb.inputs[6].default_value = (1.0, 1.0, 1.0, 1)
    cb.inputs[8].default_value = (1.03, 1.0, 0.96, 1)
except Exception as e:
    print("ColorBalance setup:", e)
# soft vignette
mask = ct.nodes.new("CompositorNodeEllipseMask")
mask.inputs["Position"].default_value = (0.5, 0.5)
mask.inputs["Size"].default_value = (0.95, 0.95)
blur = ct.nodes.new("CompositorNodeBlur")
blur.inputs["Size"].default_value = (280.0, 280.0)
blur.inputs["Type"].default_value = "Gaussian"
inv = ct.nodes.new("CompositorNodeInvert")
bw = ct.nodes.new("CompositorNodeRGBToBW")
black = ct.nodes.new("CompositorNodeRGB")
black.outputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
setalpha = ct.nodes.new("CompositorNodeSetAlpha")
vig = ct.nodes.new("CompositorNodeAlphaOver")
vig.inputs["Factor"].default_value = 0.22
gout = ct.nodes.new("NodeGroupOutput")
ct.links.new(rl.outputs["Image"], glare.inputs["Image"])
ct.links.new(glare.outputs["Image"], hs.inputs["Image"])
ct.links.new(hs.outputs["Image"], cb.inputs["Image"])
ct.links.new(cb.outputs["Image"], bright.inputs["Image"])
ct.links.new(mask.outputs["Mask"], blur.inputs["Image"])
ct.links.new(blur.outputs["Image"], inv.inputs["Color"])
ct.links.new(inv.outputs[0], bw.inputs[0])
ct.links.new(black.outputs[0], setalpha.inputs["Image"])
ct.links.new(bw.outputs[0], setalpha.inputs["Alpha"])
ct.links.new(bright.outputs["Image"], vig.inputs["Background"])
ct.links.new(setalpha.outputs[0], vig.inputs["Foreground"])
ct.links.new(vig.outputs["Image"], gout.inputs["Image"])

# render settings & save
SCN.render.filepath = os.path.join(
    RENDERS, "machikado_mart_hero.png" if FINAL else "preview.png")
SCN.render.image_settings.color_mode = "RGB"
SCN.render.image_settings.compression = 20
try:
    bpy.ops.file.pack_all()
except Exception as e:
    print("Pack warning:", e)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PROJECT, "machikado_mart.blend"))
print("SCENE OBJECTS:", len(bpy.data.objects))
print("SCENE BUILT")
if not NO_RENDER:
    import time
    t0 = time.time()
    print("RENDERING", SCN.render.resolution_x, SCN.render.resolution_y,
          "samples", SCN.eevee.taa_render_samples)
    bpy.ops.render.render(write_still=True)
    print("RENDER DONE in %.1fs -> %s" % (time.time() - t0,
                                           SCN.render.filepath))

print("ALL DONE")
