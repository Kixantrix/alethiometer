// The three framing hands, read through AS5600 analog outputs.
#pragma once

#include <Arduino.h>

struct HandReading {
  float millivolts;   // averaged ADC reading (after divider correction)
  float sensorDeg;    // raw magnet angle 0..360
  float handDeg;      // calibrated hand angle 0..360 (clockwise from 12 o'clock)
  int symbol;         // stable symbol index (with hysteresis)
  bool clipped;       // ADC near full scale - angle unreliable
};

void handsBegin();
void handsUpdate();                     // rate-limited poll; call from loop()
void handsSampleNow();                  // force an immediate fresh read
const HandReading &handsGet(int hand);
float handsReadSensorDeg(int hand);     // fresh averaged raw sensor angle (calibration)
void handsSymbols(int out[3]);

// Angle helpers shared with calibration and the needle.
float wrap360(float deg);
float wrap180(float deg);
