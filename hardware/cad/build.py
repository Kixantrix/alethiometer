"""Build every output for the brass alethiometer.

    python build.py            # check + DXF + STEP + renders + reports
    python build.py --check    # interference/fit checks only (fast-ish)

Outputs go to hardware/out/ (committed so the parts can be ordered without Python).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path

import cadquery as cq

import design as D
from geom import write_dxf

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"
DIAL_PNG = HERE.parent / "dial" / "dial_1200dpi.png"

# SendCutSend minimum part size (instant quote) and a conservative min web for laser
SCS_MIN = (0.25 * 25.4, 0.375 * 25.4)
MIN_WEB = {"spring steel .015\"": 0.4, "brass .040\"": 0.55, "brass .063\"": 0.8, "aluminium 5052 .063\"": 0.8, "copper .032\"": 0.5, "clear acrylic .063\"": 1.0}


def log(msg: str) -> None:
    print(msg, flush=True)


# ---------------------------------------------------------------------------
def placed_solids(parts, lid_open=False):
    out = []
    open_loc = D.lid_open_location()
    for p in parts:
        for i, s in enumerate(p.placed()):
            if lid_open and p.group == "lid":
                s = s.moved(open_loc)
            out.append((p, i, s))
    return out


def allowed(a: str, b: str) -> bool:
    for x, y in D.ALLOWED:
        if (a.startswith(x) and b.startswith(y)) or (a.startswith(y) and b.startswith(x)):
            return True
    return False


def interference(parts, lid_angles=(0.0,)) -> list[str]:
    items = []
    for p, i, s in placed_solids(parts):
        if p.name == "dial_sticker":
            continue
        items.append((p, i, s))
    problems = []
    for angle_index, angle in enumerate(lid_angles):
        opening = D.lid_open_location(angle)
        positioned = []
        for p, i, s in items:
            shape = s.moved(opening) if p.group == "lid" else s
            positioned.append((p, i, shape, shape.BoundingBox()))
        for a in range(len(positioned)):
            pa, ia, sa, ba = positioned[a]
            for b in range(a + 1, len(positioned)):
                pb, ib, sb, bbb = positioned[b]
                # Relative positions within the lid or within the body never change.
                if angle_index and (pa.group == "lid") == (pb.group == "lid"):
                    continue
                na, nb = pa.name, pb.name
                if na == nb or allowed(na, nb):
                    continue
                if (ba.xmax < bbb.xmin or bbb.xmax < ba.xmin or ba.ymax < bbb.ymin or bbb.ymax < ba.ymin
                        or ba.zmax < bbb.zmin or bbb.zmax < ba.zmin):
                    continue
                context = f"lid {angle:g}°: {na}[{ia}] × {nb}[{ib}]"
                try:
                    v = sa.intersect(sb).Volume()
                except Exception as exc:  # pragma: no cover - OCC edge cases
                    problems.append(f"{context}: boolean failed ({exc})")
                    continue
                if v > 0.01:
                    problems.append(f"{context}: {v:.3f} mm³")
    return problems


def bend_zone(p) -> list[tuple[str, float, float, bool]]:
    """Cut-outs within SendCutSend's bend-distortion zone: (what, distance, keep-out, on_face).
    Features in the visible face (floor/top) must stay clear; openings in a flange are placed by
    the part they mate with, so they are reported for the order notes instead."""
    keep = D.BEND_KEEPOUT.get(p.material)
    if p.tray is None or not p.bends or keep is None:
        return []
    from shapely.geometry import LineString, Point, Polygon
    lines = [LineString(b) for b in p.bends]
    face = Polygon(p.tray.floor_profile().poly.exterior)
    feats = [(Polygon(r), "cut-out") for r in p.profile.poly.interiors]
    feats += [(Point(x, y).buffer(r), f"Ø{2 * r:.1f} hole") for x, y, r in p.profile.holes]
    out = []
    for f, kind in feats:
        d = min(f.distance(ln) for ln in lines)
        if d < keep:
            c = f.centroid
            out.append((f"{kind} at ({c.x:.1f}, {c.y:.1f})", d, keep, face.contains(f)))
    return out


def bend_zone_warnings(parts) -> list[str]:
    return [f"{p.name}: {desc} {d:.1f} mm from a bend line (may distort; clean it up after forming)"
            for p in parts if p.profile is not None for desc, d, _, face in bend_zone(p) if not face]


def manufacturability(parts) -> list[str]:
    notes = []
    for p in parts:
        if p.kind not in ("scs", "scs-bent") or p.profile is None:
            continue
        w, h = p.profile.bbox
        if min(w, h) < SCS_MIN[0] or max(w, h) < SCS_MIN[1]:
            notes.append(f"{p.name}: {w:.1f}×{h:.1f} mm is below SendCutSend's minimum part size")
        web = MIN_WEB.get(p.material)
        if web and not p.name.startswith("hand_"):     # pointed hand tips are intentional
            thin = p.profile.thin_web_area(web)
            if thin > 2.0:
                notes.append(f"{p.name}: {thin:.1f} mm² of webs narrower than {web} mm")
        if p.tray is not None and p.tray.flange_flat + p.tray.setback < D.MIN_FLANGE:
            notes.append(f"{p.name}: flange {p.tray.height:.2f} mm < SCS minimum {D.MIN_FLANGE:.2f} mm")
        for desc, d, keep, face in bend_zone(p):
            if face:
                notes.append(f"{p.name}: {desc} {d:.1f} mm from a bend line (keep {keep:g} mm or it distorts)")
        from shapely.geometry import Point
        for x, y, r in p.profile.holes:
            if not p.profile.poly.buffer(-0.3).contains(Point(x, y).buffer(r)):
                notes.append(f"{p.name}: hole Ø{2 * r:.2f} at ({x:.1f}, {y:.1f}) is not inside material")
    return notes


def weight_report(parts) -> tuple[list[dict], float]:
    rows, total = [], 0.0
    for p in parts:
        vol = p.solid.Volume() * p.qty
        g = vol * D.DENSITY.get(p.density, 0.0)
        if p.group == "electronics" and p.kind == "bought":
            g = {"mcu_ProS3": 6, "battery": 7, "driver_DRV8833": 2, "amp_MAX98357A": 2,
                 "motor_X27_168": 9, "speaker": 6, "mic_INMP441": 1, "reed_switch": 0.3,
                 "usb_c_breakout": 1.5, "crown_switch": 1}.get(p.name, 1.5 if "AS5600" in p.name else 1)
        rows.append(dict(part=p.name, qty=p.qty, grams=round(g, 1), material=p.material))
        total += g
    return rows, total + 6.0  # wiring, solder, adhesive


# ---------------------------------------------------------------------------
def export_fabrication(parts) -> list[dict]:
    """out/sendcutsend/ holds exactly one file per part to order (flat parts as DXF, bent parts as
    their formed STEP), so the whole folder can be uploaded. The bent parts' flat patterns (DXF with a
    BEND layer) go to out/flat_patterns/ for reference only."""
    scs_dir = OUT / "sendcutsend"
    hold_dir = OUT / "sendcutsend_on_hold"
    flat_dir = OUT / "flat_patterns"
    step_dir = OUT / "step"
    for d in (scs_dir, hold_dir, flat_dir, step_dir):
        d.mkdir(parents=True, exist_ok=True)
        for f in d.glob("*"):
            f.unlink()
    rows = []
    for p in parts:
        if p.kind in ("scs", "scs-bent") and p.profile is not None:
            mat = p.material.replace('"', "in").replace(" ", "-").replace(".", "")
            qty = p.qty + p.qty_extra
            stem = f"{p.name}__{mat}__qty{qty}"
            held = D.HINGE_HOLD and p.name in D.HINGE_DEPENDENT
            dest = hold_dir if held else scs_dir
            if p.kind == "scs-bent":
                # Order the bent blank; the case countersinks are a post-process.
                fname = f"{stem}.step"
                blank = p.tray.formed() if p.tray is not None else p.solid
                cq.exporters.export(cq.Workplane().add(blank), str(dest / fname))
                write_dxf(flat_dir / f"{stem}__flat_reference.dxf", p.profile, p.bends)
            else:
                fname = f"{stem}.dxf"
                write_dxf(dest / fname, p.profile, p.bends)
            w, h = p.profile.bbox
            rows.append(dict(file=fname, on_hold="yes" if held else "", part=p.name, material=p.material, qty=qty,
                             size_mm=f"{w:.1f} x {h:.1f}", bends=len(p.bends),
                             notes=p.spec + "".join(
                                 f"; {desc} sits {d:.1f} mm from a bend (inside SendCutSend's {k:g} mm "
                                 "distortion zone; it is placed by the part it mates with, so clean it up "
                                 "after forming if it comes out oval)" for desc, d, k, face in bend_zone(p))))
        cq.exporters.export(cq.Workplane().add(p.solid), str(step_dir / f"{p.name}.step"))
    with open(OUT / "sendcutsend_order.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return rows


def export_assembly(parts) -> None:
    from cadquery.occ_impl.exporters.assembly import exportGLTF, exportAssembly
    for lid_open, name in ((False, "alethiometer_closed"), (True, "alethiometer_open")):
        asm = cq.Assembly(name="alethiometer")
        for p, i, s in placed_solids(parts, lid_open):
            asm.add(s, name=f"{p.name}_{i}", color=cq.Color(*p.color))
        exportAssembly(asm, str(OUT / f"{name}.step"))
        if lid_open:   # one lightweight viewable model is committed; STEPs are regenerated locally
            exportGLTF(asm, str(OUT / f"{name}.glb"), binary=True, tolerance=0.12, angularTolerance=0.35)


def export_stock_list(parts) -> None:
    rows = []
    for p in parts:
        if p.kind in ("stock", "bought"):
            rows.append(dict(part=p.name, kind=p.kind, qty=p.qty, spec=p.spec))
    with open(OUT / "stock_and_bought_parts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["part", "kind", "qty", "spec"])
        w.writeheader()
        w.writerows(rows)


TURNED_README = """# Turned-parts kit

