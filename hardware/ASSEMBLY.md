# Assembly

This is an unbuilt prototype. The hinge is one purchased brass hinge held by flush screws, not solder.
Thumbwheel laminations are bolted together too. The movement and crown still require
small bench-soldered joints; electrical soldering is
also required. Read the fabrication hold and joint status below before buying parts.

**Conventions.** "Up" is toward the dial. Positions along a shaft are measured from the
**bottom face of P1** (the movement base plate). Every dimension comes from
[`cad/design.py`](cad/design.py). If you change the design, re-run `cad/build.py` and
update this sheet.

| Level | Height above P1 bottom | What lives there |
|---|---|---|
| P1 (base plate) | 0 – 1.6 | tube bushings for every shaft |
| L0 | 2.1 | hand-I gear + sensor-I gear; bottom of all knob stacks |
| L1 | 4.1 | hand-II gear + sensor-II gear |
| L2 | 6.1 | hand-III gear + sensor-III gear (knob stacks end at 7.18) |
| L3 | 8.1 | needle gear + X27 motor gear |
| P2 (dial plate) | 9.6 – 11.2 | top bushings, cannon, dial sticker |

Above the dial (measured from the top of P2): cannon tip +0.35, needle +0.45, hand III +1.61,
hand II +2.98, hand I +4.34, cap +5.36 (top of cap +6.38). The crystal's underside sits at +7.0.

## Tools and consumables

- Soldering iron (fine chisel tip, ≥60 W) **and** a small butane torch. Brass sinks heat.
- Soft solder (lead-free Sn96/Ag4 or 60/40), liquid flux for brass (e.g. Harris Stay-Clean),
  and a solder-paste syringe for the small joints.
- Needle files, 600–2000 grit paper, and a pin vise with a set of small drills (to open a gear
  bore that comes out tight). A sharp **90° countersink** for the seven external M2 screws.
