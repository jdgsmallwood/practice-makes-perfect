/**
 * Scale notation renderer — generates ABC notation string from root + intervals
 * and renders it to staff notation via abcjs, with optional audio playback.
 *
 * Usage: renderScaleNotation(rootIndex, intervals, container, midiLow, instrument)
 *   rootIndex:  0–11 (C=0, C#=1, … B=11)
 *   intervals:  ascending semitone offsets from root, e.g. [0,2,4,5,7,9,11]
 *   container:  DOM element to render into
 *   midiLow:    lowest MIDI note of the player's instrument (default 60 = C4)
 *   instrument: optional instrument slug (e.g. 'flute', 'cornet') — enables the
 *               fingering toggle when fingering data is available for it.
 *
 * Notes are rendered as crotchets (quarter notes), starting from the lowest
 * tonic that sits within the instrument's range, ascending one octave and then
 * descending back to the tonic. Melodic minor uses its descending form (natural
 * minor) on the way down.
 */

(function () {
  // How many semitones the instrument SOUNDS below what it reads. The selected
  // scale root is the note the player actually reads/plays, so the staff, note
  // badges and fingerings are shown exactly as written (no shift). Only the audio
  // is transposed down by this amount so it plays back at concert (sounding) pitch
  // — e.g. a cornet reading F sounds Eb. Unlisted instruments sound as written (0).
  const SOUNDS_BELOW = { flute: 0, cornet: 2, trumpet: 2, flugelhorn: 2 };

  const PREFER_FLAT = new Set([1, 3, 5, 6, 8, 10]);
  const ACC_SHARP = ['C', '^C', 'D', '^D', 'E', 'F', '^F', 'G', '^G', 'A', '^A', 'B'];
  const ACC_FLAT  = ['C', '_D', 'D', '_E', 'E', 'F', '_G', 'G', '_A', 'A', '_B', 'B'];
  const NOTE_NAMES_SHARP = ['C', 'C♯', 'D', 'D♯', 'E', 'F', 'F♯', 'G', 'G♯', 'A', 'A♯', 'B'];
  const NOTE_NAMES_FLAT  = ['C', 'D♭', 'D', 'E♭', 'E', 'F', 'G♭', 'G', 'A♭', 'A', 'B♭', 'B'];
  const BLACK_KEYS = new Set([1, 3, 6, 8, 10]);
  const BPM = 100;

  // Melodic minor ascends with raised 6th/7th but descends as natural minor.
  // Detect it by its (unique) ascending interval signature so we can pick the
  // correct descending form without threading the scale slug through templates.
  const MELODIC_MINOR_ASC = [0, 2, 3, 5, 7, 9, 11];
  const MELODIC_MINOR_DESC = [0, 2, 3, 5, 7, 8, 10];

  function sameIntervals(a, b) {
    return a.length === b.length && a.every((v, i) => v === b[i]);
  }

  // The intervals used on the way down (top → tonic). Defaults to the ascending
  // set; melodic minor is the notable exception.
  function descendingIntervals(intervals) {
    if (sameIntervals(intervals, MELODIC_MINOR_ASC)) return MELODIC_MINOR_DESC;
    return intervals;
  }

  function abcNote(abs, useFlats) {
    const acc = useFlats ? ACC_FLAT : ACC_SHARP;
    const pc = ((abs % 12) + 12) % 12;
    // abs is semitones relative to MIDI 60 = C4. In ABC, the middle octave
    // (C4..B4) is uppercase with no octave mark; each octave above lowercases
    // and adds an apostrophe, each octave below adds a comma.
    const octOff = Math.floor(abs / 12);
    let n = acc[pc]; // uppercase = middle octave (C4..B4)
    if (octOff > 0) {
      n = n.replace(/[A-G]/, ch => ch.toLowerCase()) + "'".repeat(octOff - 1);
    } else if (octOff < 0) {
      n += ','.repeat(-octOff);
    }
    return n;
  }

  // Returns the lowest MIDI note >= midiLow that shares rootPc's pitch class.
  function lowestTonic(rootPc, midiLow) {
    const base = Math.floor(midiLow / 12) * 12 + rootPc;
    return base >= midiLow ? base : base + 12;
  }

  // Absolute semitone offsets (relative to MIDI 60 = C4) for every note played,
  // ascending one octave then descending back to the tonic.
  function noteSequence(intervals, startMidi) {
    const startAbs = startMidi - 60;
    const asc = intervals.map(iv => startAbs + iv);
    asc.push(startAbs + 12); // octave
    // Descend from just below the octave back to (and including) the tonic.
    const desc = descendingIntervals(intervals)
      .slice()
      .reverse()
      .map(iv => startAbs + iv);
    return { asc, desc, all: asc.concat(desc) };
  }

  function buildABC(rootIndex, intervals, startMidi) {
    const useFlats = PREFER_FLAT.has(rootIndex);
    const seq = noteSequence(intervals, startMidi);
    const ascStr = seq.asc.map(a => abcNote(a, useFlats)).join(' ');
    const descStr = seq.desc.map(a => abcNote(a, useFlats)).join(' ');
    return [
      'X:1',
      'Q:1/4=' + BPM,
      'L:1/4',
      'M:none',
      'K:C clef=treble',
      ascStr + ' | ' + descStr + ' |]',
    ].join('\n');
  }

  function renderScaleNotation(rootIndex, intervals, container, midiLow, instrument) {
    container.innerHTML = '';

    // The selected root is the note the player reads/plays, so the staff is built
    // on it directly. Audio is dropped by this many semitones to sound at concert.
    const soundsBelow = SOUNDS_BELOW[instrument] || 0;

    const startMidi = lowestTonic(rootIndex, midiLow != null ? midiLow : 60);

    let currentSynth = null;
    let currentTimeout = null;

    // Staff notation
    let visualObj = null;
    if (typeof ABCJS !== 'undefined') {
      const staffWrap = document.createElement('div');
      staffWrap.className = 'bg-white rounded-lg overflow-hidden mb-3';
      staffWrap.style.color = '#000';
      container.appendChild(staffWrap);
      const result = ABCJS.renderAbc(staffWrap, buildABC(rootIndex, intervals, startMidi), {
        scale: 2.5,
        paddingtop: 20,
        paddingbottom: 20,
        paddingleft: 24,
        paddingright: 24,
        staffwidth: 500,
      });
      if (result && result.length > 0) visualObj = result[0];
    }

    // Number of notes actually rendered (ascending octave + descending).
    const totalNotes = noteSequence(intervals, startMidi).all.length;

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
          // Staff is written pitch; shift playback down so it sounds at concert.
          await synth.init({ audioContext, visualObj, options: { midiTranspose: -soundsBelow } });
          await synth.prime();
          currentSynth = synth;
          playBtn.disabled = false;
          playBtn.textContent = '■ Stop';
          playBtn.className = activeClass;
          synth.start();

          // Auto-reset when done: (n crotchets) at BPM, plus a short buffer
          const durationMs = totalNotes * (60000 / BPM) + 800;
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

    // Note name badges (ascending octave), with optional fingering diagrams.
    const useFlats = PREFER_FLAT.has(rootIndex);
    const names = useFlats ? NOTE_NAMES_FLAT : NOTE_NAMES_SHARP;
    const fingerings = window.scaleFingerings;
    const hasFingerings = !!(instrument && fingerings && fingerings.supports(instrument));

    const badgeRow = document.createElement('div');
    badgeRow.className = 'flex flex-wrap gap-1.5 items-start';

    // Each cell holds the note badge and (optionally) a fingering diagram below.
    function noteCell(name, midi, isRoot, isOctave) {
      const cell = document.createElement('div');
      cell.className = 'flex flex-col items-center gap-1';
      const badge = document.createElement('span');
      const pc = ((midi % 12) + 12) % 12;
      badge.className = 'px-2.5 py-1 rounded-full text-sm font-mono font-semibold ' +
        (isRoot
          ? 'bg-indigo-600 text-white'
          : isOctave
            ? 'bg-indigo-900/60 text-indigo-300'
            : BLACK_KEYS.has(pc)
              ? 'bg-gray-700 text-gray-200'
              : 'bg-gray-800 text-gray-100');
      badge.textContent = name;
      cell.appendChild(badge);
      cell._fingerSlot = document.createElement('div');
      cell._fingerSlot.className = 'min-h-0';
      cell._fingerSlot.dataset.midi = midi;
      cell.appendChild(cell._fingerSlot);
      return cell;
    }

    const cells = [];
    intervals.forEach((interval, idx) => {
      const midi = startMidi + interval;
      const cell = noteCell(names[(rootIndex + interval) % 12], midi, idx === 0, false);
      cells.push(cell);
      badgeRow.appendChild(cell);
    });
    const octaveCell = noteCell(names[rootIndex] + "'", startMidi + 12, false, true);
    cells.push(octaveCell);
    badgeRow.appendChild(octaveCell);

    // Fingering toggle — only when we have data for this instrument.
    if (hasFingerings) {
      let shown = false;
      const fingBtn = document.createElement('button');
      const fingIdle = 'px-3 py-1.5 rounded-lg text-xs font-semibold bg-gray-700 hover:bg-gray-600 text-gray-200 transition-colors';
      const fingActive = 'px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-700 hover:bg-indigo-600 text-white transition-colors';
      fingBtn.className = fingIdle;
      fingBtn.textContent = '☰ Fingerings';
      fingBtn.addEventListener('click', () => {
        shown = !shown;
        fingBtn.className = shown ? fingActive : fingIdle;
        cells.forEach((cell) => {
          const slot = cell._fingerSlot;
          slot.innerHTML = '';
          if (!shown) return;
          const midi = parseInt(slot.dataset.midi, 10);
          const diagram = fingerings.renderFingering(instrument, midi);
          if (diagram) {
            slot.appendChild(diagram);
          } else {
            const dash = document.createElement('span');
            dash.className = 'text-gray-600 text-xs';
            dash.textContent = '—';
            slot.appendChild(dash);
          }
        });
      });
      const fingRow = document.createElement('div');
      fingRow.className = 'mb-3';
      fingRow.appendChild(fingBtn);
      container.appendChild(fingRow);
    }

    container.appendChild(badgeRow);
  }

  window.renderScaleNotation = renderScaleNotation;
})();
