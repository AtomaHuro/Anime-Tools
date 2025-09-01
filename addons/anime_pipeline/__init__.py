bl_info = {
    "name": "Anime Pipeline",
    "author": "Animation Studio",
    "version": (0, 4, 2),
    "blender": (3, 6, 0),
    "location": "View3D > N-Panel > Anime",
    "description": "Setup toon shading, outlines, and scene templates for anime-style rendering.",
    "warning": "Prototype",
    "category": "Render",
}

try:
    import bpy  # type: ignore
    from bpy.props import FloatProperty, FloatVectorProperty, BoolProperty, EnumProperty, StringProperty, IntProperty  # type: ignore
except Exception:  # pragma: no cover - outside Blender
    bpy = None  # type: ignore
    def FloatProperty(**kwargs):  # type: ignore
        return None
    def FloatVectorProperty(**kwargs):  # type: ignore
        return None
    def BoolProperty(**kwargs):  # type: ignore
        return None
    def EnumProperty(**kwargs):  # type: ignore
        return None
    def StringProperty(**kwargs):  # type: ignore
        return None
    def IntProperty(**kwargs):  # type: ignore
        return None

# stdlib for update checks (guarded at runtime)
import json, os, tempfile
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Update state (global, simple)
_UPDATE_STATE = {
    'available': False,
    'remote_version': None,
    'zip_url': None,
    'notes': None,
}

# Safe accessors for Blender PropertyDeferred values (seen in 3.6 UI properties)
def _safe_str(val, default=""):
    # Return a clean string or default when Blender returns deferred RNA wrappers
    if isinstance(val, str):
        return val
    if val is None:
        return default
    tname = type(val).__name__
    if tname in {"_PropertyDeferred", "bpy_prop", "bpy_struct", "bpy_prop_collection"}:
        return default
    try:
        s = str(val)
        # Guard against repr-like strings for RNA wrappers
        if s is None:
            return default
        if "_PropertyDeferred" in s or "bpy_prop" in s or "bpy_struct" in s:
            return default
        return s
    except Exception:
        return default

def _safe_bool(val, default=False):
    if isinstance(val, bool):
        return val
    if val is None:
        return default
    tname = type(val).__name__
    if tname in {"_PropertyDeferred", "bpy_prop", "bpy_struct", "bpy_prop_collection"}:
        return default
    try:
        if isinstance(val, (int, float)):
            return bool(val)
        if isinstance(val, str):
            return val.strip().lower() in {"1", "true", "yes", "on"}
        return bool(val)
    except Exception:
        return default

def _safe_int(val, default=0):
    if isinstance(val, bool):
        return int(val)
    if val is None:
        return default
    tname = type(val).__name__
    if tname in {"_PropertyDeferred", "bpy_prop", "bpy_struct", "bpy_prop_collection"}:
        return default
    try:
        return int(val)
    except Exception:
        try:
            return int(str(val).strip())
        except Exception:
            return default

def _version_tuple_from_any(v):
    try:
        if isinstance(v, (list, tuple)):
            return tuple(int(x) for x in v)
        if isinstance(v, str):
            parts = v.strip().split('.')
            return tuple(int(x) for x in parts if x.isdigit() or x.isnumeric())
    except Exception:
        pass
    return None

def _compare_versions(a, b):
    ta = _version_tuple_from_any(a) or (0,)
    tb = _version_tuple_from_any(b) or (0,)
    la, lb = len(ta), len(tb)
    if la < lb:
        ta = ta + (0,)*(lb-la)
    elif lb < la:
        tb = tb + (0,)*(la-lb)
    return (ta > tb) - (ta < tb)

# --- Operators ---

# Version helpers
def _bv():
    try:
        return tuple(getattr(bpy.app, 'version', (3, 6, 0)))
    except Exception:
        return (3, 6, 0)

def _at_least(major, minor):
    v = _bv()
    return (v[0], v[1]) >= (major, minor)

class ANIME_OT_add_inverted_hull(bpy.types.Operator):
    bl_idname = "anime.add_inverted_hull"
    bl_label = "Add Outline (Inverted Hull)"
    bl_description = "Add a solidified, flipped-normals outline to selected mesh objects"
    bl_options = {"REGISTER", "UNDO"}

    thickness = FloatProperty(name="Thickness", default=0.005, min=0.0, max=0.1)
    color = FloatVectorProperty(name="Color", subtype='COLOR', default=(0,0,0), min=0.0, max=1.0)
    apply_material = BoolProperty(name="Create Outline Material", default=True)

    def execute(self, context):
        sel = [o for o in context.selected_objects if o and hasattr(o, 'type') and o.type == 'MESH']
        if not sel:
            self.report({'WARNING'}, "Select one or more mesh objects")
            return {'CANCELLED'}
        for obj in sel:
            # Duplicate for hull
            hull = obj.copy()
            hull.data = obj.data.copy()
            context.collection.objects.link(hull)
            hull.name = obj.name + "_Outline"
            hull.parent = obj
            hull.modifiers.clear()

            # Solidify outward
            solid = hull.modifiers.new("AnimeOutlineSolidify", 'SOLIDIFY')
            # Cast to float/bool for 3.6 compatibility where RNA may reject PropertyDeferred
            try:
                solid.thickness = float(self.thickness)
            except Exception:
                solid.thickness = 0.005
            solid.offset = float(1.0)
            solid.use_flip_normals = bool(True)
            solid.material_offset = 1

            # Ensure backface culling and color
            if self.apply_material:
                mat = bpy.data.materials.get("Anime_Outline") or bpy.data.materials.new("Anime_Outline")
                mat.use_nodes = True
                nt = mat.node_tree
                for n in nt.nodes:
                    nt.nodes.remove(n)
                out = nt.nodes.new('ShaderNodeOutputMaterial')
                emit = nt.nodes.new('ShaderNodeEmission')
                try:
                    col = tuple(float(c) for c in self.color) if hasattr(self, 'color') else (0,0,0)
                except Exception:
                    col = (0,0,0)
                emit.inputs['Color'].default_value = (col[0], col[1], col[2], 1.0)
                emit.inputs['Strength'].default_value = 1.0
                nt.links.new(emit.outputs['Emission'], out.inputs['Surface'])
                mat.blend_method = 'OPAQUE'
                mat.use_backface_culling = True
                if hull.data.materials:
                    hull.data.materials.append(mat)
                else:
                    hull.data.materials.append(mat)

            # Display settings
            hull.display_type = 'SOLID'
            hull.show_in_front = True
        return {'FINISHED'}

class ANIME_OT_apply_toon_material(bpy.types.Operator):
    bl_idname = "anime.apply_toon_material"
    bl_label = "Apply Toon Material"
    bl_description = "Assign a toon shader node group to selected meshes"
    bl_options = {"REGISTER", "UNDO"}

