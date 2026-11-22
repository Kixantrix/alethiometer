#include "app.h"

#include "audio.h"
#include "calibration.h"
#include "cloud.h"
#include "config.h"
#include "console.h"
#include "crown.h"
#include "hands.h"
#include "needle.h"
#include "oracle.h"
#include "power.h"
#include "settings.h"
#include "symbols.h"

namespace {

enum class State { Awakening, Idle, Listening, Thinking, Reading, Calibrating };

State state = State::Awakening;
uint32_t lastActivityMs = 0;
bool wifiAllowed = false;
bool haveWifiCredentials = false;
bool portalPending = false;
int askHands[3];
Reading reading;
int lastAnnouncedStop = -1;

void led(State s) {
  switch (s) {
    case State::Awakening: powerLed(255, 160, 40); break;
    case State::Idle: powerLed(60, 35, 5); break;
    case State::Listening: powerLed(255, 0, 0); break;
    case State::Thinking: powerLed(0, 60, 255); break;
    case State::Reading: powerLed(0, 200, 200); break;
    case State::Calibrating: powerLed(255, 0, 255); break;
  }
}

void enter(State s) {
  state = s;
  lastActivityMs = millis();
  led(s);
}

void enterIdle() {
  needleSetMood(NeedleMood::Idle);
  enter(State::Idle);
}

void printReading(const char *label) {
  Serial.printf("[app] %s reading (%d stops)\n", label, reading.count);
  if (reading.question.length()) Serial.printf("[app] question: %s\n", reading.question.c_str());
}

void startReading() {
  needleSetMood(NeedleMood::Still);
  needleStop();
  needlePlayReading(reading.stops, reading.count);
  lastAnnouncedStop = -1;
  enter(State::Reading);
}

void startOffline() {
  oracleOfflineReading(askHands, reading);
  printReading("offline");
  startReading();
}

void startListening() {
  if (powerBatteryLow()) audioChime(Chime::LowBattery);
  audioChime(Chime::ListenStart);
  if (!audioRecordStart()) {
    audioChime(Chime::Error);
    enterIdle();
    return;
  }
  Serial.println("[app] listening...");
  enter(State::Listening);
}

void finishListening() {
  audioRecordStop();
  audioChime(Chime::ListenStop);
  const uint32_t ms = audioRecordedMs();
  Serial.printf("[app] recorded %lu ms\n", static_cast<unsigned long>(ms));
  if (ms < RECORD_MIN_MS) {
    audioChime(Chime::NoSpeech);
    enterIdle();
    return;
  }
  handsSymbols(askHands);
  Serial.printf("[app] hands: %s | %s | %s\n", SYMBOL_NAMES[askHands[0]], SYMBOL_NAMES[askHands[1]],
                SYMBOL_NAMES[askHands[2]]);
  wifiAllowed = powerWifiAllowed();
  if (!wifiAllowed || !haveWifiCredentials) {
    startOffline();
    return;
  }
  cloudConnect();
  cloudAskStart(audioWavData(), audioWavSize(), askHands);
  needleSetMood(NeedleMood::Thinking);
  enter(State::Thinking);
}

void speak() {
  powerLed(0, 255, 60);
  String error;
  const bool ok = cloudSpeak(
      reading.interpretation, [] { return digitalRead(PIN_CROWN) == LOW; }, error);
  if (!ok) {
    Serial.printf("[app] speech failed: %s\n", error.c_str());
    audioChime(Chime::Error);
  }
}

void handleIdle(const CrownSignal &sig) {
  if (sig.event == CrownEvent::HoldStart) {
    startListening();
  } else if (sig.event == CrownEvent::Clicks) {
    Serial.printf("[app] %d click(s)\n", sig.clicks);
    if (sig.clicks == CLICKS_SLEEP) appSleep();
    else if (sig.clicks == CLICKS_PORTAL) appStartPortal();
    else if (sig.clicks == CLICKS_MUTE) appToggleMute();
    else if (sig.clicks == CLICKS_CALIBRATE) appStartCalibration();
  } else if (millis() - lastActivityMs > IDLE_SLEEP_MS) {
    Serial.println("[app] idle timeout");
    appSleep();
  }
}

void handleThinking() {
  String error;
  switch (cloudAskPoll(reading, error)) {
    case AskStatus::Ok:
      printReading("cloud");
      Serial.printf("[app] interpretation: %s\n", reading.interpretation.c_str());
      startReading();
      break;
    case AskStatus::NoSpeech:
      Serial.println("[app] the alethiometer heard nothing");
      needleSetMood(NeedleMood::Still);
      audioChime(Chime::NoSpeech);
      enterIdle();
      break;
    case AskStatus::Failed:
      Serial.printf("[app] cloud failed (%s) - consulting the needle alone\n", error.c_str());
      startOffline();
      break;
    default:
      break;
  }
}

void handleReading() {
  int tag;
  if (needleArrived(tag) && tag >= 0 && tag < reading.count && tag != lastAnnouncedStop) {
    lastAnnouncedStop = tag;
    const Stop &s = reading.stops[tag];
    Serial.printf("[app] stop %d: %s (%d swing%s)\n", tag + 1, SYMBOL_NAMES[s.index], s.swings, s.swings > 1 ? "s" : "");
  }
  if (needleBusy()) return;
  if (reading.fromCloud && !settings.muted) speak();
  else audioChime(Chime::Offline);
  enterIdle();
}

}  // namespace

