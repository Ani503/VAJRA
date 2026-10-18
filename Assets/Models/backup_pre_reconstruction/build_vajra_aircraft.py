"""
VAJRA - Full Aircraft Digital Twin Model Generator for Blender (Blender 3.6 / 4.x / 5.x)
Generates high-fidelity Indian Air Force Su-30MKI (Fighter-B) Airframe with modular,
individually selectable sub-assemblies and export to glTF 2.0 (vajra_aircraft.glb).

HOW TO RUN:
  /Applications/Blender.app/Contents/MacOS/Blender --background --python "Assets /Models/build_vajra_aircraft.py"

COMPONENTS CREATED (each with metadata for Three.js raycasting & exploded views):
  1. Fuselage                  : Main lifting-body airframe, nose radome, dorsal spine, aft stinger
  2. Cockpit_Avionics          : Tandem cockpit canopy, HUD, avionics sensor nose package (IRST)
  3. Wing_Port                 : Left clipped delta wing with LERX, flaperons, and wingtip rail
  4. Wing_Starboard            : Right clipped delta wing with LERX, flaperons, and wingtip rail
  5. Vertical_Stab_Port        : Left canted vertical tail fin & rudder
  6. Vertical_Stab_Starboard   : Right canted vertical tail fin & rudder
  7. Canards_Stabilators       : Active foreplane canards & twin all-moving tail stabilators
  8. Landing_Gear              : Nose twin-wheel strut & heavy main landing gear assemblies
  9. Engine_Port               : Left nacelle intake duct & AL-31FP turbofan (ENG-003)
 10. Engine_Starboard          : Right nacelle intake duct & AL-31FP turbofan (ENG-004)
"""
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = SCRIPT_DIR
GLB_NAME = "vajra_aircraft.glb"
BLEND_NAME = "vajra_aircraft.blend"
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


def make_material(name, rgb, metallic=0.75, roughness=0.35, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha
    mat.diffuse_color = (*rgb, alpha)
    if alpha < 1.0 and hasattr(mat, "blend_method"):
        try:
            mat.blend_method = "BLEND"
        except Exception:
            pass
    return mat


def finish_object(name, bm, material, component, explode_offset, explode_axis="Z", spin=False, smooth=True):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
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


# ---------------------------------------------------------------- Geometry Helpers
def add_cross_section_loft(bm, stations, segments=24):
    """
    Lofts a 3D volume through a series of (center_vector, radius_x, radius_z) stations along Y.
    stations: list of (Vector((x, y, z)), rx, rz)
    """
    rings = []
    for center, rx, rz in stations:
        ring = []
        for i in range(segments):
            theta = 2 * math.pi * i / segments
            x = center.x + rx * math.cos(theta)
            y = center.y
            z = center.z + rz * math.sin(theta)
            ring.append(bm.verts.new((x, y, z)))
        rings.append(ring)

    # Connect rings
    for k in range(len(rings) - 1):
        r0 = rings[k]
        r1 = rings[k + 1]
        for i in range(segments):
            j = (i + 1) % segments
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))

    # Cap front and back
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[-1])))
    return rings


def add_aerofoil_wing(bm, root_y, tip_y, root_x, tip_x, root_z, tip_z, root_chord, tip_chord, root_thick, tip_thick, sweep_y):
    """
    Constructs a low-drag swept trapezoidal wing volume.
    """
    def wing_rib(y_lead, x_pos, z_pos, chord, thick):
        pts = []
        steps = 14
        for i in range(steps):
            frac = i / (steps - 1)
            # NACA 4-digit style thickness envelope
            y = y_lead + frac * chord
            yt = thick * 5 * (0.2969 * math.sqrt(max(0, frac)) - 0.1260 * frac - 0.3516 * (frac ** 2) + 0.2843 * (frac ** 3) - 0.1015 * (frac ** 4))
            pts.append((x_pos, y, z_pos + yt))
        for i in reversed(range(1, steps - 1)):
            frac = i / (steps - 1)
            y = y_lead + frac * chord
            yt = thick * 5 * (0.2969 * math.sqrt(max(0, frac)) - 0.1260 * frac - 0.3516 * (frac ** 2) + 0.2843 * (frac ** 3) - 0.1015 * (frac ** 4))
            pts.append((x_pos, y, z_pos - yt))
        return [bm.verts.new(p) for p in pts]

    r_root = wing_rib(root_y, root_x, root_z, root_chord, root_thick)
    r_tip = wing_rib(tip_y + sweep_y, tip_x, tip_z, tip_chord, tip_thick)

    for i in range(len(r_root)):
        j = (i + 1) % len(r_root)
        bm.faces.new((r_root[i], r_root[j], r_tip[j], r_tip[i]))

    bm.faces.new(r_root)
    bm.faces.new(list(reversed(r_tip)))


