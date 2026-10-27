"""Native Blender import/render smoke test for generated glTF assets.

Run:
  blender -b --factory-startup --python pipeline/blender_smoke.py -- \
    --input artifacts/smoke.glb --output artifacts/blender
This is a geometry/renderer infrastructure test, not the Hồn Tranh visual gate.
"""
import argparse
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector


def run():
    cli = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--samples", type=int, default=8)
    args = parser.parse_args(cli)

    source = Path(args.input).resolve()
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    assert source.is_file(), f"Missing asset: {source}"
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(source))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("Blender imported no meshes")
    # Test fixture is a planar XZ-size quad on the y=0 plane. Render from above.
    bpy.ops.object.camera_add(location=(3.0, -5.0, 4.0))
    camera = bpy.context.object
    direction = Vector((0.0, 0.0, 0.0)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 5
    bpy.ops.object.light_add(type="AREA", location=(1.0, -2.0, 5.0))
    bpy.context.object.data.energy = 450
    bpy.context.object.data.shape = "DISK"
    bpy.context.object.data.size = 4

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = args.samples
    scene.cycles.device = "CPU"
    scene.render.resolution_x = 400
    scene.render.resolution_y = 300
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(out / "render.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "smoke.blend"))
    bpy.ops.render.render(write_still=True)
    image = out / "render.png"
    blend = out / "smoke.blend"
    if image.stat().st_size < 100 or blend.stat().st_size < 100:
        raise RuntimeError("Render or native project output missing")
    info = {"blender_version": bpy.app.version_string, "meshes": len(meshes),
            "asset": source.name, "renderer": scene.render.engine,
            "resolution": [400, 300], "samples": args.samples,
            "outputs": [image.name, blend.name]}
    (out / "report.json").write_text(json.dumps(info, indent=2))
    print("BLENDER_SMOKE_SUCCESS", info)


if __name__ == "__main__":
    run()
