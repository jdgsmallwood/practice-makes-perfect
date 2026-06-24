/**
 * Scale notation renderer — generates ABC notation string from root + intervals
 * and renders it to staff notation via abcjs.
 *
 * Usage: renderScaleNotation(rootIndex, intervals, containerElement)
 *   rootIndex: 0–11 (C=0, C#=1, … B=11)
 *   intervals: semitone offsets from root, e.g. [0,2,4,5,7,9,11]
 */

(function () {
  const PREFER_FLAT = new Set([1, 3, 5, 6, 8, 10]);
  const ACC_SHARP = ['C', '^C', 'D', '^D', 'E', 'F', '^F', 'G', '^G', 'A', '^A', 'B'];
  const ACC_FLAT  = ['C', '_D', 'D', '_E', 'E', 'F', '_G', 'G', '_A', 'A', '_B', 'B'];
  const NOTE_NAMES_SHARP = ['C', 'C♯', 'D', 'D♯', 'E', 'F', 'F♯', 'G', 'G♯', 'A', 'A♯', 'B'];
  const NOTE_NAMES_FLAT  = ['C', 'D♭', 'D', 'E♭', 'E', 'F', 'G♭', 'G', 'A♭', 'A', 'B♭', 'B'];
  const BLACK_KEYS = new Set([1, 3, 6, 8, 10]);

  // Convert an absolute semitone offset from C4 into an ABC note token.
  // octOff 0 = C4–B4 (lowercase), 1 = C5–B5 (lowercase + '), etc.
  function abcNote(abs, useFlats) {
    const acc = useFlats ? ACC_FLAT : ACC_SHARP;
    const pc = ((abs % 12) + 12) % 12;
    const octOff = Math.floor(abs / 12);
    let n = acc[pc].replace(/[A-G]/, ch => ch.toLowerCase());
    if (octOff > 0) n += "'".repeat(octOff);
    else if (octOff < 0) n += ','.repeat(-octOff);
    return n;
  }

  function buildABC(rootIndex, intervals) {
    const useFlats = PREFER_FLAT.has(rootIndex);
    // Ascending scale + octave note
    const notes = intervals.map(iv => abcNote(rootIndex + iv, useFlats));
    notes.push(abcNote(rootIndex + 12, useFlats));
    return [
      'X:1',
      'L:1/8',
      'M:none',
      'K:C clef=treble',
      notes.join(' ') + ' |]',
    ].join('\n');
  }

  function renderScaleNotation(rootIndex, intervals, container) {
    container.innerHTML = '';

    // Staff notation (abcjs)
    if (typeof ABCJS !== 'undefined') {
      const staffWrap = document.createElement('div');
      staffWrap.className = 'bg-white rounded-lg overflow-hidden mb-3';
      container.appendChild(staffWrap);
      ABCJS.renderAbc(staffWrap, buildABC(rootIndex, intervals), {
        responsive: 'resize',
        paddingtop: 8,
        paddingbottom: 4,
        paddingleft: 12,
        paddingright: 12,
      });
    }

    // Note name badges
    const useFlats = PREFER_FLAT.has(rootIndex);
    const names = useFlats ? NOTE_NAMES_FLAT : NOTE_NAMES_SHARP;
    const badgeRow = document.createElement('div');
    badgeRow.className = 'flex flex-wrap gap-1.5';
    intervals.forEach((interval, idx) => {
      const semitone = (rootIndex + interval) % 12;
      const badge = document.createElement('span');
      badge.className = 'px-2.5 py-1 rounded-full text-sm font-mono font-semibold ' +
        (idx === 0
          ? 'bg-indigo-600 text-white'
          : BLACK_KEYS.has(semitone)
            ? 'bg-gray-700 text-gray-200'
            : 'bg-gray-800 text-gray-100');
      badge.textContent = names[semitone];
      badgeRow.appendChild(badge);
    });
    const octaveBadge = document.createElement('span');
    octaveBadge.className = 'px-2.5 py-1 rounded-full text-sm font-mono font-semibold bg-indigo-900/60 text-indigo-300';
    octaveBadge.textContent = names[rootIndex] + "'";
    badgeRow.appendChild(octaveBadge);
    container.appendChild(badgeRow);
  }

  window.renderScaleNotation = renderScaleNotation;
})();
