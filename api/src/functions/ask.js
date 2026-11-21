import { app } from '@azure/functions';
import {
  MAX_QUESTION_LENGTH,
  canonicalizeSymbols,
  clientIp,
  composeReading,
  isRateLimited,
  jsonResponse,
} from '../reading.js';

/** @returns {{question: string, symbols: string[]} | null} */
const validateBody = (body) => {
  if (!body || typeof body !== 'object') return null;
  const { question, symbols } = body;
  if (typeof question !== 'string') return null;
  const trimmed = question.trim();
  if (trimmed.length === 0 || trimmed.length > MAX_QUESTION_LENGTH) return null;
  const canonical = canonicalizeSymbols(symbols);
  if (!canonical) return null;
  return { question: trimmed, symbols: canonical };
};

app.http('ask', {
  methods: ['POST'],
  authLevel: 'anonymous',
  handler: async (request, context) => {
    if (isRateLimited(clientIp(request))) {
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

    const { reading, error } = await composeReading(payload, context);
    return error ?? jsonResponse(200, reading);
  },
});