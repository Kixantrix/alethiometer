#include "calibration.h"

#include <math.h>

#include "audio.h"
#include "config.h"
#include "hands.h"
#include "needle.h"
#include "power.h"
#include "settings.h"
#include "symbols.h"

namespace {

enum class Step { Off, Hourglass, Moon, NeedleSettle, Needle };

Step step = Step::Off;
float sensorAtHourglass[3];
float jogLastHandDeg = 0;
float jogAccumDeg = 0;
float jogApplied = 0;
float jogBaseMotor = 0;

constexpr float MOON_DEG = SYMBOL_MOON * SYMBOL_STEP_DEG;
constexpr float MOON_TOLERANCE_DEG = 15.0f;
constexpr float JOG_DEADBAND_DEG = 0.25f;

void enter(Step s) {
  step = s;
  switch (s) {
    case Step::Hourglass:
      Serial.println("[cal] 1/3: set all three hands to the Hourglass, then press the crown");
      powerLed(255, 0, 255);
      audioChime(Chime::CalStep);
      break;
    case Step::Moon:
      Serial.println("[cal] 2/3: set all three hands to the Moon, then press the crown");
      audioChime(Chime::CalStep);
      audioChime(Chime::CalStep);
      break;
    case Step::NeedleSettle:
      Serial.println("[cal] 3/3: turn hand I to steer the needle onto the Hourglass, then press the crown");
      needleSetMood(NeedleMood::Still);
      needleStop();
      needleGoToSymbol(SYMBOL_HOURGLASS, Approach::Nearest, 1200);
      audioChime(Chime::CalStep);
      audioChime(Chime::CalStep);
      audioChime(Chime::CalStep);
      break;
    case Step::Needle:
      handsSampleNow();
      jogLastHandDeg = handsGet(0).handDeg;
      jogAccumDeg = jogApplied = 0;
      jogBaseMotor = needleMotorDeg();
      break;
    case Step::Off:
      break;
  }
}

bool solveHands() {
  HandCal result[3];
  for (int i = 0; i < 3; i++) {
    const float atMoon = handsReadSensorDeg(i);
    const float delta = wrap180(atMoon - sensorAtHourglass[i]);
    if (fabsf(delta - MOON_DEG) <= MOON_TOLERANCE_DEG) {
      result[i].sign = 1;
    } else if (fabsf(delta + MOON_DEG) <= MOON_TOLERANCE_DEG) {
      result[i].sign = -1;
    } else {
      Serial.printf("[cal] hand %d moved %.1f deg (expected +/-%.0f) - starting over\n", i + 1, delta, MOON_DEG);
      return false;
    }
    // Average the offsets implied by both calibration points (on the circle).
    const float o1 = wrap360(0.0f - result[i].sign * sensorAtHourglass[i]);
    const float o2 = wrap360(MOON_DEG - result[i].sign * atMoon);
    result[i].offset = wrap360(o1 + wrap180(o2 - o1) / 2);
    Serial.printf("[cal] hand %d: sign %+d offset %.1f deg\n", i + 1, result[i].sign, result[i].offset);
  }
  for (int i = 0; i < 3; i++) settings.hands[i] = result[i];
  settingsSaveHands();
  return true;
}

void jogNeedle() {
  const float deg = handsGet(0).handDeg;
  jogAccumDeg += wrap180(deg - jogLastHandDeg);
  jogLastHandDeg = deg;
  if (fabsf(jogAccumDeg - jogApplied) < JOG_DEADBAND_DEG) return;
  jogApplied = jogAccumDeg;
  // The needle follows hand I 1:1 in dial degrees.
  needleFollowMotor(jogBaseMotor + jogApplied / (NEEDLE_DIR * NEEDLE_GEAR_RATIO));
}

void finishNeedle() {
  needleTakeUpBacklash();
  needleWaitIdle(2000);
  const float m = needleMotorDeg();
  settings.needleOffset = wrap360(0.0f - NEEDLE_DIR * NEEDLE_GEAR_RATIO * m);
  settingsSaveNeedle();
  Serial.printf("[cal] needle offset %.2f deg (motor %.2f deg) - saved\n", settings.needleOffset, m);
  audioChime(Chime::CalDone);
  needleGoToSymbol(SYMBOL_MOON, Approach::Dramatic, SWEEP_MS, -1, 300);
  needleGoToSymbol(SYMBOL_HOURGLASS, Approach::Dramatic, SWEEP_MS);
  step = Step::Off;
}

}  // namespace

void calStart() {
  needleSetMood(NeedleMood::Still);
  enter(Step::Hourglass);
}

bool calActive() { return step != Step::Off; }

void calUpdate(const CrownSignal &sig) {
  if (step == Step::Off) return;
  if (sig.event == CrownEvent::HoldStart) {
    Serial.println("[cal] aborted");
    audioChime(Chime::Error);
    step = Step::Off;
    return;
  }
  const bool confirm = sig.event == CrownEvent::Clicks && sig.clicks == 1;
  switch (step) {
    case Step::Hourglass:
      if (confirm) {
        for (int i = 0; i < 3; i++) sensorAtHourglass[i] = handsReadSensorDeg(i);
        enter(Step::Moon);
      }
      break;
    case Step::Moon:
      if (confirm) {
        if (solveHands()) {
          enter(Step::NeedleSettle);
        } else {
          audioChime(Chime::Error);
          enter(Step::Hourglass);
        }
      }
      break;
    case Step::NeedleSettle:
      if (!needleBusy()) enter(Step::Needle);
      break;
    case Step::Needle:
      if (confirm) finishNeedle();
      else jogNeedle();
      break;
    case Step::Off:
      break;
  }
}