# ---------------------------------------------------------------- Airframe Components
def build_fuselage(mat):
    bm = bmesh.new()
    # Lofted stations from Pitot probe at front (y = -9.2) to tail stinger at rear (y = 7.8)
    stations = [
        (Vector((0, -9.2, -0.1)), 0.05, 0.05),   # Pitot tip
        (Vector((0, -8.6, -0.1)), 0.35, 0.35),   # Radome front
        (Vector((0, -7.2, 0.0)), 0.72, 0.65),    # Radome bulk
        (Vector((0, -5.5, 0.15)), 0.95, 0.78),   # Forward cockpit
        (Vector((0, -3.8, 0.35)), 1.15, 0.90),   # Rear cockpit / LERX root
        (Vector((0, -1.5, 0.45)), 1.35, 0.95),   # Mid fuselage
        (Vector((0, 0.8, 0.40)), 1.45, 0.90),    # Main fuselage tunnel
        (Vector((0, 3.2, 0.35)), 1.30, 0.75),    # Engine nacelle bridge
        (Vector((0, 5.4, 0.25)), 0.95, 0.55),    # Aft tunnel
        (Vector((0, 7.2, 0.15)), 0.40, 0.28),    # Beaver tail base
        (Vector((0, 8.4, 0.10)), 0.12, 0.10),    # Stinger MAD boom tip
    ]
    add_cross_section_loft(bm, stations, segments=28)

    # Dorsal spine
    spine_stations = [
        (Vector((0, -3.2, 1.15)), 0.25, 0.20),
        (Vector((0, -0.5, 1.25)), 0.38, 0.25),
        (Vector((0, 2.5, 1.10)), 0.35, 0.22),
        (Vector((0, 4.8, 0.85)), 0.20, 0.15),
    ]
    add_cross_section_loft(bm, spine_stations, segments=16)

    return finish_object("Fuselage", bm, mat, "Fuselage", explode_offset=0.0, explode_axis="Z")


def build_cockpit(mat_glass, mat_frame):
    bm = bmesh.new()
    # Aerodynamic tandem bubble canopy
    canopy_stations = [
        (Vector((0, -6.0, 0.65)), 0.42, 0.22),
        (Vector((0, -5.0, 0.95)), 0.54, 0.42),
        (Vector((0, -3.8, 1.10)), 0.56, 0.46),
        (Vector((0, -2.5, 0.98)), 0.52, 0.38),
        (Vector((0, -1.8, 0.78)), 0.40, 0.22),
    ]
    add_cross_section_loft(bm, canopy_stations, segments=20)

    # OLS-30 IRST sensor ball on starboard forward windscreen
    irst_center = Vector((0.45, -6.2, 0.72))
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12, radius=0.18)
    for v in bm.verts[-194:]:
        v.co += irst_center

    return finish_object("Cockpit_Avionics", bm, mat_glass, "Cockpit & Avionics", explode_offset=2.4, explode_axis="Z")


def build_wing_port(mat):
    bm = bmesh.new()
    # Su-30MKI cropped delta wing with sweepback
    add_aerofoil_wing(
        bm,
        root_y=-1.8, tip_y=-0.2,
        root_x=-1.35, tip_x=-7.2,
        root_z=0.15, tip_z=0.25,
        root_chord=5.4, tip_chord=1.4,
        root_thick=0.28, tip_thick=0.08,
        sweep_y=3.2
    )
    # Wingtip missile rail pod (APU-170 / EW Pod)
    pod = [
        (Vector((-7.2, 2.2, 0.25)), 0.08, 0.08),
        (Vector((-7.2, 3.4, 0.25)), 0.12, 0.12),
        (Vector((-7.2, 5.0, 0.25)), 0.10, 0.10),
        (Vector((-7.2, 5.6, 0.25)), 0.04, 0.04),
    ]
    add_cross_section_loft(bm, pod, segments=12)

    return finish_object("Wing_Port", bm, mat, "Left Wing (Port)", explode_offset=-3.8, explode_axis="X")


