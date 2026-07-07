/**
 * The oracle: asks the Azure Function for a symbolic reading, and falls back
 * to a deterministic local reading when the API is unreachable — the
 * alethiometer always answers.
 */
import { CONFIG } from './config.js';
import { SYMBOLS, symbolIndex } from './symbols.js';

/** @typedef {{ stops: Array<{index: number, swings: number}>, interpretation: string, source: 'azure'|'local' }} Reading */

const isValidStop = (stop) =>
  stop && typeof stop.symbol === 'string' && symbolIndex(stop.symbol) >= 0
  && Number.isInteger(stop.swings) && stop.swings >= 1 && stop.swings <= 4;

/** Validate and normalize the API response into a Reading. Returns null if malformed. */
const parseApiReading = (data) => {
  if (!data || !Array.isArray(data.reading) || typeof data.interpretation !== 'string') return null;
  const stops = data.reading.filter(isValidStop).map((stop) => Object.freeze({
    index: symbolIndex(stop.symbol),
    swings: stop.swings,
  }));
  if (stops.length < 1 || data.interpretation.length < 10) return null;
  const sources = Array.isArray(data.sources)
    ? data.sources.filter((s) => typeof s === 'string' && /^https?:\/\//.test(s)).slice(0, 5)
    : [];
  return Object.freeze({
    stops: Object.freeze(stops.slice(0, 6)),
    interpretation: data.interpretation.slice(0, 2000),
    sources: Object.freeze(sources),
    source: 'azure',
  });
};

const fetchReading = async (question, handIndices) => {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), CONFIG.requestTimeoutMs);
  try {
    const response = await fetch(`${CONFIG.apiBase}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        question,
        symbols: handIndices.map((i) => SYMBOLS[i].name),
      }),
    });
    if (!response.ok) throw new Error(`API responded ${response.status}`);
    return parseApiReading(await response.json());
  } finally {
    clearTimeout(timer);
  }
};

/** Small deterministic hash so the same question yields the same local reading. */
const hashText = (text) => {
  let h = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
};

const LOCAL_OPENERS = Object.freeze([
  'The needle moves without hesitation.',
  'The needle circles twice, as if considering, then commits.',
  'The needle trembles before it settles.',
  'The needle sweeps in a slow, certain arc.',
]);

/** Compose a local reading from the question and the three hand symbols. */
const localReading = (question, handIndices) => {
  const seed = hashText(`${question}|${handIndices.join(',')}`);
  const count = 3 + (seed % 3);
  const stops = Array.from({ length: count }, (_, k) => {
    const mix = hashText(`${seed}:${k}`);
    return Object.freeze({ index: mix % SYMBOLS.length, swings: 1 + (mix >>> 8) % 3 });
  });
  const framed = handIndices.map((i) => SYMBOLS[i]);
  const parts = stops.map((stop, k) => {
    const symbol = SYMBOLS[stop.index];
    const meaning = symbol.meanings[(seed >>> (k * 3)) % symbol.meanings.length];
    return `${symbol.name} at the ${['first', 'second', 'third', 'fourth', 'fifth', 'sixth'][k]} level — ${meaning}`;
  });
  const interpretation = [
    LOCAL_OPENERS[seed % LOCAL_OPENERS.length],
    `You framed your question through ${framed[0].name}, ${framed[1].name}, and ${framed[2].name}.`,
    `It answers: ${parts.join('; ')}.`,
    'Hold the question lightly; the symbols say more the longer you sit with them.',
  ].join(' ');
  return Object.freeze({
    stops: Object.freeze(stops), interpretation, sources: Object.freeze([]), source: 'local',
  });
};

/**
 * Ask the alethiometer. Never throws: falls back to the local oracle.
 * @param {string} question
 * @param {ReadonlyArray<number>} handIndices - three symbol indices
 * @returns {Promise<Reading>}
 */
export const askOracle = async (question, handIndices) => {
  const trimmed = question.trim().slice(0, CONFIG.maxQuestionLength);
  if (trimmed.length === 0) {
    throw new Error('A question is required.');
  }
  try {
    const reading = await fetchReading(trimmed, handIndices);
    if (reading) return reading;
    console.warn('Oracle API returned a malformed reading; using local oracle.');
  } catch (error) {
    console.warn('Oracle API unreachable; using local oracle.', error);
  }
  return localReading(trimmed, handIndices);
};
