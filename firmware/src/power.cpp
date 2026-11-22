#include "power.h"

#include <driver/rtc_io.h>
#include <esp_idf_version.h>
#include <esp_sleep.h>

#include "config.h"

void powerBegin() {
  pinMode(PIN_LDO2, OUTPUT);
  digitalWrite(PIN_LDO2, HIGH);
  pinMode(PIN_CROWN, INPUT_PULLUP);
  pinMode(PIN_VBUS_SENSE, INPUT);
  analogSetPinAttenuation(PIN_VBAT_SENSE, ADC_2_5db);
  // Release any RTC pad config left over from deep sleep so the digital GPIOs work again.
  rtc_gpio_deinit(static_cast<gpio_num_t>(PIN_CROWN));
  rtc_gpio_hold_dis(static_cast<gpio_num_t>(PIN_AMP_SD));
  rtc_gpio_deinit(static_cast<gpio_num_t>(PIN_AMP_SD));
  pinMode(PIN_AMP_SD, OUTPUT);
  digitalWrite(PIN_AMP_SD, LOW);
  pinMode(PIN_CROWN, INPUT_PULLUP);
  delay(LDO2_SETTLE_MS);
}

WakeReason powerWakeReason() {
#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(6, 0, 0)
  const uint32_t causes = esp_sleep_get_wakeup_causes();
#else
  const uint32_t causes = 1u << esp_sleep_get_wakeup_cause();
#endif
  if (causes & (1u << ESP_SLEEP_WAKEUP_EXT1)) return WakeReason::Crown;
  if (causes == 0 || causes == (1u << ESP_SLEEP_WAKEUP_UNDEFINED)) return WakeReason::PowerOn;
  return WakeReason::Other;
}

float powerBatteryVolts() {
  uint32_t sum = 0;
  for (int i = 0; i < 8; i++) sum += analogReadMilliVolts(PIN_VBAT_SENSE);
  return sum / 8.0f / 1000.0f * VBAT_DIVIDER;
}

bool powerUsbPresent() { return digitalRead(PIN_VBUS_SENSE) == HIGH; }


bool powerBatteryLow() { return !powerUsbPresent() && powerBatteryVolts() < VBAT_WARN_V; }

bool powerWifiAllowed() { return powerUsbPresent() || powerBatteryVolts() >= VBAT_NO_WIFI_V; }

void powerLed(uint8_t r, uint8_t g, uint8_t b) {
  auto scale = [](uint8_t c) { return static_cast<uint8_t>(c * (LED_BRIGHTNESS + 1) >> 8); };
  rgbLedWrite(PIN_RGB_DATA, scale(r), scale(g), scale(b));
}

void powerDeepSleep() {
  powerLed(0, 0, 0);
  const uint32_t start = millis();
  while (digitalRead(PIN_CROWN) == LOW && millis() - start < 10000) delay(10);  // else ext1 wakes at once
  Serial.println("[power] deep sleep");
  Serial.flush();

  // Crown: any-low on IO9 with the RTC pull-up held through sleep.
  const auto crown = static_cast<gpio_num_t>(PIN_CROWN);
  rtc_gpio_init(crown);
  rtc_gpio_set_direction(crown, RTC_GPIO_MODE_INPUT_ONLY);
  rtc_gpio_pullup_en(crown);
  rtc_gpio_pulldown_dis(crown);
  esp_sleep_enable_ext1_wakeup_io(1ULL << PIN_CROWN, ESP_EXT1_WAKEUP_ANY_LOW);

  esp_sleep_pd_config(ESP_PD_DOMAIN_RTC_PERIPH, ESP_PD_OPTION_ON);

  // The amplifier runs from VBAT, so hold its SD_MODE low through sleep.
  const auto amp = static_cast<gpio_num_t>(PIN_AMP_SD);
  rtc_gpio_init(amp);
  rtc_gpio_set_direction(amp, RTC_GPIO_MODE_OUTPUT_ONLY);
  rtc_gpio_set_level(amp, 0);
  rtc_gpio_hold_en(amp);

  // LDO2 shuts off automatically in deep sleep; drive it low anyway.
  digitalWrite(PIN_LDO2, LOW);
  esp_deep_sleep_start();
}
