import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "assembly"))
import guide as G  # noqa: E402


class AssemblyGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guide = G.load()
        cls.cat = G.Catalogue(G.design_parts())

    def test_every_part_is_installed_by_the_guide(self):
        self.assertEqual(G.validate(self.guide, self.cat), [])

    def test_generated_docs_are_current(self):
        md, findings = G.write_markdown(self.guide)
        self.assertEqual(G.ASSEMBLY_MD.read_text(encoding="utf-8"), md,
                         "ASSEMBLY.md is stale: run python hardware/assembly/guide.py")
        self.assertEqual(G.FINDINGS_MD.read_text(encoding="utf-8"), findings,
                         "FINDINGS.md is stale: run python hardware/assembly/guide.py")

    def test_parts_arrive_and_leave_at_their_motions(self):
        runs = {r["step"]["id"]: r for r in G.replay(self.guide, self.cat)}
        r = runs["hands"]
        seg = r["tracks"]["hand_III#0"][0]
        self.assertFalse(G.present(r, "hand_III#0", seg.t0))
        self.assertTrue(G.present(r, "hand_III#0", seg.t1))
        last = r["tracks"]["hand_setting_tool#0"][-1]
        self.assertTrue(last.remove)
        self.assertFalse(G.present(r, "hand_setting_tool#0", last.t1 + 0.01))


if __name__ == "__main__":
    unittest.main()
