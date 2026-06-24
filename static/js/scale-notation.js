/**
 * Scale notation renderer — draws a mini piano keyboard SVG showing which
 * keys are active for a given scale, plus a row of note name badges.
 *
 * Usage:
 *   renderScaleNotation(rootIndex, intervals, containerElement)
 *
 * rootIndex: 0–11 (C=0, C#=1, … B=11)
 * intervals: semitone offsets from root, e.g. [0,2,4,5,7,9,11] for major
 */

(function () {
  const NOTE_NAMES_SHARP = ['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B'];
  const NOTE_NAMES_FLAT  = ['C','D♭','D','E♭','E','F','G♭','G','A♭','A','B♭','B'];
  // Prefer flats for F, Bb, Eb, Ab, Db, Gb roots (indices 5,10,3,8,1,6)
  const PREFER_FLAT = new Set([1, 3, 5, 6, 8, 10]);

  function noteNames(rootIndex) {
    return PREFER_FLAT.has(rootIndex) ? NOTE_NAMES_FLAT : NOTE_NAMES_SHARP;
  }

  // Black key positions within an octave (0-indexed, semitones)
  const BLACK_KEYS = new Set([1, 3, 6, 8, 10]);

  function renderScaleNotation(rootIndex, intervals, container) {
    container.innerHTML = '';

    const names = noteNames(rootIndex);
    // Active semitone set (within octave, and the octave note)
    const activeSemitones = new Set(intervals.map(i => (rootIndex + i) % 12));
    activeSemitones.add(rootIndex); // root always active (already in intervals[0]=0 but be safe)

    // ── Note name badges ─────────────────────────────────────────────────────
    const badgeRow = document.createElement('div');
    badgeRow.className = 'flex flex-wrap gap-1.5 mb-4';

    intervals.forEach((interval, idx) => {
      const semitone = (rootIndex + interval) % 12;
      const badge = document.createElement('span');
      const isRoot = idx === 0;
      badge.className = 'px-2.5 py-1 rounded-full text-sm font-mono font-semibold ' +
        (isRoot
          ? 'bg-indigo-600 text-white'
          : BLACK_KEYS.has(semitone)
            ? 'bg-gray-700 text-gray-200'
            : 'bg-gray-800 text-gray-100');
      badge.textContent = names[semitone];
      badgeRow.appendChild(badge);
    });
    // Add the octave note
    const octaveBadge = document.createElement('span');
    octaveBadge.className = 'px-2.5 py-1 rounded-full text-sm font-mono font-semibold bg-indigo-900/60 text-indigo-300';
    octaveBadge.textContent = names[rootIndex] + '\'';
    badgeRow.appendChild(octaveBadge);
    container.appendChild(badgeRow);

    // ── Piano keyboard SVG (2 octaves for context) ────────────────────────────
    const OCTAVES = 2;
    const WW = 28;  // white key width
    const WH = 80;  // white key height
    const BW = 17;  // black key width
    const BH = 50;  // black key height
    const WHITE_ORDER = [0, 2, 4, 5, 7, 9, 11]; // semitones for white keys in one octave
    const totalWhites = WHITE_ORDER.length * OCTAVES + 1; // +1 for final octave C
    const svgW = totalWhites * WW;
    const svgH = WH + 4;

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', `0 0 ${svgW} ${svgH}`);
    svg.setAttribute('width', '100%');
    svg.setAttribute('style', 'max-width:480px');

    // Draw white keys first
    let whiteIdx = 0;
    for (let oct = 0; oct < OCTAVES; oct++) {
      for (const semi of WHITE_ORDER) {
        const absoluteSemi = (rootIndex + (oct * 12) + semi) % 12;
        // semitone in scale (ignoring octave for highlighting)
        const inScale = activeSemitones.has((rootIndex + (oct * 12) + semi) % 12);
        // Is this the exact root (first occurrence)?
        const isRoot = semi === 0 && activeSemitones.has(rootIndex);
        const isOctaveNote = oct === 1 && semi === 0 && inScale;

        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', whiteIdx * WW + 1);
        rect.setAttribute('y', 2);
        rect.setAttribute('width', WW - 2);
        rect.setAttribute('height', WH);
        rect.setAttribute('rx', 3);

        if (oct === 0 && semi === 0) {
          rect.setAttribute('fill', inScale ? '#6366f1' : '#e2e8f0'); // root = indigo
          rect.setAttribute('stroke', '#4f46e5');
        } else if (isOctaveNote) {
          rect.setAttribute('fill', '#312e81');
          rect.setAttribute('stroke', '#4338ca');
        } else if (inScale) {
          rect.setAttribute('fill', '#818cf8');
          rect.setAttribute('stroke', '#6366f1');
        } else {
          rect.setAttribute('fill', '#e2e8f0');
          rect.setAttribute('stroke', '#94a3b8');
        }
        rect.setAttribute('stroke-width', 1);
        svg.appendChild(rect);
        whiteIdx++;
      }
    }
    // Final C (octave above end)
    {
      const inScale = true; // root note at top of scale
      const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      rect.setAttribute('x', whiteIdx * WW + 1);
      rect.setAttribute('y', 2);
      rect.setAttribute('width', WW - 2);
      rect.setAttribute('height', WH);
      rect.setAttribute('rx', 3);
      rect.setAttribute('fill', '#312e81');
      rect.setAttribute('stroke', '#4338ca');
      rect.setAttribute('stroke-width', 1);
      svg.appendChild(rect);
    }

    // Draw black keys on top
    whiteIdx = 0;
    const BLACK_OFFSETS = { 1: 0, 3: 1, 6: 3, 8: 4, 10: 5 }; // semitone -> white key index offset within octave
    for (let oct = 0; oct < OCTAVES; oct++) {
      const octaveWhiteStart = oct * WHITE_ORDER.length;
      for (const [semi, wOffset] of Object.entries(BLACK_OFFSETS)) {
        const s = parseInt(semi);
        const absoluteSemi = (rootIndex + (oct * 12) + s) % 12; // unused but kept for clarity
        const inScale = activeSemitones.has((rootIndex + (oct * 12) + s) % 12);
        const xPos = (octaveWhiteStart + parseInt(wOffset)) * WW + WW - Math.floor(BW / 2);

        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', xPos);
        rect.setAttribute('y', 2);
        rect.setAttribute('width', BW);
        rect.setAttribute('height', BH);
        rect.setAttribute('rx', 2);
        if (inScale) {
          rect.setAttribute('fill', '#4f46e5');
          rect.setAttribute('stroke', '#818cf8');
        } else {
          rect.setAttribute('fill', '#1e293b');
          rect.setAttribute('stroke', '#334155');
        }
        rect.setAttribute('stroke-width', 1);
        svg.appendChild(rect);
      }
    }

    container.appendChild(svg);
  }

  // Expose globally
  window.renderScaleNotation = renderScaleNotation;
})();
