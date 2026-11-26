"""Aviso de bateria na tela, simulação no PC e i2c-dev na imagem do Pi.

O indicador é função pura + um vigia no laço do Tk; aqui o Tk é falso. A
integração com os fronts reais está em BatteryIndicatorInFrontsTest, que
constrói as janelas (precisa do ttkbootstrap, como os outros testes de front).
"""

from __future__ import annotations

import contextlib
import re
import unittest
from pathlib import Path
from unittest import mock

from software.accessibility.battery_alert import (
    LEVEL_CRITICAL,
    LEVEL_LOW,
    LEVEL_OK,
    BatteryMonitor,
    BatteryReading,
)
from software.ui.shared.battery_indicator import (
    STYLE_CRITICAL,
    STYLE_LOW,
    BatteryIndicatorWatch,
    battery_indicator,
)

REPO = Path(__file__).resolve().parents[2]


class IndicatorTextTests(unittest.TestCase):
    def test_hidden_without_reading(self) -> None:
        self.assertEqual(battery_indicator(None)[0], "")
        self.assertEqual(battery_indicator(BatteryReading())[0], "")

    def test_hidden_when_battery_is_fine(self) -> None:
        self.assertEqual(battery_indicator(BatteryReading(LEVEL_OK, 80))[0], "")

    def test_low(self) -> None:
        self.assertEqual(
            battery_indicator(BatteryReading(LEVEL_LOW, 18.4)),
            ("BATERIA BAIXA 18%", STYLE_LOW),
        )

    def test_critical(self) -> None:
        self.assertEqual(
            battery_indicator(BatteryReading(LEVEL_CRITICAL, 6.6)),
            ("BATERIA NO FIM 7%", STYLE_CRITICAL),
        )


class _FakeRoot:
    def __init__(self) -> None:
        self.scheduled: list[tuple[int, object]] = []

    def after(self, ms, callback) -> None:
        self.scheduled.append((ms, callback))


class _FakeMonitor:
    def __init__(self, reading: BatteryReading) -> None:
        self.reading = reading

    def snapshot(self) -> BatteryReading:
        return self.reading


class WatchTests(unittest.TestCase):
    def test_no_monitor_means_nothing_scheduled(self) -> None:
        root = _FakeRoot()
        BatteryIndicatorWatch(root, None, lambda *_: None).start()
        self.assertEqual(root.scheduled, [])

    def test_applies_only_on_change_and_keeps_polling(self) -> None:
        root, applied = _FakeRoot(), []
        monitor = _FakeMonitor(BatteryReading(LEVEL_LOW, 18))
        watch = BatteryIndicatorWatch(root, monitor, lambda *a: applied.append(a), interval_ms=500)
        watch.start()
        watch.tick()  # mesma leitura: não redesenha
        monitor.reading = BatteryReading(LEVEL_CRITICAL, 9)
        watch.tick()
        self.assertEqual(
            applied, [("BATERIA BAIXA 18%", STYLE_LOW), ("BATERIA NO FIM 9%", STYLE_CRITICAL)]
        )
        self.assertEqual(len(root.scheduled), 3)
        self.assertTrue(all(ms == 500 for ms, _ in root.scheduled))

    def test_stop_ends_the_polling(self) -> None:
        root = _FakeRoot()
        watch = BatteryIndicatorWatch(root, _FakeMonitor(BatteryReading()), lambda *_: None)
        watch.stop()
        watch.tick()
        self.assertEqual(root.scheduled, [])

    def test_keeps_polling_even_if_drawing_fails(self) -> None:
        root = _FakeRoot()

        def broken(*_):
            raise RuntimeError("Tk caiu")

        watch = BatteryIndicatorWatch(root, _FakeMonitor(BatteryReading(LEVEL_LOW, 18)), broken)
        with self.assertRaises(RuntimeError):
            watch.tick()
        self.assertEqual(len(root.scheduled), 1, "o indicador morreu em silêncio")


