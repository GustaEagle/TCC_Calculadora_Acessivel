"""Silêncio inicial e reprodução em pedaços (spec speech-engine, T01/T04).

O aplay é substituído por um script Python que regista o que recebe, como em
test_speech_service.py; o motor de voz é falso. Nada aqui toca som.
"""

from __future__ import annotations

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
    LEADING_SILENCE_MS,
    SpeechService,
    _RawPlaybackProcess,
    _silence,
    _trim_trailing_silence,
)

RATE = 22050


def _wait_until(predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def _tone(marker: int, samples: int = 64) -> bytes:
    """PCM não nulo e reconhecível: `samples` amostras de valor `marker`."""
    return int(marker).to_bytes(2, "little", signed=True) * samples


class FakeEngine:
    """Motor falso: devolve um tom por frase; `block` segura uma frase."""

    is_ready = True
    failed = False
    sample_rate = RATE

    def __init__(self, tones: dict[str, int], block: str | None = None) -> None:
        self.tones = tones
        self.block = block
        self.release = threading.Event()
        self.calls: list[str] = []

    def synthesize(self, text: str) -> bytes:
        self.calls.append(text)
        if text == self.block:
            self.release.wait(timeout=5)
        return _tone(self.tones.get(text, 9000))

    def wait_ready(self) -> None:
        return None


def _service(engine: FakeEngine, phrases: list[str]) -> SpeechService:
    service = SpeechService(engine=engine, process_factory=lambda text: None)
    service._cache_rate = RATE
    for phrase in phrases:
        service._cache[phrase] = _tone(engine.tones[phrase])
    return service


class LeadingSilenceTests(unittest.TestCase):
    def test_silence_has_the_configured_duration(self) -> None:
        silence = _silence(LEADING_SILENCE_MS, RATE)
        self.assertEqual(len(silence), 2 * int(RATE * LEADING_SILENCE_MS / 1000))
        self.assertEqual(set(silence), {0})

    def test_zero_disables_it(self) -> None:
        self.assertEqual(_silence(0, RATE), b"")


class TrimTrailingSilenceTests(unittest.TestCase):
    def test_trailing_silence_is_cut_to_a_short_tail(self) -> None:
        pcm = _tone(5000, 100) + b"\x00\x00" * RATE  # 1 s de silêncio no fim
        trimmed = _trim_trailing_silence(pcm, RATE)
        self.assertLess(len(trimmed), len(pcm) // 4)
        self.assertTrue(trimmed.startswith(_tone(5000, 100)))

    def test_all_silence_is_left_alone(self) -> None:
        pcm = b"\x00\x00" * 100
        self.assertEqual(_trim_trailing_silence(pcm, RATE), pcm)


class SegmentationTests(unittest.TestCase):
    """O que está no cache sai do cache; o resto é juntado e sintetizado."""

    def setUp(self) -> None:
        self.engine = FakeEngine(
            {"Resultado": 1000, "vírgula": 2000, "1": 3001, "3": 3003,
             "e y igual a": 4000, "x igual a": 4100, "real": 4200, "ângulo": 4300}
        )
        self.service = _service(self.engine, list(self.engine.tones))

    def test_result_split_between_cache_and_synthesis(self) -> None:
        self.assertEqual(
            self.service._segments("Resultado 53 vírgula 1 3"),
            [(True, "Resultado"), (False, "53"), (True, "vírgula"), (True, "1"), (True, "3")],
        )

    def test_longest_cached_phrase_wins(self) -> None:
        segments = self.service._segments("x igual a 1 e y igual a 3")
        self.assertIn((True, "e y igual a"), segments)
        self.assertIn((True, "x igual a"), segments)

    def test_trailing_punctuation_still_matches_the_cache(self) -> None:
        self.assertEqual(
            self.service._segments("real 1, ângulo 3"),
            [(True, "real"), (True, "1"), (True, "ângulo"), (True, "3")],
        )

    def test_only_the_cardinal_is_synthesized(self) -> None:
        list(self.service._produce_chunks("Resultado 53 vírgula 1 3"))
        self.assertEqual(self.engine.calls, ["53"])

    def test_chunks_follow_the_phrase_order(self) -> None:
        chunks = [pcm for pcm, _ in self.service._produce_chunks("Resultado 53 vírgula 1")]
        self.assertEqual(chunks, [_tone(1000), _tone(9000), _tone(2000), _tone(3001)])

    def test_prefix_is_ready_before_the_number_is_synthesized(self) -> None:
        chunks = self.service._produce_chunks("Resultado 53")
        first, _ = next(chunks)
        self.assertEqual(first, _tone(1000))
        self.assertEqual(self.engine.calls, [], "o número ainda não devia ter sido sintetizado")

    def test_whole_phrase_in_cache_is_one_chunk(self) -> None:
        chunks = list(self.service._produce_chunks("Resultado"))
        self.assertEqual(len(chunks), 1)

    def test_engine_not_ready_falls_back_to_one_chunk(self) -> None:
        self.engine.is_ready = False
        with mock.patch.object(speech, "_espeak_pcm", return_value=(b"\x01\x00", RATE)):
            chunks = list(self.service._produce_chunks("Resultado 53"))
        self.assertEqual(chunks, [(b"\x01\x00", RATE)])


def _write_fake_aplay(path: Path, body: str) -> None:
    path.write_text(f"#!{sys.executable}\n{body}")
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


@unittest.skipUnless(sys.platform.startswith("linux"), "usa grupos de processos")
class ChunkedPlaybackTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self._tmp, ignore_errors=True))
        self.aplay = self._tmp / "aplay"
        self.received = self._tmp / "received"
        self.starts = self._tmp / "starts"
        # Regista cada arranque e escreve o que recebe à medida que chega.
        _write_fake_aplay(
            self.aplay,
            "import sys\n"
            f"open({str(self.starts)!r}, 'a').write('x')\n"
            f"out = open({str(self.received)!r}, 'ab', buffering=0)\n"
            "while True:\n"
            "    data = sys.stdin.buffer.read1(65536)\n"
            "    if not data:\n"
            "        break\n"
            "    out.write(data)\n",
        )
        patcher = mock.patch.object(speech, "_APLAY", str(self.aplay))
        patcher.start()
        self.addCleanup(patcher.stop)

    def _received(self) -> bytes:
        return self.received.read_bytes() if self.received.exists() else b""

    def test_prefix_plays_before_the_number_finishes(self) -> None:
        engine = FakeEngine({"Resultado": 1000}, block="53")
        service = _service(engine, ["Resultado"])
        handle = _RawPlaybackProcess(lambda: service._produce_chunks("Resultado 53"))
        handle.start()
        try:
            prefix = _silence(LEADING_SILENCE_MS, RATE) + _tone(1000)
            self.assertTrue(
                _wait_until(lambda: self._received() == prefix),
                "o prefixo não chegou ao aplay enquanto o número era sintetizado",
            )
            self.assertTrue(handle.is_alive())
        finally:
            engine.release.set()
            handle.join(timeout=5)
        self.assertEqual(self._received(), prefix + _tone(9000))

    def test_one_aplay_per_phrase_and_silence_once(self) -> None:
        engine = FakeEngine({"Resultado": 1000, "vírgula": 2000, "1": 3001, "3": 3003})
        service = _service(engine, list(engine.tones))
        handle = _RawPlaybackProcess(lambda: service._produce_chunks("Resultado 53 vírgula 1 3"))
        handle.start()
        handle.join(timeout=5)
        self.assertEqual(self.starts.read_text(), "x", "mais de um aplay para a mesma frase")
        expected = (
            _silence(LEADING_SILENCE_MS, RATE)
            + _tone(1000) + _tone(9000) + _tone(2000) + _tone(3001) + _tone(3003)
        )
        self.assertEqual(self._received(), expected)

    def test_terminate_discards_pending_chunks(self) -> None:
        # "53" (sintetizado, travado) e "vírgula" (do cache) ficam pendentes
        # quando o corte chega com só o prefixo entregue.
        engine = FakeEngine({"Resultado": 1000, "vírgula": 2000}, block="53")
        service = _service(engine, ["Resultado", "vírgula"])
        handle = _RawPlaybackProcess(lambda: service._produce_chunks("Resultado 53 vírgula"))
        handle.start()
        prefix = _silence(LEADING_SILENCE_MS, RATE) + _tone(1000)
        self.assertTrue(_wait_until(lambda: self._received() == prefix))
        handle.terminate()
        engine.release.set()
        handle.join(timeout=5)
        self.assertFalse(handle.is_alive())
        received = self._received()
        self.assertNotIn(_tone(9000), received, "o número pendente tocou depois do corte")
        self.assertNotIn(_tone(2000), received, "um pedaço do cache tocou depois do corte")


if __name__ == "__main__":
    unittest.main()
