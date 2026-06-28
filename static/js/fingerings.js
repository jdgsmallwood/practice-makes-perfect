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
 * `midi` is the *concert-pitch* MIDI number of the note being played. For
 * transposing instruments we convert to the written note before looking up the
 * fingering (e.g. a cornet sounds a major 2nd below what the player reads).
 */

(function () {
  // Concert -> written transposition, in semitones (written = concert + offset).
  const TRANSPOSE = { flute: 0, cornet: 2, trumpet: 2 };

  // ── Brass: valve combinations by written pitch class ─────────────────────
  // [] = open; numbers are the valves pressed (1 = nearest the mouthpiece).
  // Standard 3-valve combinations, identical for cornet and trumpet.
  const VALVES_BY_PC = {
    0:  [],        // C
    1:  [1, 2, 3], // C#/Db
    2:  [1, 3],    // D
    3:  [2, 3],    // D#/Eb
    4:  [1, 2],    // E
    5:  [1],       // F
    6:  [2],       // F#/Gb
    7:  [],        // G
    8:  [2, 3],    // G#/Ab
    9:  [1, 2],    // A
    10: [1],       // A#/Bb
    11: [2],       // B
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

  function writtenPc(instrument, midi) {
    const offset = TRANSPOSE[instrument] || 0;
    return (((midi + offset) % 12) + 12) % 12;
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
    if (TRANSPOSE[instrument] == null) return null;
    const pc = writtenPc(instrument, midi);
    if (instrument === 'cornet' || instrument === 'trumpet') {
      return valveDiagram(VALVES_BY_PC[pc]);
    }
    if (instrument === 'flute') {
      const keys = FLUTE_BY_PC[pc];
      return keys ? fluteDiagram(keys) : null;
    }
    return null;
  }

  window.scaleFingerings = {
    supports: (instrument) => TRANSPOSE[instrument] != null,
    renderFingering,
  };
})();
