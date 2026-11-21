import { createHash, timingSafeEqual } from 'node:crypto';
import { app } from '@azure/functions';
import {
  MAX_QUESTION_LENGTH,
  aoaiEndpoint,
  canonicalizeSymbols,
  clientIp,
  composeReading,
  isRateLimited,
  jsonResponse,
} from '../reading.js';

/* Endpoints for the physical (ESP32) instrument: spoken questions in, spoken readings out.
 * HTTP streaming lets /api/speak relay audio as it is synthesized. app.setup applies to the
 * whole app (every function file loads into one worker process) and only changes how
 * requests/responses are transported, so /api/ask behaves exactly as before. */
app.setup({ enableHttpStream: true });

const MAX_AUDIO_BYTES = 1_000_000;
const MAX_SPEECH_TEXT_LENGTH = 2000;
const MIN_TRANSCRIPT_LENGTH = 2;

const TRANSCRIBE_PROMPT = 'A question asked of an alethiometer.';
const VOICE_INSTRUCTIONS = 'Speak as an ancient, calm truth-telling instrument: measured, warm, '
  + 'a little mysterious, unhurried, with gentle pauses between symbols.';

/** Format of the raw PCM returned by Azure OpenAI text-to-speech. */
const PCM_FORMAT = 'pcm_s16le;rate=24000;channels=1';

const sha256 = (value) => createHash('sha256').update(String(value)).digest();

/** Constant-time key check; hashing both sides gives timingSafeEqual equal-length buffers. */
const isKnownDevice = (provided, expected) =>
  Boolean(provided) && timingSafeEqual(sha256(provided), sha256(expected));

/**
 * Shared gate for device routes: configuration, rate limit (per route + IP, so key
 * guessing is throttled too), then the x-device-key header.
 * @returns {object | null} an error response, or null when the instrument is admitted.
 */
const admitDevice = (route, request) => {
  const expected = process.env.DEVICE_KEY;
  if (!expected) return jsonResponse(503, { error: 'Device access is not configured.' });
  if (isRateLimited(`${route}:${clientIp(request)}`)) {
    return jsonResponse(429, { error: 'The instrument needs a moment of rest. Try again shortly.' });
  }
  if (!isKnownDevice(request.headers.get('x-device-key'), expected)) {
    return jsonResponse(401, { error: 'Unknown instrument.' });
  }
  return null;
};

/** Parse `Hourglass|Sun|Moon` (already URL-decoded) into canonical symbol names. */
const parseSymbolsParam = (value) =>
  (typeof value === 'string' ? canonicalizeSymbols(value.split('|').map((s) => s.trim())) : null);

/**
 * Read the request body into a Buffer, giving up once it exceeds maxBytes.
 * @returns {Promise<Buffer | null>} null when the body is too large.
 */
const readBodyLimited = async (request, maxBytes) => {
  if (!request.body) return Buffer.alloc(0);
  const chunks = [];
  let total = 0;
  for await (const chunk of request.body) {
    total += chunk.byteLength;
    if (total > maxBytes) return null;
    chunks.push(Buffer.from(chunk));
  }
  return Buffer.concat(chunks, total);
};

const isWav = (audio) => audio.length > 44
  && audio.toString('ascii', 0, 4) === 'RIFF'
  && audio.toString('ascii', 8, 12) === 'WAVE';

/** Speech-to-text via Azure OpenAI; returns the raw transcript text. */
const transcribe = async (audio, context) => {
  const endpoint = aoaiEndpoint();
  const apiKey = process.env.AOAI_API_KEY;
  if (!endpoint || !apiKey) throw new Error('Missing AOAI_ENDPOINT / AOAI_API_KEY app settings.');
  const form = new FormData();
  form.append('file', new Blob([audio], { type: 'audio/wav' }), 'question.wav');
  form.append('model', process.env.AOAI_TRANSCRIBE_DEPLOYMENT || 'gpt-4o-mini-transcribe');
  form.append('response_format', 'json');
  form.append('prompt', TRANSCRIBE_PROMPT);
  const response = await fetch(`${endpoint}/openai/v1/audio/transcriptions`, {
    method: 'POST',
    headers: { 'api-key': apiKey },
    body: form,
  });
  if (!response.ok) {
    const detail = await response.text();
    context.error(`Azure OpenAI transcription error ${response.status}: ${detail.slice(0, 500)}`);
    throw new Error(`Upstream transcription error (${response.status})`);
  }
  const data = await response.json();
  return typeof data?.text === 'string' ? data.text : '';
};

