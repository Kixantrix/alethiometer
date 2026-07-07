/** Deployment configuration. The API holds the Azure OpenAI key; this URL is public. */
export const CONFIG = Object.freeze({
  apiBase: 'https://func-alethiometer-kx.azurewebsites.net/api',
  requestTimeoutMs: 90000,
  maxQuestionLength: 300,
});
