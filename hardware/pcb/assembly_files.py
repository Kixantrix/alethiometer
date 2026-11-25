"""Factory through-hole assembly files for the carrier PCB: an assembly BOM and a placement (CPL)
file, in the column layout JLCPCB and PCBWay accept.

    python assembly_files.py          # uses kicad-cli; also called by make_pcb.py's fab export

The fab fits every part marked "fab" below; "you" parts arrive in the kit for the builder, and
test pads (TP*) and the J7 cable pads have nothing fitted. Plain Python, so it runs with or
without KiCad's own interpreter.
"""
from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOARD_FILE = HERE / "alethiometer_carrier.kicad_pcb"
FAB = HERE / "fab"
KICAD_CLI = os.environ.get("KICAD_CLI") or next(
    (p for p in (Path.home() / "Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
                 Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")) if p.exists()), "kicad-cli")

# Every module socket is cut from the same 5 mm-body short female header (the CAD height stack
# assumes exactly 5.0 mm: a taller body raises the AS5600s toward their magnets).
SOCKET = ("Adafruit", "3008", "Short female header 0.1\", 1×36, 5 mm body (Adafruit #3008; DigiKey 1528-3008-ND). "
          "Cut to length; one position is lost at each cut. Exactly 5 mm: no substitutes")

# designator -> (fit, description, manufacturer, MPN, notes)
PARTS = {
    "U1": ("fab", "Sockets for the ProS3: 2 × 1×17", *SOCKET[:2], SOCKET[2]),
    "U2": ("fab", "Sockets for AS5600 I: 1×6 + 1×2 rest post", *SOCKET[:2], SOCKET[2]),
    "U3": ("fab", "Sockets for AS5600 II: 1×6 + 1×2 rest post", *SOCKET[:2], SOCKET[2]),
    "U4": ("fab", "Sockets for AS5600 III: 1×6 + 1×2 rest post", *SOCKET[:2], SOCKET[2]),
    "U5": ("fab", "Sockets for the DRV8833: 1×8 + 1×6", *SOCKET[:2], SOCKET[2]),
    "U6": ("fab", "Sockets for the MAX98357A: 1×7 + 2 × 1×1 (speaker pins)", *SOCKET[:2], SOCKET[2]),
    "U7": ("fab", "Socket for the USB-C breakout: 1×8", *SOCKET[:2], SOCKET[2]),
    "M1": ("fab", "Sockets for the X27.168: 2 × 1×4", *SOCKET[:2], SOCKET[2]),
    "R1": ("fab", "Resistor 10 kΩ 1 % ¼ W metal film, axial, 10.16 mm pitch", "Yageo", "MFR-25FBF52-10K", ""),
    "R3": ("fab", "Resistor 10 kΩ 1 % ¼ W metal film, axial, 10.16 mm pitch", "Yageo", "MFR-25FBF52-10K", ""),
    "R5": ("fab", "Resistor 10 kΩ 1 % ¼ W metal film, axial, 10.16 mm pitch", "Yageo", "MFR-25FBF52-10K", ""),
    "R2": ("fab", "Resistor 47 kΩ 1 % ¼ W metal film, axial, 10.16 mm pitch", "Yageo", "MFR-25FBF52-47K", ""),
    "R4": ("fab", "Resistor 47 kΩ 1 % ¼ W metal film, axial, 10.16 mm pitch", "Yageo", "MFR-25FBF52-47K", ""),
    "R6": ("fab", "Resistor 47 kΩ 1 % ¼ W metal film, axial, 10.16 mm pitch", "Yageo", "MFR-25FBF52-47K", ""),
    "C1": ("fab", "100 µF 16 V aluminium electrolytic, radial Ø6.3 × 7 mm, 2.5 mm pitch", "Panasonic",
           "ECE-A1CKA101", "Polarised: long leg to the square + pad. ≤ 11 mm tall"),
    "J1": ("fab", "Male header 1×8, 2.54 mm, vertical (debug)", "Sullins", "PRPC008SAAN-RC", ""),
    "J4": ("fab", "PicoBlade 1.25 mm vertical header, 5 pins (mic)", "Molex", "53047-0510", ""),
    "J5": ("fab", "PicoBlade 1.25 mm vertical header, 2 pins (speaker)", "Molex", "53047-0210", ""),
    "J8": ("fab", "JST PH 2.0 mm side-entry socket, 2 pins (battery)", "JST", "S2B-PH-K-S", ""),
    "SW1": ("fab", "Right-angle 6 × 6 mm tactile switch (crown)", "Omron (Aratas)", "B3F-3152",
            "B3F-3150 footprint; the B3F-3150 itself also fits. Not the B3F-3100 (shorter plunger)"),
    "SW2": ("fab", "Right-angle SPDT slide switch (power)", "C&K", "OS102011MA1QN1", "Fit flat against the board"),
    "J2": ("dnp", "Spare GPIO header 1×7 (optional)", "", "", "Leave empty"),
    "J7": ("you", "Pads for the cut USB-C cable", "", "", "The builder solders the cable (ASSEMBLY.md §4.2)"),
}


def export_positions(path: Path) -> list[dict]:
    subprocess.run([str(KICAD_CLI), "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both",
                    "--use-drill-file-origin", "--output", str(path), str(BOARD_FILE)],
                   check=True, capture_output=True)
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write(fab: Path = FAB) -> tuple[Path, Path]:
    fab.mkdir(parents=True, exist_ok=True)
    raw = fab / "positions_all.csv"
    rows = export_positions(raw)
    raw.unlink()
    refs = {r["Ref"] for r in rows}
    missing = sorted(r for r in refs if not r.startswith("TP") and r not in PARTS)
    if missing:
        raise SystemExit(f"assembly_files.py: no BOM entry for {', '.join(missing)}")
    fitted = [r for r in rows if PARTS.get(r["Ref"], ("",))[0] == "fab"]
    bom, cpl = fab / "assembly_bom.csv", fab / "assembly_cpl.csv"
    groups: dict[tuple, list[str]] = {}
    for r in fitted:
        _, desc, mfr, mpn, notes = PARTS[r["Ref"]]
        key = (desc, mfr, mpn, notes, r["Package"]) if mpn != SOCKET[1] else (SOCKET[2], mfr, mpn, "", "")
        groups.setdefault(key, []).append(r["Ref"])
    with open(bom, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "Quantity", "Manufacturer", "Manufacturer Part #",
                    "Notes"])
        for (desc, mfr, mpn, notes, pkg), designators in groups.items():
            if mpn == SOCKET[1]:
                detail = "; ".join(f"{d}: {PARTS[d][1].split(': ', 1)[-1]}" for d in designators)
                w.writerow([desc, ",".join(designators), "socket strips", "about 3 strips (110 positions)", mfr,
                            mpn, "Fit square and flat on the board. " + detail])
            else:
                w.writerow([desc, ",".join(designators), pkg, len(designators), mfr, mpn, notes])
    with open(cpl, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in fitted:
            w.writerow([r["Ref"], f"{float(r['PosX']):.3f}mm", f"{float(r['PosY']):.3f}mm",
                        "Top" if r["Side"] == "top" else "Bottom", f"{float(r['Rot']) % 360:g}"])
    return bom, cpl


if __name__ == "__main__":
    for p in write():
        print(p.relative_to(HERE))
    sys.exit(0)
