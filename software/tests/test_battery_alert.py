"""BatteryMonitor: alerta de bateria baixa com anti-repetição, sem thread."""

import unittest

from software.accessibility.battery_alert import (
    CRITICAL_ALERT_BEEPS,
    LEVEL_CRITICAL,
    LEVEL_LOW,
    LEVEL_OK,
    LOW_ALERT_BEEPS,
    BatteryMonitor,
    default_alert_message,
    default_critical_message,
)
from software.hw_platform.ups import SimulatedUps, UpsStatus
from software.ui.shared.error_messages import ERROR_MESSAGES


class _FakeSpeech:
    def __init__(self) -> None:
        self.alerts: list[str] = []
        self.beeps: list[int] = []

    def alert(self, text: str, beeps: int = 0) -> None:
        self.alerts.append(text)
        self.beeps.append(beeps)


class _FakeUps:
    def __init__(self) -> None:
        self.percent = 100.0

    def available(self) -> bool:
        return True

    def read_status(self) -> UpsStatus:
        return UpsStatus(
            label="fake", battery_percent=self.percent, voltage=None,
            is_low=False, available=True,
        )


class _Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


class BatteryMonitorTest(unittest.TestCase):
    def _monitor(self, **kw):
        self.speech = _FakeSpeech()
        self.ups = _FakeUps()
        self.clock = _Clock()
        defaults = dict(
            interval=999, low_percent=20, renotify_drop=5,
            renotify_interval=300, clock=self.clock,
        )
        defaults.update(kw)
        return BatteryMonitor(self.speech, self.ups, **defaults)

    def test_no_alert_above_threshold(self) -> None:
        mon = self._monitor()
        self.ups.percent = 55
        mon.check()
        self.assertEqual(self.speech.alerts, [])

    def test_alerts_once_when_crossing_the_threshold(self) -> None:
        mon = self._monitor()
        self.ups.percent = 18
        mon.check()
        mon.check()  # ainda baixa, mas não caiu mais nem passou o tempo
        self.assertEqual(len(self.speech.alerts), 1)

    def test_realerts_after_a_further_drop(self) -> None:
        mon = self._monitor()
        self.ups.percent = 18
        mon.check()
        self.ups.percent = 12  # caiu mais que renotify_drop (5)
        mon.check()
        self.assertEqual(len(self.speech.alerts), 2)

    def test_realerts_after_the_configured_interval(self) -> None:
        mon = self._monitor()
        self.ups.percent = 18
        mon.check()
        self.clock.t += 301  # passou renotify_interval
        mon.check()
        self.assertEqual(len(self.speech.alerts), 2)

    def test_recovery_rearms_the_latch(self) -> None:
        mon = self._monitor()
        self.ups.percent = 18
        mon.check()
        self.ups.percent = 60  # carregou / recuperou
        mon.check()
        self.ups.percent = 18  # novo ciclo de descarga
        mon.check()
        self.assertEqual(len(self.speech.alerts), 2)

    def test_unavailable_ups_never_alerts(self) -> None:
        mon = self._monitor()
        self.ups.read_status = lambda: UpsStatus(label="x", available=False)
        mon.check()
        self.assertEqual(self.speech.alerts, [])

    def test_threshold_is_configurable(self) -> None:
        mon = self._monitor(low_percent=40)
        self.ups.percent = 35
        mon.check()
        self.assertEqual(len(self.speech.alerts), 1)


class CriticalLevelTest(unittest.TestCase):
    """"Bateria no fim": um segundo nível, mais urgente, perto do desligamento."""

    def _monitor(self, **kw):
        self.speech = _FakeSpeech()
        self.ups = _FakeUps()
        self.clock = _Clock()
        defaults = dict(
            interval=999, low_percent=20, critical_percent=10, renotify_drop=5,
            renotify_interval=300, critical_renotify_interval=60, clock=self.clock,
        )
        defaults.update(kw)
        return BatteryMonitor(self.speech, self.ups, **defaults)

    def test_critical_uses_the_urgent_message(self) -> None:
        mon = self._monitor()
        self.ups.percent = 8
        mon.check()
        self.assertEqual(self.speech.alerts, [default_critical_message(8)])

    def test_low_then_critical_escalates_immediately(self) -> None:
        """De "baixa" a "no fim" avisa logo, sem esperar queda nem intervalo."""
        mon = self._monitor()
        self.ups.percent = 13
        mon.check()
        self.ups.percent = 10  # caiu só 3 (< renotify_drop) mas cruzou o limite
        mon.check()
        self.assertEqual(
            self.speech.alerts, [default_alert_message(13), default_critical_message(10)]
        )

    def test_critical_repeats_on_its_shorter_interval(self) -> None:
        mon = self._monitor()
        self.ups.percent = 8
        mon.check()
        self.clock.t += 59
        mon.check()
        self.assertEqual(len(self.speech.alerts), 1)
        self.clock.t += 2  # passou o intervalo do nível "no fim" (60 s)
        mon.check()
        self.assertEqual(len(self.speech.alerts), 2)

    def test_critical_never_above_low(self) -> None:
        mon = self._monitor(low_percent=15, critical_percent=30)
        self.ups.percent = 20  # acima de "baixa": não pode ser "no fim"
        mon.check()
        self.assertEqual(self.speech.alerts, [])


