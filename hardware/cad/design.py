"""The brass alethiometer: every part, its material and its place.

Coordinates (mm): origin at the dial centre on the outside of the case floor.
+x points to the hinge, +y to 12 o'clock (the "Hourglass"), +z up out of the
dial. Hand/dial angles use clock convention (0° at 12, clockwise).

Run build.py to export DXF/STEP/renders and to run the interference check.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import cadquery as cq
from shapely import affinity
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

import layout as L
from gears import center_distance, gear_polygon, pitch_radius
from geom import (Profile, annulus, circle, clock, octagon, offset, polar, profile_solid,
                  rect, slot)
from sheetmetal import Tray, WallCut

IN = 25.4

# ---------------------------------------------------------------------------
# Materials (SendCutSend stock) and bend spec for .040" brass
# ---------------------------------------------------------------------------
T040 = 0.040 * IN            # 1.016  brass 260
T063 = 0.063 * IN            # 1.600  brass 260 / clear acrylic
T032 = 0.032 * IN            # 0.813  copper 110
BEND_IR = 0.040 * IN         # SendCutSend inside radius, brass .040
K_FACTOR = 0.38
MIN_FLANGE = 0.292 * IN
DENSITY = {"brass": 8.53e-3, "copper": 8.94e-3, "acrylic": 1.19e-3, "steel": 7.9e-3, "fr4": 1.85e-3}  # g/mm³

# ---------------------------------------------------------------------------
# Case outline
# ---------------------------------------------------------------------------
CASE_W = L.CASE_W
CASE_CHAMFER = L.CASE_CHAMFER
# ---- Tolerance budget --------------------------------------------------------
# SendCutSend holds about ±0.13 mm on laser-cut features and ±0.25-0.5 mm on bends.
# Every fit below is sized so worst-case parts still go together without filing.
SEAM_GAP = 0.45                       # radial gap where upper shell telescopes over lower tray
PLATE_CLEAR = 1.0                     # internal plates to case wall
KNOB_NOTCH_SIDE = 1.2                 # thumbwheel to wall-notch edge, each side
KNOB_NOTCH_BELOW, KNOB_NOTCH_ABOVE = 1.0, 1.5   # notch beyond the wheel stack, below / above
POST_HOLE = 2.7                       # M2 clearance in case, spiders and PCB (heads/standoffs cover it)
POST_HOLE_PLATE = 2.5                 # M2 standoff thread through P1/P2
CASE_SCREW_D, CASE_SCREW_HEAD_D = 2.0, 3.8   # DIN 963 slotted, 90-degree countersunk
FLOOR_SCREW_LEN, TOP_SCREW_LEN = 8.0, 6.0    # countersunk lengths include the head
CRYSTAL_CLEAR = 0.4                   # radial, crystal in its frame pocket
GEAR_BACKLASH = 0.12                  # tooth thinning per gear (plus layout.CENTER_SLOP)
LOWER_OUTER = octagon(CASE_W, CASE_CHAMFER)
LOWER_INNER = offset(LOWER_OUTER, -T040)
UPPER_OUTER = offset(LOWER_OUTER, SEAM_GAP + T040)
UPPER_INNER = offset(UPPER_OUTER, -T040)

# ---------------------------------------------------------------------------
# Vertical stack (absolute z)
# ---------------------------------------------------------------------------
# floor -> 2.5 mm nylon spacers -> carrier PCB -> M2x12 F-F standoffs -> P1 (movement)
# The bay height is set by the AS5600 chain: socket (L.MODULE_LIFT) + module + chip
# + air gap + sensor magnet + magnet drop below P1.
CARRIER_SPACER, CARRIER_T, CARRIER_STANDOFF = 2.5, 1.6, 12.0
GEAR_STANDOFF, HAND_STANDOFF = 8.0, 6.0    # M2 hex standoff lengths
Z_FLOOR_TOP = T040
Z_CARRIER = Z_FLOOR_TOP + CARRIER_SPACER   # carrier PCB (bottom face)
Z_CARRIER_TOP = Z_CARRIER + CARRIER_T
Z_P1 = Z_CARRIER_TOP + CARRIER_STANDOFF    # movement base plate (bottom face)
Z_P1_TOP = Z_P1 + T063
Z_P2 = Z_P1_TOP + GEAR_STANDOFF            # dial plate
Z_P2_TOP = Z_P2 + T063
Z_SEAT = Z_P2_TOP + HAND_STANDOFF          # crystal seat spider
Z_FRAME = Z_SEAT + T040                    # crystal frame spider / crystal bottom
Z_TOPFACE = Z_FRAME + T063                 # inside of the case top
Z_TOP = Z_TOPFACE + T040                   # outside of the case top
GEAR_PITCH_Z = 2.0
LEVELS = [Z_P1_TOP + 0.5 + i * GEAR_PITCH_Z for i in range(4)]   # L0..L3 gear bottoms
LOWER_H = LEVELS[0] + 2.5                  # lower tray wall height (seam crosses the thumbwheels)
Z_UPPER_BOTTOM = LOWER_H - 2.0             # upper shell skirt bottom (2 mm overlap)
UPPER_H = Z_TOP - Z_UPPER_BOTTOM
LID_H = 0.300 * IN                         # lid flange (>= SCS min flange .292")
STICKER_T = 0.15
CRYSTAL_T = T063

# ---------------------------------------------------------------------------
# Gear train (module 0.8, 20° PA): thin gears laser-cut in .040 brass, thumbwheels bought.
# Shared with the PCB via layout.py
# ---------------------------------------------------------------------------
MODULE = L.MODULE
Z_HAND, Z_SENSOR, Z_KNOB = L.Z_HAND, L.Z_SENSOR, L.Z_KNOB
Z_NEEDLE, Z_MOTOR = L.Z_NEEDLE, L.Z_MOTOR
R_SENSOR = L.R_SENSOR                      # 25.2
R_KNOB = L.R_KNOB                          # 48.65
# Thumbwheel: one stock gear, thick enough to grip and to span the three sensor-gear levels.
# Misumi configurable spur gear, module 0.8, brass, shape A (no hub), 26 teeth, 5 mm face, 4 mm bore.
KNOB_FACE, KNOB_BORE = 5.0, 4.0
KNOB_GEAR_SPEC = ("Misumi spur gear, module 0.8, 20° PA, brass, shape A (no hub), 26 teeth, "
                  "face width 5 mm, round bore 4 mm H7; Loctite 638 on the 5/32\" shaft")
X27_SHAFT = L.X27_SHAFT                    # 19.95, 0
X27_BODY_D, X27_BODY_H, X27_SHAFT_OFFSET = L.X27_BODY_D, 9.6, L.X27_SHAFT_OFFSET
X27_CENTER = L.X27_CENTER
X27_BODY_BOTTOM = Z_CARRIER_TOP + L.X27_SOCKET_H   # rear pins (4.4 mm) plug into 5 mm sockets
X27_BODY_TOP = X27_BODY_BOTTOM + X27_BODY_H  # motor gear rides on the Ø1 shaft above the collar
SENSOR_MAGNET_H = 2.5                      # Ø6×2.5 diametric (the usual AS5600 magnet)
SENSOR_MAGNET_DROP = 0.3                   # sensor shaft pokes below P1 so the magnet can't rub the plate

# K&S Precision Metals telescoping brass (0.014" wall); ID = OD - 0.028"
def ks_od(frac: str) -> float:
    a, b = frac.split("/")
    return int(a) / int(b) * IN


KS_WALL = 0.014 * IN
ROD_332, ROD_18, ROD_532 = ks_od("3/32"), ks_od("1/8"), ks_od("5/32")
TUBE_18, TUBE_532, TUBE_316, TUBE_732 = ks_od("1/8"), ks_od("5/32"), ks_od("3/16"), ks_od("7/32")
FIT = 0.15                                # hands, crown etc.: bonded bores that slide on even when cut -0.13
GEAR_FIT = 0.08                           # gear bores: kept close so each gear runs centred on its arbor
BUSH_FIT = 0.10                           # plate holes for the K&S tube bushings (Loctite 638 fills the gap)
# Shafts don't run in the laser-cut holes: each plate hole carries a 1.6 mm K&S tube bushing, and
# K&S telescoping sizes slide on each other with ~0.08 mm play. That locates every gear precisely
# without reaming, whatever the laser tolerance.

# The three framing hands. Knobs at 12 (top), 9 (left), 6 (bottom) o'clock.
TRAINS = [
    dict(name="I", angle=90.0, level=0, arbor=ROD_332, arbor_name="3/32 rod", length=30.6, width=3.0),
    dict(name="II", angle=180.0, level=1, arbor=TUBE_18, arbor_name="1/8 tube", length=33.0, width=3.2),
    dict(name="III", angle=270.0, level=2, arbor=TUBE_532, arbor_name="5/32 tube", length=35.4, width=3.4),
]
NEEDLE_LEN, NEEDLE_TAIL = 39.6, 9.5

# ---------------------------------------------------------------------------
# Dial and top face
# ---------------------------------------------------------------------------
DIAL_R_IN, DIAL_R_OUT = 29.0, 41.4         # sticker (see hardware/dial)
SKELETON_R = 28.4
CRYSTAL_R = 44.0
WINDOW_R = 42.0
SEAT_R_IN, SPIDER_R_OUT = 41.5, 46.6
SLOT_R0, SLOT_R1, SLOT_N, SLOT_W = 47.6, 51.4, 90, 1.1
POST_R = L.POST_R
POSTS = L.POSTS

# Electronics placements
SPEAKER = dict(c=(-28.5, 28.5), d=28.0, h=5.0)
MIC = dict(c=(-32.0, -32.0), d=14.0, h=3.0)
# Speaker and mic leads run down to their carrier pads (J5, J4; positions from pcb/make_pcb.py)
SPK_WIRE_HOLE = (-18.5, 29.75)             # Ø3.5 in P1's speaker seat, right above J5
SPK_WIRE_D, MIC_WIRE_D = 1.6, 2.4          # bundle envelopes: 2 and 5 × 30 AWG silicone
J4_PAD_MID, J5_PAD_MID = (-46.0, -22.08), (-18.5, 29.73)
REED = dict(c=polar(53.6, 300.0), angle=300.0 + 90.0, len=14.0, d=2.2)
LID_MAGNET_L = polar(54.0, 157.5)          # closure pair, between grille ring and wall
MAGNET_D, MAGNET_H = 5.0, 4.0
USB_BOARD_Z = Z_CARRIER_TOP + L.MODULE_LIFT               # Adafruit #4090 underside (on its socket)
USB = dict(y=L.USBC_PLACE["c"][1], z=USB_BOARD_Z + 1.6 + 1.63)   # receptacle centre, right wall
CROWN_Z = Z_CARRIER_TOP + L.CROWN_SW_ACT_H                # crown axis = switch actuator height
# Guden BR05050404-72: .040 sheet, .091 pin, .500 knuckle pitch.
# Curl clearance and slot width are illustrative, not manufacturer dimensions.
HINGE_KNUCKLES, KNUCKLE_GAP = 5, 0.1
KNUCKLE_LEN = 0.5 * IN - KNUCKLE_GAP
HINGE_PIN_D = 0.091 * IN
HINGE_BARREL_D = HINGE_PIN_D + 0.1 + 2 * T040
HINGE_BODY_DEPTH = 1.060 / 2 * IN               # fixed leaf left at full width (pivot to edge)
HINGE_LID_HEIGHT = LID_H - BEND_IR - T040       # lid leaf trimmed to the lid wall's flat (~5.6 mm)
HINGE_BODY_MOUNTS = (-25.4, -9.5, 9.5, 25.4)   # along the hinge; M2 countersunk from outside, nuts inside
HINGE_BODY_MOUNT_Z = -8.0                      # below the pivot
HINGE_LID_MOUNTS = (-12.7, 12.7)
HINGE_LID_MOUNT_Z = 3.6
HINGE_NUT_H, HINGE_BODY_SCREW_LEN, HINGE_LID_SCREW_HEAD_D = 1.6, 6.0, 3.2
HINGE_LID_SCREW_LEN, HINGE_LID_NUT_H = 4.0, 1.3
HINGE_LID_WASHER_D, HINGE_LID_WASHER_T = 4.0, 0.3          # DIN 125 M1.6 washer under each lid nut
GUIDE_PAD, GUIDE_HALF_LEN, GUIDE_LIP = 3.0, 37.0, 8.0      # drill guide: margin, half length, lid lip
HINGE_MOUNT_CLEAR = 2.4
HINGE_LID_CLEAR = 1.8
HINGE_REFERENCE_NOTE = (
    "Purchased hinge reference only: confirm curl/leaf offset, knuckle slots and travel "
    "on the actual Guden hinge and update the CAD pivot, mounts and stop before drilling or ordering."
)
# No separate stop: the lid opens flat (180°) and a little past, until the hinge's own leaves
# close onto each other. The leaves are tangent to the barrel on the wall side, so their
# outer faces are (barrel radius - leaf thickness) either side of the pivot when folded.
LID_REST_ANGLE = 180.0                     # "open" pose for renders, GLB and the viewer
_LEAF_OFFSET = HINGE_BARREL_D / 2 - T040
LID_OPEN_ANGLE = 180.0 + 2 * math.degrees(math.atan(_LEAF_OFFSET / HINGE_LID_HEIGHT))   # ~201°


@dataclass
class Part:
    name: str
    kind: str                       # "scs" (laser cut), "scs-bent", "stock" (K&S), "bought"
    material: str
    solid: cq.Shape                 # in its own local frame
    placements: list = field(default_factory=lambda: [cq.Location()])
    color: tuple = (0.80, 0.62, 0.30)
    group: str = "case"
    profile: Profile | None = None  # flat pattern for laser cutting
    bends: list = field(default_factory=list)
    spec: str = ""                  # stock/thickness description for BOM
    qty_extra: int = 0              # spares to order
    density: str = "brass"
    allow: tuple = ()               # names of parts this may legitimately touch/overlap
    tray: Tray | None = None

    @property
    def qty(self) -> int:
        return len(self.placements)

    def placed(self) -> list[cq.Shape]:
        return [self.solid.moved(loc) for loc in self.placements]


BRASS = (0.83, 0.65, 0.32)
BRASS_DARK = (0.62, 0.46, 0.20)
COPPER = (0.78, 0.42, 0.26)
BLUED = (0.16, 0.20, 0.32)
STEEL = (0.62, 0.63, 0.66)
PCB = (0.10, 0.35, 0.18)
BLACK = (0.08, 0.08, 0.09)
IVORY = (0.93, 0.89, 0.78)
GLASS = (0.80, 0.90, 0.95)


def loc(x=0.0, y=0.0, z=0.0, rz=0.0) -> cq.Location:
    return cq.Location(cq.Vector(x, y, z), cq.Vector(0, 0, 1), rz)


def flipped(z_top: float) -> cq.Location:
    """Local tray (floor at z=0, walls up) turned over so its floor is the top at z_top."""
    return cq.Location(cq.Vector(0, 0, z_top), cq.Vector(1, 0, 0), 180)


def flat_part(name, profile: Profile, t, *, kind="scs", material="brass .040\"",
              placements=None, color=BRASS, group="movement", spec="", qty_extra=0,
              density="brass", allow=()) -> Part:
    if profile.poly.geom_type != "Polygon":
        raise ValueError(f"{name}: outline is not a single connected piece")
    return Part(name, kind, material, profile_solid(profile, t),
                placements or [loc()], color, group, profile, [], spec or material,
                qty_extra, density, allow)


def cylinder(d, h, x=0.0, y=0.0, z=0.0, hole=0.0) -> cq.Solid:
    s = cq.Solid.makeCylinder(d / 2, h, cq.Vector(x, y, z))
    if hole:
        s = s.cut(cq.Solid.makeCylinder(hole / 2, h + 2, cq.Vector(x, y, z - 1)))
    return s


def box(x0, y0, z0, x1, y1, z1) -> cq.Solid:
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def hexagon(af, h, x, y, z, hole=0.0) -> cq.Solid:
    s = cq.Workplane("XY", origin=(x, y, z)).polygon(6, af / math.cos(math.pi / 6)).extrude(h).val()
    if hole:
        s = s.cut(cylinder(hole, h + 2, x, y, z - 1))
    return s


# ---------------------------------------------------------------------------
# Case: lower tray, upper shell (top face), lid
# ---------------------------------------------------------------------------
def knob_xy(train) -> tuple[float, float]:
    return polar(R_KNOB, train["angle"])


def knob_tip_r() -> float:
    return pitch_radius(MODULE, Z_KNOB) + MODULE


def knob_notch_width(wall_plane: float) -> float:
    """Chord of the knob wheel where it crosses a wall at distance wall_plane."""
    d = wall_plane - R_KNOB
    return 2 * math.sqrt(max(0.0, knob_tip_r() ** 2 - d * d)) + 2 * KNOB_NOTCH_SIDE


def wall_point(poly: Polygon, angle_deg: float) -> tuple[float, float]:
    """Where a ray from the centre at angle_deg meets the polygon boundary."""
    far = polar(200, angle_deg)
    from shapely.geometry import LineString
    p = LineString([(0, 0), far]).intersection(poly.exterior)
    return (p.x, p.y)


def countersunk_tray(tray: Tray) -> cq.Shape:
    """Finished case; the laser-cut blank retains plain pilot holes."""
    seats = [cq.Solid.makeCone(CASE_SCREW_HEAD_D / 2, 0, CASE_SCREW_HEAD_D / 2,
                               cq.Vector(x, y, 0), cq.Vector(0, 0, 1))
             for x, y, _ in tray.floor_holes]
    return tray.formed().cut(*seats)


def lower_tray() -> Part:
    knob_z0 = LEVELS[0] - KNOB_NOTCH_BELOW
    cuts = [WallCut(*wall_point(LOWER_OUTER, tr["angle"]), knob_notch_width(CASE_W / 2 - T040),
                    knob_z0, LOWER_H + 1) for tr in TRAINS]
    ux = wall_point(LOWER_OUTER, 0.0)[0]
    # USB-C opening big enough for a plug's overmould to enter (the receptacle sits ~1.5 mm in)
    cuts.append(WallCut(ux, USB["y"], 12.6, USB["z"] - 3.3, USB["z"] + 3.3, rounded=True))
    (cx, cy), _ = crown_axis()
    cuts.append(WallCut(cx, cy, 3.1, CROWN_Z - 1.55, CROWN_Z + 1.55, rounded=True))
    tray = Tray(LOWER_OUTER, LOWER_H, T040, BEND_IR, K_FACTOR,
                floor_holes=[(x, y, POST_HOLE) for x, y in L.BAY_POSTS], wall_cuts=cuts)
    prof, bends = tray.flat()
    p = Part("case_lower_tray", "scs-bent", "brass .040\"", countersunk_tray(tray), [loc()], BRASS,
             "case", prof, bends, "brass .040\", 8 bends 90° up; hand-countersink 3 floor holes "
             "90° to suit M2 DIN 963 heads (nominal diameter 3.8 mm) after forming", tray=tray)
    return p


def _to_local_upper(x, y, z):
    """Global point -> upper-shell local (tray) coordinates."""
    return x, -y, Z_TOP - z


def crown_axis() -> tuple[tuple[float, float], tuple[float, float]]:
    """Centre of the lower tray's top-right chamfer (outer face) and outward unit direction."""
    pts = list(LOWER_OUTER.exterior.coords)
    # TR chamfer is the edge whose midpoint lies on the +x+y diagonal
    best = None
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        if mx > 0 and my > 0 and abs(mx - my) < 1e-6:
            best = ((x0, y0), (x1, y1), (mx, my))
    (x0, y0), (x1, y1), (mx, my) = best
    L = math.hypot(x1 - x0, y1 - y0)
    e = ((x1 - x0) / L, (y1 - y0) / L)
    if e[1] < 0:
        e = (-e[0], -e[1])
    return (mx, my), (math.sqrt(0.5), math.sqrt(0.5))


