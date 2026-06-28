"""
memory/voice.py — Optional voice clip recording and playback for multimodal memories.
Gracefully degrades if sounddevice is not installed.
"""

import os
import datetime
import threading
import wave
from typing import Optional

AUDIO_DIR = os.path.join("data", "memory", "audio")
SAMPLE_RATE = 16000
CHANNELS = 1


def _has_sounddevice() -> bool:
    try:
        import sounddevice  # noqa: F401
        return True
    except ImportError:
        return False


def _has_speech_recognition() -> bool:
    try:
        import speech_recognition  # noqa: F401
        return True
    except ImportError:
        return False


class VoiceHelper:
    def __init__(self):
        self._recording = False
        self._record_thread = None
        self._frames = []

    @property
    def can_record(self) -> bool:
        return _has_sounddevice()

    @property
    def can_listen(self) -> bool:
        return _has_speech_recognition()

    def start_recording(self):
        if not self.can_record or self._recording:
            return
        self._frames = []
        self._recording = True
        self._record_thread = threading.Thread(target=self._record_loop, daemon=True)
        self._record_thread.start()

    def _record_loop(self):
        import sounddevice as sd
        import numpy as np

        def callback(indata, frames, time_info, status):
            if self._recording:
                self._frames.append(indata.copy())

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            callback=callback,
        ):
            while self._recording:
                sd.sleep(100)

    def stop_recording(self) -> Optional[str]:
        if not self._recording:
            return None
        self._recording = False
        if self._record_thread:
            self._record_thread.join(timeout=2.0)

        if not self._frames:
            return None

        import numpy as np

        os.makedirs(AUDIO_DIR, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(AUDIO_DIR, f"clip_{ts}.wav")
        audio = np.concatenate(self._frames, axis=0)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
        return path

    def play_clip(self, path: str):
        if not path or not os.path.exists(path):
            return
        try:
            if _has_sounddevice():
                import sounddevice as sd
                import soundfile as sf
                data, sr = sf.read(path)
                sd.play(data, sr)
                sd.wait()
            else:
                import winsound
                winsound.PlaySound(path, winsound.SND_FILENAME)
        except Exception:
            pass

    def listen_for_name(self, timeout: float = 5.0) -> Optional[str]:
        """Offline-ish speech via Google fallback; returns None on failure."""
        if not self.can_listen:
            return None
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.3)
                audio = r.listen(source, timeout=timeout, phrase_time_limit=4)
            text = r.recognize_google(audio)
            return text.strip()
        except Exception:
            return None
