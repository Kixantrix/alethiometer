// Crown pushbutton: debouncing and gesture recognition (hold = push-to-talk, n clicks).
#pragma once

#include <Arduino.h>

enum class CrownEvent { None, HoldStart, HoldEnd, Clicks };

struct CrownSignal {
  CrownEvent event = CrownEvent::None;
  int clicks = 0;        // for Clicks
  uint32_t heldMs = 0;   // for HoldEnd
};

void crownBegin();             // a press already in progress (the wake press) is ignored
CrownSignal crownUpdate();     // call often; returns at most one event
bool crownPressed();           // debounced level
