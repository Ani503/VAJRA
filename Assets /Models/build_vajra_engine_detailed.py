"""
VAJRA - Detailed Turbofan Engine Generator for Blender (Su-30MKI AL-31FP)
Generates high-fidelity standalone AL-31FP turbofan engine assembly matching Reference Image 3.

Modules (strictly ordered along longitudinal axis Y):
  1. Fan (LP Compressor stage 1 + spinner) -> dy = -1.2m
  2. Intermediate Casing & Bearing #3 Support -> dy = -0.7m
  3. High-Pressure Compressor (HPC multi-stage) -> dy = -0.3m
  4. Central Shaft (coaxial dual-spool) -> datum / center (0,0,0)
  5. Combustion Chamber & Fuel Injectors -> dy = +0.15m
  6. High & Low Pressure Turbines (HPT/LPT) -> dy = +0.65m
  7. Articulated 3D TVC Nozzle -> dy = +1.25m
  8. Bypass Duct Casing (top cutaway cowl) -> dz = +0.65m (lifts directly above core)
  9. Accessory Gearbox Drive -> dy = -0.4m, dz = -0.5m (directly below core)
"""
import bpy
import bmesh
import math
import os
from mathutils import Vector, Matrix

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
GLB_NAME = "vajra_engine_detailed.glb"
BLEND_NAME = "vajra_engine_detailed.blend"
SEGMENTS = 48

def clear_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials):
        for item in list(block):
            if item.users == 0:
                block.remove(item)

def lathe(bm, profile, segments=SEGMENTS, closed_profile=False):
    rings = []
    for (r, y) in profile:
        ring = []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            ring.append(bm.verts.new((r * math.cos(a), y, r * math.sin(a))))
        rings.append(ring)
    count = len(rings)
    last = count if closed_profile else count - 1
    for k in range(last):
        r0, r1 = rings[k], rings[(k + 1) % count]
        for i in range(segments):
            j = (i + 1) % segments
            try:
                bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            except ValueError:
                pass
    return rings

def blade(bm, angle, r_root, r_tip, y, chord, thick, pitch_deg, taper=0.6):
    u = Vector((math.cos(angle), 0, math.sin(angle)))
    t = Vector((-math.sin(angle), 0, math.cos(angle)))
    yv = Vector((0, 1, 0))
    p = math.radians(pitch_deg)
    c_dir = yv * math.cos(p) + t * math.sin(p)
    n_dir = -yv * math.sin(p) + t * math.cos(p)
    verts = []
    for r, cw, th in ((r_root, chord / 2, thick / 2), (r_tip, chord / 2 * taper, thick / 2 * 0.6)):
        centre = u * r + yv * y
        for sc in (-1, 1):
            for sn in (-1, 1):
                verts.append(bm.verts.new(centre + c_dir * (cw * sc) + n_dir * (th * sn)))
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 2, 6, 4), (1, 5, 7, 3), (0, 4, 5, 1), (2, 3, 7, 6)]
    for q in quads:
        try:
            bm.faces.new([verts[i] for i in q])
        except ValueError:
            pass

def blade_row(bm, count, r_root, r_tip, y, chord, thick, pitch, phase=0.0, taper=0.6):
    for i in range(count):
        blade(bm, phase + 2 * math.pi * i / count, r_root, r_tip, y, chord, thick, pitch, taper)

def disc(bm, r_in, r_out, y0, y1, segments=SEGMENTS):
    if r_in <= 0.001:
        lathe(bm, [(0.0, y0), (r_out, y0), (r_out, y1), (0.0, y1)], segments)
        return
    lathe(bm, [(r_in, y0), (r_out, y0), (r_out, y1), (r_in, y1)], segments, closed_profile=True)

