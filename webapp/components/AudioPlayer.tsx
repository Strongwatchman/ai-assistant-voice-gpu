// webapp/components/AudioPlayer.tsx
'use client';

import React, {
  useEffect,
  useRef,
  forwardRef,
  useImperativeHandle,
} from 'react';
import { apiTTS } from '../lib/api';

export type AudioPlayerHandle = {
  stop: () => void;
};

type Props = {
  /** Assistant reply to speak; when empty/unchanged nothing plays */
  text: string | null;
  /** Voice id/name passed along to backend; browser TTS tries to match by name */
  voice?: string;
  /** Fired when playback actually starts (TTS or speechSynthesis) */
  onStart?: () => void;
  /** Fired when playback fully ends/stops */
  onEnd?: () => void;
};

/**
 * AudioPlayer
 * - Prefers backend /tts (binary audio) then falls back to Web Speech API.
 * - Triggers only when [text, voice] change.
 * - De-dupes identical consecutive text so it doesn’t replay on re-renders.
 * - Exposes stop() to immediately halt playback (used by Interrupt).
 */
const AudioPlayer = forwardRef<AudioPlayerHandle, Props>(function AudioPlayer(
  { text, voice, onStart, onEnd },
  ref
) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const currentUrlRef = useRef<string | null>(null);
  const lastTextRef = useRef<string | null>(null);
  const playingRef = useRef(false);

  // Keep latest callbacks without retriggering effect
  const cbStartRef = useRef(onStart);
  const cbEndRef = useRef(onEnd);
  useEffect(() => { cbStartRef.current = onStart; }, [onStart]);
  useEffect(() => { cbEndRef.current = onEnd; }, [onEnd]);

  function safeStart() {
    playingRef.current = true;
    try { cbStartRef.current?.(); } catch {}
  }
  function safeEnd() {
    playingRef.current = false;
    try { cbEndRef.current?.(); } catch {}
  }

  function stopAll() {
    // Stop tag audio
    try {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
    } catch {}
    // Stop browser speech synthesis
    try { window.speechSynthesis?.cancel(); } catch {}
    playingRef.current = false;
    // No cb here—stop() is an imperative action, page decides if/when to mark UI
  }

  useImperativeHandle(ref, () => ({ stop: stopAll }), []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopAll();
      if (currentUrlRef.current) {
        URL.revokeObjectURL(currentUrlRef.current);
        currentUrlRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    (async () => {
      const t = (text || '').trim();
      if (!t) return;

      // De-dupe: don’t replay the exact same text back-to-back.
      if (lastTextRef.current && lastTextRef.current === t) return;
      lastTextRef.current = t;

      // Stop anything still playing
      stopAll();

      // Try server TTS first
      try {
        const url = await apiTTS(t, { voice, format: 'mp3' });
        // Revoke previous object URL
        if (currentUrlRef.current) URL.revokeObjectURL(currentUrlRef.current);
        currentUrlRef.current = url;

        // Lazily create audio element
        if (!audioRef.current) {
          const el = new Audio();
          el.preload = 'auto';

          el.addEventListener('playing', () => {
            safeStart();
          });

          el.addEventListener('ended', () => {
            safeEnd();
          });

          el.addEventListener('pause', () => {
            // If paused before reaching end, consider it "ended" from the UI perspective
            if (playingRef.current) safeEnd();
          });

          audioRef.current = el;
        }

        audioRef.current.src = url;
        await audioRef.current.play();
        return; // Success via backend; we’re done.
      } catch {
        // Fall through to browser speech synthesis
      }

      // Fallback: Web Speech API
      try {
        // Cancel any previous utterances
        window.speechSynthesis?.cancel();

        const u = new SpeechSynthesisUtterance(t);
        // If the chosen voice name matches a browser voice, use it
        if (voice) {
          const voices = window.speechSynthesis?.getVoices?.() || [];
          const match = voices.find(
            (v) => (v.name || '').toLowerCase() === voice.toLowerCase()
          );
          if (match) u.voice = match;
        }
        u.rate = 1.0;
        u.onstart = () => safeStart();
        u.onend = () => safeEnd();

        window.speechSynthesis.speak(u);
      } catch {
        // Give up silently; don’t crash UI.
      }
    })();
  }, [text, voice]); // only react to these, not to new callback identities

  return null; // no visible UI
});

export default AudioPlayer;

