# 3D Pipe – Verified CI Gates (2026-10-28)

## Evidence (immutable GitHub Actions runs)

| Gate | Status | Exact scope | Run |
|---|---|---|---|
| GLB manifest compiler + structural audit | PASS | Scene manifest, indices, geometry budgets, fixture | [40608498609](https://github.com/hungtvb/3d-pipe/actions/runs/40608498609) |
| Generic WebGL2 smoke | PASS | Chromium SwiftShader and pixel readback | [40534572309](https://github.com/hungtvb/3d-pipe/actions/runs/40534572309) |
| Generated village WebGL E2E | PASS | 936 triangles, 8 draw calls; rendered pixels + camera interaction | [40608558579](https://github.com/hungtvb/3d-pipe/actions/runs/40608558579) |
| Native Blender smoke | PASS | Real Blender 4.5.15 LTS, native .blend and Cycles PNG | [40608240607](https://github.com/hungtvb/3d-pipe/actions/runs/40608240607) |
| Generated village Blender 4 views | PASS | Imported manifest GLB as 8 meshes; front/left/back/aerial, Cycles 720×450 | [40608832581](https://github.com/hungtvb/3d-pipe/actions/runs/40608832581) |

### Village E2E run metrics
- Manifest source objects: **79**
- Triangles: **936**
- Draw calls: **8**
- Valid geometric pixels in sampling grid: **26 / 77**
- Camera yaw: **0.63 → 0.78** after keyboard interaction
- Browser page errors / WebGL errors: **0**
- Browser renderer: **Chromium SwiftShader** (software rendering; **not** physical GPU FPS benchmark).

### Blender 4-view render
- Blender: **4.5.15 LTS**
- Engine: **Cycles CPU**
- Imported mesh groups: **8**
- Resolution: **720×450 each**
- Samples per pixel: **12**
- Saved editable scene: `village-review.blend`
- QA validates images exist, dimensions match and contain color variation.

### Not yet passed (do not conflate)
- Hồn Tranh v0.5 game E2E (source/assets not yet in GitHub).
- Cycles render of the 33,620-triangle Hồn Tranh hero PBR shrine.
- Direct reference-painting fidelity comparison.
- Mobile GPU performance and real-device FPS.

The scene preview is a **procedural blockout**, not high-fidelity model quality approval.
Hồn Tranh v0.5 source package remains available as a prior local ZIP handoff;
import to `examples/hon-tranh/` is tracked by [issue #1](https://github.com/hungtvb/3d-pipe/issues/1).