def finish_object(name, bm, material, component, explode_dx=0.0, explode_dy=0.0, explode_dz=0.0, is_shell=False):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(mesh)
    bm.free()
    
    ys = [v.co.y for v in mesh.vertices]
    ymid = (min(ys) + max(ys)) / 2 if ys else 0
    mesh.transform(Matrix.Translation((0, -ymid, 0)))
    obj = bpy.data.objects.new(name, mesh)
    obj.location = (0, ymid, 0)
    bpy.context.collection.objects.link(obj)
    
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.materials.append(material)
    
    obj["vajra_component"] = component
    obj["explode_dx"] = float(explode_dx)
    obj["explode_dy"] = float(explode_dy)
    obj["explode_dz"] = float(explode_dz)
    obj["explode_offset"] = float(max(abs(explode_dx), abs(explode_dy), abs(explode_dz)))
    if abs(explode_dx) >= max(abs(explode_dy), abs(explode_dz)):
        obj["explode_axis"] = "X"
    elif abs(explode_dy) >= abs(explode_dz):
        obj["explode_axis"] = "Y"
    else:
        obj["explode_axis"] = "Z"
    obj["spin_axis"] = ""  # NEVER auto-spin!
    obj["is_shell"] = bool(is_shell)
    return obj

def make_material(name, rgb, metallic=0.8, roughness=0.35):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
    mat.diffuse_color = (*rgb, 1.0)
    return mat

# --- Parts ---
def build_fan(mat):
    bm = bmesh.new()
    lathe(bm, [(0.0, -3.2), (0.15, -3.05), (0.32, -2.85), (0.48, -2.55), (0.54, -2.25), (0.0, -2.25)])
    blade_row(bm, 24, 0.48, 1.68, -2.50, chord=0.55, thick=0.07, pitch=34, taper=0.52)
    return finish_object("Fan", bm, mat, "Fan (LP Compressor Stg 1)", explode_dy=-1.2)

def build_intermediate_casing(mat):
    bm = bmesh.new()
    disc(bm, 0.38, 0.62, -2.25, -2.0)
    disc(bm, 1.35, 1.68, -2.25, -2.0)
    for i in range(12):
        blade(bm, 2 * math.pi * i / 12, 0.62, 1.35, -2.12, chord=0.30, thick=0.06, pitch_deg=0)
    return finish_object("Intermediate_Casing", bm, mat, "Intermediate Casing & Bearing #3", explode_dy=-0.7)

def build_compressor(mat):
    bm = bmesh.new()
    lathe(bm, [(0.42, -1.95), (0.62, -1.70), (0.74, -0.80), (0.82, -0.05), (0.82, 0.05), (0.42, 0.05), (0.42, -1.95)])
    for s in range(6):
        y = -1.75 + s * 0.30
        r_tip = 1.05 - s * 0.045
        disc(bm, 0.42, 0.65 + s * 0.03, y - 0.03, y + 0.03)
        blade_row(bm, 36 + 2 * s, 0.62 + s * 0.03, r_tip, y, chord=0.18, thick=0.025, pitch=25, phase=0.05 * s, taper=0.7)
    return finish_object("Compressor", bm, mat, "High-Pressure Compressor (HPC)", explode_dy=-0.3)

def build_combustor(mat):
    bm = bmesh.new()
    lathe(bm, [(1.02, 0.20), (1.06, 0.35), (1.06, 1.35), (1.02, 1.50), (0.76, 1.50), (0.72, 1.35), (0.72, 0.35), (0.76, 0.20)], closed_profile=True)
    for i in range(6):
        y = 0.40 + i * 0.18
        lathe(bm, [(1.07, y), (1.12, y + 0.02), (1.12, y + 0.06), (1.07, y + 0.08)], closed_profile=True)
    for i in range(16):
        a = 2 * math.pi * i / 16
        c = Vector((math.cos(a), 0, math.sin(a)))
        base = Vector((0, 0.20, 0)) + c * 0.74
        for dy, w in ((0.0, 0.06), (-0.18, 0.03)):
            disc(bm, 0.0, w, 0.20 + dy, 0.20 + dy + 0.04)
    return finish_object("Combustion_Chamber", bm, mat, "Annular Combustor & Fuel Injectors", explode_dy=0.15)

