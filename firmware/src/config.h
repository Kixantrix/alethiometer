// The Alethiometer - every pin and tunable lives here.
#pragma once

#include <stdint.h>

// ---------------------------------------------------------------------------
// Pins (Unexpected Maker ProS3). Broken-out GPIOs on the ProS3 headers:
// 0-9, 12-16, 21, 34-42, 43(TX), 44(RX). IO10/11/17/18/33 are NOT on headers.
// ---------------------------------------------------------------------------
constexpr int PIN_HAND[3] = {1, 2, 4};  // AS5600 OUT for hands I/II/III (ADC1 ch0/1/3)

constexpr int PIN_MOTOR_AIN1 = 5;  // DRV8833 coil A
constexpr int PIN_MOTOR_AIN2 = 6;
constexpr int PIN_MOTOR_BIN1 = 7;  // DRV8833 coil B
constexpr int PIN_MOTOR_BIN2 = 8;

// IO11 is not broken out on the ProS3, so BCLK moved to IO21 (same header row as IO12-16).
constexpr int PIN_I2S_BCLK = 21;
constexpr int PIN_I2S_WS = 12;
constexpr int PIN_I2S_DOUT = 13;   // -> MAX98357A DIN
constexpr int PIN_I2S_DIN = 14;    // <- INMP441 SD
constexpr int PIN_AMP_SD = 15;     // MAX98357A SD_MODE: HIGH = on (left channel), LOW = shutdown

constexpr int PIN_CROWN = 9;       // pushbutton to GND, active LOW, RTC GPIO (ext1 wake)
constexpr int PIN_LID = 16;        // reed to GND, external 1 MOhm pull-up: LOW = closed (ext0 wake)
constexpr int PIN_LDO2 = 17;       // ProS3 LDO2 enable (AS5600s, INMP441, RGB LED)
constexpr int PIN_VBAT_SENSE = 10; // ProS3 on-board divider
constexpr int PIN_VBUS_SENSE = 33; // HIGH when USB 5 V present
constexpr int PIN_RGB_DATA = 18;   // on-board WS2812 (powered by LDO2)

// ---------------------------------------------------------------------------
// Power
// ---------------------------------------------------------------------------
constexpr uint32_t LDO2_SETTLE_MS = 20;
constexpr float VBAT_DIVIDER = (442.0f + 160.0f) / 160.0f;  // ProS3 VBAT sense divider
constexpr float VBAT_WARN_V = 3.45f;      // chime warning below this
constexpr float VBAT_NO_WIFI_V = 3.30f;   // refuse Wi-Fi below this
constexpr uint32_t IDLE_SLEEP_MS = 120000;
constexpr uint8_t LED_BRIGHTNESS = 24;    // 0-255; the LED is hidden in the case

// ---------------------------------------------------------------------------
// Hands (AS5600 analog OUT, ratiometric 0..VDD over 0..360 deg)
// ---------------------------------------------------------------------------
constexpr float HAND_VDD_MV = 3300.0f;      // measured AS5600 supply (LDO2)
// Multiply ADC mV by this to undo the resistor divider on each AS5600 OUT
// (10 kΩ series, 47 kΩ to GND — part of the standard wiring, see hardware/WIRING.md).
// ESP32-S3 ADC tops out near 3100 mV; without the divider the last ~22 deg of each
// sensor's rotation read as clipped. Set to 1.0f if you omit the divider.
constexpr float HAND_DIVIDER_RATIO = (10.0f + 47.0f) / 47.0f;
constexpr float HAND_ADC_CLIP_MV = 3080.0f; // readings above this are flagged as clipped
constexpr int HAND_ADC_SAMPLES = 16;
constexpr uint32_t HAND_POLL_MS = 40;
constexpr float HAND_HYSTERESIS_DEG = 2.0f; // beyond the +/-5 deg symbol half-width
constexpr float HAND_FILTER_ALPHA = 0.35f;  // exponential smoothing of hand angle