- Tube cutter (K&S #296) or a jeweller's saw and mitre box for the K&S stock.
- 1.8 mm and 2.4 mm drills for transfer-drilling the hinge, and M1.6/M2 screwdrivers.
- Tweezers, a small vise, Kapton tape, 5-minute epoxy, Loctite 638 (or any retaining compound),
  clock oil (e.g. Moebius 8030).
- Multimeter. A USB-C cable for the first flash.

## 0. Before you order

**Hinge fabrication hold.** The purchased hinge in CAD is a reference, not a verified supplier
model. Guden's [BR05050404-72 drawing](https://www.guden.com/itemdetail/BR05050404-72) specifies
.040" sheet, a .091" pin, .500" knuckle pitch and 1.060" open width, but not the curl/leaf offset
or knuckle-slot clearance. Obtain a sample or a complete drawing first. Confirm the five-knuckle
cut, retained pin and trimmed leaf heights; update the CAD pivot and mounting stack to match
before ordering hinge-related laser parts or drilling the shells. The current model's 0.1 mm
curl and slot clearances are assumptions, not vendor tolerances. The opening limit is set by
the hinge's own leaves closing on each other (§8), so the real curl also sets that angle.

1. Generate the dial with Myth Made's symbols (see [`dial/README.md`](dial/README.md)). Print
   `dial/local/dial_print_letter.pdf` at 100 % on plain paper and check the 50 mm bar.
   It confirms the printer scale before you buy sticker stock.
2. Upload the files in `out/sendcutsend/` and check the instant quote (see *Ordering* in
   [README.md](README.md)).

## 1. Prepare the laser-cut parts

1. Deburr and flatten everything. Rub each face on 600 grit on glass, then finer.
   Gears only need their faces deburred; don't round the teeth.
2. **Fit the bushings.** No shaft runs in a laser-cut hole. Each plate hole takes a
   1.6 mm piece of K&S tube (§2), and the next K&S size slides inside it with about 0.08 mm
   of play, so every shaft is located precisely whatever the laser tolerance.
   - Screw P1 and P2 together on their four gear standoffs. This keeps the two plates' holes
     aligned.
   - Rub pencil graphite on the shafts and arbor I so nothing sticks to them.
   - Put a dab of Loctite 638 on each bushing and push it into its hole, flush with the plate.
     The plate holes are drawn 0.1 mm over the tube, so they go in by hand.
   - Slide the shafts through both plates while the 638 is wet: the three sensor and three
     knob shafts through each pair of bushings, and arbor I into P1's centre bushing. This
     lines the pairs up with each other. Spin each shaft once, then let it cure (about 1 hour).
3. Test-fit every gear on its rod or tube. Gear bores are drawn only 0.08 mm over the stock, so
   each gear runs centred. If one won't slide on, turn the matching drill through it by hand.
   Everything that doesn't affect gear mesh (hands, crown, hinge, case holes) is drawn with
   more room and goes on as cut.
4. **Flush case screw seats, after forming.** The supplier DXFs and `__formed.step` files
   retain plain **Ø2.7 mm through-holes**. On the outside of the lower tray, countersink
   its three floor holes; on the outside of the upper shell, countersink its four top holes.
   Use **90° DIN 963 slotted countersunk M2 brass screws**, not raised/oval countersunk or
   larger-headed ISO alternatives. Work by hand with the thin sheet firmly supported, and
   test the actual screw frequently until its head is flush, not below the surrounding face.
   The nominal head is Ø3.8 mm: the countersink is **0.55 mm deep**, leaving about **0.47 mm**
   of straight through-hole in the 1.016 mm sheet. Do not cut through that remaining land.
   The assembly and individual-part CAD show the finished seats; the supplier gets the
   unmachined bent blanks. Clean off chips and deburr before fitting any electronics.

## 2. Cut the K&S stock

Cut, deburr and check each piece against the cut list (also in `out/stock_and_bought_parts.csv`):

| Part | Stock | Length |
|---|---|---|
| Arbor I (top hand) | 3/32" rod | 17.6 mm |
| Arbor II | 1/8" tube | 11.1 mm |
| Arbor III | 5/32" tube | 7.7 mm |
| Needle arbor | 3/16" tube | 4.4 mm |
| Cannon | 7/32" tube | 1.95 mm |
| Bushings ×12 | 5/32" tube | 1.6 mm each (sensor and knob shafts, P1 and P2) |
| Bushing ×1 | 1/8" tube | 1.6 mm (arbor I, P1 centre) |
| Sensor shafts ×3 | 1/8" rod | 11.5 mm each (0.3 mm proud below P1 for the magnet) |
| Knob shafts ×3 | 1/8" rod | 11.2 mm each |
| Sensor sleeves | 5/32" tube | 2.5 mm (II), 4.5 mm (III); I uses a 0.5 mm M3 shim washer |
| Knob upper sleeves ×3 | 5/32" tube | 2.42 mm |
| Knob lower spacers ×3 | M3 shim washer | 0.5 mm |
| Crown plunger | 3/32" rod | 6.7 mm |
| Crown collar | 5/32" tube | 1.5 mm |
| Hinge body backing | .063" brass sheet | 63.5 × 11 mm, laser-cut |
| Hinge lid backing | .063" brass strip | 63.5 × 5 mm, hand-cut (too narrow for the laser service) |

## 3. Sub-assemblies

### Mechanical joint status

Prefer removable mechanical joints wherever practical, rather than automatically replacing
solder with permanent adhesive. This revision addresses the hinge, not every joint:

| Joint | Current construction |
|---|---|
| Hinge knuckles and pin | One purchased formed hinge; no home-soldered tube knuckles. Supplier fit is still on hold above. |
| Hinge to body/lid | Flush countersunk screws from outside, nuts on backing strips inside; removable. |
| Opening stop | None added: the hinge leaves close on each other just past flat. |
| Knob laminations | Three through-bolts per wheel; four upper layers removable. Only the base layer is soldered to its shaft. |
| Knob base-to-shaft, sensor gears, hand/needle gears, crown | Still bench-soldered as described below; removable replacements have **not** been designed or checked yet. |
| Cannon | Still soldered into P2. Its existing 0.3 mm nominal bore clearance must not simply be relabelled as a retaining-compound fit. |
| Bushings, hands, magnets | Existing retaining compound/epoxy joints remain; they are not claimed to be mechanically removable. |

Do not put ordinary radial set screws directly into the thin nested hand tubes: denting them
can bind the adjacent arbor. A removable movement conversion needs properly supported hubs
and axial retention checked against the small vertical clearances.

**Knob wheels (×3).** Hand-countersink the three Ø2.4 mm clamp holes on the **underside only**
of each `knob_*_31T_base`, 90°, for Ø3.8 mm DIN 963 heads. Nominal depth is 0.7 mm, leaving
0.316 mm of straight bore. Solder **only the base layer** to its shaft, with its bottom face
**2.1 mm** above the shaft bottom; keep solder out of the three clamp holes.

Deburr the four `knob_*_31T_layers` and slide them onto that shaft. Align all five sets of teeth
against a spare 36T gear, then clamp with **three M2 countersunk through-screws and M2 nuts**.
No solder or adhesive belongs between the layers. Shorten M2×8 DIN 963 screws to **7.0 mm
including the head**, deburr, and check the nuts run freely. The lower heads must be flush;
the nuts are above the stack. The nominal screw ends project 0.32 mm beyond the nuts and
clear P2 by 0.5 mm. Check these clearances and all three clamp screws on the prototype;
do not substitute taller nuts or leave screws untrimmed. This removes twelve inter-layer
solder joints across the three wheels, but does not yet make their shaft attachment removable.

**Sensor shafts (×3).** Solder each 36T sensor gear at its level: I at 2.1 mm, II at 4.1 mm,
III at 6.1 mm above the bottom end. The magnet goes on later (§5), once the shaft
is in its bearings, because it's wider than the bearing hole.

**Arbors.** Solder the hand gears flush with the arbor *bottom* ends: hand-I gear on the
3/32" rod at 2.1 mm above its bottom end, hand-II gear on the bottom of the 1/8" tube, and
hand-III gear on the bottom of the 5/32" tube. Solder the 19T needle gear to the bottom of
the 3/16" tube. Don't let solder wick into the bores. Use a drop of paste and the iron
touched to the gear, not the tube.

**Cannon.** Solder the 7/32" cannon into P2's centre hole, flush with P2's underside so it
stands 0.35 mm proud of the top. The 3/16" needle arbor slides inside it (a K&S telescoping fit); keep solder out of the bore.

**Motor gear.** The 38T gear sits on the X27's **Ø1 output shaft**, with its bottom face
5.5 mm above the motor's front face (level L3). Press it on with a drop of Loctite 638 and
trim the shaft 0.3 mm above the gear. Don't push hard on the shaft; support it from behind.

**Crown.** Solder the three scalloped `crown_cap_disc` pieces onto one end of the plunger as a
little crown. The collar goes on later, from inside the case.

**Purchased hinge (after releasing the hold in §0).** Request one 63.5 mm five-knuckle
length of the Guden brass hinge, with both end knuckles on the fixed leaf and the pin
retained by the supplier. Nominal trimmed heights from the pivot are 13 mm for the body leaf
and 6.4 mm for the lid leaf. Nothing else is fitted outside the case: there is no separate
stop. The lid opens flat and a little beyond, until the two leaves close on each other.

## 4. Carrier PCB and bench test (before anything goes in the case)

1. Populate the carrier per [`pcb/README.md`](pcb/README.md#assembly-order): resistors, C1, pin
   headers, then the module sockets, using each module as its own soldering jig. Leave the
   X27 sockets **unsoldered** for now.
2. Work through the [bring-up checklist](pcb/README.md#bring-up-checklist) one module at a
   time. Flash the firmware (see [`../firmware/README.md`](../firmware/README.md)) once the
   ProS3 is in, then check `hands`, `home`, `sweep`, `tone` and `rec` from the serial console,
   probing the test pads if anything misbehaves. Turning a magnet over each AS5600 should walk
   through all 36 symbols.
3. Run `wifi` and **write down the setup-portal password** it prints. Once the board is
   inside the case you'll need it.

## 5. Movement

1. **Set the motor mesh (carrier as a jig).** Stand the three **M2×12 F-F** bay standoffs on the
   carrier, each held by an M2×8 countersunk screw from below through a 2.5 mm nylon spacer and
   the board. For this bench jig without the tray, use temporary M2 washers under the heads
   so their cones do not wedge into the nylon spacers.
   At the top-right corner (no bay post) an M2 nut under P1 takes the gear standoff instead.
   The floor isn't fitted yet, so the screws go a little deeper. Lay P1 on top and screw the
   four **M2×8 M-F** gear standoffs through P1 into them. The X27, plugged into its loose
   sockets, pokes up through P1's slot. Nest arbors I, II and III and the needle arbor (with its
   19T gear) in the centre bearing, as in step 3. Slide the X27 along the slot until the 38T motor gear meshes with a hair of
   backlash. Hold it there, turn the stack over and solder the eight X27 socket pins. Then
   undo the three floor screws and lift P1 + standoffs off the carrier. The X27 stays plugged in.
2. Stand P1 on its three bay standoffs on the bench. They hold it 12 mm up, so the parts below
   P1 hang free.
3. Drop in, in this order:
   - arbor I (3/32" rod into the centre bearing);
   - arbor II, then arbor III, then the needle arbor, sliding each over the last;
   - the three sensor shafts, each with its sleeve or washer below the gear;
   - the three knob shafts, each with a 0.5 mm washer below the wheel and a 2.42 mm sleeve above it.
4. Lower P2 over the cannon and onto every shaft tip. This is the fiddly watchmaker's moment:
   start from one side and coax each tip into its hole with tweezers. Screw the four **M2×6 M-F**
   standoffs through P2 into the gear standoffs.
5. From underneath, epoxy a Ø6×2.5 diametric magnet centred on the bottom end of each sensor
   shaft (the shaft pokes 0.3 mm below P1, so the magnet clears the plate).
6. Check that every knob turns its hand arbor smoothly and that the X27 gear meshes with the needle gear.
   Add a drop of clock oil to each bearing.

## 6. Dial and hands

1. Apply the dial sticker to P2, centred on the cannon. The cut-line circle ID is Ø58 mm.
   Line up **Hourglass** with the top (12 o'clock) knob.
2. Darken the three framing hands (brass black or a blued look) and polish the copper needle.
3. Press on, in order, each with a dot of Loctite 638 on its arbor, all pointing at Hourglass:
   the needle at +0.45, hand III at +1.61, hand II at +2.98, hand I at +4.34, then the cap.
   Check there is clearance between every hand. Calibration later removes any angular error.

## 7. Case

1. **Crown.** Push the crown plunger in from outside through the lower tray's top-right chamfer
   hole and solder the 1.5 mm collar on inside, leaving 0.3 mm of play.
2. **Lower tray.** Line the floor with one layer of Kapton. Put the three nylon spacers over the
   floor holes and lower the populated carrier straight in: U7's receptacle lines up with the wall
   opening and the crown switch drops in just behind the plunger. Plug in the
   battery and connect the mic, speaker and reed leads to J4, J5 and J6. Press the crown: you
   should feel the switch click.
3. Lower the movement straight down onto the carrier. The X27 and its gear rise up through
   P1's slot and the motor gear slides into mesh with the needle gear (rock the needle a hair
   if the teeth butt). Fix it with three **M2×8 countersunk** screws from under the floor, through the
   spacers and board into the bay standoffs.
4. **Upper shell (do this with the shell upside down).**
   - Glue a ring of speaker cloth under the grille slots.
   - Epoxy the body closure magnet (top-left, between grille and wall) and the reed switch
     (lower-right) to the underside of the top face.
   - Drop the crystal into the frame spider, then lay the seat spider on top.
5. **Body hinge, before fitting the shell over the movement.** Jig the checked purchased
   hinge against the right wall with its pivot at the CAD datum. Transfer-drill the four
   Ø2.4 mm holes through the fixed leaf and formed wall, using the laser-cut backing strip as
   a guide (holes at Y = ±9.5 and ±25.4 mm, 8 mm below the top edge). The supplier shell blank
   deliberately has no hinge holes. Countersink the **leaf only**, 90°, for the Ø3.8 mm heads.
   Fit four **M2×6 DIN 963** countersunk screws from outside, with the backing strip and four
   M2 nuts inside. The heads must finish flush with the leaf. P2 has a hinge-side relief for
   the backing strip and nuts.
6. Lower the shell over the movement. The thumbwheels must pass through the three notches.
   Fix it with four **M2×6 countersunk** screws through the top face.
   Countersunk lengths include the head. These give about **2.37 mm** of thread engagement
   in the hand standoffs; the bottom M2×8 screws engage about **2.88 mm** in the bay standoffs.
   Check the actual standoffs' usable thread depths before tightening: each screw must clamp
   the stack without bottoming out, and all seven heads must finish flush.

### What holds the two shells together

The overlapping rim is an **alignment skirt with 0.45 mm radial clearance**, not a press-fit
retainer. The fastener path is:

**Four top screws → hand standoffs → P2 → gear standoffs → P1 → three bay standoffs →
three bottom screws through the PCB and nylon spacers.**

At the crown corner, the gear standoff is secured by an **M2 nut under P1**, instead of a
fourth bay standoff, to leave room for the crown switch. That corner is connected through
the plates to the other three floor mounts; it has no direct post to the floor.

For servicing, remove the four top screws and lift off the upper shell and its hinged lid;
leave the three bottom screws fitted unless removing the movement. No pulling against a
friction fit is intended. Tighten the stack joints snugly without stripping the small brass
threads, and verify that the rim slides on freely before tightening the top screws.

The short hex posts and clamped plates are intended to resist sideways motion, but the
CAD checks establish fit, not structural stiffness. On the prototype, check for plate
movement or gear binding under gentle lateral loads and crown presses, especially at the
unsupported crown corner. Do not rely on the clearance skirt as rigid bracing.

## 8. Lid

1. **Lid hinge first.** Close and align the lid. Transfer-drill its two Ø1.8 mm mounting holes
   through the checked moving leaf and wall, nominally at Y = ±12.7 mm and 3.5 mm above the
   seam. Hand-countersink the **hinge leaf only**, 90°, for the Ø3.2 mm heads of two
   **M1.6×6 DIN 963** screws. Their heads must be flush: when the lid is fully open the
   leaves close face to face, and a proud head would stop it early. Nominal seat depth is
   0.7 mm, leaving 0.316 mm of straight bore.
2. Fit the hand-cut **63.5 × 5 × 1.6 mm lid backing strip** inside, between 0.2 and 5.2 mm
   above the seam, then the M1.6 nuts. Keep it below the lid's inside bend and check tool
   access before attaching the overlay. Nominal screw projection beyond each nut is 1.07 mm.
3. Epoxy the pierced overlay inside the lid, keeping the hinge nuts and backing strip clear.
   Epoxy the two lid magnets into the overlay's holes, poles attracting the body magnet.
   The purchased hinge pin is already retained; no peening or glue is needed at assembly.
4. Open the lid through its full travel. It passes flat (180°) and stops a little beyond, about
   200° with the modelled hinge, when the two leaves close face to face. On a table the lid's far
   edge comes to rest on the tabletop first. Check nothing binds anywhere in the travel and the
   screw heads don't touch. This hinge has not yet been physically prototyped.

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
| A knob is stiff | Check the base is square on its shaft, the bolted layers are aligned, clamp screws are flush below and clear P2 above, and sleeves aren't too long; the case notch leaves 1.2 mm each side. |
| A hand drags its neighbour | Add a 0.1 mm shim between the gears, or ease the tube's fit. |
| Hand reads the wrong symbol near one spot | Check the AS5600 is fully seated in its socket and level on its rest post (chip about 1.1 mm under the magnet), then recalibrate. |
| Something electrical misbehaves | Lift the movement out and probe the labelled test pads (see the [bring-up checklist](pcb/README.md#bring-up-checklist)). Any module can be pulled and swapped. |
| The needle buzzes at the wrong end on wake | Set `MOTOR_PHASE_DIR = -1` in `firmware/src/config.h`. |
| Lid doesn't wake it | Move the reed up or nearer the lid magnet, or use a stronger magnet. |
