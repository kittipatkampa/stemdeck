// Karaoke video pane: load/destroy and sync to the audio engine clock.
// Lives in its own module so transport.js can tick video on pause/seek without
// importing player.js (which already imports transport.js).

import { createVideoSync } from "./videoSync.js";
import { audioEngine } from "./state.js";

const videoPane = document.getElementById("dawVideoPane");
const videoFrame = document.getElementById("dawVideoFrame");
const videoResize = document.getElementById("dawVideoResize");
const videoSync = createVideoSync(document.getElementById("dawVideo"));

const FRAME_H_KEY = "stemdeck.video.frameHeight";
const FRAME_H_DEFAULT = 220;
const FRAME_H_MIN = 100;
const FRAME_H_MAX = 480;

let hasVideo = false;

function applyVideoFrameHeight(px) {
  if (!videoFrame) return;
  const h = Math.max(FRAME_H_MIN, Math.min(FRAME_H_MAX, px));
  videoFrame.style.setProperty("--video-frame-h", `${h}px`);
  document.documentElement.style.setProperty("--video-frame-h", `${h}px`);
}

function loadVideoFrameHeight() {
  try {
    const saved = Number(localStorage.getItem(FRAME_H_KEY));
    if (Number.isFinite(saved) && saved >= FRAME_H_MIN) {
      applyVideoFrameHeight(saved);
      return;
    }
  } catch (e) {
    console.warn("[video] could not read stored frame height:", e);
  }
  applyVideoFrameHeight(FRAME_H_DEFAULT);
}

function persistVideoFrameHeight() {
  if (!videoFrame) return;
  try {
    localStorage.setItem(FRAME_H_KEY, String(Math.round(videoFrame.getBoundingClientRect().height)));
  } catch (e) {
    console.warn("[video] could not persist frame height:", e);
  }
}

function wireVideoResize() {
  if (!videoResize || !videoFrame) return;
  videoResize.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    const startY = e.clientY;
    const startH = videoFrame.getBoundingClientRect().height;
    videoResize.setPointerCapture(e.pointerId);
    document.body.classList.add("video-resize-active");

    const onMove = (ev) => {
      applyVideoFrameHeight(startH + (ev.clientY - startY));
    };
    const onUp = (ev) => {
      videoResize.releasePointerCapture(ev.pointerId);
      videoResize.removeEventListener("pointermove", onMove);
      videoResize.removeEventListener("pointerup", onUp);
      videoResize.removeEventListener("pointercancel", onUp);
      document.body.classList.remove("video-resize-active");
      persistVideoFrameHeight();
    };
    videoResize.addEventListener("pointermove", onMove);
    videoResize.addEventListener("pointerup", onUp);
    videoResize.addEventListener("pointercancel", onUp);
  });
}

loadVideoFrameHeight();
wireVideoResize();

export function setVideoTrackUi(active, videoStatus, jobId) {
  hasVideo = !!active;
  const toggle = document.getElementById("panelVideoToggle");
  const sep = document.querySelector(".daw-panel-video-sep");
  const status = document.getElementById("dawVideoStatus");
  const app = document.querySelector(".app");

  app?.classList.toggle("has-video-track", hasVideo);

  if (hasVideo) {
    videoPane?.classList.remove("hidden");
    videoPane?.removeAttribute("aria-hidden");
    toggle?.classList.remove("hidden");
    sep?.classList.remove("hidden");
    status?.classList.toggle("hidden", videoStatus !== "failed");
    if (videoStatus !== "failed" && jobId) videoSync.load(jobId);
  } else {
    videoSync.destroy();
    videoPane?.classList.add("hidden");
    videoPane?.setAttribute("aria-hidden", "true");
    toggle?.classList.add("hidden");
    sep?.classList.add("hidden");
    status?.classList.add("hidden");
  }
}

export function tickVideoPlayback() {
  if (!hasVideo || !audioEngine) return;
  videoSync.attach(audioEngine);
  videoSync.tick(audioEngine, audioEngine.getCurrentTime());
}

export function pauseVideoPlayback(time) {
  if (!hasVideo) return;
  videoSync.pauseAt(time ?? audioEngine?.getCurrentTime?.() ?? 0);
}

export function tickVideoAt(eng, t) {
  if (!hasVideo || !eng) return;
  videoSync.attach(eng);
  videoSync.tick(eng, t);
}

document.getElementById("dawVideoFullscreen")?.addEventListener("click", () => {
  if (!videoPane) return;
  if (document.fullscreenElement) document.exitFullscreen?.();
  else videoPane.requestFullscreen?.();
});
