"""Shared plan-view layout: one source of truth for the CAD model (design.py)
and the carrier PCB generator (hardware/pcb/make_pcb.py, run under KiCad's
Python). Pure Python, no dependencies.

Coordinates are millimetres in the CAD frame: origin at the dial centre,
+x toward the hinge, +y toward 12 o'clock (y up). The PCB generator flips y.
"""
from __future__ import annotations

import math

IN = 25.4
T040 = 0.040 * IN

# ---- case outline (outer mould line of the lower tray) ---------------------
CASE_W = 110.0
CASE_CHAMFER = 16.0


def octagon_pts(width: float, chamfer: float) -> list[tuple[float, float]]:
    """Square of `width` across flats with 45° corner chamfers; CCW, starts on the right side."""
    h, c = width / 2, chamfer
    return [(h, -(h - c)), (h, h - c), (h - c, h), (-(h - c), h),
            (-h, h - c), (-h, -(h - c)), (-(h - c), -h), (h - c, -h)]


def octagon_inset(width: float, chamfer: float, d: float) -> tuple[float, float]:
    """(width, chamfer) of the same octagon offset inward by d (mitred)."""
    return width - 2 * d, chamfer - d * (2 - math.sqrt(2))


def polar(r: float, deg: float) -> tuple[float, float]:
    a = math.radians(deg)
    return r * math.cos(a), r * math.sin(a)


# ---- gear train --------------------------------------------------------------
# Module 0.8 is a stock size: the thumbwheels are bought gears; the thin gears are laser-cut.
MODULE = 0.8
Z_HAND, Z_SENSOR, Z_KNOB = 32, 32, 26
Z_NEEDLE, Z_MOTOR = 17, 34


CENTER_SLOP = 0.10   # every gear pair is spaced this much wider than theoretical: room for laser
                     # tooth error and bearing play without binding (just adds a little backlash)


def center_distance(z1: int, z2: int) -> float:
    return MODULE * (z1 + z2) / 2 + CENTER_SLOP


R_SENSOR = center_distance(Z_HAND, Z_SENSOR)                 # 25.7
R_KNOB = R_SENSOR + center_distance(Z_SENSOR, Z_KNOB)        # 49.0
TRAIN_ANGLES = {"I": 90.0, "II": 180.0, "III": 270.0}        # knob directions (12, 9, 6 o'clock)
SENSORS = {k: polar(R_SENSOR, a) for k, a in TRAIN_ANGLES.items()}

# Juken X27.168: Ø30.4 body; output shaft 10.0 mm from the body centre (datasheet);
# four rear pins at ±11.43 across and ±3.81 along the shaft axis (two per coil,
# same side = same coil); rear bushing boss on the shaft axis and a rear peg.
X27_SHAFT = (center_distance(Z_NEEDLE, Z_MOTOR), 0.0)       # (20.5, 0); slot-adjustable
X27_SHAFT_OFFSET = 10.0
X27_CENTER = (X27_SHAFT[0] + X27_SHAFT_OFFSET, 0.0)
X27_BODY_D = 30.4
X27_PINS = {   # coil A on the +y side, coil B on the -y side (CAD frame)
    "A1": (X27_CENTER[0] - 3.81, 11.43), "A2": (X27_CENTER[0] + 3.81, 11.43),
    "B1": (X27_CENTER[0] - 3.81, -11.43), "B2": (X27_CENTER[0] + 3.81, -11.43),
}

# ---- corner posts (screws through every level) -------------------------------
POST_R = 57.0
POSTS = [polar(POST_R, a) for a in (45, 135, 225, 315)]
# The top-right corner has no bay post (floor -> carrier -> P1): the crown switch sits there.
# Its P1 -> top-face posts remain (an M2 nut under P1 takes the gear standoff's thread).
BAY_POSTS = POSTS[1:]

# ---- carrier PCB modules (plan centre, rotation deg CCW in the CAD frame) -----
# Footprint frames: see hardware/pcb/make_pcb.py. Rotation 0 means the module's
# header row lies along +x, below the module centre (toward -y).
# Every module plugs into female sockets so it can be pulled for reflashing or
# replacement. The sockets are 5 mm "short" female headers (Adafruit #3008).
# Each module's male header is soldered with its black plastic spacer on TOP
# (long pins down through the module, ~4.4 mm below it), then the spacer is
# slid off and the stubs clipped, so the module rests directly on its sockets.
SOCKET_H = 5.0                     # Adafruit #3008 short female header body
MODULE_LIFT = SOCKET_H             # module PCB underside above the carrier
X27_SOCKET_H = SOCKET_H            # X27 rear pins (4.4 mm) in two 1x4 cuts of the same header
ADAFRUIT_AS5600 = dict(w=25.4, h=17.78, header_dy=-6.35, chip=(0.0, 0.0),
                       rest=((-1.27, 6.35), (1.27, 6.35)))   # far-edge rest: a bare 1x2 socket
AS5600_PLACE = {          # header row toward the dial centre
    "I": dict(c=SENSORS["I"], rot=0.0),
    "II": dict(c=SENSORS["II"], rot=90.0),
    "III": dict(c=SENSORS["III"], rot=180.0),
}
PROS3_PLACE = dict(c=(4.0, 43.7), rot=90.0)      # USB-C end toward -x: short cable to J7
DRV8833_PLACE = dict(c=(28.0, -31.0), rot=0.0)
MAX98357_PLACE = dict(c=(-32.0, 24.5), rot=0.0)
BATTERY_BOX = (-37.0, -48.0, -13.2, -13.2)       # x0, y0, x1, y1 (sits on the carrier)

# Wall USB-C: Adafruit #4090 USB-C breakout (0.1" header + two M2 holes beside the receptacle),
# on a 1x8 socket and two 5 mm spacers, receptacle facing the right wall. Frame as the other
# modules: header row toward -y, receptacle mouth at +y.
ADAFRUIT_USBC = dict(w=20.32, h=13.97, header_dy=-4.445, holes=((-7.62, 4.445), (7.62, 4.445)))
USBC_WALL_GAP = 0.75                                   # board front edge to the inner wall
USBC_PLACE = dict(c=(CASE_W / 2 - T040 - USBC_WALL_GAP - ADAFRUIT_USBC["h"] / 2, 23.5), rot=-90.0)

# Crown: centred on the top-right chamfer of the lower tray, pressing a right-angle
# Omron B3F-3150 tactile switch soldered to the carrier.
CROWN_ANGLE = 45.0
CROWN_FACE_D = (CASE_W / 2 - CASE_CHAMFER / 2) * math.sqrt(2)   # outer chamfer face from the centre
CROWN_TIP_GAP = 3.2                                    # actuator tip inside the outer face
CROWN_SW_ACT_H = 3.75                                  # actuator centre above the carrier top
CROWN_SW_ACT_LEN = 4.03                                # actuator beyond the switch body
CROWN_SW_BODY = (7.3, 6.25, 7.4)                       # width, depth, height (B3F-3150)

# Carrier board outline: inside the lower tray with 1.0 mm clearance
CARRIER_CLEAR = 1.0
