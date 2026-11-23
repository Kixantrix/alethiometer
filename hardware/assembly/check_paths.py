"""Sweep every motion in steps.yaml for collisions and screwdriver access.

    python hardware/assembly/check_paths.py [--step ID ...] [--spacing 0.5] [--json report.json]

Each moving instance is sampled along its path (about every --spacing mm of travel) and
intersected with every instance visible in that step (same visibility as the viewer). Pairs that
move together rigidly keep their installed relative pose and are skipped, as are the
intentional contacts in design.ALLOWED. A motion with `driver: {d, len}` also checks a
screwdriver/nut-driver cylinder behind the part at the end of its travel.
The installed assembly itself is covered by cad/build.py's interference check.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import cadquery as cq
from OCP.gp import gp_Trsf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guide as G  # noqa: E402

sys.path.insert(0, str(G.HW / "cad"))
import build as B  # noqa: E402
import design as D  # noqa: E402

MIN_VOL = 0.01      # mm³, as cad/build.py


def location(m: np.ndarray) -> cq.Location:
    t = gp_Trsf()
    t.SetValues(*m[0, :4], *m[1, :4], *m[2, :4])
    return cq.Location(t)


def lid_matrix(deg: float) -> np.ndarray:
    ax, az = D.HINGE_AXIS
    return G.matrix(dict(t=[0, 0, 0], rot=dict(axis=[0, 1, 0], about=[ax, 0, az], deg=deg)))


class World:
    def __init__(self, parts):
        self.parts = {p.name: p for p in parts}
        self.base: dict[str, cq.Shape] = {}
        self.corners: dict[str, np.ndarray] = {}

    def shape(self, key: str) -> cq.Shape:
        if key not in self.base:
            name, i = key.split("#")
            s = self.parts[name].placed()[int(i)]
            self.base[key] = s
            bb = s.BoundingBox()
            self.corners[key] = np.array([[x, y, z, 1.0] for x in (bb.xmin, bb.xmax)
                                          for y in (bb.ymin, bb.ymax) for z in (bb.zmin, bb.zmax)])
        return self.base[key]

    def is_lid(self, key: str) -> bool:
        return self.parts[key.split("#")[0]].group == "lid"

    def full(self, key: str, p: dict, lid: float) -> np.ndarray:
        m = G.matrix(p)
        return m @ lid_matrix(lid) if self.is_lid(key) else m

    def box(self, key: str, m: np.ndarray) -> np.ndarray:
        self.shape(key)
        c = self.corners[key] @ m.T
        return np.array([c[:, :3].min(axis=0), c[:, :3].max(axis=0)])

    def placed(self, key: str, m: np.ndarray) -> cq.Shape:
        return self.shape(key).moved(location(m))


def overlap(a: np.ndarray, b: np.ndarray, pad: float = 0.0) -> bool:
    return bool(np.all(a[0] <= b[1] + pad) and np.all(b[0] <= a[1] + pad))


def inverse_ease(s: float) -> float:
    return (s / 4) ** (1 / 3) if s < 0.5 else 1 - (2 * (1 - s)) ** (1 / 3) / 2


def travel(world: World, key: str, seg: G.Segment, lid: float) -> float:
    """Largest distance any bounding-box corner moves (covers rotations as well as translations)."""
    world.shape(key)
    a, b = world.full(key, seg.a, lid), world.full(key, seg.b, lid)
    if seg.a["rot"] or seg.b["rot"]:
        steps = [world.full(key, G.lerp_pose(seg.a, seg.b, s / 12), lid) for s in range(13)]
        return float(sum(np.abs(world.corners[key] @ (m1 - m0).T)[:, :3].max()
                         for m0, m1 in zip(steps, steps[1:])))
    return float(np.abs(world.corners[key] @ (b - a).T)[:, :3].max())


def check_step(world: World, r: dict, spacing: float, log=print) -> list[dict]:
    vis = G.visible_keys(r)
    issues = []
    reported = set()
    for key, segs in r["tracks"].items():
        if key not in vis:
            continue
        for si, seg in enumerate(segs):
            if seg.nocheck or seg.fade:
                continue
            dist = travel(world, key, seg, G.lid_at(r, seg.t1))
            if dist < 1e-6:
                continue
            n = max(2, math.ceil(dist / spacing))
            for k in range(n + 1):
                t = seg.t0 + (seg.t1 - seg.t0) * inverse_ease(k / n)    # evenly spaced along the path
                lid = G.lid_at(r, t)
                mk = world.full(key, G.pose_at(r, key, t), lid)
                bk = world.box(key, mk)
                for other in vis:
                    if other == key or other.split("#")[0] == key.split("#")[0]:
                        continue
                    if not G.present(r, other, t):
                        continue
                    pair = tuple(sorted((key, other)))
                    if pair in reported or B.allowed(key.split("#")[0], other.split("#")[0]):
                        continue
                    if other in r["tracks"] and any(s.fade or s.nocheck for s in r["tracks"][other]):
                        continue
                    mo = world.full(other, G.pose_at(r, other, t), lid)
                    if np.allclose(G.matrix(G.pose_at(r, key, t)), G.matrix(G.pose_at(r, other, t))) \
                            and world.is_lid(key) == world.is_lid(other):
                        continue                    # moving together: installed relative pose
                    if not overlap(bk, world.box(other, mo)):
                        continue
                    try:
                        v = world.placed(key, mk).intersect(world.placed(other, mo)).Volume()
                    except Exception as e:  # pragma: no cover - OCC edge cases
                        v, err = float("nan"), str(e)
                    if not v <= MIN_VOL:
                        reported.add(pair)
                        frac = (t - seg.t0) / (seg.t1 - seg.t0) if seg.t1 > seg.t0 else 1.0
                        issues.append(dict(step=r["step"]["id"], kind="collision", moving=key, other=other,
                                           t=round(t, 3), progress=round(frac, 3), volume=round(v, 3)))
                        log(f"  X {r['step']['id']}: {key} hits {other} at {frac:.0%} of its move ({v:.2f} mm³)")
            if seg.driver:
                issues += check_driver(world, r, key, seg, vis, log)
    return issues


def check_driver(world: World, r: dict, key: str, seg: G.Segment, vis: set[str], log) -> list[dict]:
    lid = G.lid_at(r, seg.t1)
    ma, mb = world.full(key, seg.a, lid), world.full(key, seg.b, lid)
    box_b = world.box(key, mb)
    d = (mb[:3, 3] - ma[:3, 3]) + (box_b.mean(axis=0) - world.box(key, ma).mean(axis=0))
    if np.linalg.norm(d) < 1e-6:
        return []
    d /= np.linalg.norm(d)
    c = world.corners[key] @ mb.T
    center = c[:, :3].mean(axis=0)
    back = (c[:, :3] - center) @ d
    head = center + d * back.min()
    radius, length = float(seg.driver.get("d", 3.0)) / 2, float(seg.driver.get("len", 40.0))
    bore = float(seg.driver.get("bore", 0.0))         # nut drivers are hollow: the screw end fits inside
    gap = float(seg.driver.get("gap", 0.05))
    origin = head - d * gap
    tool = cq.Solid.makeCylinder(radius, length, cq.Vector(*origin), cq.Vector(*(-d)))
    if bore:
        tool = tool.cut(cq.Solid.makeCylinder(bore / 2, length, cq.Vector(*origin), cq.Vector(*(-d))))
    tb = tool.BoundingBox()
    tbox = np.array([[tb.xmin, tb.ymin, tb.zmin], [tb.xmax, tb.ymax, tb.zmax]])
    out = []
    for other in vis:
        if other == key or not G.present(r, other, seg.t1):
            continue
        mo = world.full(other, G.pose_at(r, other, seg.t1), lid)
        if not overlap(tbox, world.box(other, mo)):
            continue
        v = tool.intersect(world.placed(other, mo)).Volume()
        if v > MIN_VOL:
            out.append(dict(step=r["step"]["id"], kind="driver", moving=key, other=other,
                            volume=round(v, 3), driver=seg.driver))
            log(f"  X {r['step']['id']}: Ø{2 * radius:g} driver for {key} is blocked by {other} ({v:.2f} mm³)")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", nargs="*", help="only these step ids")
    ap.add_argument("--spacing", type=float, default=0.5, help="sample spacing along each path, mm")
    ap.add_argument("--json", type=Path, help="write the issues here")
    args = ap.parse_args()
    t0 = time.time()
    parts = G.design_parts()
    guide = G.load()
    cat = G.Catalogue(parts)
    errors = G.validate(guide, cat)
    if errors:
        print("assembly guide errors:\n  " + "\n  ".join(errors))
        return 2
    world = World(parts)
    issues = []
    runs = G.replay(guide, cat)
    for r in runs:
        if args.step and r["step"]["id"] not in args.step:
            continue
        t1 = time.time()
        found = check_step(world, r, args.spacing)
        issues += found
        print(f"{r['step']['id']:<32} {'ok' if not found else f'{len(found)} issue(s)'}"
              f"  ({time.time() - t1:.1f}s)", flush=True)
    print(f"{len(issues)} issue(s) in {time.time() - t0:.0f}s")
    if args.json:
        args.json.write_text(json.dumps(issues, indent=1), encoding="utf-8")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