// ---------------------------------------------------------------------------
// Needle (Switec/Juken X27.168 via DRV8833, sine/cosine PWM microstepping)
// ---------------------------------------------------------------------------
constexpr float X27_TRAVEL_DEG = 315.0f;        // internal hard stop to hard stop
constexpr float X27_DEG_PER_STEP = 1.0f / 3.0f; // one partial step of the 6-state sequence
constexpr int X27_STEPS_PER_CYCLE = 6;          // partial steps per electrical cycle (2 deg)
constexpr float MOTOR_MIN_DEG = 2.0f;           // keep clear of the stop
constexpr float MOTOR_MAX_DEG = 313.0f;
constexpr int MOTOR_PHASE_DIR = 1;              // flip to -1 if "+" moves toward the stop
constexpr float MOTOR_MAX_SPEED_DEG_S = 450.0f; // X27 limit ~600 deg/s at the output
constexpr float HOME_SWEEP_DEG = 1000 * X27_DEG_PER_STEP;  // > full travel
constexpr float HOME_SPEED_DEG_S = 110.0f;
constexpr float BACKLASH_DEG = 1.5f;            // motor deg of overshoot before a + approach
constexpr uint16_t BACKLASH_TAKEUP_MS = 90;
constexpr uint32_t COIL_RELEASE_MS = 400;       // de-energise after the needle is at rest

// Gear train: X27 shaft 38T drives 19T needle gear (external mesh reverses direction).
constexpr float NEEDLE_GEAR_RATIO = 38.0f / 19.0f;
constexpr int NEEDLE_DIR = -1;                  // needle = DIR * RATIO * motor + offset
constexpr float NEEDLE_OFFSET_DEFAULT = 0.0f;   // overwritten by calibration step 3

constexpr uint32_t MOTION_TICK_US = 500;        // 2 kHz microstep update
constexpr uint32_t MOTOR_PWM_HZ = 20000;
constexpr uint8_t MOTOR_PWM_BITS = 10;
constexpr float MOTOR_DRIVE_LEVEL = 1.0f;       // 0..1 PWM amplitude (VM = VBAT)

// Reading animation (mirrors js/dial.js)
constexpr uint16_t SWEEP_MS = 1500;
constexpr float SWING_NEEDLE_DEG = 22.0f;
constexpr uint16_t SWING_OUT_MS = 260;
constexpr uint16_t SWING_BACK_MS = 340;
constexpr uint16_t STOP_PAUSE_MS = 350;
constexpr float DRAMA_MIN_NEEDLE_DEG = 180.0f;
constexpr float THINK_DRIFT_NEEDLE_DEG = 7.0f;
constexpr uint32_t IDLE_TREMBLE_MIN_MS = 15000;
constexpr uint32_t IDLE_TREMBLE_MAX_MS = 40000;
constexpr float IDLE_TREMBLE_NEEDLE_DEG = 1.5f;

// ---------------------------------------------------------------------------
// Audio
// ---------------------------------------------------------------------------
constexpr uint32_t MIC_SAMPLE_RATE = 16000;
constexpr int MIC_SHIFT = 14;               // 32-bit INMP441 slot -> 16-bit (>>16 is unity)
constexpr uint32_t MIC_WARMUP_MS = 100;     // INMP441 start-up garbage to discard
constexpr uint32_t RECORD_MAX_MS = 15000;
constexpr uint32_t RECORD_MIN_MS = 500;
constexpr uint32_t SPEAK_SAMPLE_RATE = 24000;
constexpr float SPEECH_VOLUME = 0.7f;
constexpr float CHIME_VOLUME = 0.25f;
constexpr uint32_t SPEAK_PREBUFFER_MS = 250;
constexpr size_t SPEAK_RING_BYTES = 64 * 1024;

// ---------------------------------------------------------------------------
// Crown gestures
// ---------------------------------------------------------------------------
constexpr uint32_t CROWN_DEBOUNCE_MS = 25;
constexpr uint32_t CROWN_HOLD_MS = 450;     // longer press = push-to-talk
constexpr uint32_t CROWN_CLICK_GAP_MS = 450;
constexpr int CLICKS_PORTAL = 3;
constexpr int CLICKS_CALIBRATE = 5;
constexpr uint32_t CAL_ABORT_HOLD_MS = 1500;

// ---------------------------------------------------------------------------
// Cloud
// ---------------------------------------------------------------------------
#define API_BASE_DEFAULT "https://func-alethiometer-kx.azurewebsites.net/api"
#define PORTAL_AP_NAME "Alethiometer"
#define OTA_HOSTNAME "alethiometer"
constexpr uint32_t ASK_TIMEOUT_MS = 30000;
constexpr uint32_t SPEAK_TIMEOUT_MS = 20000;
constexpr uint32_t WIFI_CONNECT_TIMEOUT_MS = 12000;
constexpr uint32_t PORTAL_TIMEOUT_S = 300;
constexpr int MAX_STOPS = 6;
constexpr size_t MAX_INTERPRETATION = 2000;
