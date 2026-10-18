"""
VAJRA - Render Digital Twin Views Script
Renders high-resolution verification images using Blender Cycles CPU:
  1. Aircraft Normal Mode (Isometric 3/4)
  2. Aircraft X-Ray Mode (Outer shell translucent at 12%, internal frames, spars, ribs, avionics, mounts, and engines opaque)
  3. Aircraft Exploded Mode (Assembly-aware separation along calibrated 3D vectors)
  4. Aircraft Top-Down Planform
  5. Aircraft Frontal Silhouette
  6. Engine Normal Mode
  7. Engine Exploded Mode (Strict longitudinal stage order)
"""
import bpy
import math
import os
from mathutils import Vector

MODELS_DIR = os.path.dirname(os.path.abspath(__file__))
BLEND_PATH_AIRCRAFT = os.path.join(MODELS_DIR, "vajra_aircraft_twin.blend")
BLEND_PATH_ENGINE = os.path.join(MODELS_DIR, "vajra_engine_detailed.blend")

def setup_cycles():
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        sc.cycles.device = "CPU"
    except Exception:
        pass
    sc.cycles.samples = 24
    sc.render.resolution_x = 1280
    sc.render.resolution_y = 720
    sc.render.film_transparent = False
    
    if not sc.world:
        sc.world = bpy.data.worlds.new("VajraWorld")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.05, 0.07, 0.09, 1.0)
        bg.inputs["Strength"].default_value = 0.85

def setup_lights():
    for obj in list(bpy.data.objects):
        if obj.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(obj, do_unlink=True)
            
    bpy.ops.object.light_add(type="SUN", location=(12, -15, 18))
    sun1 = bpy.context.object
    sun1.name = "KeySun"
    sun1.data.energy = 3.5
    sun1.rotation_euler = (math.radians(45), math.radians(20), math.radians(-35))
    
    bpy.ops.object.light_add(type="SUN", location=(-12, 10, 10))
    sun2 = bpy.context.object
    sun2.name = "FillSun"
    sun2.data.energy = 1.8
    sun2.rotation_euler = (math.radians(-30), math.radians(-40), math.radians(140))
    
    bpy.ops.object.light_add(type="POINT", location=(0, 0, -8))
    pt = bpy.context.object
    pt.name = "BounceLight"
    pt.data.energy = 800.0