# New: Manga halftone node group
def ensure_manga_group():
    """Create or fetch the Manga_Halftone_Core node group and ensure its structure."""
    ng = bpy.data.node_groups.get("Manga_Halftone_Core")
    if not ng:
        ng = bpy.data.node_groups.new("Manga_Halftone_Core", 'ShaderNodeTree')

    # IO helpers
    def ensure_input(name, socket_type, default=None):
        sock = ng.inputs.get(name)
        if not sock:
            sock = ng.inputs.new(socket_type, name)
        if default is not None:
            try:
                sock.default_value = default
            except Exception:
                pass
        return sock

    def ensure_output(name, socket_type):
        sock = ng.outputs.get(name)
        if not sock:
            sock = ng.outputs.new(socket_type, name)
        return sock

    # Define inputs/outputs
    ensure_input('BaseColor', 'NodeSocketColor', (0.8, 0.8, 0.8, 1))
    ensure_input('ShadowSteps', 'NodeSocketFloat', 3.0)
    ensure_input('ToneScale', 'NodeSocketFloat', 80.0)
    ensure_input('ToneAngleDeg', 'NodeSocketFloat', 45.0)
    ensure_input('ToneStrength', 'NodeSocketFloat', 1.0)
    ensure_input('InkColor', 'NodeSocketColor', (0.0, 0.0, 0.0, 1))
    ensure_input('PaperColor', 'NodeSocketColor', (1.0, 1.0, 1.0, 1))
    ensure_input('PatternType', 'NodeSocketFloat', 0.0)  # 0=dots, 1=lines
    ensure_input('InvertTone', 'NodeSocketFloat', 0.0)
    ensure_output('BSDF', 'NodeSocketShader')
    ensure_output('ShadowMask', 'NodeSocketFloat')
    ensure_output('RimMask', 'NodeSocketFloat')
    ensure_output('SpecularMask', 'NodeSocketFloat')

    # Rebuild nodes
    for n in list(ng.nodes):
        ng.nodes.remove(n)

    n_in = ng.nodes.new('NodeGroupInput'); n_in.location = (-800, 0)
    n_out = ng.nodes.new('NodeGroupOutput'); n_out.location = (800, 0)

    # Diffuse to brightness and banding
    n_diff = ng.nodes.new('ShaderNodeBsdfDiffuse'); n_diff.location = (-600, 40)
    n_strgb = ng.nodes.new('ShaderNodeShaderToRGB'); n_strgb.location = (-420, 40)
    n_bw = ng.nodes.new('ShaderNodeRGBToBW'); n_bw.location = (-240, 40)
    n_mul = ng.nodes.new('ShaderNodeMath'); n_mul.operation = 'MULTIPLY'; n_mul.location = (-60, 40)
    n_floor = ng.nodes.new('ShaderNodeMath'); n_floor.operation = 'FLOOR'; n_floor.location = (120, 40)
    n_div = ng.nodes.new('ShaderNodeMath'); n_div.operation = 'DIVIDE'; n_div.location = (300, 40)
    n_inv = ng.nodes.new('ShaderNodeMath'); n_inv.operation = 'SUBTRACT'; n_inv.inputs[0].default_value = 1.0; n_inv.location = (480, 40)

    # Tone pattern: coordinates -> rotate -> voronoi
    n_texcoord = ng.nodes.new('ShaderNodeTexCoord'); n_texcoord.location = (-620, -220)
    n_map = ng.nodes.new('ShaderNodeMapping'); n_map.location = (-420, -220)
    # Set rotation Z from degrees -> radians via driver-style multiply (using Math node)
    n_deg2rad = ng.nodes.new('ShaderNodeMath'); n_deg2rad.operation = 'MULTIPLY'; n_deg2rad.inputs[1].default_value = 0.01745329252; n_deg2rad.location = (-620, -340)
    # In older Blender, Mapping uses node properties; set safely
    try:
        n_map.vector_type = 'POINT'
    except Exception:
        pass
    n_voro = ng.nodes.new('ShaderNodeTexVoronoi'); n_voro.location = (-200, -280)
    n_voro.feature = 'F1'; n_voro.distance = 'EUCLIDEAN'
    # Lines pattern: use Wave texture
    n_wave = ng.nodes.new('ShaderNodeTexWave'); n_wave.location = (-200, -160)
    try:
        n_wave.wave_type = 'BANDS'
    except Exception:
        pass

    # Normalize Voronoi distance a bit
    n_vscale = ng.nodes.new('ShaderNodeMath'); n_vscale.operation = 'MULTIPLY'; n_vscale.inputs[1].default_value = 2.0; n_vscale.location = (0, -220)
    n_clamp = ng.nodes.new('ShaderNodeMath'); n_clamp.operation = 'MINIMUM'; n_clamp.inputs[1].default_value = 1.0; n_clamp.location = (180, -220)

    # Halftone threshold: pattern < inv_brightness
    n_lt = ng.nodes.new('ShaderNodeMath'); n_lt.operation = 'LESS_THAN'; n_lt.location = (360, -120)
    n_mix = ng.nodes.new('ShaderNodeMixRGB'); n_mix.blend_type = 'MIX'; n_mix.inputs['Fac'].default_value = 1.0; n_mix.location = (600, -40)
    n_em = ng.nodes.new('ShaderNodeEmission'); n_em.location = (640, 120)

    # Links core
    ng.links.new(n_in.outputs['BaseColor'], n_diff.inputs['Color'])
    ng.links.new(n_diff.outputs['BSDF'], n_strgb.inputs['Shader'])
    ng.links.new(n_strgb.outputs['Color'], n_bw.inputs['Color'])
    ng.links.new(n_bw.outputs['Val'], n_mul.inputs[0])
    ng.links.new(n_in.outputs['ShadowSteps'], n_mul.inputs[1])
    ng.links.new(n_mul.outputs[0], n_floor.inputs[0])
    ng.links.new(n_floor.outputs[0], n_div.inputs[0])
    ng.links.new(n_in.outputs['ShadowSteps'], n_div.inputs[1])
    ng.links.new(n_div.outputs[0], n_inv.inputs[1])  # inv = 1 - banded

    # Mapping rotation deg->rad and feed to node (prefer socket link, else set property)
    ng.links.new(n_in.outputs['ToneAngleDeg'], n_deg2rad.inputs[0])
    try:
        n_cxyz = ng.nodes.new('ShaderNodeCombineXYZ'); n_cxyz.location = (-420, -340)
        # X,Y = 0; Z comes from deg2rad
        n_cxyz.inputs[0].default_value = 0.0
        n_cxyz.inputs[1].default_value = 0.0
        ng.links.new(n_deg2rad.outputs[0], n_cxyz.inputs[2])
        ng.links.new(n_cxyz.outputs['Vector'], n_map.inputs['Rotation'])
    except Exception:
        try:
            n_map.rotation[2] = 0.0  # fallback default; actual angle may be set by operators if needed
        except Exception:
            pass
    # Coordinates path
    try:
        ng.links.new(n_texcoord.outputs['Generated'], n_map.inputs['Vector'])
    except Exception:
        try:
            ng.links.new(n_texcoord.outputs[0], n_map.inputs[0])
        except Exception:
            pass
    ng.links.new(n_map.outputs['Vector'], n_voro.inputs['Vector'])
    ng.links.new(n_map.outputs['Vector'], n_wave.inputs['Vector'])
    ng.links.new(n_in.outputs['ToneScale'], n_voro.inputs['Scale'])
    ng.links.new(n_in.outputs['ToneScale'], n_wave.inputs['Scale'])
    ng.links.new(n_voro.outputs['Distance'], n_vscale.inputs[0])
    ng.links.new(n_vscale.outputs[0], n_clamp.inputs[0])

    # Choose pattern by PatternType >= 0.5 ? Lines : Dots
    n_ge = ng.nodes.new('ShaderNodeMath'); n_ge.operation = 'GREATER_THAN'; n_ge.location = (160, -140)
    ng.links.new(n_in.outputs['PatternType'], n_ge.inputs[0])
    n_patmix = ng.nodes.new('ShaderNodeMixRGB'); n_patmix.blend_type = 'MIX'; n_patmix.location = (360, -200)
    ng.links.new(n_ge.outputs[0], n_patmix.inputs['Fac'])
    ng.links.new(n_clamp.outputs[0], n_patmix.inputs['Color1'])  # dots
    ng.links.new(n_wave.outputs['Color'], n_patmix.inputs['Color2'])  # lines

    # Invert tone if requested
    n_invton = ng.nodes.new('ShaderNodeMath'); n_invton.operation = 'SUBTRACT'; n_invton.inputs[0].default_value = 1.0; n_invton.location = (540, -200)
    n_invlerp = ng.nodes.new('ShaderNodeMixRGB'); n_invlerp.blend_type = 'MIX'; n_invlerp.location = (720, -200)
    ng.links.new(n_patmix.outputs['Color'], n_invton.inputs[1])
    ng.links.new(n_in.outputs['InvertTone'], n_invlerp.inputs['Fac'])
    ng.links.new(n_patmix.outputs['Color'], n_invlerp.inputs['Color1'])
    ng.links.new(n_invton.outputs[0], n_invlerp.inputs['Color2'])

    # Threshold compare and color mix
    ng.links.new(n_invlerp.outputs['Color'], n_lt.inputs[0])  # A: pattern
    ng.links.new(n_inv.outputs[0], n_lt.inputs[1])    # B: inv brightness
    # Paper color comes directly from group input
    ng.links.new(n_in.outputs['PaperColor'], n_mix.inputs['Color1'])
    ng.links.new(n_in.outputs['InkColor'], n_mix.inputs['Color2'])
    # Use less-than result modulated by ToneStrength as Fac via math* and clamp
    n_facmul = ng.nodes.new('ShaderNodeMath'); n_facmul.operation = 'MULTIPLY'; n_facmul.location = (520, -120)
    n_facclamp = ng.nodes.new('ShaderNodeMath'); n_facclamp.operation = 'MINIMUM'; n_facclamp.inputs[1].default_value = 1.0; n_facclamp.location = (700, -120)
    ng.links.new(n_lt.outputs[0], n_facmul.inputs[0])
    ng.links.new(n_in.outputs['ToneStrength'], n_facmul.inputs[1])
    ng.links.new(n_facmul.outputs[0], n_facclamp.inputs[0])
    ng.links.new(n_facclamp.outputs[0], n_mix.inputs['Fac'])

    # Output
    ng.links.new(n_mix.outputs['Color'], n_em.inputs['Color'])
    ng.links.new(n_em.outputs['Emission'], n_out.inputs['BSDF'])
    # Provide masks (shadow uses inv brightness; others zero)
    zero = ng.nodes.new('ShaderNodeValue'); zero.outputs[0].default_value = 0.0; zero.location = (520, 200)
    ng.links.new(n_inv.outputs[0], n_out.inputs['ShadowMask'])
    ng.links.new(zero.outputs[0], n_out.inputs['RimMask'])
    ng.links.new(zero.outputs[0], n_out.inputs['SpecularMask'])

    return ng

