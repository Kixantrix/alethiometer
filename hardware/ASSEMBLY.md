# Assembly

This is an unbuilt prototype. The hinge is one purchased brass hinge held by flush screws.
The thumbwheels are bought solid gears, and every arbor, shaft, bushing and the crown come
finished from a CNC-turning kit, so nothing in the movement is cut, measured or soldered: each
part is pushed on until it stops, with a drop of Loctite. The only soldering is electrical (the
carrier PCB and its leads). Read the fabrication hold and joint status below before buying parts.

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
hand II +2.34, hand I +3.07, cap +3.46 (top of cap +4.47). The crystal's underside sits at +6.0.
You never measure these: every height is set by a shoulder or a flush end on the turned parts.

## Tools and consumables

The full tool list, with the step that uses each tool, is in
[BOM.md §G](BOM.md#g-tools); consumables are in [BOM.md §E](BOM.md#e-dial-finish-and-consumables).
The one to get right is the countersink: a **90° zero-flute** cutter, not an 82° one.

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
2. **Fit the bushings.** No shaft runs in a laser-cut hole. Each plate hole takes a turned
   bushing exactly as thick as the plate (§2), and its shaft slides inside it with about 0.08 mm
   of play, so every shaft is located precisely whatever the laser tolerance.
   - Screw P1 and P2 together on their four gear standoffs. This keeps the two plates' holes
     aligned.
   - Rub pencil graphite on the shafts and arbor I so nothing sticks to them.
   - Stand the plates on a flat surface. Put a dab of Loctite 638 on each bushing and drop it
     into its hole until it touches the surface: it is then flush both sides. The plate holes
     are drawn 0.1 mm over the bushing, so they go in by hand.
   - Slide the shafts through both plates while the 638 is wet: the three sensor and three
     knob shafts through each pair of bushings, and arbor I into P1's centre bushing. This
     lines the pairs up with each other. Spin each shaft once, then let it cure (about 1 hour).
3. Test-fit every gear on its arbor or shaft. Gear bores are drawn only 0.08 mm over the
   turned diameter, so each gear runs centred. If one won't slide on, turn the matching drill
   through it by hand.
   Everything that doesn't affect gear mesh (hands, crown, hinge, case holes) is drawn with
   more room and goes on as cut.
4. **Flush case screw seats, after forming.** The supplier DXFs and `__formed.step` files
   retain plain **Ø2.7 mm through-holes**. On the outside of the lower tray, countersink
   its three floor holes; on the outside of the upper shell, countersink its four top holes.
   Use **90° DIN 963 slotted countersunk M2 brass screws**, not raised/oval countersunk or
   larger-headed ISO alternatives. Work by hand with the thin sheet firmly supported, and
   test the actual screw frequently until its head is flush, not below the surrounding face.
   The holes are cut at the right starting size; countersink each one until its rim measures
   **Ø3.8–3.9 mm** (about 0.55 mm deep, leaving about **0.47 mm** of straight hole in the
   1.016 mm sheet), then drop a screw in and check it sits flush. Light pressure, a few turns
   at a time: the cutter centres itself in the existing hole. Stop as soon as the head is flush.
   The assembly and individual-part CAD show the finished seats; the supplier gets the
   unmachined bent blanks. Clean off chips and deburr before fitting any electronics.

## 2. Check the turned-parts kit

Nothing to cut. The kit arrives finished; [`out/turned/README.md`](out/turned/README.md) is its
drawing (also `out/turned/turned_parts.csv`). Unpack it onto a tray and check each part's
length with calipers against that table, so you know which is which:

| Part | Qty | What sets its position |
|---|---|---|
| `arbor_I` (stepped rod) | 1 | Its collar rests on P1's centre bushing; gear I sits on the collar; hand I sits on the top shoulder; the cap is flush with the top |
| `arbor_II`, `arbor_III`, `arbor_needle` (plain tubes) | 1 each | Gear flush with the bottom end, hand flush with the top end |
| `cannon` (flanged tube) | 1 | Flange on P2's top face |
| `bushing_1_8`, `bushing_5_32`, `bushing_3_16` | 1, 6, 6 | Flush with both faces of the plate |
| `shaft_sensor_I/II/III` | 1 each | Collar on the P1 bushing (0.5, 2.5 and 4.5 mm tall: the gear sits on it) |
| `magnet_cup` | 3 | Pushed onto the sensor shaft's bottom tip until it stops |
| `shaft_knob` | 3 | Collar on the P1 bushing; the thumbwheel sits on it |
| `sleeve_knob` | 3 | Slides down onto the thumbwheel |
| `crown_turned` | 1 | E-clip in its groove inside the wall |

The **hinge body backing** (.063" brass, 63.5 × 11 mm) comes laser-cut with the SendCutSend order.

## 3. Sub-assemblies

### Mechanical joint status

Prefer removable mechanical joints wherever practical, rather than automatically replacing
solder with permanent adhesive. Current construction of every joint:

| Joint | Current construction |
|---|---|
| Hinge knuckles and pin | One purchased formed hinge; no home-soldered tube knuckles. Supplier fit is still on hold above. |
| Hinge to body/lid | Flush countersunk screws from outside; nuts on a backing strip (body) or washers (lid) inside; removable. |
| Opening stop | None added: the hinge leaves close on each other just past flat. |
| Thumbwheels | One bought solid gear each, on the knob-shaft collar, Loctite 638. |
| Sensor, hand and needle gears | On a turned collar or flush with a tube end, Loctite 638 (no solder). |
| Cannon | Flanged; pushed into P2's 0.1 mm-clearance hole, Loctite 638. |
| Crown | One turned piece, held by a DIN 6799 E-clip; removable. |
| Bushings, hands, magnets, magnet cups | Loctite 638 / epoxy; not designed to be taken apart. |

Do not put ordinary radial set screws directly into the thin nested hand tubes: denting them
can bind the adjacent arbor. A removable movement conversion needs properly supported hubs
and axial retention checked against the small vertical clearances.

Every gear goes on the same way: a drop of Loctite 638 on the shaft, slide the gear down until it
stops, wipe off the excess and keep it out of any bore. Leave each one an hour before handling.

**Thumbwheels (×3).** Each is one bought brass gear (module 0.8, 26 teeth, 5 mm wide, 4 mm bore;
see BOM.md §C). Slide it down a `shaft_knob` until it sits on the collar. No layers to align.

**Sensor shafts (×3).** Slide each 32T sensor gear down its shaft until it sits on the collar
(I has the 0.5 mm collar, II 2.5 mm, III 4.5 mm). The magnet cup goes on later (§5), once the
shaft is in its bearings, because it's wider than the bearing hole.

**Arbors.** Stand arbors II and III and the needle arbor on end on a sheet of glass. Slide each
gear down until it touches the glass: it is then flush with the bottom end. Hand-II gear on
`arbor_II`, hand-III gear on `arbor_III`, the 17T needle gear on `arbor_needle`. The hand-I gear
goes on `arbor_I` from the thin top end and down onto its collar.

**Cannon.** Push the cannon into P2's centre hole from the top until its flange sits on the
plate, with a little Loctite 638 on the outside only. The needle arbor runs inside it.

**Motor gear.** The 34T gear sits on the X27's **Ø1 output shaft**, with its bottom face
5.5 mm above the motor's front face (level L3). Press it on with a drop of Loctite 638 and
trim the shaft 0.3 mm above the gear. Don't push hard on the shaft; support it from behind.

**Crown.** Nothing to do: `crown_turned` is one finished piece. It goes in with the case (§7).

**Hinge: cut and trim it yourself (after releasing the hold in §0).** Buy the stock Guden brass
hinge and cut your piece from it with a Dremel cut-off wheel. The laser-cut `hinge_trim_gauge`
does the measuring:

1. Lay the hinge open flat on the bench, barrel up, and drop the gauge over it so the barrel
   sits in the gauge's slot. Slide it until one slot end lines up with a knuckle joint.
2. The slot is exactly **five knuckles** long. Cut across the barrel at both slot ends, right in
   the knuckle joints, so both end knuckles belong to the same leaf: that's the fixed (case)
   leaf. Centre-punch each end of the barrel lightly so the pin can't walk out.
3. Turn the gauge so its straight top edge lies over the other leaf (the lid leaf) and scribe
   along it: that line is **5.6 mm from the pivot**. Cut just outside it and file to the line.
   The case leaf stays full width.

Nothing else is fitted outside the case: there is no separate stop. The lid opens flat and a
little beyond, until the two leaves close on each other.

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
   17T gear) in the centre bearing, as in step 3. Slide the X27 along the slot until the 34T motor gear meshes with a hair of
   backlash. Hold it there, turn the stack over and solder the eight X27 socket pins. Then
   undo the three floor screws and lift P1 + standoffs off the carrier. The X27 stays plugged in.
2. Stand P1 on its three bay standoffs on the bench. They hold it 12 mm up, so the parts below
   P1 hang free.
3. Drop in, in this order:
   - arbor I (3/32" rod into the centre bearing);
   - arbor II, then arbor III, then the needle arbor, sliding each over the last;
   - the three sensor shafts, gears already on their collars;
   - the three knob shafts, thumbwheels already on their collars, then a `sleeve_knob` slid down
     onto each thumbwheel;
   - the **speaker**: solder ~6 cm of 2-core 30 AWG to its back tabs, thread the pair down through
     the open centre of P1's speaker seat (top-left) and seat the speaker on its foam ring;
     the seat is a ring so the speaker's back can breathe into the bay below;
   - the **mic**: solder ~8 cm of 5-core 30 AWG to the INMP441 (VDD GND SCK WS SD, with L/R
     bridged to GND at the mic) and stick it under P2's 7-hole mic port, port up, with
     foam tape that has a hole over the port. Its leads hang down through P1's open lattice
     beside it once P2 goes on.
4. Lower P2 over the cannon and onto every shaft tip. This is the fiddly watchmaker's moment:
   start from one side and coax each tip into its hole with tweezers. Screw the four **M2×5 M-F**
   standoffs through P2 into the gear standoffs.
5. **Magnets.** Push a Ø6×2.5 diametric magnet into each `magnet_cup` with a little epoxy until
   it bottoms. Then, from underneath, put a drop of Loctite 638 on each sensor shaft's thin
   bottom tip and push a cup on until it stops on the shoulder, while you hold the shaft down
   from above. The cup then hangs 0.3 mm below P1 and the magnet is centred automatically.
6. Check that every knob turns its hand arbor smoothly and that the X27 gear meshes with the needle gear.
   Add a drop of clock oil to each bearing.

## 6. Dial and hands

1. Apply the dial sticker to P2, centred on the cannon. The cut-line circle ID is Ø58 mm.
   Line up **Hourglass** with the top (12 o'clock) knob.
2. The framing hands come blued (spring steel): no finishing. Polish the copper needle. Handle
   the hands by the hub; they are thin.
3. Fit them in this order, each with a dot of Loctite 638 on its arbor and pointing at Hourglass.
   The laser-cut **`hand_setting_tool`** does the positioning: press it down over the arbors
   until it bottoms, and the hand under it is flush with its own arbor's end.
   - Needle on the needle arbor: press with the **one-dot** hole.
   - Hand III on arbor III: press with the **two-dot** hole.
   - Hand II on arbor II: press with the **three-dot** hole.
   - Hand I: push it down arbor I's thin top until it sits on the shoulder.
   - The cap: press it with the tool's plain end until the tool touches the top of arbor I.

   Check that every hand turns freely without touching its neighbours. Calibration later removes
   any angular error.

## 7. Case

1. **Crown.** Push `crown_turned` in from outside through the lower tray's top-right chamfer
   hole and snap the DIN 6799 E-clip into its groove from inside (flat-nose pliers or an E-clip
   applicator). The groove's position gives the 0.3 mm of play.
2. **Lower tray.** Line the floor with one layer of Kapton. Put the three nylon spacers over the
   floor holes and lower the populated carrier straight in: U7's receptacle lines up with the wall
   opening, the crown switch drops in just behind the crown's stem, and the power and mute
   sliders poke out through their two slots in the bottom wall. Plug the battery into J8 (check
   with a meter first that its red wire lands on the **+** mark: JST-PH polarity isn't
   standardised). With the movement standing beside the tray, solder
   the speaker leads into J5 (+ −) and the mic leads into J4 (VDD GND SCK WS SD): both pad rows
   sit right under their pass-throughs (see WIRING.md, *Where things go*). Press the crown: you
   should feel the switch click.
3. Lower the movement straight down onto the carrier. The X27 and its gear rise up through
   P1's slot and the motor gear slides into mesh with the needle gear (rock the needle a hair
   if the teeth butt). Fix it with three **M2×8 countersunk** screws from under the floor, through the
   spacers and board into the bay standoffs.
4. **Upper shell (do this with the shell upside down).**
   - Glue a ring of speaker cloth under the grille slots.
   - Epoxy the body closure magnet (top-left, between grille and wall) to the underside of the
     top face.
   - Drop the crystal into the frame spider, then lay the seat spider on top.
5. **Hinge, before fitting the shell over the movement.** The shell and lid blanks have no hinge
   holes. The laser-cut `hinge_drill_guide` places all six at once:
   - Set the lid on the upper shell, closed and aligned, and hold the cut hinge against their
     right side with the barrel on the seam.
   - Hang the guide over it: its lip rests on the lid top and the barrel passes through its
     slot. Centre it so both ends are the same distance from the corners, then clamp everything.
   - Drill through the guide's holes, leaf and wall in one go: four Ø2.4 mm (case) and two Ø1.8 mm
     (lid). Centre-punch or spot each hole first so the drill doesn't wander.
   - Unclamp, deburr, and countersink the **leaf holes only** with the same 90° zero-flute
     countersink until the screw heads sit flush: rim **Ø3.8–3.9 mm** on the four M2 holes
     (Ø2.4 drilled), **Ø3.0–3.1 mm** on the two M1.6 holes (Ø1.8 drilled).
   - Case side: four **M2×6 DIN 963** screws from outside, the laser-cut backing strip and four
     M2 nuts inside. P2 has a hinge-side relief for the strip and nuts.
   - Lid side: two **M1.6×4 DIN 963** screws from outside, an M1.6 washer and nut inside each.
   - Every head must finish flush: when the lid is fully open the leaves close face to face.
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

1. The lid is already hinged (§7 step 5).
2. Epoxy the pierced overlay inside the lid, keeping the two hinge nuts clear.
   Epoxy the lid magnet into the overlay's hole, its pole attracting the body magnet.
3. Open the lid through its full travel. It passes flat (180°) and stops a little beyond, about
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
| A knob is stiff | Check the thumbwheel sits flat on its collar and no Loctite reached the sleeve or bushings; the case notch leaves 1.2 mm each side. |
| A hand drags its neighbour | Add a 0.1 mm shim between the gears, or ease the tube's fit. |
| Hand reads the wrong symbol near one spot | Check the AS5600 is fully seated in its socket and level on its rest post (chip about 1.1 mm under the magnet), then recalibrate. |
| Something electrical misbehaves | Lift the movement out and probe the labelled test pads (see the [bring-up checklist](pcb/README.md#bring-up-checklist)). Any module can be pulled and swapped. |
| The needle buzzes at the wrong end on wake | Set `MOTOR_PHASE_DIR = -1` in `firmware/src/config.h`. |
| Nothing happens on a crown press | Power switch on (slid toward the corner)? Check the battery plug polarity and charge it over USB with the switch on. |
| It never speaks | The mute switch is toward the centre (muted). |