Generated by `hardware/cad/build.py`: do not edit by hand.

Every arbor, shaft, bushing, sleeve, magnet cup and the crown of the movement, made to exact length
so nothing is cut or measured during assembly. Upload the `.step` files and this table, which is
the drawing.

**Where to order.** The plain tubes (the **tube** rows below) have 0.36 mm walls. That is under the
published minimum wall of most instant-quote services (Protolabs 0.51 mm, Hubs 0.5 mm, JLCCNC
0.8 mm, and JLCCNC turns H59, not C360), so order the kit from **PCBWay CNC** (C360, quotes to a
marked drawing at ±0.01 mm) or a Swiss-lathe / watch-parts shop. Either can make the **tube** rows
from precision brass tube cut to length and faced rather than turning them; say so on the quote.
If a shop will only turn the **lathe** rows, buy the tube rows separately as precision tube cut to
length (K&S telescoping sizes are the fallback: their ±0.05 mm tolerance can make a pair tight, so
check each tube slides on the next before cutting).

- **Material:** brass C360 (free-machining), natural finish.
- **Tolerances:** {tol}.
- **Thin walls:** the tube rows are K&S telescoping sizes, so they slide inside each other; precision
  tube cut to length and faced is equally good if the ODs, bores and lengths meet the table.
- **Crown:** knurl the Ø{cap:g} mm cap (straight or diamond, about 0.5 mm pitch).
- Order **one or two spares** of the small plain parts (bushings, sleeves): they are cheap and easy
  to lose.

