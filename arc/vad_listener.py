# arc/vad_listener.py
import threading, time
import numpy as np
import sounddevice as sd

class VADListener:
    """
    Lightweight RMS-based speech detector.
    Calls on_speech() when it sees sustained voice while enabled and not muted.
    """
    def __init__(self,
                 sample_rate=16000,
                 channels=1,
                 rms_thresh=0.012,       # 1.2% FS; tune to taste
                 arm_after_ms=200,        # how long of speech to consider 'real'
                 cooldown_ms=800):        # suppress re-triggers for a bit
        self.sample_rate = sample_rate
        self.channels = channels
        self.rms_thresh = rms_thresh
        self.arm_samples = int(sample_rate * (arm_after_ms/1000.0))
        self.cooldown = cooldown_ms/1000.0

        self._muted = False
        self._enabled = False
        self._armed = False
        self._last_fire = 0.0
        self._speech_samples = 0
        self._lock = threading.Lock()
        self._stop_evt = threading.Event()
        self._thread = None
        self._on_speech = None

    def set_muted(self, muted: bool):
        with self._lock:
            self._muted = muted

    def set_enabled(self, enabled: bool):
        with self._lock:
            self._enabled = enabled
            # reset counters on state flip
            self._speech_samples = 0
            self._armed = False

    def start(self, on_speech):
        """Begin input stream and background thread."""
        self._on_speech = on_speech
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_evt.set()
        if self._thread:
            self._thread.join(timeout=1.5)
            self._thread = None

    def _run(self):
        def callback(indata, frames, time_info, status):
            # cheap RMS per callback
            rms = float(np.sqrt(np.mean(np.square(indata), dtype=np.float64)))
            now = time.time()

            with self._lock:
                if self._stop_evt.is_set():
                    raise sd.CallbackStop
                if not self._enabled or self._muted:
                    self._speech_samples = 0
                    return
                if (now - self._last_fire) < self.cooldown:
                    # cooling down after a fire
                    return

                if rms >= self.rms_thresh:
                    self._speech_samples += frames
                    if self._speech_samples >= self.arm_samples and not self._armed:
                        self._armed = True
                        # fire outside lock
                        threading.Thread(target=self._fire, daemon=True).start()
                else:
                    self._speech_samples = 0

        try:
            with sd.InputStream(samplerate=self.sample_rate,
                                channels=self.channels,
                                callback=callback):
                while not self._stop_evt.is_set():
                    time.sleep(0.05)
        except sd.CallbackStop:
            pass

    def _fire(self):
        with self._lock:
            self._last_fire = time.time()
            self._armed = False
            cb = self._on_speech
        if cb:
            cb()

