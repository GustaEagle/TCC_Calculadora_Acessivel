import threading
import time
import unittest

from software.accessibility.speech import SpeechService


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
