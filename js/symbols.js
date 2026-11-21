/**
 * The 36 symbols of the alethiometer, in wheel order.
 * Meanings are drawn from book canon (His Dark Materials, Lyra's Oxford)
 * and the reading tradition of alethiometrist scholarship; each symbol
 * carries an infinite descent of meanings — three are given here.
 * Frozen: symbol data is immutable.
 */
export const SYMBOLS = Object.freeze([
  { name: 'Hourglass', glyph: '⌛', meanings: ['time', 'death', 'change'] },
  { name: 'Sun', glyph: '☀️', meanings: ['day', 'authority', 'truth'] },
  { name: 'Alpha & Omega', glyph: 'ΑΩ', meanings: ['finality', 'beginnings and endings', 'inevitability'] },
  { name: 'Marionette', glyph: '🪆', meanings: ['obedience', 'submission', 'being moved by unseen hands'] },
  { name: 'Serpent', glyph: '🐍', meanings: ['guile', 'natural wisdom', 'temptation'] },
  { name: 'Cauldron', glyph: '⚗️', meanings: ['alchemy', 'craft', 'achieved knowledge'] },
  { name: 'Anchor', glyph: '⚓', meanings: ['hope', 'steadfastness', 'holding fast'] },
  { name: 'Angel', glyph: '👼', meanings: ['messages', 'the divine', 'disobedience'] },
  { name: 'Helmet', glyph: '🪖', meanings: ['war', 'protection', 'narrowed vision'] },
  { name: 'Beehive', glyph: '🐝', meanings: ['productive work', 'sweetness', 'community'] },
  { name: 'Moon', glyph: '🌙', meanings: ['mystery', 'the unseen', 'tides of feeling'] },
  { name: 'Madonna', glyph: '🤱', meanings: ['motherhood', 'devotion', 'the protective feminine'] },
  { name: 'Apple', glyph: '🍎', meanings: ['knowledge', 'temptation', 'consequence'] },
  { name: 'Bird', glyph: '🕊️', meanings: ['the soul', 'the dæmon', 'freedom'] },
  { name: 'Bread', glyph: '🍞', meanings: ['nourishment', 'sacrifice', 'the body'] },
  { name: 'Ant', glyph: '🐜', meanings: ['diligence', 'mechanism', 'small things compounding'] },
  { name: 'Bull', glyph: '🐂', meanings: ['earth', 'power', 'honesty'] },
  { name: 'Candle', glyph: '🕯️', meanings: ['fire', 'faith', 'learning'] },
  { name: 'Camel', glyph: '🐪', meanings: ['perseverance', 'travel', 'summer'] },
  { name: 'Cornucopia', glyph: '🧺', meanings: ['wealth', 'autumn', 'hospitality'] },
  { name: 'Chameleon', glyph: '🦎', meanings: ['air', 'patience', 'hunger never satisfied'] },
  { name: 'Compasses', glyph: '📐', meanings: ['measurement', 'mathematics', 'science'] },
  { name: 'Dolphin', glyph: '🐬', meanings: ['water', 'swiftness', 'rescue'] },
  { name: 'Elephant', glyph: '🐘', meanings: ['memory', 'sovereignty', 'restraint'] },
  { name: 'Salamander', glyph: '🔥', meanings: ['endurance', 'trial by fire', 'renewal'] },
  { name: 'Globe', glyph: '🌍', meanings: ['the world', 'politics', 'far places'] },
  { name: 'Griffin', glyph: '🦅', meanings: ['treasure', 'watchfulness', 'twinned natures'] },
  { name: 'Horse', glyph: '🐎', meanings: ['journeys', 'loyalty', 'nobility'] },
  { name: 'Lute', glyph: '🪕', meanings: ['poetry', 'rhetoric', 'consolation'] },
  { name: 'Owl', glyph: '🦉', meanings: ['wisdom', 'night', 'fear'] },
  { name: 'Sword', glyph: '⚔️', meanings: ['justice', 'force', 'division'] },
  { name: 'Thunderbolt', glyph: '⚡', meanings: ['inspiration', 'fate', 'sudden change'] },
  { name: 'Tree', glyph: '🌳', meanings: ['growth', 'firmness', 'shelter'] },
  { name: 'Walled Garden', glyph: '⛲', meanings: ['nature ordered', 'privacy', 'innocence'] },
  { name: 'Wild Man', glyph: '🧔', meanings: ['the untamed', 'raw strength', 'what civilisation forgets'] },
  { name: 'Baby', glyph: '👶', meanings: ['the future', 'potential', 'helplessness'] },
].map(Object.freeze));

export const SYMBOL_COUNT = SYMBOLS.length;

/** Degrees between adjacent symbols on the wheel. */
export const STEP_DEG = 360 / SYMBOL_COUNT;

/** @returns {number} index of a symbol by name, or -1 */
export const symbolIndex = (name) =>
  SYMBOLS.findIndex((s) => s.name.toLowerCase() === String(name).toLowerCase());

/** Angle in degrees (0 = twelve o'clock, clockwise) for a symbol index. */
export const symbolAngle = (index) => index * STEP_DEG;
