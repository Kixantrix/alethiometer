#include "settings.h"

#include <Preferences.h>

#include "config.h"

Settings settings;

namespace {
constexpr const char *NS = "aleth";
Preferences prefs;
}  // namespace

void settingsLoad() {
  prefs.begin(NS, true);
  settings.apiBase = prefs.getString("api", API_BASE_DEFAULT);
  settings.deviceKey = prefs.getString("key", "");
  settings.handsCalibrated = prefs.getBool("hcal", false);
  for (int i = 0; i < 3; i++) {
    char k[8];
    snprintf(k, sizeof k, "hs%d", i);
    settings.hands[i].sign = prefs.getChar(k, 1) < 0 ? -1 : 1;
    snprintf(k, sizeof k, "ho%d", i);
    settings.hands[i].offset = prefs.getFloat(k, 0.0f);
  }
  settings.needleCalibrated = prefs.getBool("ncal", false);
  settings.needleOffset = prefs.getFloat("noff", NEEDLE_OFFSET_DEFAULT);
  settings.portalPassword = prefs.getString("appw", "");
  prefs.end();
  if (settings.apiBase.isEmpty()) settings.apiBase = API_BASE_DEFAULT;
  if (settings.portalPassword.length() < 8) {
    // Unambiguous alphabet; 12 chars from the hardware RNG (~62 bits).
    static const char kAlphabet[] = "abcdefghjkmnpqrstuvwxyz23456789";
    String pw;
    for (int i = 0; i < 12; i++) pw += kAlphabet[esp_random() % (sizeof kAlphabet - 1)];
    settings.portalPassword = pw;
    prefs.begin(NS, false);
    prefs.putString("appw", pw);
    prefs.end();
  }
}

void settingsSaveCloud() {
  prefs.begin(NS, false);
  prefs.putString("api", settings.apiBase);
  prefs.putString("key", settings.deviceKey);
  prefs.end();
}

void settingsSaveHands() {
  prefs.begin(NS, false);
  for (int i = 0; i < 3; i++) {
    char k[8];
    snprintf(k, sizeof k, "hs%d", i);
    prefs.putChar(k, settings.hands[i].sign);
    snprintf(k, sizeof k, "ho%d", i);
    prefs.putFloat(k, settings.hands[i].offset);
  }
  prefs.putBool("hcal", true);
  prefs.end();
  settings.handsCalibrated = true;
}

void settingsSaveNeedle() {
  prefs.begin(NS, false);
  prefs.putFloat("noff", settings.needleOffset);
  prefs.putBool("ncal", true);
  prefs.end();
  settings.needleCalibrated = true;
}
