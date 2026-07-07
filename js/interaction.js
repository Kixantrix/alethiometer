/**
 * User interaction: hand selection, symbol assignment, and speech input.
 * State is held immutably; every change produces a new state object.
 */
import { SYMBOLS } from './symbols.js';

/** @typedef {{ hands: ReadonlyArray<number>, activeHand: number, busy: boolean }} DialState */

export const initialState = () => Object.freeze({
  hands: Object.freeze([0, 12, 24]),
  activeHand: 0,
  busy: false,
});

/** Assign a symbol to the active hand; advances the active hand 1→2→3→1. */
export const withSymbolAssigned = (state, symbolIdx) => Object.freeze({
  ...state,
  hands: Object.freeze(state.hands.map((v, i) => (i === state.activeHand ? symbolIdx : v))),
  activeHand: (state.activeHand + 1) % state.hands.length,
});

export const withActiveHand = (state, handIdx) => Object.freeze({ ...state, activeHand: handIdx });

export const withBusy = (state, busy) => Object.freeze({ ...state, busy });

/** Render the three hand chips into their container. */
export const renderHandChips = (container, state, onSelect) => {
  container.replaceChildren(...state.hands.map((symbolIdx, i) => {
    const symbol = SYMBOLS[symbolIdx];
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = `hand-chip${i === state.activeHand ? ' active' : ''}`;
    chip.innerHTML = `<span class="chip-ordinal">${['I', 'II', 'III'][i]}</span>`
      + `<span class="chip-glyph">${symbol.glyph}</span>`
      + `<span class="chip-name">${symbol.name}</span>`;
    chip.addEventListener('click', () => onSelect(i));
    return chip;
  }));
};

/** Show a symbol's name and meanings in the legend line. */
export const renderLegend = (node, symbolIdx) => {
  if (symbolIdx < 0) {
    node.textContent = 'Hover a symbol to read its meanings. Click to set the selected hand.';
    node.classList.remove('legend-lit');
    return;
  }
  const symbol = SYMBOLS[symbolIdx];
  node.textContent = `${symbol.glyph} ${symbol.name} — ${symbol.meanings.join(' · ')}`;
  node.classList.add('legend-lit');
};

/**
 * Wire up the mic button using the browser's Web Speech API.
 * Hides the button when the API is unavailable.
 */
export const setupSpeech = (button, input, onStateChange) => {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    button.hidden = true;
    return;
  }
  let listening = false;
  const recognizer = new Recognition();
  recognizer.lang = 'en-US';
  recognizer.interimResults = false;
  recognizer.maxAlternatives = 1;

  recognizer.addEventListener('result', (event) => {
    const transcript = event.results[0]?.[0]?.transcript ?? '';
    if (transcript) input.value = transcript;
  });
  recognizer.addEventListener('end', () => {
    listening = false;
    button.classList.remove('listening');
    onStateChange(false);
  });
  recognizer.addEventListener('error', (event) => {
    console.warn('Speech recognition error:', event.error);
  });

  button.addEventListener('click', () => {
    if (listening) {
      recognizer.stop();
      return;
    }
    try {
      recognizer.start();
      listening = true;
      button.classList.add('listening');
      onStateChange(true);
    } catch (error) {
      console.warn('Could not start speech recognition:', error);
    }
  });
};
