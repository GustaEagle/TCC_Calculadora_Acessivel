"""Prioridade do áudio: alerta crítico > configuração (volume) > normal.

Mesma injeção de `process_factory` dos testes de interrupção (RF-08): um
processo falso bloqueia em join() até ser terminado, então controlamos quem
"está tocando" e verificamos quem corta quem.
"""

import threading
import time
import unittest

from software.accessibility.speech import SpeechService


class _FakeProcess:
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


class AudioPriorityTest(unittest.TestCase):
    def _make_service(self):
        started = threading.Event()
        processes: list[_FakeProcess] = []

        def factory(text: str) -> _FakeProcess:
            started.clear()
            proc = _FakeProcess(text, on_start=started.set)
            processes.append(proc)
            return proc

        service = SpeechService(process_factory=factory)
        self.addCleanup(service.stop)
        return service, processes, started

    def test_critical_alert_preempts_normal_speech(self) -> None:
        service, processes, started = self._make_service()
        service.say("tecla cinco")
        self.assertTrue(started.wait(timeout=1))

        service.alert("Bateria baixa")

        self.assertTrue(_wait_until(lambda: processes[0].terminated))
        self.assertTrue(_wait_until(lambda: len(processes) >= 2))
        self.assertEqual(processes[1].text, "Bateria baixa")

    def test_normal_speech_never_interrupts_a_playing_alert(self) -> None:
        service, processes, started = self._make_service()
        service.alert("Bateria baixa")
        self.assertTrue(started.wait(timeout=1))

        # Um resultado chegando durante o alerta NÃO pode cortá-lo.
        service.interrupt_and_say("Resultado quatorze")
        time.sleep(0.1)
        self.assertFalse(processes[0].terminated, "o alerta crítico foi interrompido")

        # Quando o alerta termina naturalmente, o resultado enfileirado toca.
        processes[0].terminate()
        self.assertTrue(_wait_until(lambda: len(processes) >= 2))
        self.assertEqual(processes[1].text, "Resultado quatorze")

    def test_volume_feedback_preempts_normal_but_not_critical(self) -> None:
        service, processes, started = self._make_service()
        service.say("tecla cinco")
        self.assertTrue(started.wait(timeout=1))

        # CONFIG corta o feedback normal...
        service.interrupt_and_say("Volume 50 por cento", priority=SpeechService.CONFIG)
        self.assertTrue(_wait_until(lambda: processes[0].terminated))
        self.assertTrue(_wait_until(lambda: len(processes) >= 2))
        self.assertEqual(processes[1].text, "Volume 50 por cento")

        # ...mas um alerta crítico corta o próprio feedback de volume.
        service.alert("Bateria baixa")
        self.assertTrue(_wait_until(lambda: processes[1].terminated))
        self.assertTrue(_wait_until(lambda: len(processes) >= 3))
        self.assertEqual(processes[2].text, "Bateria baixa")

    def test_playing_volume_is_not_cut_by_a_later_result(self) -> None:
        service, processes, started = self._make_service()
        service.interrupt_and_say("Volume 60 por cento", priority=SpeechService.CONFIG)
        self.assertTrue(started.wait(timeout=1))

        service.interrupt_and_say("Resultado dez")  # NORMAL
        time.sleep(0.1)
        self.assertFalse(processes[0].terminated, "o aviso de volume foi cortado por um resultado")


if __name__ == "__main__":
    unittest.main()
