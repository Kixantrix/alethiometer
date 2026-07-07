/**
 * SVG rendering of the alethiometer dial: bezel, 36-symbol ring,
 * three question hands, and the answer needle with its swing animation.
 */
import { SYMBOLS, symbolAngle } from './symbols.js';

const SIZE = 640;
const CENTER = SIZE / 2;
const SYMBOL_RADIUS = 268;
const TICK_RADIUS = 238;
const HAND_LENGTHS = Object.freeze([158, 182, 206]);
const NEEDLE_LENGTH = 228;
const SVG_NS = 'http://www.w3.org/2000/svg';

const el = (tag, attrs = {}) => {
  const node = document.createElementNS(SVG_NS, tag);
  Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, String(v)));
  return node;
};

const polar = (radius, angleDeg) => {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: CENTER + radius * Math.cos(rad), y: CENTER + radius * Math.sin(rad) };
};

const buildDefs = () => {
  const defs = el('defs');
  defs.innerHTML = `
    <radialGradient id="face" cx="50%" cy="42%" r="65%">
      <stop offset="0%" stop-color="#f6e3b0"/>
      <stop offset="55%" stop-color="#e8c877"/>
      <stop offset="85%" stop-color="#c89b4a"/>
      <stop offset="100%" stop-color="#9a7332"/>
    </radialGradient>
    <linearGradient id="bezel" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#8a6a2f"/>
      <stop offset="30%" stop-color="#d9b869"/>
      <stop offset="55%" stop-color="#7c5f28"/>
      <stop offset="80%" stop-color="#e2c47a"/>
      <stop offset="100%" stop-color="#6b511f"/>
    </linearGradient>
    <linearGradient id="hand" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#3d2f12"/>
      <stop offset="100%" stop-color="#7a5f2a"/>
    </linearGradient>
    <linearGradient id="needle" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#9fc2e8"/>
      <stop offset="100%" stop-color="#2c4a6e"/>
    </linearGradient>
    <filter id="engrave" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="1" stdDeviation="0.6" flood-color="#5c4418" flood-opacity="0.7"/>
    </filter>
  `;
  return defs;
};

const buildFace = () => {
  const g = el('g');
  g.appendChild(el('circle', { cx: CENTER, cy: CENTER, r: 314, fill: 'url(#bezel)' }));
  g.appendChild(el('circle', { cx: CENTER, cy: CENTER, r: 298, fill: '#4a3714' }));
  g.appendChild(el('circle', { cx: CENTER, cy: CENTER, r: 292, fill: 'url(#face)' }));
  g.appendChild(el('circle', {
    cx: CENTER, cy: CENTER, r: TICK_RADIUS + 6,
    fill: 'none', stroke: '#7c5f28', 'stroke-width': 2, opacity: 0.6,
  }));
  SYMBOLS.forEach((_, i) => {
    const angle = symbolAngle(i) + 5;
    const a = polar(TICK_RADIUS + 2, angle);
    const b = polar(TICK_RADIUS + 12, angle);
    g.appendChild(el('line', {
      x1: a.x, y1: a.y, x2: b.x, y2: b.y, stroke: '#7c5f28', 'stroke-width': 1.5, opacity: 0.7,
    }));
  });
  return g;
};

const buildSymbolRing = (onClick, onHover) => {
  const g = el('g', { class: 'symbol-ring' });
  SYMBOLS.forEach((symbol, i) => {
    const pos = polar(SYMBOL_RADIUS, symbolAngle(i));
    const item = el('g', { class: 'symbol', 'data-index': i, filter: 'url(#engrave)' });
    const hit = el('circle', { cx: pos.x, cy: pos.y, r: 17, fill: 'transparent' });
    const label = el('text', {
      x: pos.x, y: pos.y, 'text-anchor': 'middle', 'dominant-baseline': 'central',
      'font-size': symbol.glyph.length > 2 ? 13 : 19, class: 'symbol-glyph',
    });
    label.textContent = symbol.glyph;
    item.appendChild(label);
    item.appendChild(hit);
    item.addEventListener('click', () => onClick(i));
    item.addEventListener('mouseenter', () => onHover(i));
    item.addEventListener('mouseleave', () => onHover(-1));
    g.appendChild(item);
  });
  return g;
};

