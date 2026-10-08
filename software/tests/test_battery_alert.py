"""BatteryMonitor: alerta de bateria baixa com anti-repetição, sem thread."""

import unittest

from software.accessibility.battery_alert import BatteryMonitor
from software.hw_platform.ups import UpsStatus


class _FakeSpeech:
    def __init__(self) -> None:
        self.alerts: list[str] = []

    def alert(self, text: str) -> None:
        self.alerts.append(text)


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


if __name__ == "__main__":
    unittest.main()
