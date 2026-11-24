"""Every gear pair meshes: turns freely, readable backlash, survives laser tolerance (mesh.py)."""
import unittest

import cadquery as cq

import design as D
import layout as L
import mesh as M


class GearMeshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pairs = M.pairs()
        cls.tight = [p for p in M.pairs(driven=D.GEAR_BACKLASH) if p.b in D.DRIVEN_GEARS]

    def test_centre_distances_are_theoretical_plus_slop(self):
        for p in self.pairs:
            with self.subTest(pair=p.name):
                self.assertAlmostEqual(p.nominal_distance, p.theoretical_distance + L.CENTER_SLOP, places=6)

    def test_every_pair_turns_freely(self):
        for p in self.pairs:
            with self.subTest(pair=p.name):
                self.assertTrue(M._free_rotation(p))

    def test_installed_tooth_phase_meshes(self):
        """The CAD placements put a tooth of one gear into a gap of the other."""
        for p in self.pairs:
            with self.subTest(pair=p.name):
                self.assertLessEqual(M.contact(p), M.OVERLAP)

    def test_backlash_is_readable(self):
        lo, hi = M.BACKLASH_RANGE
        for p in self.pairs:
            with self.subTest(pair=p.name):
                bl = M.backlash(p)
                self.assertGreaterEqual(bl, lo)
                self.assertLessEqual(bl, hi)

    def test_a_typical_cut_still_runs(self):
        """Teeth 0.03 mm fat per side and centres 0.05 mm close: no spares needed."""
        for p in self.pairs:
            with self.subTest(pair=p.name):
                self.assertIsNotNone(M.backlash(p, shrink=0.05, fat=0.03, samples=3))

    def test_a_worst_case_cut_still_runs(self):
        """Every laser-cut tooth 0.065 mm fat per side (SendCutSend's worst case): no swaps needed."""
        for p in self.pairs:
            with self.subTest(pair=p.name):
                bl = M.backlash(p, fat=M.LASER_FAT, samples=3)
                self.assertIsNotNone(bl)
                self.assertGreaterEqual(bl, M.BACKLASH_RANGE[0])

    def test_tight_alternates_are_readable_and_run_on_a_typical_cut(self):
        lo, hi = M.BACKLASH_RANGE
        self.assertEqual(len(self.tight), 4)
        for p in self.tight:
            with self.subTest(pair=p.name):
                bl = M.backlash(p)
                self.assertTrue(lo <= bl <= hi)
                self.assertLess(bl, M.backlash(next(q for q in self.pairs if q.name == p.name)))
                self.assertIsNotNone(M.backlash(p, shrink=0.05, fat=0.03, samples=3))

    def test_meshing_gears_overlap_in_height(self):
        parts = {p.name: p for p in D.gears()}
        for p in self.pairs:
            za = parts[p.a].placed()[0].BoundingBox()
            zb = parts[p.b].placed()[0].BoundingBox()
            with self.subTest(pair=p.name):
                self.assertGreaterEqual(min(za.zmax, zb.zmax) - max(za.zmin, zb.zmin), 0.95 * D.T040)   # >= 95 % of the face

    def test_alternates_are_fuller_versions_of_the_driven_gears(self):
        alts = {p.name: p for p in D.alternate_gears()}
        self.assertEqual(set(alts), {n + "_T" for n in D.DRIVEN_GEARS})
        nominal = {p.name: p for p in D.gears()}
        for n in D.DRIVEN_GEARS:
            with self.subTest(gear=n):
                self.assertGreater(alts[n + "_T"].profile.poly.area, nominal[n].profile.poly.area)


class StackTests(unittest.TestCase):
    """The approved assembly fixes (assembly/FINDINGS.md) are in the CAD."""

    def test_crystal_is_glued_under_the_top_face_clear_of_the_hands(self):
        crystal = D.crystal().placed()[0].BoundingBox()
        self.assertAlmostEqual(crystal.zmax, D.Z_TOPFACE, places=6)
        self.assertGreaterEqual(D.CRYSTAL_LAND, 1.5)                        # glue land round the window
        self.assertLess(D.CRYSTAL_R, D.SLOT_R0 - 2.0)                       # glue stays clear of the grille
        self.assertGreaterEqual(D.summary()["crystal_clearance"], 1.5)       # hand cap below the crystal
        self.assertEqual(D.HAND_STANDOFF, D.GEAR_STANDOFF)                  # one standoff part
        shell = D.upper_shell().placed()[0]
        self.assertLess(D.crystal().placed()[0].intersect(shell).Volume(), 1e-6)

    def test_knob_shafts_stand_proud_of_p2_and_sensor_shafts_do_not(self):
        parts = {p.name: p for p in D.arbors()}
        knob_top = parts["shaft_knob"].placed()[0].BoundingBox().zmax
        sensor_top = parts["shaft_sensor_I"].placed()[0].BoundingBox().zmax
        self.assertAlmostEqual(knob_top - D.Z_P2_TOP, D.KNOB_TIP_PROUD, places=6)
        self.assertAlmostEqual(sensor_top, D.Z_P2_TOP, places=6)

    def test_alignment_pins_slide_through_both_bushings(self):
        pins = [p for p in D.tooling() if p.name.startswith("align_pin")]
        bushings = {p.name: p for p in D.arbors() if p.name.startswith("bushing_")}
        for pin in pins:
            for s in pin.placed():
                bb = s.BoundingBox()
                self.assertLess(bb.zmin, D.Z_P1)
                self.assertGreater(bb.zmax, D.Z_P2_TOP)
                for b in bushings.values():
                    for bs in b.placed():
                        self.assertLess(s.intersect(bs).Volume(), 1e-6)


if __name__ == "__main__":
    unittest.main()
