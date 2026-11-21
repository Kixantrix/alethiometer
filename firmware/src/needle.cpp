#include "needle.h"

#include <esp_random.h>
#include <esp_timer.h>
#include <math.h>

#include "config.h"
#include "hands.h"
#include "settings.h"
#include "symbols.h"

namespace {

enum class Ease : uint8_t { Linear, OutCubic, InOut };

struct Segment {
  float target;     // motor deg
  uint16_t durMs;
  uint16_t holdMs;  // rest at the target before the next segment
  Ease ease;
  int8_t tag;       // >= 0: report an arrival with this tag
};

constexpr int QUEUE_LEN = 128;
constexpr float ELEC_RAD_PER_MOTOR_DEG = TWO_PI / (X27_STEPS_PER_CYCLE * X27_DEG_PER_STEP);
constexpr float FOLLOW_SPEED_DEG_S = 90.0f;

portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
esp_timer_handle_t timer = nullptr;

// Shared state: written under `mux`.
Segment queue[QUEUE_LEN];
int qHead = 0, qTail = 0;
float plannedEnd = MOTOR_MIN_DEG;   // where the motor will be once the queue drains
volatile float pos = MOTOR_MIN_DEG;
bool active = false;
Segment cur;
float segFrom = 0;
uint32_t segElapsedUs = 0;
bool holding = false;
uint32_t restUs = 0;
NeedleMood mood = NeedleMood::Still;
float moodCenter = MOTOR_MIN_DEG;
uint32_t nextTrembleUs = 0;
volatile uint32_t arrivalCount = 0;
volatile int arrivalTag = -1;
bool energized = false;

uint32_t seenArrivals = 0;  // main-thread only

float easeApply(Ease e, float t) {
  switch (e) {
    case Ease::OutCubic: { const float u = 1 - t; return 1 - u * u * u; }
    case Ease::InOut: return t < 0.5f ? 2 * t * t : 1 - powf(-2 * t + 2, 2) / 2;
    default: return t;
  }
}

float easePeak(Ease e) {  // max d(ease)/dt, for speed limiting
  switch (e) {
    case Ease::OutCubic: return 3.0f;
    case Ease::InOut: return 2.0f;
    default: return 1.0f;
  }
}

uint32_t randRange(uint32_t lo, uint32_t hi) { return lo + esp_random() % (hi - lo + 1); }

void writeCoil(int in1, int in2, float level) {
  const uint32_t maxDuty = (1u << MOTOR_PWM_BITS) - 1;
  const uint32_t duty = static_cast<uint32_t>(fminf(fabsf(level), 1.0f) * MOTOR_DRIVE_LEVEL * maxDuty);
  ledcWrite(in1, level >= 0 ? duty : 0);
  ledcWrite(in2, level >= 0 ? 0 : duty);
}

void driveCoils(float motorDeg) {
  const float e = motorDeg * ELEC_RAD_PER_MOTOR_DEG;
  writeCoil(PIN_MOTOR_AIN1, PIN_MOTOR_AIN2, cosf(e));
  writeCoil(PIN_MOTOR_BIN1, PIN_MOTOR_BIN2, MOTOR_PHASE_DIR * sinf(e));
}

void releaseCoils() {
  ledcWrite(PIN_MOTOR_AIN1, 0);
  ledcWrite(PIN_MOTOR_AIN2, 0);
  ledcWrite(PIN_MOTOR_BIN1, 0);
  ledcWrite(PIN_MOTOR_BIN2, 0);
}

// --- queue (call with mux held) ---
bool pushLocked(const Segment &s) {
  const int next = (qTail + 1) % QUEUE_LEN;
  if (next == qHead) return false;
  queue[qTail] = s;
  qTail = next;
  plannedEnd = s.target;
  return true;
}

uint16_t limitedDuration(float from, float to, uint16_t ms, Ease ease) {
  const float minMs = fabsf(to - from) * easePeak(ease) / MOTOR_MAX_SPEED_DEG_S * 1000.0f;
  return static_cast<uint16_t>(fminf(60000.0f, fmaxf(ms, minMs)));
}

// Queue a move; when it ends in the - direction, overshoot and finish with a short + move
// so every target is approached from the same side of the gear backlash.
void enqueueLocked(float target, uint16_t ms, Ease ease, uint16_t holdMs, int tag, bool antiBacklash) {
  target = constrain(target, MOTOR_MIN_DEG, MOTOR_MAX_DEG);
  const float from = plannedEnd;
  if (antiBacklash && target < from - 0.01f) {
    const float pre = fmaxf(target - BACKLASH_DEG, 0.0f);
    pushLocked({pre, limitedDuration(from, pre, ms, ease), 0, ease, -1});
    pushLocked({target, BACKLASH_TAKEUP_MS, holdMs, Ease::Linear, static_cast<int8_t>(tag)});
  } else {
    pushLocked({target, limitedDuration(from, target, ms, ease), holdMs, ease, static_cast<int8_t>(tag)});
  }
}

void enqueue(float target, uint16_t ms, Ease ease, uint16_t holdMs = 0, int tag = -1, bool antiBacklash = true) {
  portENTER_CRITICAL(&mux);
  enqueueLocked(target, ms, ease, holdMs, tag, antiBacklash);
  portEXIT_CRITICAL(&mux);
}

// Ambient motion generated when the queue is empty (mux held).
void ambientLocked() {
  if (mood == NeedleMood::Thinking) {
    const float swing = THINK_DRIFT_NEEDLE_DEG / NEEDLE_GEAR_RATIO;
    const float jitter = (static_cast<float>(esp_random() % 2001) / 1000.0f - 1.0f) * swing;
    enqueueLocked(moodCenter + jitter, randRange(500, 1400), Ease::InOut, randRange(80, 450), -1, false);
  } else if (mood == NeedleMood::Idle && restUs > nextTrembleUs) {
    const float d = IDLE_TREMBLE_NEEDLE_DEG / NEEDLE_GEAR_RATIO;
    const float c = plannedEnd;
    enqueueLocked(c - d, 120, Ease::InOut, 0, -1, false);
    enqueueLocked(c + d * 0.6f, 160, Ease::InOut, 0, -1, false);
    enqueueLocked(c, 200, Ease::OutCubic, 0, -1, false);
    nextTrembleUs = randRange(IDLE_TREMBLE_MIN_MS, IDLE_TREMBLE_MAX_MS) * 1000u;
  }
}

void onTick(void *) {
  bool drive = false;
  bool release = false;
  float p;
  portENTER_CRITICAL(&mux);
  if (!active && qHead == qTail) ambientLocked();
  if (!active && qHead != qTail) {
    cur = queue[qHead];
    qHead = (qHead + 1) % QUEUE_LEN;
    segFrom = pos;
    segElapsedUs = 0;
    holding = false;
    active = true;
  }
  if (active) {
    restUs = 0;
    segElapsedUs += MOTION_TICK_US;
    if (!holding) {
      const float t = cur.durMs == 0 ? 1.0f : fminf(1.0f, segElapsedUs / (cur.durMs * 1000.0f));
      pos = segFrom + (cur.target - segFrom) * easeApply(cur.ease, t);
      if (t >= 1.0f) {
        pos = cur.target;
        if (cur.tag >= 0) {
          arrivalTag = cur.tag;
          arrivalCount = arrivalCount + 1;
        }
        holding = true;
        segElapsedUs = 0;
      }
    } else if (segElapsedUs >= cur.holdMs * 1000u) {
      active = false;
    }
    drive = true;
  } else {
    restUs += MOTION_TICK_US;
    release = energized && restUs > COIL_RELEASE_MS * 1000u;
  }
  p = pos;
  portEXIT_CRITICAL(&mux);

  static float lastDriven = NAN;
  if (drive) {
    if (!energized || p != lastDriven) driveCoils(p);
    lastDriven = p;
    energized = true;
  } else if (release) {
    releaseCoils();
    energized = false;
  }
}

}  // namespace

