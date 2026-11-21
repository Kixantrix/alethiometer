#include "oracle.h"

#include <esp_random.h>

#include "symbols.h"

uint32_t oracleHash(const char *text) {
  uint32_t h = 2166136261u;
  for (const unsigned char *p = reinterpret_cast<const unsigned char *>(text); *p; ++p) {
    h ^= *p;
    h *= 16777619u;
  }
  return h;
}

void oracleLocalReading(const String &question, const int hands[3], Reading &out) {
  char buf[400];
  snprintf(buf, sizeof buf, "%s|%d,%d,%d", question.c_str(), hands[0], hands[1], hands[2]);
  const uint32_t seed = oracleHash(buf);
  out.count = 3 + seed % 3;
  for (int k = 0; k < out.count; k++) {
    snprintf(buf, sizeof buf, "%lu:%d", static_cast<unsigned long>(seed), k);
    const uint32_t mix = oracleHash(buf);
    out.stops[k].index = mix % SYMBOL_COUNT;
    out.stops[k].swings = 1 + (mix >> 8) % 3;
  }
  out.question = question;
  out.interpretation = "";
  out.fromCloud = false;
}

void oracleOfflineReading(const int hands[3], Reading &out) {
  char seed[160];
  snprintf(seed, sizeof seed, "%s|%s|%s|%lu", SYMBOL_NAMES[hands[0]], SYMBOL_NAMES[hands[1]],
           SYMBOL_NAMES[hands[2]], static_cast<unsigned long>(esp_random()));
  oracleLocalReading(seed, hands, out);
  out.question = "";
}
