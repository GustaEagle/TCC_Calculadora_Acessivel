"""Non-blocking text-to-speech feedback service."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class SpeechMessage:
    text: str
    interrupt: bool = False


class SpeechService:
    """Small TTS queue prepared for offline pt-BR engines."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._queue: queue.Queue[SpeechMessage | None] = queue.Queue()
        self._engine = self._create_engine() if enabled else None
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def say(self, text: str) -> None:
        if text:
            self._queue.put(SpeechMessage(text=text))

    def interrupt_and_say(self, text: str) -> None:
        if text:
            self._queue.put(SpeechMessage(text=text, interrupt=True))

    def stop(self) -> None:
        self._queue.put(None)

    def _create_engine(self) -> object | None:
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", 175)
            self._select_portuguese_voice(engine)
            return engine
        except Exception:
            return None

    def _select_portuguese_voice(self, engine: object) -> None:
        try:
            voices = engine.getProperty("voices")
            for voice in voices:
                haystack = f"{voice.id} {voice.name}".lower()
                if "portugu" in haystack or "brazil" in haystack or "brasil" in haystack:
                    engine.setProperty("voice", voice.id)
                    return
        except Exception:
            return

    def _worker(self) -> None:
        while True:
            message = self._queue.get()
            if message is None:
                return
            if self._engine is None:
                print(f"[TTS] {message.text}")
                continue
            try:
                if message.interrupt:
                    self._engine.stop()
                    self._drain_queue()
                self._engine.say(message.text)
                self._engine.runAndWait()
            except Exception:
                print(f"[TTS] {message.text}")

    def _drain_queue(self) -> None:
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                return
            if item is None:
                self._queue.put(None)
                return
