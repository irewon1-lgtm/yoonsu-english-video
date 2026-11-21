const turns = episode.turns;

const element = id => document.getElementById(id);
const film = element("film");
const player = document.querySelector(".player");
const el = Object.fromEntries([
  "start", "progress", "status", "phrase", "play", "mic", "restart",
  "settings", "sensitivity", "level", "mic-note", "buffer", "buffer-text", "retry",
].map(id => [id, element(id)]));

let turn = 0;
let state = "ready";
let voice;
let micPending = false;
let automaticMicStarted = false;
let leaving = false;
let displayTimer;
let repeating = false;
let startupTimer;
let stallTimer;
let recoveryTimer;
let startupReady = false;
let loading = false;
let reconnectable = false;
let needsReload = false;
let automaticRetry = 0;
let mediaRequest = 0;
let lastPosition = 0;
const source = film.getAttribute("src");
function showControls() {
  clearTimeout(displayTimer);
  document.body.classList.remove("clean-view");
  if (state === "playing") {
    displayTimer = setTimeout(() => document.body.classList.add("clean-view"), 2300);
  }
}
film.addEventListener("click", showControls);
let micMessage = "";
let voiceState = "idle";
let armTimer;
let finishTimer;
let resumeAt;
let sensitivity = 8;
try {
  const saved = Number(localStorage.getItem("album-mic-sensitivity"));
  if (Number.isInteger(saved) && saved >= 1 && saved <= 10) sensitivity = saved;
} catch { /* Stored preferences may be unavailable in a file viewer. */ }

function setBuffer(message = "", retry = false) {
  loading = Boolean(message);
  reconnectable = retry;
  el.buffer.hidden = !loading;
  el["buffer-text"].textContent = message;
  el.retry.hidden = !retry;
  if (loading) showControls();
}

function bufferedAt(position) {
  for (let i = 0; i < film.buffered.length; i++) {
    if (film.buffered.start(i) <= position + .05 && position <= film.buffered.end(i)) {
      return film.buffered.end(i) - position;
    }
  }
  return 0;
}

function prepareStart() {
  // Fill the start of the video before showing Start. On systems that defer
  // preload to a user gesture the timer below reveals Start for that gesture.
  if (state === "ready" && !startupReady && bufferedAt(0) >= 5) {
    startupReady = true;
    clearTimeout(startupTimer);
    setBuffer();
    update();
  }
}

function clearStall() {
  clearTimeout(stallTimer);
  clearTimeout(recoveryTimer);
  stallTimer = undefined;
  recoveryTimer = undefined;
  if (loading || reconnectable) setBuffer();
}

function buffering() {
  if (state !== "playing" || stallTimer !== undefined || recoveryTimer !== undefined) return;
  stallTimer = setTimeout(() => {
    stallTimer = undefined;
    if (state !== "playing" || film.ended) return;
    if (film.readyState < HTMLMediaElement.HAVE_FUTURE_DATA || film.seeking) {
      setBuffer("영상을 불러오는 중이에요.", true);
      if (automaticRetry < 1) {
        recoveryTimer = setTimeout(() => {
          recoveryTimer = undefined;
          if (state === "playing" && !document.hidden &&
              (film.readyState < HTMLMediaElement.HAVE_FUTURE_DATA || film.seeking)) {
            reconnectOnce();
          }
        }, 4000);
      }
    }
  }, 1000);
}

const status = {
  ready: "윤수 차례 안내 뒤 문장을 한 번 더 듣고 따라 말해요.",
  playing: "문장을 한 번 더 듣고 윤수 차례를 기다려요.",
  paused: "영상이 잠시 멈췄어요.",
  done: "영어놀이를 마쳤어요!",
};
function update() {
  const waiting = state === "waiting";
  const modeling = state === "playing" && repeating;
  player.classList.toggle("waiting", waiting);
  player.classList.toggle("modeling", modeling);
  player.classList.toggle("playing", state === "playing");
  if (state !== "playing") showControls();
  el.start.hidden = state !== "ready" || !startupReady;
  el.start.textContent = needsReload ? "다시 재생" : "▶ 시작";
  el.play.hidden = state !== "playing" && state !== "paused";
  el.play.textContent = state === "paused" ? "재생" : "일시정지";
  el.restart.hidden = state === "ready" || waiting;
  el.phrase.hidden = !waiting && !modeling;
  el.phrase.textContent = waiting || modeling ? turns[turn][2] : "";
  if (waiting) {
    const prompt = !voice
      ? micPending ? "마이크 권한을 확인하고 있어요." : "마이크를 켜고 문장을 말해 봐요."
      : episode.hints?.[turn] || "아래 문장을 말해 봐요.";
    el.status.textContent = voiceState === "heard" || voiceState === "settling"
      ? "듣고 있어요…" : "윤수 차례 " + (turn + 1) + "/" + turns.length + " · " + prompt;
  } else {
    el.status.textContent = modeling ? "한 번 더 들어요." : status[state];
  }
  el.mic.disabled = micPending;
  el.mic.textContent = micPending ? "권한 확인 중…" : voice ? "마이크 끄기" : "마이크 켜기";
  el.mic.setAttribute("aria-pressed", String(Boolean(voice)));
  el.settings.hidden = !voice;
  el.sensitivity.value = sensitivity;
  el.level.textContent = sensitivity;
  el["mic-note"].hidden = !micMessage;
  el["mic-note"].textContent = micMessage;
}