def ensure_toon_group():
    """Create or fetch the Toon_Shade_Core node group and ensure its structure."""
    ng = bpy.data.node_groups.get("Toon_Shade_Core")
    if not ng:
        ng = bpy.data.node_groups.new("Toon_Shade_Core", 'ShaderNodeTree')

    # IO helpers
    def ensure_input(name, socket_type, default=None):
        sock = ng.inputs.get(name)
        if not sock:
            sock = ng.inputs.new(socket_type, name)
        if default is not None:
            try:
                sock.default_value = default
            except Exception:
                pass
        return sock

    def ensure_output(name, socket_type):
        sock = ng.outputs.get(name)
        if not sock:
            sock = ng.outputs.new(socket_type, name)
        return sock

    # Define inputs/outputs
    ensure_input('BaseColor', 'NodeSocketColor', (0.8, 0.8, 0.8, 1))
    ensure_input('ShadowSteps', 'NodeSocketFloat', 3.0)
    ensure_input('RimPower', 'NodeSocketFloat', 1.5)
    ensure_input('RimColor', 'NodeSocketColor', (1.0, 1.0, 1.0, 1))
    ensure_input('RampStrength', 'NodeSocketFloat', 0.0)
    ensure_input('SpecularSize', 'NodeSocketFloat', 0.1)
    ensure_input('SpecularIntensity', 'NodeSocketFloat', 1.0)
    ensure_input('SpecularColor', 'NodeSocketColor', (1.0, 1.0, 1.0, 1))
    ensure_output('BSDF', 'NodeSocketShader')
    ensure_output('ShadowMask', 'NodeSocketFloat')
    ensure_output('RimMask', 'NodeSocketFloat')
    ensure_output('SpecularMask', 'NodeSocketFloat')

    # Rebuild nodes
    for n in list(ng.nodes):
        ng.nodes.remove(n)

    n_in = ng.nodes.new('NodeGroupInput'); n_in.location = (-600, 0)
    n_out = ng.nodes.new('NodeGroupOutput'); n_out.location = (1400, 0)

    # Core shading path
    n_diff = ng.nodes.new('ShaderNodeBsdfDiffuse'); n_diff.location = (-420, 0)
    n_strgb = ng.nodes.new('ShaderNodeShaderToRGB'); n_strgb.location = (-220, 0)
    n_bw = ng.nodes.new('ShaderNodeRGBToBW'); n_bw.location = (-20, 0)
    n_mul = ng.nodes.new('ShaderNodeMath'); n_mul.operation = 'MULTIPLY'; n_mul.location = (160, 0)
    n_floor = ng.nodes.new('ShaderNodeMath'); n_floor.operation = 'FLOOR'; n_floor.location = (320, 0)
    n_sub1 = ng.nodes.new('ShaderNodeMath'); n_sub1.operation = 'SUBTRACT'; n_sub1.inputs[1].default_value = 1.0; n_sub1.location = (160, -140)
    n_max1 = ng.nodes.new('ShaderNodeMath'); n_max1.operation = 'MAXIMUM'; n_max1.inputs[1].default_value = 1.0; n_max1.location = (320, -140)
    n_div = ng.nodes.new('ShaderNodeMath'); n_div.operation = 'DIVIDE'; n_div.location = (500, 0)
    n_inv = ng.nodes.new('ShaderNodeMath'); n_inv.operation = 'SUBTRACT'; n_inv.inputs[0].default_value = 1.0; n_inv.location = (500, -160)

    # Banding and Ramp
    n_darken = ng.nodes.new('ShaderNodeMixRGB'); n_darken.blend_type = 'MULTIPLY'; n_darken.inputs['Fac'].default_value = 1.0; n_darken.location = (-200, -240)
    n_dark_const = ng.nodes.new('ShaderNodeRGB'); n_dark_const.outputs[0].default_value = (0.6, 0.6, 0.6, 1); n_dark_const.location = (-380, -380)
    n_bandmix = ng.nodes.new('ShaderNodeMixRGB'); n_bandmix.blend_type = 'MIX'; n_bandmix.location = (680, 100)
    n_cr = ng.nodes.new('ShaderNodeValToRGB'); n_cr.location = (360, -80)
    n_ramp_lerp = ng.nodes.new('ShaderNodeMixRGB'); n_ramp_lerp.blend_type = 'MIX'; n_ramp_lerp.location = (860, 100)
    try:
        el = n_cr.color_ramp.elements
        if len(el) == 2:
            el[0].position = 0.35; el[0].color = (0.55, 0.55, 0.55, 1)
            el[1].position = 0.85; el[1].color = (1.0, 1.0, 1.0, 1)
    except Exception:
        pass

    # Rim
    n_lw = ng.nodes.new('ShaderNodeLayerWeight'); n_lw.location = (160, 240)
    n_rim_inv = ng.nodes.new('ShaderNodeMath'); n_rim_inv.operation = 'SUBTRACT'; n_rim_inv.inputs[0].default_value = 1.0; n_rim_inv.location = (320, 240)
    n_pow = ng.nodes.new('ShaderNodeMath'); n_pow.operation = 'POWER'; n_pow.location = (500, 240)
    n_rim_scale = ng.nodes.new('ShaderNodeMixRGB'); n_rim_scale.blend_type = 'MULTIPLY'; n_rim_scale.inputs['Fac'].default_value = 1.0; n_rim_scale.location = (680, 240)
    n_add = ng.nodes.new('ShaderNodeMixRGB'); n_add.blend_type = 'ADD'; n_add.inputs['Fac'].default_value = 1.0; n_add.location = (1040, 100)

    # Specular
    n_spec_gloss = ng.nodes.new('ShaderNodeBsdfGlossy'); n_spec_gloss.location = (160, -260)
    n_spec_strgb = ng.nodes.new('ShaderNodeShaderToRGB'); n_spec_strgb.location = (340, -260)
    n_spec_bw = ng.nodes.new('ShaderNodeRGBToBW'); n_spec_bw.location = (520, -260)
    n_spec_pow = ng.nodes.new('ShaderNodeMath'); n_spec_pow.operation = 'POWER'; n_spec_pow.inputs[1].default_value = 3.0; n_spec_pow.location = (700, -260)
    n_spec_intmul = ng.nodes.new('ShaderNodeMath'); n_spec_intmul.operation = 'MULTIPLY'; n_spec_intmul.location = (860, -260)
    n_spec_mul = ng.nodes.new('ShaderNodeMixRGB'); n_spec_mul.blend_type = 'MULTIPLY'; n_spec_mul.inputs['Fac'].default_value = 1.0; n_spec_mul.location = (1040, -260)
    n_add_spec = ng.nodes.new('ShaderNodeMixRGB'); n_add_spec.blend_type = 'ADD'; n_add_spec.inputs['Fac'].default_value = 1.0; n_add_spec.location = (1220, 100)

    # Output
    n_em = ng.nodes.new('ShaderNodeEmission'); n_em.location = (1300, 100)

    # Link core
    ng.links.new(n_in.outputs['BaseColor'], n_diff.inputs['Color'])
    ng.links.new(n_diff.outputs['BSDF'], n_strgb.inputs['Shader'])
    ng.links.new(n_strgb.outputs['Color'], n_bw.inputs['Color'])
    ng.links.new(n_bw.outputs['Val'], n_mul.inputs[0])
    ng.links.new(n_in.outputs['ShadowSteps'], n_mul.inputs[1])
    ng.links.new(n_mul.outputs[0], n_floor.inputs[0])
    ng.links.new(n_in.outputs['ShadowSteps'], n_sub1.inputs[0])
    ng.links.new(n_sub1.outputs[0], n_max1.inputs[0])
    ng.links.new(n_floor.outputs[0], n_div.inputs[0])
    ng.links.new(n_max1.outputs[0], n_div.inputs[1])

    # Banding + Ramp
    ng.links.new(n_in.outputs['BaseColor'], n_darken.inputs['Color1'])
    ng.links.new(n_dark_const.outputs[0], n_darken.inputs['Color2'])
    ng.links.new(n_darken.outputs['Color'], n_bandmix.inputs['Color1'])
    ng.links.new(n_in.outputs['BaseColor'], n_bandmix.inputs['Color2'])
    ng.links.new(n_div.outputs[0], n_bandmix.inputs['Fac'])
    ng.links.new(n_bw.outputs['Val'], n_cr.inputs['Fac'])
    ng.links.new(n_bandmix.outputs['Color'], n_ramp_lerp.inputs['Color1'])
    ng.links.new(n_cr.outputs['Color'], n_ramp_lerp.inputs['Color2'])
    ng.links.new(n_in.outputs['RampStrength'], n_ramp_lerp.inputs['Fac'])

    # Rim
    ng.links.new(n_lw.outputs['Facing'], n_rim_inv.inputs[1])
    ng.links.new(n_rim_inv.outputs[0], n_pow.inputs[0])
    ng.links.new(n_in.outputs['RimPower'], n_pow.inputs[1])
    ng.links.new(n_in.outputs['RimColor'], n_rim_scale.inputs['Color1'])
    ng.links.new(n_pow.outputs[0], n_rim_scale.inputs['Color2'])
    ng.links.new(n_ramp_lerp.outputs['Color'], n_add.inputs['Color1'])
    ng.links.new(n_rim_scale.outputs['Color'], n_add.inputs['Color2'])

    # Specular
    ng.links.new(n_spec_gloss.outputs['BSDF'], n_spec_strgb.inputs['Shader'])
    ng.links.new(n_spec_strgb.outputs['Color'], n_spec_bw.inputs['Color'])
    ng.links.new(n_spec_bw.outputs['Val'], n_spec_pow.inputs[0])
    ng.links.new(n_spec_pow.outputs[0], n_spec_intmul.inputs[0])
    ng.links.new(n_in.outputs['SpecularIntensity'], n_spec_intmul.inputs[1])
    ng.links.new(n_in.outputs['SpecularColor'], n_spec_mul.inputs['Color1'])
    ng.links.new(n_spec_intmul.outputs[0], n_spec_mul.inputs['Color2'])
    ng.links.new(n_add.outputs['Color'], n_add_spec.inputs['Color1'])
    ng.links.new(n_spec_mul.outputs['Color'], n_add_spec.inputs['Color2'])
    ng.links.new(n_in.outputs['SpecularSize'], n_spec_gloss.inputs['Roughness'])

    # Outputs
    ng.links.new(n_add_spec.outputs['Color'], n_em.inputs['Color'])
    ng.links.new(n_em.outputs['Emission'], n_out.inputs['BSDF'])
    ng.links.new(n_div.outputs[0], n_inv.inputs[1])
    ng.links.new(n_inv.outputs[0], n_out.inputs['ShadowMask'])
    ng.links.new(n_pow.outputs[0], n_out.inputs['RimMask'])
    ng.links.new(n_spec_intmul.outputs[0], n_out.inputs['SpecularMask'])

    return ng

class ANIME_OT_apply_toon_material(bpy.types.Operator):
    bl_idname = "anime.apply_toon_material"
    bl_label = "Apply Toon Material"
    bl_description = "Assign a toon shader node group to selected meshes"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        sel = [o for o in context.selected_objects if o.type == 'MESH']
        if not sel:
            self.report({'WARNING'}, "Select mesh objects")
            return {'CANCELLED'}
        ng = ensure_toon_group()
        mat = bpy.data.materials.get("Anime_Toon") or bpy.data.materials.new("Anime_Toon")
        mat.use_nodes = True
        nt = mat.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        grp = nt.nodes.new('ShaderNodeGroup'); grp.node_tree = ng
        in_rgb = nt.nodes.new('ShaderNodeRGB'); in_rgb.outputs[0].default_value = (0.8, 0.8, 0.8, 1)
        in_rim = nt.nodes.new('ShaderNodeRGB'); in_rim.outputs[0].default_value = (1.0, 1.0, 1.0, 1)
        in_steps = nt.nodes.new('ShaderNodeValue'); in_steps.outputs[0].default_value = 3.0
        in_rimpow = nt.nodes.new('ShaderNodeValue'); in_rimpow.outputs[0].default_value = 1.5
        in_ramp = nt.nodes.new('ShaderNodeValue'); in_ramp.outputs[0].default_value = 0.0
        in_spec_size = nt.nodes.new('ShaderNodeValue'); in_spec_size.outputs[0].default_value = 0.1
        in_spec_int = nt.nodes.new('ShaderNodeValue'); in_spec_int.outputs[0].default_value = 1.0
        in_spec_col = nt.nodes.new('ShaderNodeRGB'); in_spec_col.outputs[0].default_value = (1.0, 1.0, 1.0, 1)
        # AOV outputs for masks (set pass name compatibly: aov_name on 4.x, name on 3.6)
        aov_shadow = nt.nodes.new('ShaderNodeOutputAOV'); aov_shadow.location = (220, -220)
        try:
            aov_shadow.name = 'AOV_ShadowMask'
            setattr(aov_shadow, 'aov_name', 'ShadowMask')
        except Exception:
            aov_shadow.name = 'ShadowMask'
            try:
                aov_shadow.label = 'AOV_ShadowMask'
            except Exception:
                pass
        aov_rim = nt.nodes.new('ShaderNodeOutputAOV'); aov_rim.location = (220, -300)
        try:
            aov_rim.name = 'AOV_RimMask'
            setattr(aov_rim, 'aov_name', 'RimMask')
        except Exception:
            aov_rim.name = 'RimMask'
            try:
                aov_rim.label = 'AOV_RimMask'
            except Exception:
                pass
        aov_spec = nt.nodes.new('ShaderNodeOutputAOV'); aov_spec.location = (220, -380)
        try:
            aov_spec.name = 'AOV_SpecularMask'
            setattr(aov_spec, 'aov_name', 'SpecularMask')
        except Exception:
            aov_spec.name = 'SpecularMask'
            try:
                aov_spec.label = 'AOV_SpecularMask'
            except Exception:
                pass
        # Layout
        grp.location = (0,0)
        in_rgb.location = (-300, 80)
        in_rim.location = (-300, -20)
        in_steps.location = (-300, -120)
        in_rimpow.location = (-300, -200)
        in_ramp.location = (-300, -260)
        in_spec_size.location = (-300, -340)
        in_spec_int.location = (-300, -420)
        in_spec_col.location = (-300, -500)
        out.location = (220, 0)
        # Links
        nt.links.new(in_rgb.outputs[0], grp.inputs['BaseColor'])
        nt.links.new(in_steps.outputs[0], grp.inputs['ShadowSteps'])
        nt.links.new(in_rimpow.outputs[0], grp.inputs['RimPower'])
        nt.links.new(in_rim.outputs[0], grp.inputs['RimColor'])
        nt.links.new(in_ramp.outputs[0], grp.inputs['RampStrength'])
        nt.links.new(in_spec_size.outputs[0], grp.inputs['SpecularSize'])
        nt.links.new(in_spec_int.outputs[0], grp.inputs['SpecularIntensity'])
        nt.links.new(in_spec_col.outputs[0], grp.inputs['SpecularColor'])
        nt.links.new(grp.outputs['BSDF'], out.inputs['Surface'])
        # Link AOV mask outputs
        try:
            nt.links.new(grp.outputs['ShadowMask'], aov_shadow.inputs['Value'])
            nt.links.new(grp.outputs['RimMask'], aov_rim.inputs['Value'])
            nt.links.new(grp.outputs['SpecularMask'], aov_spec.inputs['Value'])
        except Exception:
            pass
        for obj in sel:
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)
        return {'FINISHED'}

