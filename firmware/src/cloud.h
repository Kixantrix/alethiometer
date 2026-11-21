// Wi-Fi, setup portal, OTA and the Alethiometer cloud API (ask-voice + speak).
#pragma once

#include <Arduino.h>

#include <functional>

#include "reading.h"

enum class AskStatus { Idle, Running, Ok, NoSpeech, Failed };

bool cloudHasWifiCredentials();
void cloudConnect();                   // non-blocking connect with stored credentials
bool cloudConnected();
void cloudLoop();                      // OTA service; call from loop()
bool cloudOtaActive();
bool cloudRunPortal();                 // blocking WiFiManager portal; true if Wi-Fi saved
void cloudOff();

// ask-voice runs in a background task so the needle and UI stay responsive.
bool cloudAskStart(const uint8_t *wav, size_t len, const int hands[3]);
AskStatus cloudAskPoll(Reading &out, String &error);

// Streams /speak PCM to the speaker; blocks until done or shouldCancel() returns true.
bool cloudSpeak(const String &text, std::function<bool()> shouldCancel, String &error);
