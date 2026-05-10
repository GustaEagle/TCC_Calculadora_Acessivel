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
        # Initialize COM on Windows to ensure SAPI works correctly in this thread
        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            
            # Use native Windows SAPI voice directly for maximum stability
            voice = win32com.client.Dispatch("SAPI.SpVoice")
            # Select first Portuguese voice if available
            try:
                voices = voice.GetVoices()
                for i in range(voices.Count):
                    v = voices.Item(i)
                    if "portuguese" in v.GetDescription().lower() or "brasil" in v.GetDescription().lower():
                        voice.Voice = v
                        break
            except Exception:
                pass
                
        except (ImportError, Exception) as e:
            voice = None
            print(f"[TTS] Native SAPI fallback error: {e}")

        with open("C:/Users/Administrator/TCC_Calculadora_Acessivel/speech_debug.log", "a", encoding="utf-8") as logs:
            logs.write(f"Native Worker started. SAPI Voice ready={voice is not None}\n")

            while True:
                message = self._queue.get()
                if message is None:
                    logs.write("Received stop signal\n")
                    break
                
                logs.write(f"Processing message: '{message.text}'\n")
                if voice is None:
                    print(f"[TTS] {message.text}")
                    continue
                
                try:
                    logs.write(f"Calling voice.Speak('{message.text}')\n")
                    # SAPI5 Speak flags: 1 = Async, 0 = Sync. We use Sync in this thread.
                    voice.Speak(message.text)
                    logs.write("speech finished\n")
                except Exception as e:
                    logs.write(f"ERROR in native worker during '{message.text}': {e}\n")
                    print(f"[TTS] ERROR: {e}")
                
                logs.flush()
        
        # Cleanup
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass

    def _drain_queue(self) -> None:
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                return
            if item is None:
                self._queue.put(None)
                return