def upper_shell() -> Part:
    face = []
    face.append(circle(0, 0, WINDOW_R))
    for i in range(SLOT_N):
        a = 360.0 * i / SLOT_N
        x0, y0 = polar(SLOT_R0, a)
        x1, y1 = polar(SLOT_R1, a)
        face.append(slot(x0, y0, x1, y1, SLOT_W))
    holes = [(x, -y, POST_HOLE) for x, y in POSTS]

    cuts = []
    knob_top = LEVELS[0] + KNOB_FACE + KNOB_NOTCH_ABOVE
    for tr in TRAINS:
        x, y = wall_point(UPPER_OUTER, tr["angle"])
        _, ly, _ = _to_local_upper(x, y, 0)
        cuts.append(WallCut(x, ly, knob_notch_width(CASE_W / 2 + SEAM_GAP),
                            Z_TOP - knob_top, UPPER_H + 1))
    tray = Tray(UPPER_OUTER, UPPER_H, T040, BEND_IR, K_FACTOR, floor_cuts=face,
                floor_holes=holes, wall_cuts=cuts)
    prof, bends = tray.flat()
    solid = countersunk_tray(tray)
    for y, z in hinge_body_mounts():
        solid = solid.cut(cq.Solid.makeCylinder(HINGE_MOUNT_CLEAR / 2, 4,
                          cq.Vector(HINGE_X - 2, -y, -z), cq.Vector(1, 0, 0)))
    return Part("case_upper_shell", "scs-bent", "brass .040\"", solid, [flipped(Z_TOP)],
                BRASS, "case", prof, bends,
                "brass .040\", 8 bends 90°; hand-countersink 4 top holes "
                "90° to suit M2 DIN 963 heads (nominal diameter 3.8 mm) after forming; "
                "transfer-drill hinge mounting holes only after checking the purchased hinge",
                tray=tray)