app.http('ask-voice', {
  route: 'ask-voice',
  methods: ['POST'],
  authLevel: 'anonymous',
  handler: async (request, context) => {
    const denied = admitDevice('ask-voice', request);
    if (denied) return denied;

    const symbols = parseSymbolsParam(request.query.get('symbols'));
    if (!symbols) {
      return jsonResponse(400, { error: 'Expected query ?symbols=A|B|C naming three valid symbols.' });
    }

    if (Number(request.headers.get('content-length')) > MAX_AUDIO_BYTES) {
      return jsonResponse(413, { error: 'The question is too long for the instrument to hear.' });
    }
    const audio = await readBodyLimited(request, MAX_AUDIO_BYTES);
    if (!audio) {
      return jsonResponse(413, { error: 'The question is too long for the instrument to hear.' });
    }
    if (!isWav(audio)) {
      return jsonResponse(400, { error: 'Request body must be WAV audio (16 kHz mono 16-bit PCM).' });
    }

    let transcript;
    try {
      transcript = (await transcribe(audio, context)).trim();
    } catch (error) {
      context.error('Transcription failed:', error);
      return jsonResponse(502, { error: 'The instrument could not make out the question. Ask again.' });
    }
    if (transcript.length < MIN_TRANSCRIPT_LENGTH) {
      return jsonResponse(422, { error: 'The instrument heard no question.', code: 'no_speech' });
    }

    const question = transcript.slice(0, MAX_QUESTION_LENGTH);
    const { reading, error } = await composeReading({ question, symbols }, context);
    return error ?? jsonResponse(200, { question, ...reading });
  },
});

app.http('speak', {
  route: 'speak',
  methods: ['POST'],
  authLevel: 'anonymous',
  handler: async (request, context) => {
    const denied = admitDevice('speak', request);
    if (denied) return denied;

    let body;
    try {
      body = await request.json();
    } catch {
      return jsonResponse(400, { error: 'Request body must be JSON.' });
    }
    const text = typeof body?.text === 'string' ? body.text.trim() : '';
    if (text.length === 0 || text.length > MAX_SPEECH_TEXT_LENGTH) {
      return jsonResponse(400, { error: `Expected { text: string (1-${MAX_SPEECH_TEXT_LENGTH} chars) }.` });
    }

    const endpoint = aoaiEndpoint();
    const apiKey = process.env.AOAI_API_KEY;
    if (!endpoint || !apiKey) {
      context.error('Speech failed: missing AOAI_ENDPOINT / AOAI_API_KEY app settings.');
      return jsonResponse(502, { error: 'The instrument has lost its voice. Ask again.' });
    }

    let response;
    try {
      response = await fetch(`${endpoint}/openai/v1/audio/speech`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'api-key': apiKey },
        body: JSON.stringify({
          model: process.env.AOAI_TTS_DEPLOYMENT || 'gpt-4o-mini-tts',
          input: text,
          voice: process.env.AOAI_TTS_VOICE || 'sage',
          response_format: 'pcm',
          instructions: VOICE_INSTRUCTIONS,
        }),
      });
    } catch (error) {
      context.error('Speech failed:', error);
      return jsonResponse(502, { error: 'The instrument has lost its voice. Ask again.' });
    }
    if (!response.ok || !response.body) {
      const detail = await response.text();
      context.error(`Azure OpenAI speech error ${response.status}: ${detail.slice(0, 500)}`);
      return jsonResponse(502, { error: 'The instrument has lost its voice. Ask again.' });
    }

    return {
      status: 200,
      headers: { 'Content-Type': 'audio/pcm', 'x-audio-format': PCM_FORMAT },
      body: response.body,
    };
  },
});
