#include "cloud.h"

#include <ArduinoJson.h>
#include <ArduinoOTA.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <WiFiManager.h>
#include <esp_wifi.h>

#include "audio.h"
#include "ca_roots.h"
#include "config.h"
#include "needle.h"
#include "settings.h"
#include "symbols.h"

namespace {

bool otaStarted = false;
volatile bool otaActive = false;

// ask-voice task state; the task owns `askResult`/`askError` until askStatus leaves Running.
volatile AskStatus askStatus = AskStatus::Idle;
const uint8_t *askWav = nullptr;
size_t askLen = 0;
int askHands[3];
Reading askResult;
String askError;

String urlEncode(const String &s) {
  static const char *hex = "0123456789ABCDEF";
  String out;
  out.reserve(s.length() * 3);
  for (size_t i = 0; i < s.length(); i++) {
    const uint8_t c = s[i];
    if (isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~') {
      out += static_cast<char>(c);
    } else {
      out += '%';
      out += hex[c >> 4];
      out += hex[c & 15];
    }
  }
  return out;
}

int symbolByName(const char *name) {
  if (!name) return -1;
  for (int i = 0; i < SYMBOL_COUNT; i++) {
    if (strcasecmp(SYMBOL_NAMES[i], name) == 0) return i;
  }
  return -1;
}

bool waitForWifi(uint32_t timeoutMs) {
  const uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    if (millis() - start > timeoutMs) return false;
    delay(50);
  }
  return true;
}

String apiUrl(const char *path) {
  String base = settings.apiBase;
  while (base.endsWith("/")) base.remove(base.length() - 1);
  return base + path;
}

String errorFromBody(int code, const String &body) {
  JsonDocument doc;
  if (deserializeJson(doc, body) == DeserializationError::Ok && doc["error"].is<const char *>()) {
    return String("HTTP ") + code + ": " + doc["error"].as<const char *>();
  }
  return code < 0 ? HTTPClient::errorToString(code) : String("HTTP ") + code;
}

bool parseReading(const String &body, Reading &out, String &error) {
  JsonDocument doc;
  const DeserializationError err = deserializeJson(doc, body);
  if (err) {
    error = String("bad JSON: ") + err.c_str();
    return false;
  }
  out.count = 0;
  for (JsonObjectConst stop : doc["reading"].as<JsonArrayConst>()) {
    const int index = symbolByName(stop["symbol"].as<const char *>());
    const int swings = stop["swings"] | 0;
    if (index < 0 || swings < 1 || swings > 4) continue;
    out.stops[out.count++] = {static_cast<uint8_t>(index), static_cast<uint8_t>(swings)};
    if (out.count == MAX_STOPS) break;
  }
  out.question = doc["question"] | "";
  out.interpretation = doc["interpretation"] | "";
  if (out.interpretation.length() > MAX_INTERPRETATION) out.interpretation.remove(MAX_INTERPRETATION);
  out.fromCloud = true;
  if (out.count < 1 || out.interpretation.length() < 10) {
    error = "malformed reading";
    return false;
  }
  for (JsonVariantConst src : doc["sources"].as<JsonArrayConst>()) {
    Serial.printf("[cloud] source: %s\n", src.as<const char *>());
  }
  return true;
}

void askTask(void *) {
  AskStatus result = AskStatus::Failed;
  askError = "";
  if (!waitForWifi(WIFI_CONNECT_TIMEOUT_MS)) {
    askError = "Wi-Fi not connected";
  } else {
    WiFi.setSleep(false);
    WiFiClientSecure client;
    client.setCACert(CA_ROOTS_PEM);
    HTTPClient http;
    const String symbols = String(SYMBOL_NAMES[askHands[0]]) + "|" + SYMBOL_NAMES[askHands[1]] + "|" +
                           SYMBOL_NAMES[askHands[2]];
    const String url = apiUrl("/ask-voice?symbols=") + urlEncode(symbols);
    http.setConnectTimeout(10000);
    http.setTimeout(ASK_TIMEOUT_MS);
    if (!http.begin(client, url)) {
      askError = "bad URL";
    } else {
      http.addHeader("x-device-key", settings.deviceKey);
      http.addHeader("Content-Type", "audio/wav");
      const int code = http.POST(const_cast<uint8_t *>(askWav), askLen);
      const String body = code > 0 ? http.getString() : String();
      if (code == 200) {
        if (parseReading(body, askResult, askError)) result = AskStatus::Ok;
      } else if (code == 422 && body.indexOf("no_speech") >= 0) {
        result = AskStatus::NoSpeech;
      } else {
        askError = errorFromBody(code, body);
      }
      http.end();
    }
    WiFi.setSleep(true);
  }
  askStatus = result;
  vTaskDelete(nullptr);
}

}  // namespace

bool cloudHasWifiCredentials() {
  WiFi.mode(WIFI_STA);
  wifi_config_t conf;
  return esp_wifi_get_config(WIFI_IF_STA, &conf) == ESP_OK && conf.sta.ssid[0] != 0;
}

void cloudConnect() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(OTA_HOSTNAME);
  WiFi.begin();
}

bool cloudConnected() { return WiFi.status() == WL_CONNECTED; }

