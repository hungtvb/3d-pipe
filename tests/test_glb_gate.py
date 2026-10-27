"""GLB gate tests run without Blender, npm, or network."""
from pathlib import Path
import tempfile
import unittest

from pipeline.glb_gate import inspect_glb, make_fixture, read_glb


class GLBGateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.file = Path(self.temp.name) / "scene.glb"
        make_fixture(self.file)

    def test_fixture_passes_and_is_deterministic(self):
        original = self.file.read_bytes()
        report = inspect_glb(self.file)
        self.assertTrue(report["checks_passed"], report["errors"])
        self.assertEqual(report["triangles"], 2)
        make_fixture(self.file)
        self.assertEqual(self.file.read_bytes(), original)

    def test_budget_enforced(self):
        result = inspect_glb(self.file, triangle_budget=1)
        self.assertFalse(result["checks_passed"])

    def test_corrupt_header_rejected(self):
        self.file.write_bytes(b"garbage")
        with self.assertRaises(ValueError):
            read_glb(self.file)

    def test_corrupt_declared_size_rejected(self):
        with self.file.open("ab") as f:
            f.write(b"EXTRA")
        with self.assertRaises(ValueError):
            read_glb(self.file)


if __name__ == "__main__":
    unittest.main()
