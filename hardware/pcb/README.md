# Carrier PCB

One octagonal, two-layer, **all through-hole** board in the bottom of the case. It replaces the
point-to-point wiring. **Every module plugs into sockets**, so you can pull any of them to
reflash, probe or replace it without desoldering anything. The crown switch and the wall USB-C
port are mounted on the board too, so their push and plug forces go into the screwed-down
carrier rather than a glue joint. So are the power slide switch and the battery's
JST-PH socket. The two off-board parts (mic, speaker) connect to labelled pads. Every signal also has a labelled test pad.

![top](fab/render_top.png)

| File | What it is |
|---|---|
| `make_pcb.py` | Generates the whole board from [`../cad/layout.py`](../cad/layout.py) (the same positions the CAD model uses) |
| `alethiometer_carrier.kicad_pcb` | The KiCad 10 board. Open it to inspect or tweak. |
| `fab/alethiometer_carrier_gerbers.zip` | **Upload this to the PCB fab** |
| `fab/plot_top.pdf`, `fab/plot_bottom.pdf` | 1:1 prints for checking parts against the board before soldering |
| `fab/render_top.png`, `fab/render_bottom.png` | 3D renders |
| `NETLIST.md` | Every net and the pads on it |
| `drc_report.json` | KiCad DRC (0 violations, 0 unconnected) |
| `alethiometer.pretty/` | Footprints: the Adafruit modules, the X27, and Unexpected Maker's ProS3 (CERN-OHL-1.2) |

## Ordering the board

JLCPCB, PCBWay, OSH Park and similar fabs all work. Upload `fab/alethiometer_carrier_gerbers.zip`
and pick:

