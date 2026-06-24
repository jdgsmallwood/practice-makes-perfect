/**
 * Alpine.js metronome store — Web Audio lookahead scheduler (Chris Wilson, 2013).
 *
 * Subdivisions (this.subdivision):
 *   1 = quarter notes only (default)
 *   2 = + eighth-note subdivisions
 *   4 = + sixteenth-note subdivisions
 *
 * Downbeats play at 880 Hz / full gain.
 * Subdivisions play at 550 Hz / half gain.
 * Only the downbeat drives the visual pulse dot.
 */
document.addEventListener('alpine:init', () => {
  Alpine.store('metro', {
    running: false,
    beat: false,
    bpm: 120,
    subdivision: 1,   // 1, 2, or 4

    _ctx: null,
    _next: 0.0,
    _subCount: 0,     // subdivision counter within the current beat
    _tid: null,

    _ensureCtx() {
      if (!this._ctx) {
        this._ctx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (this._ctx.state === 'suspended') this._ctx.resume();
    },

    _click(t, isDownbeat) {
      const osc = this._ctx.createOscillator();
      const gain = this._ctx.createGain();
      osc.connect(gain);
      gain.connect(this._ctx.destination);

      if (isDownbeat) {
        osc.frequency.value = 880;
        gain.gain.setValueAtTime(0.5, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.04);
        osc.start(t);
        osc.stop(t + 0.05);

        const delayMs = Math.max(0, (t - this._ctx.currentTime) * 1000);
        setTimeout(() => {
          this.beat = true;
          setTimeout(() => { this.beat = false; }, 80);
        }, delayMs);
      } else {
        // Subdivision click: softer and lower pitched
        osc.frequency.value = 550;
        gain.gain.setValueAtTime(0.18, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.025);
        osc.start(t);
        osc.stop(t + 0.03);
      }
    },

    _schedule() {
      const subdivInterval = (60.0 / this.bpm) / this.subdivision;
      while (this._next < this._ctx.currentTime + 0.1) {
        const isDownbeat = (this._subCount % this.subdivision) === 0;
        this._click(this._next, isDownbeat);
        this._next += subdivInterval;
        this._subCount++;
      }
    },

    start(bpm) {
      this._ensureCtx();
      this.bpm = bpm;
      this._next = this._ctx.currentTime + 0.05;
      this._subCount = 0;
      this.running = true;
      this._tid = setInterval(() => this._schedule(), 25);
    },

    stop() {
      clearInterval(this._tid);
      this._tid = null;
      this.running = false;
    },

    toggle(bpm) {
      this.running ? this.stop() : this.start(bpm);
    },

    setBpm(bpm) {
      this.bpm = bpm;
    },

    setSubdivision(n) {
      this.subdivision = n;
      // Reset sub-counter so the next downbeat aligns correctly
      this._subCount = 0;
    },
  });
});
