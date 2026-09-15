// Slaves a muted <video> element to the Web Audio playback clock.
// The picture never drives audio; transport.js / the audio engine remain master.

const DRIFT_THRESHOLD_SEC = 0.08;

/**
 * @param {HTMLVideoElement|null} videoEl
 */
export function createVideoSync(videoEl) {
  let engine = null;

  function load(jobId) {
    if (!videoEl || !jobId) return;
    videoEl.muted = true;
    videoEl.playsInline = true;
    videoEl.setAttribute("playsinline", "");
    videoEl.preload = "auto";
    videoEl.src = `/api/jobs/${jobId}/video-track.mp4`;
    videoEl.load();
  }

  function destroy() {
    if (!videoEl) return;
    videoEl.pause();
    videoEl.removeAttribute("src");
    videoEl.load();
    engine = null;
  }

  function attach(eng) {
    engine = eng;
  }

  function playbackRate(eng) {
    if (eng?.getPlaybackRate) return eng.getPlaybackRate();
    return 1;
  }

  function awaitingStart(eng) {
    if (!eng?.isPlaying?.()) return false;
    if (eng.isAwaitingStart) return eng.isAwaitingStart();
    return false;
  }

  /**
   * Called from the audio engine's onTime tick — no separate rAF loop.
   * @param {object} eng
   * @param {number} audioTime
   */
  function tick(eng, audioTime) {
    if (!videoEl || !eng || !videoEl.src) return;
    const rate = playbackRate(eng);
    if (Math.abs(videoEl.playbackRate - rate) > 1e-4) {
      videoEl.playbackRate = rate;
    }

    const playing = eng.isPlaying();
    const wait = awaitingStart(eng);

    if (!playing || wait) {
      if (!videoEl.paused) videoEl.pause();
      const target = Math.max(0, audioTime);
      if (Math.abs(videoEl.currentTime - target) > 0.05) {
        videoEl.currentTime = target;
      }
      return;
    }

    const vdur = videoEl.duration;
    if (Number.isFinite(vdur) && vdur > 0 && audioTime >= vdur) {
      if (!videoEl.paused) videoEl.pause();
      return;
    }

    if (Math.abs(videoEl.currentTime - audioTime) > DRIFT_THRESHOLD_SEC) {
      videoEl.currentTime = audioTime;
    }

    if (videoEl.paused) {
      videoEl.play().catch(() => {});
    }
  }

  function pauseAt(time) {
    if (!videoEl) return;
    videoEl.pause();
    if (Number.isFinite(time)) videoEl.currentTime = Math.max(0, time);
  }

  return { load, destroy, attach, tick, pauseAt };
}
