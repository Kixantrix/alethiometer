// I2S audio: push-to-talk recording (INMP441), speech streaming and chimes (MAX98357A).
// The bus is shared, so the peripheral is re-initialised for each direction.
#pragma once

#include <Arduino.h>

#include <functional>

enum class Chime { Wake, ListenStart, ListenStop, NoSpeech, Error, Offline, CalStep, CalDone, Portal, LowBattery };

void audioBegin();
void audioOff();                       // stop I2S, amplifier into shutdown
void audioChime(Chime chime);
void audioTone(float hz, uint32_t ms, float volume);

bool audioRecordStart();
bool audioRecordPoll();                // false once the buffer is full
void audioRecordStop();                // finalises the WAV header
const uint8_t *audioWavData();
size_t audioWavSize();
uint32_t audioRecordedMs();
void audioRecordStats(int &peak, float &rms);

// Stream sink for raw s16le mono 24 kHz PCM: buffers SPEAK_PREBUFFER_MS, then plays from a
// background task while the caller keeps writing network data. Returning short from write()
// (on cancel) aborts HTTPClient::writeToStream.
class SpeechPlayer : public Stream {
 public:
  bool begin(std::function<bool()> shouldCancel);
  void finish();                       // drain (or abort if cancelled) and release I2S
  bool cancelled() const { return cancelled_; }
  size_t bytesReceived() const { return received_; }

  size_t write(const uint8_t *buffer, size_t size) override;
  size_t write(uint8_t b) override { return write(&b, 1); }
  int available() override { return 0; }
  int read() override { return -1; }
  int peek() override { return -1; }
  void flush() override {}

 private:
  std::function<bool()> shouldCancel_;
  bool cancelled_ = false;
  size_t received_ = 0;
};
