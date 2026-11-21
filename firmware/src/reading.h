// A reading: the needle stops plus the interpretation that explains them.
#pragma once

#include <Arduino.h>

#include "config.h"

struct Stop {
  uint8_t index;   // symbol index 0..35
  uint8_t swings;  // 1..4
};

struct Reading {
  Stop stops[MAX_STOPS];
  int count = 0;
  String question;
  String interpretation;
  bool fromCloud = false;
};
