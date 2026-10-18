"""
VAJRA - Preview renderer (Blender 3.6 / 4.x / 5.x)

Run AFTER build_vajra_engine.py, in the same Blender session (or with vajra_engine.blend open).
It poses the engine as Normal, X-ray and Exploded and renders three PNG images - handy for
checking the model and for the project report / slides.

  Blender -> Scripting tab -> open this file -> Run Script
"""
import bpy, math, os
from mathutils import Vector

OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "vajra_assets")
RES_X, RES_Y = 1600, 900
SAMPLES = 48            # raise for cleaner images
USE_CYCLES = True       # Cycles works on every machine; set False to try EEVEE (faster with a GPU)

PARTS = ["Fan", "Compressor", "Combustion_Chamber", "Turbine", "Shaft", "Casing", "Nozzle"]
HEALTH_COLOURS = {            # demo health colours for the previews
    "Fan": (0.13, 0.65, 0.30), "Compressor": (0.13, 0.65, 0.30),
    "Combustion_Chamber": (0.85, 0.63, 0.10), "Turbine": (0.84, 0.27, 0.27),
    "Shaft": (0.13, 0.65, 0.30), "Nozzle": (0.13, 0.65, 0.30),
}


def get_parts():
    objs = {}
    for n in PARTS:
        o = bpy.data.objects.get(n)
        if o is None:
            raise RuntimeError("Object '%s' not found. Run build_vajra_engine.py first." % n)
        objs[n] = o
    return objs


def store_home(objs):
    for o in objs.values():
        if "home_loc" not in o:
            o["home_loc"] = tuple(o.location)


def reset(objs):
    for o in objs.values():
        o.location = Vector(o["home_loc"])


def set_alpha(mat, alpha, colour=None):
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Alpha"].default_value = alpha
    if colour is not None:
        bsdf.inputs["Base Color"].default_value = (*colour, 1.0)
    if hasattr(mat, "blend_method"):
        try:
            mat.blend_method = "BLEND" if alpha < 1 else "OPAQUE"
        except Exception:
            pass


def snapshot_materials(objs):
    snap = {}
    for n, o in objs.items():
        bsdf = o.active_material.node_tree.nodes.get("Principled BSDF")
        snap[n] = (tuple(bsdf.inputs["Base Color"].default_value)[:3],
                   bsdf.inputs["Alpha"].default_value)
    return snap


def restore_materials(objs, snap):
    for n, o in objs.items():
        set_alpha(o.active_material, snap[n][1], snap[n][0])


def setup_render():
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = RES_X, RES_Y
    sc.render.image_settings.file_format = "PNG"
    sc.render.film_transparent = False
    if USE_CYCLES:
        sc.render.engine = "CYCLES"
        sc.cycles.samples = SAMPLES
        sc.cycles.device = "CPU"
        try:
            sc.cycles.use_denoising = True
        except Exception:
            pass
    else:
        sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in \
            bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys() else "BLENDER_EEVEE"
    world = sc.world or bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.055, 0.075, 0.10, 1)
    bg.inputs["Strength"].default_value = 1.2
    # camera aimed at the engine centre, wide enough for the exploded view
    cam = bpy.data.objects.get("PreviewCamera")
    if cam is None:
        bpy.ops.object.camera_add()
        cam = bpy.context.object
        cam.name = "PreviewCamera"
    cam.location = (10.0, -14.5, 5.2)
    direction = Vector((0, 0.1, 0)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 38
    sc.camera = cam
    sun = bpy.data.objects.get("Sun")
    if sun:
        sun.data.energy = 4.0


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("rendered", path)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    objs = get_parts()
    store_home(objs)
    snap = snapshot_materials(objs)
    setup_render()

    # ---- 1. NORMAL (health colours on)
    reset(objs)
    restore_materials(objs, snap)
    for n, col in HEALTH_COLOURS.items():
        set_alpha(objs[n].active_material, 1.0, col)
    set_alpha(objs["Casing"].active_material, 1.0, (0.35, 0.40, 0.33))
    render(os.path.join(OUTPUT_DIR, "view_normal.png"))

    # ---- 2. X-RAY (casing almost transparent)
    set_alpha(objs["Casing"].active_material, 0.10, (0.55, 0.75, 0.95))
    render(os.path.join(OUTPUT_DIR, "view_xray.png"))

    # ---- 3. EXPLODED (parts slide apart; casing lifts away)
    set_alpha(objs["Casing"].active_material, 0.25, (0.55, 0.75, 0.95))
    for n, o in objs.items():
        off = float(o["explode_offset"])
        home = Vector(o["home_loc"])
        if o["explode_axis"] == "Z":
            o.location = home + Vector((0, 0, off))
        else:
            o.location = home + Vector((0, off, 0))
    render(os.path.join(OUTPUT_DIR, "view_exploded.png"))

    # restore the scene to Normal
    reset(objs)
    restore_materials(objs, snap)
    print("DONE - images saved in", OUTPUT_DIR)


main()
