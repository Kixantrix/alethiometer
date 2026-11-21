#include "audio.h"

#include <ESP_I2S.h>
#include <esp_heap_caps.h>
#include <freertos/stream_buffer.h>
#include <math.h>

#include "config.h"

namespace {

enum class Mode { Off, Tx, Rx };

I2SClass i2s;
Mode mode = Mode::Off;

constexpr size_t WAV_HEADER = 44;
constexpr size_t RECORD_MAX_SAMPLES = MIC_SAMPLE_RATE * RECORD_MAX_MS / 1000;
constexpr size_t MIC_CHUNK = 256;            // 32-bit samples per read (16 ms)
constexpr size_t TX_DRAIN_BYTES = 6 * 240 * 2;  // one full DMA ring of 16-bit mono frames

uint8_t *wav = nullptr;
size_t recSamples = 0;
float dcPrevIn = 0, dcPrevOut = 0;

void ensureMode(Mode want) {
  if (mode == want) return;
  if (mode != Mode::Off) i2s.end();
  digitalWrite(PIN_AMP_SD, LOW);
  mode = Mode::Off;
  if (want == Mode::Tx) {
    i2s.setPins(PIN_I2S_BCLK, PIN_I2S_WS, PIN_I2S_DOUT, -1);
    if (!i2s.begin(I2S_MODE_STD, SPEAK_SAMPLE_RATE, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO)) {
      Serial.println("[audio] I2S TX init failed");
      return;
    }
    digitalWrite(PIN_AMP_SD, HIGH);  // > 1.4 V on SD_MODE: on, left channel
    delay(2);
  } else if (want == Mode::Rx) {
    // 32-bit slots, stereo frame -> BCLK = 64 * fs as the INMP441 requires; L/R = GND -> left.
    i2s.setPins(PIN_I2S_BCLK, PIN_I2S_WS, -1, PIN_I2S_DIN);
    if (!i2s.begin(I2S_MODE_STD, MIC_SAMPLE_RATE, I2S_DATA_BIT_WIDTH_32BIT, I2S_SLOT_MODE_MONO,
                   I2S_STD_SLOT_LEFT)) {
      Serial.println("[audio] I2S RX init failed");
      return;
    }
  }
  if (want != Mode::Off) i2s.setTimeout(200);
  mode = want;
}

void writeSilence(size_t bytes) {
  static const uint8_t zeros[512] = {};
  while (bytes > 0) {
    const size_t n = bytes < sizeof zeros ? bytes : sizeof zeros;
    i2s.write(zeros, n);
    bytes -= n;
  }
}

void putLE16(uint8_t *p, uint16_t v) { p[0] = v; p[1] = v >> 8; }
void putLE32(uint8_t *p, uint32_t v) { for (int i = 0; i < 4; i++) p[i] = v >> (8 * i); }

void writeWavHeader(size_t dataBytes) {
  uint8_t *h = wav;
  memcpy(h, "RIFF", 4);
  putLE32(h + 4, 36 + dataBytes);
  memcpy(h + 8, "WAVEfmt ", 8);
  putLE32(h + 16, 16);
  putLE16(h + 20, 1);  // PCM
  putLE16(h + 22, 1);  // mono
  putLE32(h + 24, MIC_SAMPLE_RATE);
  putLE32(h + 28, MIC_SAMPLE_RATE * 2);
  putLE16(h + 32, 2);
  putLE16(h + 34, 16);
  memcpy(h + 36, "data", 4);
  putLE32(h + 40, dataBytes);
}

int16_t *recPcm() { return reinterpret_cast<int16_t *>(wav + WAV_HEADER); }

// Bell-like note: fundamental plus a faint inharmonic partial, fast attack, exponential decay.
void synthNote(float hz, uint32_t ms, float volume) {
  constexpr size_t CHUNK = 256;
  int16_t buf[CHUNK];
  const size_t total = SPEAK_SAMPLE_RATE * ms / 1000;
  const float attack = 0.006f * SPEAK_SAMPLE_RATE;
  const float tau = total / 4.0f;
  const float w1 = TWO_PI * hz / SPEAK_SAMPLE_RATE;
  const float w2 = TWO_PI * hz * 2.76f / SPEAK_SAMPLE_RATE;
  for (size_t i = 0; i < total;) {
    size_t n = 0;
    for (; n < CHUNK && i < total; n++, i++) {
      const float env = fminf(1.0f, i / attack) * expf(-static_cast<float>(i) / tau);
      const float s = 0.8f * sinf(w1 * i) + 0.2f * sinf(w2 * i);
      buf[n] = static_cast<int16_t>(s * env * volume * 32767.0f);
    }
    i2s.write(buf, n * sizeof(int16_t));
  }
}

struct Note { float hz; uint16_t ms; };

void playNotes(std::initializer_list<Note> notes, float volume) {
  ensureMode(Mode::Tx);
  if (mode != Mode::Tx) return;
  for (const Note &n : notes) {
    if (n.hz <= 0) writeSilence(SPEAK_SAMPLE_RATE * n.ms / 1000 * 2);
    else synthNote(n.hz, n.ms, volume);
  }
  writeSilence(TX_DRAIN_BYTES);
  ensureMode(Mode::Off);  // amplifier back into shutdown between sounds
}

// --- speech streaming ---
StreamBufferHandle_t speechBuf = nullptr;
StaticStreamBuffer_t speechBufStruct;
uint8_t *speechStorage = nullptr;
TaskHandle_t speechTask = nullptr;
volatile bool speechEof = false;
volatile bool speechAbort = false;
volatile bool speechDone = true;

void speechTaskFn(void *) {
  constexpr size_t PREBUFFER = SPEAK_SAMPLE_RATE * 2 * SPEAK_PREBUFFER_MS / 1000;
  while (!speechEof && !speechAbort && xStreamBufferBytesAvailable(speechBuf) < PREBUFFER) {
    vTaskDelay(pdMS_TO_TICKS(5));
  }
  alignas(4) uint8_t raw[1024 + 1];
  size_t carry = 0;  // odd byte left over from the previous receive
  while (!speechAbort) {
    const size_t got = xStreamBufferReceive(speechBuf, raw + carry, 1024, pdMS_TO_TICKS(20));
    if (got == 0) {
      if (speechEof && xStreamBufferIsEmpty(speechBuf)) break;
      continue;  // underrun: the DMA auto-clears to silence until data arrives
    }
    const size_t bytes = carry + got;
    const size_t even = bytes & ~static_cast<size_t>(1);
    int16_t *s = reinterpret_cast<int16_t *>(raw);
    for (size_t i = 0; i < even / 2; i++) s[i] = static_cast<int16_t>(s[i] * SPEECH_VOLUME);
    i2s.write(raw, even);
    carry = bytes - even;
    if (carry) raw[0] = raw[even];
  }
  if (!speechAbort) writeSilence(TX_DRAIN_BYTES);
  speechDone = true;
  vTaskDelete(nullptr);
}

}  // namespace

