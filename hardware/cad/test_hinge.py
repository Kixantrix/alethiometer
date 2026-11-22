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
        lid_grip = 2 * D.T040 + D.HINGE_LID_WASHER_T + D.HINGE_LID_NUT_H
        self.assertGreater(D.HINGE_BODY_SCREW_LEN - body_grip, 0.3)
        self.assertGreater(D.HINGE_LID_SCREW_LEN - lid_grip, 0.3)

    def test_lid_leaf_stays_on_the_flat_of_the_lid_wall(self):
        self.assertLessEqual(D.HINGE_LID_HEIGHT, D.LID_H - D.BEND_IR - D.T040 + 1e-9)
        top = self.lid_leaf.BoundingBox().zmax
        self.assertLessEqual(top, D.Z_TOP + D.HINGE_LID_HEIGHT + 1e-6)

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


class HingeToolingTests(unittest.TestCase):
    """The drill guide sits on the closed case over the hinge; the trim gauge on the hinge."""

    @classmethod
    def setUpClass(cls):
        cls.guide, cls.gauge = D.hinge_drill_guide(), D.hinge_trim_gauge()
        cls.fixed = D.hinge() + [D.upper_shell(), D.lid(), D.lid_overlay()]

    def test_guide_and_gauge_fit_over_the_mounted_hinge(self):
        for tool in (self.guide, self.gauge):
            shape = tool.placed()[0]
            for part in self.fixed:
                for s in part.placed():
                    with self.subTest(tool=tool.name, part=part.name):
                        self.assertLess(shape.intersect(s).Volume(), 1e-3)

    def test_guide_lip_rests_on_the_lid_and_plate_on_the_leaves(self):
        guide = self.guide.placed()[0]
        lid = D.lid().placed()[0]
        leaf = next(p for p in D.hinge() if p.name == "hinge_leaf_body").placed()[0]
        self.assertLess(guide.distance(lid), 0.01)
        self.assertLess(guide.distance(leaf), 0.01)

    def test_guide_holes_are_on_the_screw_axes(self):
        guide = self.guide.placed()[0]
        seats = [(y, z, D.HINGE_MOUNT_CLEAR) for y, z in D.hinge_body_mounts()]
        seats += [(y, D.HINGE_LID_MOUNT_Z, D.HINGE_LID_CLEAR) for y in D.HINGE_LID_MOUNTS]
        for y, z, d in seats:
            probe = cq.Solid.makeCylinder(d / 2 - 0.01, 10, cq.Vector(D.HINGE_X - 5, y, D.Z_TOP + z),
                                          cq.Vector(1, 0, 0))
            with self.subTest(y=y, z=z):
                self.assertLess(probe.intersect(guide).Volume(), 1e-6)

    def test_tools_are_manufacturable(self):
        self.assertEqual(build.manufacturability([self.guide, self.gauge]), [])
        self.assertEqual(len(self.guide.bends), 1)
        for tool in (self.guide, self.gauge):
            self.assertTrue(tool.solid.isValid())


if __name__ == "__main__":
    unittest.main()