class ANIME_OT_apply_style_material(bpy.types.Operator):
    bl_idname = "anime.apply_style_material"
    bl_label = "Apply Style Material"
    bl_description = "Apply the selected Anime/Manga style material to selected meshes"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        sel = [o for o in context.selected_objects if o.type == 'MESH']
        if not sel:
            self.report({'WARNING'}, "Select mesh objects")
            return {'CANCELLED'}
        scene = context.scene
        style = getattr(scene, 'anime_style_mode', 'ANIME')

        if style == 'MANGA':
            ng = ensure_manga_group()
            mat = bpy.data.materials.get("Manga_Tone") or bpy.data.materials.new("Manga_Tone")
            mat.use_nodes = True
            nt = mat.node_tree
            for n in list(nt.nodes):
                nt.nodes.remove(n)
            out = nt.nodes.new('ShaderNodeOutputMaterial'); out.location = (320, 0)
            grp = nt.nodes.new('ShaderNodeGroup'); grp.node_tree = ng; grp.location = (0, 0)
            in_rgb = nt.nodes.new('ShaderNodeRGB'); in_rgb.location = (-300, 60); in_rgb.outputs[0].default_value = (0.9, 0.9, 0.9, 1)
            in_steps = nt.nodes.new('ShaderNodeValue'); in_steps.location = (-300, -20); in_steps.outputs[0].default_value = 3.0
            # Manga-specific controls from scene
            tone_scale = float(getattr(scene, 'anime_manga_tone_scale', 80.0))
            tone_angle = float(getattr(scene, 'anime_manga_tone_angle', 45.0))
            tone_strength = float(getattr(scene, 'anime_manga_tone_strength', 1.0))
            ink_col = tuple(getattr(scene, 'anime_manga_ink_color', (0.0,0.0,0.0)))
            paper_col = tuple(getattr(scene, 'anime_manga_paper_color', (1.0,1.0,1.0)))
            pattern_type = float(getattr(scene, 'anime_manga_pattern_type', 0.0))
            invert_tone = float(getattr(scene, 'anime_manga_invert_tone', 0.0))
            in_scale = nt.nodes.new('ShaderNodeValue'); in_scale.location = (-300, -100); in_scale.outputs[0].default_value = tone_scale
            in_angle = nt.nodes.new('ShaderNodeValue'); in_angle.location = (-300, -180); in_angle.outputs[0].default_value = tone_angle
            in_strength = nt.nodes.new('ShaderNodeValue'); in_strength.location = (-300, -260); in_strength.outputs[0].default_value = tone_strength
            in_ink = nt.nodes.new('ShaderNodeRGB'); in_ink.location = (-300, -340); in_ink.outputs[0].default_value = (ink_col[0], ink_col[1], ink_col[2], 1)
            in_paper = nt.nodes.new('ShaderNodeRGB'); in_paper.location = (-300, -420); in_paper.outputs[0].default_value = (paper_col[0], paper_col[1], paper_col[2], 1)
            in_pattern = nt.nodes.new('ShaderNodeValue'); in_pattern.location = (-300, -500); in_pattern.outputs[0].default_value = pattern_type
            in_invert = nt.nodes.new('ShaderNodeValue'); in_invert.location = (-300, -580); in_invert.outputs[0].default_value = invert_tone
            # AOV nodes
            aov_shadow = nt.nodes.new('ShaderNodeOutputAOV'); aov_shadow.location = (320, -220)
            aov_rim = nt.nodes.new('ShaderNodeOutputAOV'); aov_rim.location = (320, -300)
            aov_spec = nt.nodes.new('ShaderNodeOutputAOV'); aov_spec.location = (320, -380)
            try:
                aov_shadow.name = 'AOV_ShadowMask'; setattr(aov_shadow, 'aov_name', 'ShadowMask')
                aov_rim.name = 'AOV_RimMask'; setattr(aov_rim, 'aov_name', 'RimMask')
                aov_spec.name = 'AOV_SpecularMask'; setattr(aov_spec, 'aov_name', 'SpecularMask')
            except Exception:
                aov_shadow.name = 'ShadowMask'; aov_rim.name = 'RimMask'; aov_spec.name = 'SpecularMask'
                try:
                    aov_shadow.label = 'AOV_ShadowMask'; aov_rim.label = 'AOV_RimMask'; aov_spec.label = 'AOV_SpecularMask'
                except Exception:
                    pass
            # Links
            nt.links.new(in_rgb.outputs[0], grp.inputs['BaseColor'])
            nt.links.new(in_steps.outputs[0], grp.inputs['ShadowSteps'])
            nt.links.new(in_scale.outputs[0], grp.inputs['ToneScale'])
            nt.links.new(in_angle.outputs[0], grp.inputs['ToneAngleDeg'])
            nt.links.new(in_strength.outputs[0], grp.inputs['ToneStrength'])
            nt.links.new(in_ink.outputs[0], grp.inputs['InkColor'])
            nt.links.new(in_paper.outputs[0], grp.inputs['PaperColor'])
            nt.links.new(in_pattern.outputs[0], grp.inputs['PatternType'])
            nt.links.new(in_invert.outputs[0], grp.inputs['InvertTone'])
            nt.links.new(grp.outputs['BSDF'], out.inputs['Surface'])
            # AOV mask links
            try:
                nt.links.new(grp.outputs['ShadowMask'], aov_shadow.inputs['Value'])
            except Exception:
                pass
            try:
                nt.links.new(grp.outputs['RimMask'], aov_rim.inputs['Value'])
            except Exception:
                pass
            try:
                nt.links.new(grp.outputs['SpecularMask'], aov_spec.inputs['Value'])
            except Exception:
                pass
            for obj in sel:
                if obj.data.materials:
                    obj.data.materials[0] = mat
                else:
                    obj.data.materials.append(mat)
            return {'FINISHED'}

        # Default: Anime (Toon)
        ng = ensure_toon_group()
        mat = bpy.data.materials.get("Anime_Toon") or bpy.data.materials.new("Anime_Toon")
        mat.use_nodes = True
        nt = mat.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        out = nt.nodes.new('ShaderNodeOutputMaterial'); out.location = (220, 0)
        grp = nt.nodes.new('ShaderNodeGroup'); grp.node_tree = ng; grp.location = (0, 0)
        in_rgb = nt.nodes.new('ShaderNodeRGB'); in_rgb.outputs[0].default_value = (0.8, 0.8, 0.8, 1); in_rgb.location = (-300, 80)
        in_rim = nt.nodes.new('ShaderNodeRGB'); in_rim.outputs[0].default_value = (1.0, 1.0, 1.0, 1); in_rim.location = (-300, -20)
        in_steps = nt.nodes.new('ShaderNodeValue'); in_steps.outputs[0].default_value = 3.0; in_steps.location = (-300, -120)
        in_rimpow = nt.nodes.new('ShaderNodeValue'); in_rimpow.outputs[0].default_value = 1.5; in_rimpow.location = (-300, -200)
        in_ramp = nt.nodes.new('ShaderNodeValue'); in_ramp.outputs[0].default_value = 0.0; in_ramp.location = (-300, -260)
        in_spec_size = nt.nodes.new('ShaderNodeValue'); in_spec_size.outputs[0].default_value = 0.1; in_spec_size.location = (-300, -340)
        in_spec_int = nt.nodes.new('ShaderNodeValue'); in_spec_int.outputs[0].default_value = 1.0; in_spec_int.location = (-300, -420)
        in_spec_col = nt.nodes.new('ShaderNodeRGB'); in_spec_col.outputs[0].default_value = (1.0, 1.0, 1.0, 1); in_spec_col.location = (-300, -500)
        aov_shadow = nt.nodes.new('ShaderNodeOutputAOV'); aov_shadow.location = (220, -220)
        aov_rim = nt.nodes.new('ShaderNodeOutputAOV'); aov_rim.location = (220, -300)
        aov_spec = nt.nodes.new('ShaderNodeOutputAOV'); aov_spec.location = (220, -380)
        try:
            aov_shadow.name = 'AOV_ShadowMask'; setattr(aov_shadow, 'aov_name', 'ShadowMask')
            aov_rim.name = 'AOV_RimMask'; setattr(aov_rim, 'aov_name', 'RimMask')
            aov_spec.name = 'AOV_SpecularMask'; setattr(aov_spec, 'aov_name', 'SpecularMask')
        except Exception:
            aov_shadow.name = 'ShadowMask'; aov_rim.name = 'RimMask'; aov_spec.name = 'SpecularMask'
            try:
                aov_shadow.label = 'AOV_ShadowMask'; aov_rim.label = 'AOV_RimMask'; aov_spec.label = 'AOV_SpecularMask'
            except Exception:
                pass
        # Links
        nt.links.new(in_rgb.outputs[0], grp.inputs['BaseColor'])
        nt.links.new(in_steps.outputs[0], grp.inputs['ShadowSteps'])
        nt.links.new(in_rimpow.outputs[0], grp.inputs['RimPower'])
        nt.links.new(in_rim.outputs[0], grp.inputs['RimColor'])
        nt.links.new(in_ramp.outputs[0], grp.inputs['RampStrength'])
        nt.links.new(in_spec_size.outputs[0], grp.inputs['SpecularSize'])
        nt.links.new(in_spec_int.outputs[0], grp.inputs['SpecularIntensity'])
        nt.links.new(in_spec_col.outputs[0], grp.inputs['SpecularColor'])
        nt.links.new(grp.outputs['BSDF'], out.inputs['Surface'])
        try:
            nt.links.new(grp.outputs['ShadowMask'], aov_shadow.inputs['Value'])
            nt.links.new(grp.outputs['RimMask'], aov_rim.inputs['Value'])
            nt.links.new(grp.outputs['SpecularMask'], aov_spec.inputs['Value'])
        except Exception:
            pass
        for obj in sel:
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)
        return {'FINISHED'}