float needleForMotor(float motorDeg) {
  return NEEDLE_DIR * NEEDLE_GEAR_RATIO * motorDeg + settings.needleOffset;
}

float motorForNeedle(float needleDeg) {
  return (needleDeg - settings.needleOffset) / (NEEDLE_DIR * NEEDLE_GEAR_RATIO);
}

void needleBegin() {
  ledcAttach(PIN_MOTOR_AIN1, MOTOR_PWM_HZ, MOTOR_PWM_BITS);
  ledcAttach(PIN_MOTOR_AIN2, MOTOR_PWM_HZ, MOTOR_PWM_BITS);
  ledcAttach(PIN_MOTOR_BIN1, MOTOR_PWM_HZ, MOTOR_PWM_BITS);
  ledcAttach(PIN_MOTOR_BIN2, MOTOR_PWM_HZ, MOTOR_PWM_BITS);
  releaseCoils();
  const esp_timer_create_args_t args = {
      .callback = onTick, .arg = nullptr, .dispatch_method = ESP_TIMER_TASK,
      .name = "needle", .skip_unhandled_events = true};
  esp_timer_create(&args, &timer);
  esp_timer_start_periodic(timer, MOTION_TICK_US);
}

void needleStop() {
  portENTER_CRITICAL(&mux);
  qHead = qTail = 0;
  active = false;
  plannedEnd = pos;
  moodCenter = pos;
  portEXIT_CRITICAL(&mux);
}

void needleHome() {
  portENTER_CRITICAL(&mux);
  qHead = qTail = 0;
  active = false;
  mood = NeedleMood::Still;
  pos = HOME_SWEEP_DEG;  // pretend we are beyond the far end, then drive through the stop
  plannedEnd = pos;
  const uint16_t ms = static_cast<uint16_t>(HOME_SWEEP_DEG / HOME_SPEED_DEG_S * 1000.0f);
  pushLocked({0.0f, ms, 150, Ease::Linear, -1});
  pushLocked({MOTOR_MIN_DEG, 150, 50, Ease::Linear, -1});
  portEXIT_CRITICAL(&mux);
}

