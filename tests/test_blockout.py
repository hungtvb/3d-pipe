"""Test manifest-to-GLB exporter and budget enforcement offline."""
import json
from pathlib import Path
import tempfile
import unittest

from pipeline.build_blockout import build
from pipeline.glb_gate import inspect_glb


ROOT = Path(__file__).resolve().parents[1]


class BlockoutTest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(
            (ROOT / "examples/village-blockout/scene.json").read_text()
        )

    def test_deterministic_and_batched(self):
        a = build(self.manifest)
        b = build(self.manifest)
        self.assertEqual(a, b)
        with tempfile.TemporaryDirectory() as directory:
            asset = Path(directory) / "village.glb"
            asset.write_bytes(a)
            audit = inspect_glb(asset, triangle_budget=2500)
        self.assertTrue(audit["checks_passed"], audit["errors"])
        self.assertGreater(audit["triangles"], 600)
        self.assertLessEqual(audit["mesh_primitives"], 8)
        self.assertEqual(audit["embedded_images"], 0)

    def test_reject_invalid_dimensions(self):
        self.manifest["objects"][0]["size"] = [0, 1, 1]
        with self.assertRaises(ValueError):
            build(self.manifest)

    def test_reject_invalid_material(self):
        self.manifest["objects"][0]["material"] = "missing"
        with self.assertRaises(ValueError):
            build(self.manifest)

    def test_reject_unknown_schema(self):
        self.manifest["schema_version"] = "9.9"
        with self.assertRaises(ValueError):
            build(self.manifest)


if __name__ == "__main__":
    unittest.main()