def lid() -> Part:
    tray = Tray(UPPER_OUTER, LID_H, T040, BEND_IR, K_FACTOR)
    prof, bends = tray.flat()
    solid = tray.formed()
    for y in HINGE_LID_MOUNTS:
        solid = solid.cut(cq.Solid.makeCylinder(HINGE_LID_CLEAR / 2, 4,
                          cq.Vector(HINGE_X - 2, -y, LID_H - HINGE_LID_MOUNT_Z), cq.Vector(1, 0, 0)))
    return Part("case_lid", "scs-bent", "brass .040\"", solid, [flipped(Z_TOP + LID_H)],
                BRASS, "lid", prof, bends, "brass .040\", 8 bends 90°; "
                "transfer-drill hinge holes after checking the purchased hinge", tray=tray)


def lid_overlay() -> Part:
    """Pierced rosette fixed inside the lid (seen when the lid is open)."""
    base = offset(UPPER_INNER, -(BEND_IR + 0.6))
    p = Profile(base)
    border = offset(base, -3.2)
    cells = []
    # central medallion petals
    for i in range(8):
        a = 22.5 + 45 * i
        cells.append(affinity.rotate(slot(*polar(4.2, 0), *polar(7.6, 0), 2.2), a, origin=(0, 0)))
    # two rings of 16 radial cells
    for r0, r1, n, off_a in ((11.0, 24.0, 16, 0.0), (26.0, 41.0, 16, 11.25)):
        for i in range(n):
            a0 = off_a + 360.0 * i / n
            span = 360.0 / n
            cell = annulus(r0, r1).intersection(
                Polygon([(0, 0), polar(80, a0 + 0.9), polar(80, a0 + span - 0.9)]))
            cells.append(cell.buffer(-0.7).buffer(0.4))
    ring = annulus(42.5, 45.5)
    cells.append(ring.difference(unary_union([rect(*polar(44, a), 4.0, 2.0, a) for a in range(0, 360, 30)])))
    # corner fans
    for a in (45, 135, 225, 315):
        for k, rr in enumerate((49.0, 54.0, 59.0)):
            arc = annulus(rr, rr + 3.0).intersection(Polygon([(0, 0), polar(90, a - 14 + k * 2), polar(90, a + 14 - k * 2)]))
            cells.append(arc)
    magnets = [(x, -y) for x, y in (LID_MAGNET_L, REED["c"])]
    pads = unary_union([circle(x, y, MAGNET_D / 2 + 2.2) for x, y in magnets])
    cut = unary_union(cells).intersection(border.buffer(-0.01)).difference(pads)
    p.cut(cut)
    for x, y in magnets:
        p.hole(x, y, MAGNET_D + 0.4)
    return flat_part("lid_overlay", p, T040, placements=[cq.Location(cq.Vector(0, 0, Z_TOP + LID_H - T040), cq.Vector(1, 0, 0), 180)],
                     group="lid", spec="brass .040\" pierced rosette")


# ---------------------------------------------------------------------------
# Movement plates
# ---------------------------------------------------------------------------
def sensor_xy(train):
    return polar(R_SENSOR, train["angle"])


def skeleton(outline: Polygon, keep: list[Polygon], ribs: list[tuple], rim=4.0, rib_w=3.0,
             zone: Polygon | None = None, min_void=12.0) -> Polygon:
    """Material to remove: the area inside `outline` (minus a rim) that is not
    needed by `keep` shapes or the straight `ribs` (pairs of points)."""
    free = offset(outline, -rim)
    if zone is not None:
        free = free.intersection(zone)
    solid = unary_union(keep + [slot(*a, *b, rib_w) for a, b in ribs])
    voids = free.difference(solid).buffer(-0.8).buffer(0.8)
    geoms = getattr(voids, "geoms", [voids])
    return unary_union([g for g in geoms if g.area >= min_void])


def p1_plate() -> Part:
    outline = offset(LOWER_INNER, -PLATE_CLEAR)
    p = Profile(outline)
    bearings = [(0.0, 0.0)] + [sensor_xy(t) for t in TRAINS] + [knob_xy(t) for t in TRAINS]
    keep = [circle(x, y, 4.6) for x, y in bearings] + [circle(x, y, 4.4) for x, y in POSTS]
    keep.append(circle(*X27_CENTER, X27_BODY_D / 2 + 2.6))
    keep.append(circle(*SPEAKER["c"], SPEAKER["d"] / 2 + 1.0))            # speaker seat
    ribs = []
    for tr in TRAINS:
        ribs += [((0, 0), sensor_xy(tr)), (sensor_xy(tr), knob_xy(tr))]
    ribs += [((0, 0), X27_CENTER)]
    for x, y in POSTS:
        ribs += [((x, y), (x * 0.55, y * 0.55)), ((x * 0.55, y * 0.55), (0, 0))]
    p.cut(skeleton(outline, keep, ribs))
    p.hole(0, 0, TUBE_18 + BUSH_FIT)                  # 1/8" tube bushing for the 3/32" arbor I
    for tr in TRAINS:
        p.hole(*sensor_xy(tr), TUBE_532 + BUSH_FIT)    # 5/32" tube bushings for the 1/8" shafts
        p.hole(*knob_xy(tr), TUBE_316 + BUSH_FIT)    # 3/16" tube bushings for the 5/32" knob shafts
    for x, y in POSTS:
        p.hole(x, y, POST_HOLE_PLATE)
    p.cut(slot(X27_CENTER[0] - 1.0, 0, X27_CENTER[0] + 1.0, 0, X27_BODY_D + 0.6))  # slide to set gear mesh
    p.hole(*SPK_WIRE_HOLE, 3.5)                       # speaker leads down to J5 (deburr the edge)
    return flat_part("movement_base_plate_P1", p, T063, material="brass .063\"",
                     placements=[loc(z=Z_P1)], spec="brass .063\" (hidden; skeletonised)",
                     color=BRASS_DARK)


def p2_plate() -> Part:
    outline = offset(UPPER_INNER, -PLATE_CLEAR)
    hinge_clearance = T040 + T063 + HINGE_NUT_H + 0.4       # backing strip + M2 nuts inside the wall
    outline = outline.difference(rect(HINGE_X, 0, 2 * hinge_clearance, hinge_span() + 1.0))
    p = Profile(outline)
    # hidden outer zone (under the top face) is opened up for weight and as the sound path
    keep = [circle(x, y, 4.6) for x, y in POSTS] + [circle(*knob_xy(t), 4.6) for t in TRAINS]
    keep.append(circle(*MIC["c"], MIC["d"] / 2 + 1.5))
    ribs = [(polar(DIAL_R_OUT + 1, a), polar(80, a)) for a in (0, 22.5, 45, 67.5, 112.5, 135, 157.5,
                                                               202.5, 225, 247.5, 292.5, 315, 337.5)]
    ribs += [(polar(DIAL_R_OUT + 1, t["angle"]), knob_xy(t)) for t in TRAINS]
    zone = Polygon([(-80, -80), (80, -80), (80, 80), (-80, 80)]).difference(circle(0, 0, DIAL_R_OUT + 1.4))
    p.cut(skeleton(outline, keep, ribs, rim=3.0, zone=zone))
    window = circle(0, 0, SKELETON_R)
    keep = [circle(0, 0, 5.4)]
    for a in (90, 180, 270):          # spokes to the sensor-shaft bosses; X27 side left open
        keep.append(slot(0, 0, *polar(SKELETON_R + 1, a), 3.4))
    for tr in TRAINS:
        keep.append(circle(*sensor_xy(tr), 3.8))
    # decorative inner ring that the spokes cross
    keep.append(annulus(15.0, 16.6))
    p.cut(window.difference(unary_union(keep)))
    p.hole(0, 0, TUBE_732 + FIT * 2)
    for tr in TRAINS:
        p.hole(*sensor_xy(tr), TUBE_532 + BUSH_FIT)
        p.hole(*knob_xy(tr), TUBE_316 + BUSH_FIT)
    for x, y in POSTS:
        p.hole(x, y, POST_HOLE_PLATE)
    # mic port (BL); the speaker (TL) and reed wires use the open outer lattice
    mx, my = MIC["c"]
    p.hole(mx, my, 1.2)
    for i in range(6):
        p.hole(*(v + w for v, w in zip((mx, my), polar(2.0, 60 * i))), 1.0)
    return flat_part("dial_plate_P2", p, T063, material="brass .063\"",
                     placements=[loc(z=Z_P2)], spec="brass .063\"")


