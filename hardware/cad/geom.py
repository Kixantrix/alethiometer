"""2D profile primitives shared by every flat part.

A Profile is a shapely polygon (outline + polygonal holes) plus a list of round
holes kept as true circles, so DXF exports use CIRCLE entities (clean quotes at
SendCutSend) while solids get exact cylinders.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import cadquery as cq
import ezdxf
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union

ARC_SEG = 0.35        # target chord length (mm) for polygonal arcs
ARC_MAX = 24          # cap on segments per quarter circle


def quad_segs(r: float) -> int:
    """Segments per quarter circle: fine enough for laser cutting, light enough for STEP."""
    return max(3, min(ARC_MAX, math.ceil(r * math.pi / 2 / ARC_SEG)))


def circle(x: float, y: float, r: float) -> Polygon:
    return Point(x, y).buffer(r, quad_segs=quad_segs(r))


def annulus(r_in: float, r_out: float, x: float = 0.0, y: float = 0.0) -> Polygon:
    return circle(x, y, r_out).difference(circle(x, y, r_in))


def octagon(width: float, chamfer: float) -> Polygon:
    """Square of `width` across flats with 45° corner chamfers of leg `chamfer`.
    CCW; edge 0 is the right (+x) side, then TR, top, TL, left, BL, bottom, BR."""
    h, c = width / 2, chamfer
    return Polygon([(h, -(h - c)), (h, h - c), (h - c, h), (-(h - c), h),
                    (-h, h - c), (-h, -(h - c)), (-(h - c), -h), (h - c, -h)])


def offset(poly: Polygon, d: float) -> Polygon:
    """Mitred offset (keeps octagon chamfers straight). d>0 grows."""
    return poly.buffer(d, join_style="mitre", mitre_limit=10)


def rect(cx: float, cy: float, w: float, h: float, angle_deg: float = 0.0) -> Polygon:
    r = Polygon([(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)])
    r = affinity.rotate(r, angle_deg, origin=(0, 0))
    return affinity.translate(r, cx, cy)


def slot(x0: float, y0: float, x1: float, y1: float, width: float) -> Polygon:
    return LineString([(x0, y0), (x1, y1)]).buffer(width / 2, quad_segs=quad_segs(width / 2))


def polar(r: float, deg: float) -> tuple[float, float]:
    a = math.radians(deg)
    return r * math.cos(a), r * math.sin(a)


def clock(r: float, deg_cw_from_12: float) -> tuple[float, float]:
    """Dial convention: 0° = 12 o'clock (+y), clockwise positive."""
    return polar(r, 90.0 - deg_cw_from_12)


def _largest(geom) -> Polygon:
    if isinstance(geom, MultiPolygon):
        return max(geom.geoms, key=lambda g: g.area)
    return geom


@dataclass
class Profile:
    """Flat part outline. `holes` are exact circles (x, y, r)."""
    poly: Polygon
    holes: list[tuple[float, float, float]] = field(default_factory=list)

    def cut(self, shape: Polygon) -> "Profile":
        self.poly = _largest(self.poly.difference(shape))
        return self

    def add(self, shape: Polygon) -> "Profile":
        self.poly = _largest(unary_union([self.poly, shape]))
        return self

    def hole(self, x: float, y: float, d: float) -> "Profile":
        self.holes.append((x, y, d / 2))
        return self

    def transformed(self, fn) -> "Profile":
        """Apply a shapely affine fn (geom -> geom) to outline and holes."""
        pts = [fn(Point(x, y)) for x, y, _ in self.holes]
        return Profile(fn(self.poly), [(p.x, p.y, h[2]) for p, h in zip(pts, self.holes)])

    def mirrored_y(self) -> "Profile":
        return self.transformed(lambda g: affinity.scale(g, 1, -1, origin=(0, 0)))

    @property
    def area(self) -> float:
        return self.poly.area - sum(math.pi * r * r for _, _, r in self.holes)

    @property
    def bbox(self) -> tuple[float, float]:
        x0, y0, x1, y1 = self.poly.bounds
        return x1 - x0, y1 - y0

    def thin_web_area(self, min_web: float) -> float:
        """Area of material narrower than min_web (laser manufacturability)."""
        opened = self.poly.buffer(-min_web / 2).buffer(min_web / 2)
        return self.poly.difference(opened).area


def _wire(coords) -> cq.Wire:
    pts = [cq.Vector(x, y, 0) for x, y in list(coords)[:-1]]
    return cq.Wire.makePolygon(pts, close=True)


def profile_solid(profile: Profile, thickness: float) -> cq.Solid:
    poly = profile.poly.simplify(0.002)
    face = cq.Face.makeFromWires(_wire(poly.exterior.coords),
                                 [_wire(i.coords) for i in poly.interiors])
    solid = cq.Solid.extrudeLinear(face, cq.Vector(0, 0, thickness))
    if profile.holes:
        cyls = [cq.Solid.makeCylinder(r, thickness + 2, cq.Vector(x, y, -1))
                for x, y, r in profile.holes]
        solid = solid.cut(*cyls)
    return solid


def write_dxf(path, profile: Profile, bend_lines=()) -> None:
    """Single-part DXF in millimetres: CUT layer outlines, BEND layer centre lines."""
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.layers.add("CUT", color=7)
    doc.layers.add("BEND", color=1, linetype="DASHED")
    msp = doc.modelspace()
    poly = profile.poly.simplify(0.002)
    for ring in [poly.exterior, *poly.interiors]:
        msp.add_lwpolyline(list(ring.coords)[:-1], close=True, dxfattribs={"layer": "CUT"})
    for x, y, r in profile.holes:
        msp.add_circle((x, y), r, dxfattribs={"layer": "CUT"})
    for (x0, y0), (x1, y1) in bend_lines:
        msp.add_line((x0, y0), (x1, y1), dxfattribs={"layer": "BEND"})
    doc.saveas(path)
