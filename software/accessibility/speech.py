"""Non-blocking text-to-speech feedback service."""

from __future__ import annotations

import logging
import queue
import threading
import multiprocessing
from dataclasses import dataclass
from typing import Callable, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SpeechMessage:
    text: str
    interrupt: bool = False
    generation: int = 0


class SpeakProcess(Protocol):
    """Minimal process interface SpeechService depends on (duck-typed)."""

    def start(self) -> None: ...
    def join(self, timeout: float | None = None) -> None: ...
    def is_alive(self) -> bool: ...
    def terminate(self) -> None: ...


def _speak_process(text: str) -> None:
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 175)
        # Tentar selecionar a voz pt-BR
        voices = engine.getProperty("voices")
        for voice in voices:
            haystack = f"{voice.id} {voice.name}".lower()
            if "portugu" in haystack or "brazil" in haystack or "brasil" in haystack:
                engine.setProperty("voice", voice.id)
                break

        engine.say(text)
        engine.runAndWait()
    except Exception:
        logger.exception("Falha ao falar '%s' via pyttsx3", text)


class _Generation:
    """Tracks the "latest valid" interruption generation.

    Every interrupt_and_say() bump()s the counter. A message stamped with an
    older generation is stale even if it was already dequeued by the worker
    before the interrupt arrived (closes the race that made interruption feel
    inconsistent: without this, a message that slipped past the queue clear
    but hadn't started its process yet would still play in full).
    """

    def __init__(self) -> None:
        self._value = 0
        self._lock = threading.Lock()

    def current(self) -> int:
        with self._lock:
            return self._value

    def bump(self) -> int:
        with self._lock:
            self._value += 1
            return self._value

    def is_stale(self, generation: int) -> bool:
        with self._lock:
            return generation < self._value


class SpeechService:
    """Small TTS queue prepared for offline pt-BR engines, supporting interruption."""

    def __init__(
        self,
        enabled: bool = True,
        process_factory: Callable[[str], SpeakProcess] | None = None,
    ) -> None:
        self.enabled = enabled
        self._process_factory = process_factory or (
            lambda text: multiprocessing.Process(target=_speak_process, args=(text,))
        )
        self._queue: queue.Queue[SpeechMessage | None] = queue.Queue()
        self._current_process: SpeakProcess | None = None
        self._process_lock = threading.Lock()
        self._generation = _Generation()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def say(self, text: str) -> None:
        if not text:
            return
        self._queue.put(SpeechMessage(text=text, generation=self._generation.current()))

    def interrupt_and_say(self, text: str) -> None:
        if not text:
            return
        generation = self._generation.bump()
        self._clear_queue()
        with self._process_lock:
            if self._current_process is not None and self._current_process.is_alive():
                self._current_process.terminate()
        self._queue.put(SpeechMessage(text=text, interrupt=True, generation=generation))

    def stop(self) -> None:
        with self._process_lock:
            if self._current_process is not None and self._current_process.is_alive():
                self._current_process.terminate()
        self._queue.put(None)

    def _clear_queue(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def _worker(self) -> None:
        logger.debug("Speech worker thread started")
        while True:
            message = self._queue.get()
            if message is None:
                logger.debug("Received stop signal")
                break

            if self._generation.is_stale(message.generation):
                logger.debug("Skipping stale message: '%s'", message.text)
                continue

            logger.debug("Processing message: '%s'", message.text)
            process = self._process_factory(message.text)
            with self._process_lock:
                self._current_process = process
            process.start()
            process.join()
            with self._process_lock:
                self._current_process = None
            logger.debug("Speech finished or terminated")
