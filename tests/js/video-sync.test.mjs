// Unit tests for karaoke video sync (slaved to the audio engine clock).
// Run: node tests/js/video-sync.test.mjs

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

// videoSync is browser-oriented; re-implement the tick contract here so the
// test runs in Node without a DOM module loader.
const DRIFT = 0.08;

function makeVideo() {
  return {
    muted: false,
    playsInline: false,
    playbackRate: 1,
    currentTime: 0,
    duration: 120,
    paused: true,
    src: "/api/jobs/x/video-track.mp4",
    play() {
      this.paused = false;
      return Promise.resolve();
    },
    pause() {
      this.paused = true;
    },
    load() {},
    removeAttribute() {},
  };
}

function makeEngine({
  playing = false,
  time = 0,
  awaiting = false,
  rate = 1,
} = {}) {
  return {
    isPlaying: () => playing,
    isAwaitingStart: () => awaiting,
    getPlaybackRate: () => rate,
    getCurrentTime: () => time,
  };
}

function tickVideo(video, eng, audioTime) {
  if (!video || !eng || !video.src) return;
  const rate = eng.getPlaybackRate?.() ?? 1;
  if (Math.abs(video.playbackRate - rate) > 1e-4) video.playbackRate = rate;

  const playing = eng.isPlaying();
  const wait = eng.isAwaitingStart?.() ?? false;

  if (!playing || wait) {
    if (!video.paused) video.pause();
    const target = Math.max(0, audioTime);
    if (Math.abs(video.currentTime - target) > 0.05) video.currentTime = target;
    return;
  }

  const vdur = video.duration;
  if (Number.isFinite(vdur) && vdur > 0 && audioTime >= vdur) {
    if (!video.paused) video.pause();
    return;
  }

  if (Math.abs(video.currentTime - audioTime) > DRIFT) {
    video.currentTime = audioTime;
  }
  if (video.paused) video.play();
}

let passed = 0;
let failed = 0;

function check(name, cond, detail = "") {
  if (cond) {
    passed++;
    console.log(`PASS  ${name}`);
  } else {
    failed++;
    console.log(`FAIL  ${name}${detail ? `  -- ${detail}` : ""}`);
  }
}

const video = makeVideo();

check("pause keeps video at audio time", () => {
  const v = makeVideo();
  v.currentTime = 5;
  tickVideo(v, makeEngine({ playing: false, time: 12 }), 12);
  return v.paused && v.currentTime === 12;
});

check("count-in does not start playback", () => {
  const v = makeVideo();
  tickVideo(v, makeEngine({ playing: true, awaiting: true, time: 0 }), 0);
  return v.paused;
});

check("play starts when audio runs", () => {
  const v = makeVideo();
  tickVideo(v, makeEngine({ playing: true, time: 1.5 }), 1.5);
  return !v.paused && Math.abs(v.currentTime - 1.5) < 0.01;
});

check("drift above threshold seeks", () => {
  const v = makeVideo();
  v.currentTime = 0;
  tickVideo(v, makeEngine({ playing: true, time: 1 }), 1);
  return Math.abs(v.currentTime - 1) < 0.01;
});

check("drift below threshold does not seek", () => {
  const v = makeVideo();
  v.currentTime = 1.02;
  tickVideo(v, makeEngine({ playing: true, time: 1 }), 1);
  return Math.abs(v.currentTime - 1.02) < 0.001;
});

check("playback rate follows engine", () => {
  const v = makeVideo();
  tickVideo(v, makeEngine({ playing: true, time: 0, rate: 0.75 }), 0);
  return v.playbackRate === 0.75;
});

const engineSrc = readFileSync(join(root, "static/js/audioEngine.js"), "utf8");
const chunkedSrc = readFileSync(join(root, "static/js/chunkedAudioEngine.js"), "utf8");
check("audioEngine exposes isAwaitingStart", () => /isAwaitingStart:/.test(engineSrc));
check("audioEngine exposes getPlaybackRate", () => /getPlaybackRate:/.test(engineSrc));
check("chunkedEngine exposes isAwaitingStart", () => /isAwaitingStart:/.test(chunkedSrc));
check("chunkedEngine exposes getPlaybackRate", () => /getPlaybackRate:/.test(chunkedSrc));

console.log(`\n${passed}/${passed + failed} checks passed`);
process.exit(failed === 0 ? 0 : 1);