def build_wing_starboard(mat):
    bm = bmesh.new()
    add_aerofoil_wing(
        bm,
        root_y=-1.8, tip_y=-0.2,
        root_x=1.35, tip_x=7.2,
        root_z=0.15, tip_z=0.25,
        root_chord=5.4, tip_chord=1.4,
        root_thick=0.28, tip_thick=0.08,
        sweep_y=3.2
    )
    pod = [
        (Vector((7.2, 2.2, 0.25)), 0.08, 0.08),
        (Vector((7.2, 3.4, 0.25)), 0.12, 0.12),
        (Vector((7.2, 5.0, 0.25)), 0.10, 0.10),
        (Vector((7.2, 5.6, 0.25)), 0.04, 0.04),
    ]
    add_cross_section_loft(bm, pod, segments=12)

    return finish_object("Wing_Starboard", bm, mat, "Right Wing (Starboard)", explode_offset=3.8, explode_axis="X")


def build_vertical_tail_port(mat):
    bm = bmesh.new()
    # Swept vertical fin canted outwards ~6 degrees
    cant_angle = math.radians(6)
    c = math.cos(cant_angle)
    s = math.sin(cant_angle)
    root_x = -1.65
    tip_x = root_x - 3.2 * s
    tip_z = 0.5 + 3.2 * c

    add_aerofoil_wing(
        bm,
        root_y=2.2, tip_y=4.0,
        root_x=root_x, tip_x=tip_x,
        root_z=0.5, tip_z=tip_z,
        root_chord=3.4, tip_chord=1.3,
        root_thick=0.18, tip_thick=0.06,
        sweep_y=1.5
    )
    # Rudder tip dielectric fairing
    fairing = [
        (Vector((tip_x, 4.4, tip_z)), 0.08, 0.08),
        (Vector((tip_x, 5.8, tip_z)), 0.10, 0.10),
        (Vector((tip_x, 6.4, tip_z)), 0.02, 0.02),
    ]
    add_cross_section_loft(bm, fairing, segments=12)

    return finish_object("Vertical_Stab_Port", bm, mat, "Port Vertical Stabilizer", explode_offset=-2.0, explode_axis="X")


def build_vertical_tail_starboard(mat):
    bm = bmesh.new()
    cant_angle = math.radians(6)
    c = math.cos(cant_angle)
    s = math.sin(cant_angle)
    root_x = 1.65
    tip_x = root_x + 3.2 * s
    tip_z = 0.5 + 3.2 * c

    add_aerofoil_wing(
        bm,
        root_y=2.2, tip_y=4.0,
        root_x=root_x, tip_x=tip_x,
        root_z=0.5, tip_z=tip_z,
        root_chord=3.4, tip_chord=1.3,
        root_thick=0.18, tip_thick=0.06,
        sweep_y=1.5
    )
    fairing = [
        (Vector((tip_x, 4.4, tip_z)), 0.08, 0.08),
        (Vector((tip_x, 5.8, tip_z)), 0.10, 0.10),
        (Vector((tip_x, 6.4, tip_z)), 0.02, 0.02),
    ]
    add_cross_section_loft(bm, fairing, segments=12)

    return finish_object("Vertical_Stab_Starboard", bm, mat, "Starboard Vertical Stabilizer", explode_offset=2.0, explode_axis="X")


