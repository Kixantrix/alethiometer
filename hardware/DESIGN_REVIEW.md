# Design review: simplicity and manufacturing

Two passes over the whole instrument, after the assembly guide and its fixes (F1–F10 in
[`assembly/FINDINGS.md`](assembly/FINDINGS.md)):

1. **Simplicity.** Where are we using more parts, tighter tolerances or more steps than the job needs?
2. **Design for manufacturing.** Is there a known way to buy or make every part, and is there a cheaper one?

**Status (23 Nov 2026).** S1, S2, S3, S5, D2 and D3 are **implemented** in the CAD, guide and BOM,
with the changes noted under each. S4 stays an investigation; S6 has had its feasibility check
(below) and waits for your decision. Numbers come from the model (`cad/mesh.py`, `pcb/alethiometer_carrier.kicad_pcb`, `out/*.csv`) or the cited
supplier pages, checked in November 2026. Prices are estimates; the free instant quotes in §D1 replace them.

## Summary

| ID | Proposal | Removes | Cost effect | Risk | Status |
|---|---|---|---|---|---|
| [S1](#s1) | Driven gears cut loose by default; 4 tight alternates instead of 8 spares | 4 parts and the "fit a spare if it binds" step | −$5–10 | Low | **Done** |
| [S2](#s2) | Tap the hinge backing strip M2 (by hand) | 4 nuts held inside the wall; the M2×6 screw size (now M2×4, as the top face) | ≈ $0 (+ an M2 tap) | Low | **Done** |
| [S3](#s3) | Glue the crystal into the top face; drop both spiders | 2 spiders, 2 screws, 2 nuts, 2 countersinks; one standoff size | −$10–15 | Medium | **Done** |
| [S4](#s4) | ProS3's own USB-C at the wall | breakout, cut cable, 2 screws, 2 nuts, 2 spacers, 20 joints | −$7 | Medium | Investigate (layout check) |
| [S5](#s5) | Have the carrier PCB's through-hole parts factory-soldered | ~130 of your ~230 solder joints | +$15–30 | Low | **Done** (recommended option in the guide) |
| [S6](#s6) | v2 carrier with the chips on the board (factory SMT) | every module, socket and header; ~220 joints; 6.35 mm of height | −$0–40 | High (new board) | Checked: see [S6](#s6) |
| [D1](#d1) | Get the four outstanding quotes before any order | — | — | — | **Yes, first** |
| [D2](#d2) | Tools in aluminium (P1 kept brass: it's visible) | — | −$5–10 | Low | **Done** (tools) |
| [D3](#d3) | Relax the turned-part tolerances to what the fits need | — | likely −20–40 % on the kit | Low | **Done** (quote both) |

Not worth changing (checked): [§N](#n-checked-and-kept).

---

## Simplicity

### S1

**Gears: cut the driven gear of each laser-laser pair loose by default and drop the spare set.**

Today every laser-cut gear has an `_L` twin with 0.16 mm thinner teeth (8 extra parts), fitted only
if a pair binds on the dry run. Re-running `cad/mesh.py` with only **one** loose gear per pair:

| Pair | Backlash, nominal | Worst-case cut (0.065 mm fat per side) |
|---|---|---|
| sensor → hand (×3), both gears standard (today) | 0.28 mm | **binds** |
| sensor → hand (×3), hand gear loose | 0.36 mm (1.6° at the hand) | 0.08 mm, turns |
| motor → needle, needle gear loose | 0.36 mm (3.0° at the needle) | 0.08 mm, turns |
| knob → sensor (×3), unchanged | 0.22 mm | 0.08 mm, turns |

So cutting just the three hand gears and the needle gear at the loose setting makes every pair run
even at the worst-case cut, with no spares and no decision in the build. The cost is about 0.6° more
play at each hand (symbols are 10° apart) and 1° at the needle, which the firmware's one-direction
approach already takes up.

**Done.** The hand and needle gears are cut loose (`GEAR_BACKLASH_LOOSE`), and the four `_T` gears
are tight alternates with standard teeth (0.28 mm backlash) for a cut that comes out thin, so there
are options both ways. `mesh.py` and `test_gears.py` now require every pair as ordered to run at
the worst-case cut.

### S2

**Tap the hinge backing strip M2 and drop its four nuts.**

The four case-side hinge screws pass through the shell and the 1.6 mm (.063") brass backing strip
into loose M2 nuts that have to be held inside the wall. SendCutSend taps brass from .063" up, with
M2 × 0.4 as a standard size ([tapping service](https://sendcutsend.com/services/tapping/)), but only on
parts at least 1 × 1.5" and the strip is 11 mm (0.43") tall; OSH Cut's smallest metric tap is M3.
**Done** differently: the strip is cut with Ø1.6 mm tap-drill holes and you tap them by hand
(ASSEMBLY.md §1.4, a few minutes with an M2 tap). 1.6 mm of brass thread is the same engagement as the DIN 934 nut it replaces
(1.6 mm tall). The lid side can't follow: its M1.6 screws are below SendCutSend's smallest tap, and
the lid leaf is too narrow for an M2 head, so its two nuts and washers stay.

### S3

**Glue the crystal into the top face like a watch crystal, and drop both spiders.**

The crystal stack is a .040" seat spider, a .063" frame spider (the crystal pocket) and, since F2, two
M1.6 screws and nuts to hold it all while the shell is turned over. The crystal (Ø88) already overlaps
the window (Ø84) by 2 mm all round, so it can be glued directly under the top face with clear
crystal cement or UV glue. Then:

- both spiders, both crystal screws and nuts, and their two countersinks go;
- the hand standoffs grow from 5 mm by the 2.6 mm the spiders filled. An **8 mm** M-F standoff
  (the same part as the gear posts, one SKU instead of two) raises the case top and the crystal by 0.38 mm
  (the hand-to-crystal gap grows from 1.5 to about 1.9 mm);
- F2 is solved the same way (nothing loose when the shell is turned over).

**Trade-off:** replacing a scratched crystal means softening the glue rather than undoing two screws.
The frame spider also centred the crystal; the window edge does that well enough by eye. Needs a
small CAD change and a re-run of the stack tests.

**Done.** The case is 0.33 mm taller (37.3 mm body, 45.0 mm closed) and the hand cap clears the
crystal by 1.9 mm. The top screws are now M2×4 (2.98 mm of thread in the standoffs).

### S4

**Bring the ProS3's own USB-C port to the wall, if it fits.**

The ProS3 doesn't break USB D+/D− out to its header pins, so today a cut-down USB-C cable is
soldered into J7, the carrier carries the signals to an Adafruit #4090 breakout on a socket, and the
breakout is held by two screws, nuts and spacers: 8 parts and 20 joints (4 cable, 8 socket, 8 breakout header). Turning
the ProS3 so its port faces the right (hinge) wall would remove all of it.

**Why it's only "investigate":** the ProS3 would sit over x ≈ 2…55, y ≈ 15…32, close to AS5600 I and
the X27. Also, the plug's force would then land on a socketed module instead of a screwed-down
breakout, which was the reason for the current design. A layout check in `cad/layout.py` would
settle it.

### S5

**Have the carrier's through-hole parts soldered at the factory.**

The current design needs about **230 solder joints** from you:

| Where | Joints |
|---|---|
| Carrier PCB: sockets, resistors, cap, switches, J4/J5/J7/J8, J1/J2 headers | 144 (129 without the optional J1/J2) |
| Male headers onto the modules: ProS3 34, AS5600 3 × 8, DRV8833 14, MAX98357A 9, USB breakout 8 | 89 |
| Mic and speaker pigtails | 7 |

JLCPCB and PCBWay both do through-hole assembly on the bare board (JLCPCB: about $3.50 plus
$0.017 per joint, plus setup and fixture fees; [JLCPCB pricing](https://jlcpcb.com/help/article/pcb-assembly-price)).
PCBWay's turnkey service buys parts from distributors such as DigiKey, so the Adafruit #3008 short
sockets should be possible (confirm on the quote); at JLCPCB we'd need an LCSC 5 mm-tall female
header or consigned parts. That takes the carrier's ~130 joints off your bench for
roughly $15–30. The modules' own headers (~90) are still yours unless you take S6.

**Done** as the recommended route in ASSEMBLY.md §4.1 and [pcb/README.md](pcb/README.md#factory-assembly);
the board itself is unchanged and you can still build it yourself.

### S6

**v2 carrier: put the chips on the board and have it factory-assembled.**

The bigger lever for "minimise soldering". JLCPCB stocks the chips: AS5600-ASOM (LCSC
[C79815](https://www.lcsc.com/product-detail/Position-Sensors_AMS-AS5600-ASOM_C79815.html), ≈ $1),
DRV8833PWPR ([C50506](https://www.lcsc.com/product-detail/Motor-Driver-ICs_Texas-Instruments_C50506.html), ≈ $0.62),
plus an ESP32-S3-WROOM module, a LiPo charger, the I2S amp and a USB-C receptacle placed right at
the wall. One factory-assembled board would replace the ProS3, 3 AS5600 boards, DRV8833, MAX98357A,
USB breakout, every socket and header, J7 and the cut cable.

- **Soldering:** about 7 joints (the mic and speaker pigtails).
- **Cost:** a 2-board minimum PCBA order lands around the price of today's modules plus PCB;
  roughly neutral to $40 cheaper.
- **Height:** the AS5600 chips would sit directly under their magnets with no socket stack. The
  README estimates sockets cost ~4 mm of case height; the X27 (9.6 mm body) now sets the bay, so
  the real saving needs checking.
- **What you lose:** pull-out modules (reflashing is over USB or Wi-Fi either way), and the
  ProS3's proven power path. A new schematic needs a charger, LDO, ESD and an antenna keep-out
  (inside brass; the -1U module has a u.FL jack like the ProS3[D]).

This is a new PCB design, not a tweak, so it's your call whether it belongs in this build or a v2.

**Feasibility check (LCSC stock, 23 Nov 2026):**

| Function | Part | LCSC | In stock |
|---|---|---|---|
| MCU | ESP32-S3-WROOM-**1U**-N16R8 (u.FL antenna: better inside brass) | C3013946 | 3,042 |
| MCU (PCB antenna) | ESP32-S3-WROOM-1-N8R8 (the N16R8 is out) | C2913201 | 1,158 |
| Hand sensors | AS5600-ASOM (analog, as now) | C79815 | **0** |
| | AS5600-ASOT (AMS) / AS5600-ASOT-SOIC8 (Infineon) | C499458 / C55240803 | **0 / 38** |
| | AS5600L-ASOM (I2C only, settable address: firmware change) | C2153666 | 449, ≈ $6 each |
| Motor driver | DRV8833PWPR | C50506 | 36,540 |
| Amp | MAX98357AETE+T | C910544 | 23,054 |
| LiPo charger | MCP73831T-2ACI/OT | C424093 | 9,513 |
| 3.3 V LDO | AP2112K-3.3TRG1 | C51118 | 18,565 |
| USB-C | TYPE-C-31-M-12 | C165948 | 447,620 |

Everything is stocked except the sensor, which is the weak link: the analog AS5600 that the firmware
uses is down to one 38-piece lot. The AS5600L is stocked but I2C-only (three on one bus at different
addresses: a firmware rewrite of the hand reading, and $18 of sensors).

**Height.** With the AS5600 chips on the carrier (SOIC-8, 1.75 mm) under the same 0.7 mm air gap,
magnet and cup, P1 drops from z 17.1 to **10.8 mm: 6.35 mm off the case height**, and the bay
standoffs shrink from 12 to about 5.7 mm. That needs three other changes: the X27 soldered flat to
the board instead of on 5 mm sockets (its gear then sits 4.15 mm above the motor body instead of
5.5; check the shaft), a lower-profile crown switch than the 7.4 mm B3F-3150, and C1 as a low SMD
electrolytic. The LiPo (4 mm) still fits under P1 with 1.1 mm to spare.

**Verdict:** feasible and worth 6 mm, but not drop-in: the sensor stock and the soldered X27 are
real compromises against "socketed by default". Recommendation: keep the socketed carrier for this
build, and revisit an SMD v2 once the prototype has proven the movement (by then AS5600 stock may
have recovered, or we design for the AS5600L).

---

## Design for manufacturing

### Sourcing status of every part

| Part(s) | How it's made or bought | Known? | Cheaper option |
|---|---|---|---|
| Case tray, shell, lid (8 bends each) | SendCutSend laser + bend, brass .040" | **Quote needed**: 8-flange parts may go to manual review | Order flat and bend yourself on a box-and-pan brake (last resort). OSH Cut cuts brass but doesn't list brass bending; JLCCNC sheet metal has no brass |
| Case countersinks (9) and hinge-leaf countersinks (6) | By hand, 90° zero-flute | Known | Can't be bought: SendCutSend countersinks only ≥ .125" aluminium and plastics ([countersinking](https://sendcutsend.com/services/countersinking/)) |
| P1, P2, overlay, spiders, backing strip, gears, cap | SendCutSend laser, brass | Known (instant quote) | Tools in aluminium ([D2](#d2)) |
| Hands (blued spring steel .015"), needle (copper .032"), crystal (cast acrylic .063") | SendCutSend laser | Known | — |
| Turned kit (31 parts, 15 designs) | CNC turning service, C360 | **Quote needed** | Relaxed tolerances ([D3](#d3)); plain tubes as cut-and-faced K&S tube |
| Thumbwheels (3) | Misumi configurable brass spur gear, m0.8 26T, shape A, 5 mm face, Ø4 H7 | **Quote needed** (individual credit-card accounts are allowed; [account types](https://us.misumi-ec.com/service/new-account/)) | Fallback: stack of laser-cut .040" gears, but visibly laminated |
| Hinge | Guden BR05050404-72, supplied cut and trimmed | **On hold**: curl not dimensioned; needs a sample | None found: solid-brass box hinges (Brusso) are 0.085" thick for mortising, not for .040" walls |
| DIN 963 brass M1.6 and M2 countersunk screws, M2/M1.6 nuts | [Aspen Fasteners](https://www.aspenfasteners.com/m1-6-0-35-x-4mm-din-963-iso-2009-metric-machine-screws-flat-slot-drive-full-thread-brass/), [Accu](https://accu-components.com/us/countersunk-flat-head-screws/641864-SFK-M2-6-BR) | Known | — |
| M2 brass hex standoffs (F-F 12, M-F 8+3, M-F 5+3, F-F 4) | Accu (plain or nickel-plated brass), AliExpress assortments | Known; check the M-F thread length is 3 mm | S3 makes them two sizes plus the corner |
| PicoBlade mic and speaker leads | Molex 15134 double-ended assemblies, cut in half: 5-way 100 mm ≈ $4.94, 2-way 150 mm ≈ $2.62 ([DigiKey](https://www.digikey.com/en/products/detail/molex/0151340500/6198150)) | Known | — |
| Electronics modules, X27, battery, switches | Adafruit, Unexpected Maker, DigiKey | Known | S6 |
| Carrier PCB | JLCPCB / PCBWay | Known | S5 assembly |
| Magnets, E-clip, foam, dial sticker | Commodity | Known | — |

### D1

**Get the four outstanding quotes before changing or ordering anything.** All but the last are free:

1. **SendCutSend instant quote** for `out/sendcutsend/` (shows at once whether the 8-flange parts go to review).
2. **Turned kit** at PCBWay/JLCPCB CNC and one US shop, at both tolerance sets in D3.
3. **Misumi** thumbwheel configuration (confirms the brass shape-A 26T/5 mm/Ø4 combination exists).
4. **Guden** cut-and-trimmed hinge plus a **sample** (a few dollars; it's the critical path for the case).

Together they replace every estimate in BOM.md with real numbers and show where the money goes.

### D2

**Use aluminium for the parts nobody sees.** P1 (under P2) in 5052 .063" is already offered
in the BOM and saves ~45 g. The `hinge_gauge` and `hand_setting_tool` are tools, so 5052 .063" works
for them too. Brass is the most expensive sheet at SendCutSend, so these three parts are the easy savings.
Keep everything visible (case, P2, overlay, gears, cap) in brass, and the backing strip too if it's
tapped (S2), since brass threads are stronger than aluminium.

**Done for the tools only:** `hinge_gauge` and `hand_setting_tool` are `aluminium-5052-063in` in the
order. P1 stays brass: it shows through P2's skeleton window (your call). With S3 the instrument is
about 800 g (was 819 g).

### D3

**Relax the turned-part tolerances to what the fits need.** The drawing asks for ODs 0/−0.02, bores
+0.02/0 and lengths ±0.03 on every part, which is Swiss-lathe territory and drives the price. Only
the **running** diameters need that: shaft and arbor ODs in their bushings, the bushing bores and the
nested arbor bores (0.08 mm design play). Everything else (lengths, collars, cups, crown, sleeves) is
fine at ISO 2768-f (±0.05 mm), which keeps hands and gears visibly flush. Ask for both on the quote.

**Done:** the turned-parts drawing (`out/turned/README.md`) marks each running diameter with ★; the
tight tolerance applies only to those.

---

## N: checked and kept

- **Turned bushings (13).** They're what lets ±0.13 mm laser holes locate shafts to ~0.05 mm. Reaming
  plate holes instead would add hand work and tooling.
- **Analog AS5600 with 6 divider resistors.** All three sensors share one fixed I2C address, so
  digital would need a mux. Analog is the simpler choice.
- **Three sensor-shaft designs.** They differ only in collar height (each gear sits on its own level).
  A single shaft plus spacers would add parts.
- **Knob sleeves (3).** They're the shaft's upward end stop and have to go on after the thumbwheel. A
  thicker thumbwheel would rub P2 on a larger radius and need taller wall notches.
- **Magnet cups (3).** The Ø6 magnet is wider than the Ø3.2 shaft.
- **Three tools** (hinge gauge, hand-setting tool, drill blanks). Each removes a measured or
  hand-judged step.
- **Flush countersunk screws.** Hand-countersinking is the only route (see the sourcing table), and
  flush screws were your requirement.
- **Lid M1.6 nuts and washers.** See S2.
