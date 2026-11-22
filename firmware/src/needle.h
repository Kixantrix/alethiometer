// The answer needle: X27.168 stepper -> 34T:17T gears -> needle.
// Motion runs in a 2 kHz esp_timer callback; callers only queue segments.
#pragma once

#include <Arduino.h>

#include "reading.h"

enum class Approach { Dramatic, Nearest };
enum class NeedleMood { Still, Idle, Thinking };

void needleBegin();
void needleHome();                     // drive into the hard stop, define motor 0 there
void needleAwaken();                   // home, sweep once around, settle on the Hourglass
void needleGoToSymbol(int symbol, Approach approach, uint16_t ms, int tag = -1, uint16_t holdMs = 0);
void needlePlayReading(const Stop *stops, int count);
void needleFollowMotor(float motorDeg);   // immediate, speed-limited (calibration jog)
void needleTakeUpBacklash();
void needleStop();                     // drop queued motion; stays where it is
bool needleBusy();
bool needleWaitIdle(uint32_t timeoutMs);
void needleSetMood(NeedleMood mood);
bool needleArrived(int &tag);          // true once per arrival event (stop index in tag)

float needleMotorDeg();                // current motor angle (0 = hard stop)
float needleAngleDeg();                // current needle angle 0..360
float needleForMotor(float motorDeg);  // unwrapped needle angle for a motor angle
float motorForNeedle(float needleDeg);
