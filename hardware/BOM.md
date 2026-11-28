# Bill of materials

Prices are rough USD estimates from late 2026 for **one** instrument. Check current prices
before ordering. Every fabricated part comes from `out/`, which `cad/build.py` regenerates.

**Estimated total ≈ $570–860**: SendCutSend ≈ $300–380, electronics ≈ $135–170 (carrier PCB and
its factory assembly included), hardware and consumables ≈ $35–60, and the turned-parts kit
(§B, guess $100–250). Not included: the hinge (§C, needs a quote) and the thumbwheels (§C, needs
a Misumi quote). Tools are listed separately in [§G](#g-tools) (≈ $330 starting from nothing;
skip whatever you already own).

**Do not order hinge-related parts yet.** The reference hinge's undimensioned curl geometry
needs a supplier drawing/sample and a CAD update before fabrication; see
[ASSEMBLY.md §0](ASSEMBLY.md#0-before-you-order). The build keeps those files (upper shell, lid,
lid overlay, backing strip, hinge gauge) in `out/sendcutsend_on_hold/`, apart from the rest. Motion checks cover the nominal model,
not an inspected commercial hinge.

## A. SendCutSend: laser-cut and bent parts

Upload every file in [`out/sendcutsend/`](out/sendcutsend): one file per part, flat parts as DXF and
the bent lower tray as its formed `.step` (don't add the reference flat patterns in `out/flat_patterns/`,
or it is quoted twice). The parts marked *on hold* below are in `out/sendcutsend_on_hold/` until the
hinge is checked. Each filename carries the material
and quantity, e.g. `gear_sensor_I_32T__brass-040in__qty1.dxf`. The same list is in
[`out/sendcutsend_order.csv`](out/sendcutsend_order.csv).

| Part | Material | Qty | Notes |
|---|---|---|---|
| `case_lower_tray` | Brass 260 .040" | 1 | **Bent**: 8 × 90° flanges up. USB-C opening (right wall), crown hole (top-right chamfer) and the power-switch slot (back wall). Uploaded as its formed `.step`. |
| `case_upper_shell` | Brass 260 .040" | 1 | **On hold** (`out/sendcutsend_on_hold/`). **Bent**: top face with crystal window and 90-slot grille ring, 8 flanges 17.2 mm. Knob notches and four hinge holes (right wall). |
| `case_lid` | Brass 260 .040" | 1 | **On hold** (`out/sendcutsend_on_hold/`). **Bent**: 8 flanges 7.62 mm (just above SCS's .292" minimum), two hinge holes (right wall). |
| `lid_overlay` | Brass 260 .040" | 1 | **On hold** (`out/sendcutsend_on_hold/`). Pierced rosette, fixed inside the lid |
| `dial_plate_P2` | Brass 260 .063" | 1 | Skeleton window; carries the dial sticker and top bearings |
| `movement_base_plate_P1` | Brass 260 .063" | 1 | Lattice, bottom bearings, X27 cutout; seen through P2's skeleton window, so brass to match |
| `crystal` | **Clear cast acrylic .063"** | 1 | Ø88 mm, glued under the top face. Upgrade: any Ø88 × 1.5 mm flat mineral watch/clock glass. |
| `gear_hand_I/II/III_32T` | Brass 260 .040" | 1 each | Module 0.8, 20° PA. Bores differ to suit arbors I, II, III. Cut with 0.16 mm thinner teeth so the pair runs at a worst-case cut |
| `gear_sensor_I/II/III_32T` | Brass 260 .040" | 1 each | |
| `gear_needle_17T` | Brass 260 .040" | 1 | Thinner teeth, like the hand gears |
| `gear_motor_34T` | Brass 260 .040" | 1 | Press fit on the X27's Ø1 shaft |
| `gear_hand_*_32T_T`, `gear_needle_17T_T` | Brass 260 .040" | 1 each | **Tight alternates**: the four driven gears with standard (fuller) teeth, marked by a Ø0.5 mm hole in the rim. Fitted only to take play out of a pair that feels sloppy (ASSEMBLY.md §11) |
| `hand_I`, `hand_II`, `hand_III` | **1075 blue-tempered spring steel .015"** | 1 each | Comes blued: no finishing. SendCutSend's only thickness for this material |
| `hand_needle` | **Copper 110 .032"** | 1 | The answering needle |
| `hand_cap_rosette` | Brass 260 .040" | 1 | Ø10 centre cap |
| `hinge_backing_body` | Brass 260 .063" | 1 | **On hold** (`out/sendcutsend_on_hold/`). Strip inside the upper shell's hinge wall; **you tap its four Ø1.6 holes M2** so it is the nut for the hinge screws (ASSEMBLY.md §1.4). SendCutSend's tapping needs parts at least 1 × 1.5", and this strip is 11 mm tall |
| `hinge_gauge` | **Aluminium 5052 .063"** | 1 | **On hold** (`out/sendcutsend_on_hold/`). **Tool**: checks the hinge's cut and lid-leaf trim, and is the drilling template for the six leaf holes (ASSEMBLY.md §3.7) |
| `hand_setting_tool` | **Aluminium 5052 .063"** | 1 | **Tool**: presses each hand flush with its arbor (ASSEMBLY.md §7) |