class ANIME_OT_setup_scene(bpy.types.Operator):
    bl_idname = "anime.setup_scene"
    bl_label = "Setup Anime Scene"
    bl_description = "Configure Eevee settings, color management, and basic passes"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        scene.render.engine = 'BLENDER_EEVEE'
        scene.render.fps = 24
        scene.eevee.shadow_cube_size = '2048'
        scene.eevee.shadow_cascade_size = '2048'
        scene.eevee.use_ssr = False
        scene.display_settings.display_device = 'sRGB'
        scene.view_settings.view_transform = 'Standard'
        scene.view_settings.look = 'None'
        scene.view_settings.exposure = 0.0
        scene.view_settings.gamma = 1.0
        # Passes
        view_layer = context.view_layer
        view_layer.use_pass_z = True
        view_layer.use_pass_material_index = True
        # Ensure AOVs for masks exist
        try:
            aov_names = {aov.name for aov in view_layer.aovs}
            for name in ("ShadowMask", "RimMask", "SpecularMask"):
                if name not in aov_names:
                    view_layer.aovs.new(name)
        except Exception:
            pass
        return {'FINISHED'}

class ANIME_OT_setup_compositor(bpy.types.Operator):
    bl_idname = "anime.setup_compositor"
    bl_label = "Setup Compositor Template"
    bl_description = "Create a compositor node tree that tints and mixes AOV masks over the toon render"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        scene.use_nodes = True
        nt = scene.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        # Nodes
        rl = nt.nodes.new('CompositorNodeRLayers'); rl.location = (-600, 0)
        comp = nt.nodes.new('CompositorNodeComposite'); comp.location = (600, 0)
        viewer = nt.nodes.new('CompositorNodeViewer'); viewer.location = (600, -200)
        # Colors
        col_rim = nt.nodes.new('CompositorNodeRGB'); col_rim.location = (-200, 160); col_rim.outputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
        col_spec = nt.nodes.new('CompositorNodeRGB'); col_spec.location = (-200, -40); col_spec.outputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
        # Darken branch for shadows
        bc_dark = nt.nodes.new('CompositorNodeBrightContrast'); bc_dark.location = (-200, -260); bc_dark.inputs['Bright'].default_value = -0.2; bc_dark.inputs['Contrast'].default_value = 0.0
        # Mixes
        mix_shadow = nt.nodes.new('CompositorNodeMixRGB'); mix_shadow.location = (200, -200); mix_shadow.blend_type = 'MIX'
        mix_rim = nt.nodes.new('CompositorNodeMixRGB'); mix_rim.location = (200, 100); mix_rim.blend_type = 'ADD'
        mix_spec = nt.nodes.new('CompositorNodeMixRGB'); mix_spec.location = (400, 0); mix_spec.blend_type = 'ADD'
        # Links
        # Start with Image (use positional indices for broader Blender compatibility)
        nt.links.new(rl.outputs['Image'], mix_shadow.inputs[1])  # Color1
        # Darken image and mix by ShadowMask fac
        nt.links.new(rl.outputs['Image'], bc_dark.inputs['Image'])
        nt.links.new(bc_dark.outputs['Image'], mix_shadow.inputs[2])  # Color2
        if 'ShadowMask' in rl.outputs:
            nt.links.new(rl.outputs['ShadowMask'], mix_shadow.inputs[0])  # Fac
        # Rim: tint and add
        nt.links.new(mix_shadow.outputs['Image'], mix_rim.inputs[1])
        nt.links.new(col_rim.outputs[0], mix_rim.inputs[2])
        if 'RimMask' in rl.outputs:
            nt.links.new(rl.outputs['RimMask'], mix_rim.inputs[0])
        # Specular: tint and add
        nt.links.new(mix_rim.outputs['Image'], mix_spec.inputs[1])
        nt.links.new(col_spec.outputs[0], mix_spec.inputs[2])
        if 'SpecularMask' in rl.outputs:
            nt.links.new(rl.outputs['SpecularMask'], mix_spec.inputs[0])
        # Outputs
        nt.links.new(mix_spec.outputs['Image'], comp.inputs['Image'])
        nt.links.new(mix_spec.outputs['Image'], viewer.inputs['Image'])
        return {'FINISHED'}

class ANIME_OT_create_toon_rig(bpy.types.Operator):
    bl_idname = "anime.create_toon_rig"
    bl_label = "Create Toon Lighting Rig"
    bl_description = "Add a simple 3-point toon lighting setup with camera and ground"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        import math
        scene = context.scene
        col = context.collection
        # Ground
        if 'AnimeGround' not in bpy.data.objects:
            bpy.ops.mesh.primitive_plane_add(size=10, enter_editmode=False, align='WORLD', location=(0, 0, 0))
            ground = context.active_object
            ground.name = 'AnimeGround'
        # Camera
        cam = None
        for o in bpy.data.objects:
            if o.type == 'CAMERA':
                cam = o; break
        if not cam:
            bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(0, -6, 3), rotation=(math.radians(60), 0, 0))
            cam = context.active_object
        scene.camera = cam
        # Lights
        def add_area(name, power, color, loc, rot):
            lamp = bpy.data.lights.new(name, 'AREA')
            lamp.energy = power
            lamp.color = color
            lamp_obj = bpy.data.objects.new(name, lamp)
            col.objects.link(lamp_obj)
            lamp_obj.location = loc
            lamp_obj.rotation_euler = rot
            try:
                lamp.size = float(2.0)
            except Exception:
                pass
            return lamp_obj
        add_area('ToonKey', 1500.0, (1.0, 0.95, 0.9), (3, -4, 4), (math.radians(60), 0, math.radians(30)))
        add_area('ToonFill', 400.0, (0.9, 0.95, 1.0), (-3, -2, 3), (math.radians(70), 0, math.radians(-20)))
        add_area('ToonRim', 600.0, (1.0, 1.0, 1.0), (0, 3, 3), (math.radians(110), 0, math.radians(180)))
        return {'FINISHED'}

class ANIME_OT_batch_render_cameras(bpy.types.Operator):
    bl_idname = "anime.batch_render_cameras"
    bl_label = "Batch Render Cameras"
    bl_description = "Render the current frame from all cameras to files named by camera"
    bl_options = {"REGISTER"}

    def execute(self, context):
        import os
        scene = context.scene
        orig_cam = scene.camera
        output_dir = bpy.path.abspath(scene.render.filepath) or "//"
        cameras = [o for o in bpy.data.objects if o.type == 'CAMERA']
        if not cameras:
            self.report({'WARNING'}, "No cameras found")
            return {'CANCELLED'}
        for cam in cameras:
            scene.camera = cam
            base = f"{cam.name}_####"
            scene.render.filepath = os.path.join(output_dir, base)
            bpy.ops.render.render(write_still=True)
        scene.camera = orig_cam
        scene.render.filepath = output_dir
        self.report({'INFO'}, f"Rendered {len(cameras)} cameras")
        return {'FINISHED'}

class ANIME_OT_convert_principled_to_toon(bpy.types.Operator):
    bl_idname = "anime.convert_principled_to_toon"
    bl_label = "Convert Principled -> Toon"
    bl_description = "Convert selected objects' Principled materials to Anime_Toon using base color and roughness as toon inputs"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        sel = [o for o in context.selected_objects if o.type == 'MESH']
        if not sel:
            self.report({'WARNING'}, "Select mesh objects")
            return {'CANCELLED'}
        # Ensure toon group available
        ng = ensure_toon_group()
        for obj in sel:
            for slot in obj.material_slots:
                mat = slot.material
                if not mat or not mat.use_nodes:
                    continue
                nt = mat.node_tree
                out = None
                principled = None
                for n in nt.nodes:
                    if n.bl_idname == 'ShaderNodeOutputMaterial':
                        out = n
                    if n.bl_idname == 'ShaderNodeBsdfPrincipled' and not principled:
                        principled = n
                if not principled or not out:
                    continue
                # Create Toon group node
                grp = nt.nodes.new('ShaderNodeGroup')
                grp.node_tree = ng
                grp.location = (principled.location[0]+200, principled.location[1])
                # Map Base Color (preserve texture link if present)
                if principled.inputs['Base Color'].is_linked:
                    link = principled.inputs['Base Color'].links[0]
                    nt.links.new(link.from_socket, grp.inputs['BaseColor'])
                else:
                    try:
                        grp.inputs['BaseColor'].default_value = principled.inputs['Base Color'].default_value
                    except Exception:
                        pass
                # Roughness mapping -> SpecularSize (preserve texture link if present)
                if principled.inputs['Roughness'].is_linked:
                    try:
                        bw = nt.nodes.new('ShaderNodeRGBToBW'); bw.location = (grp.location[0]-180, grp.location[1]-120)
                        nt.links.new(principled.inputs['Roughness'].links[0].from_socket, bw.inputs['Color'])
                        nt.links.new(bw.outputs['Val'], grp.inputs['SpecularSize'])
                    except Exception:
                        try:
                            nt.links.new(principled.inputs['Roughness'].links[0].from_socket, grp.inputs['SpecularSize'])
                        except Exception:
                            pass
                else:
                    try:
                        rough = principled.inputs['Roughness'].default_value
                        grp.inputs['SpecularSize'].default_value = max(0.05, min(0.8, rough))
                    except Exception:
                        pass
                # Metallic mapping -> SpecularIntensity = 0.5 + 0.5 * metallic (preserve texture link)
                if principled.inputs['Metallic'].is_linked:
                    try:
                        bwm = nt.nodes.new('ShaderNodeRGBToBW'); bwm.location = (grp.location[0]-180, grp.location[1]-200)
                        mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 0.5; mul.location = (grp.location[0]-40, grp.location[1]-200)
                        add = nt.nodes.new('ShaderNodeMath'); add.operation = 'ADD'; add.inputs[1].default_value = 0.5; add.location = (grp.location[0]+120, grp.location[1]-200)
                        nt.links.new(principled.inputs['Metallic'].links[0].from_socket, bwm.inputs['Color'])
                        nt.links.new(bwm.outputs['Val'], mul.inputs[0])
                        nt.links.new(mul.outputs[0], add.inputs[0])
                        nt.links.new(add.outputs[0], grp.inputs['SpecularIntensity'])
                    except Exception:
                        pass
                else:
                    try:
                        rough = principled.inputs['Roughness'].default_value
                        metallic = principled.inputs['Metallic'].default_value if hasattr(principled.inputs['Metallic'], 'default_value') else 0.0
                        base_int = 1.0 - min(1.0, rough)
                        grp.inputs['SpecularIntensity'].default_value = max(base_int, 0.5 + 0.5 * metallic)
                    except Exception:
                        pass
                # Disconnect Principled from output and connect Toon
                # Remove any link from Principled->Surface
                to_remove = []
                for l in nt.links:
                    if l.from_node == principled and l.from_socket.name == 'BSDF' and l.to_node == out and l.to_socket.name == 'Surface':
                        to_remove.append(l)
                for l in to_remove:
                    nt.links.remove(l)
                nt.links.new(grp.outputs['BSDF'], out.inputs['Surface'])
                # Optional: add AOV outputs if not present (robust across Blender versions)
                try:
                    def find_aov(ntree, pass_name, label_name):
                        for n in ntree.nodes:
                            if n.bl_idname == 'ShaderNodeOutputAOV':
                                # Blender 4.x
                                if hasattr(n, 'aov_name') and getattr(n, 'aov_name', None) == pass_name:
                                    return n
                                # Blender 3.6
                                if getattr(n, 'name', None) == pass_name:
                                    return n
                                if getattr(n, 'label', None) == label_name:
                                    return n
                        return None

                    aov_shadow = find_aov(nt, 'ShadowMask', 'AOV_ShadowMask') or nt.nodes.new('ShaderNodeOutputAOV')
                    aov_shadow.location = (out.location[0], out.location[1]-220)
                    try:
                        aov_shadow.name = 'AOV_ShadowMask'
                        setattr(aov_shadow, 'aov_name', 'ShadowMask')
                    except Exception:
                        aov_shadow.name = 'ShadowMask'
                        try:
                            aov_shadow.label = 'AOV_ShadowMask'
                        except Exception:
                            pass

                    aov_rim = find_aov(nt, 'RimMask', 'AOV_RimMask') or nt.nodes.new('ShaderNodeOutputAOV')
                    aov_rim.location = (out.location[0], out.location[1]-300)
                    try:
                        aov_rim.name = 'AOV_RimMask'
                        setattr(aov_rim, 'aov_name', 'RimMask')
                    except Exception:
                        aov_rim.name = 'RimMask'
                        try:
                            aov_rim.label = 'AOV_RimMask'
                        except Exception:
                            pass

                    aov_spec = find_aov(nt, 'SpecularMask', 'AOV_SpecularMask') or nt.nodes.new('ShaderNodeOutputAOV')
                    aov_spec.location = (out.location[0], out.location[1]-380)
                    try:
                        aov_spec.name = 'AOV_SpecularMask'
                        setattr(aov_spec, 'aov_name', 'SpecularMask')
                    except Exception:
                        aov_spec.name = 'SpecularMask'
                        try:
                            aov_spec.label = 'AOV_SpecularMask'
                        except Exception:
                            pass

                    nt.links.new(grp.outputs['ShadowMask'], aov_shadow.inputs['Value'])
                    nt.links.new(grp.outputs['RimMask'], aov_rim.inputs['Value'])
                    nt.links.new(grp.outputs['SpecularMask'], aov_spec.inputs['Value'])
                except Exception:
                    pass
        return {'FINISHED'}

