"""Export the brass alethiometer for the web viewer in this folder.

    python hardware/viewer/export_viewer.py [--tolerance 0.1]

Writes hardware/viewer/assets/:
    alethiometer.glb   one mesh per part type (node name = part name), in its local frame
    parts.json         manifest: metadata, placements, open-lid transform, explode offsets
    dial.png           dial sticker texture (downscaled)

Coordinates are millimetres, Z up, exactly as in hardware/cad/design.py.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CAD = HERE.parent / "cad"
sys.path.insert(0, str(CAD))

import design as D  # noqa: E402

ASSETS = HERE / "assets"
DIAL_DIR = HERE.parent / "dial"
DIAL_SOURCES = [DIAL_DIR / "local" / "dial_1200dpi.png", DIAL_DIR / "dial_1200dpi.png"]
DIAL_HALF = 42.2          # make_dial.py: 84.4 mm square artboard centred on the arbor
DIAL_TEX_PX = 2048

GROUPS = [
    ("case", "Case"),
    ("lid", "Lid"),
    ("plates", "Movement plates"),
    ("gears", "Gear train"),
    ("hands", "Hands"),
    ("dial", "Dial"),
    ("electronics", "Electronics"),
    ("hardware", "Hardware"),
]


def view_group(p) -> str:
    if p.name in ("movement_base_plate_P1", "dial_plate_P2"):
        return "plates"
    if p.group == "movement":
        return "gears"
    return p.group


def explode_dz(p, zmin: float) -> float:
    """Vertical offset (mm) at full explode, bottom-to-top in assembly order."""
    n, g = p.name, p.group
    if g == "lid":
        return 270.0
    if n.startswith(("case_upper", "crown_", "hinge_", "magnet_body", "reed_switch", "usb_c")):
        return 225.0
    if n == "crystal_seat_spider":
        return 178.0
    if n in ("crystal_frame_spider", "crystal") or n.startswith("screw_top"):
        return 195.0
    if g == "hands":
        order = ["hand_needle", "hand_III", "hand_II", "hand_I", "hand_cap_rosette"]
        return 135.0 + 8.0 * (order.index(n) if n in order else 0)
    if n == "dial_sticker":
        return 110.0
    if n in ("dial_plate_P2", "cannon", "standoff_hand"):
        return 105.0
    if n.startswith("gear_"):
        return 72.0 + 3.0 * max(0.0, zmin - D.LEVELS[0])
    if n.startswith(("arbor_", "shaft_", "sleeve_", "knob_", "magnet_")):
        return 72.0
    if n in ("movement_base_plate_P1", "standoff_gear"):
        return 48.0
    if n in ("pcb_carrier", "standoff_bay"):
        return 12.0
    if g == "electronics":
        return 24.0
    return 0.0


def finish(p) -> str:
    if p.material.startswith("clear") or p.color == D.GLASS:
        return "glass"
    if p.name == "dial_sticker":
        return "dial"
    if p.color in (D.BRASS, D.BRASS_DARK, D.COPPER, D.STEEL, D.BLUED):
        return "metal"
    return "matte"


def loc_matrix(loc) -> list[float]:
    """cq.Location -> column-major 4x4 (three.js Matrix4.fromArray order)."""
    t = loc.wrapped.Transformation()
    m = [[t.Value(r, c) for c in range(1, 5)] for r in range(1, 4)] + [[0.0, 0.0, 0.0, 1.0]]
    return [m[r][c] for c in range(4) for r in range(4)]


def apply(m16: list[float], pts: np.ndarray) -> np.ndarray:
    m = np.array(m16, dtype=float).reshape(4, 4).T
    return pts @ m[:3, :3].T + m[:3, 3]


# ---------------------------------------------------------------------------
def write_glb(path: Path, meshes: list[tuple[str, np.ndarray, np.ndarray]]) -> None:
    """Minimal glTF 2.0 binary: one node + mesh per entry, POSITION + indices only."""
    blob = bytearray()
    views, accessors, gl_meshes, nodes = [], [], [], []

    def add_view(data: bytes, target: int) -> int:
        while len(blob) % 4:
            blob.append(0)
        views.append(dict(buffer=0, byteOffset=len(blob), byteLength=len(data), target=target))
        blob.extend(data)
        return len(views) - 1

    for name, verts, tris in meshes:
        v = verts.astype(np.float32)
        idx = tris.astype(np.uint16 if len(v) < 65536 else np.uint32).ravel()
        pv = add_view(v.tobytes(), 34962)
        accessors.append(dict(bufferView=pv, componentType=5126, count=len(v), type="VEC3",
                              min=v.min(axis=0).tolist(), max=v.max(axis=0).tolist()))
        pa = len(accessors) - 1
        iv = add_view(idx.tobytes(), 34963)
        accessors.append(dict(bufferView=iv, componentType=5123 if idx.dtype == np.uint16 else 5125,
                              count=int(idx.size), type="SCALAR"))
        gl_meshes.append(dict(name=name, primitives=[dict(attributes=dict(POSITION=pa),
                                                           indices=len(accessors) - 1)]))
        nodes.append(dict(name=name, mesh=len(gl_meshes) - 1))

    while len(blob) % 4:
        blob.append(0)
    gltf = dict(asset=dict(version="2.0", generator="alethiometer export_viewer.py"),
                scene=0, scenes=[dict(nodes=list(range(len(nodes))))], nodes=nodes,
                meshes=gl_meshes, accessors=accessors, bufferViews=views,
                buffers=[dict(byteLength=len(blob))])
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    total = 12 + 8 + len(js) + 8 + len(blob)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        f.write(struct.pack("<II", len(blob), 0x004E4942) + bytes(blob))


def export_dial() -> str | None:
    src = next((p for p in DIAL_SOURCES if p.exists()), None)
    if src is None:
        return None
    from PIL import Image
    im = Image.open(src).convert("RGBA")
    if max(im.size) > DIAL_TEX_PX:
        im = im.resize((DIAL_TEX_PX, DIAL_TEX_PX), Image.LANCZOS)
    im.save(ASSETS / "dial.png", optimize=True)
    return src.relative_to(HERE.parent.parent).as_posix()


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tolerance", type=float, default=0.1, help="linear tessellation tolerance, mm")
    ap.add_argument("--angular", type=float, default=0.3, help="angular tolerance, rad")
    args = ap.parse_args()

    t0 = time.time()
    parts = D.all_parts()
    print(f"built {len(parts)} part types in {time.time() - t0:.1f}s", flush=True)
    ASSETS.mkdir(exist_ok=True)

    meshes, manifest_parts = [], []
    open_m = loc_matrix(D.lid_open_location())
    for p in parts:
        vs, ts = p.solid.tessellate(args.tolerance, args.angular)
        verts = np.array([v.toTuple() for v in vs], dtype=float)
        tris = np.array(ts, dtype=np.int64).reshape(-1, 3)
        meshes.append((p.name, verts, tris))
        mats = [loc_matrix(loc) for loc in p.placements]
        zs = np.concatenate([apply(m, verts)[:, 2] for m in mats])
        zmin, zmax = float(zs.min()), float(zs.max())
        manifest_parts.append(dict(
            name=p.name, group=view_group(p), cad_group=p.group, kind=p.kind,
            material=p.material, spec=p.spec, qty=p.qty, qty_extra=p.qty_extra,
            color=[round(c, 4) for c in p.color], finish=finish(p),
            z=[round(zmin, 3), round(zmax, 3)], explode=explode_dz(p, zmin),
            placements=[[round(x, 6) for x in m] for m in mats],
            open=[round(x, 6) for x in open_m] if p.group == "lid" else None,
            triangles=len(tris),
        ))

    write_glb(ASSETS / "alethiometer.glb", meshes)
    dial_src = export_dial()
    ax, az = D.HINGE_AXIS
    manifest = dict(
        units="mm", up="z", generated=int(time.time()),
        groups=[dict(id=g, label=lbl) for g, lbl in GROUPS],
        hinge=dict(point=[ax, 0.0, az], axis=[0.0, 1.0, 0.0], open_deg=D.LID_OPEN_ANGLE, rest_deg=D.LID_REST_ANGLE),
        dial=dict(texture="dial.png" if dial_src else None, source=dial_src, half=DIAL_HALF),
        z_top=D.Z_TOP, summary=D.summary(), parts=manifest_parts,
    )
    (ASSETS / "parts.json").write_text(json.dumps(manifest, indent=1, default=str), encoding="utf-8")

    tri = sum(m["triangles"] for m in manifest_parts)
    size = sum(f.stat().st_size for f in ASSETS.iterdir()) / 1e6
    print(f"wrote {len(parts)} parts, {tri:,} triangles, {size:.1f} MB to {ASSETS} "
          f"(dial: {dial_src or 'none'}) in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