**Ordering notes**
- Add **deburring** to the plates if offered for that thickness. The case parts will be hand-finished anyway.
- The three bent parts each have **eight** flanges. SendCutSend's instant quote covers 3- and
  4-sided boxes, so an 8-flange tray may go to manual review. Myth Made's published case is
  also an 8-bend folded tray. If it's rejected, ask for a custom quote. As a last resort, order the DXF
  flat and bend it yourself on a small box-and-pan brake.
- The four `_T` gears are tight alternates of the hand and needle gears, with standard teeth: the gears
  as ordered already run at SendCutSend's worst-case cut, so the alternates only take out play if the
  cut comes out thin (ASSEMBLY.md §11). The thumbwheels are bought gears (§C).
- Fits are sized for SendCutSend's ±0.13 mm. Shafts run in turned bushings, not in the cut
  holes, so nothing needs reaming (ASSEMBLY.md §1).
- **Gear precision upgrade (optional).** The laser-cut gears are fine for this slow, hand-turned
  mechanism: 0.22–0.36 mm of backlash at the pitch circle, under 2° of play at a hand (symbols are
  10° apart), and calibration absorbs any fixed offset (`cad/mesh.py` checks every pair).
  If you want tighter meshing, send the same `gear_*` DXFs to a wire-EDM service
  (e.g. Xometry, PCBWay) for about ±0.01 mm teeth. No design change is needed.

## B. Turned-parts kit (CNC turning service)

Every arbor, shaft, bushing, sleeve, magnet cup and the crown: 31 small brass parts in 15 designs,
made to exact length with their shoulders so nothing is cut or measured during assembly.
Upload the files in [`out/turned/`](out/turned) (one `.step` per design, quantity in the
filename) with its [`README.md`](out/turned/README.md), which is the drawing: every diameter,
bore and length, the tolerances and the knurl.

| Service | Notes |
|---|---|
| **PCBWay CNC machining** (turning, brass C360) | Recommended: brass C360 and ±0.01 mm on a marked drawing are both in its published capability. Ask for the "tube" rows to be made from precision tube cut to length and faced |
| A local Swiss-lathe or watch-parts shop | Equally good, especially for the 0.36 mm-wall tubes |
| Protolabs, Hubs/Protolabs Network, JLCCNC | **Not suitable as-is**: their published minimum walls are 0.5–0.8 mm (JLCCNC also turns H59, not C360). Use them only for the "lathe" rows and buy the "tube" rows as precision tube |

| Item | Qty | ≈ $ | Notes |
|---|---|---|---|
| Turned-parts kit, brass C360 | 1 set | Quote (guess 100–250) | Only the running diameters (★ on the drawing) need 0/−0.02 mm ODs and +0.02/0 bores; everything else, lengths included, is ISO 2768-f (±0.05). Ask for the quote both ways. The plain tubes may be quoted as precision tube cut to length and faced: equally good. Order a spare or two of the bushings and sleeves |

The diameters keep K&S telescoping sizes (3/32", 1/8", 5/32", 3/16", 7/32" with .014" walls), so
in a pinch the plain tubes and bushings can still be cut from K&S stock. K&S holds about ±0.05 mm,
which can leave a pair tight: check that each tube slides on the next before cutting.

