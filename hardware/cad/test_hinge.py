import unittest

import cadquery as cq

import build
import design as D


class HingeTests(unittest.TestCase):
    """The lid opens past flat until the hinge's own leaves close on each other."""

    @classmethod
    def setUpClass(cls):
        cls.hinge = D.hinge()
        cls.parts = cls.hinge + [D.upper_shell(), D.lid(), D.lid_overlay()]
        named = {p.name: p for p in cls.hinge}
        cls.body_leaf = named["hinge_leaf_body"].placed()[0]
        cls.lid_leaf = named["hinge_leaf_lid"].placed()[0]

    def test_leaves_are_the_stop(self):
        stop = D.LID_OPEN_ANGLE
        self.assertGreater(stop, 180.0)
        for angle in (0, 90, 180, stop - 1.0):
            with self.subTest(angle=angle):
                leaf = self.lid_leaf.moved(D.lid_open_location(angle))
                self.assertGreater(self.body_leaf.distance(leaf), 0.001)
        at_stop = self.lid_leaf.moved(D.lid_open_location(stop))
        self.assertLess(self.body_leaf.distance(at_stop), 0.05)
        past = self.lid_leaf.moved(D.lid_open_location(stop + 2.0))
        self.assertGreater(self.body_leaf.intersect(past).Volume(), 0.01)

    def test_lid_clears_case_and_hardware_through_full_travel(self):
        angles = [*range(0, int(D.LID_OPEN_ANGLE), 5), D.LID_OPEN_ANGLE - 0.5]
        self.assertEqual(build.interference(self.parts, lid_angles=angles), [])

    def test_parts_are_valid_and_manufacturable(self):
        self.assertEqual(build.manufacturability(self.hinge), [])
        for part in self.hinge:
            with self.subTest(part=part.name):
                self.assertTrue(part.solid.isValid())

    def test_outside_screw_heads_are_flush(self):
        for part in self.hinge:
            if part.name.endswith(tuple(f"_screw_{i}" for i in range(1, 9))):
                with self.subTest(screw=part.name):
                    self.assertAlmostEqual(part.placed()[0].BoundingBox().xmax, D.HINGE_X + D.T040, places=6)

    def test_screws_pass_through_their_nuts(self):
        body_grip = 2 * D.T040 + D.T063 + D.HINGE_NUT_H
        lid_grip = 2 * D.T040 + D.T063 + 1.3
        self.assertGreater(D.HINGE_BODY_SCREW_LEN - body_grip, 0.3)
        self.assertGreater(6 - lid_grip, 0.3)

    def test_holes_line_up_through_leaf_wall_and_backing(self):
        named = {p.name: p for p in self.hinge}
        shell = D.upper_shell().placed()[0]
        backing = named["hinge_backing_body"].placed()[0]
        for y, z in D.hinge_body_mounts():
            probe = cq.Solid.makeCylinder(D.HINGE_MOUNT_CLEAR / 2 - 0.01, 5,
                                          cq.Vector(D.HINGE_X - D.T040 - D.T063 - 0.1, y, D.Z_TOP + z),
                                          cq.Vector(1, 0, 0))
            for name, sheet in (("shell", shell), ("backing", backing), ("leaf", self.body_leaf)):
                with self.subTest(y=y, sheet=name):
                    self.assertLess(probe.intersect(sheet).Volume(), 1e-6)


if __name__ == "__main__":
    unittest.main()