def spider(name, r_in, t, z) -> Part:
    shape = annulus(r_in, SPIDER_R_OUT)
    for x, y in POSTS:
        a = math.degrees(math.atan2(y, x))
        shape = shape.union(slot(*polar(SPIDER_R_OUT - 1, a), x, y, 6.0)).union(circle(x, y, 3.4))
    shape = shape.difference(circle(0, 0, r_in))
    p = Profile(shape)
    for x, y in POSTS:
        p.hole(x, y, POST_HOLE)
    return flat_part(name, p, t, material=f"brass {'.040' if t < 1.2 else '.063'}\"",
                     placements=[loc(z=z)], group="case")


def crystal() -> Part:
    p = Profile(circle(0, 0, CRYSTAL_R))
    return flat_part("crystal", p, CRYSTAL_T, material="clear acrylic .063\"",
                     placements=[loc(z=Z_FRAME)], color=GLASS, group="case",
                     spec="clear cast acrylic .063\" (or Ø88×1.5 mineral glass)", density="acrylic")


def dial_sticker() -> Part:
    p = Profile(annulus(DIAL_R_IN, DIAL_R_OUT))
    return Part("dial_sticker", "bought", "printed vinyl", profile_solid(p, STICKER_T),
                [loc(z=Z_P2_TOP)], IVORY, "dial", None, [], "hardware/dial/dial_print_letter.pdf",
                density="acrylic")


# ---------------------------------------------------------------------------
# Gears, hands, arbors
# ---------------------------------------------------------------------------
def gear_profile(z, hole, pattern=None) -> Profile:
    p = Profile(gear_polygon(MODULE, z, backlash=GEAR_BACKLASH))
    if pattern:
        p.cut(crossings(z, hole, **pattern))
    p.hole(0, 0, hole)
    return p


def crossings(z, hole, *, kind="curved", n=5, sweep=30.0, spoke=1.2, ring=None) -> Polygon:
    """Clock-wheel style 'crossings': windows cut between a rim and a hub, leaving
    `n` spokes (curved by `sweep` degrees, or straight) and an optional ring
    (radius) — or, for kind='rosette', n round windows. Returns the area to remove."""
    rf = pitch_radius(MODULE, z) - 1.25 * MODULE
    r_rim = rf - 1.3                       # solid rim under the teeth
    r_hub = hole / 2 + 1.7                 # solder land around the arbor
    band = annulus(r_hub, r_rim)
    if kind == "rosette":
        rm = (r_hub + r_rim) / 2
        r_win = min((r_rim - r_hub) / 2 - 0.9, math.pi * rm / n - 1.0)
        wins = [circle(*polar(rm, 360.0 * k / n), r_win) for k in range(n)]
        wins += [circle(*polar(r_rim - 1.0, 360.0 * (k + 0.5) / n), 0.55) for k in range(n)]
        return unary_union(wins).intersection(band.buffer(-0.6))
    keep = []
    for k in range(n):
        a0 = 360.0 * k / n
        pts = []
        for i in range(13):
            t = i / 12
            r = (r_hub - 0.5) + t * (r_rim - r_hub + 1.0)
            pts.append(polar(r, a0 + (sweep * math.sin(t * math.pi / 2) if kind == "curved" else 0.0)))
        keep.append(LineString(pts).buffer(spoke / 2, quad_segs=6))
    if ring:
        keep.append(annulus(ring - spoke / 2, ring + spoke / 2))
    return band.difference(unary_union(keep)).buffer(-0.35).buffer(0.35)


# Crossing patterns for the gears you can see through the dial window.
GEAR_PATTERNS = {
    "I": dict(kind="curved", n=5, sweep=34.0),
    "II": dict(kind="straight", n=6, ring=7.6),
    "III": dict(kind="curved", n=4, sweep=-46.0),
    "sensor": dict(kind="rosette", n=6),
    "motor": dict(kind="curved", n=6, sweep=-28.0),
}


def mesh_rot(direction_deg, z, gap=False):
    """Rotation that puts a tooth (or a gap) of a gear toward direction_deg."""
    return direction_deg + (180.0 / z if gap else 0.0)


def gears() -> list[Part]:
    parts = []
    tubes = [ROD_332, TUBE_18, TUBE_532]
    for tr, od in zip(TRAINS, tubes):
        z = LEVELS[tr["level"]]
        a = tr["angle"]
        sx, sy = sensor_xy(tr)
        kx, ky = knob_xy(tr)
        parts.append(flat_part(f"gear_hand_{tr['name']}_{Z_HAND}T",
                               gear_profile(Z_HAND, od + GEAR_FIT, GEAR_PATTERNS[tr["name"]]), T040,
                               placements=[loc(z=z, rz=mesh_rot(a, Z_HAND))]))
        parts.append(flat_part(f"gear_sensor_{tr['name']}_{Z_SENSOR}T",
                               gear_profile(Z_SENSOR, ROD_18 + GEAR_FIT, GEAR_PATTERNS["sensor"]), T040,
                               placements=[loc(sx, sy, z, mesh_rot(a + 180, Z_SENSOR, gap=True))]))
        knob = profile_solid(Profile(gear_polygon(MODULE, Z_KNOB)).hole(0, 0, KNOB_BORE), KNOB_FACE)
        parts.append(stock(f"knob_{tr['name']}_{Z_KNOB}T", knob,
                           [loc(kx, ky, LEVELS[0], mesh_rot(a + 180, Z_KNOB))], KNOB_GEAR_SPEC,
                           kind="bought"))
    parts.append(flat_part(f"gear_needle_{Z_NEEDLE}T", gear_profile(Z_NEEDLE, TUBE_316 + GEAR_FIT), T040,
                           placements=[loc(z=LEVELS[3], rz=0.0)]))
    parts.append(flat_part(f"gear_motor_{Z_MOTOR}T", gear_profile(Z_MOTOR, 1.0 + GEAR_FIT, GEAR_PATTERNS["motor"]), T040,
                           placements=[loc(*X27_SHAFT, LEVELS[3], mesh_rot(180, Z_MOTOR, gap=True))]))
    return parts


def hand_shape(length, width, hub_r, tail=5.0, pierce=True) -> Polygon:
    w = width / 2
    blade = Polygon([(0, length), (-w, length * 0.60), (-w * 0.42, hub_r - 0.6),
                     (w * 0.42, hub_r - 0.6), (w, length * 0.60)])
    shape = blade.union(circle(0, 0, hub_r))
    shape = shape.union(Polygon([(0, -tail), (-w * 0.8, -hub_r * 0.6), (w * 0.8, -hub_r * 0.6)]))
    if pierce and width >= 3.2:
        shape = shape.difference(circle(0, length * 0.60, w * 0.38))
    return shape


def needle_shape(hub_r) -> Polygon:
    blade = Polygon([(0, NEEDLE_LEN), (-0.75, NEEDLE_LEN * 0.55), (-1.15, hub_r - 0.6),
                     (1.15, hub_r - 0.6), (0.75, NEEDLE_LEN * 0.55)])
    tail = Polygon([(-1.0, 0), (1.0, 0), (0.9, -NEEDLE_TAIL + 2.6), (-0.9, -NEEDLE_TAIL + 2.6)])
    weight = circle(0, -NEEDLE_TAIL + 1.0, 2.9).difference(circle(0, -NEEDLE_TAIL + 1.0, 1.3))
    return blade.union(circle(0, 0, hub_r)).union(tail).union(weight)


HAND_GAP = 0.35
Z_NEEDLE_HAND = Z_P2_TOP + STICKER_T + 0.2 + 0.1
Z_HANDS = {}
_z = Z_NEEDLE_HAND + T032 + HAND_GAP
for _tr in reversed(TRAINS):           # III lowest, I on top
    Z_HANDS[_tr["name"]] = _z
    _z += T040 + HAND_GAP
Z_CAP = Z_HANDS["I"] + T040
DEMO_SYMBOLS = {"I": 1, "II": 10, "III": 23, "needle": 29}   # Sun, Moon, Elephant, Owl