void audioBegin() {
  pinMode(PIN_AMP_SD, OUTPUT);
  digitalWrite(PIN_AMP_SD, LOW);
  if (!wav) wav = static_cast<uint8_t *>(heap_caps_malloc(WAV_HEADER + RECORD_MAX_SAMPLES * 2, MALLOC_CAP_SPIRAM));
  if (!speechStorage) {
    speechStorage = static_cast<uint8_t *>(heap_caps_malloc(SPEAK_RING_BYTES + 1, MALLOC_CAP_SPIRAM));
    speechBuf = xStreamBufferCreateStatic(SPEAK_RING_BYTES, 1, speechStorage, &speechBufStruct);
  }
  if (!wav || !speechBuf) Serial.println("[audio] PSRAM allocation failed");
}

void audioOff() { ensureMode(Mode::Off); }

void audioTone(float hz, uint32_t ms, float volume) { playNotes({{hz, static_cast<uint16_t>(ms)}}, volume); }

void audioChime(Chime chime) {
  const float v = CHIME_VOLUME;
  switch (chime) {
    case Chime::Wake: playNotes({{523, 220}, {659, 220}, {784, 420}}, v * 0.7f); break;
    case Chime::ListenStart: playNotes({{660, 110}, {880, 180}}, v); break;
    case Chime::ListenStop: playNotes({{880, 110}, {660, 180}}, v); break;
    case Chime::NoSpeech: playNotes({{440, 260}, {392, 420}}, v * 0.6f); break;
    case Chime::Error: playNotes({{233, 220}, {0, 60}, {220, 360}}, v); break;
    case Chime::Offline: playNotes({{392, 300}, {330, 300}, {262, 520}}, v * 0.8f); break;
    case Chime::CalStep: playNotes({{1047, 260}}, v); break;
    case Chime::CalDone: playNotes({{523, 160}, {659, 160}, {784, 160}, {1047, 480}}, v); break;
    case Chime::Portal: playNotes({{784, 160}, {988, 160}, {1175, 360}}, v); break;
    case Chime::LowBattery: playNotes({{330, 260}, {262, 420}}, v); break;
  }
}

