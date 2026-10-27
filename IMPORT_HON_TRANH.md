# Import the existing Hồn Tranh sample into 3D Pipe

The full local workspace package places the project under `examples/hon-tranh/`. The reusable stage-0 GLB gate is already committed to `main`.

Source/assets import: [issue #1](https://github.com/hungtvb/3d-pipe/issues/1); browser E2E: [#2](https://github.com/hungtvb/3d-pipe/issues/2); native Blender: [#3](https://github.com/hungtvb/3d-pipe/issues/3).

The full workspace ZIP contains Hồn Tranh source and binary assets. The GitHub connector can write UTF-8 files but cannot directly transfer local binary files from this runtime; **those binary assets are not yet in GitHub**.

On a machine with GitHub push access:

```bash
git clone https://github.com/hungtvb/3d-pipe.git
cd 3d-pipe
# Copy contents of the supplied workspace ZIP here, merging its 3d-pipe root.
git checkout -b feat/import-hon-tranh
python -m unittest discover -s tests -v
python -m pipeline.glb_gate audit --file examples/hon-tranh/public/assets/hero_shrine.glb --triangle-budget 50000
python -m pipeline.glb_gate audit --file examples/hon-tranh/public/assets/village.glb --triangle-budget 120000
git add .
git commit -m "feat: import Hon Tranh playable reference pipeline"
git push -u origin feat/import-hon-tranh
```

Open a PR and inspect GitHub Actions before merging.

**Important:** the current green workflow tests GLB structure and a generated fixture, not browser gameplay or Blender rendering. The integration workflow is included in the workspace package and becomes actionable when sample assets are imported.