def hands() -> list[Part]:
    parts = []
    for tr, od in zip(TRAINS, [ROD_332, TUBE_18, TUBE_532]):
        hub = max(od / 2 + 1.5, 3.25)      # also keeps the part above SCS minimum size
        p = Profile(hand_shape(tr["length"], tr["width"], hub))
        p.hole(0, 0, od + FIT)
        parts.append(flat_part(f"hand_{tr['name']}", p, T040, group="hands", color=BLUED,
                               placements=[loc(z=Z_HANDS[tr["name"]], rz=-10 * DEMO_SYMBOLS[tr["name"]])],
                               spec="brass .040\" (blue/black patina or paint)"))
    hub = TUBE_316 / 2 + 1.5
    p = Profile(needle_shape(hub))
    p.hole(0, 0, TUBE_316 + FIT)
    parts.append(flat_part("hand_needle", p, T032, material="copper .032\"", group="hands",
                           color=COPPER, density="copper",
                           placements=[loc(z=Z_NEEDLE_HAND, rz=-10 * DEMO_SYMBOLS["needle"])],
                           spec="copper .032\""))
    cap = circle(0, 0, 4.0)
    for i in range(8):
        cap = cap.union(circle(*polar(4.0, 45 * i + 22.5), 1.25))
    p = Profile(cap)
    p.hole(0, 0, ROD_332 + FIT)
    for i in range(8):
        p.hole(*polar(3.1, 45 * i + 22.5), 0.9)
    parts.append(flat_part("hand_cap_rosette", p, T040, group="hands", placements=[loc(z=Z_CAP)]))
    return parts


def stock(name, solid, placements, spec, color=BRASS, group="movement", density="brass", kind="stock"):
    return Part(name, kind, spec, solid, placements, color, group, None, [], spec, density=density)


def arbors() -> list[Part]:
    parts = []
    # framing-hand arbors: 3/32 rod (I), 1/8 tube (II), 5/32 tube (III); needle 3/16 tube; cannon 7/32
    tops = {tr["name"]: Z_HANDS[tr["name"]] + T040 for tr in TRAINS}
    tops["I"] = Z_CAP + T040
    specs = [(TRAINS[0], ROD_332, 0.0, Z_P1, "K&S 3/32\" brass rod"),
             (TRAINS[1], TUBE_18, TUBE_18 - 2 * KS_WALL, LEVELS[1], "K&S 1/8\" brass tube"),
             (TRAINS[2], TUBE_532, TUBE_532 - 2 * KS_WALL, LEVELS[2], "K&S 5/32\" brass tube")]
    for tr, od, idia, z0, spec in specs:
        h = tops[tr["name"]] - z0
        parts.append(stock(f"arbor_{tr['name']}", cylinder(od, h, z=z0, hole=idia), [loc()],
                           f"{spec}, {h:.1f} mm"))
    zn = LEVELS[3]
    h = Z_NEEDLE_HAND + T032 - zn
    parts.append(stock("arbor_needle", cylinder(TUBE_316, h, z=zn, hole=TUBE_316 - 2 * KS_WALL), [loc()],
                       f"K&S 3/16\" brass tube, {h:.1f} mm"))
    h = Z_NEEDLE_HAND - 0.1 - Z_P2
    parts.append(stock("cannon", cylinder(TUBE_732, h, z=Z_P2, hole=TUBE_732 - 2 * KS_WALL), [loc()],
                       f"K&S 7/32\" brass tube, {h:.2f} mm (soldered into P2)"))
    # plate bushings (K&S tube, flush with each plate)
    bush = [(0.0, 0.0, TUBE_18, Z_P1, "1/8")]
    for tr in TRAINS:
        for xy, od, size in ((sensor_xy(tr), TUBE_532, "5/32"), (knob_xy(tr), TUBE_316, "3/16")):
            bush += [(*xy, od, Z_P1, size), (*xy, od, Z_P2, size)]
    for size in ("1/8", "5/32", "3/16"):
        items = [b for b in bush if b[4] == size]
        x0, y0, od, z0, _ = items[0]
        parts.append(stock(f"bushing_{size.replace('/', '_')}",
                           cylinder(od, T063, x0, y0, z0, hole=od - 2 * KS_WALL),
                           [loc(x - x0, y - y0, z - z0) for x, y, _, z, _ in items],
                           f"K&S {size}\" brass tube, {T063:.1f} mm bushing, Loctite 638 into the plate"))
    # sensor and knob shafts
    shaft_h = Z_P2_TOP - Z_P1
    for tr in TRAINS:
        sx, sy = sensor_xy(tr)
        kx, ky = knob_xy(tr)
        sh = shaft_h + SENSOR_MAGNET_DROP
        parts.append(stock(f"shaft_sensor_{tr['name']}", cylinder(ROD_18, sh, sx, sy, Z_P1 - SENSOR_MAGNET_DROP),
                           [loc()], f"K&S 1/8\" brass rod, {sh:.1f} mm"))
        parts.append(stock(f"shaft_knob_{tr['name']}", cylinder(ROD_532, shaft_h, kx, ky, Z_P1), [loc()],
                           f"K&S 5/32\" brass rod, {shaft_h:.1f} mm"))
        zl = LEVELS[tr["level"]]
        sl = cylinder(TUBE_532, zl - Z_P1_TOP, sx, sy, Z_P1_TOP, hole=TUBE_532 - 2 * KS_WALL)
        parts.append(stock(f"sleeve_sensor_{tr['name']}", sl, [loc()],
                           f"K&S 5/32\" tube, {zl - Z_P1_TOP:.2f} mm"))
        k0, k1 = LEVELS[0], LEVELS[0] + KNOB_FACE
        parts.append(stock(f"sleeve_knob_{tr['name']}",
                           cylinder(TUBE_316, k0 - Z_P1_TOP, kx, ky, Z_P1_TOP, hole=TUBE_316 - 2 * KS_WALL)
                           .fuse(cylinder(TUBE_316, Z_P2 - k1, kx, ky, k1, hole=TUBE_316 - 2 * KS_WALL)),
                           [loc()], f"K&S 3/16\" tube, {k0 - Z_P1_TOP:.2f} + {Z_P2 - k1:.2f} mm"))
        parts.append(stock(f"magnet_{tr['name']}",
                           cylinder(6.0, SENSOR_MAGNET_H, sx, sy, Z_P1 - SENSOR_MAGNET_DROP - SENSOR_MAGNET_H),
                           [loc()],
                           f"Ø6×{SENSOR_MAGNET_H:g} mm diametric NdFeB (AS5600 magnet)", STEEL,
                           density="steel", kind="bought"))
    return parts


# ---------------------------------------------------------------------------
# Hardware, electronics and fittings (simplified bodies for fit checks/renders)
# ---------------------------------------------------------------------------
def countersunk_screw(length: float, d=CASE_SCREW_D, head_d=CASE_SCREW_HEAD_D) -> cq.Shape:
    head_h = (head_d - d) / 2
    head = cq.Solid.makeCone(head_d / 2, d / 2, head_h)
    shaft = cylinder(d, length - head_h, z=head_h)
    screw = head.fuse(shaft)
    return screw.cut(box(-head_d / 2 - 0.1, -0.25, -0.1,
                         head_d / 2 + 0.1, 0.25, 0.35))


def hardware() -> list[Part]:
    parts = []
    hx = lambda h, z, hole=0.0: [hexagon(4.0, h, x, y, z, hole) for x, y in POSTS]
    for name, h, z, spec in (("standoff_bay", CARRIER_STANDOFF, Z_CARRIER_TOP,
                              f"M2×{CARRIER_STANDOFF:g} F-F brass hex standoff"),
                             ("standoff_gear", GEAR_STANDOFF, Z_P1_TOP, "M2×8+3 M-F brass hex standoff"),
                             ("standoff_hand", HAND_STANDOFF, Z_P2_TOP, "M2×6+3 M-F brass hex standoff")):
        posts = L.BAY_POSTS if name == "standoff_bay" else POSTS
        (x0, y0) = posts[0]
        sol = hexagon(4.0, h, x0, y0, z, 2.0)
        parts.append(Part(name, "bought", spec, sol, [loc(x - x0, y - y0) for x, y in posts],
                          BRASS_DARK, "hardware", spec=spec))
    nx, ny = POSTS[0]
    parts.append(Part("nut_p1_corner", "bought", "M2 brass hex nut", hexagon(4.0, 1.6, nx, ny, Z_P1 - 1.6, 2.0),
                      [loc()], BRASS_DARK, "hardware",
                      spec="M2 brass hex nut (top-right gear standoff under P1; no bay post there)"))
    x0, y0 = L.BAY_POSTS[0]
    spacer = cylinder(4.5, CARRIER_SPACER, x0, y0, Z_FLOOR_TOP, hole=2.2)
    parts.append(Part("spacer_carrier", "bought", "M2 nylon spacer 2.5 mm", spacer,
                      [loc(x - x0, y - y0) for x, y in L.BAY_POSTS], IVORY, "hardware",
                      spec="M2 nylon round spacer, 2.5 mm long, Ø4.5 OD (insulates the PCB from the case)"))
    for name, length, posts, solid in (
        ("screw_floor", FLOOR_SCREW_LEN, L.BAY_POSTS, countersunk_screw(FLOOR_SCREW_LEN)),
        ("screw_top", TOP_SCREW_LEN, POSTS, countersunk_screw(TOP_SCREW_LEN).moved(flipped(Z_TOP))),
    ):
        spec = f"M2×{length:g} brass slotted countersunk screw, DIN 963, 90° (length includes head)"
        parts.append(Part(name, "bought", spec, solid, [loc(x, y) for x, y in posts],
                          BRASS_DARK, "hardware", spec=spec))
    return parts


def carrier_outline() -> Polygon:
    w, c = L.octagon_inset(CASE_W, CASE_CHAMFER, T040 + L.CARRIER_CLEAR)
    return octagon(w, c)


def _place_pt(pt, place):
    (x, y), r = place["c"], math.radians(place["rot"])
    return (x + pt[0] * math.cos(r) - pt[1] * math.sin(r), y + pt[0] * math.sin(r) + pt[1] * math.cos(r))


def placed(solid: cq.Solid, place: dict, z: float = 0.0) -> cq.Solid:
    (x, y), rot = place["c"], place["rot"]
    return solid.rotate(cq.Vector(), cq.Vector(0, 0, 1), rot).translate(cq.Vector(x, y, z))


