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
MODULE = 0.7
Z_HAND, Z_SENSOR, Z_KNOB = 36, 36, 31
Z_NEEDLE, Z_MOTOR = 19, 38


def center_distance(z1: int, z2: int) -> float:
    return MODULE * (z1 + z2) / 2


R_SENSOR = center_distance(Z_HAND, Z_SENSOR)                 # 25.2
R_KNOB = R_SENSOR + center_distance(Z_SENSOR, Z_KNOB)        # 48.65
TRAIN_ANGLES = {"I": 90.0, "II": 180.0, "III": 270.0}        # knob directions (12, 9, 6 o'clock)
SENSORS = {k: polar(R_SENSOR, a) for k, a in TRAIN_ANGLES.items()}

# Juken X27.168: Ø30.4 body; output shaft 10.0 mm from the body centre (datasheet);
# four rear pins at ±11.43 across and ±3.81 along the shaft axis (two per coil,
# same side = same coil); rear bushing boss on the shaft axis and a rear peg.
X27_SHAFT = (center_distance(Z_NEEDLE, Z_MOTOR), 0.0)       # (19.95, 0)
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

# ---- carrier PCB modules (plan centre, rotation deg CCW in the CAD frame) -----
# Footprint frames: see hardware/pcb/make_pcb.py. Rotation 0 means the module's
# header row lies along +x, below the module centre (toward -y).
# Every module plugs into female sockets so it can be pulled for reflashing or
# replacement: its own male headers (plastic under the module) sit on 5 mm
# "short" female headers (Adafruit #3008) soldered to the carrier.
SOCKET_H = 5.0                     # Adafruit #3008 short female header body
HEADER_PLASTIC_H = 2.54            # standard male header spacer
MODULE_LIFT = SOCKET_H + HEADER_PLASTIC_H        # module PCB underside above the carrier
X27_SOCKET_H = 8.5                 # X27 rear pins plug into two standard 1x4 female headers
ADAFRUIT_AS5600 = dict(w=25.4, h=17.78, header_dy=-6.35, chip=(0.0, 0.0),
                       rest=((-1.27, 6.35), (1.27, 6.35)))   # far-edge rest post (2-pin socket + header)
AS5600_PLACE = {          # header row toward the dial centre
    "I": dict(c=SENSORS["I"], rot=0.0),
    "II": dict(c=SENSORS["II"], rot=90.0),
    "III": dict(c=SENSORS["III"], rot=180.0),
}
PROS3_PLACE = dict(c=(0.0, 43.4), rot=-90.0)     # USB-C end toward +x (FPC extension to the wall)
DRV8833_PLACE = dict(c=(28.0, -31.0), rot=0.0)
MAX98357_PLACE = dict(c=(-32.0, 24.5), rot=0.0)
BATTERY_BOX = (-37.0, -48.0, -13.2, -13.2)       # x0, y0, x1, y1 (sits on the carrier)

# Carrier board outline: inside the lower tray with 0.6 mm clearance
CARRIER_CLEAR = 0.6
