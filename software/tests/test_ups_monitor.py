"""UpsMonitor: leitura real do INA219 (registrador de Bus Voltage) via i2cget.

Não há hardware aqui, então injetamos um `runner` que devolve exatamente o que o
`i2cget ... w` devolveria (palavra little-endian). Verificamos a troca de bytes,
a conversão para tensão (LSB 4 mV, bits [15:3]) e a percentagem.
"""

import subprocess
import unittest

from software.hw_platform.ups import UpsMonitor


def _runner_for(word_le: int):
    """Runner que simula `i2cget -y BUS ADDR 0x02 w` devolvendo `word_le`."""

    def run(cmd, capture_output, text, check, timeout=None):
        return subprocess.CompletedProcess(cmd, 0, stdout=f"{word_le:#06x}\n", stderr="")

    return run


def _le_word_for_voltage(voltage: float) -> int:
    """Monta a palavra little-endian que o i2cget devolveria para `voltage`.

    Inverte a conta do driver: raw_be = (V / 4mV) << 3, depois troca os bytes.
    """
    raw_be = (round(voltage / 0.004) << 3) & 0xFFFF
    return ((raw_be & 0xFF) << 8) | ((raw_be >> 8) & 0xFF)


class UpsMonitorTest(unittest.TestCase):
    def test_bus_voltage_byte_swap_and_scale(self) -> None:
        ups = UpsMonitor(runner=_runner_for(_le_word_for_voltage(3.6)))
        status = ups.read_status()
        self.assertTrue(status.available)
        self.assertAlmostEqual(status.voltage, 3.6, places=2)

    def test_full_battery_is_about_100_percent(self) -> None:
        ups = UpsMonitor(runner=_runner_for(_le_word_for_voltage(4.2)))
        self.assertAlmostEqual(ups.read_status().battery_percent, 100.0, delta=1.0)

    def test_empty_battery_is_about_0_percent(self) -> None:
        ups = UpsMonitor(runner=_runner_for(_le_word_for_voltage(3.0)))
        self.assertAlmostEqual(ups.read_status().battery_percent, 0.0, delta=1.0)

    def test_midpoint_voltage_is_about_50_percent(self) -> None:
        ups = UpsMonitor(runner=_runner_for(_le_word_for_voltage(3.6)))
        self.assertAlmostEqual(ups.read_status().battery_percent, 50.0, delta=2.0)

    def test_is_low_when_below_configured_threshold(self) -> None:
        ups = UpsMonitor(low_percent=20, runner=_runner_for(_le_word_for_voltage(3.15)))
        status = ups.read_status()
        self.assertLessEqual(status.battery_percent, 20)
        self.assertTrue(status.is_low)

    def test_unreadable_i2c_is_reported_unavailable_not_faked(self) -> None:
        def failing(cmd, capture_output, text, check, timeout=None):
            raise FileNotFoundError("i2cget ausente")

        status = UpsMonitor(runner=failing).read_status()
        self.assertFalse(status.available)
        self.assertIsNone(status.battery_percent)

    def test_illegible_output_is_unavailable(self) -> None:
        def junk(cmd, capture_output, text, check, timeout=None):
            return subprocess.CompletedProcess(cmd, 0, stdout="lixo\n", stderr="")

        self.assertFalse(UpsMonitor(runner=junk).read_status().available)


if __name__ == "__main__":
    unittest.main()