def electronics() -> list[Part]:
    E = []

    def add(name, solid, spec, color=PCB):
        E.append(Part(name, "bought", spec, solid, [loc()], color, "electronics", spec=spec,
                      density="steel"))

    zt = Z_CARRIER_TOP
    zm = zt + L.MODULE_LIFT                                   # socketed module undersides
    # carrier PCB (ordered from a PCB fab; see hardware/pcb)
    pcb = Profile(carrier_outline())
    for x, y in L.BAY_POSTS:
        pcb.hole(x, y, POST_HOLE)
    u = L.ADAFRUIT_USBC
    for hx_, hy_ in u["holes"]:                               # USB breakout screws
        pcb.hole(*_place_pt((hx_, hy_), L.USBC_PLACE), 2.4)
    for x, y in L.X27_PINS.values():
        pcb.hole(x, y, 1.2)
    E.append(Part("pcb_carrier", "pcb", "FR4 1.6 mm, 2 layers", profile_solid(pcb, CARRIER_T),
                  [loc(z=Z_CARRIER)], (0.06, 0.28, 0.14), "electronics", pcb, [],
                  "hardware/pcb (JLCPCB/PCBWay, 2-layer 1.6 mm)", density="fr4"))

    # Sockets: (module placement, [(x, y, along_x, n_pins)] in the module frame)
    def row(x, y, along_x, n):
        return (x, y, along_x, n)
    a = L.ADAFRUIT_AS5600
    sockets = [(L.PROS3_PLACE, [row(7.62, 0, False, 17), row(-7.62, 0, False, 17)]),
               (L.DRV8833_PLACE, [row(-6.35, 0, False, 8), row(6.35, 0, False, 6)]),
               (L.MAX98357_PLACE, [row(0, -6.985, True, 7), row(-1.8, 5.969, True, 1), row(1.7, 5.969, True, 1)])]
    sockets += [(L.AS5600_PLACE[tr["name"]], [row(0, a["header_dy"], True, 6), row(0, a["rest"][0][1], True, 2)])
                for tr in TRAINS]
    sockets += [(L.USBC_PLACE, [row(0, u["header_dy"], True, 8)])]
    strip = None
    for place, rows in sockets:
        for x, y, along_x, n in rows:
            hx, hy = (n * 1.27, 1.27) if along_x else (1.27, n * 1.27)
            body = box(x - hx, y - hy, 0, x + hx, y + hy, L.SOCKET_H)
            body = placed(body, place, zt)
            strip = body if strip is None else strip.fuse(body)
    cx = X27_CENTER[0]
    for sy in (11.43, -11.43):                                # X27: two 1x4 short female headers
        body = box(cx - 5.08, sy - 1.27, zt, cx + 5.08, sy + 1.27, zt + L.X27_SOCKET_H)
        strip = strip.fuse(body)
    E.append(Part("module_sockets", "bought", "5 mm female header sockets", strip, [loc()],
                  BLACK, "electronics", spec="Adafruit #3008 5 mm short female headers, cut to length "
                  "(modules and X27)", density="acrylic"))

    # ProS3 (frame: USB-C toward +y; placed with USB toward +x), on its headers
    pros3 = box(-8.9, -27.76, 0, 8.9, 24.13, 1.0).fuse(box(-6.5, -14, 1.0, 6.5, 14, 2.6)) \
        .fuse(box(-4.47, 17.3, 1.0, 4.47, 25.1, 4.3)).fuse(box(-3, -27.0, 1.0, 3, -22.0, 5.4))
    pros3 = pros3.fuse(box(-4.2, 25.1, 0.2, 4.2, 37.0, 5.4))  # USB-C cable plug overmould (to J7)
    add("mcu_ProS3", placed(pros3, L.PROS3_PLACE, zm), "Unexpected Maker ProS3 (ESP32-S3) + short USB-C cable")
    bx0, by0, bx1, by1 = L.BATTERY_BOX
    add("battery", box(bx0, by0, zt + 0.3, bx1, by1, zt + 4.8), "LiPo 1S 402535 (~350 mAh)", (0.5, 0.5, 0.55))
    drv = box(-8.89, -12.7, 0, 8.89, 12.7, 1.6).fuse(box(-3, -4, 1.6, 3, 4, 2.8))
    add("driver_DRV8833", placed(drv, L.DRV8833_PLACE, zm), "Adafruit DRV8833 #3297")
    amp = box(-8.89, -9.525, 0, 8.89, 9.525, 1.6).fuse(box(-2.5, -4, 1.6, 2.5, 2, 2.6))
    add("amp_MAX98357A", placed(amp, L.MAX98357_PLACE, zm), "Adafruit MAX98357A #3006")
    as5600 = box(-a["w"] / 2, -a["h"] / 2, 0, a["w"] / 2, a["h"] / 2, 1.6) \
        .fuse(box(-2.5, -3.0, 1.6, 2.5, 3.0, 3.1)) \
        .fuse(box(-12.7, -3.0, 1.6, -7.6, 3.0, 4.5)).fuse(box(7.6, -3.0, 1.6, 12.7, 3.0, 4.5))
    for tr in TRAINS:
        add(f"sensor_AS5600_{tr['name']}", placed(as5600, L.AS5600_PLACE[tr["name"]], zm),
            "Adafruit AS5600 #6357, plugged into the carrier")
    # X27.168: rear pins plug into 5 mm sockets, motor gear on the Ø1 shaft
    bx, by = X27_CENTER
    body = cylinder(X27_BODY_D, X27_BODY_H, bx, by, X27_BODY_BOTTOM)
    body = body.fuse(cylinder(2.0, 2.2, *X27_SHAFT, X27_BODY_TOP)).fuse(
        cylinder(1.0, LEVELS[3] + T040 + 0.3 - X27_BODY_TOP, *X27_SHAFT, X27_BODY_TOP))
    body = body.fuse(cylinder(2.0, 2.4, *X27_SHAFT, X27_BODY_BOTTOM - 2.4))
    for px, py in L.X27_PINS.values():
        body = body.fuse(cylinder(0.5, 4.4, px, py, X27_BODY_BOTTOM - 4.4))
    add("motor_X27_168", body, "Juken/Switec X27.168 gauge stepper", (0.92, 0.92, 0.88))
    sx, sy = SPEAKER["c"]
    add("speaker", cylinder(SPEAKER["d"], SPEAKER["h"], sx, sy, Z_P1_TOP + 0.2),
        "28 mm 8 Ω 1 W micro speaker (≤5 mm thick)", BLACK)
    mx, my = MIC["c"]
    add("mic_INMP441", cylinder(MIC["d"], MIC["h"], mx, my, Z_P2 - 0.5 - MIC["h"]),
        "INMP441 I2S MEMS mic module", PCB)
    # What holds them: a foam ring under the speaker, a foam tape pad between the mic and P2
    sx_, sy_ = SPEAKER["c"]
    E.append(Part("speaker_foam_ring", "bought", "foam ring", cylinder(SPEAKER["d"], 0.2, sx_, sy_, Z_P1_TOP,
                  hole=SPEAKER["d"] - 6.0), [loc()], BLACK, "electronics",
                  spec="0.2 mm adhesive foam ring, Ø28 × Ø22: seats and seals the speaker on P1",
                  density="acrylic"))
    mx_, my_ = MIC["c"]
    E.append(Part("mic_foam_tape", "bought", "foam tape", cylinder(MIC["d"], 0.5, mx_, my_, Z_P2 - 0.5, hole=2.5),
                  [loc()], (0.85, 0.85, 0.80), "electronics",
                  spec="0.5 mm double-sided foam tape, Ø14 with a Ø2.5 hole over the mic port: sticks the "
                  "INMP441 to the underside of P2 and seals the port", density="acrylic"))
    # Speaker and mic leads, so the routes are visible and collision-checked
    def run(name, pts, d, color, spec):
        sol = None
        for a, b in zip(pts, pts[1:]):
            va, vb = cq.Vector(*a), cq.Vector(*b)
            seg = cq.Solid.makeCylinder(d / 2, (vb - va).Length, va, vb - va)
            sol = seg if sol is None else sol.fuse(seg)
        for p_ in pts[1:-1]:
            sol = sol.fuse(cq.Solid.makeSphere(d / 2, cq.Vector(*p_)))
        E.append(Part(name, "bought", spec, sol.clean(), [loc()], color, "electronics", spec=spec,
                      density="copper"))
    zp = Z_CARRIER_TOP + 0.05
    hx, hy = SPK_WIRE_HOLE
    run("wire_speaker", [(hx, hy, Z_P1_TOP + 0.2), (hx, hy, zp + 2.0), (*J5_PAD_MID, zp + 1.0), (*J5_PAD_MID, zp)], SPK_WIRE_D,
        (0.75, 0.12, 0.10), "speaker leads: 2 × 30 AWG, ~6 cm, from its back tabs down through P1's "
        "Ø3.5 hole to J5 (+/−)")
    mz = Z_P2 - 0.5 - MIC["h"]
    run("wire_mic", [(-37.5, -28.5, mz), (-37.5, -28.5, mz - 1.6), (-42.5, -25.5, Z_P1_TOP + 1.0),
                     (-43.5, -24.5, Z_P1 - 3.0), (*J4_PAD_MID, zp + 1.5), (*J4_PAD_MID, zp)],
        MIC_WIRE_D, (0.35, 0.38, 0.45),
        "mic leads: 5 × 30 AWG, ~8 cm, from the INMP441 pins down through P1's open lattice to J4 "
        "(VDD GND SCK WS SD; tie L/R to GND at the mic)")
    rx, ry = REED["c"]
    reed = cq.Solid.makeCylinder(REED["d"] / 2, REED["len"], cq.Vector(-REED["len"] / 2, 0, 0),
                                 cq.Vector(1, 0, 0))
    reed = reed.rotate(cq.Vector(), cq.Vector(0, 0, 1), REED["angle"]).translate(
        cq.Vector(rx, ry, Z_TOPFACE - 0.2 - REED["d"] / 2))
    add("reed_switch", reed, "Glass reed switch, NO, ~2×14 mm", GLASS)
    # Wall USB-C: Adafruit #4090 on its socket + two 5 mm spacers, receptacle mouth toward the wall
    hw, hh = u["w"] / 2, u["h"] / 2
    usb = box(-hw, -hh, 0, hw, hh, 1.6).fuse(
        cq.Workplane("XZ", origin=(0, hh + 0.23, 1.6 + 1.63)).slot2D(8.94, 3.26).extrude(7.6).val())
    add("usb_c_breakout", placed(usb, L.USBC_PLACE, USB_BOARD_Z),
        "Adafruit USB Type C breakout #4090 (wall port), screwed down on two spacers")
    sp = None
    for hx_, hy_ in u["holes"]:
        c_ = cylinder(4.5, L.MODULE_LIFT, hx_, hy_, 0, hole=2.2)
        sp = c_ if sp is None else sp.fuse(c_)
    E.append(Part("spacer_usb", "bought", "M2 nylon spacer 5 mm", placed(sp, L.USBC_PLACE, Z_CARRIER_TOP),
                  [loc()], IVORY, "electronics",
                  spec="M2 nylon round spacer 5 mm ×2 + M2×10 screws and nuts (USB breakout)"))
    # crown: right-angle tactile switch on the carrier, plunger through the lower tray chamfer
    (cx, cy), (dx, dy) = crown_axis()
    ang = math.degrees(math.atan2(dy, dx))

    def along(solid):
        return solid.rotate(cq.Vector(), cq.Vector(0, 0, 1), ang).translate(cq.Vector(cx, cy, CROWN_Z))

    bw, bd, bh = L.CROWN_SW_BODY
    tip = -L.CROWN_TIP_GAP
    front = tip - L.CROWN_SW_ACT_LEN
    sw = box(front - bd, -bw / 2, -L.CROWN_SW_ACT_H, front, bw / 2, bh - L.CROWN_SW_ACT_H).fuse(
        box(front, -1.45, -1.45, tip, 1.45, 1.45))
    add("crown_switch", along(sw), "Omron B3F-3150 right-angle tactile switch on the carrier")
    pl_len = -tip - 0.2 + 0.6 + 3 * T040
    plunger = cq.Solid.makeCylinder(ROD_332 / 2, pl_len, cq.Vector(tip + 0.2, 0, 0), cq.Vector(1, 0, 0))
    E.append(stock("crown_plunger", along(plunger), [loc()], f"K&S 3/32\" brass rod, {pl_len:.1f} mm",
                   group="electronics"))
    c0, cl = -T040 - 0.3 - 1.5, 1.5
    collar = cq.Solid.makeCylinder(TUBE_532 / 2, cl, cq.Vector(c0, 0, 0), cq.Vector(1, 0, 0)).cut(
        cq.Solid.makeCylinder(TUBE_532 / 2 - KS_WALL, cl, cq.Vector(c0, 0, 0), cq.Vector(1, 0, 0)))
    E.append(stock("crown_collar", along(collar), [loc()],
                   "K&S 5/32\" tube, 1.5 mm, soldered on the plunger inside the wall", group="electronics"))
    magnet_spec = f"Ø{MAGNET_D:g}×{MAGNET_H:g} mm N52 magnet"
    for x, y in (LID_MAGNET_L,):
        E.append(stock("magnet_body", cylinder(MAGNET_D, MAGNET_H, x, y, Z_TOPFACE - MAGNET_H), [loc()],
                       magnet_spec, STEEL, "case", "steel", "bought"))
    for x, y in (LID_MAGNET_L, REED["c"]):
        E.append(stock(f"magnet_lid_{'closure' if x < 0 else 'reed'}",
                       cylinder(MAGNET_D, MAGNET_H, x, y, Z_TOP + LID_H - T040 - MAGNET_H), [loc()],
                       magnet_spec, STEEL, "lid", "steel", "bought"))
    return E


