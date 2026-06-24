/**
 * Scale notation renderer — generates ABC notation string from root + intervals
 * and renders it to staff notation via abcjs, with optional audio playback.
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
  const BPM = 100;

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
    const notes = intervals.map(iv => abcNote(rootIndex + iv, useFlats));
    notes.push(abcNote(rootIndex + 12, useFlats));
    return [
      'X:1',
      'Q:1/4=' + BPM,
      'L:1/8',
      'M:none',
      'K:C clef=treble',
      notes.join(' ') + ' |]',
    ].join('\n');
  }

  function renderScaleNotation(rootIndex, intervals, container) {
    container.innerHTML = '';

    let currentSynth = null;
    let currentTimeout = null;

    // Staff notation
    let visualObj = null;
    if (typeof ABCJS !== 'undefined') {
      const staffWrap = document.createElement('div');
      staffWrap.className = 'bg-white rounded-lg overflow-hidden mb-3';
      container.appendChild(staffWrap);
      const result = ABCJS.renderAbc(staffWrap, buildABC(rootIndex, intervals), {
        responsive: 'resize',
        scale: 1.8,
        paddingtop: 16,
        paddingbottom: 16,
        paddingleft: 20,
        paddingright: 20,
      });
      if (result && result.length > 0) visualObj = result[0];
    }

    // Play button (only if synth is available)
    const canPlay = visualObj &&
      typeof ABCJS !== 'undefined' &&
      ABCJS.synth &&
      ABCJS.synth.supportsAudio();

    if (canPlay) {
      const idleClass = 'px-3 py-1.5 rounded-lg text-xs font-semibold bg-gray-700 hover:bg-gray-600 text-gray-200 transition-colors';
      const activeClass = 'px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-700 hover:bg-indigo-600 text-white transition-colors';

      const playBtn = document.createElement('button');
      playBtn.className = idleClass;
      playBtn.textContent = '▶ Play';

      function resetPlay() {
        if (currentTimeout) { clearTimeout(currentTimeout); currentTimeout = null; }
        if (currentSynth) { try { currentSynth.stop(); } catch (e) {} currentSynth = null; }
        playBtn.textContent = '▶ Play';
        playBtn.className = idleClass;
        playBtn.disabled = false;
      }

      playBtn.addEventListener('click', async () => {
        if (currentSynth) { resetPlay(); return; }

        // AudioContext must be created synchronously inside a user gesture (Safari requirement)
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        if (audioContext.state === 'suspended') await audioContext.resume();

        playBtn.disabled = true;
        playBtn.textContent = '…';

        try {
          const synth = new ABCJS.synth.CreateSynth();
          await synth.init({ audioContext, visualObj, options: {} });
          await synth.prime();
          currentSynth = synth;
          playBtn.disabled = false;
          playBtn.textContent = '■ Stop';
          playBtn.className = activeClass;
          synth.start();

          // Auto-reset when done: (n 8th notes) at BPM, plus a short buffer
          const totalNotes = intervals.length + 1;
          const durationMs = totalNotes * (60000 / BPM / 2) + 800;
          currentTimeout = setTimeout(resetPlay, durationMs);
        } catch (e) {
          console.error('Scale audio error:', e);
          playBtn.disabled = false;
          playBtn.textContent = '▶ Play';
          playBtn.className = idleClass;
        }
      });

      const playRow = document.createElement('div');
      playRow.className = 'mb-3';
      playRow.appendChild(playBtn);
      container.appendChild(playRow);
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
