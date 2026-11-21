// Persistent settings in NVS (Preferences): cloud credentials and calibration.
#pragma once

#include <Arduino.h>

struct HandCal {
  int8_t sign = 1;      // +1 or -1
  float offset = 0.0f;  // hand deg = sign * sensor deg + offset
};

struct Settings {
  String apiBase;
  String deviceKey;
  String portalPassword;  // random WPA2 password for the setup AP, generated on first boot
  HandCal hands[3];
  float needleOffset;   // needle deg when motor is at 0 (the hard stop)
  bool handsCalibrated = false;
  bool needleCalibrated = false;
};

extern Settings settings;

void settingsLoad();
void settingsSaveCloud();
void settingsSaveHands();
void settingsSaveNeedle();