## C. Fasteners and fittings

| Item | Qty | ≈ $ | Notes |
|---|---|---|---|
| M2 brass hex standoff, **female-female 12 mm**, 4 mm AF | 3 | 3 | Bay posts (carrier PCB → P1); none at the top-right corner (crown switch) |
| M2 nylon round spacer, 2.5 mm long, Ø4.0 OD, Ø2.2 bore: **Ettinger 005.81.025** | 3 | 1 | Floor → carrier PCB (keeps the board off the brass). Sold by Ettinger (packs of 100) and Bürklin (18H0153); any M2 nylon spacer 2.5 mm long and ≤ Ø5 OD will do |
| M2 × 4 brass hex standoff, **female-female**, 4 mm AF | 1 | 1 | Under P1 at the top-right corner (no bay post there) |
| M2 brass hex standoff, **male-female 8 mm**, 4 mm AF, 5 mm stud: **Würth 971080244** (DigiKey 732-12911-ND) | 8 | 5 | Four gear posts (P1 → P2) and four hand posts (P2 → top face): one part. Its 5 mm female thread takes the next post's stud (3.4 mm in) and the top screws |
| M2 × 8 brass slotted **countersunk** screw, DIN 963, 90° | 3 | 2 | Flush in the floor → spacer → PCB → bay standoff; length includes head. Westfield Fasteners WF35489 (packs of 10) |
| M2 × 4 brass slotted **countersunk** screw, DIN 963, 90° | 8 | 3 | Four flush in the top face (into the hand posts) and four in the fixed hinge leaf (into the tapped backing strip); length includes head. Model Fixings MF-CS04BR or Westfield WF35483 (packs of 10–15) |
| **Thumbwheel gear**: Misumi **GEAHB0.8-25-5-A-5** (free-cutting brass, module 0.8, 20° PA, shape A: no hub, 25 teeth, 5 mm face, 5 mm bore H7) | 3 | Quote | One solid gear per knob, on the knob shaft's 5 mm seat with Loctite 638. Misumi's brass range has no 26T and offers a 4 mm bore only up to 23T; the 25T part is in its catalogue, but confirm it in the us.misumi-ec.com cart before ordering (individual accounts pay by card). KHK's brass BSS0.8 gears have a long hub that doesn't fit |
| Brass hinge, **Guden BR05050404-72**, supplied cut to 63.5 mm | 1 | Quote | .040" sheet, .091" pin, .500" pitch, 1.060" open width. Ask for five knuckles with both end knuckles on one leaf, pin staked, and the other (lid) leaf trimmed to 5.6 mm from the pivot; quote it with the §0 sample. Cutting it from the 72" stock yourself is the fallback (ASSEMBLY.md §3.7). |
| M1.6 × 4 DIN 963 countersunk screw, 90°, Ø3.0 mm head, brass | 2 | see note | Flush in the lid hinge leaf, so visible. Brass M1.6 is hard to buy in small numbers: ask Model Fixings (they take requests for other sizes) or buy Aspen's box of 300 (ME193, about $170); A2 stainless (Accu SFK-M1.6-4-A2) fits but shows as two small silver heads |
| M1.6 hex nut, 3.2 mm AF × 1.3 mm (brass, Accu HPN-M1.6-BR), and M1.6 DIN 125 washer, Ø4 × 0.3 (A2 stainless: hidden) | 2 each | 3 | Inside the lid wall |
| DIN 6799 retaining washer (E-clip), **size 1.5** (for Ø2–2.5 shafts), stainless | 1 (+ spares) | 2 | Holds the crown in, inside the wall. They fly: buy a pack |
| Ø6 × 2.5 mm **diametrically magnetised** NdFeB magnet (the standard AS5600 magnet; ≤ 2.5 mm thick), e.g. Radial Magnet 8995 | 3 | 5 | Sensor-shaft magnets for the AS5600s; the §4.4 bench test borrows them before they're glued |
| Ø5 × 4 mm N52 axial magnet, e.g. JC Magnetics JCN52-DSC5-4 | 2 | 2 | Lid closure pair |

