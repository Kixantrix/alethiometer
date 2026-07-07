# The Alethiometer

A working alethiometer — the symbolic truth-reading instrument from Philip Pullman's
*His Dark Materials* — as a website.

**Live site:** https://kixantrix.github.io/alethiometer/

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
| `aoai-alethiometer-kx` | Azure OpenAI, `gpt-5-mini` deployment |
| `func-alethiometer-kx` | Azure Function (Node 24, consumption) — the `ask` endpoint |
| `stalethiometerkx` | Storage for the Function App |

Deploy the API after changes:

```powershell
Compress-Archive -Path api\* -DestinationPath api.zip -Force
az functionapp deployment source config-zip --name func-alethiometer-kx `
  --resource-group rg-alethiometer --src api.zip --build-remote true
```

The function needs app settings `AOAI_ENDPOINT`, `AOAI_API_KEY`, `AOAI_DEPLOYMENT`
(set in Azure, never committed).

## Ideas for v2

- Ornate hand-drawn symbol artwork replacing the emoji glyphs
- Spoken readings (text-to-speech in an oracular voice)
- A "study mode" that teaches the symbol meanings
- The physical object — e-ink or servo dials driven by the same API
