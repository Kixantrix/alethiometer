"""Bent sheet-metal trays (floor + walls on every polygon edge).

Builds both the formed 3D solid (for STEP upload / assembly) and the flat
pattern with bend centre lines (for DXF upload), from SendCutSend's bend
spec for the material: inside radius `ir` and K-factor `k`.

Local frame: floor outer face on z=0, flanges rise to z=height, outer
polygon is the outer mould line of the walls.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import cadquery as cq
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from geom import Profile, offset


@dataclass
class WallCut:
    """Rectangular opening in a wall: tangential centre point (x, y) on the
    wall (local XY), width along the wall, z range (local), optional round ends."""
    x: float
    y: float
    width: float
    z0: float
    z1: float
    rounded: bool = False


@dataclass
class Edge:
    p0: tuple[float, float]
    e: tuple[float, float]   # unit direction p0 -> p1
    n: tuple[float, float]   # outward unit normal
    length: float
    a: float                 # wall start trim (inner-face mitre)
    b: float                 # wall end trim

    def at(self, s: float, u: float) -> tuple[float, float]:
        return (self.p0[0] + s * self.e[0] + u * self.n[0],
                self.p0[1] + s * self.e[1] + u * self.n[1])

    def local(self, x: float, y: float) -> tuple[float, float]:
        dx, dy = x - self.p0[0], y - self.p0[1]
        return dx * self.e[0] + dy * self.e[1], dx * self.n[0] + dy * self.n[1]


@dataclass
class Tray:
    outer: Polygon
    height: float
    t: float
    ir: float
    k: float
    relief: float = 1.0
    floor_cuts: list = field(default_factory=list)      # shapely polygons (local XY)
    floor_holes: list = field(default_factory=list)     # (x, y, d)
    wall_cuts: list[WallCut] = field(default_factory=list)

    # ---- derived geometry -------------------------------------------------
    @property
    def setback(self) -> float:          # outer mould line to bend tangent
        return self.ir + self.t

    @property
    def bend_allowance(self) -> float:
        return math.pi / 2 * (self.ir + self.k * self.t)

    @property
    def flange_flat(self) -> float:      # straight wall length above the bend
        return self.height - self.setback

    def edges(self) -> list[Edge]:
        pts = list(self.outer.exterior.coords)[:-1]
        if not Polygon(pts).exterior.is_ccw:
            pts.reverse()
        n = len(pts)
        raw = []
        for i in range(n):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
            L = math.hypot(x1 - x0, y1 - y0)
            e = ((x1 - x0) / L, (y1 - y0) / L)
            raw.append(((x0, y0), e, (e[1], -e[0]), L))

        def turn(i: int) -> float:       # exterior turn angle at vertex i
            e0, e1 = raw[i - 1][1], raw[i][1]
            return math.acos(max(-1.0, min(1.0, e0[0] * e1[0] + e0[1] * e1[1])))

        out = []
        for i, (p0, e, nrm, L) in enumerate(raw):
            a = self.t * math.tan(turn(i) / 2)
            b = self.t * math.tan(turn((i + 1) % n) / 2)
            out.append(Edge(p0, e, nrm, L, a, b))
        return out

    def floor_profile(self) -> Profile:
        prof = Profile(offset(self.outer, -self.setback))
        for c in self.floor_cuts:
            prof.cut(c)
        for x, y, d in self.floor_holes:
            prof.hole(x, y, d)
        return prof

    def _edge_for(self, x: float, y: float) -> tuple[int, Edge]:
        best = min(enumerate(self.edges()), key=lambda ie: abs(ie[1].local(x, y)[1]))
        return best

    def _bend_span(self, ed: Edge) -> tuple[float, float]:
        return ed.a + self.relief, ed.length - ed.b - self.relief

    # ---- formed solid -----------------------------------------------------
    def formed(self) -> cq.Solid:
        t, ir, H, sb = self.t, self.ir, self.height, self.setback
        parts = [_profile_solid(self.floor_profile(), t)]
        for ed in self.edges():
            s0, s1 = self._bend_span(ed)
            # canonical frame: X = s, Y = -u (inward), Z = z
            uc, zc = -sb, sb
            outer_mid = (uc + sb * math.cos(math.radians(-45)), zc + sb * math.sin(math.radians(-45)))
            inner_mid = (uc + ir * math.cos(math.radians(-45)), zc + ir * math.sin(math.radians(-45)))
            bend = (cq.Workplane("YZ", origin=(s0, 0, 0))
                    .moveTo(-uc, 0)
                    .threePointArc((-outer_mid[0], outer_mid[1]), (0, zc))
                    .lineTo(t, zc)
                    .threePointArc((-inner_mid[0], inner_mid[1]), (-uc, t))
                    .close().extrude(s1 - s0).val())
            wall = (cq.Workplane("YZ", origin=(ed.a, 0, 0))
                    .moveTo(0, zc).lineTo(t, zc).lineTo(t, H).lineTo(0, H).close()
                    .extrude(ed.length - ed.a - ed.b).val())
            ang = math.degrees(math.atan2(ed.e[1], ed.e[0]))
            for s in (bend, wall):
                parts.append(s.rotate(cq.Vector(), cq.Vector(0, 0, 1), ang)
                             .translate(cq.Vector(ed.p0[0], ed.p0[1], 0)))
        solid = parts[0].fuse(*parts[1:]).clean()
        cuts = [self._wall_cut_solid(c) for c in self.wall_cuts]
        if cuts:
            solid = solid.cut(*cuts)
        return solid

    def _wall_cut_solid(self, c: WallCut) -> cq.Solid:
        _, ed = self._edge_for(c.x, c.y)
        s, _ = ed.local(c.x, c.y)
        depth = 4 * self.t
        wp = cq.Workplane("YZ", origin=(s - c.width / 2, 0, 0))
        if c.rounded:
            h = c.z1 - c.z0
            wp2 = cq.Workplane("XZ", origin=(0, 0, 0)).center(s, (c.z0 + c.z1) / 2)
            wp2 = wp2.slot2D(c.width, h) if c.width > h + 0.01 else wp2.circle(h / 2)
            body = wp2.extrude(depth / 2, both=True).val()
        else:
            body = (wp.moveTo(-depth / 2, c.z0).lineTo(depth / 2, c.z0)
                    .lineTo(depth / 2, c.z1).lineTo(-depth / 2, c.z1).close()
                    .extrude(c.width).val())
        ang = math.degrees(math.atan2(ed.e[1], ed.e[0]))
        return (body.rotate(cq.Vector(), cq.Vector(0, 0, 1), ang)
                .translate(cq.Vector(ed.p0[0], ed.p0[1], 0)))

    # ---- flat pattern -----------------------------------------------------
    def flat(self) -> tuple[Profile, list]:
        ba, sb = self.bend_allowance, self.setback
        floor = self.floor_profile()
        pieces, bends, cut_polys = [floor.poly], [], []

        def quad(ed: Edge, s0, s1, u0, u1) -> Polygon:
            # u' measured outward from the floor edge line (outer line - setback)
            return Polygon([ed.at(s0, u0 - sb), ed.at(s1, u0 - sb),
                            ed.at(s1, u1 - sb), ed.at(s0, u1 - sb)])

        flanges = []
        for ed in self.edges():
            s0, s1 = self._bend_span(ed)
            pieces.append(quad(ed, s0, s1, -0.01, ba + 0.01))
            fl = quad(ed, ed.a, ed.length - ed.b, ba, ba + self.flange_flat)
            flanges.append(fl)
            pieces.append(fl)
            bends.append((ed.at(s0, ba / 2 - sb), ed.at(s1, ba / 2 - sb)))
        for i, f in enumerate(flanges):
            for g in flanges[i + 1:]:
                if f.intersection(g).area > 1e-6:
                    raise ValueError("flat pattern flanges overlap; increase relief")
        for c in self.wall_cuts:
            _, ed = self._edge_for(c.x, c.y)
            s, _ = ed.local(c.x, c.y)
            u0 = ba + (c.z0 - sb)
            u1 = ba + (c.z1 - sb)
            if c.z0 < sb + 0.5:
                raise ValueError(f"wall cut at z={c.z0} intrudes into the bend zone")
            q = quad(ed, s - c.width / 2, s + c.width / 2, u0, u1)
            if c.rounded:
                h = u1 - u0
                um = (u0 + u1) / 2 - sb
                half = max(0.0, c.width / 2 - h / 2)
                q = LineString([ed.at(s - half, um), ed.at(s + half + 1e-6, um)]).buffer(h / 2, quad_segs=16)
            cut_polys.append(q)
        prof = Profile(unary_union(pieces), list(floor.holes))
        for q in cut_polys:
            prof.cut(q)
        return prof, bends


def _profile_solid(profile: Profile, t: float) -> cq.Solid:
    from geom import profile_solid
    return profile_solid(profile, t)


def tray_inner(outer: Polygon, t: float) -> Polygon:
    return offset(outer, -t)
