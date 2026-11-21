"use strict";

// Port of PhonicsVoiceAttemptGate from the user's English Play A source.
// Signed PCM, 16 kHz, 20 ms frames, 60 ms onset, 300 ms trailing silence.
const PhonicsVoice = (() => {
  const pcmHz = 16000;
  const frameSize = 320;
  const thresholds = [4000, 2600, 1600, 1200, 900, 700, 500, 350, 160, 70];

  function isSingleTone(pcm) {
    const n = pcm.length;
    const mean = pcm.reduce((sum, value) => sum + value, 0) / n;
    const signal = Float64Array.from(pcm, value => value - mean);
    const energy = signal.reduce((sum, value) => sum + value * value, 0);
    if (energy === 0) return true;

    let peak = 1;
    let brightest = 0;
    for (let k = 1; k <= n / 2; k++) {
      const coefficient = 2 * Math.cos(2 * Math.PI * k / n);
      let prior = 0;
      let second = 0;
      for (const sample of signal) {
        const current = sample + coefficient * prior - second;
        second = prior;
        prior = current;
      }
      const power = prior * prior + second * second - coefficient * prior * second;
      if (power > brightest) {
        brightest = power;
        peak = k;
      }
    }
    for (let offset = -8; offset <= 8; offset++) {
      const bin = peak + offset / 8;
      if (bin <= 0 || bin > n / 2) continue;
      const step = 2 * Math.PI * bin / n;
      let cc = 0, ss = 0, cs = 0, cSum = 0, sSum = 0, xc = 0, xs = 0;
      for (let i = 0; i < n; i++) {
        const c = Math.cos(step * i), s = Math.sin(step * i);
        cc += c * c;
        ss += s * s;
        cs += c * s;
        cSum += c;
        sSum += s;
        xc += signal[i] * c;
        xs += signal[i] * s;
      }
      cc -= cSum * cSum / n;
      ss -= sSum * sSum / n;
      cs -= cSum * sSum / n;
      const determinant = cc * ss - cs * cs;
      const explained = determinant > 1e-6
        ? (ss * xc * xc - 2 * cs * xc * xs + cc * xs * xs) / determinant
        : xc * xc / cc;
      if (explained / energy >= .985) return true;
    }
    return false;
  }

  class Gate {
    constructor(level) {
      this.threshold = thresholds[level - 1];
      this.candidate = new Int16Array(960);
      this.count = 0;
      this.quiet = 0;
      this.talking = false;
    }
    feed(frame) {
      const sum = frame.reduce((total, sample) => total + sample * sample, 0);
      const rms = Math.sqrt(sum / frame.length);
      if (!this.talking) {
        if (rms < this.threshold) {
          this.count = 0;
          return "wait";
        }
        this.candidate.set(frame, this.count);
        this.count += frame.length;
        if (this.count < this.candidate.length) return "wait";
        this.count = 0;
        if (isSingleTone(this.candidate)) return "wait";
        this.talking = true;
        return "onset";
      }
      this.quiet = rms >= this.threshold * .6 ? 0 : this.quiet + frame.length;
      return this.quiet >= 4800 ? "end" : "wait";
    }
  }

  // Average the browser's capture samples into the 16 kHz bins used by the app.
  class SampleFrames {
    constructor(rate, callback) {
      this.ratio = rate / pcmHz;
      this.callback = callback;
      this.toFill = this.ratio;
      this.total = 0;
      this.offset = 0;
      this.frame = new Int16Array(frameSize);
    }
    feed(channel) {
      for (const value of channel) {
        let remainder = 1;
        while (remainder > 1e-8) {
          const count = Math.min(remainder, this.toFill);
          this.total += count * value;
          remainder -= count;
          this.toFill -= count;
          if (this.toFill > 1e-8) continue;
          this.frame[this.offset++] = Math.max(-32768,
            Math.min(32767, Math.round(32768 * this.total / this.ratio)));
          this.total = 0;
          this.toFill = this.ratio;
          if (this.offset === frameSize) {
            this.offset = 0;
            if (this.callback(this.frame) === false) return;
          }
        }
      }
    }
  }

  async function open(trackEnded) {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error("SECURE_BROWSER_REQUIRED");
    }
    const Context = window.AudioContext || window.webkitAudioContext;
    if (!Context) throw new Error("SECURE_BROWSER_REQUIRED");

    let context;
    try { context = new Context({ sampleRate: pcmHz }); }
    catch { context = new Context(); }
    let stream, source, capture, mute, accept;
    let enabled = false;
    const close = () => {
      enabled = false;
      accept = undefined;
      if (capture) capture.onaudioprocess = null;
      stream?.getTracks().forEach(track => track.stop());
      if (context.state !== "closed") void context.close().catch(() => {});
    };
    try {
      // Resume within the user's gesture, before the permission prompt resolves.
      const resumed = context.resume();
      void resumed.catch(() => {});
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: { ideal: 1 },
          sampleRate: { ideal: pcmHz },
          autoGainControl: false,
          noiseSuppression: false,
          echoCancellation: false,
        },
      });
      await resumed;
      const tracks = stream.getAudioTracks();
      tracks.forEach(track => {
        track.enabled = false;
        track.addEventListener("ended", trackEnded);
      });
      source = context.createMediaStreamSource(stream);
      // ScriptProcessor is supported on standalone file pages as well as HTTPS.
      // Audio is only read while paused for a turn. Nothing is recorded or uploaded.
      capture = context.createScriptProcessor(1024, 1, 1);
      mute = context.createGain();
      mute.gain.value = 0;
      source.connect(capture);
      capture.connect(mute);
      mute.connect(context.destination);
      capture.onaudioprocess = event => {
        if (enabled) accept(event.inputBuffer.getChannelData(0));
      };
      return {
        listen(level, report) {
          const gate = new Gate(level);
          const frames = new SampleFrames(context.sampleRate, pcm => {
            const result = gate.feed(pcm);
            if (result !== "wait") report(result);
            return enabled;
          });
          accept = input => frames.feed(input);
          enabled = true;
          tracks.forEach(track => { track.enabled = true; });
          void context.resume().catch(trackEnded);
        },
        stop() {
          enabled = false;
          accept = undefined;
          tracks.forEach(track => { track.enabled = false; });
        },
        close,
      };
    } catch (error) {
      close();
      throw error;
    }
  }
  return { Gate, SampleFrames, open };
})();