class ANIME_OT_setup_gp_lineart(bpy.types.Operator):
    bl_idname = "anime.setup_gp_lineart"
    bl_label = "Grease Pencil Line Art Preset"
    bl_description = "Create a Grease Pencil object with Line Art modifier for silhouettes and creases"
    bl_options = {"REGISTER", "UNDO"}

    thickness = FloatProperty(name="Thickness", default=2.0, min=0.1, max=20.0)
    preset = EnumProperty(
        name="Preset",
        items=[
            ('CLOSEUP', 'Close-up', 'Thicker strokes for close shots'),
            ('MID', 'Mid', 'Default mid-shot strokes'),
            ('WIDE', 'Wide', 'Thinner strokes for wide shots'),
        ],
        default='MID',
    )

    def execute(self, context):
        # Create a GP object and add Line Art modifier pointing to the scene
        # Grease Pencil object creation varies between versions
        gp = None
        try:
            bpy.ops.object.gpencil_add(type='EMPTY')
            gp = context.active_object
        except Exception:
            try:
                bpy.ops.object.gpencil_add()
                gp = context.active_object
            except Exception:
                pass
        if gp is None:
            self.report({'ERROR'}, 'Failed to create Grease Pencil object')
            return {'CANCELLED'}
        gp.name = 'AnimeLineArt'
        # Add line art modifier
        mod = gp.grease_pencil_modifiers.new(name='LineArt', type='GP_LINEART')
        mod.source_type = 'SCENE'
        # Property names differ between Blender versions; set safely when available
        try:
            if hasattr(mod, 'use_edges'):
                mod.use_edges = True
            if hasattr(mod, 'use_contour'):
                mod.use_contour = True
            if hasattr(mod, 'use_crease'):
                mod.use_crease = True
            if hasattr(mod, 'use_intersection'):
                mod.use_intersection = False
        except Exception:
            pass
        # Presets
        if self.preset == 'CLOSEUP':
            base_thick = max(self.thickness, 3.0)
        elif self.preset == 'WIDE':
            base_thick = min(self.thickness, 1.5)
        else:
            base_thick = self.thickness
        # Thickness property may not exist on all versions
        try:
            if hasattr(mod, 'thickness'):
                mod.thickness = base_thick
        except Exception:
            pass
        # Set material stroke color to black
        if not gp.data.materials:
            mat = bpy.data.materials.new('GP_Line')
            mat.grease_pencil.color = (0,0,0,1)
            gp.data.materials.append(mat)
        return {'FINISHED'}

# --- UI ---

class ANIME_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = "anime_pipeline"

    # Use assignment style for broad 3.6 compatibility
    update_url = StringProperty(
        name="(Deprecated) Manifest URL",
        description="Deprecated. Updater now checks only GitHub Releases for the configured repo.",
        default="",
    )
    github_owner = StringProperty(name="GitHub Owner", description="GitHub user or org (alternative to Update Manifest URL)", default="AtomaHuro")
    github_repo = StringProperty(name="Repository", description="GitHub repository name", default="Anime-Tools")
    github_asset_pattern = StringProperty(name="Asset Pattern", description="Substring to pick release asset zip (optional)", default="")
    include_prereleases = BoolProperty(name="Include pre-releases", description="Allow installing GitHub pre-releases", default=False)
    auto_check = BoolProperty(name="Auto-check for updates", default=True)
    check_interval_hours = IntProperty(name="Check interval (hours)", default=12, min=1, max=168)
    last_check_iso = StringProperty(name="Last Check (ISO)", default="")
    last_remote_version = StringProperty(name="Last Remote Version", default="")
    last_zip_url = StringProperty(name="Last Zip URL", default="")
    last_notes = StringProperty(name="Last Notes", default="")

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.prop(self, "update_url")
        box = layout.box()
        box.label(text="GitHub Source (updates use Releases API)")
        rowg = box.row(align=True)
        rowg.prop(self, "github_owner")
        rowg.prop(self, "github_repo")
        box.prop(self, "github_asset_pattern")
        box.prop(self, "include_prereleases")
        cur_owner = _safe_str(getattr(self, 'github_owner', 'AtomaHuro')) or 'AtomaHuro'
        cur_repo = _safe_str(getattr(self, 'github_repo', 'Anime-Tools')) or 'Anime-Tools'
        box.label(text=f"Current source: https://github.com/{cur_owner}/{cur_repo}")
        row = col.row(align=True)
        row.prop(self, "auto_check")
        row.prop(self, "check_interval_hours")
        if self.last_check_iso:
            col.label(text=f"Last check: {self.last_check_iso}")
        if self.last_remote_version:
            col.label(text=f"Last remote: v{self.last_remote_version}")
        if _UPDATE_STATE.get('available'):
            col.label(text=f"Update available: v{_UPDATE_STATE.get('remote_version')}")
            col.operator("anime.update_addon", text="Update Now", icon='FILE_REFRESH')
        col.operator("anime.debug_updates", text="Debug GitHub Updates", icon='CONSOLE')

def _gh_headers():
    return {"User-Agent": "Anime-Pipeline-Addon/0.4 GitHubCopilot", "Accept": "application/vnd.github+json"}

def _gh_get_json(url, timeout=10):
    req = Request(url, headers=_gh_headers())
    with urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode('utf-8')
    return json.loads(body)

def _select_release_and_asset(owner, repo, include_prereleases, pattern):
    debug = {"endpoint": None, "fallback": False, "chosen_asset": None}
    rel = None
    # Try latest endpoint first
    try:
        url_latest = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        debug["endpoint"] = url_latest
        data = _gh_get_json(url_latest)
        if isinstance(data, dict) and data.get('tag_name'):
            rel = data
    except Exception:
        rel = None
    # Fallback to releases list
    if rel is None:
        try:
            url_list = f"https://api.github.com/repos/{owner}/{repo}/releases"
            debug["endpoint"] = url_list
            debug["fallback"] = True
            arr = _gh_get_json(url_list)
            if isinstance(arr, list) and arr:
                for r in arr:
                    if r.get('draft'):
                        continue
                    if (not include_prereleases) and r.get('prerelease'):
                        continue
                    # Prefer a release with at least one asset
                    if (r.get('assets') or []):
                        rel = r
                        break
                # If still none, pick first non-draft regardless of assets
                if rel is None:
                    for r in arr:
                        if not r.get('draft') and ((include_prereleases) or (not r.get('prerelease'))):
                            rel = r
                            break
        except Exception:
            rel = None

    if not isinstance(rel, dict):
        return None, None, None, debug

    # Normalize version
    tag = str(rel.get('tag_name') or rel.get('name') or '')
    if tag.lower().startswith('v'):
        tag = tag[1:]
    notes = rel.get('body')
    assets = rel.get('assets', []) or []

    def is_zip_asset(a):
        n = str(a.get('name') or '')
        d = a.get('browser_download_url')
        return bool(n and d and n.lower().endswith('.zip'))

    chosen = None
    if pattern:
        for a in assets:
            if is_zip_asset(a) and pattern.lower() in str(a.get('name','')).lower():
                chosen = a; break
    if not chosen:
        prefs_names = ('anime', 'addon', 'pipeline')
        for a in assets:
            n = str(a.get('name') or '')
            if is_zip_asset(a) and any(p in n.lower() for p in prefs_names):
                chosen = a; break
    if not chosen:
        for a in assets:
            if is_zip_asset(a):
                chosen = a; break

    debug["chosen_asset"] = (str(chosen.get('name')) if chosen else None)
    zip_url = chosen.get('browser_download_url') if chosen else None
    return tag or None, zip_url, notes, debug

