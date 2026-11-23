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
        cls.loose = M.pairs(D.GEAR_BACKLASH_LOOSE)

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

    def test_loose_spares_fix_a_worst_case_cut(self):
        for p in self.loose:
            with self.subTest(pair=p.name):
                bl = M.backlash(p, fat=M.LASER_FAT, samples=3)
                self.assertIsNotNone(bl)
                self.assertGreaterEqual(bl, M.BACKLASH_RANGE[0])

    def test_meshing_gears_overlap_in_height(self):
        parts = {p.name: p for p in D.gears()}
        for p in self.pairs:
            za = parts[p.a].placed()[0].BoundingBox()
            zb = parts[p.b].placed()[0].BoundingBox()
            with self.subTest(pair=p.name):
                self.assertGreaterEqual(min(za.zmax, zb.zmax) - max(za.zmin, zb.zmin), 0.95 * D.T040)   # >= 95 % of the face

    def test_tuning_spares_are_thinner_versions_of_every_laser_gear(self):
        laser = {p.name for p in D.gears() if p.kind == "scs"}
        spares = {p.name: p for p in D.mesh_tuning_gears()}
        self.assertEqual(set(spares), {n + "_L" for n in laser})
        nominal = {p.name: p for p in D.gears()}
        for n in laser:
            with self.subTest(gear=n):
                self.assertLess(spares[n + "_L"].profile.poly.area, nominal[n].profile.poly.area)


class StackTests(unittest.TestCase):
    """The approved assembly fixes (assembly/FINDINGS.md) are in the CAD."""

    def test_crystal_screws_pass_every_layer_into_their_nuts(self):
        hw = {p.name: p for p in D.hardware()}
        screws, nuts = hw["screw_crystal"].placed(), hw["nut_crystal"].placed()
        shell = D.upper_shell().placed()[0]
        spiders = [D.spider("crystal_seat_spider", D.SEAT_R_IN, D.T040, D.Z_SEAT),
                   D.spider("crystal_frame_spider", D.CRYSTAL_R + D.CRYSTAL_CLEAR, D.T063, D.Z_FRAME)]
        crystal = D.crystal().placed()[0]
        for s, n in zip(screws, nuts):
            sb, nb = s.BoundingBox(), n.BoundingBox()
            self.assertAlmostEqual(sb.zmax, D.Z_TOP, places=6)          # flush head
            self.assertGreaterEqual(nb.zmax - sb.zmin, D.RETAIN_NUT[1] - 0.05)   # full nut engaged
            for other in [shell, crystal] + [sp.placed()[0] for sp in spiders]:
                self.assertLess(s.intersect(other).Volume(), 1e-6)

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
