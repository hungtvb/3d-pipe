# Contract: AI → Geometry → QA → Web / Video

Each run should produce:
- `manifest.json`: source reference rights, units, scale, camera framing, triangle and texture budgets.
- `assets/**/*.glb`: packed texture dependencies, valid accessors/index bounds, deterministic build metadata.
- `qa/structural.json`: triangle count, SHA-256, violations, and gate status.
- `qa/visual/`: four reproducible camera angles, Blender version, render settings.
- `qa/browser/`: WebGL logs, screenshots, gameplay E2E and FPS samples from a declared device.
- `release/`: versioned artifacts only if all required quality gates pass.

**Structural PASS is not equivalent to visual PASS.**
A file can have valid geometry and still be unusable or aesthetically poor.
