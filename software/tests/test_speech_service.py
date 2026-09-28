import os
import shutil
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock

from software.accessibility.speech import SpeechService, _SpeakProcess, _speak_process


class _FakeProcess:
    """Stands in for multiprocessing.Process: blocks in join() until terminated."""

    def __init__(self, text: str, on_start=None) -> None:
        self.text = text
        self.terminated = False
        self._done = threading.Event()
        self._on_start = on_start

    def start(self) -> None:
        if self._on_start:
            self._on_start()

    def join(self, timeout: float | None = None) -> None:
        self._done.wait(timeout)

    def is_alive(self) -> bool:
        return not self._done.is_set()

    def terminate(self) -> None:
        self.terminated = True
        self._done.set()


def _wait_until(predicate, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


class SpeechServiceInterruptionTest(unittest.TestCase):
    def _make_service(self):
        started = threading.Event()
        processes: list[_FakeProcess] = []

        def factory(text: str) -> _FakeProcess:
            started.clear()
            proc = _FakeProcess(text, on_start=started.set)
            processes.append(proc)
            return proc

        service = SpeechService(process_factory=factory)
        return service, processes, started

    def test_interrupt_terminates_currently_playing_message(self) -> None:
        service, processes, started = self._make_service()
        try:
            service.say("tecla pressionada")
            self.assertTrue(started.wait(timeout=1), "a primeira fala nunca começou")

            service.interrupt_and_say("resultado quatorze")

            self.assertTrue(_wait_until(lambda: processes[0].terminated))
            self.assertTrue(_wait_until(lambda: len(processes) >= 2))
            self.assertEqual(processes[1].text, "resultado quatorze")
        finally:
            service.stop()

    def test_pending_queued_messages_are_discarded_on_interrupt(self) -> None:
        service, processes, started = self._make_service()
        try:
            service.say("tecla 1")
            self.assertTrue(started.wait(timeout=1))

            # Enfileiradas enquanto "tecla 1" ainda está tocando; nenhuma delas
            # deve ser ouvida depois que um anúncio prioritário chegar.
            service.say("tecla 2")
            service.say("tecla 3")

            service.interrupt_and_say("resultado final")

            self.assertTrue(_wait_until(lambda: len(processes) >= 2))
            self.assertEqual(processes[1].text, "resultado final")
        finally:
            service.stop()

    def test_say_without_interrupt_plays_in_order(self) -> None:
        service, processes, started = self._make_service()
        try:
            service.say("primeiro")
            self.assertTrue(started.wait(timeout=1))
            processes[0].terminate()  # simula o fim natural da fala

            self.assertTrue(_wait_until(lambda: len(processes) >= 1))
            service.say("segundo")
            self.assertTrue(_wait_until(lambda: len(processes) >= 2))
            self.assertEqual(processes[1].text, "segundo")
        finally:
            service.stop()


class _EspeakLikeEngine:
    """pyttsx3 engine the way its espeak driver behaves: runAndWait() announces
    'started-utterance' and returns with the phrase still to play, and
    'finished-utterance' comes later, from espeak-ng's own thread. Like
    pyttsx3, say() drops blank text."""

    def __init__(self) -> None:
        self.playback_over = threading.Event()
        self._callbacks: dict[str, list] = {}
        self._text = ""

    def setProperty(self, name, value) -> None:
        pass

    def getProperty(self, name):
        return []

    def connect(self, topic, callback) -> None:
        self._callbacks.setdefault(topic, []).append(callback)

    def say(self, text) -> None:
        if text.strip():
            self._text = text

    def runAndWait(self) -> None:
        if not self._text:
            return
        self._notify("started-utterance")

        def play() -> None:
            self.playback_over.wait()
            self._notify("finished-utterance", completed=True)

        threading.Thread(target=play, daemon=True).start()

    def _notify(self, topic, **kwargs) -> None:
        for callback in self._callbacks.get(topic, []):
            callback(name=None, **kwargs)


class SpeakWaitsForPlaybackTest(unittest.TestCase):
    def _speak_in_background(self, text: str) -> tuple[threading.Thread, _EspeakLikeEngine]:
        engine = _EspeakLikeEngine()
        patcher = mock.patch.dict(sys.modules, {"pyttsx3": types.SimpleNamespace(init=lambda: engine)})
        patcher.start()
        self.addCleanup(patcher.stop)
        speaking = threading.Thread(target=_speak_process, args=(text,), daemon=True)
        speaking.start()
        return speaking, engine

    def test_returns_only_after_the_phrase_finishes_playing(self) -> None:
        speaking, engine = self._speak_in_background("resultado quatorze")

        speaking.join(timeout=0.3)
        # Voltar aqui deixaria o aplay órfão: a fila não esperaria o fim da
        # fala e a interrupção não acharia processo vivo para encerrar.
        self.assertTrue(speaking.is_alive(), "voltou com a fala ainda tocando")

        engine.playback_over.set()
        speaking.join(timeout=2)
        self.assertFalse(speaking.is_alive())

    def test_blank_text_does_not_wait_for_a_phrase_that_never_starts(self) -> None:
        speaking, _ = self._speak_in_background("   ")

        speaking.join(timeout=2)
        # Travar aqui prenderia o worker: nenhuma fala seguinte sairia.
        self.assertFalse(speaking.is_alive(), "travou esperando uma fala que nunca começou")


def _play_like_the_espeak_driver(report: str) -> None:
    """What the pyttsx3 espeak driver does per phrase: a temporary WAV played by
    `aplay` through os.system. Here `sleep` is the aplay; `exec` keeps the PID
    the shell wrote to `report`."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav:
        pass
    os.system(f"echo {wav.name} $$ > {report}.part && mv {report}.part {report} && exec sleep 30")
    os.remove(wav.name)


def _playing(pid: int) -> bool:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except FileNotFoundError:
        return False
    return stat.rsplit(")", 1)[1].split()[0] not in ("Z", "X")  # zumbi não toca mais


@unittest.skipUnless(sys.platform.startswith("linux"), "usa grupos de processos e /proc")
class SpeakProcessTerminateTest(unittest.TestCase):
    def _speak(self) -> tuple[_SpeakProcess, str, int]:
        scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, scratch, True)
        report = Path(scratch) / "report"
        process = _SpeakProcess(target=_play_like_the_espeak_driver, args=(str(report),))
        process.start()

        def stop() -> None:
            if process.is_alive():
                process.terminate()
            process.join(5)

        self.addCleanup(stop)
        self.assertTrue(_wait_until(report.exists, timeout=5), "o aplay nunca começou")
        wav, aplay = report.read_text().split()
        return process, wav, int(aplay)

    def test_terminate_silences_the_aplay_too(self) -> None:
        process, _, aplay = self._speak()

        process.terminate()
        process.join(timeout=5)

        self.assertFalse(process.is_alive())
        self.assertTrue(_wait_until(lambda: not _playing(aplay)), "o aplay seguiu tocando")

    def test_interrupted_phrase_leaves_no_wav_behind(self) -> None:
        process, wav, _ = self._speak()

        process.terminate()
        process.join(timeout=5)

        # O driver só apaga o WAV depois do aplay; interrompido, nunca chega lá.
        self.assertFalse(os.path.exists(wav))


class GenerationTest(unittest.TestCase):
    def test_bump_increments_and_marks_older_generations_stale(self) -> None:
        from software.accessibility.speech import _Generation

        generation = _Generation()
        self.assertEqual(generation.current(), 0)
        self.assertFalse(generation.is_stale(0))

        generation.bump()
        self.assertEqual(generation.current(), 1)
        self.assertTrue(generation.is_stale(0))
        self.assertFalse(generation.is_stale(1))


if __name__ == "__main__":
    unittest.main()