void appSetup() {
  Serial.begin(115200);
  powerBegin();
  settingsLoad();
  const WakeReason wake = powerWakeReason();
  Serial.printf("\n[app] The Alethiometer wakes (reason %d), battery %.2f V%s%s\n", static_cast<int>(wake),
                powerBatteryVolts(), powerUsbPresent() ? " (USB)" : "", settings.muted ? ", muted" : "");

  crownBegin();
  handsBegin();
  audioBegin();
  needleBegin();
  needleAwaken();
  enter(State::Awakening);
  audioChime(Chime::Wake);
  if (powerBatteryLow()) audioChime(Chime::LowBattery);

  wifiAllowed = powerWifiAllowed();
  if (!wifiAllowed) {
    Serial.println("[app] battery too low for Wi-Fi - offline readings only");
  } else {
    haveWifiCredentials = cloudHasWifiCredentials();
    if (haveWifiCredentials) cloudConnect();
    else portalPending = true;
  }
  if (!settings.handsCalibrated || !settings.needleCalibrated) {
    Serial.println("[app] not calibrated yet - click the crown 5 times (or type 'cal')");
  }
}

void appLoop() {
  cloudLoop();
  if (cloudOtaActive()) return;
  handsUpdate();
  consoleLoop();
  const CrownSignal sig = crownUpdate();
  if (sig.event != CrownEvent::None) lastActivityMs = millis();

  switch (state) {
    case State::Awakening:
      if (!needleBusy()) {
        enterIdle();
        if (portalPending) {
          portalPending = false;
          appStartPortal();
        }
      }
      break;
    case State::Idle:
      handleIdle(sig);
      break;
    case State::Listening:
      if (sig.event == CrownEvent::HoldEnd || !audioRecordPoll()) finishListening();
      break;
    case State::Thinking:
      handleThinking();
      break;
    case State::Reading:
      handleReading();
      break;
    case State::Calibrating:
      calUpdate(sig);
      if (!calActive()) enterIdle();
      break;
  }
}

void appStartCalibration() {
  if (state != State::Idle) return;
  needleSetMood(NeedleMood::Still);
  enter(State::Calibrating);
  calStart();
}

void appStartPortal() {
  if (state != State::Idle) return;
  if (!powerWifiAllowed()) {
    audioChime(Chime::LowBattery);
    return;
  }
  needleSetMood(NeedleMood::Still);
  powerLed(255, 255, 255);
  audioChime(Chime::Portal);
  const bool ok = cloudRunPortal();
  haveWifiCredentials = cloudHasWifiCredentials();
  audioChime(ok ? Chime::CalDone : Chime::Error);
  if (haveWifiCredentials) cloudConnect();
  enterIdle();
}

void appSleep() {
  needleSetMood(NeedleMood::Still);
  needleStop();
  needleGoToSymbol(SYMBOL_HOURGLASS, Approach::Nearest, 1200);
  needleWaitIdle(5000);
  audioOff();
  cloudOff();
  powerDeepSleep();
}

void appToggleMute() {
  settings.muted = !settings.muted;
  settingsSaveMuted();
  Serial.printf("[app] %s\n", settings.muted ? "muted" : "sound on");
  if (settings.muted) {   // silent acknowledgement: the needle nods to the Moon and back
    needleSetMood(NeedleMood::Still);
    needleGoToSymbol(SYMBOL_MOON, Approach::Nearest, 900, -1, 600);
    needleGoToSymbol(SYMBOL_HOURGLASS, Approach::Nearest, 900);
  } else {
    audioChime(Chime::CalDone);
  }
  enterIdle();
}

void appTouch() { lastActivityMs = millis(); }

bool appIsIdle() { return state == State::Idle; }
