"""
VAJRA - Full Aircraft Engineering Digital Twin Generator for Blender
High-Fidelity IAF Su-30MKI Twin-Engine Fighter Assembly with Logical Structure.

Key Engineering Features:
- Coherent, recognizable aerodynamic exterior in Normal mode.
- Internal structural framework (zinc-chromate bulkheads, carry-through bridge, wing spars, and ribs).
- Real AL-31FP turbofan engine geometry placed inside nacelles with titanium trunnion mounts.
- Logically grouped, assembly-aware exploded coordinates along 3D vectors (dx, dy, dz).
  Wings, spars, ribs, and flaperons move together laterally without detached or scattered strips.
- Zero unwanted movement: all spin_axis values disabled.
- Full custom metadata matching VAJRA Airframe specification.
"""
import bpy
import bmesh
import math
import os
from mathutils import Vector, Matrix

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
GLB_NAME = "vajra_aircraft_twin.glb"
BLEND_NAME = "vajra_aircraft_twin.blend"

def clear_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials):
        for item in list(block):
            if item.users == 0:
                block.remove(item)

def make_pbr_material(name, rgb, metallic=0.35, roughness=0.45, alpha=1.0, transmission=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha
        if transmission > 0.0 and "Transmission Weight" in bsdf.inputs:
            bsdf.inputs["Transmission Weight"].default_value = transmission
        elif transmission > 0.0 and "Transmission" in bsdf.inputs:
            bsdf.inputs["Transmission"].default_value = transmission
    mat.diffuse_color = (*rgb, alpha)
    if alpha < 1.0 or transmission > 0.0:
        mat.blend_method = 'BLEND'
    return mat

def finish_mesh_object(name, bm, material, component_title,
                       explode_dx=0.0, explode_dy=0.0, explode_dz=0.0,
                       is_internal=False, is_shell=False, smooth=True):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    if smooth:
        for poly in mesh.polygons:
            poly.use_smooth = True
            
    if material:
        mesh.materials.append(material)
        
    obj["vajra_component"] = component_title
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
    obj["is_internal"] = bool(is_internal)
    obj["is_shell"] = bool(is_shell)
    return obj

def add_box(bm, center, size):
    cx, cy, cz = center
    sx, sy, sz = [s / 2.0 for s in size]
    pts = [
        bm.verts.new((cx - sx, cy - sy, cz - sz)),
        bm.verts.new((cx + sx, cy - sy, cz - sz)),
        bm.verts.new((cx + sx, cy + sy, cz - sz)),
        bm.verts.new((cx - sx, cy + sy, cz - sz)),
        bm.verts.new((cx - sx, cy - sy, cz + sz)),
        bm.verts.new((cx + sx, cy - sy, cz + sz)),
        bm.verts.new((cx + sx, cy + sy, cz + sz)),
        bm.verts.new((cx - sx, cy + sy, cz + sz)),
    ]
    quads = [
        (0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
        (2, 6, 7, 3), (0, 3, 7, 4), (1, 5, 6, 2)
    ]
    for q in quads:
        try:
            bm.faces.new([pts[i] for i in q])
        except ValueError:
            pass

def add_oriented_box(bm, p1, p2, width, height):
    """Creates a beam box precisely oriented along vector p2 - p1."""
    v1 = Vector(p1)
    v2 = Vector(p2)
    axis = v2 - v1
    length = axis.length
    if length < 1e-5:
        return
    z_dir = axis.normalized()
    up = Vector((0, 0, 1))
    if abs(z_dir.dot(up)) > 0.95:
        up = Vector((0, 1, 0))
    x_dir = z_dir.cross(up).normalized()
    y_dir = z_dir.cross(x_dir).normalized()
    
    hw = width / 2.0
    hh = height / 2.0
    
    c_start = [
        v1 - x_dir * hw - y_dir * hh,
        v1 + x_dir * hw - y_dir * hh,
        v1 + x_dir * hw + y_dir * hh,
        v1 - x_dir * hw + y_dir * hh,
    ]
    c_end = [
        v2 - x_dir * hw - y_dir * hh,
        v2 + x_dir * hw - y_dir * hh,
        v2 + x_dir * hw + y_dir * hh,
        v2 - x_dir * hw + y_dir * hh,
    ]
    
    v_start = [bm.verts.new(p) for p in c_start]
    v_end = [bm.verts.new(p) for p in c_end]
    
    try:
        bm.faces.new(v_start[::-1])
        bm.faces.new(v_end)
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new([v_start[i], v_start[j], v_end[j], v_end[i]])
    except ValueError:
        pass

def add_cylinder(bm, p1, p2, radius, segments=16):
    v1 = Vector(p1)
    v2 = Vector(p2)
    axis = v2 - v1
    length = axis.length
    if length < 1e-5:
        return
    z_dir = axis.normalized()
    up = Vector((0, 0, 1))
    if abs(z_dir.dot(up)) > 0.95:
        up = Vector((0, 1, 0))
    x_dir = z_dir.cross(up).normalized()
    y_dir = z_dir.cross(x_dir).normalized()
    
    r1, r2 = [], []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        ca, sa = math.cos(a) * radius, math.sin(a) * radius
        offset = x_dir * ca + y_dir * sa
        r1.append(bm.verts.new(v1 + offset))
        r2.append(bm.verts.new(v2 + offset))
        
    for i in range(segments):
        j = (i + 1) % segments
        try:
            bm.faces.new([r1[i], r1[j], r2[j], r2[i]])
        except ValueError:
            pass
    try:
        bm.faces.new(r1[::-1])
        bm.faces.new(r2)
    except ValueError:
        pass

# -----------------------------------------------------------------------------
# 1. Outer Airframe
# -----------------------------------------------------------------------------
def build_radome(mat):
    bm = bmesh.new()
    slices = 16
    segments = 24
    rings = []
    for s in range(slices):
        t = s / float(slices - 1)
        y = -10.8 + t * (-7.6 - (-10.8))
        r = math.sin(t * math.pi / 2.0) * 0.92
        z_droop = -0.32 * math.cos(t * math.pi / 2.0)
        ring = []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            rx = r * math.cos(a)
            rz = r * 0.95 * math.sin(a) + z_droop
            ring.append(bm.verts.new((rx, y, rz)))
        rings.append(ring)
        
    for s in range(slices - 1):
        for i in range(segments):
            j = (i + 1) % segments
            bm.faces.new((rings[s][i], rings[s][j], rings[s+1][j], rings[s+1][i]))
            
    # Pitot probe & vanes
    add_cylinder(bm, (0, -10.8, -0.32), (0, -12.4, -0.35), radius=0.035, segments=12)
    for ang in (0, 90, 180, 270):
        rad = math.radians(ang)
        dx = math.cos(rad) * 0.12
        dz = math.sin(rad) * 0.12
        add_box(bm, (dx, -11.4, -0.33 + dz), (0.02, 0.4, 0.08))
        
    # OLS-30 IRST sensor sphere
    add_cylinder(bm, (0.34, -7.9, 0.46), (0.34, -7.4, 0.42), radius=0.18, segments=16)
    return finish_mesh_object("Radome", bm, mat, "Radome & OLS-30 IRST", explode_dy=-1.5, is_shell=True)

def build_cockpit_canopy(mat):
    bm = bmesh.new()
    slices = 18
    segments = 24
    rings = []
    for s in range(slices):
        t = s / float(slices - 1)
        y = -7.2 + t * (-2.6 - (-7.2))
        w = math.sin(t * math.pi) * 0.68 + 0.12
        h = math.sin(t * math.pi) * 0.52 + 0.08
        z_base = 0.40 + math.sin(t * math.pi * 0.8) * 0.28
        ring = []
        for i in range(segments // 2 + 1):
            a = math.pi * i / float(segments // 2)
            rx = math.cos(a) * w
            rz = z_base + math.sin(a) * h
            ring.append(bm.verts.new((rx, y, rz)))
        rings.append(ring)
        
    for s in range(slices - 1):
        for i in range(len(rings[0]) - 1):
            bm.faces.new((rings[s][i], rings[s][i+1], rings[s+1][i+1], rings[s+1][i]))
            
    # Canopy structural arches
    for y_arch in (-5.8, -4.2):
        add_cylinder(bm, (-0.68, y_arch, 0.42), (0.68, y_arch, 0.42), radius=0.04, segments=12)
    return finish_mesh_object("Cockpit_Canopy", bm, mat, "Tandem Cockpit Canopy", explode_dz=0.8, is_shell=True)

def build_cockpit_interior(mat):
    bm = bmesh.new()
    add_box(bm, (0, -4.9, 0.22), (0.92, 4.4, 0.35))
    for y_seat, z_seat in [(-6.1, 0.45), (-4.1, 0.65)]:
        add_box(bm, (0, y_seat, z_seat), (0.50, 0.50, 0.12))
        add_box(bm, (0, y_seat + 0.24, z_seat + 0.45), (0.45, 0.14, 0.82))
        add_box(bm, (0, y_seat + 0.26, z_seat + 0.95), (0.35, 0.18, 0.22))
        add_box(bm, (0, y_seat - 0.40, z_seat + 0.28), (0.46, 0.32, 0.35))
    add_box(bm, (0, -6.65, 0.90), (0.24, 0.06, 0.22))
    return finish_mesh_object("Cockpit_Interior", bm, mat, "Cockpit Interior & Ejection Seats", is_internal=True)

def build_fuselage(mat):
    bm = bmesh.new()
    stations = [
        (-7.6, 0.92, 0.85, -0.05),
        (-6.2, 1.25, 0.95, 0.02),
        (-4.4, 1.55, 1.05, 0.08),
        (-2.2, 1.85, 1.08, 0.10),
        (0.0, 1.95, 1.02, 0.08),
        (2.2, 1.90, 0.96, 0.05),
        (4.4, 1.70, 0.88, 0.02),
        (6.5, 1.35, 0.70, -0.02),
        (8.5, 0.65, 0.45, -0.08),
        (10.2, 0.25, 0.22, -0.12),
    ]
    segments = 24
    rings = []
    for (y, hw, hh, z_center) in stations:
        ring = []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            x = math.cos(a) * hw
            z = z_center + math.sin(a) * hh
            ring.append(bm.verts.new((x, y, z)))
        rings.append(ring)
        
    for s in range(len(stations) - 1):
        for i in range(segments):
            j = (i + 1) % segments
            bm.faces.new((rings[s][i], rings[s][j], rings[s+1][j], rings[s+1][i]))
            
    # LERX chines
    for sgn in (-1.0, 1.0):
        p1 = (0.92 * sgn, -6.8, 0.05)
        p2 = (1.85 * sgn, -2.2, 0.12)
        p3 = (1.95 * sgn, 0.0, 0.10)
        add_oriented_box(bm, p1, p2, width=0.18, height=0.08)
        add_oriented_box(bm, p2, p3, width=0.22, height=0.08)
        
    # Dorsal spine tunnel & tail sting boom
    add_box(bm, (0, 0.5, 1.15), (0.75, 7.5, 0.28))
    add_cylinder(bm, (0, 6.5, 0.15), (0, 10.4, -0.10), radius=0.32, segments=16)
    return finish_mesh_object("Fuselage", bm, mat, "Main Lifting Fuselage & Spine", is_shell=True)

def build_wing(mat, side="Port"):
    bm = bmesh.new()
    sgn = -1.0 if side == "Port" else 1.0
    
    n_spans = 10
    n_chord = 16
    station_rings = []
    
    for s in range(n_spans):
        t = s / float(n_spans - 1)
        x = (1.75 + t * (7.35 - 1.75)) * sgn
        y_le = -1.5 + t * (3.3 - (-1.5))
        y_te = 4.4 + t * (4.5 - 4.4)
        chord = y_te - y_le
        thick = 0.38 * (1.0 - t * 0.60)
        z_camber = 0.04 + t * 0.08
        
        ring = []
        for i in range(n_chord):
            ct = i / float(n_chord - 1)
            y = y_le + ct * chord
            z = z_camber + math.sin(ct * math.pi) * (thick / 2.0)
            ring.append(bm.verts.new((x, y, z)))
        for i in range(n_chord - 2, 0, -1):
            ct = i / float(n_chord - 1)
            y = y_le + ct * chord
            z = z_camber - math.sin(ct * math.pi) * (thick / 2.0)
            ring.append(bm.verts.new((x, y, z)))
        station_rings.append(ring)
        
    n_pts = len(station_rings[0])
    for s in range(n_spans - 1):
        r1 = station_rings[s]
        r2 = station_rings[s + 1]
        for i in range(n_pts):
            j = (i + 1) % n_pts
            if sgn < 0:
                bm.faces.new((r1[i], r1[j], r2[j], r2[i]))
            else:
                bm.faces.new((r1[j], r1[i], r2[i], r2[j]))
                
    # Wingtip ECM pod
    tip_x = 7.45 * sgn
    add_cylinder(bm, (tip_x, 1.8, 0.12), (tip_x, 5.0, 0.12), radius=0.14, segments=16)
    
    # 4 Underwing weapons pylons
    for px, py, pz in [(3.0 * sgn, 1.0, -0.30), (4.4 * sgn, 2.0, -0.26), (5.8 * sgn, 2.8, -0.22), (7.0 * sgn, 3.5, -0.18)]:
        add_box(bm, (px, py, pz), (0.08, 1.2, 0.22))
        
    return finish_mesh_object(f"Wing_{side}", bm, mat, f"{side} Wing & Pylons", explode_dx=1.8 * sgn, is_shell=True)

def build_flaperon(mat, side="Port"):
    bm = bmesh.new()
    sgn = -1.0 if side == "Port" else 1.0
    add_box(bm, (3.2 * sgn, 4.6, 0.02), (2.4, 0.55, 0.08))
    add_box(bm, (6.0 * sgn, 4.6, 0.08), (2.2, 0.45, 0.06))
    for fx in (2.6, 4.2, 5.8):
        add_cylinder(bm, (fx * sgn, 4.1, -0.12), (fx * sgn, 4.8, -0.08), radius=0.08, segments=12)
    return finish_mesh_object(f"Flaperon_{side}", bm, mat, f"{side} Trailing-Edge Flaperon", explode_dx=1.8 * sgn, explode_dy=0.35, is_shell=True)

def build_canard(mat, side="Port"):
    bm = bmesh.new()
    sgn = -1.0 if side == "Port" else 1.0
    root = (1.55 * sgn, -4.4, 0.12)
    tip = (3.25 * sgn, -3.2, 0.22)
    add_box(bm, ((root[0] + tip[0]) / 2.0, (root[1] + tip[1]) / 2.0, 0.17), (1.8, 1.2, 0.09))
    add_cylinder(bm, (1.2 * sgn, -3.8, 0.15), (1.8 * sgn, -3.8, 0.15), radius=0.08, segments=12)
    return finish_mesh_object(f"Canard_{side}", bm, mat, f"{side} Active Canard Foreplane", explode_dx=0.8 * sgn, explode_dy=-0.3, is_shell=True)

def build_horizontal_stabilizer(mat, side="Port"):
    bm = bmesh.new()
    sgn = -1.0 if side == "Port" else 1.0
    root = (2.2 * sgn, 5.2, -0.15)
    tip = (4.6 * sgn, 7.8, -0.22)
    add_box(bm, ((root[0] + tip[0]) / 2.0, (root[1] + tip[1]) / 2.0, -0.18), (2.5, 2.2, 0.10))
    add_cylinder(bm, (1.8 * sgn, 6.2, -0.16), (2.4 * sgn, 6.2, -0.16), radius=0.10, segments=12)
    return finish_mesh_object(f"Horizontal_Stabilizer_{side}", bm, mat, f"{side} All-Moving Stabilator", explode_dx=0.9 * sgn, explode_dy=0.5, is_shell=True)

def build_vertical_stabilizer(mat, side="Port"):
    bm = bmesh.new()
    sgn = -1.0 if side == "Port" else 1.0
    cant = math.radians(7.0 * sgn)
    height = 3.8
    n_z = 8
    n_chord = 10
    fin_rings = []
    
    for s in range(n_z):
        t = s / float(n_z - 1)
        z = 0.5 + t * height
        y_le = 2.4 + t * 2.2
        y_te = 5.8 + t * 0.4
        chord = y_te - y_le
        thick = 0.20 * (1.0 - t * 0.55)
        x_center = (1.9 + math.sin(cant) * (z - 0.5)) * sgn
        
        ring = []
        for i in range(n_chord):
            ct = i / float(n_chord - 1)
            y = y_le + ct * chord
            dx = math.sin(ct * math.pi) * (thick / 2.0)
            ring.append(bm.verts.new((x_center + dx, y, z)))
        for i in range(n_chord - 2, 0, -1):
            ct = i / float(n_chord - 1)
            y = y_le + ct * chord
            dx = -math.sin(ct * math.pi) * (thick / 2.0)
            ring.append(bm.verts.new((x_center + dx, y, z)))
        fin_rings.append(ring)
        
    n_pts = len(fin_rings[0])
    for s in range(n_z - 1):
        r1 = fin_rings[s]
        r2 = fin_rings[s + 1]
        for i in range(n_pts):
            j = (i + 1) % n_pts
            if sgn < 0:
                bm.faces.new((r1[i], r1[j], r2[j], r2[i]))
            else:
                bm.faces.new((r1[j], r1[i], r2[i], r2[j]))
                
    tip_z = 0.5 + height
    tip_x = (1.9 + math.sin(cant) * height) * sgn
    add_cylinder(bm, (tip_x, 4.0, tip_z), (tip_x, 6.4, tip_z), radius=0.12, segments=16)
    add_box(bm, (tip_x - 0.15 * sgn, 2.2, 0.75), (0.14, 0.60, 0.22))
    return finish_mesh_object(f"Vertical_Stabilizer_{side}", bm, mat, f"{side} Canted Vertical Fin", explode_dx=0.6 * sgn, explode_dz=0.7, is_shell=True)

def build_rudder(mat, side="Port"):
    bm = bmesh.new()
    sgn = -1.0 if side == "Port" else 1.0
    cant = math.radians(7.0 * sgn)
    for h in range(4):
        z = 1.0 + h * 0.8
        x = (1.9 + math.sin(cant) * (z - 0.5)) * sgn
        y = 5.7 + h * 0.1
        add_box(bm, (x, y, z), (0.12, 0.75, 0.70))
    return finish_mesh_object(f"Rudder_{side}", bm, mat, f"{side} Directional Rudder", explode_dx=0.6 * sgn, explode_dy=0.4, explode_dz=0.7, is_shell=True)

def build_intake(mat, side="Port"):
    bm = bmesh.new()
    sgn = -1.0 if side == "Port" else 1.0
    cx = 1.55 * sgn
    add_box(bm, (cx, -1.0, -1.05), (1.45, 3.2, 0.90))
    add_box(bm, (cx, -2.6, -0.62), (1.50, 0.6, 0.08))
    add_cylinder(bm, (cx, -2.4, -1.05), (cx, 1.2, -0.85), radius=0.62, segments=24)
    return finish_mesh_object(f"Intake_{side}", bm, mat, f"{side} 2D Supersonic Intake", explode_dx=0.3 * sgn, explode_dz=-0.5, is_shell=True)

def build_nose_gear(mat):
    bm = bmesh.new()
    y_gear = -6.2
    add_cylinder(bm, (0, y_gear, 0.1), (0, y_gear + 0.2, -1.75), radius=0.08, segments=16)
    add_cylinder(bm, (-0.32, y_gear + 0.2, -1.75), (0.32, y_gear + 0.2, -1.75), radius=0.05, segments=12)
    for wx in (-0.26, 0.26):
        add_cylinder(bm, (wx - 0.06, y_gear + 0.2, -1.75), (wx + 0.06, y_gear + 0.2, -1.75), radius=0.34, segments=24)
    add_box(bm, (0, y_gear + 0.48, -1.65), (0.64, 0.08, 0.40))
    add_box(bm, (0.32, y_gear - 0.4, -0.35), (0.04, 1.4, 0.60))
    return finish_mesh_object("Nose_Gear", bm, mat, "Steerable Twin Nose Gear", explode_dy=-0.2, explode_dz=-0.6, is_internal=False)

def build_main_gear(mat, side="Port"):
    bm = bmesh.new()
    sgn = -1.0 if side == "Port" else 1.0
    gx = 2.45 * sgn
    gy = 2.4
    add_cylinder(bm, (1.65 * sgn, gy - 0.4, -0.1), (gx, gy, -1.85), radius=0.12, segments=16)
    add_cylinder(bm, (1.4 * sgn, gy + 0.6, 0.0), (gx - 0.3 * sgn, gy, -1.0), radius=0.06, segments=12)
    add_cylinder(bm, (gx - 0.14 * sgn, gy, -1.85), (gx + 0.14 * sgn, gy, -1.85), radius=0.52, segments=28)
    add_box(bm, (1.8 * sgn, gy, -0.45), (0.05, 1.8, 0.75))
    return finish_mesh_object(f"Main_Gear_{side}", bm, mat, f"{side} Main Landing Gear & Brakes", explode_dx=0.5 * sgn, explode_dz=-0.6, is_internal=False)

# -----------------------------------------------------------------------------
# 2. Internal Structure (Zinc-Chromate Structural Green / Titanium)
# -----------------------------------------------------------------------------
def build_fuselage_frames(mat):
    bm = bmesh.new()
    y_stations = [-7.4, -6.0, -4.5, -3.0, -1.5, 0.0, 1.5, 3.0, 4.5, 6.0, 7.5, 9.0]
    for y in y_stations:
        t = (y - (-7.4)) / (9.0 - (-7.4))
        hw = 0.95 + math.sin(t * math.pi) * 0.95
        hh = 0.65 + math.sin(t * math.pi) * 0.42
        zc = 0.05 * math.sin(t * math.pi)
        
        segments = 20
        outer, inner = [], []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            x = math.cos(a) * hw
            z = zc + math.sin(a) * hh
            outer.append(bm.verts.new((x, y, z)))
            inner.append(bm.verts.new((x * 0.88, y, zc + (z - zc) * 0.86)))
            
        for i in range(segments):
            j = (i + 1) % segments
            bm.faces.new((outer[i], outer[j], inner[j], inner[i]))
            
        add_oriented_box(bm, (-hw * 0.88, y, zc), (hw * 0.88, y, zc), width=0.04, height=0.08)
        add_oriented_box(bm, (0, y, zc - hh * 0.86), (0, y, zc + hh * 0.86), width=0.04, height=0.08)
        
    # Central fuselage carry-through spar boxes
    add_oriented_box(bm, (-1.8, -0.6, 0.04), (1.8, -0.6, 0.04), width=0.06, height=0.22)
    add_oriented_box(bm, (-1.8, 4.0, 0.02), (1.8, 4.0, 0.02), width=0.06, height=0.20)
    return finish_mesh_object("Fuselage_Frames", bm, mat, "Fuselage Longitudinal Frames & Bulkheads", is_internal=True)

def build_wing_spars(mat, side="Port"):
    bm = bmesh.new()
    sgn = -1.0 if side == "Port" else 1.0
    # Front Spar (swept 42°)
    p_front_root = (1.8 * sgn, -0.6, 0.04)
    p_front_tip = (7.1 * sgn, 3.3, 0.08)
    add_oriented_box(bm, p_front_root, p_front_tip, width=0.04, height=0.18)
    
    # Rear Spar
    p_rear_root = (1.8 * sgn, 4.0, 0.02)
    p_rear_tip = (7.0 * sgn, 4.25, 0.06)
    add_oriented_box(bm, p_rear_root, p_rear_tip, width=0.04, height=0.15)
    return finish_mesh_object(f"Wing_Spars_{side}", bm, mat, f"{side} Wing Spars (Front & Rear I-Beams)", explode_dx=1.8 * sgn, is_internal=True)

def build_wing_ribs(mat, side="Port"):
    bm = bmesh.new()
    sgn = -1.0 if side == "Port" else 1.0
    for r in range(8):
        t = (r + 1) / 9.0
        x = (1.8 + t * (7.0 - 1.8)) * sgn
        y_front = -0.5 + t * (3.2 - (-0.5))
        y_rear = 3.9 + t * (4.2 - 3.9)
        height = 0.20 * (1.0 - t * 0.60)
        add_oriented_box(bm, (x, y_front, 0.04), (x, y_rear, 0.04), width=0.03, height=height)
    return finish_mesh_object(f"Wing_Ribs_{side}", bm, mat, f"{side} Wing Chordwise Rib Assembly (8 Ribs)", explode_dx=1.8 * sgn, is_internal=True)

def build_engine_mounts(mat):
    bm = bmesh.new()
    for sgn in (-1.0, 1.0):
        ex = 1.55 * sgn
        add_cylinder(bm, (ex, 1.8, -0.85), (ex - 0.45 * sgn, 1.8, 0.1), radius=0.045, segments=12)
        add_cylinder(bm, (ex, 1.8, -0.85), (ex + 0.45 * sgn, 1.8, 0.1), radius=0.045, segments=12)
        add_cylinder(bm, (ex, 1.8, -0.85), (ex, 1.8, 0.45), radius=0.05, segments=12)
        add_cylinder(bm, (ex - 0.4 * sgn, 5.2, -0.85), (ex - 0.2 * sgn, 3.8, 0.2), radius=0.065, segments=16)
        add_cylinder(bm, (ex + 0.4 * sgn, 5.2, -0.85), (ex + 0.2 * sgn, 3.8, 0.2), radius=0.065, segments=16)
        add_cylinder(bm, (ex, 1.75, -0.85), (ex, 1.90, -0.85), radius=0.68, segments=24)
        add_cylinder(bm, (ex, 5.15, -0.85), (ex, 5.30, -0.85), radius=0.64, segments=24)
    return finish_mesh_object("Engine_Mounts", bm, mat, "Titanium Engine Mounts & Thrust Links", explode_dy=0.2, explode_dz=-0.2, is_internal=True)

# -----------------------------------------------------------------------------
# 3. Internal Systems (Avionics, Fuel, Hydraulics, Electrical)
# -----------------------------------------------------------------------------
def build_avionics_bay(mat):
    bm = bmesh.new()
    add_box(bm, (0.0, -7.5, -0.15), (0.95, 1.4, 0.55))
    lru_offsets = [
        (-0.25, -7.8, 0.0), (0.25, -7.8, 0.0), (-0.25, -7.4, 0.0), (0.25, -7.4, 0.0),
        (-0.25, -7.8, -0.22), (0.25, -7.8, -0.22), (-0.25, -7.4, -0.22), (0.25, -7.4, -0.22),
    ]
    for lx, ly, lz in lru_offsets:
        add_box(bm, (lx, ly, lz), (0.35, 0.32, 0.18))
        add_box(bm, (lx, ly - 0.17, lz), (0.30, 0.02, 0.14))
    return finish_mesh_object("Avionics_Bay", bm, mat, "Forward Avionics Bay & Mission Computers", explode_dy=-0.4, explode_dz=-0.5, is_internal=True)

def build_fuel_system(mat):
    bm = bmesh.new()
    add_box(bm, (0, -3.2, 0.25), (1.4, 2.0, 0.65))
    add_box(bm, (0, 0.8, 0.45), (1.5, 4.2, 0.55))
    add_box(bm, (0, 4.2, 0.10), (1.1, 2.8, 0.45))
    for sgn in (-1.0, 1.0):
        add_cylinder(bm, (0, -2.5, 0.0), (1.2 * sgn, 1.2, -0.4), radius=0.04, segments=12)
        add_cylinder(bm, (1.2 * sgn, 1.2, -0.4), (1.55 * sgn, 2.0, -0.8), radius=0.04, segments=12)
        add_box(bm, (1.2 * sgn, 1.2, -0.4), (0.16, 0.16, 0.16))
    return finish_mesh_object("Fuel_System", bm, mat, "Conformal Fuel Cells & Boost Pumps", explode_dz=0.3, is_internal=True)

def build_hydraulic_system(mat):
    bm = bmesh.new()
    for sgn in (-1.0, 1.0):
        hx = 0.55 * sgn
        add_cylinder(bm, (hx, -1.8, 0.35), (hx, -0.6, 0.35), radius=0.12, segments=16)
        add_box(bm, (hx, -0.4, 0.35), (0.18, 0.18, 0.18))
        add_cylinder(bm, (hx, -0.3, 0.35), (1.5 * sgn, 4.2, 0.05), radius=0.025, segments=10)
        add_cylinder(bm, (hx, -0.3, 0.35), (0.2 * sgn, 6.5, -0.1), radius=0.025, segments=10)
        add_cylinder(bm, (hx, -1.8, 0.35), (1.2 * sgn, -4.0, 0.15), radius=0.025, segments=10)
    return finish_mesh_object("Hydraulic_System", bm, mat, "280-Bar Dual Hydraulic System & Lines", explode_dz=0.2, is_internal=True)

def build_electrical_system(mat):
    bm = bmesh.new()
    add_box(bm, (0, -2.0, -0.15), (0.7, 0.8, 0.28))
    add_box(bm, (-0.25, -2.8, -0.12), (0.22, 0.35, 0.20))
    add_box(bm, (0.25, -2.8, -0.12), (0.22, 0.35, 0.20))
    for sgn in (-1.0, 1.0):
        add_cylinder(bm, (0.15 * sgn, -2.0, 0.55), (0.35 * sgn, 5.5, 0.55), radius=0.035, segments=12)
        add_cylinder(bm, (0.35 * sgn, 2.0, 0.55), (3.5 * sgn, 3.0, 0.10), radius=0.025, segments=10)
    return finish_mesh_object("Electrical_System", bm, mat, "Electrical Distribution & Harness Looms", explode_dz=0.25, is_internal=True)

# -----------------------------------------------------------------------------
# 4. Propulsion (Port & Starboard Coherent Turbofan Assemblies)
# -----------------------------------------------------------------------------
def build_engine_assembly(mat_metal, mat_comb, side="Port"):
    bm = bmesh.new()
    sgn = -1.0 if side == "Port" else 1.0
    cx = 1.55 * sgn
    cz = -0.85
    
    # Fan spinner & blades
    y_fan = 1.35
    add_cylinder(bm, (cx, y_fan - 0.45, cz), (cx, y_fan, cz), radius=0.22, segments=16)
    n_blades = 22
    for b in range(n_blades):
        ang = 2 * math.pi * b / n_blades
        bx = cx + math.cos(ang) * 0.42
        bz = cz + math.sin(ang) * 0.42
        add_box(bm, (bx, y_fan, bz), (0.04, 0.14, 0.45))
        
    # Compressor drum & 6 rotor stages
    for s in range(6):
        y_c = 1.65 + s * 0.22
        r_disc = 0.52 - s * 0.025
        add_cylinder(bm, (cx, y_c - 0.04, cz), (cx, y_c + 0.04, cz), radius=r_disc, segments=20)
        for b in range(16):
            ang = 2 * math.pi * b / 16 + s * 0.2
            bx = cx + math.cos(ang) * (r_disc + 0.05)
            bz = cz + math.sin(ang) * (r_disc + 0.05)
            add_box(bm, (bx, y_c, bz), (0.025, 0.06, 0.12))
            
    # Combustor & 12 fuel nozzles
    add_cylinder(bm, (cx, 3.0, cz), (cx, 3.8, cz), radius=0.50, segments=24)
    for inj in range(12):
        ang = 2 * math.pi * inj / 12
        ix = cx + math.cos(ang) * 0.54
        iz = cz + math.sin(ang) * 0.54
        add_box(bm, (ix, 3.4, iz), (0.05, 0.12, 0.05))
        
    # Turbine: HPT + LPT stages
    for t in range(4):
        y_t = 4.05 + t * 0.22
        r_turb = 0.48 + t * 0.02
        add_cylinder(bm, (cx, y_t - 0.04, cz), (cx, y_t + 0.04, cz), radius=r_turb, segments=20)
        for b in range(16):
            ang = 2 * math.pi * b / 16 - t * 0.15
            bx = cx + math.cos(ang) * (r_turb + 0.04)
            bz = cz + math.sin(ang) * (r_turb + 0.04)
            add_box(bm, (bx, y_t, bz), (0.025, 0.06, 0.10))
            
    # Central shaft & afterburner duct
    add_cylinder(bm, (cx, 1.2, cz), (cx, 5.0, cz), radius=0.09, segments=16)
    add_cylinder(bm, (cx, 5.0, cz), (cx, 6.8, cz), radius=0.55, segments=24)
    add_cylinder(bm, (cx, 5.4, cz), (cx, 5.5, cz), radius=0.45, segments=20)
    add_cylinder(bm, (cx, 5.8, cz), (cx, 5.9, cz), radius=0.35, segments=20)
    
    # TVC nozzle petals
    n_petals = 16
    for p in range(n_petals):
        ang = 2 * math.pi * p / n_petals
        px = cx + math.cos(ang) * 0.52
        pz = cz + math.sin(ang) * 0.52
        add_box(bm, (px, 7.35, pz), (0.08, 1.1, 0.03))
        
    # Outer nacelle casing
    add_cylinder(bm, (cx, 1.2, cz), (cx, 6.8, cz), radius=0.62, segments=28)
    
    comp_title = f"{side} AL-31FP Turbofan Engine (ENG-{'003' if side == 'Port' else '004'})"
    return finish_mesh_object(f"Engine_{side}", bm, mat_metal, comp_title,
                              explode_dx=0.35 * sgn, explode_dy=0.6, explode_dz=-0.35,
                              is_internal=False)

def export_gltf(filepath):
    kwargs = dict(
        filepath=filepath,
        export_format="GLB",
        use_selection=False,
        export_yup=True,
        export_extras=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    bpy.ops.export_scene.gltf(**kwargs)

def main():
    clear_scene()
    bpy.context.scene.unit_settings.system = "METRIC"
    
    mat_iaf_grey = make_pbr_material("Mat_IAF_Airframe", (0.56, 0.60, 0.64), metallic=0.35, roughness=0.42)
    mat_glass = make_pbr_material("Mat_Canopy_Glass", (0.48, 0.65, 0.74), metallic=0.10, roughness=0.15, alpha=0.35, transmission=0.85)
    mat_titanium = make_pbr_material("Mat_Titanium_Alloy", (0.35, 0.38, 0.42), metallic=0.85, roughness=0.30)
    mat_zinc = make_pbr_material("Mat_Zinc_Chromate", (0.52, 0.66, 0.35), metallic=0.40, roughness=0.50)
    mat_combustor = make_pbr_material("Mat_Combustor_Heat", (0.58, 0.48, 0.38), metallic=0.75, roughness=0.40)
    mat_avionics = make_pbr_material("Mat_Avionics_Gold", (0.83, 0.69, 0.22), metallic=0.80, roughness=0.35)
    mat_fuel = make_pbr_material("Mat_Fuel_Cell", (0.33, 0.42, 0.18), metallic=0.15, roughness=0.70)
    mat_hydraulic = make_pbr_material("Mat_Hydraulic_Red", (0.65, 0.16, 0.16), metallic=0.70, roughness=0.35)
    mat_electrical = make_pbr_material("Mat_Electrical_Copper", (0.72, 0.45, 0.20), metallic=0.85, roughness=0.25)
    mat_rubber = make_pbr_material("Mat_Rubber", (0.12, 0.12, 0.12), metallic=0.05, roughness=0.85)
    
    all_objects = [
        # Nose & Cockpit
        build_radome(mat_iaf_grey),
        build_cockpit_canopy(mat_glass),
        build_cockpit_interior(mat_titanium),
        build_avionics_bay(mat_avionics),
        build_nose_gear(mat_rubber),
        
        # Fuselage & Spine
        build_fuselage(mat_iaf_grey),
        build_fuselage_frames(mat_zinc),
        build_fuel_system(mat_fuel),
        build_hydraulic_system(mat_hydraulic),
        build_electrical_system(mat_electrical),
        
        # Port Wing Assembly (Aerodynamic Skin, Spars, Ribs, Flaperon)
        build_wing(mat_iaf_grey, "Port"),
        build_wing_spars(mat_zinc, "Port"),
        build_wing_ribs(mat_zinc, "Port"),
        build_flaperon(mat_iaf_grey, "Port"),
        build_main_gear(mat_rubber, "Port"),
        
        # Starboard Wing Assembly (Aerodynamic Skin, Spars, Ribs, Flaperon)
        build_wing(mat_iaf_grey, "Starboard"),
        build_wing_spars(mat_zinc, "Starboard"),
        build_wing_ribs(mat_zinc, "Starboard"),
        build_flaperon(mat_iaf_grey, "Starboard"),
        build_main_gear(mat_rubber, "Starboard"),
        
        # Foreplanes & Tail Flight Control Surfaces
        build_canard(mat_iaf_grey, "Port"),
        build_canard(mat_iaf_grey, "Starboard"),
        build_horizontal_stabilizer(mat_iaf_grey, "Port"),
        build_horizontal_stabilizer(mat_iaf_grey, "Starboard"),
        build_vertical_stabilizer(mat_iaf_grey, "Port"),
        build_rudder(mat_iaf_grey, "Port"),
        build_vertical_stabilizer(mat_iaf_grey, "Starboard"),
        build_rudder(mat_iaf_grey, "Starboard"),
        
        # Intakes & Propulsion Installations
        build_intake(mat_iaf_grey, "Port"),
        build_intake(mat_iaf_grey, "Starboard"),
        build_engine_mounts(mat_titanium),
        build_engine_assembly(mat_titanium, mat_combustor, "Port"),
        build_engine_assembly(mat_titanium, mat_combustor, "Starboard"),
    ]
    
    root = bpy.data.objects.new("VAJRA_Su30MKI_Digital_Twin", None)
    bpy.context.collection.objects.link(root)
    for obj in all_objects:
        obj.parent = root
        
    glb_out = os.path.join(OUTPUT_DIR, GLB_NAME)
    blend_out = os.path.join(OUTPUT_DIR, BLEND_NAME)
    
    bpy.ops.object.select_all(action="DESELECT")
    export_gltf(glb_out)
    bpy.ops.wm.save_as_mainfile(filepath=blend_out)
    print(f"Generated {glb_out} with {len(all_objects)} components")

if __name__ == "__main__":
    main()