class AlertBeepsTest(unittest.TestCase):
    """Sinal sonoro antes da frase: 2 bipes na baixa, 3 no fim."""

    def _monitor(self):
        self.speech = _FakeSpeech()
        self.ups = _FakeUps()
        return BatteryMonitor(
            self.speech, self.ups, interval=999, low_percent=20,
            critical_percent=10, clock=_Clock(),
        )

    def test_low_battery_beeps_twice(self) -> None:
        mon = self._monitor()
        self.ups.percent = 18
        mon.check()
        self.assertEqual(self.speech.beeps, [LOW_ALERT_BEEPS])
        self.assertEqual(LOW_ALERT_BEEPS, 2)

    def test_critical_battery_beeps_three_times(self) -> None:
        mon = self._monitor()
        self.ups.percent = 7
        mon.check()
        self.assertEqual(self.speech.beeps, [CRITICAL_ALERT_BEEPS])
        self.assertEqual(CRITICAL_ALERT_BEEPS, 3)


class MessagesTest(unittest.TestCase):
    """Frases curtas e de ação: a carga e "Conecte o carregador"."""

    def test_low_message(self) -> None:
        self.assertEqual(
            default_alert_message(18.4),
            "Bateria baixa, 18 por cento. Conecte o carregador.",
        )

    def test_critical_message(self) -> None:
        self.assertEqual(
            default_critical_message(6.6),
            "Bateria no fim, 7 por cento. A calculadora vai desligar. "
            "Conecte o carregador agora.",
        )

    def test_the_spoken_phrase_has_no_warning_number(self) -> None:
        """O número do aviso (020) fica no log e no catálogo, não na voz."""
        for message in (default_alert_message(15), default_critical_message(5)):
            with self.subTest(message=message):
                self.assertNotIn("020", message)
                self.assertNotIn("Aviso", message)
                self.assertIn("Conecte o carregador", message)


class SnapshotTest(unittest.TestCase):
    """A última leitura, que a tela consulta, com histerese nos limites."""

    def _monitor(self):
        self.speech = _FakeSpeech()
        self.ups = _FakeUps()
        return BatteryMonitor(
            self.speech, self.ups, interval=999, low_percent=20,
            critical_percent=10, clock=_Clock(),
        )

    def test_no_reading_yet(self) -> None:
        reading = self._monitor().snapshot()
        self.assertIsNone(reading.level)
        self.assertIsNone(reading.percent)

    def test_levels(self) -> None:
        mon = self._monitor()
        for percent, level in ((55, LEVEL_OK), (18, LEVEL_LOW), (7, LEVEL_CRITICAL)):
            with self.subTest(percent=percent):
                self.ups.percent = percent
                mon.check()
                self.assertEqual(mon.snapshot().level, level)
                self.assertEqual(mon.snapshot().percent, percent)

    def test_indicator_does_not_flicker_just_above_the_limit(self) -> None:
        """A 21% (acima de 20, mas sem a folga de 3 pontos) continua "baixa",
        e sem novo aviso de voz."""
        mon = self._monitor()
        self.ups.percent = 19
        mon.check()
        self.ups.percent = 21
        mon.check()
        self.assertEqual(mon.snapshot().level, LEVEL_LOW)
        self.assertEqual(len(self.speech.alerts), 1)
        self.ups.percent = 23
        mon.check()
        self.assertEqual(mon.snapshot().level, LEVEL_OK)

    def test_unavailable_keeps_the_last_reading(self) -> None:
        mon = self._monitor()
        self.ups.percent = 18
        mon.check()
        self.ups.read_status = lambda: UpsStatus(label="x", available=False)
        mon.check()
        self.assertEqual(mon.snapshot().level, LEVEL_LOW)


class SimulatedDischargeTest(unittest.TestCase):
    """Uma descarga simulada inteira: o que o PC mostra com --simulate-battery."""

    def test_full_discharge_from_23_percent(self) -> None:
        speech = _FakeSpeech()
        mon = BatteryMonitor(
            speech, SimulatedUps(23, step=1), interval=999, low_percent=20,
            critical_percent=10, renotify_drop=5, clock=_Clock(),
        )
        for _ in range(24):
            mon.check()
        # 20% (baixa), 15% (caiu 5), 10% (no fim), 5% (caiu 5), 0% (caiu 5).
        self.assertEqual(
            speech.alerts,
            [
                default_alert_message(20),
                default_alert_message(15),
                default_critical_message(10),
                default_critical_message(5),
                default_critical_message(0),
            ],
        )

    def test_simulated_ups_never_goes_below_the_floor(self) -> None:
        ups = SimulatedUps(2, step=1)
        readings = [ups.read_status().battery_percent for _ in range(5)]
        self.assertEqual(readings, [2, 1, 0, 0, 0])


class CatalogueTest(unittest.TestCase):
    def test_wrn_020_exists_in_the_error_catalogue(self) -> None:
        """WRN-020 tem de existir no catálogo usado pela UI (RF-07)."""
        self.assertIn("WRN-020", ERROR_MESSAGES)


if __name__ == "__main__":
    unittest.main()
