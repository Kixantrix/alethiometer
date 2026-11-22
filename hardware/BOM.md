# Bill of materials

Prices are rough USD estimates from late 2026 for **one** instrument. Check current prices
before ordering. Every fabricated part comes from `out/`, which `cad/build.py` regenerates.

**Previous estimated total ≈ $450–590**, excluding the newly proposed purchased hinge,
which still needs a quote (≈ $300–380 SendCutSend, ≈ $115–140 electronics including the
carrier PCB, ≈ $35–60 stock, hardware and consumables). Tools are not included.

**Do not order hinge-related parts yet.** The reference hinge's undimensioned curl geometry
needs a supplier drawing/sample and a CAD update before fabrication; see
[ASSEMBLY.md §0](ASSEMBLY.md#0-before-you-order). Motion checks cover the nominal model,
not an inspected commercial hinge.

## A. SendCutSend: laser-cut and bent parts

Upload every file in [`out/sendcutsend/`](out/sendcutsend). Each filename carries the material
and quantity, e.g. `gear_sensor_I_32T__brass-040in__qty1.dxf`. The same list is in
[`out/sendcutsend_order.csv`](out/sendcutsend_order.csv).

| Part | Material | Qty | Notes |
|---|---|---|---|
| `case_lower_tray` | Brass 260 .040" | 1 | **Bent**: 8 × 90° flanges up. USB-C opening (right wall) and crown hole (top-right chamfer). Upload `case_lower_tray__formed.step` (preferred) or the DXF with its BEND layer. |
| `case_upper_shell` | Brass 260 .040" | 1 | **Bent**: top face with crystal window and 90-slot grille ring, 8 flanges 18.25 mm. Knob notches. |
| `case_lid` | Brass 260 .040" | 1 | **Bent**: 8 flanges 7.62 mm (just above SCS's .292" minimum). |
| `lid_overlay` | Brass 260 .040" | 1 | Pierced rosette, fixed inside the lid |
| `dial_plate_P2` | Brass 260 .063" | 1 | Skeleton window; carries the dial sticker and top bearings |
| `movement_base_plate_P1` | Brass 260 .063" | 1 | Hidden lattice; bottom bearings, X27 cutout. Aluminium 5052 .063" works too and saves ~45 g. |
| `crystal_seat_spider` | Brass 260 .040" | 1 | |
| `crystal_frame_spider` | Brass 260 .063" | 1 | Crystal pocket |
| `crystal` | **Clear cast acrylic .063"** | 1 | Ø88 mm. Upgrade: any Ø88 × 1.5 mm flat mineral watch/clock glass. |
| `gear_hand_I/II/III_32T` | Brass 260 .040" | 1 each | Module 0.8, 20° PA. Bores differ (3/32", 1/8", 5/32") |
| `gear_sensor_I/II/III_32T` | Brass 260 .040" | 1 each | Bore 1/8" |
| `gear_needle_17T` | Brass 260 .040" | 1 | Bore 3/16" |
| `gear_motor_34T` | Brass 260 .040" | 1 | Press fit on the X27's Ø1 shaft |
| `hand_I`, `hand_II`, `hand_III` | Brass 260 .040" | 1 each | Darken after cutting |
| `hand_needle` | **Copper 110 .032"** | 1 | The answering needle |
| `hand_cap_rosette` | Brass 260 .040" | 1 | Ø10 centre cap |
| `crown_cap_disc` | Brass 260 .040" | 3 | Scalloped crown |
| `hinge_backing_body` | Brass 260 .063" | 1 | Load-spreading strip inside the upper shell |
| `hinge_drill_guide` | Brass 260 .040" | 1 | **Tool**, one 90° bend: hooks over the closed lid and drills all six hinge holes. Upload `hinge_drill_guide__formed.step`. |
| `hinge_trim_gauge` | Brass 260 .063" | 1 | **Tool**: marks the hinge's cut-to-length and the lid-leaf trim line |

**Ordering notes**
- Add **deburring** to the plates if offered for that thickness. The case parts will be hand-finished anyway.
- The three bent parts each have **eight** flanges. SendCutSend's instant quote covers 3- and
  4-sided boxes, so an 8-flange tray may go to manual review. Myth Made's published case is
  also an 8-bend folded tray. If it's rejected, ask for a custom quote. As a last resort, order the DXF
  flat and bend it yourself on a small box-and-pan brake.