def crown_cap() -> list[Part]:
    (cx, cy), (dx, dy) = crown_axis()
    ang = math.degrees(math.atan2(dy, dx))
    shape = circle(0, 0, 4.2)
    for i in range(12):
        shape = shape.union(circle(*polar(4.2, 30 * i), 0.9))
    p = Profile(shape)
    p.hole(0, 0, ROD_332 + FIT)
    sol = profile_solid(p, T040)
    locs = []
    for i in range(3):   # discs stacked outward from the wall, normal along the crown axis
        locs.append(cq.Location(cq.Vector(cx + dx * (0.6 + i * T040), cy + dy * (0.6 + i * T040), CROWN_Z),
                                cq.Vector(0, 0, 1), ang) * cq.Location(cq.Vector(), cq.Vector(0, 1, 0), 90))
    cap = flat_part("crown_cap_disc", p, T040, placements=locs, group="case",
                    spec="brass .040\" ×3 soldered onto the plunger")
    return [cap]


# ---------------------------------------------------------------------------
# Hinge: one purchased brass hinge, screwed on with flush countersunk screws.
# Nothing else outside the case: the leaves themselves are the opening stop.
# ---------------------------------------------------------------------------
HINGE_X = wall_point(UPPER_OUTER, 0.0)[0]       # outer face of the right wall
HINGE_AXIS = (HINGE_X + HINGE_BARREL_D / 2, Z_TOP)


def hinge_span() -> float:
    return HINGE_KNUCKLES * 0.5 * IN


def hinge_body_mounts() -> list[tuple[float, float]]:
    """(y along the hinge, z relative to the pivot) of the body-leaf screws."""
    return [(y, HINGE_BODY_MOUNT_Z) for y in HINGE_BODY_MOUNTS]


def hinge() -> list[Part]:
    total = hinge_span()
    y0 = -total / 2
    spans = [(y0 + i * (KNUCKLE_LEN + KNUCKLE_GAP), y0 + i * (KNUCKLE_LEN + KNUCKLE_GAP) + KNUCKLE_LEN)
             for i in range(HINGE_KNUCKLES)]
    body_k = spans[0::2]
    lid_k = spans[1::2]
    ax, az = HINGE_AXIS
    clear = HINGE_BARREL_D / 2 + 0.3

    def leaf(own, strip_lo, strip_hi, tab_lo, tab_hi) -> Profile:
        poly = rect(0, (strip_lo + strip_hi) / 2, total, strip_hi - strip_lo)
        for a, b in own:
            poly = poly.union(rect((a + b) / 2, (tab_lo + tab_hi) / 2, b - a, tab_hi - tab_lo))
        return Profile(poly)

    # Leaves are drawn in their own XY (x = along the hinge, y = height above the pivot), then stood up
    stand = cq.Location(cq.Vector(HINGE_X, 0, 0), cq.Vector(0, 0, 1), 90) * \
        cq.Location(cq.Vector(), cq.Vector(1, 0, 0), 90)
    body_leaf = leaf(body_k, -HINGE_BODY_DEPTH, -clear, -clear - 0.5, 0.0)
    lid_leaf = leaf(lid_k, clear, HINGE_LID_HEIGHT, 0.0, clear + 0.5)
    body_seats = [(y, z, HINGE_MOUNT_CLEAR, CASE_SCREW_HEAD_D) for y, z in hinge_body_mounts()]
    lid_seats = [(y, HINGE_LID_MOUNT_Z, HINGE_LID_CLEAR, HINGE_LID_SCREW_HEAD_D) for y in HINGE_LID_MOUNTS]
    for prof, seats in ((body_leaf, body_seats), (lid_leaf, lid_seats)):
        for y, z, hole, _ in seats:
            prof.hole(y, z, hole)
    kn = cq.Solid.makeCylinder(HINGE_BARREL_D / 2, KNUCKLE_LEN, cq.Vector(ax, 0, az), cq.Vector(0, 1, 0)) \
        .cut(cq.Solid.makeCylinder((HINGE_PIN_D + 0.1) / 2, KNUCKLE_LEN, cq.Vector(ax, 0, az),
                                   cq.Vector(0, 1, 0)))
    parts = []
    leaf_loc = cq.Location(cq.Vector(0, 0, Z_TOP)) * stand
    for name, prof, seats, spans_, group in (
        ("hinge_leaf_body", body_leaf, body_seats, body_k, "case"),
        ("hinge_leaf_lid", lid_leaf, lid_seats, lid_k, "lid"),
    ):
        solid = profile_solid(prof, T040)
        for y, z, _, head in seats:                       # 90° countersinks: heads sit flush
            solid = solid.cut(cq.Solid.makeCone(head / 2, 0, head / 2,
                                                cq.Vector(y, z, T040), cq.Vector(0, 0, -1)))
        solid = solid.moved(leaf_loc)
        solid = solid.fuse(*(kn.moved(loc(0, a)) for a, _ in spans_))
        parts.append(stock(name, solid, [loc()],
                           "Guden BR05050404-72 brass hinge, "
                           f"{'fixed' if group == 'case' else 'moving'} half of ONE cut-to-length assembly; "
                           "countersink the screw holes 90° in the leaf; " + HINGE_REFERENCE_NOTE,
                           group=group, kind="bought"))
    pin = cq.Solid.makeCylinder(HINGE_PIN_D / 2, total, cq.Vector(ax, y0, az), cq.Vector(0, 1, 0))
    parts.append(stock("hinge_pin", pin, [loc()],
                       "Included in the purchased hinge; have the supplier retain the pin after cutting",
                       group="case", kind="bought"))

    # A backing strip inside the case wall spreads the body screws' load into the .040" sheet
    # (and is the drilling pattern); the two lid screws use washers.
    for name, height, z, seats, group, kind in (
        ("hinge_backing_body", 11.0, HINGE_BODY_MOUNT_Z, body_seats, "case", "scs"),
    ):
        profile = Profile(rect(0, z, total, height))
        for y, z_, hole, _ in seats:
            profile.hole(y, z_, hole)
        backing_loc = cq.Location(cq.Vector(-T040 - T063, 0, Z_TOP)) * stand
        parts.append(flat_part(name, profile, T063, material="brass .063\"", group=group,
                               placements=[backing_loc], kind=kind,
                               spec=f"brass .063\" hinge backing strip, {total:.1f} x {height:g} mm"
                               + ("; hand-cut (below laser service minimum width)" if kind == "stock" else "")))

    # Flush countersunk screws from outside; nuts on the backing strip (case) or washers (lid) inside
    for prefix, seats, length, d, head, nut_af, nut_h, group, inside in (
        ("hinge_body", body_seats, HINGE_BODY_SCREW_LEN, 2.0, CASE_SCREW_HEAD_D, 4.0, HINGE_NUT_H, "case",
         HINGE_X - T040 - T063),
        ("hinge_lid", lid_seats, HINGE_LID_SCREW_LEN, 1.6, HINGE_LID_SCREW_HEAD_D, 3.2, HINGE_LID_NUT_H, "lid",
         HINGE_X - T040 - HINGE_LID_WASHER_T),
    ):
        size = f"M{d:g}"
        for index, (y, z, _, _) in enumerate(seats):
            screw = countersunk_screw(length, d, head).rotate(cq.Vector(), cq.Vector(0, 1, 0), -90) \
                .translate(cq.Vector(HINGE_X + T040, y, az + z))
            parts.append(stock(f"{prefix}_screw_{index + 1}", screw, [loc()],
                               f"{size}x{length:g} DIN 963 slotted countersunk brass screw, from outside",
                               group=group, kind="bought"))
            nut = hexagon(nut_af, nut_h, 0, 0, 0, d).rotate(cq.Vector(), cq.Vector(0, 1, 0), -90) \
                .translate(cq.Vector(inside, y, az + z))
            parts.append(stock(f"{prefix}_nut_{index + 1}", nut, [loc()],
                               f"{size} brass hex nut, {nut_af:g} mm AF, inside the wall",
                               group=group, kind="bought"))
            if group == "lid":
                washer = cylinder(HINGE_LID_WASHER_D, HINGE_LID_WASHER_T, 0, 0, 0, 1.7) \
                    .rotate(cq.Vector(), cq.Vector(0, 1, 0), -90) \
                    .translate(cq.Vector(HINGE_X - T040, y, az + z))
                parts.append(stock(f"{prefix}_washer_{index + 1}", washer, [loc()],
                                   "M1.6 DIN 125 brass washer, Ø4 × 0.3 mm", group=group, kind="bought"))
    return parts


