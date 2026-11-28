"""Line drawing of the finished instrument for the carrier's bottom silkscreen.

Projects the case, lid (open), dial, hands, thumbwheels and crown (not the crystal, which would
hide the dial) from the CAD in the
viewer's default isometric direction, removes hidden lines (OpenCascade HLR), drops edges too
short to print at silkscreen scale, and writes `emblem_iso.json`: polylines in mm, centred on the
origin, x right and y up, `size` mm across. `make_pcb.py` (KiCad's Python, no CadQuery) reads it.

    python hardware/pcb/emblem_art.py      # from the repo's .venv; re-run after a CAD change
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "cad"))

import cadquery as cq  # noqa: E402
from OCP.BRepAdaptor import BRepAdaptor_Curve  # noqa: E402
from OCP.GCPnts import GCPnts_QuasiUniformDeflection  # noqa: E402
from OCP.HLRAlgo import HLRAlgo_Projector  # noqa: E402
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape  # noqa: E402
from OCP.TopAbs import TopAbs_EDGE  # noqa: E402
from OCP.TopExp import TopExp_Explorer  # noqa: E402
from OCP.TopoDS import TopoDS  # noqa: E402
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt  # noqa: E402

import design as D  # noqa: E402

OUT = HERE / "emblem_iso.json"
VIEW = (0.55, -0.85, 0.6)          # viewer.js "iso" (CAD frame, z up)
SIZE = 27.0                         # mm across on the board
MIN_LEN = 3.0                       # drop visible edges shorter than this (instrument mm)
PARTS = ("case_lower_tray", "case_upper_shell", "case_lid", "dial_plate_P2", "dial_sticker", "hand_I",
         "hand_II", "hand_III", "hand_needle", "hand_cap_rosette", "crown_turned", "hinge_leaf_body",
         "hinge_leaf_lid", "knob_I_25T", "knob_II_25T", "knob_III_25T")


def shapes() -> list:
    out = []
    by_name = {p.name: p for p in D.all_parts()}
    open_loc = D.lid_open_location()
    for name in PARTS:
        p = by_name.get(name)
        if p is None:
            continue
        for s in p.placed():
            out.append(s.moved(open_loc) if p.group == "lid" else s)
    return out


def visible_polylines(solids) -> list[list[tuple[float, float]]]:
    algo = HLRBRep_Algo()
    for s in solids:
        algo.Add(s.wrapped)
    v = VIEW
    n = math.sqrt(sum(c * c for c in v))
    d = gp_Dir(*(c / n for c in v))
    up = gp_Dir(0, 0, 1)
    x = up.Crossed(d)                                    # screen x: right
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), d, x)))
    algo.Update()
    algo.Hide()
    hlr = HLRBRep_HLRToShape(algo)
    lines = []
    for comp in (hlr.VCompound(), hlr.OutLineVCompound()):
        if comp.IsNull():
            continue
        exp = TopExp_Explorer(comp, TopAbs_EDGE)
        while exp.More():
            edge = TopoDS.Edge_s(exp.Current())
            curve = BRepAdaptor_Curve(edge)
            disc = GCPnts_QuasiUniformDeflection(curve, 0.05)
            if disc.IsDone() and disc.NbPoints() >= 2:
                lines.append([(disc.Value(i).X(), disc.Value(i).Y()) for i in range(1, disc.NbPoints() + 1)])
            exp.Next()
    lines = chain(lines)
    return [ln for ln in lines if sum(math.dist(a, b) for a, b in zip(ln, ln[1:])) >= MIN_LEN]


def chain(lines, tol=0.02):
    """Join edges that meet end to end: the CAD's circles and outlines are many short facets."""
    key = lambda p: (round(p[0] / tol), round(p[1] / tol))     # noqa: E731
    open_ = [list(ln) for ln in lines]
    ends = {}
    for i, ln in enumerate(open_):
        for e in (0, -1):
            ends.setdefault(key(ln[e]), []).append(i)
    used, out = set(), []
    for i in range(len(open_)):
        if i in used:
            continue
        used.add(i)
        cur = open_[i]
        for _ in range(2):                                     # grow forward, then from the start
            while True:
                nxt = [j for j in ends.get(key(cur[-1]), []) if j not in used]
                if not nxt:
                    break
                j = nxt[0]
                used.add(j)
                seg = open_[j] if key(open_[j][0]) == key(cur[-1]) else open_[j][::-1]
                cur += seg[1:]
            cur.reverse()
        out.append(cur)
    return out


def main() -> None:
    lines = visible_polylines(shapes())
    xs = [p[0] for ln in lines for p in ln]
    ys = [p[1] for ln in lines for p in ln]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    k = SIZE / max(max(xs) - min(xs), max(ys) - min(ys))
    out = [[(round((x - cx) * k, 3), round((y - cy) * k, 3)) for x, y in ln] for ln in lines]
    OUT.write_text(json.dumps(dict(size=SIZE, view=VIEW, lines=out)), encoding="utf-8")
    print(f"{len(out)} polylines, {sum(len(ln) for ln in out)} points, "
          f"{(max(xs) - min(xs)) * k:.1f} × {(max(ys) - min(ys)) * k:.1f} mm -> {OUT.name}")


if __name__ == "__main__":
    main()
