import unittest

import design as D

LASER_TOL = 0.13


def bbox(part, i=0):
    return part.placed()[i].BoundingBox()


class TurnedKitTests(unittest.TestCase):
    """Every gear and hand is positioned by a turned shoulder or a flush end, never by measuring."""

    @classmethod
    def setUpClass(cls):
        cls.p = {p.name: p for p in D.gears() + D.hands() + D.arbors()}

    def shoulder_z(self, part, index):
        """Top of segment `index` of a turned part (absolute z)."""
        z0 = bbox(part).zmin
        return z0 + sum(h for *_, h in part.drawing["segments"][: index + 1])

    def test_gears_sit_on_a_collar_or_flush_with_the_tube_end(self):
        p = self.p
        self.assertAlmostEqual(bbox(p[f"gear_hand_I_{D.Z_HAND}T"]).zmin, self.shoulder_z(p["arbor_I"], 1), 6)
        for name, arbor in (("II", "arbor_II"), ("III", "arbor_III")):
            self.assertAlmostEqual(bbox(p[f"gear_hand_{name}_{D.Z_HAND}T"]).zmin, bbox(p[arbor]).zmin, 6)
        self.assertAlmostEqual(bbox(p[f"gear_needle_{D.Z_NEEDLE}T"]).zmin, bbox(p["arbor_needle"]).zmin, 6)
        for tr in D.TRAINS:
            n = tr["name"]
            with self.subTest(sensor=n):
                self.assertAlmostEqual(bbox(p[f"gear_sensor_{n}_{D.Z_SENSOR}T"]).zmin,
                                       self.shoulder_z(p[f"shaft_sensor_{n}"], 2), 6)
            with self.subTest(knob=n):
                self.assertAlmostEqual(bbox(p[f"knob_{n}_{D.Z_KNOB}T"]).zmin, self.shoulder_z(p["shaft_knob"], 1), 6)

    def test_hands_sit_flush_with_their_arbor_or_on_its_shoulder(self):
        p = self.p
        for hand, arbor in (("hand_needle", "arbor_needle"), ("hand_III", "arbor_III"), ("hand_II", "arbor_II")):
            with self.subTest(hand=hand):
                self.assertAlmostEqual(bbox(p[hand]).zmax, bbox(p[arbor]).zmax, 6)
        self.assertAlmostEqual(bbox(p["hand_I"]).zmin, self.shoulder_z(p["arbor_I"], 2), 6)
        self.assertAlmostEqual(bbox(p["hand_cap_rosette"]).zmax, bbox(p["arbor_I"]).zmax, 6)

    def test_hand_setting_tool_clears_inner_arbor_and_bears_on_its_own(self):
        for hole, inner, rim in D.HAND_TOOL_HOLES:
            with self.subTest(hole=hole):
                self.assertGreater(hole - LASER_TOL, inner + 0.05)
                self.assertLess(hole + LASER_TOL, rim - 0.2)

    def test_shafts_have_endshake(self):
        p = self.p
        for i in range(len(D.TRAINS)):
            self.assertAlmostEqual(D.Z_P1 - bbox(p["magnet_cup"], i).zmax, D.CUP_GAP, 6)
        sleeve_top = bbox(p["sleeve_knob"]).zmax
        self.assertAlmostEqual(D.Z_P2 - sleeve_top, D.KNOB_ENDSHAKE, 6)
        self.assertGreater(D.CUP_GAP, 0.1)
        self.assertGreater(D.KNOB_ENDSHAKE, 0.1)

    def test_crown_clip_is_retained_by_the_wall(self):
        self.assertGreater(D.ECLIP["od"], 3.1 + LASER_TOL)     # lower-tray crown hole is Ø3.1
        self.assertLess(D.ROD_332, 3.1 - LASER_TOL)
        self.assertGreater(D.ECLIP["groove_w"], D.ECLIP["t"])

    def test_turned_parts_are_valid_solids(self):
        for p in D.arbors():
            if p.kind == "turned":
                with self.subTest(part=p.name):
                    self.assertTrue(D.turned_solid(p.drawing["segments"]).isValid())


if __name__ == "__main__":
    unittest.main()
