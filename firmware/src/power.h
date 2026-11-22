// Power rails, battery, status LED and deep sleep.
#pragma once

#include <Arduino.h>

enum class WakeReason { PowerOn, Crown, Other };

void powerBegin();               // enable LDO2 and wait for it to settle
WakeReason powerWakeReason();
float powerBatteryVolts();
bool powerUsbPresent();
bool powerBatteryLow();          // below VBAT_WARN_V and not on USB
bool powerWifiAllowed();         // above VBAT_NO_WIFI_V or on USB
void powerLed(uint8_t r, uint8_t g, uint8_t b);
[[noreturn]] void powerDeepSleep();
