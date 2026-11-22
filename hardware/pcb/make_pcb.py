"""Generate the alethiometer carrier PCB (KiCad 10) from the shared layout.

Run with KiCad's bundled Python (it provides `pcbnew`):

    & "$env:LOCALAPPDATA\\Programs\\KiCad\\10.0\\bin\\python.exe" hardware/pcb/make_pcb.py --freerouting <freerouting-1.9.0.jar>

It builds alethiometer_carrier.kicad_pcb from scratch: board outline from the
case geometry, every footprint placed from hardware/cad/layout.py, nets from the
tables below, labelled test pads and wire pads, ground pours. It then autoroutes
with Freerouting (if given), refills zones, runs DRC with kicad-cli and exports
Gerbers/drill (zipped for JLCPCB/PCBWay), PDF plots, 3D renders and a STEP.

Everything is through-hole and every module is socketed: the carrier gets
0.1" female headers (5 mm "short" ones for the breakouts and the ProS3, two
standard 1x4 for the X27 motor's rear pins) and each module plugs in on its own
male headers, so any of them can be pulled to reflash or replace it. Off-board
parts (mic, speaker, crown switch, lid reed) are wired to labelled pads.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "cad"))
import layout as L  # noqa: E402

if sys.platform == "darwin":
    KICAD = next(p for p in Path(pcbnew.__file__).resolve().parents if p.name == "Contents")
    KICAD_CLI = KICAD / "MacOS" / "kicad-cli"
    STD_FP = KICAD / "SharedSupport" / "footprints"
else:
    KICAD = Path(sys.executable).resolve().parents[1]
    KICAD_CLI = KICAD / "bin" / "kicad-cli.exe"
    STD_FP = KICAD / "share" / "kicad" / "footprints"
LOCAL_LIB = HERE / "alethiometer.pretty"
BOARD_FILE = HERE / "alethiometer_carrier.kicad_pcb"
FAB = HERE / "fab"
ORIGIN = (150.0, 100.0)            # where the dial centre lands on the KiCad page

TRACK_W, CLEARANCE, VIA_D, VIA_DRILL = 0.35, 0.25, 0.8, 0.4
POWER_TRACK_W = 0.6
POWER_NETS = {"GND", "VBAT", "+5V", "+3V3", "3V3_SW", "AOUT1", "AOUT2", "BOUT1", "BOUT2", "SPK+", "SPK-",
              "USB_VBUS"}

mm = pcbnew.FromMM


def P(x: float, y: float) -> pcbnew.VECTOR2I:
    """CAD frame (y up, dial centre origin) -> KiCad board coordinates."""
    return pcbnew.VECTOR2I(mm(ORIGIN[0] + x), mm(ORIGIN[1] - y))


def LP(x: float, y: float) -> pcbnew.VECTOR2I:
    """Footprint-local CAD coordinates (y up) -> KiCad footprint-local (y down)."""
    return pcbnew.VECTOR2I(mm(x), mm(-y))


def _text(parent, text, pos, size, layer, angle=0.0):
    t = pcbnew.PCB_TEXT(parent)
    t.SetText(text)
    t.SetPosition(pos)
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(max(0.1, size * 0.15)))
    t.SetTextAngleDegrees(angle)
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    return t


# =============================================================================
# Footprints
# =============================================================================
def _seg(fp, a, b, layer, width):
    s = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(LP(*a))
    s.SetEnd(LP(*b))
    s.SetLayer(layer)
    s.SetWidth(mm(width))
    fp.Add(s)


def _rect(fp, w, h, layer, width):
    c = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    for a, b in zip(c, c[1:] + c[:1]):
        _seg(fp, a, b, layer, width)


def _circle(fp, x, y, r, layer, width=0.12):
    s = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_CIRCLE)
    s.SetCenter(LP(x, y))
    s.SetEnd(LP(x + r, y))
    s.SetLayer(layer)
    s.SetWidth(mm(width))
    fp.Add(s)


def _label(fp, text, x, y, size=0.8, both=True, angle=0.0):
    fp.Add(_text(fp, text, LP(x, y), size, pcbnew.F_SilkS, angle))
    if both:
        fp.Add(_text(fp, text, LP(x, y), size, pcbnew.B_SilkS, angle))


def module_fp(board, name, desc, pads, outline=None, extra=None, silk=True):
    """pads: [(number, x, y, drill, pad_dia, label, label_dy)] in CAD-local mm.
    pad_dia 0 -> non-plated clearance hole. Pad '1' is square."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID("alethiometer", name))
    fp.SetLibDescription(desc)
    fp.SetAttributes(pcbnew.FP_THROUGH_HOLE)
    for num, x, y, drill, dia, label, ldy in pads:
        pad = pcbnew.PAD(fp)
        pad.SetNumber(str(num))
        if dia:
            pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
            pad.SetShape(pcbnew.PAD_SHAPE_RECTANGLE if str(num) == "1" else pcbnew.PAD_SHAPE_CIRCLE)
            pad.SetSize(pcbnew.VECTOR2I(mm(dia), mm(dia)))
            pad.SetLayerSet(pad.PTHMask())
        else:
            pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
            pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
            pad.SetSize(pcbnew.VECTOR2I(mm(drill), mm(drill)))
            pad.SetLayerSet(pad.UnplatedHoleMask())
        pad.SetDrillSize(pcbnew.VECTOR2I(mm(drill), mm(drill)))
        pad.SetFPRelativePosition(LP(x, y))
        fp.Add(pad)
        if label:
            _label(fp, label, x, y + ldy)
    if outline:
        if silk:
            _rect(fp, *outline, pcbnew.F_SilkS, 0.12)
        _rect(fp, *outline, pcbnew.F_Fab, 0.1)
        _rect(fp, outline[0] + 0.5, outline[1] + 0.5, pcbnew.F_CrtYd, 0.05)
    if extra:
        extra(fp)
    fp.Reference().SetLayer(pcbnew.F_Fab)
    fp.Value().SetLayer(pcbnew.F_Fab)
    return fp