function stopListening() {
  clearTimeout(armTimer);
  clearTimeout(finishTimer);
  voice?.stop();
  voiceState = "idle";
}

function armListening() {
  stopListening();
  update();
  if (!voice || state !== "waiting" || document.hidden) return;
  const activeTurn = turn;
  // Keep the final syllable of the repeated sentence out of the mic window.
  armTimer = setTimeout(() => {
    if (!voice || state !== "waiting" || activeTurn !== turn || document.hidden) return;
    voiceState = "listening";
    const onSpeech = result => {
      if (!voice || state !== "waiting" || turn !== activeTurn || document.hidden) return;
      if (result === "onset") {
        clearTimeout(finishTimer);
        voiceState = "heard";
        update();
      } else if (result === "end" && voiceState === "heard") {
        voiceState = "settling";
        finishTimer = setTimeout(() => {
          if (state === "waiting" && turn === activeTurn &&
              voiceState === "settling" && !document.hidden) advance();
        }, 1000);
        // Installed launchers end each native recording at the first pause.
        // Start the next capture immediately so further words cancel the timer.
        if (window.NativeMic) voice.listen(sensitivity, onSpeech);
        update();
      }
    };
    voice.listen(sensitivity, onSpeech);
    update();
  }, 150);
}

function pauseAtTurn() {
  state = "waiting";
  clearStall();
  film.pause();
  const [at] = turns[turn];
  if (film.currentTime - at > .06) film.currentTime = at;
  armListening();
}

function checkTime() {
  if (!film.seeking && film.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
    const at = film.currentTime;
    el.progress.value = at;
    if (state === "playing") lastPosition = at;
    if (state === "playing" && turn < turns.length && at >= turns[turn][0]) {
      repeating = false;
      pauseAtTurn();
    } else if (state === "playing") {
      const again = episode.repeatStarts?.[turn] !== undefined && at >= episode.repeatStarts[turn];
      if (again !== repeating) {
        repeating = again;
        update();
      }
    }
  }
}

async function play() {
  if (state === "waiting") return;
  const originalState = state;
  state = "playing";
  clearTimeout(startupTimer);
  clearStall();
  if (needsReload) {
    needsReload = false;
    film.src = source + "?reconnect=" + (++mediaRequest);
    film.load();
  }
  if (resumeAt !== undefined) {
    // A pre-metadata seek is retained by the browser as the playback start.
    film.currentTime = resumeAt;
    lastPosition = resumeAt;
    resumeAt = undefined;
  }
  update();
  showControls();
  buffering();
  try { await film.play(); }
  catch (error) {
    if (state !== "playing" || error.name === "AbortError") return;
    if (film.error) {
      handleMediaError();
      return;
    }
    clearStall();
    state = originalState === "ready" ? "ready" : "paused";
    update();
    el.status.textContent = "재생 버튼을 다시 눌러 주세요.";
  }
}

function reconnectOnce() {
  automaticRetry += 1;
  needsReload = true;
  resumeAt = lastPosition;
  void play();
}

function handleMediaError() {
  if (!film.error) return;
  clearStall();
  needsReload = true;
  if (state === "waiting" || state === "done" || leaving) return;
  if (state === "playing" && automaticRetry < 1) {
    reconnectOnce();
    return;
  }
  if (state === "playing") state = "paused";
  startupReady = true;
  clearTimeout(startupTimer);
  resumeAt = lastPosition;
  update();
  if (state !== "ready") setBuffer("연결이 끊겼어요. 멈춘 곳에서 이어 볼 수 있어요.", true);
}

function retryPlayback() {
  if (state !== "playing" && state !== "paused" && state !== "ready") return;
  automaticRetry = 0;
  needsReload = true;
  resumeAt = lastPosition;
  void play();
}

function advance() {
  if (state !== "waiting" || voiceState !== "settling" || !voice || document.hidden) return;
  const past = turns[turn][1];
  stopListening();
  repeating = false;
  turn += 1;
  state = "paused";
  // Resume at the end of this turn after the learner finishes speaking.
  resumeAt = past;
  void play();
}

