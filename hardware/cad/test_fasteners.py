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


class PowerSwitchSlotTests(unittest.TestCase):
    def test_a_fingernail_reaches_behind_the_slider_at_both_ends(self):
        """A 1 mm × 2 mm nail tip passes the wall to the slider's back face, on or off."""
        import cadquery as cq
        import layout as L
        tray = D.lower_tray().placed()[0]
        wall_out = L.CASE_W / 2
        aw, _, z0, z1 = L.SLIDE_SW_ACT
        for pos, push in ((0.0, -1), (L.SLIDE_SW_TRAVEL, +1)):      # off: nail below it, on: above
            y_face = L.SW_POWER_PIN1_Y + pos + (0.0 if push < 0 else aw)
            y0 = y_face - 1.0 if push < 0 else y_face
            nail = cq.Solid.makeBox(D.T040 + L.SLIDE_SW_TIP_GAP + 0.3, 1.0, 2.0,
                                    cq.Vector(wall_out - D.T040 - L.SLIDE_SW_TIP_GAP - 0.3, y0,
                                              D.Z_CARRIER_TOP + (z0 + z1) / 2 - 1.0))
            with self.subTest(position="off" if pos == 0 else "on"):
                self.assertLess(nail.intersect(tray).Volume(), 1e-6)


if __name__ == "__main__":
    unittest.main()
