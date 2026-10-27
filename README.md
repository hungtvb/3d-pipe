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
