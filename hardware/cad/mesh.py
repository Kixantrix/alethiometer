"""Gear mesh analysis: does every pair turn freely, how much backlash, and how much margin.

Each meshing pair is taken from the CAD (the same profiles that are laser-cut, and the bought
thumbwheel's nominal profile), placed at its real centres and phase, and turned in plan view:

- free running: the driven gear follows at the exact ratio through a full turn of the driver
  without the teeth ever overlapping;
- backlash: with the driver held, how far the driven gear can rock, in mm at its pitch circle;
- margin: how much the centre distance can shrink before the pair binds, with the laser-cut
  teeth cut fat by the supplier's worst case. This is what the bushings, plate holes and
  laser tolerance have to stay inside.

    python mesh.py            # print the table
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from shapely import affinity
from shapely.geometry import Polygon

import design as D
import layout as L
from gears import pitch_radius

LASER_FAT = 0.065      # per side: SendCutSend holds about ±0.13 mm on a cut feature
OVERLAP = 1e-5         # mm² counted as contact
BACKLASH_RANGE = (0.05, 0.45)   # mm at the pitch circle: enough to run free, little enough to read well
MIN_MARGIN = 0.12      # mm of centre-distance shrink the worst-case-fat teeth must survive


@dataclass
class Pair:
    name: str
    a: str                  # driver part name
    b: str                  # driven part name
    za: int
    zb: int
    ca: tuple[float, float]
    cb: tuple[float, float]
    rot_a: float            # installed rotation, deg
    rot_b: float
    poly_a: Polygon         # outline at the origin, unrotated
    poly_b: Polygon
    laser_a: bool
    laser_b: bool

    @property
    def nominal_distance(self) -> float:
        return math.dist(self.ca, self.cb)

    @property
    def theoretical_distance(self) -> float:
        return pitch_radius(L.MODULE, self.za) + pitch_radius(L.MODULE, self.zb)

    def placed(self, theta: float = 0.0, delta_b: float = 0.0, shrink: float = 0.0, fat: float = 0.0):
        """Driver turned theta (deg), driven following at the ratio plus delta_b (deg); the driven
        gear moved shrink mm toward the driver; laser-cut outlines grown by fat mm per side."""
        pa = self.poly_a.buffer(fat, join_style="mitre") if fat and self.laser_a else self.poly_a
        pb = self.poly_b.buffer(fat, join_style="mitre") if fat and self.laser_b else self.poly_b
        ga = affinity.translate(affinity.rotate(pa, self.rot_a + theta, origin=(0, 0)), *self.ca)
        d = self.nominal_distance
        ux, uy = ((self.ca[0] - self.cb[0]) / d, (self.ca[1] - self.cb[1]) / d)
        cb = (self.cb[0] + ux * shrink, self.cb[1] + uy * shrink)
        tb = self.rot_b - theta * self.za / self.zb + delta_b
        gb = affinity.translate(affinity.rotate(pb, tb, origin=(0, 0)), *cb)
        return ga, gb


def _outline(part) -> Polygon:
    poly = part.profile.poly if part.profile is not None else None
    return Polygon(poly.exterior)


def pairs(backlash=None, driven=None) -> list[Pair]:
    """Every meshing pair; backlash=/driven= build the laser-cut drivers/driven gears with that tooth
    thinning instead (driven=D.GEAR_BACKLASH gives the tight alternates)."""
    parts = {p.name: p for p in D.gears(backlash, driven)}
    rz = lambda p: p.placements[0].toTuple()[1][2]            # noqa: E731  (installed rotation, deg)
    knob_poly = Polygon(D.gear_polygon(L.MODULE, D.Z_KNOB).exterior)
    out = []
    for tr in D.TRAINS:
        n = tr["name"]
        hand, sensor, knob = parts[f"gear_hand_{n}_{D.Z_HAND}T"], parts[f"gear_sensor_{n}_{D.Z_SENSOR}T"], \
            parts[f"knob_{n}_{D.Z_KNOB}T"]
        out.append(Pair(f"knob {n} → sensor {n}", knob.name, sensor.name, D.Z_KNOB, D.Z_SENSOR,
                        D.knob_xy(tr), D.sensor_xy(tr), rz(knob), rz(sensor),
                        knob_poly, _outline(sensor), False, True))
        out.append(Pair(f"sensor {n} → hand {n}", sensor.name, hand.name, D.Z_SENSOR, D.Z_HAND,
                        D.sensor_xy(tr), (0.0, 0.0), rz(sensor), rz(hand),
                        _outline(sensor), _outline(hand), True, True))
    motor, needle = parts[f"gear_motor_{D.Z_MOTOR}T"], parts[f"gear_needle_{D.Z_NEEDLE}T"]
    out.append(Pair("motor → needle", motor.name, needle.name, D.Z_MOTOR, D.Z_NEEDLE, D.X27_SHAFT, (0.0, 0.0),
                    rz(motor), rz(needle), _outline(motor), _outline(needle),
                    True, True))
    return out


def contact(pair: Pair, theta=0.0, delta_b=0.0, shrink=0.0, fat=0.0) -> float:
    ga, gb = pair.placed(theta, delta_b, shrink, fat)
    return ga.intersection(gb).area


def _free_rotation(pair: Pair, shrink=0.0, fat=0.0, steps_per_pitch=24) -> bool:
    """The driven gear can sit somewhere inside its backlash at every sampled driver angle."""
    pitch_a = 360.0 / pair.za
    for k in range(steps_per_pitch * 2):
        theta = k * pitch_a / steps_per_pitch
        if _play(pair, theta, shrink, fat) is None:
            return False
    return True


def _play(pair: Pair, theta: float, shrink=0.0, fat=0.0):
    """Angular play (deg) of the driven gear with the driver held at theta: (minus, plus), or None if
    no free position exists. The search starts from the best-centred driven angle."""
    pitch_b = 360.0 / pair.zb
    trial = [i * pitch_b / 40 for i in range(-20, 21)]
    free = [d for d in trial if contact(pair, theta, d, shrink, fat) <= OVERLAP]
    if not free:
        return None
    mid = free[len(free) // 2]

    def edge(sign):
        lo, hi = 0.0, pitch_b / 2
        if contact(pair, theta, mid + sign * hi, shrink, fat) <= OVERLAP:
            return hi
        for _ in range(22):
            m = (lo + hi) / 2
            if contact(pair, theta, mid + sign * m, shrink, fat) <= OVERLAP:
                lo = m
            else:
                hi = m
        return lo

    return edge(-1), edge(+1)


def backlash(pair: Pair, shrink=0.0, fat=0.0, samples=6) -> float | None:
    """Smallest total backlash (mm at the driven pitch circle) over a pitch of the driver."""
    rb = pitch_radius(L.MODULE, pair.zb)
    pitch_a = 360.0 / pair.za
    worst = None
    for k in range(samples):
        play = _play(pair, k * pitch_a / samples, shrink, fat)
        if play is None:
            return None
        bl = math.radians(play[0] + play[1]) * rb
        worst = bl if worst is None else min(worst, bl)
    return worst


def margin(pair: Pair, fat=LASER_FAT) -> float:
    """How far (mm) the centres can close up, with fat laser-cut teeth, before the pair binds."""
    lo, hi = -0.3, 0.6
    if backlash(pair, lo, fat, samples=3) is None:
        return lo
    for _ in range(14):
        m = (lo + hi) / 2
        if backlash(pair, m, fat, samples=3) is None:
            hi = m
        else:
            lo = m
    return lo


def report() -> list[dict]:
    rows = []
    for p, pt in zip(pairs(), pairs(driven=D.GEAR_BACKLASH)):
        alt = pt.b in set(D.DRIVEN_GEARS)
        rows.append(dict(
            pair=p.name, ratio=f"{p.za}:{p.zb}",
            centre_mm=round(p.nominal_distance, 3), theoretical_mm=round(p.theoretical_distance, 3),
            backlash_mm=round(backlash(p), 3),
            backlash_fat_mm=round(backlash(p, fat=LASER_FAT) or 0.0, 3),
            backlash_tight_mm=round(backlash(pt), 3) if alt else None,
            margin_mm=round(margin(p), 3),
        ))
    return rows


def problems(rows: list[dict]) -> list[str]:
    """Design rules: the gears as ordered run with readable backlash and survive a worst-case cut;
    the tight alternates are readable too."""
    out = []
    lo, hi = BACKLASH_RANGE
    for r in rows:
        if not lo <= r["backlash_mm"] <= hi:
            out.append(f"{r['pair']}: backlash {r['backlash_mm']:.2f} mm outside {lo}-{hi} mm")
        if r["backlash_fat_mm"] < lo:
            out.append(f"{r['pair']}: binds at a worst-case cut")
        if r["backlash_tight_mm"] is not None and not lo <= r["backlash_tight_mm"] <= hi:
            out.append(f"{r['pair']}: tight alternate backlash {r['backlash_tight_mm']:.2f} mm outside {lo}-{hi} mm")
    return out


if __name__ == "__main__":
    print(f"{'pair':<22} {'ratio':>6} {'centre':>8} {'backlash':>9} {'fat':>6} {'tight':>6} {'margin':>7}  (mm)")
    for r in report():
        tight = f"{r['backlash_tight_mm']:>6.3f}" if r["backlash_tight_mm"] is not None else f"{'-':>6}"
        print(f"{r['pair']:<22} {r['ratio']:>6} {r['centre_mm']:>8.3f} {r['backlash_mm']:>9.3f} "
              f"{r['backlash_fat_mm']:>6.3f} {tight} {r['margin_mm']:>7.3f}")
