function droneComponent(hz) {
  return {
    hz: hz,
    running: false,
    _ctx: null,
    _osc: null,
    _gain: null,

    _ensure() {
      if (!this._ctx) {
        this._ctx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (this._ctx.state === 'suspended') {
        this._ctx.resume();
      }
    },

    start() {
      this._ensure();
      this._osc = this._ctx.createOscillator();
      this._gain = this._ctx.createGain();
      this._osc.type = 'sine';
      this._osc.frequency.setValueAtTime(this.hz, this._ctx.currentTime);
      this._gain.gain.setValueAtTime(0, this._ctx.currentTime);
      this._gain.gain.linearRampToValueAtTime(0.35, this._ctx.currentTime + 0.05);
      this._osc.connect(this._gain);
      this._gain.connect(this._ctx.destination);
      this._osc.start();
      this.running = true;
    },

    stop() {
      if (this._gain) {
        this._gain.gain.setValueAtTime(this._gain.gain.value, this._ctx.currentTime);
        this._gain.gain.linearRampToValueAtTime(0, this._ctx.currentTime + 0.05);
      }
      const osc = this._osc;
      this._osc = null;
      this._gain = null;
      this.running = false;
      setTimeout(() => { try { osc.stop(); } catch(e) {} }, 60);
    },

    toggle() {
      this.running ? this.stop() : this.start();
    },
  };
}
