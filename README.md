# The Alethiometer

A working alethiometer — the symbolic truth-reading instrument from Philip Pullman's
*His Dark Materials* — as a website.

**Live site:** https://kixantrix.github.io/alethiometer/

**The physical instrument:** a hand-held brass alethiometer with three thumbwheel-set hands,
a motor-driven needle and a hidden speaker and microphone. It's built from laser-cut brass
(SendCutSend) and an ESP32-S3, and uses the same oracle as the site.
See [`hardware/`](hardware/README.md) for the design, the parts to order and assembly, and
[`firmware/`](firmware/README.md) for the code.

## How to use it

1. **Ask a question** — type it, or tap the microphone and speak it (Chrome/Edge).
2. **Frame it with three hands** — click a hand chip (I, II, III) to select it, then click a
   symbol on the dial. The three symbols you choose set the context and register of your
   question, just as in the books. Hover any symbol to see its layered meanings.
3. **Press Ask** — the blue needle sweeps the dial, stopping at a sequence of symbols.
   The number of swings at each stop tells you which level of that symbol's meaning applies.
   The interpretation appears below the device.

## How it works

- **Frontend** — vanilla HTML/CSS/JS, no build step, hosted on GitHub Pages. The dial is an
  SVG with the 36 classic symbols; needle animation is requestAnimationFrame with easing.
- **The scholar** — readings are composed by `gpt-5-mini` on Azure OpenAI (Responses API),
  reached through a small Azure Function (`api/`) so the API key never leaves the server.
  For questions about current events ("is the USA still in the World Cup?"), the model uses
  its built-in `web_search` tool to learn the truth before composing the reading, and the
  consulted sources appear beneath the interpretation. The function validates input,
  rate-limits, and returns strict JSON:
  `{"reading": [{"symbol", "swings"}...], "interpretation", "sources"}`.
- **Fallback oracle** — if the API can't be reached, the device composes a deterministic
  local reading from your question and chosen symbols, so it always answers.
- **Speech** — browser Web Speech API; no audio ever leaves your machine except to your
  browser's own speech service.

## Symbol meanings

The 36 symbols follow book canon and the reading tradition of alethiometrist fan
scholarship (each symbol carries an infinite descent of meanings; three are listed per
symbol in `js/symbols.js`).

## Development

Serve locally (the API allows `http://localhost:8000` via CORS):

```sh
python -m http.server 8000
```

### Azure resources (resource group `rg-alethiometer`, eastus2)

| Resource | Purpose |
|---|---|
| `aoai-alethiometer-kx` | Azure OpenAI, `gpt-5-mini` (+ speech model) deployments |
| `func-alethiometer-kx` | Azure Function (Node 24, consumption) — `ask`, `ask-voice`, `speak` endpoints |
| `stalethiometerkx` | Storage for the Function App |

Deploy the API after changes:

```powershell
Compress-Archive -Path api\* -DestinationPath api.zip -Force
az functionapp deployment source config-zip --name func-alethiometer-kx `
  --resource-group rg-alethiometer --src api.zip --build-remote true
```

The function needs app settings `AOAI_ENDPOINT`, `AOAI_API_KEY`, `AOAI_DEPLOYMENT`
(set in Azure, never committed).

### Physical instrument API

The brass alethiometer (ESP32-S3 with mic + speaker) uses two extra endpoints in
`api/src/functions/voice.js`. Both require header `x-device-key` matching app setting
`DEVICE_KEY` (503 if unset, 401 if wrong) and are rate-limited to 10 requests/minute.

- **`POST /api/ask-voice?symbols=Hourglass%7CSun%7CMoon`** — body is raw WAV
  (`Content-Type: audio/wav`, 16 kHz mono 16-bit PCM, ≤ 15 s / 1,000,000 bytes, else 413).
  The question is transcribed, then read exactly like `/api/ask`. Returns
  `{"question", "reading": [{"symbol", "swings"}...], "interpretation", "sources"}`;
  422 `{"error", "code": "no_speech"}` if nothing intelligible was heard.
- **`POST /api/speak`** — JSON `{"text": "..."}` (1-2000 chars). Streams back raw PCM
  speech in an oracular voice: `Content-Type: audio/pcm`,
  `x-audio-format: pcm_s16le;rate=24000;channels=1`.

Extra app settings: `DEVICE_KEY` (required), `AOAI_TRANSCRIBE_DEPLOYMENT`
(default `gpt-4o-mini-transcribe`), `AOAI_TTS_DEPLOYMENT` (default `gpt-4o-mini-tts`),
`AOAI_TTS_VOICE` (default `sage`). Streaming responses need `@azure/functions` ≥ 4.3 and
Functions host ≥ 4.28 (enabled via `app.setup({ enableHttpStream: true })`).

Create the speech model deployments in the existing Azure OpenAI resource (check available
versions first; `2025-12-15` was current at time of writing, `2025-03-20` is the original):

```powershell
az cognitiveservices account list-models --name aoai-alethiometer-kx `
  --resource-group rg-alethiometer `
  --query "[?contains(name, 'mini-transcribe') || contains(name, 'mini-tts')].{name:name, version:version}" -o table

az cognitiveservices account deployment create --name aoai-alethiometer-kx `
  --resource-group rg-alethiometer --deployment-name gpt-4o-mini-transcribe `
  --model-name gpt-4o-mini-transcribe --model-version <version> --model-format OpenAI `
  --sku-name GlobalStandard --sku-capacity 1

az cognitiveservices account deployment create --name aoai-alethiometer-kx `
  --resource-group rg-alethiometer --deployment-name gpt-4o-mini-tts `
  --model-name gpt-4o-mini-tts --model-version <version> --model-format OpenAI `
  --sku-name GlobalStandard --sku-capacity 1

az functionapp config appsettings set --name func-alethiometer-kx `
  --resource-group rg-alethiometer --settings `
  DEVICE_KEY=<long-random-secret> `
  AOAI_TRANSCRIBE_DEPLOYMENT=gpt-4o-mini-transcribe `
  AOAI_TTS_DEPLOYMENT=gpt-4o-mini-tts `
  AOAI_TTS_VOICE=sage
```

## Ideas for v2

- Ornate hand-drawn symbol artwork replacing the emoji glyphs
- Spoken readings (text-to-speech in an oracular voice)
- A "study mode" that teaches the symbol meanings
