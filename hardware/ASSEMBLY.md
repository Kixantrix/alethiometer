# Assembly

Allow two or three evenings. It's watchmaking-lite: soft-soldering small brass parts,
setting arbors into plates, and some fine wiring. Read it through once before starting.

**Conventions.** "Up" is toward the dial. Positions along a shaft are measured from the
**bottom face of P1** (the movement base plate). Every dimension comes from
[`cad/design.py`](cad/design.py). If you change the design, re-run `cad/build.py` and
update this sheet.

| Level | Height above P1 bottom | What lives there |
|---|---|---|
| P1 (base plate) | 0 – 1.6 | bearings for every shaft |
| L0 | 2.1 | hand-I gear + sensor-I gear; bottom of all knob stacks |
| L1 | 4.1 | hand-II gear + sensor-II gear |
| L2 | 6.1 | hand-III gear + sensor-III gear (knob stacks end at 7.18) |
| L3 | 8.1 | needle gear + X27 motor gear |
| P2 (dial plate) | 9.6 – 11.2 | top bearings, cannon, dial sticker |

Above the dial (measured from the top of P2): cannon tip +0.35, needle +0.45, hand III +1.61,
hand II +2.98, hand I +4.34, cap +5.36 (top of cap +6.38). The crystal's underside sits at +7.0.

## Tools and consumables

- Soldering iron (fine chisel tip, ≥60 W) **and** a small butane torch. Brass sinks heat.
- Soft solder (lead-free Sn96/Ag4 or 60/40), liquid flux for brass (e.g. Harris Stay-Clean),
  and a solder-paste syringe for the small joints.
- Needle files, 600–2000 grit paper, a pin vise with **1/8" (3.18 mm)** and **3/32" (2.38 mm)**
  drills to ream bearing holes, a 0.5 mm drill.
