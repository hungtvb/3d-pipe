"""Render a generated scene as four Blender/Cycles QA views.

Usage:
blender -b --factory-startup --python pipeline/blender_scene_review.py -- \
  --input artifacts/village-blockout.glb --output artifacts/blender-village
"""
from __future__ import annotations

import argparse
import json
from math import sqrt
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    cli = argparse.ArgumentParser()
    cli.add_argument("--input", required=True)
    cli.add_argument("--output", required=True)
    cli.add_argument("--samples", type=int, default=16)
    cli.add_argument("--resolution-x", type=int, default=720)
    cli.add_argument("--resolution-y", type=int, default=450)
    config = cli.parse_args(args)

    source = Path(config.input).resolve()
    out = Path(config.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not source.is_file():
        raise FileNotFoundError(source)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(source))

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("GLB imported with zero mesh objects")
    bpy.context.view_layer.update()

    points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    mins = [min(point[i] for point in points) for i in range(3)]
    maxs = [max(point[i] for point in points) for i in range(3)]
    dims = [maxs[i] - mins[i] for i in range(3)]
    center = Vector([(maxs[i] + mins[i]) * .5 for i in range(3)])
    footprint = max(dims[0], dims[1])
    depth = max(dims)
    if footprint <= 0 or depth <= 0:
        raise RuntimeError("Invalid imported mesh dimensions")

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = config.samples
    scene.render.resolution_x = config.resolution_x
    scene.render.resolution_y = config.resolution_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    if scene.world is None:
        scene.world = bpy.data.worlds.new("Studio sky")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.14, 0.18, 0.25, 1.0)
    background.inputs["Strength"].default_value = 0.75

    bpy.ops.object.light_add(type="AREA", location=center + Vector((depth*0.5,-depth*0.9,depth*1.4)))
    lamp = bpy.context.object
    lamp.name="QA Softbox"
    lamp.data.energy=2500
    lamp.data.shape="DISK"
    lamp.data.size=depth*0.95
    direction = center - lamp.location
    lamp.rotation_euler = direction.to_track_quat("-Z","Y").to_euler()

    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name="QA Camera"
    camera.data.type="ORTHO"
    camera.data.ortho_scale=depth*1.75
    scene.camera=camera
    # Scene is imported into Blender's Z-up coordinates automatically.
    views = {
       "front": Vector((.65,-1.0,.70)),
       "left": Vector((-1.1,-.2,.67)),
       "back": Vector((-.7,1.0,.72)),
       "aerial": Vector((.45,-.6,1.65)),
    }
    project=out/"village-review.blend"
    report={
        "blender_version":bpy.app.version_string,
        "asset":source.name,
        "imported_meshes":len(meshes),
        "bounds_min":mins,"bounds_max":maxs,
        "dimensions":dims,
        "renderer":"CYCLES",
        "samples":config.samples,
        "resolution":[config.resolution_x, config.resolution_y],
        "views":[],
    }
    # Save as an editable Blender project with materials and camera.
    camera.location=center+views["front"].normalized()*depth*2.5
    camera.rotation_euler=(center-camera.location).to_track_quat("-Z","Y").to_euler()
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    for name, vector in views.items():
        camera.location=center+vector.normalized()*depth*2.5
        camera.rotation_euler=(center-camera.location).to_track_quat("-Z","Y").to_euler()
        filename=f"{name}.png"
        scene.render.filepath=str(out/filename)
        bpy.ops.render.render(write_still=True)
        if (out/filename).stat().st_size < 1000:
            raise RuntimeError(f"{name} render is missing")
        report["views"].append({"name":name,"file":filename})
    (out/"report.json").write_text(json.dumps(report,indent=2),encoding="utf8")
    print("SCENE_CYCLES_REVIEW_PASS",json.dumps(report))


if __name__=="__main__":
    main()
