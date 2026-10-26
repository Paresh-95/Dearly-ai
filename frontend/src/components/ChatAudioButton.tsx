import { useEffect, useRef, useState } from "react";

// Browser playbackRate does naive time-stretching, not pitch-preserving
// resampling — anything above ~1.05-1.1x noticeably distorts sibilants
// ("s"/"sh" sounds smear into a lisp-like slur). Keep at 1 for clarity.
const PLAYBACK_RATE = 1;

// Module-level (shared across every mounted ChatAudioButton) so starting
// one playback — by click or autoplay — pauses whatever else was playing,
// instead of multiple replies overlapping.
let currentlyPlaying: HTMLAudioElement | null = null;

export default function ChatAudioButton({ src, autoPlay }: { src: string; autoPlay?: boolean }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.playbackRate = PLAYBACK_RATE;
    const onPlay = () => {
      if (currentlyPlaying && currentlyPlaying !== audio) currentlyPlaying.pause();
      currentlyPlaying = audio;
      setPlaying(true);
    };
    const onPauseOrEnd = () => {
      if (currentlyPlaying === audio) currentlyPlaying = null;
      setPlaying(false);
    };
    const onLoadedMetadata = () => {
      audio.playbackRate = PLAYBACK_RATE;
    };
    audio.addEventListener("play", onPlay);
    audio.addEventListener("pause", onPauseOrEnd);
    audio.addEventListener("ended", onPauseOrEnd);
    audio.addEventListener("loadedmetadata", onLoadedMetadata);
    return () => {
      audio.removeEventListener("play", onPlay);
      audio.removeEventListener("pause", onPauseOrEnd);
      audio.removeEventListener("ended", onPauseOrEnd);
      audio.removeEventListener("loadedmetadata", onLoadedMetadata);
      if (currentlyPlaying === audio) currentlyPlaying = null;
    };
  }, []);

  function toggle() {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) audio.play();
    else audio.pause();
  }

  return (
    <button
      type="button"
      className="chat-audio-btn"
      onClick={toggle}
      aria-label={playing ? "Pause voice reply" : "Play voice reply"}
    >
      <audio ref={audioRef} src={src} autoPlay={autoPlay} crossOrigin="use-credentials" />
      {playing ? <PauseIcon /> : <PlayIcon />}
    </button>
  );
}

function PlayIcon() {
  return (
    <svg viewBox="0 0 16 16" width="12" height="12" fill="currentColor">
      <path d="M3.5 2.5a.5.5 0 0 1 .77-.42l8.5 5.5a.5.5 0 0 1 0 .84l-8.5 5.5a.5.5 0 0 1-.77-.42v-11Z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg viewBox="0 0 16 16" width="12" height="12" fill="currentColor">
      <rect x="3" y="2.5" width="3.3" height="11" rx="0.8" />
      <rect x="9.7" y="2.5" width="3.3" height="11" rx="0.8" />
    </svg>
  );
}
