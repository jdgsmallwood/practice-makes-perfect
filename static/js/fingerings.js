/**
 * Instrument fingering charts for scale notation.
 *
 * This is the first slice of a larger feature — only flute and cornet/trumpet
 * are covered so far, and the flute chart is the reliable beginner range only
 * (notes we don't have data for render as "—" so it's obvious where the chart
 * still needs filling in). Extend the data tables below to add coverage.
 *
 * API (consumed by scale-notation.js):
 *   window.scaleFingerings.supports(instrumentSlug) -> bool
 *   window.scaleFingerings.renderFingering(instrumentSlug, midi) -> Element|null
 *
 * `midi` is the *written-pitch* MIDI number of the note as it appears on the
 * player's staff. scale-notation.js has already applied any transposition, so
 * the fingering is looked up directly from the written pitch class.
 */

(function () {
  // Instruments we have fingering charts for. (Transposition to written pitch is
  // handled upstream in scale-notation.js.)
  const BRASS = new Set(['cornet', 'trumpet', 'flugelhorn']);
  const SUPPORTED = new Set(['flute', 'cornet', 'trumpet', 'flugelhorn']);

  // ── Brass: valve combinations by WRITTEN MIDI note ───────────────────────
  // [] = open; numbers are the valves pressed (1 = nearest the mouthpiece).
  // Standard 3-valve combinations, identical for cornet, trumpet and flugelhorn.
  // Keyed by absolute written pitch (not pitch class) because the harmonic series
  // gives the same note name different fingerings in different octaves — e.g.
  // written D4 is 1-3 but D5 is 1, and E4 is 1-2 but E5 is open. Covers the
  // practical scale range F#3 (54) to D6 (86); notes outside render as "—".
  const VALVES_BY_MIDI = {
    54: [1, 2, 3], // F#3
    55: [1, 3],    // G3
    56: [2, 3],    // G#3
    57: [1, 2],    // A3
    58: [1],       // Bb3
    59: [2],       // B3
    60: [],        // C4
    61: [1, 2, 3], // C#4
    62: [1, 3],    // D4
    63: [2, 3],    // Eb4
    64: [1, 2],    // E4
    65: [1],       // F4
    66: [2],       // F#4
    67: [],        // G4
    68: [2, 3],    // G#4
    69: [1, 2],    // A4
    70: [1],       // Bb4
    71: [2],       // B4
    72: [],        // C5
    73: [1, 2],    // C#5
    74: [1],       // D5
    75: [2, 3],    // Eb5
    76: [],        // E5
    77: [1],       // F5
    78: [2],       // F#5
    79: [],        // G5
    80: [2, 3],    // G#5
    81: [1, 2],    // A5
    82: [1],       // Bb5
    83: [2],       // B5
    84: [],        // C6
    85: [1, 2],    // C#6
    86: [1],       // D6
  };

  // ── Flute: simplified Boehm fingerings by written pitch class ─────────────
  // Keys, top to bottom: [Thumb, LH1, LH2, LH3, RH1, RH2, RH3, Eb(pinky)].
  // 1 = key down. Covers the reliable diatonic beginner range; C and the
  // remaining accidentals are left out (null) until verified.
  const FLUTE_BY_PC = {
    2:  [1, 1, 1, 1, 1, 1, 1, 1], // D
    4:  [1, 1, 1, 1, 1, 1, 0, 1], // E
    5:  [1, 1, 1, 1, 1, 0, 0, 1], // F
    6:  [1, 1, 1, 1, 0, 0, 1, 1], // F#
    7:  [1, 1, 1, 1, 0, 0, 0, 1], // G
    9:  [1, 1, 1, 0, 0, 0, 0, 1], // A
    11: [1, 1, 0, 0, 0, 0, 0, 1], // B
  };

  function pitchClass(midi) {
    return (((midi % 12) + 12) % 12);
  }

  function dot(filled, title) {
    const d = document.createElement('span');
    d.title = title || '';
    d.style.display = 'inline-block';
    d.style.width = '8px';
    d.style.height = '8px';
    d.style.borderRadius = '9999px';
    d.style.border = '1px solid #9ca3af';
    d.style.background = filled ? '#9ca3af' : 'transparent';
    return d;
  }

  function valveDiagram(valves) {
    const wrap = document.createElement('div');
    wrap.style.display = 'flex';
    wrap.style.gap = '2px';
    wrap.style.justifyContent = 'center';
    for (let v = 1; v <= 3; v++) {
      wrap.appendChild(dot(valves.includes(v), 'Valve ' + v));
    }
    return wrap;
  }

  // Vertical column of key dots, grouped Thumb / LH / RH / Eb.
  function fluteDiagram(keys) {
    const wrap = document.createElement('div');
    wrap.style.display = 'flex';
    wrap.style.flexDirection = 'column';
    wrap.style.alignItems = 'center';
    wrap.style.gap = '2px';
    const groups = [[0], [1, 2, 3], [4, 5, 6], [7]];
    const labels = ['Thumb', 'LH', 'LH', 'LH', 'RH', 'RH', 'RH', 'Eb'];
    groups.forEach((group, gi) => {
      const row = document.createElement('div');
      row.style.display = 'flex';
      row.style.gap = '2px';
      if (gi > 0) row.style.marginTop = '1px';
      group.forEach((k) => row.appendChild(dot(keys[k] === 1, labels[k])));
      wrap.appendChild(row);
    });
    return wrap;
  }

  function renderFingering(instrument, midi) {
    if (!SUPPORTED.has(instrument)) return null;
    if (BRASS.has(instrument)) {
      const valves = VALVES_BY_MIDI[midi];
      return valves ? valveDiagram(valves) : null;
    }
    if (instrument === 'flute') {
      const keys = FLUTE_BY_PC[pitchClass(midi)];
      return keys ? fluteDiagram(keys) : null;
    }
    return null;
  }

  window.scaleFingerings = {
    supports: (instrument) => SUPPORTED.has(instrument),
    renderFingering,
  };
})();
