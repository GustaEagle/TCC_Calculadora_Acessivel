"""Leitura do UPS HAT da Waveshare (bateria) por I2C.

O UPS HAT expõe um medidor INA219 no barramento I2C1 (GPIO2/GPIO3, pinos 3/5 -
reservados a ele em `keypad_pinout.py`), no endereço 0x42 (RF-06/RF-14, ver
`docs/waveshare/UPS_HAT.md`). Deste medidor sai a **tensão do barramento** da
bateria, de onde estimamos a carga restante.

Como lemos (sem leitura fictícia): o registrador 0x02 (Bus Voltage) do INA219 é
preenchido continuamente pelo próprio chip após o reset, sem precisar escrever a
calibração - então basta LER esse registrador. Fazemos a leitura com o `i2cget`
(pacote `i2c-tools`, já na imagem para o bring-up do UPS), em vez de puxar uma
biblioteca Python de I2C nova: é o mesmo estilo do resto do projeto, que chama
binários do sistema (`aplay`, `xrandr`, `amixer`). O `i2cget ... w` devolve a
palavra em little-endian; o INA219 é big-endian, então trocamos os bytes.

Fora do Raspberry Pi (sem `/dev/i2c-*` ou sem `i2cget`) a leitura não é inventada:
`read_status()` devolve `available=False` e quem monitora simplesmente não alerta.

Bateria do HAT: 2x 18650 em paralelo (3,7 V nominal, 3,0 V vazio - 4,2 V cheio);
a percentagem segue a fórmula do demo oficial, (V - vazio) / (cheio - vazio). As
tensões de referência e o endereço/barramento são ajustáveis por ambiente.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Barramento e endereço do INA219 do UPS HAT (0x42 na FAQ da wiki). Em alguns
# Pi o barramento é 0 em vez de 1; sobrescreva por ambiente se precisar.
_I2C_BUS = os.environ.get("CALC_UPS_I2C_BUS", "1")
_I2C_ADDR = int(os.environ.get("CALC_UPS_I2C_ADDR", "0x42"), 0)

# Registrador de Bus Voltage do INA219.
_REG_BUS_VOLTAGE = 0x02
# LSB do Bus Voltage = 4 mV; os dados ficam nos bits [15:3].
_BUS_VOLTAGE_LSB_V = 0.004

# Tensões de referência da bateria (ajustáveis). Vazio/cheio por célula, já que
# as duas células do HAT ficam em paralelo (a tensão não soma).
_EMPTY_V = float(os.environ.get("CALC_UPS_EMPTY_V", "3.0"))
_FULL_V = float(os.environ.get("CALC_UPS_FULL_V", "4.2"))

_I2C_TIMEOUT_S = 2.0


def _clamp_percent(value: float) -> float:
    return max(0.0, min(100.0, value))


@dataclass(frozen=True)
class UpsStatus:
    label: str
    battery_percent: float | None = None
    voltage: float | None = None
    is_low: bool = False
    # False quando não foi possível ler o hardware (fora do Pi, sem i2c-tools):
    # o monitor usa isto para não emitir alerta com base em nada.
    available: bool = False


class UpsMonitor:
    """Lê o nível da bateria do Waveshare UPS HAT pelo INA219 (I2C)."""

    def __init__(
        self,
        *,
        bus: str = _I2C_BUS,
        address: int = _I2C_ADDR,
        empty_v: float = _EMPTY_V,
        full_v: float = _FULL_V,
        low_percent: float | None = None,
        runner=subprocess.run,
    ) -> None:
        self._bus = str(bus)
        self._address = address
        self._empty_v = empty_v
        self._span_v = max(0.01, full_v - empty_v)
        # O limite de "bateria baixa" vive no monitor de alerta
        # (accessibility/battery_alert.py); aqui só é guardado para quem quiser
        # marcar is_low a partir do próprio status.
        self._low_percent = low_percent
        self._run = runner
        self._i2cget = shutil.which("i2cget") or "i2cget"

    def available(self) -> bool:
        """Há hardware para ler? (barramento I2C presente e `i2cget` instalado)."""
        return os.path.exists(f"/dev/i2c-{self._bus}") and shutil.which("i2cget") is not None

    def read_status(self) -> UpsStatus:
        voltage = self._read_bus_voltage()
        if voltage is None:
            return UpsStatus(label="indisponível", available=False)
        percent = _clamp_percent((voltage - self._empty_v) / self._span_v * 100.0)
        is_low = self._low_percent is not None and percent <= self._low_percent
        return UpsStatus(
            label="UPS HAT",
            battery_percent=percent,
            voltage=voltage,
            is_low=is_low,
            available=True,
        )

    # ------------------------------------------------------------------

    def _read_bus_voltage(self) -> float | None:
        """Tensão do barramento (V) lida do registrador 0x02, ou None em falha."""
        raw = self._read_word(_REG_BUS_VOLTAGE)
        if raw is None:
            return None
        # i2cget "w" devolve little-endian; o INA219 é big-endian -> troca bytes.
        swapped = ((raw & 0xFF) << 8) | ((raw >> 8) & 0xFF)
        # Dados nos bits [15:3]; LSB = 4 mV.
        return (swapped >> 3) * _BUS_VOLTAGE_LSB_V

    def _read_word(self, register: int) -> int | None:
        cmd = [
            self._i2cget,
            "-y",
            self._bus,
            hex(self._address),
            hex(register),
            "w",
        ]
        try:
            proc = self._run(
                cmd, capture_output=True, text=True, check=True, timeout=_I2C_TIMEOUT_S
            )
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("i2cget do UPS falhou (%s); bateria indisponível.", exc)
            return None
        text = proc.stdout.strip()
        if not text:
            return None
        try:
            return int(text, 0) & 0xFFFF
        except ValueError:
            logger.warning("i2cget devolveu valor ilegível: %r", text)
            return None
