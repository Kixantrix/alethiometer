# Bill of materials

Prices are rough USD estimates from late 2026 for **one** instrument. Check current prices
before ordering. Every fabricated part comes from `out/`, which `cad/build.py` regenerates.

**Estimated total ≈ $430–560** (≈ $300–380 SendCutSend, ≈ $95–115 electronics, ≈ $35–60 stock,
hardware and consumables). Tools are not included.

## A. SendCutSend: laser-cut and bent parts

Upload every file in [`out/sendcutsend/`](out/sendcutsend). Each filename carries the material
and quantity, e.g. `knob_I_31T_x5__brass-040in__qty5.dxf`. The same list is in
[`out/sendcutsend_order.csv`](out/sendcutsend_order.csv).

| Part | Material | Qty | Notes |
|---|---|---|---|
| `case_lower_tray` | Brass 260 .040" | 1 | **Bent**: 8 × 90° flanges up, 13.6 mm tall. Upload `case_lower_tray__formed.step` (preferred) or the DXF with its BEND layer. |
| `case_upper_shell` | Brass 260 .040" | 1 | **Bent**: top face with crystal window and 90-slot grille ring, 8 flanges 18.25 mm. Knob notches, USB-C slot, crown hole. |
| `case_lid` | Brass 260 .040" | 1 | **Bent**: 8 flanges 7.62 mm (just above SCS's .292" minimum). |
| `lid_overlay` | Brass 260 .040" | 1 | Pierced rosette, fixed inside the lid |
| `dial_plate_P2` | Brass 260 .063" | 1 | Skeleton window; carries the dial sticker and top bearings |
| `movement_base_plate_P1` | Brass 260 .063" | 1 | Hidden lattice; bottom bearings, X27 cutout. Aluminium 5052 .063" works too and saves ~45 g. |
| `crystal_seat_spider` | Brass 260 .040" | 1 | |
| `crystal_frame_spider` | Brass 260 .063" | 1 | Crystal pocket |
| `crystal` | **Clear cast acrylic .063"** | 1 | Ø88 mm. Upgrade: any Ø88 × 1.5 mm flat mineral watch/clock glass. |
| `gear_hand_I/II/III_36T` | Brass 260 .040" | 1 each | Module 0.7, 20° PA. Bores differ (3/32", 1/8", 5/32") |
| `gear_sensor_I/II/III_36T` | Brass 260 .040" | 1 each | Bore 1/8" |
| `knob_I/II/III_31T_x5` | Brass 260 .040" | 5 each | Five layers → one thumbwheel |
| `gear_needle_19T` | Brass 260 .040" | 1 | Bore 3/16" |
| `gear_motor_38T` | Brass 260 .040" | 1 | Bore Ø2.05 (X27 collar) |
| `hand_I`, `hand_II`, `hand_III` | Brass 260 .040" | 1 each | Darken after cutting |
| `hand_needle` | **Copper 110 .032"** | 1 | The answering needle |
| `hand_cap_rosette` | Brass 260 .040" | 1 | Ø10 centre cap |
| `crown_cap_disc` | Brass 260 .040" | 3 | Scalloped crown |
| `hinge_leaf_body`, `hinge_leaf_lid` | Brass 260 .040" | 1 each | Comb leaves for the knuckles |

**Ordering notes**
- Add **deburring** to the plates if offered for that thickness. The case parts will be hand-finished anyway.
- The three bent parts each have **eight** flanges. SendCutSend's instant quote covers 3- and
  4-sided boxes, so an 8-flange tray may go to manual review. Myth Made's published case is
  also an 8-bend folded tray. If it's rejected, ask for a custom quote. As a last resort, order the DXF
  flat and bend it yourself on a small box-and-pan brake.
- Order a spare set of the small gears (`gear_*`, one extra `knob_*` layer each). They're cheap,
  and laser-cut module-0.7 teeth sometimes need a second try.
- Bearing holes are drawn at nominal +0.12 mm; ream them to fit (ASSEMBLY.md §1).

## B. K&S Precision Metals brass stock (hobby shops, Amazon)

