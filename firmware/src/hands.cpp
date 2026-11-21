#include "hands.h"

#include <math.h>

#include "config.h"
#include "settings.h"
#include "symbols.h"

namespace {
HandReading readings[3];
bool primed[3] = {false, false, false};
uint32_t lastPollMs = 0;

float readMillivolts(int hand) {
  uint32_t sum = 0;
  for (int i = 0; i < HAND_ADC_SAMPLES; i++) sum += analogReadMilliVolts(PIN_HAND[hand]);
  return static_cast<float>(sum) / HAND_ADC_SAMPLES * HAND_DIVIDER_RATIO;
}

float millivoltsToDeg(float mv) { return wrap360(mv / HAND_VDD_MV * 360.0f); }

int nearestSymbol(float deg) {
  return static_cast<int>(lroundf(deg / SYMBOL_STEP_DEG)) % SYMBOL_COUNT;
}

void poll(int hand) {
  HandReading &r = readings[hand];
  const float mv = readMillivolts(hand);
  const float sensor = millivoltsToDeg(mv);
  const HandCal &cal = settings.hands[hand];
  const float deg = wrap360(cal.sign * sensor + cal.offset);

  r.millivolts = mv;
  r.sensorDeg = sensor;
  r.clipped = mv / HAND_DIVIDER_RATIO > HAND_ADC_CLIP_MV;
  if (!primed[hand]) {
    r.handDeg = deg;
    r.symbol = nearestSymbol(deg);
    primed[hand] = true;
    return;
  }
  // Smooth along the shortest arc so the 359->0 seam doesn't jump.
  r.handDeg = wrap360(r.handDeg + HAND_FILTER_ALPHA * wrap180(deg - r.handDeg));
  const float fromCurrent = fabsf(wrap180(r.handDeg - r.symbol * SYMBOL_STEP_DEG));
  if (fromCurrent > SYMBOL_STEP_DEG / 2 + HAND_HYSTERESIS_DEG) r.symbol = nearestSymbol(r.handDeg);
}
}  // namespace

float wrap360(float deg) {
  float d = fmodf(deg, 360.0f);
  return d < 0 ? d + 360.0f : d;
}

float wrap180(float deg) {
  float d = wrap360(deg + 180.0f) - 180.0f;
  return d;
}

void handsBegin() {
  for (int i = 0; i < 3; i++) {
    pinMode(PIN_HAND[i], INPUT);
    analogSetPinAttenuation(PIN_HAND[i], ADC_11db);
    primed[i] = false;
  }
  handsSampleNow();
}

void handsSampleNow() {
  for (int i = 0; i < 3; i++) poll(i);
  lastPollMs = millis();
}

void handsUpdate() {
  if (millis() - lastPollMs < HAND_POLL_MS) return;
  handsSampleNow();
}

const HandReading &handsGet(int hand) { return readings[hand]; }

float handsReadSensorDeg(int hand) {
  // Average several polls on the circle for a steady calibration point.
  float sx = 0, sy = 0;
  for (int i = 0; i < 8; i++) {
    const float rad = millivoltsToDeg(readMillivolts(hand)) * DEG_TO_RAD;
    sx += cosf(rad);
    sy += sinf(rad);
    delay(2);
  }
  return wrap360(atan2f(sy, sx) * RAD_TO_DEG);
}

void handsSymbols(int out[3]) {
  for (int i = 0; i < 3; i++) out[i] = readings[i].symbol;
}