- Order a spare set of the small gears (`gear_*`). They're cheap, and laser-cut teeth sometimes
  need a second try. The thumbwheels are bought gears (§C).
- Fits are sized for SendCutSend's ±0.13 mm. Shafts run in K&S tube bushings, not in the cut
  holes, so nothing needs reaming (ASSEMBLY.md §1).
- **Gear precision upgrade (optional).** The laser-cut gears are fine for this slow, hand-turned
  mechanism: expect about a degree of play at the hands, and calibration absorbs any fixed offset.
  If you want tighter meshing, send the same `gear_*` DXFs to a wire-EDM service
  (e.g. Xometry, PCBWay) for about ±0.01 mm teeth. No design change is needed.

## B. K&S Precision Metals brass stock (hobby shops, Amazon)

| Item | Qty | ≈ $ | Used for |
|---|---|---|---|
| Round brass tube, .014" wall, 12": **1/8", 5/32", 3/16", 7/32"** (or the K&S #3400 telescoping assortment) | 1 each | 15–25 | Hand arbors, needle arbor, cannon, sleeves and crown collar |
| Round brass rod, 12": **3/32", 1/8", 5/32"** | 1 each | Check | Arbor I and crown plunger, sensor shafts, knob shafts |

Cut list in [ASSEMBLY.md](ASSEMBLY.md) §2 and `out/stock_and_bought_parts.csv`.

## C. Fasteners and fittings

| Item | Qty | ≈ $ | Notes |
|---|---|---|---|
| M2 brass hex standoff, **female-female 12 mm**, 4 mm AF | 3 | 3 | Bay posts (carrier PCB → P1); none at the top-right corner (crown switch) |
| M2 nylon round spacer, 2.5 mm × Ø4.5 | 3 | 1 | Floor → carrier PCB (keeps the board off the brass) |
| M2 brass hex nut | 1 | | Under P1 at the top-right corner |
| M2 brass hex standoff, **male-female 8 mm** (+3 mm thread) | 4 | 3 | Gear posts (P1 → P2) |
| M2 brass hex standoff, **male-female 6 mm** (+3 mm thread) | 4 | 3 | Hand posts (P2 → crystal) |
| M2 × 8 brass slotted **countersunk** screw, DIN 963, 90° | 3 | 2 | Flush in the floor → spacer → PCB → bay standoff; length includes head |
| M2 × 6 brass slotted **countersunk** screw, DIN 963, 90° | 4 | | Flush in the top face; length includes head |
| **Thumbwheel gear**: Misumi configurable spur gear, module 0.8, 20° PA, **brass, shape A (no hub)**, 26 teeth, face width 5 mm, round bore 4 mm H7 | 3 | Quote | One solid gear per knob, Loctite 638 on its 5/32" shaft (misumi-ec.com; KHK's brass BSS0.8-26A has the right teeth but a long hub that doesn't fit) |
| Brass hinge, **Guden BR05050404-72** (72" stock length) | 1 | Quote | .040" sheet, .091" pin, .500" pitch, 1.060" open width. Cut your 5-knuckle piece with a Dremel and trim the lid leaf, using `hinge_trim_gauge` (ASSEMBLY.md §3). Plenty left over for spares. |
| M2 × 6 DIN 963 countersunk screw, 90°, Ø3.8 mm head + M2 hex nut | 4 each | Check | Flush in the fixed hinge leaf → shell → body backing strip → nut |
| M1.6 × 4 DIN 963 countersunk screw, 90°, Ø3.2 mm head | 2 | Check | Flush in the lid hinge leaf |
| M1.6 hex nut, 3.2 mm AF × 1.3 mm, and M1.6 DIN 125 washer (Ø4 × 0.3) | 2 each | Check | Inside the lid wall |
| M3 brass shim washer 0.5 mm (Ø6 × Ø3.2) | 1 | 2 | Sensor-I shaft spacer |
| M4 brass shim washer 0.5 mm (Ø8 × Ø4.2) | 3 | 2 | Under each thumbwheel |
| Ø6 × 2.5 mm **diametrically magnetised** NdFeB magnet (the standard AS5600 magnet; ≤ 2.5 mm thick) | 3 | 5 | Sensor-shaft magnets for the AS5600s |
| Ø5 × 4 mm N52 axial magnet | 3 | 3 | Lid closure pair + reed trigger |

The external screws use nominal Ø3.8 mm heads
([DIN 963 dimensions](https://www.jandesupply.com/reference-metric-machine-screw-dimensions.php)).
Hand-countersink the seven case holes after forming, to suit the actual screws
([ASSEMBLY.md §1](ASSEMBLY.md#1-prepare-the-laser-cut-parts)). Do not substitute oval/raised
countersunk heads, a different head diameter, or an 82° screw. The supplier files retain
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
| **Unexpected Maker ProS3** (ESP32-S3, 16 MB/8 MB PSRAM, LiPo charger, switchable LDO2) | 1 | 30 | unexpectedmaker.com, Adafruit, Pimoroni. The ProS3[D] (Adafruit #6398, adds a u.FL antenna jack) drops into the same sockets. |
| **Adafruit AS5600** magnetic angle sensor, STEMMA QT (**#6357**) | 3 | 15 | Header included |
| **Adafruit DRV8833** dual H-bridge breakout (#3297) | 1 | 5 | Header included |
| **Adafruit MAX98357A** I2S class-D amp (#3006) | 1 | 6 | Header included |
| **Juken/Switec X27.168** gauge stepper (with internal stop; *don't* remove it) | 1 | 4–10 | Adafruit #2424, AliExpress |
| Short female headers, 5 mm body (**Adafruit #3008**, 5 × 36-pin) | 1 pack | 5 | Every module socket, including the X27 |
| Male header strip 0.1", 1×40 | 1 | 1 | Speaker pins, J1/J2 |
| Resistors ¼ W metal film: **10 kΩ × 3, 47 kΩ × 3, 1 MΩ × 1** | 7 | 1 | Hand dividers, lid pull-up |
| 100 µF 10–16 V electrolytic, radial Ø6.3 mm, 2.5 mm pitch, ≤ 11 mm tall | 1 | 0.3 | VBAT bulk cap |
| LiPo 1S 3.7 V, **402535** (≈4 × 25 × 35 mm, ~350 mAh), PicoBlade 1.25 lead | 1 | 6–9 | Anything ≤ 4.5 × 25 × 35 mm fits |
| **Adafruit USB Type C breakout** (#4090) + 2× M2 × 10 screws, nuts and 5 mm nylon spacers | 1 | 4 | Wall USB-C port, screwed to the carrier |
| Short USB-C cable with data (thin), cut to ~6 cm | 1 | 3 | ProS3 → carrier J7 |
| 28 mm, 8 Ω, 0.5–1 W thin speaker (≤ 5 mm) | 1 | 2–4 | e.g. Adafruit #1890 |
| **INMP441** I2S MEMS microphone module (round, Ø14 mm) | 1 | 3 | |
| Glass reed switch, normally open, ≈ 2 × 14 mm | 1 | 1 | Lid sensor |
| **Omron B3F-3150** right-angle tactile switch | 1 | 0.5 | Crown, on the carrier |
| 30 AWG silicone wire (optional small inline connectors), Kapton tape, thin double-sided foam tape,  | — | 6 | Off-board leads to J4–J6 |

## E. Dial, finish and consumables

| Item | ≈ $ | Notes |
|---|---|---|
| Matte white (or cream) inkjet vinyl sticker sheet + clear matte laminate | 8 | Generate the dial with Myth Made's symbols (`dial/make_dial.py --art …`), then print `dial/local/dial_print_letter.pdf` or upload `dial/local/dial_1200dpi.png` to a die-cut sticker service. See `dial/README.md`. |
| Soft solder + brass flux + solder paste | 12 | Still needed for shaft/movement and crown joints; no hinge or knob-lamination soldering |
| 5-minute epoxy, Loctite 638 (retaining compound) | 10 | |
| Clock oil | 6 | |
| Speaker cloth / fine acoustic mesh (a 60 × 60 mm piece) | 3 | Under the grille ring |
| Brass black / gun blue for the hands (optional) | 8 | |
| Renaissance Wax or clear lacquer | 10 | |

## F. Cloud

The instrument talks to this repo's Azure Function (`/api/ask-voice`, `/api/speak`). It needs
`gpt-4o-mini-transcribe` and `gpt-4o-mini-tts` deployments in the Azure OpenAI resource and a
`DEVICE_KEY` app setting (see the root README). Expect a few cents per reading
(transcription, the reading, optional web search, and about a minute of speech).