def build_turbine(mat):
    bm = bmesh.new()
    lathe(bm, [(0.40, 1.60), (0.58, 1.75), (0.64, 2.30), (0.58, 2.85), (0.42, 2.90), (0.40, 1.60)])
    for s in range(4):
        y = 1.80 + s * 0.28
        r_tip = 0.92 + s * 0.06
        disc(bm, 0.40, 0.60, y - 0.04, y + 0.04)
        blade_row(bm, 42 - 3 * s, 0.58, r_tip, y, chord=0.22, thick=0.03, pitch=-28, phase=0.04 * s, taper=0.65)
    return finish_object("Turbine", bm, mat, "High & Low Pressure Turbines", explode_dy=0.65)

def build_shaft(mat):
    bm = bmesh.new()
    lathe(bm, [(0.0, -2.8), (0.18, -2.8), (0.18, 3.2), (0.0, 3.2)])
    lathe(bm, [(0.28, -2.1), (0.28, 2.1)])
    return finish_object("Shaft", bm, mat, "Dual-Spool Central Shaft", explode_dy=0.0)

def build_casing(mat):
    bm = bmesh.new()
    outer = [(1.82, -2.9), (1.95, -2.7), (2.00, -2.1), (1.98, -1.2), (1.82, 0.8), (1.56, 1.8), (1.32, 2.7), (1.20, 3.2)]
    inner = [(r - 0.08, y) for (r, y) in outer]
    lathe(bm, outer + inner[::-1], closed_profile=True)
    return finish_object("Casing", bm, mat, "Bypass Duct Casing", explode_dz=1.45, is_shell=True)

def build_nozzle(mat):
    bm = bmesh.new()
    lathe(bm, [(1.02, 3.2), (0.92, 3.6), (0.78, 4.1), (0.72, 4.1), (0.85, 3.6), (0.95, 3.2)], closed_profile=True)
    lathe(bm, [(0.0, 4.25), (0.20, 3.8), (0.38, 3.3), (0.42, 3.2), (0.0, 3.2)])
    return finish_object("Nozzle", bm, mat, "Articulated 3D TVC Nozzle", explode_dy=1.25)

def build_gearbox(mat):
    bm = bmesh.new()
    disc(bm, 0.0, 0.35, -0.9, -0.3)
    return finish_object("Gearbox", bm, mat, "Accessory Gearbox Drive", explode_dy=-0.4, explode_dz=-0.5)

def export_glb(path):
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_extras=True)

def main():
    clear_scene()
    bpy.context.scene.unit_settings.system = "METRIC"
    mats = {
        "Fan": make_material("Mat_Fan_HD", (0.74, 0.76, 0.82), 0.9, 0.22),
        "Casing": make_material("Mat_Casing_HD", (0.42, 0.45, 0.48), 0.5, 0.40),
        "Compressor": make_material("Mat_Compressor_HD", (0.62, 0.65, 0.70), 0.9, 0.28),
        "Combustor": make_material("Mat_Combustor_HD", (0.58, 0.48, 0.38), 0.75, 0.42),
        "Turbine": make_material("Mat_Turbine_HD", (0.52, 0.54, 0.58), 0.9, 0.28),
        "Shaft": make_material("Mat_Shaft_HD", (0.82, 0.84, 0.86), 1.0, 0.18),
        "Nozzle": make_material("Mat_Nozzle_HD", (0.45, 0.42, 0.40), 0.85, 0.35),
    }
    objs = [
        build_fan(mats["Fan"]),
        build_intermediate_casing(mats["Casing"]),
        build_compressor(mats["Compressor"]),
        build_combustor(mats["Combustor"]),
        build_turbine(mats["Turbine"]),
        build_shaft(mats["Shaft"]),
        build_casing(mats["Casing"]),
        build_nozzle(mats["Nozzle"]),
        build_gearbox(mats["Casing"]),
    ]
    root = bpy.data.objects.new("VAJRA_AL31FP_Detailed", None)
    bpy.context.collection.objects.link(root)
    for o in objs:
        o.parent = root
        
    glb_path = os.path.join(OUTPUT_DIR, GLB_NAME)
    blend_path = os.path.join(OUTPUT_DIR, BLEND_NAME)
    export_glb(glb_path)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Exported detailed turbofan engine to {glb_path} with {len(objs)} modules")

if __name__ == "__main__":
    main()