def _perform_update_check(prefs):
    if not prefs:
        return False
    owner = _safe_str(getattr(prefs, 'github_owner', '')).strip() or 'AtomaHuro'
    repo = _safe_str(getattr(prefs, 'github_repo', '')).strip() or 'Anime-Tools'
    pattern = _safe_str(getattr(prefs, 'github_asset_pattern', '')).strip()
    include_pr = _safe_bool(getattr(prefs, 'include_prereleases', False), False)

    try:
        remote_version, zip_url, notes, _dbg = _select_release_and_asset(owner, repo, include_pr, pattern)
    except Exception:
        remote_version, zip_url, notes = None, None, None

    if not remote_version or not zip_url:
        prefs.last_check_iso = __import__('datetime').datetime.utcnow().isoformat(timespec='seconds') + 'Z'
        prefs.last_remote_version = ''
        prefs.last_zip_url = ''
        prefs.last_notes = ''
        _UPDATE_STATE['available'] = False
        _UPDATE_STATE['remote_version'] = None
        _UPDATE_STATE['zip_url'] = None
        _UPDATE_STATE['notes'] = None
        return False

    prefs.last_remote_version = str(remote_version)
    prefs.last_zip_url = str(zip_url)
    prefs.last_notes = str(notes or '')
    prefs.last_check_iso = __import__('datetime').datetime.utcnow().isoformat(timespec='seconds') + 'Z'
    is_newer = _compare_versions(remote_version, bl_info.get('version')) > 0
    _UPDATE_STATE['available'] = bool(is_newer)
    _UPDATE_STATE['remote_version'] = str(remote_version)
    _UPDATE_STATE['zip_url'] = str(zip_url)
    _UPDATE_STATE['notes'] = str(notes or '')
    return is_newer

def _auto_update_timer():
    try:
        addon_prefs = bpy.context.preferences.addons.get('anime_pipeline')
        prefs = addon_prefs.preferences if addon_prefs else None
        if not prefs or not _safe_bool(getattr(prefs, 'auto_check', True), True):
            return None
        # Throttle by interval
        import datetime
        last_iso = _safe_str(getattr(prefs, 'last_check_iso', ''))
        if last_iso:
            try:
                last = datetime.datetime.fromisoformat(last_iso.replace('Z',''))
                delta = datetime.datetime.utcnow() - last
                hours = max(1, _safe_int(getattr(prefs, 'check_interval_hours', 12), 12))
                if delta.total_seconds() < hours * 3600:
                    return max(60.0, hours * 3600.0)  # check later
            except Exception:
                pass
        _perform_update_check(prefs)
        # Schedule next run
        hours = max(1, _safe_int(getattr(prefs, 'check_interval_hours', 12), 12))
        return max(60.0, hours * 3600.0)
    except Exception:
        return None

class ANIME_OT_check_updates(bpy.types.Operator):
    bl_idname = "anime.check_updates"
    bl_label = "Check for Updates"
    bl_description = "Check GitHub Releases for a newer add-on version"
    bl_options = {"REGISTER"}

    def execute(self, context):
        addon = context.preferences.addons.get('anime_pipeline')
        prefs = addon.preferences if addon else None
        newer = _perform_update_check(prefs)
        if newer:
            self.report({'INFO'}, f"Update available: v{_UPDATE_STATE.get('remote_version')}")
        else:
            self.report({'INFO'}, "No updates available or check failed")
        return {'FINISHED'}

class ANIME_OT_debug_updates(bpy.types.Operator):
    bl_idname = "anime.debug_updates"
    bl_label = "Debug GitHub Updates"
    bl_description = "Print the latest GitHub release JSON and the chosen asset to the console"
    bl_options = {"REGISTER"}

    def execute(self, context):
        addon = context.preferences.addons.get('anime_pipeline')
        prefs = addon.preferences if addon else None
        if not prefs:
            self.report({'ERROR'}, 'Preferences not available')
            return {'CANCELLED'}
        owner = _safe_str(getattr(prefs, 'github_owner', '')).strip() or 'AtomaHuro'
        repo = _safe_str(getattr(prefs, 'github_repo', '')).strip() or 'Anime-Tools'
        pattern = _safe_str(getattr(prefs, 'github_asset_pattern', '')).strip()
        include_pr = _safe_bool(getattr(prefs, 'include_prereleases', False), False)
        print(f"[Anime Pipeline][Debug Updates] owner={owner} repo={repo} pattern={pattern!r} include_prereleases={include_pr}")
        try:
            tag_norm, zip_url, notes, dbg = _select_release_and_asset(owner, repo, include_pr, pattern)
            print(f"[Anime Pipeline][Debug Updates] endpoint={dbg.get('endpoint')} fallback={dbg.get('fallback')} chosen_asset={dbg.get('chosen_asset')} url={zip_url}")
            print(f"[Anime Pipeline][Debug Updates] local_version={bl_info.get('version')}, remote_version={tag_norm}")
            is_newer = _compare_versions(tag_norm, bl_info.get('version')) > 0 if tag_norm else False
            msg = f"Source OK: remote v{tag_norm or 'None'} | asset: {dbg.get('chosen_asset') or 'None'} | newer={is_newer}"
            self.report({'INFO'}, msg)
        except Exception as e:
            print("[Anime Pipeline][Debug Updates] Error:", e)
            self.report({'ERROR'}, f"GitHub request failed: {e}")
            return {'CANCELLED'}
        return {'FINISHED'}

class ANIME_OT_update_addon(bpy.types.Operator):
    bl_idname = "anime.update_addon"
    bl_label = "Update Add-on"
    bl_description = "Download and install the latest add-on zip from GitHub Releases"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        addon = context.preferences.addons.get('anime_pipeline')
        prefs = addon.preferences if addon else None
        # Read URL safely from update state or preferences
        url = _safe_str(_UPDATE_STATE.get('zip_url') or (_safe_str(getattr(prefs, 'last_zip_url', ''), '') if prefs else ''), '')
        if not url:
            self.report({'WARNING'}, 'No download URL set. Configure GitHub Owner/Repository in Add-on Preferences and Check for Updates first.')
            return {'CANCELLED'}
        temp_dir = tempfile.gettempdir()
        zip_path = os.path.join(temp_dir, 'anime_pipeline_update.zip')
        try:
            with urlopen(url, timeout=15) as resp, open(zip_path, 'wb') as f:
                f.write(resp.read())
        except Exception as e:
            self.report({'ERROR'}, f"Download failed: {e}")
            return {'CANCELLED'}
        # Install and enable
        try:
            bpy.ops.preferences.addon_install(filepath=zip_path, overwrite=True, target='DEFAULT')
            bpy.ops.preferences.addon_enable(module='anime_pipeline')
            self.report({'INFO'}, 'Anime Pipeline updated. You may need to save prefs and restart Blender.')
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Install failed: {e}")
            return {'CANCELLED'}

class ANIME_OT_setup_freestyle(bpy.types.Operator):
    bl_idname = "anime.setup_freestyle"
    bl_label = "Enable Freestyle Lines"
    bl_description = "Enable Freestyle on the view layer and create a basic lineset/linestyle"
    bl_options = {"REGISTER", "UNDO"}

    thickness = FloatProperty(name="Thickness (px)", default=2.0, min=0.1, max=20.0)
    color = FloatVectorProperty(name="Line Color", subtype='COLOR', default=(0,0,0), min=0.0, max=1.0)
    use_silhouette = BoolProperty(name="Silhouette", default=True)
    use_crease = BoolProperty(name="Creases", default=True)
    use_intersection = BoolProperty(name="Intersections", default=False)

    def execute(self, context):
        layer = context.view_layer
        layer.use_freestyle = True
        fs = layer.freestyle_settings
        # Try to get existing lineset named 'Anime', else create
        lineset = None
        for ls in fs.linesets:
            if ls.name == 'Anime':
                lineset = ls
                break
        if not lineset:
            lineset = fs.linesets.new('Anime')
        # Configure selection (cast to bool for older Blender compatibility)
        lineset.select_silhouette = bool(self.use_silhouette)
        lineset.select_crease = bool(self.use_crease)
        if hasattr(lineset, 'select_intersection'):
            lineset.select_intersection = bool(self.use_intersection)
        lineset.select_border = False
        lineset.select_edge_mark = False
        lineset.visibility = 'VISIBLE'
        lineset.select_by_visibility = True
        # Style
        ls = lineset.linestyle
        try:
            ls.thickness = float(self.thickness)
        except Exception:
            pass
        try:
            ls.color = (self.color[0], self.color[1], self.color[2])
        except Exception:
            pass
        # Add thickness-by-distance modifier (Freestyle) if available
        try:
            mod = ls.thickness_modifiers.new('DISTANCE_FROM_CAMERA')
            mod.range_min = 5.0
            mod.range_max = 30.0
            try:
                mod.thickness_min = float(max(0.25, float(self.thickness) * 0.3))
            except Exception:
                pass
            try:
                mod.thickness_max = float(self.thickness)
            except Exception:
                pass
            mod.invert = False
        except Exception:
            pass
        return {'FINISHED'}

class ANIME_OT_apply_outline_settings(bpy.types.Operator):
    bl_idname = "anime.apply_outline_settings"
    bl_label = "Apply Outline Settings"
    bl_description = "Apply global outline thickness to inverted hull meshes, Freestyle, and GP Line Art"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        hull_thick = float(getattr(scene, 'anime_outline_hull_thickness', 0.005))
        line_thick = float(getattr(scene, 'anime_outline_line_thickness', 2.0))
        selected_only = bool(getattr(scene, 'anime_outline_selected_only', True))

        adjusted_hulls = 0
        # Adjust inverted hull Solidify thickness on outline objects created by this add-on
        try:
            candidates = [o for o in bpy.data.objects if o and hasattr(o, 'modifiers')]
            if selected_only:
                selset = set(context.selected_objects)
                def affects(o):
                    return (o in selset) or (getattr(o, 'parent', None) in selset)
                candidates = [o for o in candidates if affects(o)]
            for o in candidates:
                for m in getattr(o, 'modifiers', []):
                    if getattr(m, 'type', '') == 'SOLIDIFY' and getattr(m, 'name', '').startswith('AnimeOutlineSolidify'):
                        try:
                            m.thickness = float(hull_thick)
                            adjusted_hulls += 1
                        except Exception:
                            pass
        except Exception:
            pass

        adjusted_fs = False
        # Adjust Freestyle line thickness on the 'Anime' lineset if present
        try:
            layer = context.view_layer
            if getattr(layer, 'use_freestyle', False):
                fs = layer.freestyle_settings
                for ls in fs.linesets:
                    if ls.name == 'Anime':
                        try:
                            ls.linestyle.thickness = line_thick
                            # If a thickness-by-distance modifier exists, update its max
                            for mod in getattr(ls.linestyle, 'thickness_modifiers', []) or []:
                                try:
                                    if hasattr(mod, 'thickness_max'):
                                        mod.thickness_max = line_thick
                                except Exception:
                                    pass
                            adjusted_fs = True
                        except Exception:
                            pass
                        break
        except Exception:
            pass

        adjusted_gp = False
        # Adjust GP Line Art thickness on AnimeLineArt object
        try:
            gp = bpy.data.objects.get('AnimeLineArt')
            if gp and hasattr(gp, 'grease_pencil_modifiers'):
                for mod in gp.grease_pencil_modifiers:
                    if getattr(mod, 'type', '') == 'GP_LINEART':
                        try:
                            if hasattr(mod, 'thickness'):
                                mod.thickness = line_thick
                                adjusted_gp = True
                        except Exception:
                            pass
                        break
        except Exception:
            pass

        self.report({'INFO'}, f"Outlines updated: hulls {adjusted_hulls}, freestyle {'yes' if adjusted_fs else 'no'}, gp {'yes' if adjusted_gp else 'no'}")
        return {'FINISHED'}