void needleAwaken() {
  needleHome();
  enqueue(MOTOR_MIN_DEG + 360.0f / NEEDLE_GEAR_RATIO, 1600, Ease::InOut, 120);
  needleGoToSymbol(SYMBOL_HOURGLASS, Approach::Nearest, 1100);
}

void needleGoToSymbol(int symbol, Approach approach, uint16_t ms, int tag, uint16_t holdMs) {
  portENTER_CRITICAL(&mux);
  const float from = plannedEnd;
  portEXIT_CRITICAL(&mux);

  const float base = symbol * SYMBOL_STEP_DEG;
  float best = NAN, bestTravel = 1e9f, nearest = NAN, nearestTravel = 1e9f;
  for (int k = -4; k <= 4; k++) {
    const float m = motorForNeedle(base + 360.0f * k);
    if (m < MOTOR_MIN_DEG || m > MOTOR_MAX_DEG) continue;
    const float travel = fabsf(m - from) * NEEDLE_GEAR_RATIO;
    if (travel < nearestTravel) { nearest = m; nearestTravel = travel; }
    if (travel >= DRAMA_MIN_NEEDLE_DEG && travel < bestTravel) { best = m; bestTravel = travel; }
  }
  if (isnan(nearest)) return;  // unreachable only if the configured range is < 180 deg

  portENTER_CRITICAL(&mux);
  if (approach == Approach::Nearest || !isnan(best)) {
    const float target = approach == Approach::Nearest ? nearest : best;
    enqueueLocked(target, ms, Ease::OutCubic, holdMs, tag, true);
  } else {
    // No dramatic candidate: detour toward the far end of travel and come back.
    const float far = (nearest - MOTOR_MIN_DEG > MOTOR_MAX_DEG - nearest) ? MOTOR_MIN_DEG + 5 : MOTOR_MAX_DEG - 5;
    enqueueLocked(far, ms * 0.55f, Ease::InOut, 0, -1, false);
    enqueueLocked(nearest, ms * 0.65f, Ease::OutCubic, holdMs, tag, true);
  }
  portEXIT_CRITICAL(&mux);
}

void needlePlayReading(const Stop *stops, int count) {
  const float swingMotor = SWING_NEEDLE_DEG / NEEDLE_GEAR_RATIO;
  for (int s = 0; s < count; s++) {
    const int swings = constrain(stops[s].swings, 1, 4);
    needleGoToSymbol(stops[s].index, Approach::Dramatic, SWEEP_MS, s, swings > 1 ? 0 : STOP_PAUSE_MS);
    portENTER_CRITICAL(&mux);
    const float m = plannedEnd;
    for (int k = 1; k < swings; k++) {
      const bool last = k == swings - 1;
      // Swing out on the - side when possible so the return is already a + approach.
      const float out = (m - swingMotor >= MOTOR_MIN_DEG) ? m - swingMotor : m + swingMotor;
      enqueueLocked(out, SWING_OUT_MS, Ease::InOut, 0, -1, false);
      enqueueLocked(m, SWING_BACK_MS, Ease::OutCubic, last ? STOP_PAUSE_MS : 0, s, true);
    }
    portEXIT_CRITICAL(&mux);
  }
}

void needleFollowMotor(float motorDeg) {
  portENTER_CRITICAL(&mux);
  qHead = qTail = 0;
  active = false;
  plannedEnd = pos;
  const float target = constrain(motorDeg, MOTOR_MIN_DEG, MOTOR_MAX_DEG);
  const uint16_t ms = static_cast<uint16_t>(fmaxf(40.0f, fabsf(target - pos) / FOLLOW_SPEED_DEG_S * 1000.0f));
  enqueueLocked(target, ms, Ease::Linear, 0, -1, false);
  portEXIT_CRITICAL(&mux);
}

void needleTakeUpBacklash() {
  portENTER_CRITICAL(&mux);
  const float m = plannedEnd;
  enqueueLocked(fmaxf(m - BACKLASH_DEG, 0.0f), BACKLASH_TAKEUP_MS, Ease::Linear, 0, -1, false);
  enqueueLocked(m, BACKLASH_TAKEUP_MS, Ease::Linear, 50, -1, false);
  portEXIT_CRITICAL(&mux);
}

bool needleBusy() {
  portENTER_CRITICAL(&mux);
  const bool busy = active || qHead != qTail;
  portEXIT_CRITICAL(&mux);
  return busy;
}

bool needleWaitIdle(uint32_t timeoutMs) {
  const uint32_t start = millis();
  while (needleBusy()) {
    if (millis() - start > timeoutMs) return false;
    delay(10);
  }
  return true;
}

void needleSetMood(NeedleMood m) {
  portENTER_CRITICAL(&mux);
  mood = m;
  moodCenter = plannedEnd;
  nextTrembleUs = randRange(IDLE_TREMBLE_MIN_MS, IDLE_TREMBLE_MAX_MS) * 1000u;
  portEXIT_CRITICAL(&mux);
}

bool needleArrived(int &tag) {
  if (arrivalCount == seenArrivals) return false;
  seenArrivals = arrivalCount;
  tag = arrivalTag;
  return true;
}

float needleMotorDeg() { return pos; }

float needleAngleDeg() { return wrap360(needleForMotor(pos)); }
