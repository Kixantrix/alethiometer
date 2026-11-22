import unittest

import cadquery as cq

import build
import design as D


class HingeStopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hinge = D.hinge()
        cls.parts = cls.hinge + [D.upper_shell(), D.lid(), D.lid_overlay()]
        cls.pin = next(p for p in cls.hinge if p.name == "hinge_stop_pin").placed()[0]
        cls.leaf = next(p for p in cls.hinge if p.name == "hinge_leaf_lid").placed()[0]

    def test_stop_engages_at_135_degrees(self):
        for angle in (0, 90, 130, 134, 134.9):
            with self.subTest(angle=angle):
                leaf = self.leaf.moved(D.lid_open_location(angle))
                self.assertGreater(self.pin.distance(leaf), 0.001)
        leaf = self.leaf.moved(D.lid_open_location(135))
        self.assertLess(self.pin.distance(leaf), 1e-6)
        self.assertLess(self.pin.intersect(leaf).Volume(), 1e-6)
        overtravel = self.leaf.moved(D.lid_open_location(135.1))
        self.assertGreater(self.pin.intersect(overtravel).Volume(), 0.01)

    def test_lid_clears_hinge_and_shell_through_opening(self):
        self.assertEqual(build.interference(self.parts, lid_angles=range(136)), [])

    def test_stop_parts_are_manufacturable(self):
        self.assertEqual(build.manufacturability(self.hinge), [])
        for part in self.hinge:
            with self.subTest(part=part.name):
                self.assertTrue(part.solid.isValid())

    def test_removable_mounts_reach_threads_without_bottoming(self):
        body_engagement = 6 - (2 * D.T040 + D.T063)
        bracket_engagement = 5 - D.T040
        self.assertGreaterEqual(body_engagement, 2.0)
        self.assertLess(body_engagement + 0.6, 3.5)
        self.assertGreaterEqual(bracket_engagement, 2.0)
        self.assertLess(bracket_engagement + 0.6, 5.0)
        lid_grip = 2 * D.T040 + D.T063
        self.assertGreaterEqual(6 - lid_grip, 1.3 + 0.25)

    def test_finished_holes_follow_the_clamp_path(self):
        parts = {p.name: p for p in self.hinge}
        shell = D.upper_shell().placed()[0]
        backing = parts["hinge_backing_body"].placed()[0]
        leaf = parts["hinge_leaf_body"].placed()[0]
        for y, z in D.hinge_body_mounts():
            probe = cq.Solid.makeCylinder(D.HINGE_MOUNT_CLEAR / 2 - 0.01, 5,
                    cq.Vector(D.HINGE_X - D.T040 - D.T063 - 0.1, y, D.Z_TOP + z),
                    cq.Vector(1, 0, 0))
            for name, sheet in (("shell", shell), ("backing", backing), ("leaf", leaf)):
                with self.subTest(y=y, z=z, sheet=name):
                    self.assertLess(probe.intersect(sheet).Volume(), 1e-6)
        self.assertGreater(D.upper_shell().tray.formed().Volume(), D.upper_shell().solid.Volume())
        self.assertGreater(D.lid().tray.formed().Volume(), D.lid().solid.Volume())


if __name__ == "__main__":
    unittest.main()
