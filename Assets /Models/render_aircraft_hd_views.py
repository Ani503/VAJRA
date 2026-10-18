"""
Renders high-resolution preview shots of the high-fidelity Su-30MKI digital twin
from vajra_aircraft_hd.blend using Blender EEVEE/Cycles.
Outputs:
  - Assets/Models/preview_su30mki_iso.png
  - Assets/Models/preview_su30mki_top.png
  - Assets/Models/preview_su30mki_front.png
"""

import bpy
import math
import os
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BLEND_PATH = os.path.join(SCRIPT_DIR, "vajra_aircraft_hd.blend")

# Open high-def model file
bpy.ops.wm.open_mainfile(filepath=BLEND_PATH)

sc = bpy.context.scene
sc.render.resolution_x = 1280
sc.render.resolution_y = 720
sc.render.image_settings.file_format = "PNG"

# Use Cycles CPU for reliable headless rendering
sc.render.engine = "CYCLES"
sc.cycles.samples = 16
sc.cycles.device = "CPU"


# Dark Tactical Studio World Background
world = sc.world or bpy.data.worlds.new("World")
sc.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (0.055, 0.070, 0.090, 1.0)
    bg.inputs["Strength"].default_value = 1.0

# Key Lights (Sun + Fill Point Lights)
sun = bpy.data.objects.get("Sun")
if not sun:
    bpy.ops.object.light_add(type="SUN", location=(8.0, -10.0, 12.0))
    sun = bpy.context.object
    sun.name = "Sun"
sun.data.energy = 4.5
sun.data.color = (0.95, 0.98, 1.0)

# Rim backlight
bpy.ops.object.light_add(type="POINT", location=(-10.0, 12.0, 6.0))
rim = bpy.context.object
rim.data.energy = 800.0
rim.data.color = (0.55, 0.75, 1.0)

# Camera
cam = bpy.data.objects.get("RenderCamera")
if not cam:
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.name = "RenderCamera"
sc.camera = cam

# View 1: 3/4 Isometric Perspective View
cam.location = (14.5, -16.0, 9.5)
direction = Vector((0.0, -0.5, 0.2)) - cam.location
cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 42

out_iso = os.path.join(SCRIPT_DIR, "preview_su30mki_iso.png")
sc.render.filepath = out_iso
bpy.ops.render.render(write_still=True)
print(f"[RENDER] Saved Isometric Preview: {out_iso}")

# View 2: Full Top-down Planform View
cam.location = (0.0, 0.0, 36.0)
direction = Vector((0.0, 0.0, 0.0)) - cam.location
cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 32

out_top = os.path.join(SCRIPT_DIR, "preview_su30mki_top.png")
sc.render.filepath = out_top
bpy.ops.render.render(write_still=True)
print(f"[RENDER] Saved Top-down Planform Preview: {out_top}")

# View 3: Aggressive Front / Head-on View
cam.location = (0.0, -22.0, 1.8)
direction = Vector((0.0, 0.0, 0.4)) - cam.location
cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 55

out_front = os.path.join(SCRIPT_DIR, "preview_su30mki_front.png")
sc.render.filepath = out_front
bpy.ops.render.render(write_still=True)
print(f"[RENDER] Saved Front View Preview: {out_front}")

# View 4: Rear-Quarter View (AL-31FP Thrust-Vectoring Nozzles & Stabilators)
cam.location = (-15.0, 16.0, 7.5)
direction = Vector((0.0, 2.0, 0.2)) - cam.location
cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 42

out_rear = os.path.join(SCRIPT_DIR, "preview_su30mki_rear.png")
sc.render.filepath = out_rear
bpy.ops.render.render(write_still=True)
print(f"[RENDER] Saved Rear-Quarter View Preview: {out_rear}")