def build_control_surfaces(mat):
    bm = bmesh.new()
    # Foreplane active canards near cockpit
    add_aerofoil_wing(
        bm,
        root_y=-4.0, tip_y=-3.6,
        root_x=-1.0, tip_x=-2.3,
        root_z=0.35, tip_z=0.40,
        root_chord=1.4, tip_chord=0.55,
        root_thick=0.08, tip_thick=0.03,
        sweep_y=0.4
    )
    add_aerofoil_wing(
        bm,
        root_y=-4.0, tip_y=-3.6,
        root_x=1.0, tip_x=2.3,
        root_z=0.35, tip_z=0.40,
        root_chord=1.4, tip_chord=0.55,
        root_thick=0.08, tip_thick=0.03,
        sweep_y=0.4
    )
    # Aft all-moving horizontal stabilators (tail planes)
    add_aerofoil_wing(
        bm,
        root_y=4.8, tip_y=5.8,
        root_x=-2.2, tip_x=-4.8,
        root_z=0.10, tip_z=0.05,
        root_chord=2.8, tip_chord=1.1,
        root_thick=0.12, tip_thick=0.04,
        sweep_y=1.6
    )
    add_aerofoil_wing(
        bm,
        root_y=4.8, tip_y=5.8,
        root_x=2.2, tip_x=4.8,
        root_z=0.10, tip_z=0.05,
        root_chord=2.8, tip_chord=1.1,
        root_thick=0.12, tip_thick=0.04,
        sweep_y=1.6
    )

    return finish_object("Canards_Stabilators", bm, mat, "Flight Control Surfaces", explode_offset=-2.2, explode_axis="Y")


def build_landing_gear(mat):
    bm = bmesh.new()
    # Nose gear: strut + twin wheels
    nose_strut = [
        (Vector((0, -5.2, -0.4)), 0.08, 0.08),
        (Vector((0, -5.3, -1.6)), 0.07, 0.07),
    ]
    add_cross_section_loft(bm, nose_strut, segments=12)
    # Twin nose wheels
    for side in (-0.18, 0.18):
        bmesh.ops.create_cone(bm, cap_ends=True, radius1=0.22, radius2=0.22, depth=0.10,
                              matrix=Matrix.Translation((side, -5.3, -1.6)) @ Matrix.Rotation(math.radians(90), 4, 'Y'))

    # Main gear: port and starboard heavy trailing arms
    for side in (-1.65, 1.65):
        main_strut = [
            (Vector((side, 0.8, -0.4)), 0.10, 0.10),
            (Vector((side, 1.1, -1.7)), 0.09, 0.09),
        ]
        add_cross_section_loft(bm, main_strut, segments=12)
        # Main heavy tire
        bmesh.ops.create_cone(bm, cap_ends=True, radius1=0.45, radius2=0.45, depth=0.22,
                              matrix=Matrix.Translation((side + (0.12 if side < 0 else -0.12), 1.1, -1.7)) @ Matrix.Rotation(math.radians(90), 4, 'Y'))

    return finish_object("Landing_Gear", bm, mat, "Landing Gear & Hydraulics", explode_offset=-2.5, explode_axis="Z")