class SimulationFlagTests(unittest.TestCase):
    """--simulate-battery: testar o aviso no PC, sem UPS HAT."""

    def test_flag_parses(self) -> None:
        from software.app import build_parser

        self.assertEqual(build_parser().parse_args(["--simulate-battery", "23"]).simulate_battery, 23)
        self.assertIsNone(build_parser().parse_args([]).simulate_battery)

    def test_simulation_starts_a_monitor_without_hardware(self) -> None:
        from software import app

        speech = mock.MagicMock()
        monitor = app.start_battery_monitor(speech, simulate=23)
        try:
            self.assertIsInstance(monitor, BatteryMonitor)
            monitor.check()
            self.assertEqual(monitor.snapshot().percent, 23)
        finally:
            monitor.stop()

    def test_without_simulation_and_without_hardware_there_is_no_monitor(self) -> None:
        from software import app

        with mock.patch.object(app.UpsMonitor, "available", return_value=False):
            self.assertIsNone(app.start_battery_monitor(mock.MagicMock()))


class PiImageI2cTests(unittest.TestCase):
    """Sem o módulo i2c-dev, /dev/i2c-1 não existe e o aviso nunca dispara."""

    def setUp(self) -> None:
        self.script = (REPO / "system/rpi-os/alpine/build-alpine-img.sh").read_text()

    def _function(self, name: str) -> str:
        match = re.search(rf"^{name}\(\) \{{\n(.*?)^\}}", self.script, re.S | re.M)
        self.assertIsNotNone(match, f"função {name} não encontrada")
        return match.group(1)

    def test_i2c_dev_is_loaded_at_boot(self) -> None:
        body = self._function("apply_overlay_and_app")
        self.assertIn("i2c-dev", body)
        self.assertIn("/etc/modules", body)

    def test_it_runs_also_when_reusing_the_rootfs(self) -> None:
        """apply_overlay_and_app corre nos dois caminhos do main()."""
        main = self._function("main")
        self.assertEqual(main.count("apply_overlay_and_app"), 2)

    def test_the_bus_is_enabled_and_readable_by_the_kiosk(self) -> None:
        cfg = (REPO / "system/rpi-os/alpine/overlay/boot/usercfg.txt").read_text()
        self.assertRegex(cfg, r"(?m)^dtparam=i2c_arm=on")
        packages = (REPO / "system/rpi-os/alpine/packages").read_text()
        self.assertRegex(packages, r"(?m)^i2c-tools\b")


FRONTS = ("lcd", "hdmi")


class BatteryIndicatorInFrontsTest(unittest.TestCase):
    """Os dois fronts mostram o aviso na barra de indicadores.

    Uma janela de cada vez, destruída no fim de cada iteração, como nos outros
    testes de front: o ttkbootstrap não aceita duas janelas vivas no processo.
    """

    @contextlib.contextmanager
    def _app(self, front: str, reading: BatteryReading | None):
        module = __import__(f"software.ui.{front}.app", fromlist=["CalculatorApp"])
        monitor = None if reading is None else _FakeMonitor(reading)
        app = module.CalculatorApp(speech=mock.MagicMock(), battery=monitor)
        try:
            yield app
        finally:
            app.root.destroy()

    def test_low_battery_shows_in_both_fronts(self) -> None:
        for front in FRONTS:
            with self.subTest(front=front), self._app(front, BatteryReading(LEVEL_LOW, 18)) as app:
                app.battery_watch.tick()
                self.assertEqual(app.battery_var.get(), "BATERIA BAIXA 18%")

    def test_critical_battery_shows_in_red(self) -> None:
        for front in FRONTS:
            with self.subTest(front=front), self._app(front, BatteryReading(LEVEL_CRITICAL, 7)) as app:
                app.battery_watch.tick()
                self.assertEqual(app.battery_var.get(), "BATERIA NO FIM 7%")
                self.assertIn("danger", str(app.battery_label.cget("style")).lower())

    def test_fine_battery_shows_nothing(self) -> None:
        for front in FRONTS:
            with self.subTest(front=front), self._app(front, BatteryReading(LEVEL_OK, 80)) as app:
                app.battery_watch.tick()
                self.assertEqual(app.battery_var.get(), "")

    def test_front_without_ups_has_an_empty_indicator(self) -> None:
        for front in FRONTS:
            with self.subTest(front=front), self._app(front, None) as app:
                app.battery_watch.start()
                self.assertEqual(app.battery_var.get(), "")


if __name__ == "__main__":
    unittest.main()