bool audioRecordStart() {
  if (!wav) return false;
  ensureMode(Mode::Rx);
  if (mode != Mode::Rx) return false;
  recSamples = 0;
  dcPrevIn = dcPrevOut = 0;
  int32_t discard[MIC_CHUNK];
  for (size_t got = 0; got < MIC_SAMPLE_RATE * MIC_WARMUP_MS / 1000; got += MIC_CHUNK) {
    i2s.readBytes(reinterpret_cast<char *>(discard), sizeof discard);
  }
  return true;
}

bool audioRecordPoll() {
  if (mode != Mode::Rx || recSamples >= RECORD_MAX_SAMPLES) return false;
  int32_t raw[MIC_CHUNK];
  const size_t bytes = i2s.readBytes(reinterpret_cast<char *>(raw), sizeof raw);
  const size_t n = bytes / sizeof(int32_t);
  int16_t *out = recPcm();
  for (size_t i = 0; i < n && recSamples < RECORD_MAX_SAMPLES; i++) {
    const float x = static_cast<float>(raw[i] >> MIC_SHIFT);
    const float y = x - dcPrevIn + 0.995f * dcPrevOut;  // DC blocker
    dcPrevIn = x;
    dcPrevOut = y;
    out[recSamples++] = static_cast<int16_t>(constrain(y, -32768.0f, 32767.0f));
  }
  return recSamples < RECORD_MAX_SAMPLES;
}

void audioRecordStop() {
  if (wav) writeWavHeader(recSamples * 2);
  ensureMode(Mode::Off);
}

const uint8_t *audioWavData() { return wav; }
size_t audioWavSize() { return WAV_HEADER + recSamples * 2; }
uint32_t audioRecordedMs() { return recSamples * 1000 / MIC_SAMPLE_RATE; }

void audioRecordStats(int &peak, float &rms) {
  peak = 0;
  double sum = 0;
  const int16_t *pcm = recPcm();
  for (size_t i = 0; i < recSamples; i++) {
    const int v = abs(pcm[i]);
    if (v > peak) peak = v;
    sum += static_cast<double>(pcm[i]) * pcm[i];
  }
  rms = recSamples ? sqrt(sum / recSamples) : 0;
}

bool SpeechPlayer::begin(std::function<bool()> shouldCancel) {
  shouldCancel_ = std::move(shouldCancel);
  cancelled_ = false;
  received_ = 0;
  if (!speechBuf) return false;
  ensureMode(Mode::Tx);
  if (mode != Mode::Tx) return false;
  xStreamBufferReset(speechBuf);
  speechEof = false;
  speechAbort = false;
  speechDone = false;
  if (xTaskCreatePinnedToCore(speechTaskFn, "speech", 4096, nullptr, 5, &speechTask, 1) != pdPASS) {
    speechDone = true;
    return false;
  }
  return true;
}

size_t SpeechPlayer::write(const uint8_t *buffer, size_t size) {
  size_t sent = 0;
  while (sent < size) {
    if (shouldCancel_ && shouldCancel_()) {
      cancelled_ = true;
      speechAbort = true;
      return sent;
    }
    sent += xStreamBufferSend(speechBuf, buffer + sent, size - sent, pdMS_TO_TICKS(20));
  }
  received_ += sent;
  return sent;
}

void SpeechPlayer::finish() {
  speechEof = true;
  while (!speechDone) {
    if (!cancelled_ && shouldCancel_ && shouldCancel_()) {
      cancelled_ = true;
      speechAbort = true;
    }
    delay(10);
  }
  ensureMode(Mode::Off);
}
