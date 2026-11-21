// Offline oracle: a port of localReading() in js/oracle.js (FNV-1a based, deterministic).
#pragma once

#include <Arduino.h>

#include "reading.h"

uint32_t oracleHash(const char *text);  // FNV-1a, identical to hashText() in js/oracle.js

// Same algorithm as the website: seed = hash(`${question}|${i0},${i1},${i2}`).
void oracleLocalReading(const String &question, const int hands[3], Reading &out);

// Device fallback: no transcript offline, so seed with the hand names plus esp_random().
void oracleOfflineReading(const int hands[3], Reading &out);