void cloudLoop() {
  if (!cloudConnected()) return;
  // Never expose an unauthenticated OTA endpoint: wait until a device key is configured.
  if (!otaStarted && settings.deviceKey.length()) {
    ArduinoOTA.setHostname(OTA_HOSTNAME);
    ArduinoOTA.setPassword(settings.deviceKey.c_str());
    ArduinoOTA.onStart([] {
      otaActive = true;
      needleStop();
      audioOff();
      Serial.println("[ota] update started");
    });
    ArduinoOTA.onEnd([] { Serial.println("[ota] done, rebooting"); });
    ArduinoOTA.onError([](ota_error_t e) {
      otaActive = false;
      Serial.printf("[ota] error %u\n", e);
    });
    ArduinoOTA.begin();
    otaStarted = true;
    Serial.printf("[cloud] Wi-Fi %s, IP %s, OTA as %s.local\n", WiFi.SSID().c_str(),
                  WiFi.localIP().toString().c_str(), OTA_HOSTNAME);
  }
  if (otaStarted) ArduinoOTA.handle();
}

bool cloudOtaActive() { return otaActive; }

bool cloudRunPortal() {
  if (otaStarted) {
    ArduinoOTA.end();
    otaStarted = false;
  }
  WiFi.mode(WIFI_STA);
  WiFiManager wm;
  WiFiManagerParameter apiParam("api", "API base URL", settings.apiBase.c_str(), 160);
  // The key is never echoed back into the page; leave blank to keep the stored key.
  WiFiManagerParameter keyParam("key", "Device key (blank = keep current)", "", 128);
  wm.addParameter(&apiParam);
  wm.addParameter(&keyParam);
  wm.setTitle("The Alethiometer");
  wm.setConfigPortalTimeout(PORTAL_TIMEOUT_S);
  wm.setBreakAfterConfig(true);
  // WPA2-protected AP: WiFiManager's firmware-upload routes can't be disabled, so the
  // access point itself must not be open.
  Serial.printf("[cloud] setup portal: join Wi-Fi \"%s\" (password %s) and open http://192.168.4.1\n",
                PORTAL_AP_NAME, settings.portalPassword.c_str());
  const bool connected = wm.startConfigPortal(PORTAL_AP_NAME, settings.portalPassword.c_str());

  const String api = apiParam.getValue();
  const String key = keyParam.getValue();
  const bool apiChanged = api.length() && api != settings.apiBase;
  const bool keyChanged = key.length() && key != settings.deviceKey;
  if (apiChanged || keyChanged) {
    if (apiChanged) settings.apiBase = api;
    if (keyChanged) settings.deviceKey = key;
    settingsSaveCloud();
    Serial.println("[cloud] API settings saved");
  }
  return connected;
}

void cloudOff() {
  if (otaStarted) ArduinoOTA.end();
  otaStarted = false;
  WiFi.disconnect(false, false);
  WiFi.mode(WIFI_OFF);
}

bool cloudAskStart(const uint8_t *wav, size_t len, const int hands[3]) {
  if (askStatus == AskStatus::Running) return false;
  askWav = wav;
  askLen = len;
  for (int i = 0; i < 3; i++) askHands[i] = hands[i];
  askStatus = AskStatus::Running;
  if (xTaskCreatePinnedToCore(askTask, "ask", 16384, nullptr, 3, nullptr, 0) != pdPASS) {
    askError = "no memory for task";
    askStatus = AskStatus::Failed;
  }
  return true;
}

AskStatus cloudAskPoll(Reading &out, String &error) {
  const AskStatus s = askStatus;
  if (s == AskStatus::Running || s == AskStatus::Idle) return s;
  if (s == AskStatus::Ok) out = askResult;
  error = askError;
  askStatus = AskStatus::Idle;
  return s;
}

bool cloudSpeak(const String &text, std::function<bool()> shouldCancel, String &error) {
  if (!waitForWifi(WIFI_CONNECT_TIMEOUT_MS)) {
    error = "Wi-Fi not connected";
    return false;
  }
  WiFi.setSleep(false);
  WiFiClientSecure client;
  client.setCACert(CA_ROOTS_PEM);
  HTTPClient http;
  http.setConnectTimeout(10000);
  http.setTimeout(SPEAK_TIMEOUT_MS);
  bool ok = false;
  if (!http.begin(client, apiUrl("/speak"))) {
    error = "bad URL";
  } else {
    http.addHeader("x-device-key", settings.deviceKey);
    http.addHeader("Content-Type", "application/json");
    JsonDocument doc;
    doc["text"] = text;
    String body;
    serializeJson(doc, body);
    const int code = http.POST(body);
    if (code == 200) {
      SpeechPlayer player;
      if (player.begin(shouldCancel)) {
        const int written = http.writeToStream(&player);
        player.finish();
        ok = written > 0 || player.cancelled();
        if (!ok) error = String("stream: ") + HTTPClient::errorToString(written);
        Serial.printf("[cloud] speech %u bytes%s\n", player.bytesReceived(), player.cancelled() ? " (cancelled)" : "");
      } else {
        error = "audio init failed";
      }
    } else {
      error = errorFromBody(code, code > 0 ? http.getString() : String());
    }
    http.end();
  }
  WiFi.setSleep(true);
  return ok;
}
