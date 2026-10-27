# 3D Pipe

**AI-assisted 3D production pipeline**: references → scene plan → procedural geometry → GLB/PBR → validation → browser preview → Blender renders → game / video.

## First reference project: Hồn Tranh

Vietnamese-inspired interactive village and shrine prototype. Current release: **v0.5**, developed and tested locally; the assets and complete application are being imported into this repository. Do not interpret placeholder workflows as passed CI until their GitHub Actions runs are green.

### Pipeline stages

1. `ingest`: source painting/book and art direction
2. `plan`: scene manifest, units, performance budget
3. `build`: deterministic Blender/Python asset generation
4. `validate`: GLB structure, PBR texture channels and geometry
5. `review`: four-view render, reference comparison and QA
6. `deliver`: GLB, WebGL playable prototype, camera cinematic, CI artifacts

### Release quality gates

- Asset audit PASS: valid GLB and texture references, normals, sane transforms
- Automated gameplay logic PASS
- WebGL browser E2E PASS with screenshots and browser errors captured
- Native Blender rendering PASS with `.blend` and multi-angle evidence
- No claims of performance or fidelity without measured evidence

See [the roadmap](docs/ROADMAP.md) and [pipeline contracts](docs/PIPELINE_CONTRACT.md).

Project-specific source and large binary assets are shipped separately until source import is complete.

## Run the new manifest-driven blockout stage

```bash
python -m unittest discover -s tests -v
python -m pipeline.build_blockout \\
  --manifest examples/village-blockout/scene.json \\
  --out artifacts/village-blockout.glb
python -m pipeline.glb_gate audit \\
  --file artifacts/village-blockout.glb \\
  --triangle-budget 2500 \\
  --out artifacts/village-audit.json
```

This JSON manifest has 79 scene objects with named positions, dimensions and materials.
The resulting GLB is *automatically built* in [Manifest → GLB CI](https://github.com/hungtvb/3d-pipe/actions/workflows/blockout.yml) and available under the run's artifacts. It is a reference **blockout**, not the existing Hồn Tranh v0.5 hero PBR asset.

## Verification workflows

- [Structural GLB Gate](https://github.com/hungtvb/3d-pipe/actions/workflows/qa.yml): dependency-free structural audit.
- [Browser WebGL2 smoke](https://github.com/hungtvb/3d-pipe/actions/workflows/browser-smoke.yml): real Chromium shader and pixel readback, screenshot evidence; **not gameplay E2E**.
- [Native Blender Cycles smoke](https://github.com/hungtvb/3d-pipe/actions/workflows/blender-smoke.yml): Blender glTF import, native `.blend`, Cycles image; **not Hồn Tranh art review**.
- [Manifest blockout](https://github.com/hungtvb/3d-pipe/actions/workflows/blockout.yml): edit scene JSON → regenerate GLB → structural budget audit.

Hồn Tranh v0.5 source and larger binary assets remain in the previously shared full workspace ZIP; GitHub import is still tracked in [issue #1](https://github.com/hungtvb/3d-pipe/issues/1). Do not treat generic smoke tests as Hồn Tranh E2E success.