def hdr(n0, x0, y0, dx, dy, names, ldy, drill=1.0, dia=1.7):
    return [(n0 + i, x0 + i * dx, y0 + i * dy, drill, dia, names[i], ldy) for i in range(len(names))]


def fp_as5600(board):
    a = L.ADAFRUIT_AS5600

    def extra(fp):
        _circle(fp, 0, 0, 3.0, pcbnew.F_SilkS)               # chip centre = magnet axis
        _seg(fp, (-1.5, 0), (1.5, 0), pcbnew.F_SilkS, 0.12)
        _seg(fp, (0, -1.5), (0, 1.5), pcbnew.F_SilkS, 0.12)
        _label(fp, "AS5600 - magnet above", 0, 4.4, 0.8, both=False)
        _label(fp, "rest post", 5.4, a["rest"][0][1], 0.8, both=False)
    pads = hdr(1, -6.35, a["header_dy"], 2.54, 0, ["VIN", "3Vo", "GND", "SCL", "SDA", "OUT"], 1.6)
    pads += [(7 + i, x, y, 1.0, 1.7, None, 0) for i, (x, y) in enumerate(a["rest"])]   # 2-pin socket, GND
    return module_fp(board, "Adafruit_AS5600_6357", "Adafruit AS5600 #6357 on a 1x6 socket + 2-pin rest post",
                     pads, (a["w"], a["h"]), extra)


def fp_drv8833(board):
    left = hdr(1, -6.35, 8.89, 0, -2.54, ["VM", "GND", "FLT", "BIN1", "BIN2", "SLP", "AIN2", "AIN1"], 0)
    right = hdr(9, 6.35, -6.35, 0, 2.54, ["AO1", "AO2", "BO2", "BO1", "ASEN", "BSEN"], 0)
    for i, p in enumerate(left):
        left[i] = p[:5] + (None, 0)
    for i, p in enumerate(right):
        right[i] = p[:5] + (None, 0)

    def extra(fp):
        for _, x, y, *_r, in hdr(1, -6.35, 8.89, 0, -2.54, [""] * 8, 0):
            pass
        names_l = ["VM", "GND", "FLT", "BIN1", "BIN2", "SLP", "AIN2", "AIN1"]
        names_r = ["AO1", "AO2", "BO2", "BO1", "ASEN", "BSEN"]
        for i, n in enumerate(names_l):
            _label(fp, n, -3.4, 8.89 - 2.54 * i)
        for i, n in enumerate(names_r):
            _label(fp, n, 3.2, -6.35 + 2.54 * i)
        _label(fp, "DRV8833", 0, 11.0, 0.9, both=False)
    return module_fp(board, "Adafruit_DRV8833_3297", "Adafruit DRV8833 #3297 on 1x8 + 1x6 sockets",
                     left + right, (17.78, 25.4), extra)


def fp_max98357(board):
    row = hdr(1, 7.62, -6.985, -2.54, 0, ["VIN", "GND", "SD", "GAIN", "DIN", "BCLK", "LRC"], 1.6)
    spk = [(8, -1.8, 5.969, 1.0, 1.8, "SPK-", -1.6), (9, 1.7, 5.969, 1.0, 1.8, "SPK+", -1.6)]

    def extra(fp):
        _label(fp, "MAX98357A", 0, 0.5, 0.9, both=False)
    return module_fp(board, "Adafruit_MAX98357A_3006", "Adafruit MAX98357A #3006 on a 1x7 socket + two 1-pin speaker sockets",
                     row + spk, (17.78, 19.05), extra)


