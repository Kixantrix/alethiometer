# The Alethiometer — device firmware

Firmware for the physical brass alethiometer: three thumbwheel-driven framing hands read by
AS5600 magnetic sensors, a stepper-driven answer needle, push-to-talk voice questions sent to
the cloud oracle (`api/`), and the interpretation spoken through a hidden speaker.

Target: **Unexpected Maker ProS3** (ESP32-S3, 16 MB flash, 8 MB QSPI PSRAM), PlatformIO +
Arduino framework (arduino-esp32 **3.3.x**, via the pinned
[pioarduino](https://github.com/pioarduino/platform-espressif32) platform `55.03.313`).

## Build and flash

```powershell
pip install platformio
cd firmware
pio run                      # build (first run downloads ~1 GB of toolchains)
```

> **Windows:** the ESP32 framework contains very deep paths. If the package install fails with
> `FileNotFoundError ... connectedhomeip ...`, either enable long paths
> (`HKLM\SYSTEM\CurrentControlSet\Control\FileSystem\LongPathsEnabled = 1`) or use a short
> PlatformIO home: `$env:PLATFORMIO_CORE_DIR = "C:\pio"` before running `pio`.

**Over USB.** The ProS3's USB-C reaches the wall port through the carrier PCB, so USB
flashing and the serial console work before and after assembly. For the very first flash you can
also plug straight into the ProS3 on the bench:

```powershell
pio run -t upload            # hold BOOT, tap RST if the port doesn't appear (or IO0→GND + RST on carrier J1)
pio device monitor           # 115200 baud, USB CDC
```

**After assembly — over the air.** OTA is enabled whenever the device is on Wi-Fi, awake, **and
has a device key** (hostname `alethiometer`, password = the device key; with no key, OTA stays
off). Open the lid (or press the crown) so it wakes, then:

```powershell
$env:ALETHIOMETER_KEY = "<device key>"
pio run -e pros3_ota -t upload
```

If mDNS doesn't resolve on your network, add `--upload-port <ip>` (the IP is printed on the
serial console at connect).

## First run: Wi-Fi and device key

With no saved Wi-Fi credentials the device opens a setup portal automatically after it wakes
(rising three-note chime, white LED). Later you can reopen it with a **triple-click** of the
crown (or `wifi` on the console).

The setup access point is **WPA2-protected** with a random 12-character password generated on
first boot and stored in NVS. The portal prints it to the serial console whenever it opens:
`setup portal: join Wi-Fi "Alethiometer" (password …)`. **Write it down during the bench test**,
before the board goes into the case. To see it later, connect USB and run `wifi`.

1. Join the Wi-Fi network **`Alethiometer`** with that password from a phone or laptop. The
   captive portal opens (otherwise browse to `http://192.168.4.1`).
2. Choose *Configure WiFi*, pick your network and enter its password.
3. Fill in **API base URL** (default `https://func-alethiometer-kx.azurewebsites.net/api`) and
   **Device key**, the value of the Function App's `DEVICE_KEY` app setting. The key field is
   always shown blank and the stored key is never sent to the browser. Leave it blank to keep
   the current key.
4. Save. The portal closes after 5 minutes if unused. Settings live in NVS (`aleth` namespace)
   and survive reflashing.

TLS is verified against embedded roots (`src/ca_roots.h`: DigiCert Global Root G2/G3,
Microsoft RSA/ECC Root CA 2017) — `*.azurewebsites.net` currently chains to DigiCert Global
Root G2.

## Calibration

Run once after assembly, and again if a gear is re-meshed. **Click the crown 5 times** (or type
`cal`). Hold the crown at any step to abort.

> Before calibrating, check the homing direction on first wake: the needle should run gently
> into the X27's internal stop and then sweep away from it. If it instead buzzes at the far end
> of travel, set `MOTOR_PHASE_DIR = -1` in `src/config.h` (or swap one coil's wires).

1. *One chime*: turn all three hands to the **Hourglass** (12 o'clock), click the crown once.
2. *Two chimes*: turn all three hands to the **Moon** (index 10, 100° clockwise), click once.
   The firmware derives each hand's direction and offset; if a hand moved by something other
   than ±100° (±15°) you hear the error chime and calibration restarts at step 1.
3. *Three chimes*: the needle moves to its best guess of the Hourglass. Turn **hand I's**
   thumbwheel to steer the needle (it follows hand I degree-for-degree) until it points exactly
   at the Hourglass, then click once. The needle offset is stored, an arpeggio plays and the
   needle sweeps to the Moon and back as confirmation.

## Using it

| Gesture | Action |
|---|---|
| Open the lid / press the crown | Wake: the needle homes against its stop, sweeps once around and settles on the Hourglass |
| **Hold** the crown | Ask: chime, speak while holding (max 15 s), release to send |
| Triple-click | Wi-Fi / API setup portal |
| 5 clicks | Calibration |
| Press during speech | Stop speaking |
| Close the lid | Needle parks on the Hourglass, deep sleep |
| 120 s without use | Park and deep sleep |

Waking with the lid closed (e.g. the crown is bumped in a pocket) goes straight back to sleep
without moving the needle.

While the question is considered the needle drifts and trembles; then it sweeps through the
reading (each stop approached with a dramatic ≥180° sweep where the gearing allows; extra
swings = deeper meaning, as on the website) and the interpretation is spoken.
If nothing intelligible was heard, a soft descending chime plays. If Wi-Fi or the API fails,
the needle gives a local reading (same FNV-1a algorithm as `js/oracle.js`, seeded with the hand
symbols plus a random number) and three low "offline" bells replace speech.

Battery below 3.45 V: low-battery chime on wake and when asking. Below 3.30 V Wi-Fi is not
started (offline readings only). On USB power these limits are ignored.

## Serial console (115200 baud)

| Command | |
|---|---|
| `hands` | raw mV, sensor and hand angles, symbol per hand (flags ADC clipping) |
| `needle <0-35>` | move the needle to a symbol (dramatic approach) |
| `home` | re-home against the hard stop |
| `sweep` | visit four symbols around the dial and return to the Hourglass |
| `rec` | record 3 s and print length / peak / RMS (dBFS) |
| `tone [hz]` | play a test bell (default 880 Hz) |
| `cal` | start calibration |
| `wifi` | open the setup portal |
| `sleep` | park and deep sleep |
| `status` | battery, USB, lid, needle position, API/key/calibration state |

## Pin map

All pins are defined in `src/config.h`.

| Function | ProS3 GPIO | Notes |
|---|---|---|
| Hand I / II / III — AS5600 OUT | IO1 / IO2 / IO4 | ADC1 ch0/1/3, 11 dB attenuation |
| DRV8833 AIN1 / AIN2 (coil A) | IO5 / IO6 | 20 kHz LEDC PWM |
| DRV8833 BIN1 / BIN2 (coil B) | IO7 / IO8 | nSLEEP → LDO2 3V3, VM → VBAT |
| I2S BCLK | **IO21** | IO11 is not broken out on the ProS3 |
| I2S WS | IO12 | shared by mic and amp |
| I2S DOUT → MAX98357A DIN | IO13 | |
| I2S DIN ← INMP441 SD | IO14 | INMP441 L/R → GND (left) |
| MAX98357A SD_MODE | IO15 | HIGH = on (left channel), LOW = shutdown; held LOW in deep sleep |
| Crown button → GND | IO9 | internal/RTC pull-up, ext1 wake (any-low) |
| Lid reed → GND | IO16 | 1 MΩ pull-up (R7) to 3V3; LOW = closed; ext0 wake on HIGH |
| LDO2 enable | IO17 (on-board) | powers AS5600 ×3, INMP441, RGB LED |
| VBAT sense | IO10 (on-board) | divider 442k/160k |
| VBUS sense | IO33 (on-board) | |
| RGB LED | IO18 (on-board) | status colour |

### Hands

Each AS5600 drives its default analog output (0…VDD over 0…360°). The ESP32-S3 ADC saturates
at ~3.1 V, so each OUT goes through a divider (10 kΩ series, 47 kΩ to GND — R1–R6 on the
carrier PCB, see `hardware/pcb/README.md`) and `HAND_DIVIDER_RATIO` defaults to `57.0f / 47.0f`.
If you build without the dividers, set it to `1.0f` and expect the two symbols in the last
~22° of sensor rotation to read unreliably (the `hands` command flags clipping). Readings are
averaged (16 samples), smoothed along the shortest arc and snapped to the nearest symbol with
±2° hysteresis.

### Needle

X27.168 (315° travel, 1/3° per partial step) driven with sine/cosine microstepping from a 2 kHz
`esp_timer`, so motion never blocks audio or networking. The 38T→19T external mesh gives
`needle = −2 × motor + offset`, about 630° of needle travel. Targets are always finished with a
small move in the + motor direction to take up backlash. Coils are de-energised 0.4 s after the
needle comes to rest (the X27 gear train holds position).

## Symbols

`src/symbols.h` is generated from `js/symbols.js` (the website is the source of truth):

```powershell
python firmware/tools/gen_symbols.py
```

## Power budget (400 mAh LiPo)

| State | Estimated current |
|---|---|
| Deep sleep | ~25–30 µA (ESP32-S3 + ProS3 regulator ~10 µA, VBAT divider ~7 µA, reed pull-up 3.3 µA when closed, MAX98357A/DRV8833 shutdown ~2 µA; LDO2 loads are off) |
| Awake, idle on Wi-Fi | ~70 mA (S3 + modem-sleep Wi-Fi ~45 mA, 3 × AS5600 ~20 mA, mic/LED ~3 mA) |
| Needle moving | +20 mA |
| Recording | ~75 mA |
| Uploading / waiting for the reading | ~130 mA |
| Speaking | ~250–300 mA average (amplifier at speech volume + Wi-Fi streaming) |

A typical session — wake and awakening sweep (5 s), 20 s before asking, 6 s question, 10 s
thinking, 15 s needle reading, 60 s of speech — uses ≈ 6 mAh; letting it idle out (120 s)
instead of closing the lid adds ≈ 2.3 mAh. With ~340 mAh usable above the 3.3–3.45 V
thresholds that is **roughly 40 readings per charge (≈ 55 if the lid is closed afterwards)**.
Standby in deep sleep alone would last over a year; LiPo self-discharge dominates.
