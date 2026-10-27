"""Dependency-free GLB 2.0 inspection and a reproducible smoke-test fixture.

Stage 0 is intentionally about file integrity, not render quality. Avoid marking
Blender/Cycles, browser WebGL, reference matching, or FPS as passed here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

GLTF_JSON = b"JSON"
GLTF_BIN = b"BIN\x00"
COMPONENT_SIZE = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
COMPONENT_FMT = {5121: "B", 5123: "H", 5125: "I"}
TYPE_SIZE = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}


def read_glb(path: Path) -> tuple[dict, bytes, bytes]:
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError("GLB too short")
    magic, version, total = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2 or total != len(raw):
        raise ValueError("Invalid GLB header, version or declared length")
    chunks = []
    cursor = 12
    while cursor < len(raw):
        if cursor + 8 > len(raw):
            raise ValueError("Incomplete GLB chunk header")
        size, kind = struct.unpack_from("<I4s", raw, cursor)
        cursor += 8
        if size % 4 or cursor + size > len(raw):
            raise ValueError("Invalid GLB chunk length / alignment")
        chunks.append((kind, raw[cursor:cursor + size]))
        cursor += size
    if not chunks or chunks[0][0] != GLTF_JSON:
        raise ValueError("GLB must start with JSON chunk")
    doc = json.loads(chunks[0][1].rstrip(b" \x00"))
    binary = next((chunk for kind, chunk in chunks[1:] if kind == GLTF_BIN), b"")
    return doc, binary, raw


def inspect_glb(path: Path, *, triangle_budget: int = 100_000, size_budget_mb: float = 30) -> dict:
    doc, binary, raw = read_glb(path)
    errors: list[str] = []
    mesh_count = 0
    triangle_count = 0
    views = doc.get("bufferViews", [])
    accessors = doc.get("accessors", [])
    if doc.get("asset", {}).get("version") != "2.0":
        errors.append("asset.version must equal 2.0")
    buffers = doc.get("buffers", [])
    if len(buffers) != 1 or buffers[0].get("uri"):
        errors.append("Expected one embedded GLB binary buffer")
    elif buffers[0].get("byteLength", 0) > len(binary):
        errors.append("Embedded binary buffer is truncated")

    def accessor_info(index: int) -> tuple[int, int, int]:
        if not isinstance(index, int) or index < 0 or index >= len(accessors):
            raise ValueError(f"Invalid accessor reference: {index}")
        accessor = accessors[index]
        view_index = accessor.get("bufferView")
        if not isinstance(view_index, int) or not 0 <= view_index < len(views):
            raise ValueError("Missing or invalid accessor bufferView")
        view = views[view_index]
        count = accessor.get("count", 0)
        width = TYPE_SIZE.get(accessor.get("type"))
        component = COMPONENT_SIZE.get(accessor.get("componentType"))
        if not isinstance(count, int) or count < 0 or width is None or component is None:
            raise ValueError("Invalid accessor type/count/component")
        element_bytes = width * component
        stride = view.get("byteStride", element_bytes)
        if stride < element_bytes:
            raise ValueError("Buffer stride smaller than element")
        start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        last = start + (count - 1) * stride + element_bytes if count else start
        view_end = view.get("byteOffset", 0) + view.get("byteLength", 0)
        if start < 0 or last > view_end or view_end > len(binary):
            raise ValueError("Accessor points outside binary buffer")
        return count, start, stride

    for mesh in doc.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            mesh_count += 1
            attrs = primitive.get("attributes", {})
            try:
                if "POSITION" not in attrs:
                    raise ValueError("Missing POSITION")
                positions, _, _ = accessor_info(attrs["POSITION"])
                for name in ("NORMAL", "TEXCOORD_0"):
                    if name in attrs and accessor_info(attrs[name])[0] != positions:
                        raise ValueError(f"{name} count != POSITION count")
                if primitive.get("mode", 4) != 4:
                    raise ValueError("Only TRIANGLES primitive mode supported by this gate")
                if "indices" not in primitive:
                    raise ValueError("Missing triangle indices")
                idx = primitive["indices"]
                count, start, stride = accessor_info(idx)
                accessor = accessors[idx]
                if accessor["type"] != "SCALAR" or accessor["componentType"] not in COMPONENT_FMT:
                    raise ValueError("Indices must be unsigned SCALAR")
                if count % 3:
                    raise ValueError("Triangle index count is not divisible by 3")
                fmt = "<" + COMPONENT_FMT[accessor["componentType"]]
                for j in range(count):
                    if struct.unpack_from(fmt, binary, start + j * stride)[0] >= positions:
                        raise ValueError("Triangle index points outside vertex positions")
                triangle_count += count // 3
            except (ValueError, KeyError, TypeError, struct.error) as exc:
                errors.append(f"mesh {mesh_count}: {exc}")

    for i, img in enumerate(doc.get("images", [])):
        if "bufferView" in img:
            v = img["bufferView"]
            if not isinstance(v, int) or not 0 <= v < len(views):
                errors.append(f"image {i}: invalid bufferView")
                continue
            view = views[v]
            start = view.get("byteOffset", 0)
            end = start + view.get("byteLength", 0)
            payload = binary[start:end]
            mime = img.get("mimeType")
            if end > len(binary) or not ((mime == "image/png" and payload.startswith(b"\x89PNG\r\n\x1a\n")) or (mime == "image/jpeg" and payload.startswith(b"\xff\xd8"))):
                errors.append(f"image {i}: invalid embedded image bytes or MIME")
        elif img.get("uri"):
            errors.append(f"image {i}: external images are not packed into GLB")
        else:
            errors.append(f"image {i}: missing source")

    if triangle_count > triangle_budget:
        errors.append(f"triangle budget exceeded: {triangle_count} > {triangle_budget}")
    if len(raw) > size_budget_mb * 1024 * 1024:
        errors.append("GLB exceeds file size budget")
    if not mesh_count:
        errors.append("No mesh primitives in asset")
    return {"file": path.name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "mesh_primitives": mesh_count, "triangles": triangle_count,
            "embedded_images": len(doc.get("images", [])), "checks_passed": not errors,
            "errors": errors, "scope": "Structural GLB only; not visual or browser E2E"}


def make_fixture(path: Path) -> None:
    """Create a deterministic textured-coordinate floor quad (two triangles)."""
    positions = [-1., 0., -1., 1., 0., -1., 1., 0., 1., -1., 0., 1.]
    normals = [0., 1., 0.] * 4
    uv = [0., 0., 1., 0., 1., 1., 0., 1.]
    indices = [0, 2, 1, 0, 3, 2]
    groups = [struct.pack("<12f", *positions), struct.pack("<12f", *normals),
              struct.pack("<8f", *uv), struct.pack("<6H", *indices)]
    data = b"".join(groups)
    offsets = [0, 48, 96, 128]
    views = [{"buffer": 0, "byteOffset": off, "byteLength": len(group)} for off, group in zip(offsets, groups)]
    accessors = [{"bufferView": i, "componentType": comp, "count": count, "type": kind}
                 for i, comp, count, kind in [(0, 5126, 4, "VEC3"), (1, 5126, 4, "VEC3"),
                                               (2, 5126, 4, "VEC2"), (3, 5123, 6, "SCALAR")]]
    doc = {"asset": {"version": "2.0", "generator": "3d-pipe fixture"},
           "buffers": [{"byteLength": len(data)}], "bufferViews": views, "accessors": accessors,
           "meshes": [{"name": "qa_floor", "primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1,
                      "TEXCOORD_0": 2}, "indices": 3, "mode": 4}]}],
           "nodes": [{"mesh": 0}], "scenes": [{"nodes": [0]}], "scene": 0}
    json_blob = json.dumps(doc, separators=(",", ":"), sort_keys=True).encode("utf-8")
    json_blob += b" " * (-len(json_blob) % 4)
    data += b"\x00" * (-len(data) % 4)
    total = 12 + 8 + len(json_blob) + 8 + len(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, total) + struct.pack("<I4s", len(json_blob), GLTF_JSON)
                     + json_blob + struct.pack("<I4s", len(data), GLTF_BIN) + data)


def main() -> int:
    parser = argparse.ArgumentParser(description="3D Pipe GLB quality gate")
    parser.add_argument("action", choices=["make-fixture", "audit"])
    parser.add_argument("--file", type=Path, default=Path("docs/fixture.glb"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--triangle-budget", type=int, default=100_000)
    parser.add_argument("--size-budget-mb", type=float, default=30)
    args = parser.parse_args()
    if args.action == "make-fixture":
        make_fixture(args.file)
        print(f"Generated: {args.file}")
        return 0
    try:
        report = inspect_glb(args.file, triangle_budget=args.triangle_budget, size_budget_mb=args.size_budget_mb)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report = {"file": args.file.name, "checks_passed": False, "errors": [str(exc)]}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
