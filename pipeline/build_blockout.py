"""Deterministic manifest → batched PBR GLB blockout.

No Blender, NumPy or model weights required.  This is an early blockout stage,
NOT a substitute for geometry/UV authoring or painting similarity review.

python -m pipeline.build_blockout --manifest examples/village-blockout/scene.json --out artifacts/village.glb
"""
import argparse
import json
import math
from pathlib import Path
import struct

DEFAULT_MATERIALS = {
    "stone": [0.43, 0.45, 0.44, 1],
    "plaster": [0.72, 0.67, 0.54, 1],
    "wood": [0.28, 0.15, 0.10, 1],
    "roof": [0.64, 0.18, 0.12, 1],
    "brass": [0.75, 0.53, 0.25, 1],
    "foliage": [0.16, 0.38, 0.23, 1],
    "earth": [0.36, 0.43, 0.28, 1],
    "lantern": [0.86, 0.42, 0.18, 1],
}

class MeshBatch:
    def __init__(self):
        self.vertices = []
        self.normals = []
        self.indices = []

    def quad(self, a, b, c, d):
        """Wind points counter-clockwise; flat normal per quad."""
        ux, uy, uz = (b[i] - a[i] for i in range(3))
        vx, vy, vz = (d[i] - a[i] for i in range(3))
        n = [uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx]
        mag = math.sqrt(sum(x*x for x in n))
        if mag < 1e-9:
            raise ValueError("Degenerate polygon in manifest")
        normal = tuple(x / mag for x in n)
        base = len(self.vertices)
        self.vertices.extend((tuple(a), tuple(b), tuple(c), tuple(d)))
        self.normals.extend((normal,)*4)
        self.indices.extend((base, base+1, base+2, base, base+2, base+3))

    def tri(self, a, b, c):
        ux, uy, uz = (b[i] - a[i] for i in range(3))
        vx, vy, vz = (c[i] - a[i] for i in range(3))
        n = [uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx]
        mag = math.sqrt(sum(x*x for x in n))
        if mag < 1e-9:
            raise ValueError("Degenerate triangle in manifest")
        normal = tuple(x / mag for x in n)
        base = len(self.vertices)
        self.vertices.extend((tuple(a), tuple(b), tuple(c)))
        self.normals.extend((normal,)*3)
        self.indices.extend((base, base+1, base+2))

    def box(self, center, size):
        x, y, z = center
        w, h, d = (v/2 for v in size)
        p = [(x-w,y-h,z-d), (x+w,y-h,z-d),
             (x+w,y+h,z-d), (x-w,y+h,z-d),
             (x-w,y-h,z+d), (x+w,y-h,z+d),
             (x+w,y+h,z+d), (x-w,y+h,z+d)]
        for face in [(0,3,2,1),(4,5,6,7),(0,4,7,3),
                     (1,2,6,5),(3,7,6,2),(0,1,5,4)]:
            self.quad(*(p[i] for i in face))

    def gable_roof(self, center, size):
        x, y, z = center
        w, rise, d = size
        if rise <= 0:
            raise ValueError("Roof rise must be positive")
        x0, x1 = x-w/2, x+w/2
        z0, z1 = z-d/2, z+d/2
        # Top ridge at y+rise; two sloped planes plus gables.
        ridge0 = (x,y+rise,z0)
        ridge1 = (x,y+rise,z1)
        le0=(x0,y,z0); le1=(x0,y,z1)
        ri0=(x1,y,z0); ri1=(x1,y,z1)
        self.quad(le0,le1,ridge1,ridge0)
        self.quad(ridge0,ridge1,ri1,ri0)
        # Cap triangular gables with real triangle topology, no degenerate faces.
        self.tri(le0,ridge0,ri0)
        self.tri(ri1,ridge1,le1)

    def encoded(self):
        if not self.vertices or not self.indices:
            raise ValueError("Empty mesh")
        return (struct.pack("<%sf" % (len(self.vertices)*3),
                            *(x for p in self.vertices for x in p)),
                struct.pack("<%sf" % (len(self.normals)*3),
                            *(x for p in self.normals for x in p)),
                struct.pack("<%sI" % len(self.indices), *self.indices))