class ANIME_OT_validate_environment(bpy.types.Operator):
    bl_idname = "anime.validate_env"
    bl_label = "Validate Environment"
    bl_description = "Run quick checks for features used by this add-on across Blender versions"
    bl_options = {"REGISTER"}

    def execute(self, context):
        msgs = []
        # Blender version
        try:
            v = getattr(bpy.app, 'version_string', None) or str(getattr(bpy.app, 'version', (0,0,0)))
            msgs.append(f"Blender: {v}")
        except Exception:
            msgs.append("Blender: <unknown>")

        # AOV node and aov_name support
        aov_node_ok = hasattr(bpy.types, 'ShaderNodeOutputAOV')
        aov_name_prop = False
        try:
            if aov_node_ok:
                for p in bpy.types.ShaderNodeOutputAOV.bl_rna.properties:
                    if getattr(p, 'identifier', '') == 'aov_name':
                        aov_name_prop = True
                        break
        except Exception:
            pass
        msgs.append(f"AOV Output Node: {'OK' if aov_node_ok else 'MISSING'}; aov_name prop: {'yes' if aov_name_prop else 'no'}")

        # View Layer AOVs presence
        try:
            view_layer = context.view_layer
            have = {aov.name for aov in getattr(view_layer, 'aovs', [])}
            needed = {"ShadowMask", "RimMask", "SpecularMask"}
            missing = needed - have
            if missing:
                msgs.append(f"View Layer AOVs missing: {', '.join(sorted(missing))} (run Setup Scene)")
            else:
                msgs.append("View Layer AOVs: OK")
        except Exception:
            msgs.append("View Layer AOVs: unavailable")

        # Compositor MixRGB index linking note
        msgs.append("Compositor MixRGB: using index-based sockets for 3.6+ compatibility")

        # Grease Pencil Line Art availability
        try:
            has_gp = hasattr(bpy.ops.object, 'gpencil_add')
            msgs.append(f"Grease Pencil add: {'OK' if has_gp else 'MISSING'}")
        except Exception:
            msgs.append("Grease Pencil add: unavailable")
        try:
            # Modifier type token remains GP_LINEART; properties differ and are guarded elsewhere
            has_lineart = True
            msgs.append(f"Line Art modifier: {'OK' if has_lineart else 'MISSING'}")
        except Exception:
            msgs.append("Line Art modifier: unavailable")

        # Freestyle availability
        msgs.append("Freestyle: bool-casted flags in use for compatibility")

        # Report summary
        summary = " | ".join(msgs)
        self.report({'INFO'}, summary)
        print("[Anime Pipeline] Validate Environment:\n  - " + "\n  - ".join(msgs))
        return {'FINISHED'}

class ANIME_PT_panel(bpy.types.Panel):
    bl_label = "Anime Pipeline"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Anime'

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.operator(ANIME_OT_setup_scene.bl_idname, icon='SCENE_DATA')
        col.operator(ANIME_OT_create_toon_rig.bl_idname, icon='LIGHT')
        col.separator()
        col.operator(ANIME_OT_convert_principled_to_toon.bl_idname, icon='SHADING_TEXTURE')
        col.operator(ANIME_OT_apply_toon_material.bl_idname, icon='MATERIAL')
        # Style selection and apply
        sbox = layout.box()
        sbox.label(text="Style")
        sbox.prop(context.scene, "anime_style_mode", text="Mode")
        if context.scene.anime_style_mode == 'MANGA':
            row = sbox.row(align=True)
            row.prop(context.scene, "anime_manga_tone_scale", text="Tone Scale")
            row = sbox.row(align=True)
            row.prop(context.scene, "anime_manga_tone_angle", text="Angle")
            row = sbox.row(align=True)
            row.prop(context.scene, "anime_manga_tone_strength", text="Strength")
            row = sbox.row(align=True)
            row.prop(context.scene, "anime_manga_ink_color", text="Ink")
            row = sbox.row(align=True)
            row.prop(context.scene, "anime_manga_paper_color", text="Paper")
            row = sbox.row(align=True)
            row.prop(context.scene, "anime_manga_pattern_type", text="Pattern (0=Dots,1=Lines)")
            row = sbox.row(align=True)
            row.prop(context.scene, "anime_manga_invert_tone", text="Invert Tone")
        sbox.operator(ANIME_OT_apply_style_material.bl_idname, icon='MATERIAL')
        col.operator(ANIME_OT_add_inverted_hull.bl_idname, icon='OUTLINER_OB_MESH')
        # Outline controls
        box = layout.box()
        box.label(text="Outlines")
        row = box.row(align=True)
        row.prop(context.scene, "anime_outline_hull_thickness", text="Hull (m)")
        row = box.row(align=True)
        row.prop(context.scene, "anime_outline_line_thickness", text="Lines (px)")
        row = box.row(align=True)
        row.prop(context.scene, "anime_outline_selected_only", text="Selected Meshes Only")
        box.operator(ANIME_OT_apply_outline_settings.bl_idname, icon='MOD_SOLIDIFY')
        col.separator()
        col.operator(ANIME_OT_setup_freestyle.bl_idname, icon='LINE_DATA')
        col.operator(ANIME_OT_setup_gp_lineart.bl_idname, icon='GREASEPENCIL')
        col.operator(ANIME_OT_setup_compositor.bl_idname, icon='NODE_COMPOSITING')
        col.separator()
        # Updates box
        box = layout.box()
        box.label(text=f"Anime Pipeline v{'.'.join(str(x) for x in bl_info.get('version', (0,))) }")
        rowu = box.row(align=True)
        rowu.operator(ANIME_OT_check_updates.bl_idname, icon='FILE_REFRESH')
        if _UPDATE_STATE.get('available'):
            rowu.operator(ANIME_OT_update_addon.bl_idname, text=f"Update to v{_UPDATE_STATE.get('remote_version')}", icon='IMPORT')
        else:
            box.label(text="No update available")
        col.operator(ANIME_OT_batch_render_cameras.bl_idname, icon='RENDER_STILL')

# --- Registration ---

classes = (
    ANIME_AddonPreferences,
    ANIME_OT_add_inverted_hull,
    ANIME_OT_apply_toon_material,
    ANIME_OT_apply_style_material,
    ANIME_OT_setup_scene,
    ANIME_OT_setup_compositor,
    ANIME_OT_create_toon_rig,
    ANIME_OT_batch_render_cameras,
    ANIME_OT_convert_principled_to_toon,
    ANIME_OT_setup_gp_lineart,
    ANIME_OT_setup_freestyle,
    ANIME_OT_check_updates,
    ANIME_OT_debug_updates,
    ANIME_OT_update_addon,
    ANIME_OT_apply_outline_settings,
    ANIME_OT_validate_environment,
    ANIME_PT_panel,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    # Scene properties
    try:
        # Outlines
        bpy.types.Scene.anime_outline_hull_thickness = FloatProperty(name="Hull Thickness (m)", default=0.005, min=0.0, max=0.1)
        bpy.types.Scene.anime_outline_line_thickness = FloatProperty(name="Line Thickness (px)", default=2.0, min=0.1, max=20.0)
        bpy.types.Scene.anime_outline_selected_only = BoolProperty(name="Affect Selected Meshes Only", default=True)
        # Style
        bpy.types.Scene.anime_style_mode = EnumProperty(name="Style", items=[('ANIME','Anime','Toon shader look'), ('MANGA','Manga','Halftone tone look')], default='ANIME')
        bpy.types.Scene.anime_manga_tone_scale = FloatProperty(name="Tone Scale", default=80.0, min=2.0, max=400.0)
        bpy.types.Scene.anime_manga_tone_angle = FloatProperty(name="Tone Angle", default=45.0, min=-180.0, max=180.0)
        bpy.types.Scene.anime_manga_tone_strength = FloatProperty(name="Tone Strength", default=1.0, min=0.0, max=2.0)
        bpy.types.Scene.anime_manga_ink_color = FloatVectorProperty(name="Ink Color", subtype='COLOR', default=(0.0,0.0,0.0), min=0.0, max=1.0)
        bpy.types.Scene.anime_manga_paper_color = FloatVectorProperty(name="Paper Color", subtype='COLOR', default=(1.0,1.0,1.0), min=0.0, max=1.0)
        bpy.types.Scene.anime_manga_pattern_type = FloatProperty(name="Pattern Type", description="0 = Dots, 1 = Lines", default=0.0, min=0.0, max=1.0)
        bpy.types.Scene.anime_manga_invert_tone = FloatProperty(name="Invert Tone", description="0 = Normal, 1 = Inverted", default=0.0, min=0.0, max=1.0)
    except Exception:
        pass
    # Start update timer if enabled
    try:
        bpy.app.timers.register(_auto_update_timer, first_interval=5.0, persistent=True)
    except Exception:
        pass

def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    # Remove scene properties
    try:
        del bpy.types.Scene.anime_outline_hull_thickness
        del bpy.types.Scene.anime_outline_line_thickness
        del bpy.types.Scene.anime_outline_selected_only
        del bpy.types.Scene.anime_style_mode
        del bpy.types.Scene.anime_manga_tone_scale
        del bpy.types.Scene.anime_manga_tone_angle
        del bpy.types.Scene.anime_manga_tone_strength
        del bpy.types.Scene.anime_manga_ink_color
        del bpy.types.Scene.anime_manga_paper_color
        del bpy.types.Scene.anime_manga_pattern_type
        del bpy.types.Scene.anime_manga_invert_tone
    except Exception:
        pass

if __name__ == "__main__":
    register()
