"""
VAJRA - Turbofan engine generator for Blender (works on Blender 3.6 / 4.x / 5.x)

HOW TO RUN (inside Blender)
  1. Open Blender -> top tab "Scripting" -> "Open" this file -> press "Run Script" (play icon).
  2. Files are written to OUTPUT_DIR (change it below).
  3. Check the system console / Info area for the "DONE" message.

HOW TO RUN (command line, no UI)
  blender --background --python build_vajra_engine.py

WHAT IT CREATES (each one a separate object, names must not change - the API and
Three.js viewer use them):
  Fan, Compressor, Combustion_Chamber, Turbine, Shaft, Casing, Nozzle

Engine axis = Blender +Y.  Fan (front) is at -Y, exhaust at +Y.
After glTF export (+Y up) the engine lies along Three.js Z, fan facing +Z (toward the
default camera).

Each object carries custom properties that end up in glTF "extras":
  vajra_component  : name used by the API (e.g. "Combustion Chamber")
  explode_offset   : distance to move in the exploded view (Blender units)
  explode_axis     : "Y" (along engine) or "Z" (lift upward) in Blender axes
  spin_axis        : "Y" if the part may be rotated for a live animation, else ""
"""
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "vajra_assets")
GLB_NAME = "vajra_engine.glb"
BLEND_NAME = "vajra_engine.blend"
USE_DRACO = False        # True makes the file smaller but the frontend then needs DRACOLoader
SEGMENTS = 64            # smoothness of round parts
# ----------------------------------------------------------------------------


def clear_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


# ---------------------------------------------------------------- geometry helpers
def lathe(bm, profile, segments=SEGMENTS, closed_profile=False):
    """Revolve a (radius, y) profile around the Y axis."""
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
                pass  # degenerate (radius 0 on both rings)
    return rings


def cap_ring(bm, ring):
    try:
        bm.faces.new(ring)
    except ValueError:
        pass


def blade(bm, angle, r_root, r_tip, y, chord, thick, pitch_deg, taper=0.6):
    """Add one tapered, pitched blade (8-vertex box) to bm."""
    u = Vector((math.cos(angle), 0, math.sin(angle)))        # radial
    t = Vector((-math.sin(angle), 0, math.cos(angle)))       # tangential
    yv = Vector((0, 1, 0))
    p = math.radians(pitch_deg)
    c_dir = yv * math.cos(p) + t * math.sin(p)               # chord direction (pitched)
    n_dir = -yv * math.sin(p) + t * math.cos(p)              # thickness direction
    verts = []
    for r, cw, th in ((r_root, chord / 2, thick / 2), (r_tip, chord / 2 * taper, thick / 2 * 0.6)):
        centre = u * r + yv * y
        for sc in (-1, 1):
            for sn in (-1, 1):
                verts.append(bm.verts.new(centre + c_dir * (cw * sc) + n_dir * (th * sn)))
    # verts: root(0..3) tip(4..7), index = sc*2+sn pattern -> (-1,-1),(-1,1),(1,-1),(1,1)
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
    """Solid ring/disc between radii r_in..r_out, axial y0..y1."""
    if r_in <= 0.001:
        rings = lathe(bm, [(0.0, y0), (r_out, y0), (r_out, y1), (0.0, y1)], segments)
        return
    lathe(bm, [(r_in, y0), (r_out, y0), (r_out, y1), (r_in, y1)], segments, closed_profile=True)


