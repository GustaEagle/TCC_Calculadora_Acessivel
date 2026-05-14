"""Non-blocking text-to-speech feedback service."""

from __future__ import annotations

import queue
import threading
import multiprocessing
from dataclasses import dataclass


@dataclass(frozen=True)
class SpeechMessage:
    text: str
    interrupt: bool = False


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
    except Exception as e:
        with open("speech_debug.log", "a", encoding="utf-8") as f:
            f.write(f"Error in pyttsx3 process: {e}\n")


class SpeechService:
    """Small TTS queue prepared for offline pt-BR engines, supporting interruption."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._queue: queue.Queue[SpeechMessage | None] = queue.Queue()
        self._current_process: multiprocessing.Process | None = None
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def say(self, text: str) -> None:
        if text:
            self._queue.put(SpeechMessage(text=text))

    def interrupt_and_say(self, text: str) -> None:
        if text:
            self._clear_queue()
            if self._current_process and self._current_process.is_alive():
                self._current_process.terminate()
            self._queue.put(SpeechMessage(text=text, interrupt=True))

    def stop(self) -> None:
        if self._current_process and self._current_process.is_alive():
            self._current_process.terminate()
        self._queue.put(None)

    def _clear_queue(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def _worker(self) -> None:
        with open("speech_debug.log", "a", encoding="utf-8") as logs:
            logs.write("Worker thread started with multiprocessing.\n")

            while True:
                message = self._queue.get()
                if message is None:
                    logs.write("Received stop signal\n")
                    break
                
                logs.write(f"Processing message: '{message.text}'\n")
                
                self._current_process = multiprocessing.Process(
                    target=_speak_process, 
                    args=(message.text,)
                )
                self._current_process.start()
                
                # Bloqueia a thread até o processo terminar ou ser interrompido
                self._current_process.join()
                self._current_process = None
                
                logs.write("speech finished or terminated\n")
                logs.flush()

