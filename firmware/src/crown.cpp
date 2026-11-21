#include "crown.h"

#include "config.h"

namespace {
bool stable = false;        // debounced: true = pressed
bool lastRaw = false;
uint32_t rawChangedMs = 0;
uint32_t pressStartMs = 0;
uint32_t lastReleaseMs = 0;
bool holdFired = false;
bool ignoreUntilRelease = false;
int clicks = 0;

bool readRaw() { return digitalRead(PIN_CROWN) == LOW; }
}  // namespace

void crownBegin() {
  stable = lastRaw = readRaw();
  rawChangedMs = millis();
  ignoreUntilRelease = stable;
  clicks = 0;
  holdFired = false;
}

bool crownPressed() { return stable; }

CrownSignal crownUpdate() {
  CrownSignal sig;
  const uint32_t now = millis();
  const bool raw = readRaw();
  if (raw != lastRaw) {
    lastRaw = raw;
    rawChangedMs = now;
  }
  if (raw != stable && now - rawChangedMs >= CROWN_DEBOUNCE_MS) {
    stable = raw;
    if (stable) {
      pressStartMs = now;
    } else if (ignoreUntilRelease) {
      ignoreUntilRelease = false;
    } else if (holdFired) {
      holdFired = false;
      sig.event = CrownEvent::HoldEnd;
      sig.heldMs = now - pressStartMs;
      return sig;
    } else {
      clicks++;
      lastReleaseMs = now;
    }
  }
  if (ignoreUntilRelease) return sig;

  if (stable && !holdFired && now - pressStartMs >= CROWN_HOLD_MS) {
    holdFired = true;
    clicks = 0;  // a hold ends any click sequence
    sig.event = CrownEvent::HoldStart;
    return sig;
  }
  if (!stable && clicks > 0 && now - lastReleaseMs >= CROWN_CLICK_GAP_MS) {
    sig.event = CrownEvent::Clicks;
    sig.clicks = clicks;
    clicks = 0;
  }
  return sig;
}