- **2 layers, FR-4, 1.6 mm**, 1 oz copper;
- HASL (lead-free) or ENIG, any solder-mask colour;
- assembly: see [Factory assembly](#factory-assembly) (recommended), or none to build it yourself;
- leave "remove order number" at the default, or pay for it.

The board is about 108 mm across, a little over the 100 × 100 mm price break, so expect roughly $10–20 for five
boards plus shipping.

## Factory assembly

Recommended: have the fab solder every through-hole part on the board, so the only soldering left
to you is the modules' own header pins, J7's USB cable and the mic and speaker pigtails. That
takes about 130 joints off your bench. Choose **through-hole (THT) assembly** on the order:

- **PCBWay turnkey** sources from distributors such as DigiKey, so it can buy the Adafruit #3008
  5 mm short sockets and everything else in the table below; confirm the socket on the quote.
- **JLCPCB** assembles THT parts from its LCSC library (about $3.50 plus $0.017 per joint, plus
  setup and fixture fees; [pricing](https://jlcpcb.com/help/article/pcb-assembly-price)). Pick an
  LCSC 0.1" single-row female header with a **5 mm body**, or send the #3008 strips as consigned parts.
- Order the parts marked **fab** in the table; the rest come from you. Budget about $15–30 for the
  assembly of one or two boards.
- What you get checked: the bare boards are **100 % electrically tested** against the netlist (opens
  and shorts), and the assembled board gets **optical inspection** (AOI). Neither powers it up, so
  still do the [bring-up checklist](#bring-up-checklist).
- The sockets have to sit square for the modules to plug in at the right height: ask for them to be
  fitted flat on the board, and check that each module plugs in level when the boards arrive.

## Bill of materials (carrier)

| Ref | Part | Qty | Notes |
|---|---|---|---|
| — | Carrier PCB (above) | 1 | |
| U1 | **Unexpected Maker ProS3** (ESP32-S3) | 1 | Solder its two 1×17 male headers on, pins down |
| U2–U4 | **Adafruit AS5600** magnetic angle sensor, STEMMA QT (#6357) | 3 | Header included. Use the 1×6 row only. **Magnets not included**; see the main BOM. |
| U5 | **Adafruit DRV8833** dual H-bridge (#3297) | 1 | Header included (1×8 + 1×6) |
| U6 | **Adafruit MAX98357A** I2S amp (#3006) | 1 | Header included. Leave the screw terminal off. |
| M1 | **Juken/Switec X27.168** gauge stepper (keep its internal stop) | 1 | Adafruit #2424 or AliExpress |
| — | **Short female header, 0.1", 5 mm body** (Adafruit #3008, 5 × 36-pin) | 1 pack | Cut into every socket: 2× 1×17 (ProS3), 3× 1×6 + 3× 1×2 (AS5600 + rest posts), 1×8 + 1×6 (DRV8833), 1×7 + 2× 1×1 (MAX98357A), 2× 1×4 (X27). About 110 of the 180 positions. **fab**|
| — | Male header strip 0.1", 1×40 | 1 | MAX98357A speaker pins, J1 (and J2 if wanted) |
| U7 | **Adafruit USB Type C breakout, downstream (#4090)** | 1 | Wall USB-C port. Header included; 5.1 kΩ CC resistors on board. Plugs into a 1×8 socket. |
| — | M2 nylon round spacer, 5 mm × Ø4.5; M2 × 10 screw; M2 nut | 2 each | Clamp U7 down beside its receptacle (screw from the top, nut under the carrier) |
| SW1 | **Omron B3F-3150** right-angle 6 × 6 mm tactile switch (or B3F-3100) | 1 | Crown switch, soldered at the top-right corner **fab**|
| — | Short USB-C cable **with data** (USB 2.0), thin (≤ 3.5 mm) | 1 | Cut to ~6 cm from the plug: ProS3 USB-C → J7. Check D+/D− continuity first; charge-only cables won't work. |
| R1, R3, R5 | 10 kΩ, ¼ W metal film, 0.4" (10.16 mm) lead pitch | 3 | Series resistors of the hand-sensor dividers **fab**|
| R2, R4, R6 | 47 kΩ, ¼ W metal film | 3 | Divider shunts (`HAND_DIVIDER_RATIO` = 57/47 in firmware) **fab**|
| SW2 | **C&K OS102011MA1QN1** right-angle SPDT slide switch | 1 | Power, on the back edge; reached through a slot in the back wall **fab**|
| J8 | **JST S2B-PH-K-S** side-entry 2-pin socket, 2.0 mm | 1 | Battery plug. Polarity is marked on the silkscreen. **fab**|
| C1 | 100 µF 10–16 V aluminium electrolytic, radial Ø6.3 mm, 2.5 mm pitch, **≤ 11 mm tall** (a 6.3 × 7 can is ideal) | 1 | Bulk cap on VBAT for the motor and amp. **Polarised.** **fab**|
| J4, J5 | **Molex PicoBlade** 1.25 mm vertical headers **53047-0510** (5-pin) and **53047-0210** (2-pin) | 1 each | Mic and speaker plug in here **fab**|
| — | PicoBlade-compatible pre-crimped pigtails, 5-way and 2-way, ~10 cm | 1 each | Soldered at the INMP441 and the speaker |
| — | M2 nylon round spacer, 2.5 mm × Ø4.5 | 3 | Between the case floor and the board |
| — | M2 × 12 mm brass hex standoff, female-female | 3 | Board → P1 |
| — | M2 × 8 mm brass slotted countersunk screw, DIN 963, 90° | 3 | Flush case floor → spacer → board → standoff; length includes head |
| — | Kapton tape | | One layer on the case floor under the board |

## How it goes together

The board stands on three nylon spacers above a Kapton-lined floor. Brass M2 × 12 standoffs carry
plate P1 above it. The top-right corner has no bay post, which leaves room for the crown switch;
P1's corner there is held by an M2 nut instead. Around the post holes the board has a 3.4 mm
copper keep-out, so the brass case never touches a net. Every module rests **directly on its 5 mm sockets**: its male header is
soldered with the black plastic spacer on top, which is then pulled off (step 4 below). The bay
height is set by the AS5600 chain (socket 5 + board and chip 3.1 + 1.1 mm air gap + Ø6×2.5 magnet
+ 0.3 mm below P1 = 12 mm). The sockets cost about 4 mm of case height compared with soldering the
modules flat.

```
 P1 (brass)                 ────────────────────────────────────────
                                magnet ▒▒        X27 body ██████
 M2×12 standoff ║          AS5600 ▬▬▬▬▬▬▬           │  │
                ║          socket ▮   rest post ▮   socket
 carrier PCB    ═══════════════════════════════════════════════════
 nylon spacer   ▯  Kapton  ─────────────────────────────────────────
 case floor     ════════════════════════════════════════════════════
```

**Socket positions** (the silkscreen shows the module outlines and every pin name):

- **ProS3 (U1).** Two 1×17 rows, with its USB-C toward the left. The ProS3 has no USB data pins
  on its headers, so a short cut-down USB-C cable runs from its port to **J7** (VBUS red,
  D− white, D+ green, GND black). The board carries those four lines to the wall port U7. Put a
  dot of hot glue on the cable jacket near J7 as strain relief.
- **Wall USB-C (U7).** The Adafruit #4090 breakout plugs into a 1×8 socket with its receptacle
  facing the right wall. Two M2 × 10 screws go through its mounting holes (right beside the
  receptacle) and 5 mm nylon spacers, with nuts under the carrier, so plugging in pushes on
  screws, not on the socket. Its mouth sits about 1.5 mm inside the outer face, behind a
  10 × 4.4 mm opening that hugs the port (plugs with short shells may not latch fully).
- **Crown switch (SW1).** An Omron B3F-3150 right-angle tactile switch soldered at the top-right
  corner, its button on the crown axis. The turned brass crown's stem presses it through the lower
  case's chamfer.
- **AS5600 ×3 (U2–U4).** Each chip sits exactly under its sensor shaft. The 1×6 row faces the
  dial centre. A **rest post** under the far edge (just a bare 1×2 socket) holds the board level at the
  same height as the header row. Its
  pads are grounded. Only VIN, GND and OUT are used; leave SDA, SCL and 3Vo unconnected.
- **DRV8833 (U5).** A 1×8 row (VM … AIN1) and a 1×6 row (AO1 … BSEN). BSEN and ASEN are grounded on the board.
- **MAX98357A (U6).** The 1×7 row, plus two single-pin sockets under its **SPK−/SPK+** holes. Solder a
  single male pin into each of those holes. They carry the speaker signal to **J5** and support
  the board's far edge.
- **X27.168 (M1).** Its four rear pins plug into two 1×4 sockets cut from the same 5 mm strip
  (outer positions only). Solder them square with the other sockets: the board's hole positions set
  the motor mesh, like every other gear centre (`cad/mesh.py`).

**Off-board connections.** The mic and speaker plug into **J4** and **J5**, vertical PicoBlade
headers: header and mated plug stand about 6.5 mm, well under P1 (12 mm). Solder pre-crimped
pigtails to the INMP441 and the speaker; they plug in before the movement frame goes down
(ASSEMBLY.md §6.4) and unplug when it is lifted out. J1 and J2 take ordinary vertical male headers
(8.5 mm fits under P1); you only plug into J1 on the bench, with the movement lifted off.

| Ref | Pins (silkscreen) | Goes to |
|---|---|---|
| J1 DEBUG | GND 3V3 TX RX IO0 RST 5V BAT | USB-serial adapter / probes. Hold IO0 low and tap RST for ROM download mode. |
| J2 SPARE GPIO | GND 3 38 34 35 36 37 | Free ESP32-S3 pins for later ideas (IO39–42 stay free on the ProS3, unrouted) |
| J4 MIC | VDD GND SCK WS SD | INMP441 (tie its L/R pin to GND at the mic) |
| J5 SPKR | + − | 28 mm speaker |
| J7 USB CABLE | VBUS D− D+ GND | Cut USB-C cable from the ProS3's own port (wire colours on the silkscreen) |

## Assembly order

If the board came factory-assembled, only steps 4 (the modules' header pins, using the fitted
sockets as the jig), 5 (the battery) and 7 (screwing down U7 and the J7 cable) are left.

1. **Check the bare board** with a multimeter. The GND test pad must not be shorted to `VBAT`,
   `+5V`, `+3V3` or `3V3_SW`.
2. **Resistors and C1.** R1–R6 lie flat. C1's long leg (+) goes to the square pad marked `+`.
   Clip the leads.
3. **Male header** for J1 (and J2 if you want it).
4. **Module sockets: use the modules as jigs.** Cut each socket strip to length (you lose one
   position at each cut; file it smooth) and drop the strips into the board, unsoldered.
   Push the module's male header **long pins down** through the module's holes and into the
   sockets, so the black plastic spacer sits on *top* of the module and the module sits flat on
   the sockets (and on the bare rest-post socket for the AS5600s). Solder **one** socket pin from
   underneath, check that everything is square and flat, then solder the rest. Solder the header
   pins on top of the module. Then slide the plastic spacer up and off with pliers, and clip the
   stubs flush. The MAX98357A's two speaker pins are single header pins fitted the same way.
   Every module now unplugs and drops back in at exactly the right height.
5. **Power switch, J8 and battery.** Solder SW2 and J8 flat on the board. Check with a meter that
   your battery's red wire meets J8's **+** pin; if not, swap the two crimps in its plug (lift the
   tabs with a pin). Stick the cell to the `BATTERY` area with foam tape, lead end toward the top,
   and plug it into J8.
6. **X27 sockets, J4 and J5.** Solder the X27's two 1×4 sockets (plug the motor in as a jig so they
   stand square, then take it out again: it goes in through P1 in ASSEMBLY.md §6) and the two
   PicoBlade headers.
7. **SW1 and U7.** Solder the crown switch flat on the board. Screw U7 down: M2 × 10 screws from
   the top through U7, the 5 mm spacers and the board, with nuts underneath. Cut a USB-C cable
   about 6 cm from the plug, strip the four wires and solder them into J7 by colour. Plug it into
   the ProS3.
8. **Kapton** on the case floor. Spacers, board, then the standoffs, fixed with M2 × 8
   countersunk screws from below. Machine the flush seats in the brass case beforehand
   ([ASSEMBLY.md §1](../ASSEMBLY.md#1-prepare-the-laser-cut-parts)); do not countersink the PCB
   or nylon spacers.

## Bring-up checklist

Do this on the bench before closing the case. Everything is reachable from the top through
the **test pads** in the bottom strip and J1. Every pad is labelled with its net.

| Step | Fitted | Check |
|---|---|---|
| 1 | Bare board + passives | Resistance GND↔`+3V3`, `+5V`, `VBAT`, `3V3_SW` all > 1 kΩ. `H1`/`H2`/`H3` → GND ≈ 47 kΩ. |
| 2 | ProS3 only, USB connected | `+5V` ≈ 5.0 V, `+3V3` ≈ 3.3 V, `VBAT` ≈ 4.2 V (charging or battery). Flash the firmware (see [`../../firmware/README.md`](../../firmware/README.md)) and open the serial monitor. |
| 3 | + AS5600 ×3 | `3V3_SW` ≈ 3.3 V while awake. `hands` prints three angles. Turning a magnet over each chip moves `H1`–`H3` between about 0 and 2.7 V. |
| 4 | + DRV8833 + X27 | `FLT` reads high (no fault). `home` buzzes the needle against its stop, and `sweep` visits the symbols. You can scope `AIN1`/`AIN2`/`BIN1`/`BIN2`. If it homes the wrong way, set `MOTOR_PHASE_DIR = -1`. |
| 5 | + MAX98357A + speaker | `tone` (or `tone 440`) beeps. `AMP_SD` is high while it plays. `BCLK`/`WS`/`DOUT` carry I2S. |
| 6 | + INMP441 on J4 | `rec` records and plays back. `MIC_SD` carries data. |
| 7 | Crown / power | Press the crown: `status` shows it, and a crown press wakes it from `sleep`. Power switch off: `BAT+` and `VBAT` disconnect (on battery, it goes dark). |

**Firmware iteration.** The ProS3's native USB (CDC serial + the ESP32-S3's built-in USB-JTAG
auto-reset) reaches the wall port through J7 and U7, so `pio run -t upload` works with
the case closed. Over the air (OTA) works once a device key is set. If a bad build ever
bricks USB, use J1 with any 3.3 V USB-serial adapter: TX↔RX, RX↔TX, GND; hold IO0 to GND and
tap RST.

## Regenerating

You need KiCad 10 and Java 17+. Download `freerouting-1.9.0.jar` from
[github.com/freerouting/freerouting/releases](https://github.com/freerouting/freerouting/releases).
Freerouting 2.x's native CLI crashes on Windows.

```powershell
& "$env:LOCALAPPDATA\Programs\KiCad\10.0\bin\python.exe" hardware\pcb\make_pcb.py --freerouting path\to\freerouting-1.9.0.jar
```

The script places everything from `cad/layout.py`, routes the board (power nets 0.6 mm,
signals 0.35 mm, GND pours on both sides), refills the zones, runs DRC and exports `fab/`. If you
move a module in `layout.py`, rerun this script and `cad/build.py` together. The CAD model uses
the same positions.