- Tube cutter (K&S #296) or a jeweller's saw and mitre box for the K&S stock.
- Tweezers, a small vise, Kapton tape, 5-minute epoxy, Loctite 638 (or any retaining compound),
  clock oil (e.g. Moebius 8030).
- Multimeter. A USB-C cable for the first flash.

## 0. Before you order

1. Generate the dial with Myth Made's symbols (see [`dial/README.md`](dial/README.md)). Print
   `dial/local/dial_print_letter.pdf` at 100 % on plain paper and check the 50 mm bar.
   It confirms the printer scale before you buy sticker stock.
2. Upload the files in `out/sendcutsend/` and check the instant quote (see *Ordering* in
   [README.md](README.md)).

## 1. Prepare the laser-cut parts

1. Deburr and flatten everything. Rub each face on 600 grit on glass, then finer.
   Gears only need their faces deburred; don't round the teeth.
2. **Ream the bearing holes.** P1 and P2 have 3.30 mm holes for the 1/8" shafts and
   P1 has a 2.50 mm centre hole for the 3/32" arbor. Laser tolerance is ±0.13 mm, so run
   the matching drill through each hole by hand until the rod turns freely without
   rattling.
3. Test-fit every gear on its rod or tube. Holes are drawn 0.05 mm over the stock diameter
   so solder can wick in.

## 2. Cut the K&S stock

Cut, deburr and check each piece against the cut list (also in `out/stock_and_bought_parts.csv`):

| Part | Stock | Length |
|---|---|---|
| Arbor I (top hand) | 3/32" rod | 17.6 mm |
| Arbor II | 1/8" tube | 11.1 mm |
| Arbor III | 5/32" tube | 7.7 mm |
| Needle arbor | 3/16" tube | 4.4 mm |
| Cannon | 7/32" tube | 1.95 mm |
| Sensor shafts ×3, knob shafts ×3 | 1/8" rod | 11.2 mm each |
| Sensor sleeves | 5/32" tube | 2.5 mm (II), 4.5 mm (III); I uses a 0.5 mm M3 shim washer |
| Knob upper sleeves ×3 | 5/32" tube | 2.42 mm |
| Knob lower spacers ×3 | M3 shim washer | 0.5 mm |
| Crown plunger | 3/32" rod | 10.5 mm |
| Crown collar | 5/32" tube | 2.0 mm |
| Hinge knuckles ×5 | 3/16" tube | 11.6 mm |
| Hinge pin | 5/32" rod | 60 mm |

## 3. Sub-assemblies (bench soldering)

**Knob wheels (×3).** Thread five `knob_*_31T` layers onto a 1/8" rod. Align the teeth by
meshing them all against one spare 36T gear held flat on the bench. Then clamp and
sweat-solder the stack with paste between the layers, and file the knurl flush. Slide each
stack onto its knob shaft at **2.1 mm** above the shaft bottom and solder it.

**Sensor shafts (×3).** Solder each 36T sensor gear at its level: I at 2.1 mm, II at 4.1 mm,
III at 6.1 mm above the bottom end. Epoxy a Ø6×2.5 mm **diametric** magnet centred on the
bottom end face, with its face square to the shaft.

**Arbors.** Solder the hand gears flush with the arbor *bottom* ends: hand-I gear on the
3/32" rod at 2.1 mm above its bottom end, hand-II gear on the bottom of the 1/8" tube, and
hand-III gear on the bottom of the 5/32" tube. Solder the 19T needle gear to the bottom of
the 3/16" tube. Don't let solder wick into the bores. Use a drop of paste and the iron
touched to the gear, not the tube.

**Cannon.** Solder the 7/32" cannon into P2's centre hole, flush with P2's underside so it
stands 0.35 mm proud of the top. Ream the bore to slide on the 3/16" tube.

**Motor gear.** Trim the X27.168 shaft so it ends 0.3 mm above the 38T gear's top face.
Put the gear on the **Ø2 collar** of the X27 shaft, about 0.5 mm above the housing, and fix
it with Loctite 638. If your motor's Ø2 collar doesn't turn with the shaft, open the gear hole
to fit the Ø1 shaft and raise the motor 2 mm with a shim instead.

**Crown.** Solder the three scalloped `crown_cap_disc` pieces onto one end of the plunger as a
little crown. The collar goes on later, from inside the case.

**Hinge.** Pin all five knuckles in a row on the hinge pin with 0.5 mm paper spacers. Lay the two
comb leaves against them, so each knuckle sits on its own tab tangent along the tab centre-line.
Solder knuckles 1, 3, 5 to the body leaf and 2, 4 to the lid leaf. Remove the paper spacers.

## 4. Electronics bench test (before anything goes in the case)

1. Flash the firmware over the ProS3's own USB-C (see [`../firmware/README.md`](../firmware/README.md)).
2. Wire everything per [WIRING.md](WIRING.md) on the bench with the X27 and one AS5600.
3. In the serial console check `hands`, `home`, `sweep`, `rec`, `tone`. Turning a magnet over
   the AS5600 should walk through all 36 symbols.
4. Run `wifi` and **write down the setup-portal password** it prints. Once the board is
   inside the case you'll need it.

## 5. Movement

1. Screw the four **M2×8 M-F** standoffs into the four **M2×8 F-F** bay standoffs through P1.
   The male threads pass through P1.
2. Fit the X27 through P1's Ø31 cutout so the motor gear sits at L3 (8.1 mm). Fillet it to P1
   with epoxy and let it cure.
3. With P1 flat on the bench, drop in, in this order:
   - arbor I (3/32" rod into the centre bearing);
   - arbor II, then arbor III, then the needle arbor, sliding each over the last;
   - the three sensor shafts, each with its sleeve or washer below the gear;
   - the three knob shafts, each with a 0.5 mm washer below the wheel and a 2.42 mm sleeve above it.
4. Lower P2 over the cannon and onto every shaft tip. This is the fiddly watchmaker's moment:
   start from one side and coax each tip into its hole with tweezers. Screw the four **M2×6 M-F**
   standoffs through P2 into the gear standoffs.
5. Check that every knob turns its hand arbor smoothly and that the X27 gear meshes with the needle gear.
   Add a drop of clock oil to each bearing.

## 6. Dial and hands

1. Apply the dial sticker to P2, centred on the cannon. The cut-line circle ID is Ø58 mm.
   Line up **Hourglass** with the top (12 o'clock) knob.
2. Darken the three framing hands (brass black or a blued look) and polish the copper needle.
3. Press on, in order, each with a dot of Loctite 638 on its arbor, all pointing at Hourglass:
   the needle at +0.45, hand III at +1.61, hand II at +2.98, hand I at +4.34, then the cap.
   Check there is clearance between every hand. Calibration later removes any angular error.

## 7. Case

1. **Lower tray.** Lay out the bay modules (WIRING.md "Where things go") and wire them. Place
   the AS5600 boards using P1's bearing holes as the template. Lower the movement in so the
   bay standoffs land on the floor holes, and fix it with four **M2×4** screws from below.
2. **Upper shell (do this with the shell upside down).**
   - Glue a ring of speaker cloth under the grille slots.
   - Epoxy the body closure magnet (top-left, between grille and wall) and the reed switch
     (lower-right) to the underside of the top face.
   - Push the crown plunger in from outside through the chamfer hole and solder the collar on
     the inside, leaving 0.3 mm of play.
   - Drop the crystal into the frame spider, then lay the seat spider on top.
3. Solder the **body hinge leaf** to the shell's right wall: its top edge level with the top face,
   centred on the wall.
4. Lower the shell over the movement. The thumbwheels must pass through the three notches and
   the USB-C receptacle into its slot. Fix it with four **M2×5** screws through the top face.

## 8. Lid

1. Epoxy (or sweat-solder) the pierced overlay inside the lid. Epoxy the two lid magnets into the
   overlay's holes, poles attracting the body magnet.
2. Close the lid on the body. Align it, then solder the **lid hinge leaf** to the lid's right wall.
3. Peen or epoxy the hinge-pin ends.

## 9. Finish and first run

1. Polish, then protect the case with Renaissance Wax or a clear lacquer. Unprotected brass will patina.
2. Charge through the side USB-C port.
3. Triple-click the crown to open the **Alethiometer** Wi-Fi portal. Join it with the password
   you noted in §4, then enter your Wi-Fi, API URL and device key.
4. Click the crown five times to **calibrate**: set all hands to Hourglass and press, set all
   hands to Moon and press, then jog the needle onto Hourglass with knob I and press.
5. Hold the crown, ask your question, release, and watch the needle.

## Troubleshooting

| Symptom | Fix |
|---|---|
| A knob is stiff | Ream that shaft's P1/P2 holes; check the wheel isn't rubbing the case notch. |
| A hand drags its neighbour | Add a 0.1 mm shim between the gears, or ease the tube's fit. |
| Hand reads the wrong symbol near one spot | Check the AS5600 chip is centred under its magnet and 0.5–1 mm away, then recalibrate. |
| The needle buzzes at the wrong end on wake | Set `MOTOR_PHASE_DIR = -1` in `firmware/src/config.h`. |
| Lid doesn't wake it | Move the reed up or nearer the lid magnet, or use a stronger magnet. |