# ---------------------------------------------------------------- object helpers
def finish_object(name, bm, material, component, explode_offset, explode_axis="Y", spin=False,
                  smooth=True):
    """Turn a bmesh into an object: recalc normals, centre origin on the axis, add props."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(mesh)
    bm.free()
    # origin: on the engine axis (x=z=0) at the mid-point of the part along Y
    ys = [v.co.y for v in mesh.vertices]
    ymid = (min(ys) + max(ys)) / 2
    mesh.transform(Matrix.Translation((0, -ymid, 0)))
    obj = bpy.data.objects.new(name, mesh)
    obj.location = (0, ymid, 0)
    bpy.context.collection.objects.link(obj)
    if smooth:
        for poly in mesh.polygons:
            poly.use_smooth = True
    mesh.materials.append(material)
    obj["vajra_component"] = component
    obj["explode_offset"] = float(explode_offset)
    obj["explode_axis"] = explode_axis
    obj["spin_axis"] = "Y" if spin else ""
    return obj


def make_material(name, rgb, metallic=0.8, roughness=0.35):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    mat.diffuse_color = (*rgb, 1.0)
    return mat


# ---------------------------------------------------------------- the parts
def build_fan(mat):
    bm = bmesh.new()
    # spinner nose cone + hub
    lathe(bm, [(0.0, -2.75), (0.12, -2.68), (0.30, -2.52), (0.46, -2.30), (0.52, -2.05),
               (0.52, -1.85), (0.0, -1.85)])
    # 22 wide-chord fan blades
    blade_row(bm, 22, 0.46, 1.62, -2.18, chord=0.55, thick=0.07, pitch=32, taper=0.55)
    return finish_object("Fan", bm, mat, "Fan", explode_offset=-3.4, spin=True)


def build_compressor(mat):
    bm = bmesh.new()
    # drum
    lathe(bm, [(0.42, -1.80), (0.60, -1.55), (0.72, -0.70), (0.80, -0.05), (0.80, 0.05),
               (0.42, 0.05), (0.42, -1.80)], closed_profile=False)
    stages = 6
    for s in range(stages):
        y = -1.65 + s * 0.30
        r_tip = 0.98 - s * 0.045
        disc(bm, 0.42, 0.62 + s * 0.035, y - 0.03, y + 0.03)
        blade_row(bm, 34 + 2 * s, 0.60 + s * 0.035, r_tip, y, chord=0.17, thick=0.025,
                  pitch=24, phase=0.05 * s, taper=0.7)
    return finish_object("Compressor", bm, mat, "Compressor", explode_offset=-1.8, spin=True)


def build_combustor(mat):
    bm = bmesh.new()
    # annular liner (hollow ring, closed profile)
    lathe(bm, [(1.00, 0.20), (1.04, 0.35), (1.04, 1.25), (1.00, 1.40),
               (0.74, 1.40), (0.70, 1.25), (0.70, 0.35), (0.74, 0.20)],
          closed_profile=True)
    # six cooling ribs
    for i in range(6):
        y = 0.38 + i * 0.16
        lathe(bm, [(1.05, y), (1.10, y + 0.02), (1.10, y + 0.06), (1.05, y + 0.08)],
              closed_profile=True)
    # fuel injector stubs (12)
    for i in range(12):
        a = 2 * math.pi * i / 12
        for r_out in (0.70,):
            c = Vector((math.cos(a), 0, math.sin(a)))
            t = Vector((-math.sin(a), 0, math.cos(a)))
            base = Vector((0, 0.20, 0)) + c * 0.72
            pts = []
            for dy, w in ((0.0, 0.05), (-0.16, 0.025)):
                for sx in (-1, 1):
                    for sz in (-1, 1):
                        pts.append(bm.verts.new(base + Vector((0, dy, 0)) + t * (w * sx) + c * (w * sz)))
            for q in [(0, 1, 3, 2), (4, 6, 7, 5), (0, 2, 6, 4), (1, 5, 7, 3), (0, 4, 5, 1), (2, 3, 7, 6)]:
                try:
                    bm.faces.new([pts[k] for k in q])
                except ValueError:
                    pass
    return finish_object("Combustion_Chamber", bm, mat, "Combustion Chamber", explode_offset=0.0,
                         explode_axis="Z")


def build_turbine(mat):
    bm = bmesh.new()
    lathe(bm, [(0.40, 1.50), (0.55, 1.65), (0.62, 2.20), (0.55, 2.75), (0.42, 2.80),
               (0.40, 1.50)], closed_profile=False)
    for s in range(4):
        y = 1.70 + s * 0.28
        r_tip = 0.88 + s * 0.06
        disc(bm, 0.40, 0.58, y - 0.04, y + 0.04)
        blade_row(bm, 40 - 3 * s, 0.56, r_tip, y, chord=0.20, thick=0.03, pitch=-26,
                  phase=0.04 * s, taper=0.65)
    return finish_object("Turbine", bm, mat, "Turbine", explode_offset=2.2, spin=True)


def build_shaft(mat):
    bm = bmesh.new()
    rings = lathe(bm, [(0.0, -2.35), (0.17, -2.35), (0.17, 2.85), (0.0, 2.85)])
    # outer low-pressure shaft sleeve with splines
    lathe(bm, [(0.26, -1.9), (0.26, 1.9)], segments=SEGMENTS)
    for y in (-1.4, -0.3, 0.8, 1.9):
        lathe(bm, [(0.30, y), (0.30, y + 0.10)], segments=SEGMENTS)
    return finish_object("Shaft", bm, mat, "Shaft", explode_offset=0.0, spin=True)


def build_casing(mat):
    bm = bmesh.new()
    t = 0.07  # wall thickness
    outer = [(1.78, -2.62), (1.90, -2.50), (1.96, -2.10), (1.98, -1.50), (1.94, -0.50),
             (1.78, 0.60), (1.52, 1.60), (1.28, 2.40), (1.18, 2.85)]
    inner = [(r - t, y) for (r, y) in outer]
    profile = outer + inner[::-1]
    lathe(bm, profile, closed_profile=True)
    # core cowl (inner bypass wall around the engine core)
    core = [(1.10, -1.55), (1.10, 0.10), (1.14, 1.40), (1.08, 2.60), (1.02, 2.85)]
    core_in = [(r - 0.05, y) for (r, y) in core]
    lathe(bm, core + core_in[::-1], closed_profile=True)
    return finish_object("Casing", bm, mat, "Casing", explode_offset=3.2, explode_axis="Z")


def build_nozzle(mat):
    bm = bmesh.new()
    # outer exhaust nozzle
    lathe(bm, [(0.96, 2.85), (0.86, 3.20), (0.74, 3.55),
               (0.68, 3.55), (0.80, 3.20), (0.90, 2.85)], closed_profile=True)
    # centre plug cone
    lathe(bm, [(0.0, 3.70), (0.18, 3.35), (0.34, 2.95), (0.38, 2.85), (0.0, 2.85)])
    return finish_object("Nozzle", bm, mat, "Nozzle", explode_offset=3.6)


# ---------------------------------------------------------------- scene / export
def add_lighting_and_camera():
    bpy.ops.object.light_add(type="SUN", location=(4, -6, 8))
    bpy.context.object.data.energy = 3.0
    bpy.context.object.name = "Sun"
    bpy.ops.object.camera_add(location=(6.5, -7.5, 3.5), rotation=(math.radians(72), 0, math.radians(42)))
    bpy.context.object.name = "PreviewCamera"
    bpy.context.scene.camera = bpy.context.object


def export_glb(path):
    kwargs = dict(
        filepath=path,
        export_format="GLB",
        use_selection=False,
        export_apply_modifiers=True,
        export_yup=True,
        export_extras=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    if USE_DRACO:
        kwargs["export_draco_mesh_compression_enable"] = True
    try:
        bpy.ops.export_scene.gltf(**kwargs)
    except TypeError as err:   # property renamed in some Blender versions: retry minimal
        print("glTF option mismatch, retrying with minimal options:", err)
        bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_extras=True)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    clear_scene()
    bpy.context.scene.unit_settings.system = "METRIC"

    mats = {
        "Fan": make_material("Mat_Fan", (0.72, 0.75, 0.80), 0.9, 0.25),
        "Compressor": make_material("Mat_Compressor", (0.60, 0.64, 0.70), 0.9, 0.30),
        "Combustion_Chamber": make_material("Mat_Combustion_Chamber", (0.55, 0.50, 0.46), 0.7, 0.45),
        "Turbine": make_material("Mat_Turbine", (0.50, 0.52, 0.56), 0.9, 0.30),
        "Shaft": make_material("Mat_Shaft", (0.80, 0.82, 0.85), 1.0, 0.20),
        "Casing": make_material("Mat_Casing", (0.35, 0.40, 0.33), 0.3, 0.55),
        "Nozzle": make_material("Mat_Nozzle", (0.42, 0.40, 0.38), 0.8, 0.40),
    }
    objs = [
        build_fan(mats["Fan"]),
        build_compressor(mats["Compressor"]),
        build_combustor(mats["Combustion_Chamber"]),
        build_turbine(mats["Turbine"]),
        build_shaft(mats["Shaft"]),
        build_casing(mats["Casing"]),
        build_nozzle(mats["Nozzle"]),
    ]
    # group under one empty so the whole engine can be moved/scaled as one
    root = bpy.data.objects.new("VAJRA_Engine", None)
    bpy.context.collection.objects.link(root)
    for o in objs:
        o.parent = root

    add_lighting_and_camera()

    glb_path = os.path.join(OUTPUT_DIR, GLB_NAME)
    blend_path = os.path.join(OUTPUT_DIR, BLEND_NAME)

    # export only the engine (not light/camera)
    bpy.ops.object.select_all(action="DESELECT")
    export_glb(glb_path)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    tris = sum(len(o.data.polygons) for o in objs)   # quads count roughly x2 triangles
    size_mb = os.path.getsize(glb_path) / 1e6
    print("=" * 60)
    print("DONE - VAJRA engine generated")
    print("  parts :", ", ".join(o.name for o in objs))
    print("  faces : ~%d (about %d triangles)" % (tris, tris * 2))
    print("  GLB   : %s  (%.2f MB)" % (glb_path, size_mb))
    print("  BLEND : %s" % blend_path)
    print("=" * 60)


main()
