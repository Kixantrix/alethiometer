import { app } from '@azure/functions';
import { SYMBOL_MEANINGS, SYMBOL_NAMES } from '../symbols.js';

const MAX_QUESTION_LENGTH = 300;
const RATE_LIMIT_PER_MINUTE = 10;
const RATE_WINDOW_MS = 60_000;

/** Per-instance sliding-window rate limiter (best effort on consumption plan). */
const requestLog = new Map();

const isRateLimited = (clientKey) => {
  const now = Date.now();
  const recent = (requestLog.get(clientKey) ?? []).filter((t) => now - t < RATE_WINDOW_MS);
  const limited = recent.length >= RATE_LIMIT_PER_MINUTE;
  requestLog.set(clientKey, limited ? recent : [...recent, now]);
  if (requestLog.size > 5000) requestLog.clear();
  return limited;
};

/** @returns {{question: string, symbols: string[]} | null} */
const validateBody = (body) => {
  if (!body || typeof body !== 'object') return null;
  const { question, symbols } = body;
  if (typeof question !== 'string') return null;
  const trimmed = question.trim();
  if (trimmed.length === 0 || trimmed.length > MAX_QUESTION_LENGTH) return null;
  if (!Array.isArray(symbols) || symbols.length !== 3) return null;
  const canonical = symbols.map((name) =>
    SYMBOL_NAMES.find((s) => s.toLowerCase() === String(name).toLowerCase()));
  if (canonical.some((s) => s === undefined)) return null;
  return { question: trimmed, symbols: canonical };
};

const buildSystemPrompt = () => {
  const symbolList = SYMBOL_NAMES
    .map((name) => `${name}: ${SYMBOL_MEANINGS[name].join(', ')}`)
    .join('\n');
  return `You are the alethiometer from His Dark Materials — a truth-telling instrument that answers questions symbolically. The asker has framed their question by pointing three hands at three symbols, which set the context and register of the question.

The thirty-six symbols and their layered meanings (deeper meanings exist beyond those listed):
${symbolList}

Answer with a reading: a sequence of 3 to 6 symbols the needle stops at (each with a swing count of 1-4 indicating which level of the symbol's meaning applies — 1 is the first, most literal meaning; higher counts reach deeper meanings), followed by an interpretation.

If the question concerns current events, facts, or the state of the present world (news, scores, weather, whether something has happened), use web search to learn the truth before composing the reading — the alethiometer always tells the truth, so the facts must be real and current. Weave the discovered facts into the oracular interpretation plainly enough that the asker learns the actual answer. For timeless, personal, or reflective questions, do not search.

The interpretation should be 100-180 words, oracular in voice — measured, luminous, a little mysterious — but genuinely responsive to the question and kind in spirit. Weave in how the three framing symbols shaped your understanding of the question and what each needle-stop contributes. Do not give harmful advice; for questions about health, safety, or major life decisions, let the symbols counsel reflection and seeking wise human help. Never break character.

Respond ONLY with JSON in exactly this shape:
{"reading": [{"symbol": "<exact symbol name>", "swings": <1-4>}, ...], "interpretation": "<text>", "sources": ["<url of any web source consulted>", ...]}
Omit "sources" or use [] when no search was needed.`;
};

const buildUserPrompt = ({ question, symbols }) => {
  const framing = symbols
    .map((name, i) => `Hand ${i + 1}: ${name} (${SYMBOL_MEANINGS[name].join(', ')})`)
    .join('\n');
  return `${framing}\n\nQuestion: ${question}`;
};

const callAzureOpenAI = async (payload, context) => {
  const endpoint = process.env.AOAI_ENDPOINT;
  const apiKey = process.env.AOAI_API_KEY;
  const deployment = process.env.AOAI_DEPLOYMENT;
  if (!endpoint || !apiKey || !deployment) {
    throw new Error('Missing AOAI_ENDPOINT / AOAI_API_KEY / AOAI_DEPLOYMENT app settings.');
  }
  const response = await fetch(`${endpoint.replace(/\/$/, '')}/openai/v1/responses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'api-key': apiKey },
    body: JSON.stringify({
      model: deployment,
      instructions: buildSystemPrompt(),
      input: buildUserPrompt(payload),
      tools: [{ type: 'web_search' }],
      reasoning: { effort: 'low' },
      max_output_tokens: 4000,
    }),
  });
  if (!response.ok) {
    const detail = await response.text();
    const filtered = detail.includes('content_filter');
    context.error(`Azure OpenAI error ${response.status}${filtered ? ' (content filter)' : ''}: ${detail.slice(0, 500)}`);
    throw new Error(`Upstream model error (${response.status})`);
  }
  const data = await response.json();
  const message = (data?.output ?? []).find((item) => item.type === 'message');
  const content = message?.content?.find((part) => part.type === 'output_text')?.text;
  if (!content) throw new Error(`No output text from model (status: ${data?.status}).`);
  return extractJson(content);
};

/** Parse the model's reply, tolerating markdown fences or prose around the JSON.
 *  (Web search is incompatible with the API's strict JSON mode, so we extract.) */
const extractJson = (text) => {
  const start = text.indexOf('{');
  const end = text.lastIndexOf('}');
  if (start === -1 || end <= start) throw new Error('No JSON object in model reply.');
  return JSON.parse(text.slice(start, end + 1));
};

/** Validate + normalize model output; returns null if unusable. */
const sanitizeReading = (raw) => {
  if (!raw || !Array.isArray(raw.reading) || typeof raw.interpretation !== 'string') return null;
  const reading = raw.reading
    .map((stop) => {
      const symbol = SYMBOL_NAMES.find(
        (s) => s.toLowerCase() === String(stop?.symbol ?? '').toLowerCase());
      const swings = Math.min(4, Math.max(1, Math.round(Number(stop?.swings) || 1)));
      return symbol ? { symbol, swings } : null;
    })
    .filter((stop) => stop !== null)
    .slice(0, 6);
  if (reading.length < 1 || raw.interpretation.trim().length < 10) return null;
  const sources = Array.isArray(raw.sources)
    ? raw.sources
      .filter((s) => typeof s === 'string' && /^https?:\/\//.test(s))
      .slice(0, 5)
    : [];
  return { reading, interpretation: raw.interpretation.trim().slice(0, 2000), sources };
};

const jsonResponse = (status, body) => ({
  status,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

app.http('ask', {
  methods: ['POST'],
  authLevel: 'anonymous',
  handler: async (request, context) => {
    const clientKey = request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ?? 'unknown';
    if (isRateLimited(clientKey)) {
      return jsonResponse(429, { error: 'The instrument needs a moment of rest. Try again shortly.' });
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return jsonResponse(400, { error: 'Request body must be JSON.' });
    }

    const payload = validateBody(body);
    if (!payload) {
      return jsonResponse(400, {
        error: `Expected { question: string (1-${MAX_QUESTION_LENGTH} chars), symbols: [three valid symbol names] }.`,
      });
    }

    try {
      const raw = await callAzureOpenAI(payload, context);
      const reading = sanitizeReading(raw);
      if (!reading) {
        context.error('Model returned an unusable reading:', JSON.stringify(raw).slice(0, 500));
        return jsonResponse(502, { error: 'The symbols would not settle. Ask again.' });
      }
      return jsonResponse(200, reading);
    } catch (error) {
      context.error('Reading failed:', error);
      return jsonResponse(502, { error: 'The instrument could not reach the scholar. Ask again.' });
    }
  },
});