def fp_x27(board):
    cx = L.X27_CENTER[0]
    pads = []
    for num, key in (("1", "A1"), ("2", "A2"), ("3", "B1"), ("4", "B2")):
        x, y = L.X27_PINS[key]
        # 1.3 mm holes let the sockets float ~0.3 mm so they can be soldered after the gear mesh is set
        pads.append((num, x - cx, y, 1.3, 2.0, key, -2.0 if y > 0 else 2.0))
    for i, (x, y) in enumerate(((-1.27, 11.43), (1.27, 11.43), (-1.27, -11.43), (1.27, -11.43))):
        pads.append((5 + i, x, y, 1.3, 2.0, None, 0))                 # unused socket positions

    def extra(fp):
        _circle(fp, 0, 0, L.X27_BODY_D / 2, pcbnew.F_SilkS)
        _circle(fp, 0, 0, L.X27_BODY_D / 2, pcbnew.F_Fab, 0.1)
        _label(fp, "X27.168  in two 1x4 sockets", 0, 4.0, 0.9, both=False)
        _label(fp, "coil A", 0, 7.6)
        _label(fp, "coil B", 0, -7.6)
    return module_fp(board, "X27_168_socketed", "Juken X27.168 gauge stepper, rear pins in two 1x4 female headers",
                     pads, None, extra)


def fp_usbc(board):
    u = L.ADAFRUIT_USBC
    names = ["GND", "VBUS", "SBU2", "CC1", "D-", "D+", "SBU1", "CC2"]
    pads = [(i + 1, 8.89 - i * 2.54, u["header_dy"], 1.0, 1.7, None, 0) for i in range(8)]
    pads += [("", x, y, 2.4, 0, None, 0) for x, y in u["holes"]]          # M2 screws on 5 mm spacers

    def extra(fp):
        for i, n in enumerate(names):
            _label(fp, n, 8.89 - i * 2.54, u["header_dy"] + 3.0, 0.8, angle=90)
        _label(fp, "USB-C #4090", 0, 2.6, 0.9, both=False)
        _seg(fp, (-u["w"] / 2, u["h"] / 2 - 2.0), (-u["w"] / 2, -u["h"] / 2), pcbnew.F_SilkS, 0.12)
        _seg(fp, (-u["w"] / 2, -u["h"] / 2), (u["w"] / 2, -u["h"] / 2), pcbnew.F_SilkS, 0.12)
        _seg(fp, (u["w"] / 2, -u["h"] / 2), (u["w"] / 2, u["h"] / 2 - 2.0), pcbnew.F_SilkS, 0.12)
    return module_fp(board, "Adafruit_USB_C_4090", "Adafruit USB Type C breakout #4090 on a 1x8 socket, 2x M2",
                     pads, (u["w"], u["h"]), extra, silk=False)


def place_by_feature(fp, local_pt, local_dir, cad_pt, cad_dir):
    """Orient/position a stock footprint so a feature (KiCad-local mm, y down) lands on cad_pt
    and the feature's direction local_dir points along cad_dir (CAD frame, y up)."""
    want = math.atan2(-cad_dir[1], cad_dir[0])                    # board frame is y-down
    have = math.atan2(local_dir[1], local_dir[0])
    best = None
    for deg in range(-180, 180, 15):                              # find KiCad's rotation sign empirically
        fp.SetOrientationDegrees(deg)
        fp.SetPosition(pcbnew.VECTOR2I(0, 0))
        pads = sorted(fp.Pads(), key=lambda q: (q.GetFPRelativePosition().x, q.GetFPRelativePosition().y))
        a, b = pads[0], pads[-1]
        la, lb = a.GetFPRelativePosition(), b.GetFPRelativePosition()
        ga, gb = a.GetPosition(), b.GetPosition()
        rot = math.atan2(gb.y - ga.y, gb.x - ga.x) - math.atan2(lb.y - la.y, lb.x - la.x)
        err = abs((have + rot - want + math.pi) % (2 * math.pi) - math.pi)
        if best is None or err < best[0]:
            best = (err, deg, rot)
    _, deg, rot = best
    fp.SetOrientationDegrees(deg)
    lx, ly = local_pt
    gx = lx * math.cos(rot) - ly * math.sin(rot)
    gy = lx * math.sin(rot) + ly * math.cos(rot)
    t = P(*cad_pt)
    fp.SetPosition(pcbnew.VECTOR2I(int(t.x - mm(gx)), int(t.y - mm(gy))))


