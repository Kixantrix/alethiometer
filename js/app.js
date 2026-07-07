/** Application wiring: dial + interaction + oracle. */
import { SYMBOLS } from './symbols.js';
import { createDial } from './dial.js';
import {
  initialState, withSymbolAssigned, withActiveHand, withBusy,
  renderHandChips, renderLegend, setupSpeech,
} from './interaction.js';
import { askOracle } from './oracle.js';

const $ = (id) => document.getElementById(id);

const ORDINALS = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth'];

const describeStop = (stop, position) => {
  const symbol = SYMBOLS[stop.index];
  return `<li><span class="stop-glyph">${symbol.glyph}</span>`
    + `<strong>${symbol.name}</strong> — ${ORDINALS[position]} stop, `
    + `${stop.swings} swing${stop.swings > 1 ? 's' : ''}</li>`;
};

const main = () => {
  const svg = $('dial');
  const questionInput = $('question');
  const askButton = $('ask');
  const micButton = $('mic');
  const chipsBox = $('hand-chips');
  const legend = $('legend');
  const readingPanel = $('reading');
  const readingStops = $('reading-stops');
  const readingText = $('reading-text');
  const readingSources = $('reading-sources');
  const statusLine = $('status');

  let state = initialState();

  const dial = createDial(svg, {
    onSymbolClick: (symbolIdx) => {
      if (state.busy) return;
      const hand = state.activeHand;
      state = withSymbolAssigned(state, symbolIdx);
      dial.setHand(hand, symbolIdx);
      renderHandChips(chipsBox, state, selectHand);
    },
    onSymbolHover: (symbolIdx) => renderLegend(legend, symbolIdx),
  });

  const selectHand = (handIdx) => {
    if (state.busy) return;
    state = withActiveHand(state, handIdx);
    renderHandChips(chipsBox, state, selectHand);
  };

  state.hands.forEach((symbolIdx, i) => dial.setHand(i, symbolIdx));
  renderHandChips(chipsBox, state, selectHand);
  renderLegend(legend, -1);
  setupSpeech(micButton, questionInput, (listening) => {
    statusLine.textContent = listening ? 'Listening…' : '';
  });

  const setBusy = (busy) => {
    state = withBusy(state, busy);
    askButton.disabled = busy;
    questionInput.disabled = busy;
  };

  const ask = async () => {
    const question = questionInput.value.trim();
    if (!question) {
      statusLine.textContent = 'Frame a question first.';
      questionInput.focus();
      return;
    }
    setBusy(true);
    readingPanel.classList.remove('visible');
    readingStops.innerHTML = '';
    readingText.textContent = '';
    readingSources.replaceChildren();
    statusLine.textContent = 'The needle is moving… (questions about the wider world can take a minute)';
    try {
      const reading = await askOracle(question, state.hands);
      const finished = await dial.animateNeedle(reading.stops, (index) => {
        dial.setHighlight(index);
      });
      dial.setHighlight(-1);
      if (finished) {
        readingStops.innerHTML = reading.stops.map(describeStop).join('');
        readingText.textContent = reading.interpretation;
        if (reading.sources.length > 0) {
          const label = document.createElement('span');
          label.textContent = 'Glimpsed through the aether: ';
          readingSources.replaceChildren(label, ...reading.sources.map((url, i) => {
            const a = document.createElement('a');
            a.href = url;
            a.target = '_blank';
            a.rel = 'noopener noreferrer';
            try { a.textContent = new URL(url).hostname.replace(/^www\./, ''); }
            catch { a.textContent = `source ${i + 1}`; }
            return a;
          }));
        }
        readingPanel.classList.add('visible');
        statusLine.textContent = reading.source === 'local'
          ? 'Read by the device alone (the scholar could not be reached).'
          : '';
      }
    } catch (error) {
      console.error('Reading failed:', error);
      statusLine.textContent = error.message || 'The instrument is silent. Try again.';
    } finally {
      setBusy(false);
    }
  };

  askButton.addEventListener('click', ask);
  questionInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') ask();
  });
};

document.addEventListener('DOMContentLoaded', main);