def build(manifest: dict) -> bytes:
    if manifest.get("schema_version") != "1.0":
        raise ValueError("Expected schema_version 1.0")
    objects = manifest.get("objects")
    if not isinstance(objects,list) or not objects:
        raise ValueError("Manifest must include non-empty objects array")
    mats = {**DEFAULT_MATERIALS, **manifest.get("materials", {})}
    batches = {name: MeshBatch() for name in mats}
    for obj in objects:
        name = obj.get("name", "")
        material = obj.get("material", "")
        if not name or material not in batches:
            raise ValueError("Every object needs name and known material")
        center = obj.get("center", [])
        size = obj.get("size", [])
        if len(center) != 3 or len(size) != 3:
            raise ValueError(f"{name}: center and size must have three numbers")
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in center+size):
            raise ValueError(f"{name}: nonfinite/non-numeric dimensions")
        if any(v <= 0 for v in size):
            raise ValueError(f"{name}: sizes must be positive")
        if obj.get("kind") == "box":
            batches[material].box(center, size)
        elif obj.get("kind") == "gable_roof":
            batches[material].gable_roof(center, size)
        else:
            raise ValueError(f"{name}: unsupported primitive type")

    doc = {"asset": {"version":"2.0","generator":"3d-pipe manifest blockout v1"},
           "scene":0,"scenes":[{"nodes":[]}],"nodes":[],"meshes":[],
           "materials":[],"buffers":[{"byteLength":0}],"bufferViews":[],"accessors":[]}
    binary = bytearray()
    for name,batch in batches.items():
        if not batch.indices:
            continue
        mat_index = len(doc["materials"])
        rgba = mats[name]
        if len(rgba) != 4 or any(not isinstance(x,(int,float)) or x<0 or x>1 for x in rgba):
            raise ValueError(f"Invalid baseColorFactor for {name}")
        doc["materials"].append({
            "name":name, "pbrMetallicRoughness":{
                "baseColorFactor":rgba,
                "metallicFactor":0.45 if name=="brass" else 0,
                "roughnessFactor":0.85}, "doubleSided":True
        })
        access = []
        chunks = batch.encoded()
        for chunk, ctype, cnt, typ, target in [
            (chunks[0],5126,len(batch.vertices),"VEC3",34962),
            (chunks[1],5126,len(batch.normals),"VEC3",34962),
            (chunks[2],5125,len(batch.indices),"SCALAR",34963)]:
            while len(binary)%4: binary.append(0)
            start = len(binary)
            binary.extend(chunk)
            view_id = len(doc["bufferViews"])
            doc["bufferViews"].append({"buffer":0, "byteOffset":start,
                                       "byteLength":len(chunk), "target":target})
            acc_id = len(doc["accessors"])
            doc["accessors"].append({"bufferView":view_id, "componentType":ctype,
                                     "count":cnt, "type":typ})
            access.append(acc_id)
        doc["meshes"].append({"name":name, "primitives":[{
            "attributes":{"POSITION":access[0],"NORMAL":access[1]},
            "indices":access[2], "material":mat_index, "mode":4}]})
        doc["nodes"].append({"mesh":len(doc["meshes"])-1})
        doc["scenes"][0]["nodes"].append(len(doc["nodes"])-1)

    doc["buffers"][0]["byteLength"] = len(binary)
    j = json.dumps(doc, separators=(",",":"), sort_keys=True).encode("utf8")
    j += b" " * (-len(j)%4)
    binary.extend(b"\0" * (-len(binary)%4))
    total = 12+8+len(j)+8+len(binary)
    return (struct.pack("<4sII", b"glTF",2,total)
            +struct.pack("<I4s",len(j),b"JSON")+j
            +struct.pack("<I4s",len(binary),b"BIN\x00")+binary)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args = parser.parse_args()
    result = build(json.loads(args.manifest.read_text(encoding="utf8")))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_bytes(result)
    print(f"Exported {args.out} ({len(result)} bytes)")

if __name__ == "__main__":
    main()