def fp_load(lib_dir: Path, name: str):
    fp = pcbnew.FootprintLoad(str(lib_dir), name)
    if fp is None:
        raise SystemExit(f"missing footprint {lib_dir.name}:{name}")
    return fp


def fp_std(lib, name):
    return fp_load(STD_FP / f"{lib}.pretty", name)


# =============================================================================
# Netlist + placement tables (CAD frame mm)
# =============================================================================
# ProS3 header pin -> net (pin numbers from Unexpected Maker's ProS3 KiCad symbol)
PROS3_NETS = {
    1: "VBAT", 2: "GND", 3: "+5V", 4: "+3V3", 5: "H1", 6: "H2", 7: "IO3", 8: "H3", 9: "AIN1",
    10: "BCLK", 11: "IO0", 12: "3V3_SW", 13: "LID", 14: "AMP_SD", 15: "MIC_SD", 16: "DOUT", 17: "WS",
    22: "IO38", 23: "RX", 24: "TX", 25: "GND", 26: "RST",
    27: "AIN2", 28: "BIN1", 29: "BIN2", 30: "CROWN", 31: "IO34", 32: "IO36", 33: "IO37", 34: "IO35",
}
PROS3_LABELS = {1: "VBAT", 2: "GND", 3: "5V", 4: "3V3", 5: "IO1", 6: "IO2", 7: "IO3", 8: "IO4", 9: "IO5",
                10: "IO21", 11: "IO0", 12: "LDO2", 13: "IO16", 14: "IO15", 15: "IO14", 16: "IO13", 17: "IO12",
                18: "IO42", 19: "IO41", 20: "IO40", 21: "IO39", 22: "IO38", 23: "RX", 24: "TX", 25: "GND",
                26: "RST", 27: "IO6", 28: "IO7", 29: "IO8", 30: "IO9", 31: "IO34", 32: "IO36", 33: "IO37",
                34: "IO35"}

AS5600_NETS = {"I": "H1_OUT", "II": "H2_OUT", "III": "H3_OUT"}

# Test pads: a strip along the bottom edge, two rows, vertical labels above each pad
TP_X0, TP_PITCH, TP_ROW_Y = -11.4, 2.8, (-40.9, -44.0)   # clear of the battery (x < -13.2)
TEST_PADS = [
    "GND", "VBAT", "+5V", "+3V3", "3V3_SW", "H1", "H2", "H3", "CROWN", "LID", "FLT",
    "GND", "AIN1", "AIN2", "BIN1", "BIN2", "BCLK", "WS", "DOUT", "MIC_SD", "AMP_SD", "GND",
]

# Wire pads / aux headers: ref -> (title, x, y, dx, dy, [(net, label)])
HEADERS = {
    "J1": ("DEBUG", 16.0, 30.5, 2.54, 0.0, [("GND", "GND"), ("+3V3", "3V3"), ("TX", "TX"), ("RX", "RX"),
                                           ("IO0", "IO0"), ("RST", "RST"), ("+5V", "5V"), ("VBAT", "BAT")]),
    "J2": ("SPARE GPIO", 16.0, 24.5, 2.54, 0.0, [("GND", "GND"), ("IO3", "3"), ("IO38", "38"), ("IO34", "34"),
                                                 ("IO35", "35"), ("IO36", "36"), ("IO37", "37")]),
    "J4": ("MIC", -46.0, -17.0, 0.0, -2.54, [("3V3_SW", "VDD"), ("GND", "GND"), ("BCLK", "SCK"),
                                             ("WS", "WS"), ("MIC_SD", "SD")]),
    "J5": ("SPKR", -18.5, 31.0, 0.0, -2.54, [("SPK+", "+"), ("SPK-", "-")]),
    "J6": ("LID", 44.0, -18.0, 0.0, -2.54, [("LID", "SW"), ("GND", "GND")]),
    # cut-down USB-C cable from the ProS3's own port: red, white, green, black
    "J7": ("USB CABLE", -35.0, 49.3, 0.0, -2.54, [("USB_VBUS", "VBUS red"), ("USB_D-", "D- white"),
                                                 ("USB_D+", "D+ green"), ("GND", "GND black")]),
}

# Resistors: ref -> (value, net pad1, net pad2, x, y, rot); 10.16 mm axial, pad 1 at (x, y)
RESISTORS = {
    "R1": ("10k", "H1_OUT", "H1", -13.0, 13.5, -90), "R2": ("47k", "H1", "GND", -13.0, 1.0, -90),
    "R3": ("10k", "H2_OUT", "H2", -9.2, 13.5, -90), "R4": ("47k", "H2", "GND", -9.2, 1.0, -90),
    "R5": ("10k", "H3_OUT", "H3", -5.4, 13.5, -90), "R6": ("47k", "H3", "GND", -5.4, 1.0, -90),
    "R7": ("1M", "LID", "+3V3", -1.6, 13.5, -90),
}
CAP = ("C1", "100uF 10V", "VBAT", "GND", (44.0, -30.0), 90)