# ---------------------------------------------------------------------------
# Hinge tooling (laser-cut with the case; not part of the instrument)
# ---------------------------------------------------------------------------
def _barrel_slot_width(t: float) -> float:
    """Width a plate of thickness t lying on the leaves needs to pass the hinge barrel."""
    r = HINGE_BARREL_D / 2
    a, b = -r + T040, -r + T040 + t            # plate faces relative to the pivot (x)
    near = 0.0 if a <= 0 <= b else min(abs(a), abs(b))
    return 2 * math.sqrt(r * r - near * near) + 0.25


def _on_hinge(t_offset: float) -> cq.Location:
    """Leaf-style frame (x = along hinge, y = height above pivot, z = thickness) on the leaves."""
    stand = cq.Location(cq.Vector(HINGE_X, 0, 0), cq.Vector(0, 0, 1), 90) * \
        cq.Location(cq.Vector(), cq.Vector(1, 0, 0), 90)
    return cq.Location(cq.Vector(t_offset, 0, Z_TOP)) * stand


def hinge_drill_guide() -> Part:
    """Bent plate that hooks over the closed lid and fits round the barrel. Clamped on the
    closed case with the hinge in place, its six holes drill leaf and wall together."""
    t, ir, L = T040, BEND_IR, GUIDE_HALF_LEN
    v_bot = -(HINGE_BODY_DEPTH + GUIDE_PAD)
    v_tan = LID_H - ir                          # bend tangent, just under the lid's top face
    slot_w, slot_l = _barrel_slot_width(t), hinge_span() + 0.3

    def drill(prof, w_axis):
        prof.cut(rect(0, w_axis, slot_l, slot_w))
        for y, z in hinge_body_mounts():
            prof.hole(y, w_axis + z, HINGE_MOUNT_CLEAR)
        for y in HINGE_LID_MOUNTS:
            prof.hole(y, w_axis + HINGE_LID_MOUNT_Z, HINGE_LID_CLEAR)
        return prof

    plate = drill(Profile(rect(0, (v_bot + v_tan) / 2, 2 * L, v_tan - v_bot)), 0.0)
    solid = profile_solid(plate, t).moved(_on_hinge(T040))
    x0, zt = HINGE_X + T040, Z_TOP + LID_H      # plate inner face, lip inner face
    cx, cz = x0 - ir, zt - ir
    ring = cq.Solid.makeCylinder(ir + t, 2 * L, cq.Vector(cx, -L, cz), cq.Vector(0, 1, 0)).cut(
        cq.Solid.makeCylinder(ir, 2 * L, cq.Vector(cx, -L, cz), cq.Vector(0, 1, 0)))
    bend = ring.intersect(box(cx, -L, cz, cx + ir + t, L, cz + ir + t))
    lip = box(cx - GUIDE_LIP, -L, zt, cx, L, zt + t)
    solid = solid.fuse(bend, lip).clean()

    ba = math.pi / 2 * (ir + K_FACTOR * t)
    flat_len = (v_tan - v_bot) + ba + GUIDE_LIP
    flat = drill(Profile(rect(0, flat_len / 2, 2 * L, flat_len)), -v_bot)
    bend_w = (v_tan - v_bot) + ba / 2
    return Part("hinge_drill_guide", "scs-bent", "brass .040\"", solid, [loc()], BRASS_DARK, "tools",
                flat, [((-L, bend_w), (L, bend_w))],
                "brass .040\", one 90° bend: drill guide for all six hinge holes (lip rests on the closed "
                "lid, the barrel passes through its slot)")


def hinge_trim_gauge() -> Part:
    """Flat gauge laid over the hinge (barrel through its slot) on the bench: the slot ends mark
    the two cuts to length, the top edge is the lid-leaf trim line."""
    t = T063
    slot_w, span = _barrel_slot_width(t), hinge_span()
    half = span / 2 + 6.0
    prof = Profile(rect(0, (HINGE_LID_HEIGHT - 12.0) / 2, 2 * half, HINGE_LID_HEIGHT + 12.0))
    prof.cut(rect(0, 0, span + 0.1, slot_w))
    solid = profile_solid(prof, t).moved(_on_hinge(T040))
    return Part("hinge_trim_gauge", "scs", "brass .063\"", solid, [loc()], BRASS_DARK, "tools",
                prof, [], "brass .063\": slot ends = cuts to length (5 knuckles), top edge = lid-leaf "
                f"trim line {HINGE_LID_HEIGHT:.2f} mm from the pivot")


def tooling() -> list[Part]:
    return [hinge_drill_guide(), hinge_trim_gauge()]


# ---------------------------------------------------------------------------
def all_parts() -> list[Part]:
    parts = [lower_tray(), upper_shell(), lid(), lid_overlay(), p1_plate(), p2_plate(),
             spider("crystal_seat_spider", SEAT_R_IN, T040, Z_SEAT),
             spider("crystal_frame_spider", CRYSTAL_R + CRYSTAL_CLEAR, T063, Z_FRAME),
             crystal(), dial_sticker()]
    parts += gears() + hands() + arbors() + hardware() + electronics() + crown_cap() + hinge()
    return parts


# Intentional contacts the interference check should ignore (pairs of name prefixes)
ALLOWED = [
    ("screw_floor", "standoff_bay"), ("screw_top", "standoff_hand"),
    ("standoff_gear", "standoff_bay"), ("standoff_hand", "standoff_gear"),
    ("crown_plunger", "crown_"),
    ("magnet_lid", "lid_overlay"), ("module_sockets", "motor_X27"),   # X27 pins inside their sockets
]

def lid_open_location(angle: float = LID_REST_ANGLE) -> cq.Location:
    ax, az = HINGE_AXIS
    return (cq.Location(cq.Vector(ax, 0, az)) * cq.Location(cq.Vector(), cq.Vector(0, 1, 0), angle)
            * cq.Location(cq.Vector(-ax, 0, -az)))


def summary() -> dict:
    return dict(
        case_outer=f"{UPPER_OUTER.bounds[2] * 2:.1f} × {UPPER_OUTER.bounds[3] * 2:.1f} mm",
        body_height=round(Z_TOP, 2), closed_height=round(Z_TOP + LID_H, 2),
        knob_protrusion=round(R_KNOB + knob_tip_r() - UPPER_OUTER.bounds[2], 2),
        levels=[round(z, 3) for z in LEVELS], hands=Z_HANDS, cap=round(Z_CAP, 3),
        crystal_clearance=round(Z_FRAME - (Z_CAP + T040), 3),
        x27_body=(round(X27_BODY_TOP - X27_BODY_H, 2), round(X27_BODY_TOP, 2)),
        as5600_magnet_gap=round(Z_P1 - SENSOR_MAGNET_DROP - SENSOR_MAGNET_H - (Z_CARRIER_TOP + L.MODULE_LIFT + 3.1), 2),
        lid_open_angle=LID_OPEN_ANGLE,
        hinge_fabrication_hold=HINGE_REFERENCE_NOTE,
        needle_ratio=Z_MOTOR / Z_NEEDLE, knob_turns_per_rev=Z_SENSOR / Z_KNOB,
    )