film.addEventListener("timeupdate", checkTime);
film.addEventListener("progress", prepareStart);
film.addEventListener("loadeddata", prepareStart);
film.addEventListener("waiting", buffering);
film.addEventListener("stalled", buffering);
film.addEventListener("seeking", () => {
  if (state === "waiting") {
    const at = turns[turn][0];
    if (Math.abs(film.currentTime - at) > .001) film.currentTime = at;
  } else {
    buffering();
  }
});
film.addEventListener("play", () => {
  if (state !== "playing") film.pause();
});
film.addEventListener("playing", clearStall);
film.addEventListener("canplay", () => {
  prepareStart();
  if (state === "playing" && !film.seeking) clearStall();
});
if ("requestVideoFrameCallback" in film) {
  const watch = () => {
    checkTime();
    film.requestVideoFrameCallback(watch);
  };
  film.requestVideoFrameCallback(watch);
}
film.addEventListener("pause", () => {
  if (state === "playing" && !film.ended && film.paused && !film.error) {
    clearStall();
    state = "paused";
    update();
  }
});
film.addEventListener("ended", () => {
  if (state !== "playing") return;
  if (turn < turns.length) {
    repeating = false;
    pauseAtTurn();
    return;
  }
  clearStall();
  state = "done";
  stopListening();
  if (voice) {
    voice.close();
    voice = undefined;
  }
  update();
});
film.addEventListener("error", handleMediaError);
el.retry.addEventListener("click", retryPlayback);
el.start.addEventListener("click", () => {
  if (state !== "ready") return;
  prepareMicrophone();
  void play();
});
el.play.addEventListener("click", () => {
  if (state === "paused") void play();
  else if (state === "playing") {
    checkTime();
    if (state !== "playing") return;
    state = "paused";
    film.pause();
    update();
  }
});
el.restart.addEventListener("click", () => {
  if (state === "waiting") return;
  if (state === "done") void openMicrophone();
  automaticRetry = 0;
  stopListening();
  repeating = false;
  state = "paused";
  turn = 0;
  resumeAt = 0;
  void play();
});

// The Android launcher implements this fixed protocol. Ordinary browsers use Web Audio.
function nativeVoice(lost) {
  return new Promise((resolve, reject) => {
    let report;
    let ticket = 0;
    const changed = event => {
      const { type, token } = event.detail;
      if (type === "permission-granted") {
        resolve({
          listen(level, callback) {
            ticket += 1;
            report = callback;
            NativeMic.listen(level, ticket);
          },
          stop() { ticket += 1; report = undefined; NativeMic.stop(); },
          close() {
            ticket += 1;
            document.removeEventListener("native-mic", changed);
            report = undefined;
            NativeMic.stop();
          },
        });
      } else if (type === "permission-denied") {
        document.removeEventListener("native-mic", changed);
        reject(new Error("ANDROID_MIC_PERMISSION"));
      } else if (token === ticket && type === "capture-error") {
        lost();
      } else if (token === ticket && report) {
        report(type);
      }
    };
    document.addEventListener("native-mic", changed);
    NativeMic.authorize();
  });
}

function micLost() {
  stopListening();
  voice?.close();
  voice = undefined;
  micMessage = "마이크 연결이 끊겼어요. 마이크를 다시 켜 주세요.";
  update();
}
async function openMicrophone() {
  if (voice || micPending || leaving) return;
  micMessage = "";
  micPending = true;
  update();
  try {
    const opened = await (window.NativeMic ? nativeVoice(micLost) : PhonicsVoice.open(micLost));
    if (leaving) { opened.close(); return; }
    voice = opened;
    armListening();
  } catch (error) {
    micMessage = error.message === "SECURE_BROWSER_REQUIRED"
      ? "마이크를 지원하는 브라우저에서 보안 연결(HTTPS)로 열어 주세요."
      : error.message === "ANDROID_MIC_PERMISSION"
        ? "앱의 마이크 권한을 허용한 뒤 마이크를 다시 켜 주세요."
        : "마이크를 켤 수 없어요. 브라우저의 마이크 권한과 연결을 확인한 뒤 다시 켜 주세요.";
  } finally {
    micPending = false;
    update();
  }
}

function prepareMicrophone() {
  if (automaticMicStarted) return;
  automaticMicStarted = true;
  void openMicrophone();
}

el.mic.addEventListener("click", () => {
  automaticMicStarted = true;
  if (!voice) {
    void openMicrophone();
    return;
  }
  stopListening();
  voice.close();
  voice = undefined;
  update();
});
el.sensitivity.addEventListener("input", () => {
  sensitivity = Number(el.sensitivity.value);
  try { localStorage.setItem("album-mic-sensitivity", String(sensitivity)); } catch {}
  armListening();
});
document.addEventListener("visibilitychange", () => {
  if (document.hidden) stopListening();
  else if (state === "waiting") armListening();
});
window.addEventListener("pagehide", () => {
  leaving = true;
  clearTimeout(startupTimer);
  clearStall();
  stopListening();
  voice?.close();
  voice = undefined;
}, { capture: true });
window.addEventListener("pageshow", event => {
  leaving = false;
  if (event.persisted && window.NativeMic) {
    automaticMicStarted = false;
    prepareMicrophone();
  }
  update();
});
window.addEventListener("app-paused", () => {
  stopListening();
  if (state === "playing") {
    clearStall();
    state = "paused";
    film.pause();
  }
  update();
});
window.addEventListener("app-resumed", () => {
  if (state === "waiting") armListening();
});
setBuffer("영상을 준비하고 있어요.");
startupTimer = setTimeout(() => {
  if (state !== "ready") return;
  startupReady = true;
  setBuffer();
  update();
}, 5500);
prepareStart();
update();
if (window.NativeMic) prepareMicrophone();
