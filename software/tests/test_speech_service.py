import os
import stat
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from software.accessibility import speech
from software.accessibility.speech import (
    PiperEngine,
    SpeechService,
    _RawPlaybackProcess,
    default_fixed_phrases,
)


class _FakeProcess:
    """Stands in for a playback handle: blocks in join() until terminated."""

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


class _FakeEngine:
    """Resident engine stand-in: no Piper, no audio, records synthesize() calls."""

    def __init__(self, *, ready: bool = True, failed: bool = False, sample_rate: int = 22050) -> None:
        self._ready = ready
        self.failed = failed
        self.sample_rate = sample_rate
        self.calls: list[str] = []
        self._settled = threading.Event()
        if ready or failed:
            self._settled.set()

    @property
    def is_ready(self) -> bool:
        return self._ready

    def load_async(self) -> None:
        self._settled.set()

    def wait_ready(self, timeout: float | None = None) -> bool:
        self._settled.wait(timeout)
        return self._ready

    def synthesize(self, text: str) -> bytes:
        self.calls.append(text)
        return f"PCM:{text}".encode()


def _wait_until(predicate, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


class SpeechServiceInterruptionTest(unittest.TestCase):
    """RF-08: the queue/generation/interruption contract, engine-agnostic."""

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


class CacheAndSynthesisTest(unittest.TestCase):
    """D4: frases fixas saem do cache; resultados dinâmicos são sintetizados."""

    def _service(self, engine, **kw):
        service = SpeechService(engine=engine, warm_cache=False, **kw)
        self.addCleanup(service.stop)
        return service

    def test_cached_phrase_is_not_resynthesized(self) -> None:
        engine = _FakeEngine(ready=True)
        service = self._service(engine)
        service._cache["seno"] = b"CACHED"

        pcm, rate = service._produce("seno")

        self.assertEqual(pcm, b"CACHED")
        self.assertEqual(rate, service._cache_rate)
        self.assertEqual(engine.calls, [], "uma frase em cache não deve chamar a síntese")

    def test_dynamic_result_is_synthesized(self) -> None:
        engine = _FakeEngine(ready=True)
        service = self._service(engine)

        pcm, rate = service._produce("Resultado 14")

        self.assertEqual(pcm, b"PCM:Resultado 14")
        self.assertEqual(rate, engine.sample_rate)
        self.assertEqual(engine.calls, ["Resultado 14"])

    def test_cache_warm_prefills_fixed_phrases(self) -> None:
        engine = _FakeEngine(ready=True)
        service = SpeechService(engine=engine, fixed_phrases=["seno", "cosseno"])
        self.addCleanup(service.stop)

        self.assertTrue(_wait_until(lambda: "seno" in service._cache and "cosseno" in service._cache))
        self.assertCountEqual(engine.calls, ["seno", "cosseno"])

        engine.calls.clear()
        pcm, _ = service._produce("seno")
        self.assertEqual(pcm, b"PCM:seno")
        self.assertEqual(engine.calls, [], "após aquecido, a frase fixa não é re-sintetizada")


class FallbackTest(unittest.TestCase):
    """D6: sem Piper, cai para espeak-ng, loga WRN-011 uma vez, e não trava."""

    def test_missing_engine_falls_back_and_logs_wrn011_once(self) -> None:
        engine = _FakeEngine(ready=False, failed=True)
        service = SpeechService(engine=engine, warm_cache=False)
        self.addCleanup(service.stop)

        with mock.patch.object(speech, "_espeak_pcm", return_value=(b"ESPEAK", 22050)) as espeak:
            with self.assertLogs(speech.logger, level="WARNING") as logs:
                first = service._produce("Calculadora pronta")
                second = service._produce("Erro 001. Divisão por zero.")

        self.assertEqual(first, (b"ESPEAK", 22050))
        self.assertEqual(second, (b"ESPEAK", 22050))
        self.assertEqual(espeak.call_count, 2, "toda frase degradada usa o fallback")
        wrn = [line for line in logs.output if "WRN-011" in line]
        self.assertEqual(len(wrn), 1, "WRN-011 é logado uma única vez")

    def test_queue_keeps_working_under_fallback(self) -> None:
        engine = _FakeEngine(ready=False, failed=True)
        played: list[str] = []
        service = SpeechService(engine=engine, warm_cache=False)
        self.addCleanup(service.stop)

        with mock.patch.object(speech, "_espeak_pcm", side_effect=lambda t: (played.append(t) or (b"", 22050))):
            service.say("uma")
            service.say("duas")
            self.assertTrue(_wait_until(lambda: played == ["uma", "duas"]))


def _write_fake_aplay(path: Path, body: str) -> None:
    path.write_text("#!/usr/bin/env python3\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


@unittest.skipUnless(sys.platform.startswith("linux"), "usa grupos de processos e /proc")
class RawPlaybackProcessTest(unittest.TestCase):
    """3.2: player raw via aplay pela stdin; terminate() mata o aplay."""

    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self._tmp, ignore_errors=True))
        self._aplay = Path(self._tmp) / "aplay"
        patcher = mock.patch.object(speech, "_APLAY", str(self._aplay))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_command_format_and_pcm_reach_aplay(self) -> None:
        report = Path(self._tmp) / "report"
        _write_fake_aplay(
            self._aplay,
            "import sys\n"
            f"data = sys.stdin.buffer.read()\n"
            f"open({str(report)!r}, 'wb').write(('|'.join(sys.argv[1:]) + '\\n').encode() + data)\n",
        )
        handle = _RawPlaybackProcess(lambda: (b"\x01\x02\x03\x04", 22050))
        handle.start()
        handle.join(timeout=5)

        self.assertTrue(report.exists(), "o aplay não recebeu a frase")
        head, _, data = report.read_bytes().partition(b"\n")
        self.assertEqual(
            head.decode().split("|"),
            ["-q", "-t", "raw", "-f", "S16_LE", "-c", "1", "-r", "22050", "-"],
        )
        self.assertEqual(data, b"\x01\x02\x03\x04")

    def test_terminate_kills_the_aplay(self) -> None:
        pidfile = Path(self._tmp) / "pid"
        _write_fake_aplay(
            self._aplay,
            "import os, time\n"
            f"open({str(pidfile)!r}, 'w').write(str(os.getpid()))\n"
            "time.sleep(30)\n",
        )
        handle = _RawPlaybackProcess(lambda: (b"\x00" * 16, 22050))
        handle.start()
        self.assertTrue(_wait_until(pidfile.exists, timeout=5), "o aplay nunca começou")
        pid = int(pidfile.read_text())

        handle.terminate()
        handle.join(timeout=5)

        self.assertFalse(handle.is_alive())
        self.assertTrue(_wait_until(lambda: not _alive(pid)), "o aplay seguiu tocando")


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


class DefaultFixedPhrasesTest(unittest.TestCase):
    def test_covers_key_names_digits_and_errors(self) -> None:
        phrases = default_fixed_phrases()
        self.assertIn("seno", phrases)                 # nome de tecla (SPOKEN_TOKEN_NAMES)
        self.assertIn("7", phrases)                    # dígito
        self.assertIn("Calculadora pronta", phrases)   # anúncio fixo
        self.assertTrue(any(p.startswith("Erro 001.") for p in phrases))  # §13
        self.assertEqual(len(phrases), len(set(phrases)), "sem duplicatas")


class PiperEngineImportTest(unittest.TestCase):
    def test_engine_without_voice_reports_failed_not_ready(self) -> None:
        engine = PiperEngine(voice_path="/caminho/que/nao/existe.onnx")
        engine.load_async()
        self.assertTrue(engine.wait_ready(timeout=5) is False)
        self.assertTrue(engine.failed)
        self.assertFalse(engine.is_ready)


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
