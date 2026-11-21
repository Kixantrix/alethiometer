// Power rails, battery, status LED, lid switch and deep sleep.
#pragma once

#include <Arduino.h>

enum class WakeReason { PowerOn, Crown, Lid, Other };

void powerBegin();               // enable LDO2 and wait for it to settle
WakeReason powerWakeReason();
float powerBatteryVolts();
bool powerUsbPresent();
bool powerLidClosed();
bool powerBatteryLow();          // below VBAT_WARN_V and not on USB
bool powerWifiAllowed();         // above VBAT_NO_WIFI_V or on USB
void powerLed(uint8_t r, uint8_t g, uint8_t b);
[[noreturn]] void powerDeepSleep();
