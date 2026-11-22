import unittest

import design as D


class FlushFastenerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.floor = D.lower_tray()
        cls.top = D.upper_shell()
        cls.screws = {p.name: p for p in D.hardware() if p.name.startswith("screw_")}

    def test_external_heads_are_flush_and_clear_the_case(self):
        for name, case, face_z in (
            ("screw_floor", self.floor, 0.0),
            ("screw_top", self.top, D.Z_TOP),
        ):
            sheet = case.placed()[0]
            for screw in self.screws[name].placed():
                with self.subTest(screw=name):
                    bounds = screw.BoundingBox()
                    outer_z = bounds.zmin if name == "screw_floor" else bounds.zmax
                    self.assertAlmostEqual(outer_z, face_z, places=6)
                    self.assertLess(sheet.intersect(screw).Volume(), 1e-6)

    def test_seats_leave_material_and_keep_laser_pilot_holes(self):
        depth = (D.CASE_SCREW_HEAD_D - D.POST_HOLE) / 2
        self.assertGreater(D.T040 - depth, 0.4)
        for case in (self.floor, self.top):
            with self.subTest(case=case.name):
                self.assertTrue(case.solid.isValid())
                self.assertLess(case.solid.Volume(), case.tray.formed().Volume())
                self.assertTrue(all(2 * r == D.POST_HOLE for _, _, r in case.profile.holes))

    def test_screw_lengths_reach_the_standoffs(self):
        floor_grip = D.Z_CARRIER_TOP
        top_grip = D.Z_TOP - (D.Z_P2_TOP + D.HAND_STANDOFF)
        for engagement, post_h in (
            (D.FLOOR_SCREW_LEN - floor_grip, D.CARRIER_STANDOFF),
            (D.TOP_SCREW_LEN - top_grip, D.HAND_STANDOFF),
        ):
            with self.subTest(engagement=engagement):
                self.assertGreaterEqual(engagement, D.CASE_SCREW_D)
                self.assertLess(engagement, post_h)

    def test_knob_clamps_clear_plates_and_engage_nuts(self):
        gears = {p.name: p for p in D.gears()}
        hardware = {p.name: p for p in D.hardware()}
        for train in D.TRAINS:
            name = train["name"]
            base = gears[f"knob_{name}_31T_base"].placed()[0]
            layers = gears[f"knob_{name}_31T_layers"].placed()
            screws = hardware[f"knob_{name}_clamp_screw"].placed()
            nuts = hardware[f"knob_{name}_clamp_nut"].placed()
            for screw, nut in zip(screws, nuts):
                with self.subTest(train=name):
                    bounds = screw.BoundingBox()
                    self.assertAlmostEqual(bounds.zmin, D.LEVELS[0], places=6)
                    self.assertGreater(bounds.zmin - D.Z_P1_TOP, 0.4)
                    self.assertGreater(D.Z_P2 - bounds.zmax, 0.4)
                    self.assertGreater(bounds.zmax - nut.BoundingBox().zmax, 0.25)
                    for sheet in [base, *layers, nut]:
                        self.assertLess(sheet.intersect(screw).Volume(), 1e-6)


if __name__ == "__main__":
    unittest.main()
