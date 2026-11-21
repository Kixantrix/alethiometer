#include "console.h"

#include "app.h"
#include "audio.h"
#include "config.h"
#include "hands.h"
#include "needle.h"
#include "power.h"
#include "settings.h"
#include "symbols.h"

namespace {

String line;

void help() {
  Serial.println(
      "commands: hands | needle <0-35> | home | sweep | rec | tone [hz] | cal | wifi | sleep | status");
}

void printHands() {
  handsSampleNow();
  for (int i = 0; i < 3; i++) {
    const HandReading &h = handsGet(i);
    Serial.printf("hand %d: %7.1f mV  sensor %6.1f deg  hand %6.1f deg  -> %2d %s%s\n", i + 1, h.millivolts,
                  h.sensorDeg, h.handDeg, h.symbol, SYMBOL_NAMES[h.symbol], h.clipped ? "  (ADC CLIPPED)" : "");
  }
}

void status() {
  Serial.printf("battery %.2f V, USB %s, lid %s, needle %.1f deg (motor %.1f), offset %.1f\n",
                powerBatteryVolts(), powerUsbPresent() ? "yes" : "no", powerLidClosed() ? "closed" : "open",
                needleAngleDeg(), needleMotorDeg(), settings.needleOffset);
  Serial.printf("api %s, device key %s, hands %scalibrated, needle %scalibrated\n", settings.apiBase.c_str(),
                settings.deviceKey.length() ? "set" : "MISSING", settings.handsCalibrated ? "" : "NOT ",
                settings.needleCalibrated ? "" : "NOT ");
}

void recordTest() {
  Serial.println("recording 3 s...");
  if (!audioRecordStart()) {
    Serial.println("I2S RX failed");
    return;
  }
  const uint32_t start = millis();
  while (millis() - start < 3000 && audioRecordPoll()) {
  }
  audioRecordStop();
  int peak;
  float rms;
  audioRecordStats(peak, rms);
  Serial.printf("%lu ms, %u bytes WAV, peak %d (%.1f dBFS), rms %.1f (%.1f dBFS)\n",
                static_cast<unsigned long>(audioRecordedMs()), audioWavSize(), peak,
                20 * log10f(fmaxf(peak, 1) / 32768.0f), rms, 20 * log10f(fmaxf(rms, 1) / 32768.0f));
}

void sweep() {
  needleSetMood(NeedleMood::Still);
  needleStop();
  for (int i = 0; i < SYMBOL_COUNT; i += 9) needleGoToSymbol(i, Approach::Dramatic, SWEEP_MS, -1, 300);
  needleGoToSymbol(SYMBOL_HOURGLASS, Approach::Nearest, SWEEP_MS);
}

void run(String cmd) {
  cmd.trim();
  if (cmd.isEmpty()) return;
  appTouch();
  const int space = cmd.indexOf(' ');
  const String verb = space < 0 ? cmd : cmd.substring(0, space);
  const String arg = space < 0 ? String() : cmd.substring(space + 1);

  if (verb == "hands") {
    printHands();
  } else if (verb == "needle") {
    const int i = arg.toInt();
    if (arg.isEmpty() || i < 0 || i >= SYMBOL_COUNT) {
      Serial.println("usage: needle <0-35>");
      return;
    }
    needleSetMood(NeedleMood::Still);
    needleGoToSymbol(i, Approach::Dramatic, SWEEP_MS);
    Serial.printf("needle -> %d %s\n", i, SYMBOL_NAMES[i]);
  } else if (verb == "home") {
    needleHome();
  } else if (verb == "sweep") {
    sweep();
  } else if (verb == "rec") {
    recordTest();
  } else if (verb == "tone") {
    audioTone(arg.length() ? arg.toFloat() : 880.0f, 600, CHIME_VOLUME);
  } else if (verb == "cal") {
    if (appIsIdle()) appStartCalibration();
    else Serial.println("busy - try again when idle");
  } else if (verb == "wifi") {
    if (appIsIdle()) appStartPortal();
    else Serial.println("busy - try again when idle");
  } else if (verb == "sleep") {
    appSleep();
  } else if (verb == "status") {
    status();
  } else {
    help();
  }
}

}  // namespace

void consoleLoop() {
  while (Serial.available()) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\r' || c == '\n') {
      run(line);
      line = "";
    } else if (line.length() < 64) {
      line += c;
    }
  }
}