Segments are listed from the bottom of the part up (as fitted), as OD × length; a bore runs through
that segment only. "—" = solid. **★** = running fit, held to {tol_run}; quote the kit both ways
(★ only, and everything at the tight tolerance) if the shop prices them differently.

| Part | Make as | Qty | Length | Segments (bottom up) | How it is fitted |
|---|---|---|---|---|---|
{rows}
"""


def export_turned(parts) -> list:
    """STEP per turned part (axis Z, bottom at z=0) plus the drawing table."""
    out = OUT / "turned"
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*"):
        f.unlink()
    turned = [p for p in parts if p.kind == "turned"]
    rows, csv_rows = [], []
    for p in turned:
        segs = p.drawing["segments"]
        cq.exporters.export(cq.Workplane().add(D.turned_solid(segs)),
                            str(out / f"{p.name}__qty{p.qty + p.qty_extra}.step"))
        marks = D.running_marks(p.name, segs)
        cells = "; ".join(f"Ø{od:.3f}{'★' * mo}" + (f" (bore Ø{bore:.3f}{'★' * mb})" if bore else " —")
                          + f" × {h:.3f}" for (od, bore, h), (mo, mb) in zip(segs, marks))
        make = "tube" if len(segs) == 1 and segs[0][1] else "lathe"
        rows.append(f"| `{p.name}` | {make} | {p.qty} | {p.drawing['length']:.3f} | {cells} | {p.drawing['use']} |")
        csv_rows.append(dict(part=p.name, make_as=make, qty=p.qty, length_mm=round(p.drawing["length"], 3),
                             segments=cells, use=p.drawing["use"]))
    (out / "README.md").write_text(TURNED_README.format(tol=D.TURNED_TOL, tol_run=D.TURNED_TOL_RUNNING, cap=D.CROWN_CAP_D,
                                                        rows="\n".join(rows)), encoding="utf-8")
    with open(out / "turned_parts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        w.writeheader()
        w.writerows(csv_rows)
    return turned


# ---------------------------------------------------------------------------
# Rendering (VTK, offscreen)
# ---------------------------------------------------------------------------
def render(parts, path: Path, *, view="iso", lid_open=False, hide=(), explode=False,
           clip_x=None, size=(1600, 1200), dial_texture=True) -> None:
    import vtk
    from vtk.util.numpy_support import numpy_to_vtk  # noqa: F401

    ren = vtk.vtkRenderer()
    ren.SetBackground(0.10, 0.09, 0.08)
    ren.SetBackground2(0.30, 0.26, 0.21)
    ren.GradientBackgroundOn()
    ren.SetUseDepthPeeling(1)
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetAlphaBitPlanes(1)
    win.SetMultiSamples(0)
    win.AddRenderer(ren)
    win.SetSize(*size)

    explode_dz = {"case": 0, "lid": 70, "hands": 52, "dial": 40, "movement": 22,
                  "electronics": 0, "hardware": 0}
    plane = None
    if clip_x is not None:
        plane = vtk.vtkPlane()
        plane.SetOrigin(0, clip_x, 0)
        plane.SetNormal(0, 1, 0)

    for p, i, s in placed_solids(parts, lid_open):
        if p.name in hide or p.group in hide:
            continue
        if p.name == "dial_sticker" and dial_texture and DIAL_PNG.exists():
            continue
        if explode:
            dz = explode_dz.get(p.group, 0)
            if p.name.startswith(("case_upper", "crystal", "screw_top", "standoff_hand", "hinge")):
                dz = 95 if not p.name.startswith("standoff_hand") else 40
            if p.name.startswith(("case_lid", "lid_", "magnet_lid", "hinge_leaf_lid", "hinge_knuckle_lid")):
                dz = 125
            if p.name.startswith(("dial_plate", "cannon", "standoff_gear")):
                dz = 40
            s = s.translate(cq.Vector(0, 0, dz))
        verts, tris = s.tessellate(0.03, 0.15)
        pts = vtk.vtkPoints()
        for v in verts:
            pts.InsertNextPoint(v.x, v.y, v.z)
        cells = vtk.vtkCellArray()
        for t in tris:
            cells.InsertNextCell(3)
            for k in t:
                cells.InsertCellPoint(k)
        poly = vtk.vtkPolyData()
        poly.SetPoints(pts)
        poly.SetPolys(cells)
        normals = vtk.vtkPolyDataNormals()
        normals.SetInputData(poly)
        normals.SetFeatureAngle(35)
        normals.SplittingOn()
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(normals.GetOutputPort())
        if plane is not None:
            mapper.AddClippingPlane(plane)
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetColor(*p.color)
        prop.SetInterpolationToPhong()
        metallic = p.color in (D.BRASS, D.BRASS_DARK, D.COPPER, D.STEEL)
        prop.SetSpecular(0.55 if metallic else 0.15)
        prop.SetSpecularPower(28 if metallic else 8)
        prop.SetDiffuse(0.75)
        prop.SetAmbient(0.18)
        if p.name == "crystal":
            prop.SetOpacity(0.12)
        ren.AddActor(actor)

    if dial_texture and DIAL_PNG.exists() and "dial" not in hide:
        reader = vtk.vtkPNGReader()
        reader.SetFileName(str(DIAL_PNG))
        tex = vtk.vtkTexture()
        tex.SetInputConnection(reader.GetOutputPort())
        tex.InterpolateOn()
        half = 42.2
        z = D.Z_P2_TOP + D.STICKER_T + (40 if explode else 0)
        ps = vtk.vtkPlaneSource()
        ps.SetOrigin(-half, -half, z)
        ps.SetPoint1(half, -half, z)
        ps.SetPoint2(-half, half, z)
        tm = vtk.vtkPolyDataMapper()
        tm.SetInputConnection(ps.GetOutputPort())
        if plane is not None:
            tm.AddClippingPlane(plane)
        ta = vtk.vtkActor()
        ta.SetMapper(tm)
        ta.SetTexture(tex)
        ta.GetProperty().SetAmbient(0.35)
        ta.GetProperty().SetDiffuse(0.7)
        ta.ForceTranslucentOn()
        ren.AddActor(ta)

    kit = vtk.vtkLightKit()
    kit.SetKeyLightIntensity(0.95)
    kit.AddLightsToRenderer(ren)

    cam = ren.GetActiveCamera()
    cz = D.Z_TOP / 2
    views = {
        "iso": ((150, -230, 210), (0, 0, cz)),
        "open": ((60, -260, 300), (60, 0, cz)),
        "dial": ((0, 0, 400), (0, 0, cz)),
        "front": ((0, -400, 60), (0, 0, cz)),
        "exploded": ((230, -330, 260), (0, 0, 60)),
        "section": ((25, -320, 45), (0, 0, cz)),
        "back": ((-120, 160, -260), (0, 0, cz)),
    }
    pos, focal = views[view]
    cam.SetPosition(*pos)
    cam.SetFocalPoint(*focal)
    cam.SetViewUp(0, 0, 1) if view not in ("dial",) else cam.SetViewUp(0, 1, 0)
    ren.ResetCamera()
    cam.Zoom({"dial": 1.25, "open": 1.35, "exploded": 1.1, "section": 1.6}.get(view, 1.25))
    win.Render()
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(win)
    w2i.Update()
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(path))
    writer.SetInputConnection(w2i.GetOutputPort())
    writer.Write()
    log(f"  rendered {path.name}")


def renders(parts) -> None:
    rd = OUT / "renders"
    rd.mkdir(parents=True, exist_ok=True)
    render(parts, rd / "closed.png", view="iso")
    render(parts, rd / "open.png", view="open", lid_open=True)
    render(parts, rd / "dial_top.png", view="dial", lid_open=True, hide=("lid",))
    render(parts, rd / "exploded.png", view="exploded", explode=True)
    render(parts, rd / "section.png", view="section", lid_open=True, hide=("lid",), clip_x=0.0)
    render(parts, rd / "movement.png", view="iso", hide=("case", "lid", "crystal"))
    render(parts, rd / "back.png", view="back")


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="checks only")
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    parts = D.all_parts()
    log(f"built {len(parts)} part types in {time.time() - t0:.1f}s")
    log(json.dumps(D.summary(), indent=1))

    tools = D.tooling()
    spares = D.alternate_gears()
    notes = manufacturability(parts + tools + spares)
    log("manufacturability: " + ("OK" if not notes else ""))
    for n in notes:
        log("  ! " + n)
    bend_warn = bend_zone_warnings(parts)
    for n in bend_warn:
        log("  ~ " + n)

    t1 = time.time()
    angles = [*range(0, math.ceil(D.LID_OPEN_ANGLE), 5), D.LID_OPEN_ANGLE]
    problems = interference(parts, lid_angles=angles)
    log(f"interference check ({time.time() - t1:.0f}s): " + ("none" if not problems else ""))
    for pr in problems:
        log("  X " + pr)

    import mesh
    t1 = time.time()
    gear_mesh = mesh.report()
    log(f"gear mesh ({time.time() - t1:.0f}s), mm at the driven pitch circle:")
    for r in gear_mesh:
        log(f"  {r['pair']:<22} backlash {r['backlash_mm']:.2f}, worst-case cut {r['backlash_fat_mm']:.2f}"
            + (f", tight alternate {r['backlash_tight_mm']:.2f}" if r["backlash_tight_mm"] is not None else "")
            + f", centre margin {r['margin_mm']:+.2f}")
    mesh_problems = mesh.problems(gear_mesh)
    for pr in mesh_problems:
        log("  X " + pr)

    rows, grams = weight_report(parts)
    log(f"estimated weight: {grams:.0f} g")
    if args.check:
        return 1 if problems or mesh_problems else 0

    OUT.mkdir(exist_ok=True)
    order = export_fabrication(parts + tools + spares)
    export_stock_list(parts)
    turned = export_turned(parts)
    export_assembly(parts)
    with open(OUT / "weights.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["part", "qty", "grams", "material"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: -r["grams"]))
    report = dict(summary=D.summary(), weight_g=round(grams), interference=problems,
                  lid_check_angles=angles,
                  manufacturability=notes, bend_zone=bend_warn, sendcutsend_files=len(order), gear_mesh=gear_mesh,
                  turned_parts=sum(p.qty for p in turned))
    (OUT / "build_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    log(f"exported {len(order)} SendCutSend files")
    if not args.no_render:
        renders(parts)
    log(f"done in {time.time() - t0:.0f}s")
    return 1 if problems or mesh_problems else 0


if __name__ == "__main__":
    sys.exit(main())