def build_engine_nacelle(name, x_offset, mat_casing, mat_nozzle, component_name):
    bm = bmesh.new()
    # Air intake ramp to afterburner nozzle
    nacelle_stations = [
        (Vector((x_offset, -2.6, -0.35)), 0.62, 0.52),  # Intake scoop
        (Vector((x_offset, -1.0, -0.28)), 0.68, 0.58),  # Intake duct
        (Vector((x_offset, 1.2, -0.20)), 0.74, 0.62),   # Engine bay mid
        (Vector((x_offset, 3.4, -0.15)), 0.72, 0.60),   # Afterburner section
        (Vector((x_offset, 5.4, -0.10)), 0.66, 0.56),   # Nozzle convergent root
    ]
    add_cross_section_loft(bm, nacelle_stations, segments=24)

    # Thrust-vectoring articulated nozzle petals
    nozzle_stations = [
        (Vector((x_offset, 5.4, -0.10)), 0.65, 0.55),
        (Vector((x_offset, 6.2, -0.08)), 0.56, 0.50),
        (Vector((x_offset, 6.8, -0.06)), 0.52, 0.46),
    ]
    add_cross_section_loft(bm, nozzle_stations, segments=24)

    # Internal fan stage nose spinner visible inside intake
    spinner_stations = [
        (Vector((x_offset, -1.6, -0.30)), 0.05, 0.05),
        (Vector((x_offset, -1.0, -0.28)), 0.22, 0.22),
    ]
    add_cross_section_loft(bm, spinner_stations, segments=16)

    return finish_object(name, bm, mat_casing, component_name, explode_offset=3.5, explode_axis="Y", spin=True)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    clear_scene()
    bpy.context.scene.unit_settings.system = "METRIC"

    # Materials Palette: Indian Air Force Tactical Air Superiority Livery
    # IAF Su-30MKI distinctive dual-tone air superiority grey with titanium hot sections
    mats = {
        "Fuselage": make_material("Mat_Fuselage", (0.42, 0.47, 0.52), metallic=0.45, roughness=0.40),
        "Cockpit_Glass": make_material("Mat_Canopy", (0.15, 0.35, 0.45), metallic=0.85, roughness=0.10, alpha=0.35),
        "Cockpit_Frame": make_material("Mat_CockpitFrame", (0.22, 0.25, 0.28), metallic=0.70, roughness=0.35),
        "Wings": make_material("Mat_Wings", (0.40, 0.45, 0.50), metallic=0.45, roughness=0.40),
        "Tails": make_material("Mat_Tails", (0.38, 0.43, 0.48), metallic=0.45, roughness=0.40),
        "Controls": make_material("Mat_Controls", (0.42, 0.47, 0.52), metallic=0.50, roughness=0.35),
        "Gear": make_material("Mat_Gear", (0.18, 0.20, 0.22), metallic=0.80, roughness=0.30),
        "Engine_Port": make_material("Mat_Engine_Port", (0.32, 0.35, 0.38), metallic=0.75, roughness=0.30),
        "Engine_Starboard": make_material("Mat_Engine_Starboard", (0.32, 0.35, 0.38), metallic=0.75, roughness=0.30),
        "Nozzle": make_material("Mat_Nozzle", (0.28, 0.26, 0.24), metallic=0.90, roughness=0.25),
    }

    objs = [
        build_fuselage(mats["Fuselage"]),
        build_cockpit(mats["Cockpit_Glass"], mats["Cockpit_Frame"]),
        build_wing_port(mats["Wings"]),
        build_wing_starboard(mats["Wings"]),
        build_vertical_tail_port(mats["Tails"]),
        build_vertical_tail_starboard(mats["Tails"]),
        build_control_surfaces(mats["Controls"]),
        build_landing_gear(mats["Gear"]),
        build_engine_nacelle("Engine_Port", -1.65, mats["Engine_Port"], mats["Nozzle"], "Port Engine (ENG-003)"),
        build_engine_nacelle("Engine_Starboard", 1.65, mats["Engine_Starboard"], mats["Nozzle"], "Starboard Engine (ENG-004)"),
    ]

    # Root empty object
    root = bpy.data.objects.new("VAJRA_Su30MKI_Aircraft", None)
    bpy.context.collection.objects.link(root)
    for o in objs:
        o.parent = root

    glb_path = os.path.join(OUTPUT_DIR, GLB_NAME)
    blend_path = os.path.join(OUTPUT_DIR, BLEND_NAME)

    bpy.ops.object.select_all(action="DESELECT")
    try:
        bpy.ops.export_scene.gltf(
            filepath=glb_path,
            export_format="GLB",
            export_extras=True,
            export_materials="EXPORT",
            export_cameras=False,
            export_lights=False,
        )
    except TypeError:
        bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB", export_extras=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    tris = sum(len(o.data.polygons) for o in objs)
    size_mb = os.path.getsize(glb_path) / 1e6
    print("=" * 65)
    print("DONE - VAJRA full aircraft model generated successfully!")
    print("  airframe : Su-30MKI IAF Flanker-H Multi-role Air Superiority")
    print("  parts    :", ", ".join(o.name for o in objs))
    print("  faces    : ~%d (approx %d tris)" % (tris, tris * 2))
    print("  GLB      : %s (%.2f MB)" % (glb_path, size_mb))
    print("  BLEND    : %s" % blend_path)
    print("=" * 65)


if __name__ == "__main__":
    main()