def create_camera(name, loc, rot):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = 38
    cam_obj = bpy.data.objects.new(name, cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = loc
    cam_obj.rotation_euler = rot
    return cam_obj

def render_view(cam_obj, out_path):
    bpy.context.scene.camera = cam_obj
    bpy.context.scene.render.filepath = out_path
    print(f"Rendering: {out_path} ...")
    bpy.ops.render.render(write_still=True)
    print(f"Saved: {out_path} ({os.path.getsize(out_path)} bytes)")

def apply_normal_mode():
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            obj.location = (0, 0, 0)
            is_internal = obj.get("is_internal", False)
            obj.hide_render = is_internal
            
            if obj.data.materials:
                mat = obj.data.materials[0]
                if mat and mat.node_tree:
                    bsdf = mat.node_tree.nodes.get("Principled BSDF")
                    if bsdf:
                        is_glass = "Glass" in mat.name
                        if "Transmission Weight" in bsdf.inputs:
                            bsdf.inputs["Transmission Weight"].default_value = 0.88 if is_glass else 0.0
                        elif "Transmission" in bsdf.inputs:
                            bsdf.inputs["Transmission"].default_value = 0.88 if is_glass else 0.0
                        if "Alpha" in bsdf.inputs:
                            bsdf.inputs["Alpha"].default_value = 0.35 if is_glass else 1.0

def apply_xray_mode():
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            obj.location = (0, 0, 0)
            obj.hide_render = False
            is_shell = obj.get("is_shell", False)
            if obj.data.materials:
                mat = obj.data.materials[0]
                if mat and mat.node_tree:
                    bsdf = mat.node_tree.nodes.get("Principled BSDF")
                    if bsdf:
                        if is_shell and "Glass" not in mat.name:
                            if "Alpha" in bsdf.inputs:
                                bsdf.inputs["Alpha"].default_value = 0.12
                            if "Transmission Weight" in bsdf.inputs:
                                bsdf.inputs["Transmission Weight"].default_value = 0.85
                            elif "Transmission" in bsdf.inputs:
                                bsdf.inputs["Transmission"].default_value = 0.85
                        else:
                            if "Alpha" in bsdf.inputs:
                                bsdf.inputs["Alpha"].default_value = 1.0
                            if "Transmission Weight" in bsdf.inputs:
                                bsdf.inputs["Transmission Weight"].default_value = 0.0
                            elif "Transmission" in bsdf.inputs:
                                bsdf.inputs["Transmission"].default_value = 0.0

def apply_exploded_mode(scale_factor=1.0):
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            obj.hide_render = False
            dx = float(obj.get("explode_dx", 0.0))
            dy = float(obj.get("explode_dy", 0.0))
            dz = float(obj.get("explode_dz", 0.0))
            if dx == 0.0 and dy == 0.0 and dz == 0.0:
                offset = float(obj.get("explode_offset", 0.0))
                axis = str(obj.get("explode_axis", "Y")).upper()
                if axis == "X": dx = offset
                elif axis == "Y": dy = offset
                elif axis == "Z": dz = offset
                
            disp = Vector((dx, dy, dz)) * scale_factor
            obj.location = disp
            
            is_shell = obj.get("is_shell", False)
            if is_shell and obj.data.materials:
                mat = obj.data.materials[0]
                if mat and mat.node_tree:
                    bsdf = mat.node_tree.nodes.get("Principled BSDF")
                    if bsdf:
                        if "Casing" in obj.name:
                            if "Alpha" in bsdf.inputs:
                                bsdf.inputs["Alpha"].default_value = 0.22
                            if "Transmission Weight" in bsdf.inputs:
                                bsdf.inputs["Transmission Weight"].default_value = 0.75
                            elif "Transmission" in bsdf.inputs:
                                bsdf.inputs["Transmission"].default_value = 0.75
                        elif "Alpha" in bsdf.inputs:
                            bsdf.inputs["Alpha"].default_value = 0.85

def render_aircraft_suite():
    print(f"Opening aircraft blend file: {BLEND_PATH_AIRCRAFT}")
    bpy.ops.wm.open_mainfile(filepath=BLEND_PATH_AIRCRAFT)
    setup_cycles()
    setup_lights()
    
    cam_iso = create_camera("Cam_Iso", (18.0, -22.0, 11.0), (math.radians(65), 0, math.radians(40)))
    cam_top = create_camera("Cam_Top", (0, 0, 34.0), (0, 0, math.radians(180)))
    cam_front = create_camera("Cam_Front", (0, -26.0, 0.4), (math.radians(90), 0, 0))
    
    # 1. Normal Mode Isometric View
    apply_normal_mode()
    render_view(cam_iso, os.path.join(MODELS_DIR, "preview_twin_normal_iso.png"))
    
    # 2. X-Ray Mode Isometric View
    apply_xray_mode()
    render_view(cam_iso, os.path.join(MODELS_DIR, "preview_twin_xray.png"))
    
    # 3. Exploded Mode Isometric View (calibrated 3D displacement vectors)
    apply_exploded_mode(1.0)
    render_view(cam_iso, os.path.join(MODELS_DIR, "preview_twin_exploded.png"))
    
    # 4. Top-Down Planform (Normal)
    apply_normal_mode()
    render_view(cam_top, os.path.join(MODELS_DIR, "preview_twin_top.png"))
    
    # 5. Front View (Normal)
    apply_normal_mode()
    render_view(cam_front, os.path.join(MODELS_DIR, "preview_twin_front.png"))

def render_engine_suite():
    print(f"Opening engine blend file: {BLEND_PATH_ENGINE}")
    bpy.ops.wm.open_mainfile(filepath=BLEND_PATH_ENGINE)
    setup_cycles()
    setup_lights()
    
    cam_eng_iso = create_camera("Cam_Eng_Iso", (6.5, -7.5, 4.2), (math.radians(68), 0, math.radians(45)))
    
    # Engine Normal View
    apply_normal_mode()
    render_view(cam_eng_iso, os.path.join(MODELS_DIR, "preview_engine_normal.png"))
    
    # Engine Exploded View (Strict longitudinal stage order)
    apply_exploded_mode(1.0)
    render_view(cam_eng_iso, os.path.join(MODELS_DIR, "preview_engine_exploded.png"))

def main():
    render_aircraft_suite()
    render_engine_suite()
    print("ALL DIGITAL TWIN VIEWS (AIRCRAFT + ENGINE) SUCCESSFULLY RENDERED!")

if __name__ == "__main__":
    main()