| Item | Qty | ≈ $ | Used for |
|---|---|---|---|
| Round brass tube, .014" wall, 12": **1/8", 5/32", 3/16", 7/32"** (or the K&S #3400 telescoping assortment) | 1 each | 15–25 | Hand arbors, needle arbor, cannon, sleeves, collar, hinge knuckles |
| Round brass rod, 12": **3/32", 1/8", 5/32"** | 1 each | 8–12 | Arbor I, sensor/knob shafts, crown plunger, hinge pin |

Cut list in [ASSEMBLY.md](ASSEMBLY.md) §2 and `out/stock_and_bought_parts.csv`.

## C. Fasteners and fittings

| Item | Qty | ≈ $ | Notes |
|---|---|---|---|
| M2 brass hex standoff, **female-female 8 mm**, 4 mm AF | 4 | 3 | Bay posts (floor → P1) |
| M2 brass hex standoff, **male-female 8 mm** (+3 mm thread) | 4 | 3 | Gear posts (P1 → P2) |
| M2 brass hex standoff, **male-female 6 mm** (+3 mm thread) | 4 | 3 | Hand posts (P2 → crystal) |
| M2 × 4 brass slotted cheese-head screw | 4 | 2 | Floor (they double as feet) |
| M2 × 5 brass slotted cheese-head screw | 4 | | Top face |
| M3 brass shim washer 0.5 mm (Ø6 × Ø3.2) | 4 | 2 | Shaft spacers |
| Ø6 × 2.5 mm **diametric** NdFeB magnet | 3 | (incl.) | Usually supplied with AS5600 boards |
| Ø5 × 4 mm N52 axial magnet | 3 | 3 | Lid closure pair + reed trigger |

## D. Electronics

| Item | Qty | ≈ $ | Source / notes |
|---|---|---|---|
| **Unexpected Maker ProS3** (ESP32-S3, 16 MB/8 MB PSRAM, LiPo charger, switchable LDO2) | 1 | 30 | unexpectedmaker.com, Pimoroni, Mouser |
| LiPo 1S 3.7 V, **402535** (≈4 × 25 × 35 mm, ~350 mAh), PicoBlade 1.25 lead | 1 | 6–9 | Anything ≤ 4.5 × 25 × 35 mm fits |
| **Juken/Switec X27.168** gauge stepper (with internal stop; *don't* remove it) | 1 | 4–10 | Adafruit #2424, AliExpress |
| **Adafruit DRV8833** dual H-bridge breakout (#3297) | 1 | 5 | |
| **Adafruit MAX98357A** I2S class-D amp (#3006) | 1 | 6 | |
| 28 mm, 8 Ω, 0.5–1 W thin speaker (≤ 5 mm) | 1 | 2–4 | e.g. Adafruit #1890 |
| **INMP441** I2S MEMS microphone module (round, Ø14 mm) | 1 | 3 | |
| **AS5600** magnetic encoder board (≤ 23 × 23 mm, OUT pin broken out) + diametric magnet | 3 | 6–10 | |
| USB-C power breakout (CC pull-downs fitted), e.g. Adafruit #4090 | 1 | 3 | Side charging port |
| Glass reed switch, normally open, ≈ 2 × 14 mm | 1 | 1 | Lid sensor |
| Tactile switch 4.5 × 4.5 mm, through-hole | 1 | 0.2 | Crown |
| Resistors 1/8 W: **10 kΩ × 3, 47 kΩ × 3, 1 MΩ × 1** | 7 | 1 | Hand dividers, reed pull-up |
| 30 AWG silicone or Kynar wire, heat-shrink, scrap perfboard, Kapton tape, thin double-sided foam tape | — | 8 | |

## E. Dial, finish and consumables

| Item | ≈ $ | Notes |
|---|---|---|
| Matte white (or cream) inkjet vinyl sticker sheet + clear matte laminate | 8 | Generate the dial with Myth Made's symbols (`dial/make_dial.py --art …`), then print `dial/local/dial_print_letter.pdf` or upload `dial/local/dial_1200dpi.png` to a die-cut sticker service. See `dial/README.md`. |
| Soft solder + brass flux + solder paste | 12 | |
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