The external screws use nominal Ø3.8 mm heads
([DIN 963 dimensions](https://www.jandesupply.com/reference-metric-machine-screw-dimensions.php)).
Hand-countersink the seven case holes after forming, to suit the actual screws
([ASSEMBLY.md §1](ASSEMBLY.md#1-prepare-the-laser-cut-parts)). Do not substitute oval/raised
countersunk heads, a different head diameter, or an 82° screw. Tool: a 90° zero-flute countersink (~6 mm body); finished rim Ø3.8–3.9 mm for M2, Ø3.0–3.1 mm for M1.6. The supplier files retain
plain pilot holes; do not request countersinking from the laser-cut/bending service.

The hinge is a **procurement candidate with a fabrication hold**, not a dimensionally verified
drop-in. Source: [Guden product and drawing](https://www.guden.com/itemdetail/BR05050404-72).
Guden's 1.06" width is its narrowest solid-brass continuous hinge, hence the lid-leaf trim.
Narrower miniature hinges (e.g. K&S 90000, 1/2") are usually brass-*plated* and not the hinge
modelled in CAD. Don't substitute one without measuring it and updating the design.

## D. Electronics

The modules plug into the [carrier PCB](pcb/README.md), whose own BOM lists every socket, resistor and
header with part numbers. Summary:

| Item | Qty | ≈ $ | Source / notes |
|---|---|---|---|
| **Carrier PCB** (`pcb/fab/alethiometer_carrier_gerbers.zip`), 2-layer, 1.6 mm | 1 (of 5) | 10–20 | JLCPCB, PCBWay, OSH Park |
| **Carrier through-hole assembly** (recommended) | 1–2 boards | 15–30 | PCBWay turnkey solders the sockets, resistors, C1, switches and connectors from `pcb/fab/assembly_bom.csv` and `assembly_cpl.csv` (the parts marked **fab** in [pcb/README.md](pcb/README.md#factory-assembly)), saving about 130 joints |
| **Unexpected Maker ProS3[D]** (ESP32-S3, 16 MB/8 MB PSRAM, LiPo charger, switchable LDO2, u.FL jack) | 1 | 27 | Adafruit #6398. The original ProS3 is no longer sold; the [D] is a pin-for-pin drop-in, 2 mm longer at the antenna end (modelled) |
| **Adafruit AS5600** magnetic angle sensor, STEMMA QT (**#6357**) | 3 | 15 | Header included |
| **Adafruit DRV8833** dual H-bridge breakout (#3297) | 1 | 5 | Header included |
| **Adafruit MAX98357A** I2S class-D amp (#3006) | 1 | 6 | Header included. Now ships with a screw terminal soldered on: remove it (ASSEMBLY.md §4.1) |
| **Juken/Switec X27.168** gauge stepper (with internal stop and 4 rear pins; *don't* remove the stop) | 1 | 4–10 | Adafruit #2424 when in stock; otherwise a 4–6 pack from Amazon (uxcell) or eBay gauge-repair sellers. Listings rarely say whether they have the stop: the §4.4 `home` test shows it (the needle stops dead at one end), and a multi-pack covers a dud |
| Short female headers, 5 mm body (**Adafruit #3008**, 5 × 36-pin; DigiKey 1528-3008-ND) | 1 pack | 8 | Every module socket, including the X27. Exactly 5 mm: LCSC's single-row sockets are 8.5 mm and would lift the sensors into their magnets. Bought by the PCB assembler if you order assembly |
| Male header strip 0.1", 1×40 | 1 | 1 | Speaker pins, J1/J2 |
| Resistors ¼ W metal film: **10 kΩ × 3, 47 kΩ × 3** | 6 | 1 | Hand-sensor dividers |
| 100 µF 16 V electrolytic, radial Ø6.3 × 7 mm, 2.5 mm pitch: Panasonic ECE-A1CKA101 | 1 | 0.3 | VBAT bulk cap |
| LiPo 1S 3.7 V, **402535** (≈4 × 25 × 35 mm, about 300 mAh), **JST-PH 2.0** lead (with protection circuit) | 1 | 6–9 | Anything ≤ 4.5 × 25 × 35 mm fits. Plugs into J8; check the polarity (PCB README) |
| **C&K OS102011MA1QN1** right-angle slide switch | 1 | 1 | Power, on the carrier |
| **JST S2B-PH-K-S** side-entry 2-pin socket | 1 | 0.5 | Battery socket J8 on the carrier |
| **Adafruit USB Type C breakout** (#4090) + 2× M2 × 10 brass DIN 84 cheese-head screws (Accu SFE-M2-10-BR), 2 M2 brass nuts and 2 M2 nylon spacers 5 mm long, Ø4.0 (Ettinger 005.81.050) | 1 | 4 | Wall USB-C port, screwed to the carrier |
| Short USB-C cable with data (thin), cut to ~6 cm | 1 | 3 | ProS3 → carrier J7 |
| Speaker: **Same Sky CMS-28468N** (Ø28 × 4.6 mm, 8 Ω, 0.5 W rated / 1 W max, solder pads) | 1 | 4 | Mouser 490-CMS-28468N. Any 28 mm, 8 Ω, ≥ 0.5 W speaker ≤ 5 mm thick fits; Adafruit #1890 is only 0.25 W |
| **INMP441** I2S MEMS microphone module, the **round** Ø14 mm board | 1 | 3 | Sold round and square; the square one isn't modelled |
| **Omron (Aratas) B3F-3152** right-angle tactile switch | 1 | 0.5 | Crown, on the carrier. Same footprint and 6.15 mm plunger as the B3F-3150 it replaces (out of stock until 2027), slightly firmer. Don't use the B3F-3100: its plunger is 3 mm shorter |
| **Molex PicoBlade** 1.25 mm vertical headers **53047-0510** (5-pin, J4) and **53047-0210** (2-pin, J5) | 1 each | 2 | Mic and speaker plug in on the carrier |
| Molex PicoBlade double-ended cables, 300 mm: **0151340503** (5-way) and **0151340203** (2-way) | 1 each | 9 | Cut each in half: 150 mm pigtails, soldered at the mic and speaker (one spare each) |
| Kapton tape, thin double-sided foam tape | — | 4 | Floor lining, battery |

## E. Dial, finish and consumables

| Item | ≈ $ | Notes |
|---|---|---|
| Matte white (or cream) inkjet vinyl sticker sheet + clear matte laminate | 8 | Generate the dial with Myth Made's symbols (`dial/make_dial.py --art …`), then print `dial/local/dial_print_letter.pdf` or upload `dial/local/dial_1200dpi.png` to a die-cut sticker service. See `dial/README.md`. |
| Electronics solder (lead-free or 60/40, 0.5–0.8 mm) and flux pen | 10 | PCB and leads only: nothing in the movement is soldered |
| 5-minute epoxy, Loctite 638 (retaining compound) | 10 | 638 holds every gear, hand, bushing and the cannon; epoxy the magnets |
| Clear UV-curing glue (or watch-crystal cement such as G-S Hypo) + a small UV torch | 8 | Glues the crystal under the top face (ASSEMBLY.md §8) |
| Clock oil | 6 | |
| Speaker cloth / fine acoustic mesh (a 60 × 60 mm piece) | 3 | Under the grille ring |
| Renaissance Wax or clear lacquer, and a metal polish (Autosol or Brasso) | 15 | §10.1 |
| Wet-and-dry abrasive paper, 600, 1000 and 2000 grit | 6 | §1.1 flattening and deburring on glass |
| Contact adhesive (e.g. Evo-Stik or Barge), small tube | 6 | §8.1 speaker cloth under the grille |
| Isopropanol and cotton buds | 5 | Cleaning off glue squeeze-out (§8.1) and Loctite joints (§11) |
| Hot-melt glue | — | Strain relief on the J7 cable (pcb/README.md) |

## F. Cloud

The instrument talks to this repo's Azure Function (`/api/ask-voice`, `/api/speak`). It needs
`gpt-4o-mini-transcribe` and `gpt-4o-mini-tts` deployments in the Azure OpenAI resource and a
`DEVICE_KEY` app setting (see the root README). Expect a few cents per reading
(transcription, the reading, optional web search, and about a minute of speech).

## G. Tools

Everything needed to build the instrument, with the assembly step that uses it. Consumables
(solder, flux, glue, oil, abrasive paper) are in [§E](#e-dial-finish-and-consumables). The two
laser-cut jigs, `hinge_gauge` and `hand_setting_tool`, come with the SendCutSend order.

| Tool | Used for (ASSEMBLY.md) | ≈ $ | Notes |
|---|---|---|---|
| Temperature-controlled soldering iron, fine chisel tip (e.g. Pinecil) | §4 module header pins (and the carrier if not factory-assembled), §5 speaker and mic pigtails; releasing a Loctite 638 joint (§11) | 35 | Electronics only |
| **90° zero-flute (cross-hole) countersink**, ~6 mm (1/4") body, for holes down to 1.6 mm, + T-handle | §1 seven case screw seats, §3 six hinge-leaf seats | 20 | Must be **90°**, not the common US 82°. Finished rim Ø3.8–3.9 mm (M2), Ø3.0–3.1 mm (M1.6) |
| Digital calipers | §1 measuring the gears and countersink rims, §2 identifying the turned parts | 20 | |
| **Drill blanks** (HSS gauge pins) **1/8" ×3 and 5/32" ×3**, 25 mm or longer | §1 lining up the bushing pairs while the Loctite cures | 10 | Exactly the shaft diameters; reusable |
| Rotary tool (Dremel) + reinforced cut-off wheels | Only if you cut the hinge from stock yourself (§3.7) | 50 | Wear safety glasses |
| Drill (cordless or drill press), low speed, with **Ø1.8 mm** and **Ø2.4 mm** HSS bits | §3 drilling the hinge leaves through `hinge_gauge` | — | Assumed owned; bits ≈ $5 |
| Automatic centre punch | Only if you cut the hinge yourself (staking the pin) | 10 | |
| **M2×0.4 hand tap** + small tap wrench, cutting oil | §1 tapping the hinge backing strip | 10 | Any HSS M2 tap; a spiral-point one is easiest in brass |
| Small bench vise + two small spring or C-clamps | §3 clamping the gauge to the hinge for drilling | 30 | Soft jaws or a scrap of card to protect the brass |
| Needle file set | §1 deburring gears and plates, §3 touching up the lid leaf to the gauge | 12 | |
| 10× loupe | §1 checking the gear teeth for burrs | 5 | |
| Flat glass plate (or a tile) | §1 flattening and deburring on 600–2000 grit | 5 | |
| Number drills **#41, #30, #20, #11** (2.44, 3.26, 4.09, 4.85 mm) + a T-handle drill chuck | §3.1 opening a gear bore that comes out tight | 20 | Turned by hand; a #1–#60 set covers them |
| Fibreglass scratch pen | §11 cleaning a Loctite joint back to bare metal | 8 | |
| Olfa CMP-1 compass circle cutter (or a sharp craft knife) | Cutting out the dial sticker (dial/README.md) | 12 | |
| Flat-nose pliers or an E-clip applicator | §6 snapping the crown's E-clip on | 8 | |
| Flat glass sheet (the same one) | §1 bushings flush, §3 gears flush with the arbor ends | — | |
| Precision screwdrivers (slotted 1.5–2.5 mm) and nut drivers 3.2 mm and 4 mm | M1.6/M2 screws, nuts and hex standoffs throughout | 15 | |
| Solder wick (desoldering braid), 2 mm | §4.1 removing the MAX98357A's terminal block | 4 | |
| Flush cutters and a 30 AWG wire stripper | Socket strips, speaker/mic leads, the USB-C cable for J7 | 18 | |
| Hard-wire cutters (rated for piano wire) or a diamond needle file | §3.6 trimming the X27's Ø1 steel shaft | 12 | Don't use the soft-wire flush cutters on it |
| Fine tweezers | Nuts, seating P2 on the shaft tips (§6), rocking gears in the tests | 8 | |
| Multimeter | PCB bring-up and continuity checks (`pcb/README.md`) | 25 | |
| USB-C data cable and a computer with PlatformIO | First firmware flash (`firmware/README.md`) | — | |
| Safety glasses | Drilling | 5 | |