const handPath = (length) => {
  const tip = CENTER - length;
  return [
    `M ${CENTER} ${tip}`,
    `L ${CENTER - 7} ${CENTER - length * 0.55}`,
    `L ${CENTER - 3} ${CENTER}`,
    `L ${CENTER + 3} ${CENTER}`,
    `L ${CENTER + 7} ${CENTER - length * 0.55}`,
    'Z',
  ].join(' ');
};

const needlePath = () => {
  const tip = CENTER - NEEDLE_LENGTH;
  return `M ${CENTER} ${tip} L ${CENTER - 3.5} ${CENTER + 26} L ${CENTER + 3.5} ${CENTER + 26} Z`;
};

const rotationAttr = (deg) => `rotate(${deg} ${CENTER} ${CENTER})`;

const easeOutCubic = (t) => 1 - (1 - t) ** 3;
const easeInOut = (t) => (t < 0.5 ? 2 * t * t : 1 - ((-2 * t + 2) ** 2) / 2);

/**
 * Create the dial inside an <svg> element.
 * @returns dial API: setHand, animateNeedle, setHighlight, cancel
 */
export const createDial = (svg, { onSymbolClick, onSymbolHover }) => {
  svg.setAttribute('viewBox', `0 0 ${SIZE} ${SIZE}`);
  svg.appendChild(buildDefs());
  svg.appendChild(buildFace());
  svg.appendChild(buildSymbolRing(onSymbolClick, onSymbolHover));

  const hands = HAND_LENGTHS.map((length, i) => {
    const hand = el('path', {
      d: handPath(length), fill: 'url(#hand)', stroke: '#2e2208',
      'stroke-width': 0.8, class: `hand hand-${i}`,
    });
    svg.appendChild(hand);
    return hand;
  });

  const needle = el('path', {
    d: needlePath(), fill: 'url(#needle)', stroke: '#1b2f47',
    'stroke-width': 0.6, class: 'needle',
  });
  svg.appendChild(needle);
  svg.appendChild(el('circle', {
    cx: CENTER, cy: CENTER, r: 14, fill: 'url(#bezel)', stroke: '#3d2f12', 'stroke-width': 1.5,
  }));

  let needleAngle = 0;
  let animationId = 0;
  needle.setAttribute('transform', rotationAttr(needleAngle));

  const setHand = (handIdx, symbolIdx) => {
    if (handIdx < 0 || handIdx >= hands.length) return;
    hands[handIdx].style.transition = 'transform 0.7s cubic-bezier(0.34, 1.4, 0.64, 1)';
    hands[handIdx].style.transformOrigin = `${CENTER}px ${CENTER}px`;
    hands[handIdx].style.transform = `rotate(${symbolAngle(symbolIdx)}deg)`;
  };

  const setHighlight = (symbolIdx) => {
    svg.querySelectorAll('.symbol').forEach((node) => {
      node.classList.toggle('lit', Number(node.dataset.index) === symbolIdx);
    });
  };

  const rotateNeedleTo = (targetDeg, duration, ease) => new Promise((resolve) => {
    const startDeg = needleAngle;
    const start = performance.now();
    const id = ++animationId;
    const frame = (now) => {
      if (id !== animationId) { resolve(false); return; }
      const t = Math.min(1, (now - start) / duration);
      needleAngle = startDeg + (targetDeg - startDeg) * ease(t);
      needle.setAttribute('transform', rotationAttr(needleAngle));
      if (t < 1) requestAnimationFrame(frame); else resolve(true);
    };
    requestAnimationFrame(frame);
  });

  /**
   * Swing the needle through a sequence of stops.
   * @param {ReadonlyArray<{index: number, swings: number}>} stops
   * @param {(index: number, stop: number) => void} onArrive
   */
  const animateNeedle = async (stops, onArrive) => {
    for (let s = 0; s < stops.length; s += 1) {
      const { index, swings } = stops[s];
      const base = Math.ceil(needleAngle / 360) * 360 + 360 + symbolAngle(index);
      const arrived = await rotateNeedleTo(base, 1500, easeOutCubic);
      if (!arrived) return false;
      onArrive(index, s);
      for (let k = 1; k < Math.min(swings, 4); k += 1) {
        if (!(await rotateNeedleTo(base - 22, 260, easeInOut))) return false;
        if (!(await rotateNeedleTo(base, 340, easeOutCubic))) return false;
        onArrive(index, s);
      }
      await new Promise((r) => setTimeout(r, 350));
    }
    return true;
  };

  const cancel = () => { animationId += 1; };

  return Object.freeze({ setHand, animateNeedle, setHighlight, cancel });
};
