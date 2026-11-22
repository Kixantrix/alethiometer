"""Export the brass alethiometer for the web viewer in this folder.

    python hardware/viewer/export_viewer.py [--tolerance 0.1] [--no-pcb]

Writes hardware/viewer/assets/:
    alethiometer.glb   one mesh per part type (node name = part name), in its local frame
    parts.json         manifest: metadata, placements, open-lid transform, explode offsets
    dial.png           dial sticker texture (downscaled)
    pcb.glb            the real carrier board from KiCad (copper, pads, holes, mask, silkscreen,
                       fitted THT parts), if kicad-cli is installed; manifest["pcb"] places it

Coordinates are millimetres, Z up, exactly as in hardware/cad/design.py.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import struct
import subprocess
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

PCB_DIR = HERE.parent / "pcb"
PCB_BOARD = PCB_DIR / "alethiometer_carrier.kicad_pcb"
PCB_PART = "pcb_carrier"
# 3D models for what is actually soldered to the bare board: resistors, C1, the J1 debug header and
# the crown switch. J2 is optional and J4-J7 are wire pads, so their pin-header models stay out.
PCB_COMPONENTS = "R*,C*,J1,SW*"
# CAD stand-ins that KiCad draws for real, by reference designator. Replaced only when the KiCad
# export actually contains a model for that reference (KiCad 10 ships none for the B3F-315x).
PCB_DUPLICATES = {"SW1": "crown_switch"}

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
    write_container(path, gltf, blob)


def write_container(path: Path, gltf: dict, blob: bytes) -> None:
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
# Real carrier PCB from KiCad
def find_kicad_cli() -> str | None:
    env = os.environ.get("KICAD_CLI")
    if env and Path(env).is_file():
        return env
    found = shutil.which("kicad-cli")
    if found:
        return found
    cands: list[Path] = []
    for var in ("LOCALAPPDATA", "ProgramFiles", "ProgramW6432"):
        base = os.environ.get(var)
        for root in ([Path(base) / "Programs" / "KiCad", Path(base) / "KiCad"] if base else []):
            cands += root.glob("*/bin/kicad-cli.exe")
    cands += [Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"),
              Path("/usr/local/bin/kicad-cli"), Path("/usr/bin/kicad-cli")]
    cands = [c for c in cands if c.is_file()]
    version = lambda c: [int(n) for n in re.findall(r"\d+", c.parent.parent.name)]  # noqa: E731
    return str(max(cands, key=version)) if cands else None


def pcb_origin() -> tuple[float, float]:
    """make_pcb.ORIGIN: where the CAD origin (dial centre) sits on the KiCad page, mm."""
    tree = ast.parse((PCB_DIR / "make_pcb.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "ORIGIN" for t in node.targets):
            return tuple(ast.literal_eval(node.value))
    raise ValueError("ORIGIN not found in make_pcb.py")


def read_glb(path: Path) -> tuple[dict, bytes]:
    b = path.read_bytes()
    jl, = struct.unpack("<I", b[12:16])
    js = json.loads(b[20:20 + jl])
    bl, = struct.unpack("<I", b[20 + jl:24 + jl])
    return js, b[28 + jl:28 + jl + bl]


def read_accessor(js: dict, blob: bytes, i: int) -> np.ndarray:
    a = js["accessors"][i]
    bv = js["bufferViews"][a["bufferView"]]
    dt = np.dtype({5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}[a["componentType"]])
    n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride") or dt.itemsize * n
    arr = np.ndarray((a["count"], n), dt, blob, off, (stride, dt.itemsize))
    return arr.astype(np.float64 if dt.kind == "f" else np.int64)


def node_matrix(n: dict) -> np.ndarray:
    if "matrix" in n:
        return np.array(n["matrix"], dtype=float).reshape(4, 4).T
    x, y, z, w = n.get("rotation", [0.0, 0.0, 0.0, 1.0])
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    m = np.eye(4)
    m[:3, :3] = r * np.array(n.get("scale", [1.0, 1.0, 1.0]))
    m[:3, 3] = n.get("translation", [0.0, 0.0, 0.0])
    return m


def compact_pcb_glb(src: Path, dst: Path) -> dict:
    """Re-pack KiCad's GLB (thousands of tiny primitives) into one primitive per material.

    Board layers (copper, pads, vias, mask, silkscreen, body) are prismatic, so they lose their
    normals and get welded; the viewer flat-shades them. Component models keep smooth normals.
    Everything is baked into the glTF root frame (metres, Y up), which the manifest matrix maps
    to the CAD frame.
    """
    js, blob = read_glb(src)
    layer_prefix = PCB_BOARD.stem + "_"
    groups: dict[tuple, dict] = {}
    refs: set[str] = set()
    body = [np.inf, -np.inf]

    def visit(i: int, parent: np.ndarray, ref: str | None) -> None:
        n = js["nodes"][i]
        m = parent @ node_matrix(n)
        name = n.get("name") or ""
        if name and not name.startswith("=>"):
            ref = name
        if "mesh" in n:
            mesh = js["meshes"][n["mesh"]]
            mname = mesh.get("name") or ""
            layer = mname[len(layer_prefix):] if mname.startswith(layer_prefix) else None
            if layer is None and ref:
                refs.add(ref)
            for pr in mesh["primitives"]:
                if pr.get("mode", 4) != 4:
                    continue
                pos = read_accessor(js, blob, pr["attributes"]["POSITION"]) @ m[:3, :3].T + m[:3, 3]
                idx = (read_accessor(js, blob, pr["indices"]).ravel() if "indices" in pr
                       else np.arange(len(pos)))
                if layer == "PCB":
                    body[0], body[1] = min(body[0], pos[:, 1].min()), max(body[1], pos[:, 1].max())
                g = groups.setdefault((layer or "parts", pr.get("material")), dict(pos=[], nrm=[], idx=[], n=0))
                if layer is None and "NORMAL" in pr["attributes"]:
                    nrm = read_accessor(js, blob, pr["attributes"]["NORMAL"]) @ np.linalg.inv(m[:3, :3])
                    g["nrm"].append(nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12))
                g["pos"].append(pos)
                g["idx"].append(idx + g["n"])
                g["n"] += len(pos)
        for c in n.get("children", []):
            visit(c, m, ref)

    for r in js["scenes"][js.get("scene", 0)]["nodes"]:
        visit(r, np.eye(4), None)

    out = bytearray()
    views, accessors, meshes, nodes = [], [], [], []
    materials = [dict(m) for m in js.get("materials", [])]
    for m in materials:
        # KiCad leaves metallicFactor out on component models, and glTF then defaults it to 1.
        # Treat light, unsaturated colours as metal (leads, pins) and the rest as plastic.
        pbr = m.setdefault("pbrMetallicRoughness", {})
        if "metallicFactor" not in pbr:
            c = pbr.get("baseColorFactor", [1, 1, 1, 1])[:3]
            metal = max(c) > 0.3 and max(c) - min(c) < 0.1
            pbr["metallicFactor"], pbr["roughnessFactor"] = (1.0, 0.35) if metal else (0.0, 0.5)

    def add(data: np.ndarray, target: int, **acc) -> int:
        while len(out) % 4:
            out.append(0)
        views.append(dict(buffer=0, byteOffset=len(out), byteLength=data.nbytes, target=target))
        out.extend(data.tobytes())
        accessors.append(dict(bufferView=len(views) - 1, count=len(data), **acc))
        return len(accessors) - 1

    tris = 0
    for (layer, mat), g in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1] or 0)):
        pos, idx = np.concatenate(g["pos"]), np.concatenate(g["idx"]).reshape(-1, 3)
        nrm = np.concatenate(g["nrm"]) if len(g["nrm"]) == len(g["pos"]) else None
        if layer != "parts":                                  # weld coincident vertices (0.1 um)
            _, first, inv = np.unique(np.round(pos * 1e7).astype(np.int64), axis=0,
                                      return_index=True, return_inverse=True)
            pos, idx = pos[first], inv.ravel()[idx]
            idx = idx[(idx[:, 0] != idx[:, 1]) & (idx[:, 1] != idx[:, 2]) & (idx[:, 0] != idx[:, 2])]
        if layer == "silkscreen" and mat is not None:         # ink is opaque; avoids blend sorting
            pbr = materials[mat].setdefault("pbrMetallicRoughness", {})
            pbr["baseColorFactor"] = pbr.get("baseColorFactor", [1, 1, 1, 1])[:3] + [1.0]
            materials[mat].pop("alphaMode", None)
        p32 = pos.astype(np.float32)
        attrs = dict(POSITION=add(p32, 34962, componentType=5126, type="VEC3",
                                  min=p32.min(axis=0).tolist(), max=p32.max(axis=0).tolist()))
        if nrm is not None:
            attrs["NORMAL"] = add(nrm.astype(np.float32), 34962, componentType=5126, type="VEC3")
        big = len(pos) >= 65536
        ia = add(idx.astype(np.uint32 if big else np.uint16).ravel(), 34963,
                 componentType=5125 if big else 5123, type="SCALAR")
        prim = dict(attributes=attrs, indices=ia, mode=4)
        if mat is not None:
            prim["material"] = mat
        side = "" if layer not in ("silkscreen", "soldermask") else ("_top" if pos[:, 1].mean() > 0.0008 else "_bottom")
        name = f"{layer}{side}"
        meshes.append(dict(name=name, primitives=[prim]))
        nodes.append(dict(name=name, mesh=len(meshes) - 1))
        tris += len(idx)

    while len(out) % 4:
        out.append(0)
    gltf = dict(asset=dict(version="2.0", generator="alethiometer export_viewer.py (from KiCad)"),
                scene=0, scenes=[dict(nodes=list(range(len(nodes))))], nodes=nodes, meshes=meshes,
                materials=materials, accessors=accessors, bufferViews=views,
                buffers=[dict(byteLength=len(out))])
    write_container(dst, gltf, out)
    return dict(refs=sorted(refs), triangles=tris, body_y=body)


def export_pcb(cad_box: np.ndarray | None, part_names: set[str]) -> dict | None:
    """kicad-cli -> assets/pcb.glb, plus the manifest entry that places it on the CAD carrier."""
    cli = find_kicad_cli()
    if cli is None:
        print("warning: kicad-cli not found (install KiCad or set KICAD_CLI); "
              "the viewer will show the plain CAD carrier", flush=True)
        return None
    if not PCB_BOARD.exists():
        print(f"warning: {PCB_BOARD} missing; skipping the KiCad board", flush=True)
        return None
    ox, oy = pcb_origin()
    raw = ASSETS / "pcb_kicad.glb"
    cmd = [cli, "pcb", "export", "glb", "--force", "--subst-models", "--include-tracks", "--include-pads",
           "--include-zones", "--include-silkscreen", "--include-soldermask",
           "--component-filter", PCB_COMPONENTS, "--user-origin", f"{ox:g}x{oy:g}mm", "-o", str(raw), str(PCB_BOARD)]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"warning: kicad-cli failed ({e}); skipping the KiCad board", flush=True)
        return None
    if r.returncode != 0 or not raw.exists():
        print(f"warning: kicad-cli exited {r.returncode}; skipping the KiCad board\n{r.stdout}{r.stderr}", flush=True)
        return None
    try:
        info = compact_pcb_glb(raw, ASSETS / "pcb.glb")
    finally:
        raw.unlink(missing_ok=True)

    # KiCad glTF: metres, Y up, board body bottom at y = 0, z = -CAD y (KiCad page y points down),
    # x/z relative to --user-origin = the CAD origin. CAD = (1000 gx, -1000 gz, 1000 gy + dz), a
    # proper rotation (+90 deg about X, not a mirror), so the top silkscreen reads from above.
    # dz centres the board body on the CAD slab; KiCad's body is thinner than 1.6 mm by the
    # copper and mask layers on either face.
    dz = float((D.Z_CARRIER + D.Z_CARRIER_TOP) / 2 - 1000.0 * (info["body_y"][0] + info["body_y"][1]) / 2)
    rows = [[1000.0, 0, 0, 0], [0, 0, -1000.0, 0], [0, 1000.0, 0, dz], [0, 0, 0, 1.0]]
    matrix = [round(rows[r][c], 6) for c in range(4) for r in range(4)]
    if cad_box is not None:
        js, _ = read_glb(ASSETS / "pcb.glb")
        lo = np.full(3, np.inf)
        hi = -lo
        for mesh in js["meshes"]:
            if mesh["name"] == "PCB":
                a = js["accessors"][mesh["primitives"][0]["attributes"]["POSITION"]]
                lo, hi = np.minimum(lo, a["min"]), np.maximum(hi, a["max"])
        m = np.array(rows)
        corners = np.array([lo, hi]) @ m[:3, :3].T + m[:3, 3]
        k_box = np.array([corners.min(axis=0), corners.max(axis=0)])
        err = np.abs(k_box - cad_box).max(axis=0)
        print(f"  KiCad board vs CAD {PCB_PART}: x/y/z bounds differ by {err.round(3).tolist()} mm", flush=True)
        if max(err[0], err[1]) > 0.1:
            print("warning: the KiCad outline does not match the CAD carrier; regenerate hardware/pcb", flush=True)
    replaces = [PCB_PART] + [n for ref, n in PCB_DUPLICATES.items() if ref in info["refs"] and n in part_names]
    size = (ASSETS / "pcb.glb").stat().st_size / 1e6
    print(f"  KiCad board: {info['triangles']:,} triangles, {size:.1f} MB, parts {','.join(info['refs'])} "
          f"in {time.time() - t0:.0f}s ({Path(cli).name})", flush=True)
    return dict(file="pcb.glb", source=PCB_BOARD.relative_to(HERE.parent.parent).as_posix(), attach=PCB_PART,
                replaces=replaces, components=info["refs"], matrix=matrix, triangles=info["triangles"])


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tolerance", type=float, default=0.1, help="linear tessellation tolerance, mm")
    ap.add_argument("--angular", type=float, default=0.3, help="angular tolerance, rad")
    ap.add_argument("--no-pcb", action="store_true", help="skip the KiCad carrier board export")
    args = ap.parse_args()

    t0 = time.time()
    parts = D.all_parts()
    print(f"built {len(parts)} part types in {time.time() - t0:.1f}s", flush=True)
    ASSETS.mkdir(exist_ok=True)

    meshes, manifest_parts = [], []
    cad_pcb_box = None
    open_m = loc_matrix(D.lid_open_location())
    for p in parts:
        vs, ts = p.solid.tessellate(args.tolerance, args.angular)
        verts = np.array([v.toTuple() for v in vs], dtype=float)
        tris = np.array(ts, dtype=np.int64).reshape(-1, 3)
        meshes.append((p.name, verts, tris))
        mats = [loc_matrix(loc) for loc in p.placements]
        zs = np.concatenate([apply(m, verts)[:, 2] for m in mats])
        zmin, zmax = float(zs.min()), float(zs.max())
        if p.name == PCB_PART:
            w = apply(mats[0], verts)
            cad_pcb_box = np.array([w.min(axis=0), w.max(axis=0)])
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
    pcb = None
    if not args.no_pcb:
        pcb = export_pcb(cad_pcb_box, {p.name for p in parts})
    if pcb is None:
        (ASSETS / "pcb.glb").unlink(missing_ok=True)
    ax, az = D.HINGE_AXIS
    manifest = dict(
        units="mm", up="z", generated=int(time.time()),
        groups=[dict(id=g, label=lbl) for g, lbl in GROUPS],
        hinge=dict(point=[ax, 0.0, az], axis=[0.0, 1.0, 0.0], open_deg=D.LID_OPEN_ANGLE, rest_deg=D.LID_REST_ANGLE),
        dial=dict(texture="dial.png" if dial_src else None, source=dial_src, half=DIAL_HALF),
        pcb=pcb, z_top=D.Z_TOP, summary=D.summary(), parts=manifest_parts,
    )
    (ASSETS / "parts.json").write_text(json.dumps(manifest, indent=1, default=str), encoding="utf-8")

    tri = sum(m["triangles"] for m in manifest_parts)
    size = sum(f.stat().st_size for f in ASSETS.iterdir()) / 1e6
    print(f"wrote {len(parts)} parts, {tri:,} triangles, {size:.1f} MB to {ASSETS} "
          f"(dial: {dial_src or 'none'}) in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