def build() -> pcbnew.BOARD:
    board = pcbnew.BOARD()
    nets: dict[str, pcbnew.NETINFO_ITEM] = {}

    def net(name: str) -> pcbnew.NETINFO_ITEM:
        if name not in nets:
            n = pcbnew.NETINFO_ITEM(board, name)
            board.Add(n)
            nets[name] = n
        return nets[name]

    def add(fp, ref, value, xy, rot=0.0, padnets=None):
        fp.SetReference(ref)
        fp.SetValue(value)
        board.Add(fp)
        fp.SetPosition(P(*xy))
        fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            n = (padnets or {}).get(pad.GetNumber())
            if n:
                pad.SetNet(net(n))
        return fp

    def text(s, xy, size, layer=pcbnew.F_SilkS, angle=0.0):
        t = _text(board, s, P(*xy), size, layer, angle)
        board.Add(t)
        return t

    # ---- design rules ----
    ds = board.GetDesignSettings()
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetTrackWidth(mm(TRACK_W))
    nc.SetClearance(mm(CLEARANCE))
    nc.SetViaDiameter(mm(VIA_D))
    nc.SetViaDrill(mm(VIA_DRILL))
    ds.m_CopperEdgeClearance = mm(0.5)
    ns = ds.m_NetSettings
    power = pcbnew.NETCLASS("Power")
    power.SetTrackWidth(mm(POWER_TRACK_W))
    power.SetClearance(mm(CLEARANCE))
    power.SetViaDiameter(mm(VIA_D))
    power.SetViaDrill(mm(VIA_DRILL))
    ns.SetNetclass("Power", power)
    for n in POWER_NETS:
        ns.SetNetclassPatternAssignment(n, "Power")

    # ---- outline ----
    w, c = L.octagon_inset(L.CASE_W, L.CASE_CHAMFER, L.T040 + L.CARRIER_CLEAR)
    pts = L.octagon_pts(w, c)
    for a, b in zip(pts, pts[1:] + pts[:1]):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a))
        s.SetEnd(P(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        board.Add(s)

    # ---- modules ----
    pp = L.PROS3_PLACE
    pros3 = add(fp_load(LOCAL_LIB, "ProS3_TH"), "U1", "UM ProS3", pp["c"], pp["rot"],
                {str(k): v for k, v in PROS3_NETS.items()})
    pros3.Reference().SetVisible(False)
    for pad in pros3.Pads():          # pin names between the rows
        lab = PROS3_LABELS.get(int(pad.GetNumber()), "")
        pos = pad.GetPosition()
        off = mm(2.6) if pros3.GetPosition().y > pos.y else -mm(2.6)      # toward the module centre
        p = pcbnew.VECTOR2I(pos.x, pos.y + off)
        for layer in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            board.Add(_text(board, lab, p, 0.8, layer, 90))
    text("ProS3   USB-C -> cable to J7", (pp["c"][0] + 2, pp["c"][1]), 1.0)

    for i, (k, place) in enumerate(L.AS5600_PLACE.items()):
        add(fp_as5600(board), f"U{2 + i}", f"AS5600 hand {k}", place["c"], place["rot"],
            {"1": "3V3_SW", "3": "GND", "6": AS5600_NETS[k], "7": "GND", "8": "GND"})
    add(fp_drv8833(board), "U5", "DRV8833", L.DRV8833_PLACE["c"], L.DRV8833_PLACE["rot"],
        {"1": "VBAT", "2": "GND", "3": "FLT", "4": "BIN1", "5": "BIN2", "6": "3V3_SW", "7": "AIN2", "8": "AIN1",
         "9": "AOUT1", "10": "AOUT2", "11": "BOUT2", "12": "BOUT1", "13": "GND", "14": "GND"})
    add(fp_max98357(board), "U6", "MAX98357A", L.MAX98357_PLACE["c"], L.MAX98357_PLACE["rot"],
        {"1": "VBAT", "2": "GND", "3": "AMP_SD", "5": "DOUT", "6": "BCLK", "7": "WS", "8": "SPK-", "9": "SPK+"})
    add(fp_usbc(board), "U7", "USB-C wall port", L.USBC_PLACE["c"], L.USBC_PLACE["rot"],
        {"1": "GND", "2": "USB_VBUS", "5": "USB_D-", "6": "USB_D+"})
    # crown switch: actuator tip (KiCad-local 2.25, -6.4) on the crown axis, pointing out of the corner
    sw = add(fp_std("Button_Switch_THT", "SW_SPST_Omron_B3F-315x_Angled"), "SW1", "B3F-3150 crown",
             (0, 0), 0.0, {"1": "CROWN", "2": "GND"})
    d = L.CROWN_FACE_D - L.CROWN_TIP_GAP
    ca = math.radians(L.CROWN_ANGLE)
    place_by_feature(sw, (2.25, -6.4), (0.0, -1.0), (d * math.cos(ca), d * math.sin(ca)),
                     (math.cos(ca), math.sin(ca)))
    sw.Reference().SetVisible(False)
    sw.Value().SetVisible(False)
    text("CROWN", L.polar(d - 13.0, L.CROWN_ANGLE), 0.9, angle=-45)
    add(fp_x27(board), "M1", "X27.168", L.X27_CENTER, 0.0,
        {"1": "AOUT1", "2": "AOUT2", "3": "BOUT1", "4": "BOUT2"})
    bx0, by0, bx1, by1 = L.BATTERY_BOX
    text("BATTERY (tape here)", ((bx0 + bx1) / 2, (by0 + by1) / 2), 1.0, angle=90)

    # ---- passives ----
    for ref, (val, na, nb, x, y, rot) in RESISTORS.items():
        fp = add(fp_std("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"), ref, val,
                 (x, y), rot, {"1": na, "2": nb})
        fp.Value().SetVisible(False)
        fp.Reference().SetVisible(False)
        text(val, (x, y + 1.9 if y > 5 else y - 12.0), 0.8)
    ref, val, na, nb, xy, rot = CAP
    add(fp_std("Capacitor_THT", "CP_Radial_D6.3mm_P2.50mm"), ref, val, xy, rot, {"1": na, "2": nb})

    # ---- wire pads / headers ----
    for ref, (title, x, y, dx, dy, pins) in HEADERS.items():
        n = len(pins)
        fp = fp_std("Connector_PinHeader_2.54mm", f"PinHeader_1x{n:02d}_P2.54mm_Vertical")
        add(fp, ref, title, (x, y), 0.0 if dy < 0 else 90.0, {str(i + 1): pins[i][0] for i in range(n)})
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        for i, (_, lab) in enumerate(pins):
            px, py = x + i * dx, y + i * dy
            pos = (px, py + 1.9) if dy == 0 else (px + 1.8, py)
            for layer in (pcbnew.F_SilkS, pcbnew.B_SilkS):
                t = text(lab, pos, 0.8, layer)
                if dy != 0:
                    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_RIGHT if layer == pcbnew.B_SilkS
                                      else pcbnew.GR_TEXT_H_ALIGN_LEFT)
        tpos = (x + (n - 1) * dx / 2, y - 2.0) if dy == 0 else (x, y + 2.3)
        if ref == "J7":                               # top-left corner: title below, clear of the post
            tpos = (x + 7.0, y + (n - 1) * dy - 2.4)
        text(f"{ref} {title}", tpos, 0.85)

    # ---- test pads ----
    per_row = (len(TEST_PADS) + 1) // 2
    for i, n in enumerate(TEST_PADS):
        x = TP_X0 + (i % per_row) * TP_PITCH
        y = TP_ROW_Y[i // per_row]
        fp = add(fp_std("TestPoint", "TestPoint_THTPad_D1.5mm_Drill0.7mm"), f"TP{i + 1}", n, (x, y), 0.0, {"1": n})
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        up = i < per_row                  # row 1 labels read upward, row 2 downward
        t = _text(board, n, P(x, y + (1.6 if up else -1.6)), 0.8, pcbnew.F_SilkS, 90)
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT if up else pcbnew.GR_TEXT_H_ALIGN_RIGHT)
        board.Add(t)
    text("TEST PADS  -  ALETHIOMETER CARRIER rev A", (TP_X0 + (per_row - 1) * TP_PITCH / 2, -51.6), 0.8)

    # ---- corner posts: NPTH + copper keep-out (brass standoffs must not touch copper) ----
    for i, (x, y) in enumerate(L.BAY_POSTS):
        fp = add(fp_std("MountingHole", "MountingHole_2.7mm_M2.5"), f"H{i + 1}", "M2 post", (x, y))
        fp.Reference().SetVisible(False)
        ra = pcbnew.ZONE(board)
        ra.SetIsRuleArea(True)
        ra.SetDoNotAllowTracks(True)
        ra.SetDoNotAllowVias(True)
        ra.SetDoNotAllowZoneFills(True)
        ra.SetDoNotAllowPads(False)
        ra.SetLayerSet(pcbnew.LSET.AllCuMask())
        poly = ra.Outline()
        poly.NewOutline()
        for k in range(16):
            a = 2 * math.pi * k / 16
            v = P(x + 3.4 * math.cos(a), y + 3.4 * math.sin(a))
            poly.Append(v.x, v.y)
        board.Add(ra)

    # ---- title (bottom side, centre) ----
    for s, y, size in (("ALETHIOMETER CARRIER  rev A", -20.0, 1.3), ("github.com/Kixantrix/alethiometer", -22.4, 0.9),
                       ("solder side faces the case floor:", -25.4, 0.8),
                       ("Kapton on the floor + 2.5 mm nylon spacers", -27.0, 0.8)):
        text(s, (-25.0, y), size, pcbnew.B_SilkS)

    # ---- ground pours (both layers) ----
    wi, ci = L.octagon_inset(L.CASE_W, L.CASE_CHAMFER, L.T040 + L.CARRIER_CLEAR + 0.6)
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(net("GND"))
        z.SetLocalClearance(mm(0.3))
        z.SetMinThickness(mm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(mm(0.4))
        z.SetThermalReliefSpokeWidth(mm(0.45))
        poly = z.Outline()
        poly.NewOutline()
        for x, y in L.octagon_pts(wi, ci):
            v = P(x, y)
            poly.Append(v.x, v.y)
        board.Add(z)
    return board


# =============================================================================
# Pipeline
# =============================================================================
def run(cmd, timeout=600, cwd=None):
    print("  $", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], check=False, capture_output=True, text=True,
                          timeout=timeout, encoding="utf-8", errors="replace", cwd=cwd)


def fill_zones(board):
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def autoroute(board, freerouting: Path | None) -> bool:
    if not freerouting or not Path(freerouting).exists():
        print("  Freerouting not found; board left unrouted (ratsnest only)")
        return False
    dsn, ses = HERE / "_route.dsn", HERE / "_route.ses"
    # Route GND as an ordinary net (Freerouting skips plane nets), so no pad depends on the pour
    # and copy footprint keep-outs (the ProS3 antenna area) to the board, because the DSN export skips them.
    zones = [z for z in board.Zones() if not z.GetIsRuleArea()]
    for z in zones:
        board.Remove(z)
    temp = []
    for fp in board.GetFootprints():
        for z in fp.Zones():
            if z.GetIsRuleArea() and z.GetDoNotAllowTracks():
                k = pcbnew.ZONE(board)
                k.SetIsRuleArea(True)
                k.SetDoNotAllowTracks(True)
                k.SetDoNotAllowVias(True)
                k.SetLayerSet(z.GetLayerSet())
                k.SetOutline(pcbnew.SHAPE_POLY_SET(z.Outline()))
                board.Add(k)
                temp.append(k)
    # Freerouting ignores the copper-to-edge rule: fence the outline with a 0.7 mm keep-out band.
    w, c = L.octagon_inset(L.CASE_W, L.CASE_CHAMFER, L.T040 + L.CARRIER_CLEAR)
    pts = L.octagon_pts(w, c)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        dx, dy = x1 - x0, y1 - y0
        n = math.hypot(dx, dy)
        nx, ny = -dy / n * 0.7, dx / n * 0.7          # inward normal (outline is CCW)
        k = pcbnew.ZONE(board)
        k.SetIsRuleArea(True)
        k.SetDoNotAllowTracks(True)
        k.SetDoNotAllowVias(True)
        k.SetLayerSet(pcbnew.LSET.AllCuMask())
        poly = k.Outline()
        poly.NewOutline()
        for x, y in ((x0 - nx, y0 - ny), (x1 - nx, y1 - ny), (x1 + nx, y1 + ny), (x0 + nx, y0 + ny)):
            v = P(x, y)
            poly.Append(v.x, v.y)
        board.Add(k)
        temp.append(k)
    pcbnew.ExportSpecctraDSN(board, str(dsn))
    for k in temp:
        board.Remove(k)
    for z in zones:
        board.Add(z)
    # Freerouting 1.9 jar (java 17+); the 2.x native CLI crashes on Windows with a GraalVM serialization error
    exe = ["java", "-jar", freerouting] if str(freerouting).endswith(".jar") else [freerouting]
    r = run(exe + ["-de", dsn, "-do", ses, "-mp", 40], timeout=3600, cwd=HERE)   # it writes logs/ in cwd
    tail = (r.stdout + r.stderr).strip().splitlines()[-4:]
    print("   ", "\n    ".join(tail))
    if not ses.exists():
        print("  Freerouting produced no session file")
        return False
    ok = pcbnew.ImportSpecctraSES(board, str(ses))
    for f in (dsn, ses):
        f.unlink(missing_ok=True)
    return ok


def drc() -> dict:
    report = HERE / "drc_report.json"
    run([KICAD_CLI, "pcb", "drc", "--format", "json", "--severity-all", "--output", report, BOARD_FILE])
    data = json.loads(report.read_text(encoding="utf-8"))
    by_type: dict[str, int] = {}
    for v in data.get("violations", []):
        key = f"{v['severity']}:{v['type']}"
        by_type[key] = by_type.get(key, 0) + 1
    return {"violations": len(data.get("violations", [])),
            "unconnected": len(data.get("unconnected_items", [])), "by_type": by_type}


def export_fab():
    if FAB.exists():
        shutil.rmtree(FAB)
    gerb = FAB / "gerbers"
    gerb.mkdir(parents=True)
    layers = "F.Cu,B.Cu,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"
    run([KICAD_CLI, "pcb", "export", "gerbers", "--layers", layers, "--output", str(gerb) + os.sep, BOARD_FILE])
    run([KICAD_CLI, "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th",
         "--output", str(gerb) + os.sep, BOARD_FILE])
    with zipfile.ZipFile(FAB / "alethiometer_carrier_gerbers.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(gerb.iterdir()):
            z.write(f, f.name)
    run([KICAD_CLI, "pcb", "export", "pdf", "--layers", "F.Cu,F.Silkscreen,Edge.Cuts", "--mode-single",
         "--output", FAB / "plot_top.pdf", BOARD_FILE])
    run([KICAD_CLI, "pcb", "export", "pdf", "--layers", "B.Cu,B.Silkscreen,Edge.Cuts", "--mirror",
         "--mode-single", "--output", FAB / "plot_bottom.pdf", BOARD_FILE])
    for side in ("top", "bottom"):
        run([KICAD_CLI, "pcb", "render", "--side", side, "--width", "1600", "--height", "1600",
             "--quality", "basic", "--output", FAB / f"render_{side}.png", BOARD_FILE], timeout=900)


def write_netlist(board):
    rows: dict[str, list[str]] = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            n = pad.GetNetname()
            if n:
                rows.setdefault(n, []).append(f"{fp.GetReference()}.{pad.GetNumber()}")
    lines = ["# Carrier PCB netlist", "", "Generated by `make_pcb.py`. `U1` = ProS3 (pin numbers per "
             "Unexpected Maker's symbol), `U2-U4` = AS5600 I-III, `U5` = DRV8833, `U6` = MAX98357A, "
             "`M1` = X27.168.", "", "| Net | Pads |", "|---|---|"]
    for n in sorted(rows):
        lines.append(f"| `{n}` | {', '.join(sorted(rows[n]))} |")
    (HERE / "NETLIST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_library():
    """Write the custom footprints to alethiometer.pretty and register it for the project."""
    scratch = pcbnew.BOARD()
    for maker, name in ((fp_as5600, "Adafruit_AS5600_6357"), (fp_drv8833, "Adafruit_DRV8833_3297"),
                        (fp_max98357, "Adafruit_MAX98357A_3006"), (fp_x27, "X27_168_socketed"),
                        (fp_usbc, "Adafruit_USB_C_4090")):
        fp = maker(scratch)
        fp.SetReference("REF**")
        pcbnew.FootprintSave(str(LOCAL_LIB), fp)
    (HERE / "fp-lib-table").write_text(
        '(fp_lib_table\n  (version 7)\n  (lib (name "alethiometer")(type "KiCad")'
        '(uri "${KIPRJMOD}/alethiometer.pretty")(options "")(descr "Alethiometer carrier footprints"))\n)\n',
        encoding="utf-8")


def write_rules():
    """Project rules: through-hole GND pads may tie into the pour with a single thermal spoke."""
    pro = HERE / "alethiometer_carrier.kicad_pro"      # the rules file is only read inside a project
    if not pro.exists():
        pro.write_text("{}\n", encoding="utf-8")
    (HERE / "alethiometer_carrier.kicad_dru").write_text(
        '(version 1)\n(rule "single spoke ok"\n  (constraint min_resolved_spokes 1))\n', encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freerouting", type=Path, default=os.environ.get("FREEROUTING"),
                    help="path to freerouting-1.9.0.jar (or set FREEROUTING)")
    ap.add_argument("--no-route", action="store_true")
    ap.add_argument("--no-export", action="store_true")
    args = ap.parse_args()

    save_library()
    write_rules()
    board = build()
    if not args.no_route and autoroute(board, args.freerouting):
        print("  routed")
    fill_zones(board)
    pcbnew.SaveBoard(str(BOARD_FILE), board)
    write_netlist(board)
    summary = drc()
    print("DRC:", json.dumps(summary, indent=1))
    if not args.no_export:
        export_fab()
    (HERE / "build_report.json").write_text(json.dumps({"drc": summary}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
